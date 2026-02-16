# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

"""Değer normalizasyonu — boş string → None, geçersiz rating → None."""

from __future__ import annotations
import re


def normalize_empty(value: str | None) -> str | None:
    """Boş string, 'N/A' gibi değerleri None'a çevirir."""
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if not stripped or stripped.lower() in ("n/a", "na"):
        return None
    return value


def normalize_rating(value: str | None) -> str | None:
    """Geçersiz rating değerlerini None'a çevirir."""
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if not stripped:
        return None
    if re.match(r'^[\d.]+$', stripped):
        try:
            if float(stripped) == 0:
                return None
        except ValueError:
            return None
    return value
