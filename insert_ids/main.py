import argparse
from pathlib import Path

from insert_ids.inserter import IDInserter
import insert_ids.settings as st
from insert_ids.utils import read_file, validate_filter
from shared.exceptions import InvalidData


def main() -> None:
    parser = argparse.ArgumentParser(description='Inserts test case IDs into story-files')
    parser.add_argument('qty', type=int, nargs='?', default=1,
                        help='number of ids to insert (default: 1)')
    parser.add_argument('patterns', type=Path, nargs='?', default=st.PATTERNS,
                        help=f'path to file containing story filename patterns (default: {st.PATTERNS})')
    args = parser.parse_args()
    inserted_count, inserted_ids = 0, ''
    try:
        if args.qty < 1:
            raise InvalidData('[ERROR] Number of test case IDs must be greater than 0')
        if not args.patterns.is_file():
            raise InvalidData(f'[ERROR] File containing story filename patterns not found at {args.patterns}')
        validate_filter()
        patterns = read_file(args.patterns).strip()
        patterns = patterns.split('\n') if patterns else []
        id_inserter = IDInserter(args.qty, patterns)
        inserted_count, inserted_ids = id_inserter.run()
    except Exception as e:
        print(e)
    print(f'[DONE ] Script has been completed')
    if inserted_count:
        print(f'[DONE ] Inserted {inserted_count} of {args.qty} test case ID(s): {inserted_ids}')
    else:
        print('[DONE ] No test case IDs have been inserted')
