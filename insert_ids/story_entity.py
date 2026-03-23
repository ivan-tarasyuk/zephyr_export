from typing import Iterable, List, Set, Generator, Tuple, Dict

import insert_ids.settings as st
import shared.constants as const
from shared.exceptions import Skipped, InvalidData
from shared.helpers import remove_prefix


class StoryEntity:
    def __init__(self, story_data: str, id_prefix: str):
        self._lines = iter(story_data.split('\n'))
        self._id_prefix = id_prefix
        self._meta = {}
        self._steps = []

    def _parse_meta(self, matches_filter_by_default: bool) -> None:
        while (line := next(self._lines, '')).strip().startswith(const.META_MARK):
            line = line.strip().translate(str.maketrans(r',;', 2 * ' '))
            attr, *values = line.split()
            self._meta[remove_prefix(attr, const.META_MARK)] = list(map(str.strip, values))
        self._skip_by_meta(matches_filter_by_default)
        self._steps.append(line)

    def _skip_by_meta(self, matches_filter_by_default: bool) -> None:
        if st.SKIP in self._meta:
            self._skip()
        for attr, values in st.GROOVY_FILTERS.items():
            if all([value not in self._meta.get(attr, value if matches_filter_by_default else []) for value in values]):
                self._skip()

    def _skip(self):
        raise Skipped


class StoryMeta(StoryEntity):
    def __init__(self, story_meta: str, id_prefix: str):
        super().__init__(story_meta.strip().partition(st.META + '\n')[2], id_prefix)

    def process_object(self) -> None:
        self._parse_meta(matches_filter_by_default=False)


class Scenario(StoryEntity):
    def __init__(self, scenario: str, id_prefix: str):
        super().__init__(scenario, id_prefix)
        self.title = self._skip_by_title(next(self._lines, '').strip())
        self._multitest = False
        self._ids = set()
        self._examples_ids = set()
        self._transformers = []
        self._sep = '|'
        self._headers = []
        self._widths = {}
        self._examples = []
        self._examples_to_fill = []

    def _skip_by_title(self, title: str) -> str:
        if any(title.lower().startswith(word.lower()) for word in const.IGNORED_TITLES):
            self._skip()
        return title

    def _sort_ids(self, ids: Iterable[str]) -> List[str]:
        return sorted(ids, key=lambda x: int(remove_prefix(x, self._id_prefix)))

    def _is_valid_id(self, _id: str) -> bool:
        return _id.startswith(self._id_prefix) and remove_prefix(_id, self._id_prefix).isdigit()

    def _validate_id(self, _id: str, valid_ids: Set[str], *, placeholder: bool = False) -> bool:
        if self._is_valid_id(_id):
            valid_ids.add(_id)
            return True
        if placeholder and _id == st.PLACEHOLDER:
            return False
        raise InvalidData(f'[ERROR] Invalid test case ID is specified: {_id}')

    def process_object(self, id_generator: Generator[str, None, None], id_left: int) -> Tuple[bool, int]:
        self._parse_scenario()
        to_generate = max(0, 1 - len(self._ids), self._multitest * (len(self._examples) - len(self._ids)))
        if to_generate > id_left:
            return False, id_left

        self._ids.update(next(id_generator) for _ in range(to_generate))
        if self._multitest:
            if const.ID_HEADER in self._headers:
                self._headers.remove(const.ID_HEADER)
            self._headers.insert(0, const.ID_HEADER)
            for i, _id in zip(self._examples_to_fill, self._sort_ids(self._ids - self._examples_ids)):
                self._examples[i][const.ID_HEADER] = _id
                self._update_width(const.ID_HEADER, _id)
        id_left -= to_generate
        return bool(id_left), id_left

    def _parse_scenario(self) -> None:
        if (line := next(self._lines, '')).strip() == st.META:
            self._parse_meta(matches_filter_by_default=True)
            for _id in self._meta.get(const.ID, []):
                self._validate_id(_id, self._ids)
            self._meta.pop(const.ID, None)
        else:
            self._steps.append(line)

        self._multitest = const.MULTITEST in self._meta
        if not self._multitest:
            self._steps.extend(self._lines)
        elif self._parse_steps():
            if self._parse_examples():
                for i, _id in enumerate(row[const.ID_HEADER] for row in self._examples):
                    if not self._validate_id(_id, self._examples_ids, placeholder=True):
                        self._examples_to_fill.append(i)
                self._ids.update(self._examples_ids)
            else:
                self._examples_to_fill.extend(range(len(self._examples)))

    def _parse_steps(self) -> bool:
        while line := next(self._lines, ''):
            if line.strip() == st.EXAMPLES:
                return True
            self._steps.append(line)
        return False

    def _parse_examples(self) -> bool:
        def examples_source(line: str, has_id: bool) -> Iterable:
            source = line.strip(self._sep)
            return map(str.strip, source.split(self._sep)) if has_id else [source]

        while (line := next(self._lines, '')) and not line.startswith(self._sep):
            self._transformers.append(line)
            if self._sep == '|' and -1 < (pos := line.find(st.SEP)) < (len(line) - len(st.SEP)):
                self._sep = line[pos + len(st.SEP)]

        has_id = const.ID_HEADER in line
        for param in examples_source(line, has_id):
            self._headers.append(param)
            self._update_width(param, param)

        while line := next(self._lines, ''):
            row = {}
            for param, value in zip(self._headers, examples_source(line, has_id)):
                row[param] = value
                self._update_width(param, value)
            self._examples.append(row)
        return has_id

    def _update_width(self, param: str, new_value: str) -> None:
        self._widths[param] = max(self._widths.get(param, len(param)), len(new_value))

    def format_scenario(self) -> str:
        lines = [self.title]
        if self._meta or self._ids:
            lines += ([st.META] +
                      ([self._format_meta(const.ID, self._sort_ids(self._ids))] if self._ids else []) +
                      [self._format_meta(attr, values) for attr, values in self._meta.items()])
        lines += self._steps
        if self._multitest:
            lines += ([st.EXAMPLES] +
                      self._transformers +
                      [self._format_row(dict(zip(self._headers, self._headers)))] +
                      [self._format_row(row) for row in self._examples])
        return '\n'.join(lines)

    @staticmethod
    def _format_meta(attr: str, values: List[str]) -> str:
        sep = '; ' if attr in (const.ID, st.REQ_ID) else ' '
        return f'{4 * " "}{const.META_MARK + attr} {sep.join(values)}'

    def _format_row(self, row: Dict[str, str]) -> str:
        parts = [row[param].ljust(self._widths[param]) for param in self._headers]
        return f'{self._sep}{self._sep.join(parts)}{self._sep}'
