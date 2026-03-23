import os

from shared.exceptions import InvalidData

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    load_dotenv = None


class BaseConfig:
    _base_params = ['JIRA_BASE_URL', 'JIRA_TOKEN', 'JIRA_PROJECT_KEY']
    jira_base_url: str
    jira_token: str
    jira_project_key: str

    def __init__(self):
        required_params = self._base_params + getattr(self, '_extra_params', [])
        config_params = {var: os.getenv(var, '') for var in required_params}
        missing = [param for param, value in config_params.items() if not value]
        if missing:
            raise InvalidData(f'[ERROR] Missing env variables: {", ".join(missing)}')

        for param, value in config_params.items():
            setattr(self, param.lower(), value)
        self.id_prefix = self.jira_project_key + '-T'
        self.req_prefix = self.jira_project_key + '-'
        self.headers = {
            'Authorization': f'Bearer {self.jira_token}',
            'Content-Type': 'application/json'
        }


class CaseConfig(BaseConfig):
    _extra_params = ['JIRA_CASE_OWNER']
    jira_case_owner: str


class CycleConfig(BaseConfig):
    _extra_params = ['JIRA_CASE_OWNER', 'JIRA_CYCLE_ID', 'ALLURE_BASE_DIR']
    jira_case_owner: str
    allure_base_dir: str
    jira_cycle_id: str


class StoryConfig(BaseConfig):
    _extra_params = ['STORY_DIR']
    story_dir: str
