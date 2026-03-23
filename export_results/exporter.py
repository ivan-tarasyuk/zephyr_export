import asyncio
from pathlib import Path
from typing import Optional, Tuple

import aiohttp

from export_results.json_scenario import JSONScenario
import export_results.settings as st
from export_results.utils import read_json, write_json, safe_async
from shared.case_config import CycleConfig
from shared.exceptions import ZException, Skipped, RequestException


class ResultExporter:
    def __init__(self, send_status: bool):
        self._config = CycleConfig()
        self._session = None
        self._file_semaphore = asyncio.Semaphore(st.MAX_IO_FILE_TASKS)
        self._request_semaphore = asyncio.Semaphore(st.MAX_REQUEST_TASKS)
        self._send_status = send_status
        self._exported_count = 0

    async def __aenter__(self):
        self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()

    @safe_async
    async def _read_json(self, file_path: Path) -> dict:
        async with self._file_semaphore:
            return await read_json(file_path)

    @safe_async
    async def _write_json(self, file_path: Path, data: dict) -> None:
        async with self._file_semaphore:
            return await write_json(file_path, data)

    async def _request(self, method: str, endpoint: str, payload: dict) -> None:
        if not self._session:
            raise RequestException('[ERROR] Session is not initialized')
        url = f'{self._config.jira_base_url}/{endpoint}'
        async with self._request_semaphore:
            try:
                async with self._session.request(method, url, json=payload) as response:
                    if response.status in (200, 201, 204):
                        print(f'[DONE ] Request succeeded: {method} /{endpoint}')
                        return
                    text = await response.text()
                    print(f'[ERROR] Request {method} /{endpoint} failed, status = {response.status}')
                    print(f'[ERROR] {text}')
                    file_path = Path(f'{payload.get("name", "unknown").translate(st.TRANSLATION)}.json')
                    await self._write_json(file_path, payload)
            except ZException:
                pass
            except Exception as e:
                raise RequestException(f'[ERROR] An error occurred for request {method} /{endpoint}. {e}')

    @safe_async
    async def _post(self, endpoint: str, payload: dict) -> None:
        return await self._request('POST', endpoint, payload)

    @safe_async
    async def _put(self, endpoint: str, payload: dict) -> None:
        return await self._request('PUT', endpoint, payload)

    @staticmethod
    def _format_result_body(env: str, status: bool) -> dict:
        body = {
            'status': 'Pass' if status else 'Fail',
            'environment': env.upper()
        }
        return body

    @staticmethod
    def _parse_dir_name(path: Path) -> Optional[Tuple[str, str]]:
        if not path.name.startswith(st.DIR_PREFIX):
            return
        try:
            _, env, region = path.name.split('_')
            return env, region
        except ValueError:
            return

    async def _process_file(self, file_path: Path, pending: set, completed: set) -> None:
        json = await self._read_json(file_path)
        if not json:
            return
        try:
            scenario = JSONScenario(json, self._config.id_prefix, self._config.req_prefix)
        except Skipped:
            return
        except Exception as e:
            print(f'{e}, file {file_path}')
            return
        if scenario.id in completed:
            return
        env, region = self._parse_dir_name(file_path.parent.parent)
        if scenario.id not in pending:
            scenario.parse_json()
            payload = scenario.format_case_body(self._config.jira_case_owner, region)
            await self._put(f'testcase/{scenario.id}', payload)
            self._exported_count += 1
            if scenario.parameterized and not scenario.multitest:
                pending.add(scenario.id)
        if scenario.id in pending and scenario.status:
            return
        if self._send_status:
            endpoint = f'testrun/{self._config.jira_cycle_id}/testcase/{scenario.id}/testresult'
            payload = self._format_result_body(env, scenario.status)
            await self._post(endpoint, payload)
        if scenario.id in pending:
            completed.add(scenario.id)
            pending.discard(scenario.id)

    async def _process_dir(self, path: Path):
        results_dir = path / 'allure-results'
        if not results_dir.exists():
            print(f'[ERROR] Allure results path {results_dir} does not exist')
            return
        pending, completed = set(), set()
        tasks = [asyncio.create_task(self._process_file(file_path, pending, completed))
                 for file_path in results_dir.glob('*.json')]
        if not tasks:
            print(f'[ERROR] No test execution results have been found at {results_dir}')
            return
        await asyncio.gather(*tasks)
        if not self._send_status:
            return
        env, _ = self._parse_dir_name(path)
        tasks = []
        for scenario_id in pending:
            endpoint = f'testrun/{self._config.jira_cycle_id}/testcase/{scenario_id}/testresult'
            payload = self._format_result_body(env, True)
            tasks.append(asyncio.create_task(self._post(endpoint, payload)))
        await asyncio.gather(*tasks)

    async def run(self) -> int:
        tasks = []
        for path in Path(self._config.allure_base_dir).iterdir():
            if path.is_dir() and self._parse_dir_name(path):
                tasks.append(asyncio.create_task(self._process_dir(path)))
        await asyncio.gather(*tasks)
        return self._exported_count
