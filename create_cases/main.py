import argparse

import requests

from shared.case_config import CaseConfig
from shared.exceptions import InvalidData


def create_test_case(session: requests.Session, config: CaseConfig) -> str:
    payload = {
        'name': '[Placeholder] Temporary name',
        'projectKey': config.jira_project_key,
        'owner': config.jira_case_owner
    }
    response = None
    try:
        response = session.post(f'{config.jira_base_url}/testcase', json=payload, timeout=60)
        response.raise_for_status()
        case = response.json()
        case_id = case.get('key') if isinstance(case, dict) else None
        if not case_id:
            raise InvalidData('Empty or invalid test case ID')
        return case_id
    except Exception as e:
        status = response.status_code if response else 'no response'
        raise type(e)(f'Failed to create test case: {e}, status = {status}') from e


def main() -> None:
    parser = argparse.ArgumentParser(description='Creates draft Zephyr test cases')
    parser.add_argument('qty', type=int, nargs='?', default=1, help='number of test cases to create (default: 1)')
    args = parser.parse_args()
    cases = []
    try:
        if args.qty < 1:
            raise InvalidData('[ERROR] Number of test cases must be greater than 0')
        config = CaseConfig()
        with requests.Session() as session:
            session.headers.update(config.headers)
            for i in range(args.qty):
                try:
                    cases.append(create_test_case(session, config))
                except Exception as e:
                    print(f'[ERROR] Failed on creation test case {i + 1} of {args.qty}. {e}')
                    break
    except InvalidData as e:
        print(e)
    except Exception as e:
        print(f'[ERROR] Session error\n{e}')
    print(f'[DONE ] Script has been completed')
    cases_count = len(cases)
    if not cases_count:
        print('[DONE ] No test cases have been created')
    else:
        created_cases = f'{cases[0]}'
        if cases_count > 1:
            created_cases += f' - {cases[-1]}'
        print(f'[DONE ] Created {cases_count} of {args.qty} test case(s): {created_cases}')


if __name__ == '__main__':
    main()
