from typing import List, Tuple, Optional

import export_results.settings as st
import shared.constants as const
from shared.exceptions import InvalidData, Skipped
from shared.helpers import remove_prefix


class JSONScenario:
    def __init__(self, json: dict, id_prefix: str, req_prefix: str):
        self.id_prefix = id_prefix
        self.req_prefix = req_prefix
        self.id, self.json = self.validate_json(json)
        self.title = ''
        self.parameterized = None
        self.multitest = False
        self.folder = None
        self.reqs_ids = []
        self.status = self.json.get('status', '').lower() == st.PASSED
        self.steps = ''

    def parse_json(self) -> None:
        self.parse_title(self.json.get('name').strip())
        self.parse_labels(self.json.get('labels'))
        if self.multitest:
            self.parse_params(self.json.get('parameters'))
        self.parse_reqs(self.json.get('links', []))
        self.parse_steps(self.json.get('steps'))
        return None

    def is_valid_id(self, _id: str, prefix: Optional[str] = None) -> bool:
        if prefix is None:
            prefix = self.id_prefix
        return _id.startswith(prefix) and remove_prefix(_id, prefix).isdigit()

    def validate_id(self, _id: str, prefix: Optional[str] = None) -> str:
        if not self.is_valid_id(_id, prefix):
            raise InvalidData(f'[ERROR] Invalid {const.ID} is specified: {_id or None}')
        return _id

    @staticmethod
    def should_ignore(line: str, ignored_words: List[str]) -> bool:
        return any(line.lower().startswith(word.lower()) for word in ignored_words)

    def validate_json(self, json: dict) -> Tuple[str, dict]:
        if not json or not isinstance(json, dict) or not json.get('labels', None):
            raise InvalidData(f'[ERROR] Invalid JSON file format')
        for label in json.get('labels'):
            if label.get('name', '') == const.ID:
                return self.validate_id(label.get('value', '')), json
        if self.should_ignore(json.get('name').strip(), const.IGNORED_TITLES):
            raise Skipped(f'[NOTE ] Scenario is ignored: {json.get("name").strip()}')
        raise InvalidData(f'[ERROR] Test case ID not found: {json.get("name").strip()}')

    def parse_title(self, title: str) -> None:
        if self.should_ignore(title, const.IGNORED_TITLES):
            raise Skipped(f'[NOTE ] Scenario is ignored: {title}')
        head, sep, tail = title.partition('[')
        self.parameterized = bool(sep)
        self.title = head.strip() if self.parameterized else title
        return None

    def parse_labels(self, labels: List[dict]) -> None:
        for label in labels:
            if label.get('name', '') == 'tag':
                if not self.multitest and label.get('value', '') == const.META_MARK + const.MULTITEST:
                    self.multitest = True
                    self.id = None if self.multitest else self.id
                elif not self.folder and label.get('value', '').startswith(const.META_MARK + st.FOLDER):
                    self.folder = remove_prefix(label.get('value', ''), const.META_MARK + st.FOLDER).strip()
            if self.multitest and self.folder:
                break
        return None

    def parse_reqs(self, links: List[dict]) -> None:
        self.reqs_ids = [self.validate_id(link.get('name', ''), prefix=self.req_prefix)
                         for link in links if link.get('type', '') == 'requirement']
        return None

    def parse_steps(self, steps: List[dict]) -> None:
        new_steps = []
        for step in steps:
            if step.get('status', 'skipped') != 'skipped' and not step.get('name', '').startswith('@'):
                lines = step.get('name', '').replace('␤', '\n').split('\n')
                for line in lines:
                    line = line.replace('｟', '').replace('｠', '').replace('"""', '')
                    if not self.should_ignore(line, st.BDD_WORDS):
                        if line.startswith('!') and not line.startswith('!|') and '|' in line:
                            line = line.replace('|', ' OR ')
                        line = '|' + line
                    new_steps.append(line)
        self.steps = '\n'.join(new_steps)
        return None

    def parse_params(self, parameters: List[dict]) -> None:
        for param in parameters:
            if param.get('name', '') == st.TITLE_SUFFIX:
                if not (title_suffix := param.get('value', '').strip()):
                    raise InvalidData(f'[ERROR] Invalid {st.TITLE_SUFFIX} is specified')
                self.title += f' ({title_suffix})'
            elif self.id is None and param.get('name', '') == const.ID_HEADER:
                self.id = self.validate_id(param.get('value', ''))
        return None

    def format_case_body(self, jira_case_owner: str, region: str) -> dict:
        payload = {
            'name': f'[{region}] {self.title}',
            'folder': self.folder,
            'status': 'Approved',
            'owner': jira_case_owner,
            'issueLinks': self.reqs_ids,
            'testScript': {
                'type': 'BDD',
                'text': self.steps
            }
        }
        return payload

    def __bool__(self) -> bool:
        return bool(self.status)
