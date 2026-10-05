# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

"""DOM parser oluşturmadan JS, URL ve düz metin üzerinde sorgu yap."""

import re


YEAR_PATTERN = r"(?<!\&#)\b(19\d{2}|20\d{2})\b"
_YEAR_RE     = re.compile(YEAR_PATTERN)


def extract_year_text(value: object, pattern: str = YEAR_PATTERN) -> int | None:
    if value is None or not str(value).strip():
        return None
    match = _YEAR_RE.search(str(value)) if pattern == YEAR_PATTERN else re.search(pattern, str(value))
    year  = match.group(1) if match else None
    return int(year) if year and year.isdigit() else None


class TextHelper:
    __slots__ = ("html",)

    def __init__(self, text: str | None):
        self.html = text or ""

    def _regex_source(self, target: str | int | None) -> str:
        return target if isinstance(target, str) else self.html

    def regex_first(self, pattern: str, target: str | int | None = None, group: int | None = 1, flags: int = 0) -> str | tuple | None:
        match = re.search(pattern, self._regex_source(target), flags=flags)
        if not match:
            return None
        if group is None:
            return match.groups()
        last_idx = match.lastindex or 0
        return match.group(group) if last_idx >= group else match.group(0)

    def regex_all(self, pattern: str, target: str | int | None = None, flags: int = 0) -> list[str] | list[tuple]:
        return re.findall(pattern, self._regex_source(target), flags=flags)

    def regex_replace(self, pattern: str, repl: str, target: str | int | None = None, flags: int = 0) -> str:
        return re.sub(pattern, repl, self._regex_source(target), flags=flags)
