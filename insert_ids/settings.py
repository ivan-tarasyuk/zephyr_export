from pathlib import Path


PATTERNS = Path(__file__).resolve().parent / 'input' / 'patterns.txt'

GROOVY_FILTERS = {
    'epic': 'regression',
    'env': 'qa',
    'region': 'APAC',
}

SKIP = 'skip'

TITLE = 'Scenario:'
META = 'Meta:'
REQ_ID = 'requirementId'
EXAMPLES = 'Examples:'
SEP = 'headerSeparator='
PLACEHOLDER = 'X'
