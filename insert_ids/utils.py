from pathlib import Path

import insert_ids.settings as st
from shared.exceptions import IOException, FileNotFound


def read_file(file_path: Path) -> str:
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        raise FileNotFound(f'[ERROR] File not found at {file_path}')
    except Exception as e:
        raise IOException(f'[ERROR] An error occurred while reading file {file_path}. {e}')


def write_file(file_path: Path, text: str) -> None:
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(text)
            return None
    except Exception as e:
        raise IOException(f'[ERROR] An error occurred while writing to {file_path}. {e}')


def validate_filter() -> None:
    for key, value in st.GROOVY_FILTERS.items():
        st.GROOVY_FILTERS[key] = set(value if isinstance(value, list) else [value])
        if '' in st.GROOVY_FILTERS[key]:
            st.GROOVY_FILTERS[key].remove('')
        if not st.GROOVY_FILTERS[key]:
            raise FileNotFound(f'[ERROR] Filter {key.upper()} has not been defined')
