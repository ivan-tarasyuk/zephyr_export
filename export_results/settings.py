TITLE_SUFFIX = 'useCase'
PASSED = 'passed'
FOLDER = 'folder'
DIR_PREFIX = 'output1_'

BDD_WORDS = [
    'Given',
    'When',
    'Then',
    '|'
]

INVALID_CHARS = r'\/:*?"<>|'
TRANSLATION = str.maketrans(INVALID_CHARS, '_' * len(INVALID_CHARS))

MAX_REQUEST_TASKS = 10
MAX_IO_FILE_TASKS = 10
