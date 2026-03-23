def remove_prefix(line: str, prefix: str) -> str:
    return line[len(prefix):] if line.startswith(prefix) else line


def remove_suffix(line: str, suffix: str) -> str:
    return line[:-len(suffix)] if line.endswith(suffix) else line
