# Jira/Zephyr Test Case Sync Toolkit

---

## Overview
These scripts synchronize automated tests implemented in a Vividus-based test suite with Zephyr Scale Test Management System integrated into Jira.

The solution helps to:
- Keep traceability between requirements (Jira), automated scenarios (Vividus `.story`), and Zephyr test cases
- Keep Zephyr test cases up to date as the automation suite changes
- Optionally export automated execution results into a Zephyr test cycle for reporting

---

## Scripts
- [insert_ids.py](insert_ids.py) - walks `.story` files and inserts test case IDs into scenarios; support "multi-test export" scenarios
- [create_cases.py](create_cases.py) - creates draft Zephyr test cases via ATM API
- [export_results.py](export_results.py) - parses Allure JSON results and updates Zephyr test case content

---

## Prerequisites
- Python `3.10+`
- Network access to Jira / Zephyr Scale ATM API

---

## Installation
```bash
git clone https://github.com/ivan-tarasyuk/zephyr_export.git
cd zephyr_export
pip install -r requirements.txt
```
**Required packages:** `aiofiles>=24.1.0`, `aiohttp>=3.11.11`, `requests>=2.31.0`, `python-dotenv>=1.2.2`

---

## Configuration
Create `.env` file in the project root and add the following variables:
- `JIRA_BASE_URL` - example: `https://jira.online.com/rest/atm/1.0`
- `JIRA_TOKEN` - Bearer token for Zephyr Scale ATM API
- `JIRA_PROJECT_KEY` - example: `ABCD`
- `JIRA_CASE_OWNER` - Jira user key that will be used as the test case owner (example: `JIRAUSER00000`)
- `JIRA_CYCLE_ID` - required for exporting test results (example: `ABCD-C12`)
- `STORY_DIR` - directory storing `.story` files
- `ALLURE_BASE_DIR` - Allure directory storing JSON files with test execution results

If needed, modify default variables in `settings.py` (per script) and shared values in `shared/constants.py`.

---

## Recommended execution order
1. Insert test case IDs into `.story` files using `insert_ids.py`.

2. Execute automated tests to generate Allure report with JSON files referencing the test case IDs from step #1.
   
3. If the test report is ready for export, create draft Zephyr test cases using `create_cases.py`.

4. Export results and update Zephyr test cases using `export_results.py`.

---

## Script 1 - Insert test case IDs into story files
Script: [insert_ids.py](insert_ids.py)

### Purpose
Inserts unique Zephyr test case IDs into Vividus `.story` scenarios, so automation scenarios and Zephyr test cases stay linked and traceable.

### What it does
- Recursively walks the target directory and selects `.story` files matching provided filename patterns (see "Filtering" below).
- For each scenario:
  - Skips scenarios whose titles start with ignored prefixes (see "Filtering" below)
  - Parses scenario metadata lines starting with `META_MARK` (default: `@`)
  - Applies filters based on scenario meta (see "Filtering" below)
  - Ensures each scenario has a valid `META_MARK + ID ...` entry (default: `@testCaseId ...`)
  - Supports "multi-test export" scenarios having `META_MARK + MULTITEST` (default: `@multiTestExport`) by filling/adding `ID_HEADER` (default: `caseId`) column values in the Examples table

### Filtering
- Filename-based skip:
  - If filename does not match `PATTERNS` (default: `/insert_ids/input/patterns.txt`) → scenario skipped
  - Each pattern in `PATTERNS` must be written on a new line
  - If `PATTERNS` is empty, all scenario are processed
- Title-based skip: ignores titles starting with values in `IGNORED_TITLES` (e.g., `[Precondition]`, `[Postcondition]`)
- Meta-based skip:
  - If meta contains `META_MARK + SKIP` (default: `@skip`) → scenario skipped
  - If meta does not match `GROOVY_FILTERS` → scenario skipped

### ID generation behavior
- Reads the last existing test case key from Jira (`/testcase/search`) and computes the next numeric suffix
- Generates sequential IDs like `PROJECTID-T1234`, and writes them into `.story` files
- Limits the number of IDs added per run

### Usage
```bash
python insert_ids.py [QTY] [PATTERNS]
```
`QTY` - number of ids to insert (optional, default: `1`)<br>
`PATTERNS` - path to file containing `.story` filename patterns (optional, default: `input/patterns.txt`)

### Output
- Updates `.story` files in place
- Prints the next available test case ID, how many IDs were inserted, and the ID range
- Prints notes for skipped scenarios and errors for processing failures

---

## Script 2 - Create draft test cases in Zephyr
Script: [create_cases.py](create_cases.py)

### Purpose
Creates draft Zephyr test cases that can later be populated/updated by the export script. This avoids manual test case creation before syncing automation content.

### What it does
- Sends `POST /testcase` to Zephyr Scale (ATM API)
- Creates test cases with a temporary placeholder name and assigns an owner

### Usage
```bash
python create_cases.py [QTY]
```
`QTY` - number of test cases to create (optional, default: `1`)

### Output
- Prints how many test cases were created and the ID range
- Prints errors for processing failures

---

## Script 3 - Parse test execution results and update Zephyr test cases
Script: [export_results.py](export_results.py)

### Purpose
Parses JSON test execution results (Allure `allure-results/*.json`) and:
- Updates the corresponding Zephyr test case content (name, folder, requirement links, BDD script)
- Optionally exports pass/fail execution status into a Zephyr test cycle

### Input directory layout (required)
The script expects an **Allure base directory** that contains subdirectories named:
- `<DIR_PREFIX>_<env>_<region>`

For each such directory, it reads JSON files from:
- `<DIR_PREFIX>_<env>_<region>/allure-results/*.json`

### How a JSON is mapped to a Zephyr test case
For each JSON file:
- Extracts `ID` (default: `testCaseId`) from JSON labels (`labels[].name == "testCaseId"`)
- Uses labels to detect:
  - multi-test export `META_MARK + MULTITEST` (default: `@multiTestExport`)
  - Zephyr folder `META_MARK + FOLDER ...` (default: `@folder ...`)
- Extracts requirement links from JSON `links` where `type == "requirement"`
- Builds BDD steps text from `steps[]`:
  - ignores skipped steps
  - ignores step lines starting with `META_MARK` (default: `@`)
  - normalizes/cleans up special characters
  - prefixes non-BDD lines to fit a pipe-separated BDD format

### What it sends to Zephyr
- `PUT /testcase/{test_case_id}` - updates the test case with:
  - name (prefixed with `[region]`)
  - folder
  - status (e.g., `Approved`)
  - owner
  - issue links (requirements)
  - BDD script text
- `POST /testrun/{JIRA_CYCLE_ID}/testcase/{test_case_id}/testresult` - sends execution status (optional)

### Concurrency
Uses `asyncio.Semaphore` to control concurrency per processed output directory:
- Limits HTTP requests to `MAX_REQUEST_TASKS` (default: `10`)
- Limits file I/O tasks to `MAX_IO_FILE_TASKS` (default: `10`)

### Usage
```bash
python export_results.py [-s]
```
`-s`, `--send_status` - send execution status (disabled by default)

### Output
- Prints how many test execution results were exported
- Prints notes for skipped files and errors for processing failures

---