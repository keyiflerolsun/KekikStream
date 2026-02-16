# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

"""Başlık temizleyici — izle / türkçe vb. suffix'leri kaldırır."""

from __future__ import annotations
import re

_TITLE_SUFFIXES = [
    " izle",
    " full film",
    " filmini full",
    " full türkçe",
    " alt yazılı",
    " altyazılı",
    " tr dublaj",
    " hd türkçe",
    " türkçe dublaj",
    " yeşilçam ",
    " erotik fil",
    " türkçe",
    " yerli",
    " tüekçe dublaj",
]


def clean_title(title: str | None) -> str | None:
    """Başlıktan izle / türkçe vb. suffix'leri temizler."""
    if not title or not isinstance(title, str):
        return title

    cleaned = title.strip()
    if not cleaned:
        return None

    # "Film(2024)" → "Film (2024)"
    cleaned = re.sub(r"(\S)\(", r"\1 (", cleaned)

    for suffix in _TITLE_SUFFIXES:
        cleaned = re.sub(f"{re.escape(suffix)}.*$", "", cleaned, flags=re.IGNORECASE).strip()

    return cleaned or None
