import fnmatch
from pathlib import Path
from typing import Optional, Tuple, List, Generator

import requests

import insert_ids.settings as st
from insert_ids.story_entity import StoryMeta, Scenario
from insert_ids.utils import read_file, write_file
from shared.case_config import StoryConfig
from shared.exceptions import ZException, Skipped, InvalidData
from shared.helpers import remove_prefix


class IDInserter:
    def __init__(self, qty: int, patterns: Optional[List[str]] = None):
        self._config = StoryConfig()
        self._ids_qty = qty
        self._ids_left = qty
        self._id_can_be_added = self._ids_left > 0
        self._patterns = patterns or []
        self._next_id = self._fetch_next_id()
        self._next_id_num = int(remove_prefix(self._next_id, self._config.id_prefix)) + 1
        self._id_generator = self._generate_id(self._next_id_num)

    def _generate_id(self, next_id: int) -> Generator[str, None, None]:
        _id = next_id
        while True:
            yield f'{self._config.id_prefix}{_id}'
            _id += 1

    def _fetch_next_id(self) -> str:
        response = None
        url = self._config.jira_base_url + '/testcase/search'
        params = {
            'query': f'projectKey = "{self._config.jira_project_key}"',
            'fields': 'key',
            'maxResults': '100000'
        }
        try:
            response = requests.get(url, params=params, headers=self._config.headers, timeout=60)
            response.raise_for_status()
            cases = response.json() or []
            if not isinstance(cases, list) or not cases or (next_id := cases[-1].get('key')) is None:
                raise InvalidData('Empty or invalid test case ID list')
            print(f'[DONE] Next test case ID: {next_id}')
            return next_id
        except Exception as e:
            status = response.status_code if response else 'no response'
            raise ZException(f'[ERROR] Failed to get test case ID list from Jira. {e}, status = {status}')

    def _process_story(self, file_path: Path) -> None:
        if not self._id_can_be_added:
            return
        try:
            story = read_file(file_path)
            story_meta, *scenarios = map(str.strip, story.split(st.TITLE))
            StoryMeta(story_meta, self._config.id_prefix).process_object()
        except Exception as e:
            print(e)
            return
        processed_story = [story_meta]
        try:
            for raw_scenario in (scenarios := iter(scenarios)):
                try:
                    scenario = Scenario(raw_scenario, self._config.id_prefix)
                    self._id_can_be_added, self._ids_left = scenario.process_object(self._id_generator, self._ids_left)
                    processed_story.append(scenario.format_scenario())
                    if not self._id_can_be_added:
                        processed_story.extend(scenarios)
                        break
                except Skipped:
                    processed_story.append(raw_scenario)
            write_file(file_path, f'{3 * "\n"}{st.TITLE} '.join(processed_story))
        except Exception:
            print(f'[ERROR] File {file_path} was not processed. {st.TITLE} {scenario.title}')

    def _process_story_dir(self, story_path: Path):
        for file_path in story_path.rglob('*.story'):
            if self._patterns and not any(fnmatch.fnmatch(file_path.name, pattern) for pattern in self._patterns):
                continue
            self._process_story(file_path)
            if not self._id_can_be_added or not self._ids_left:
                break

    def run(self) -> Tuple[int, str]:
        story_path = Path(self._config.story_dir)
        if story_path.is_file():
            self._process_story(story_path)
        else:
            self._process_story_dir(story_path)
        inserted_count = self._ids_qty - self._ids_left
        if not inserted_count:
            return 0, ''
        inserted_ids = self._config.id_prefix + str(self._next_id_num + 1)
        if inserted_count > 1:
            inserted_ids += (' - ' + self._config.id_prefix + str(self._next_id_num + inserted_count))
        return inserted_count, inserted_ids
