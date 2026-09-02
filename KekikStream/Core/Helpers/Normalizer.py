# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

"""Model ve eklentilerin paylaştığı değer/URL normalizasyonu."""

from datetime     import date
from urllib.parse import urljoin
import re


_EMPTY_VALUES  = {"", "n/a", "na", "none", "null"}
_YEAR          = re.compile(r"(?:18|19|20)\d{2}")
_URL_ONLY_TEXT = re.compile(r"(?:https?://\S+\s*)+(?:\([^)]*\))?$")


def normalize_empty(value: str | None) -> str | None:
    """Boş ve kaynakların yaygın null yer tutucularını ``None``a çevir."""
    if not isinstance(value, str):
        return value
    value = value.strip()
    return None if value.casefold() in _EMPTY_VALUES else value


def normalize_rating(value: str | None) -> str | None:
    """Gerçek, sıfırdan büyük sayısal puanı döndür; diğerini ``None`` yap."""
    value = normalize_empty(value)
    if not value:
        return None
    value = value.replace(",", ".")
    try:
        return value if float(value) > 0 else None
    except ValueError:
        return None


def normalize_year(value: str | int | None) -> str | None:
    """Gerçekçi olmayan veya belirsiz yıl değerlerini ``None`` yap."""
    value = normalize_empty(str(value) if value is not None else None)
    if not value or not _YEAR.fullmatch(value):
        return None
    year = int(value)
    return value if 1888 <= year <= date.today().year + 10 else None


def normalize_description(value: str | None, title: str | None = None) -> str | None:
    """Boş, başlığın tekrarı veya salt tanıtım bağlantısı olan açıklamayı at."""
    value = normalize_empty(value)
    if not value or _URL_ONLY_TEXT.fullmatch(value):
        return None
    return None if title and value.casefold() == title.casefold() else value


def normalize_url(url: str | None, main_url: str = "") -> str | None:
    """Boş URL'yi koru; göreli/protokol-göreli URL'yi kanonik hale getir."""
    url = normalize_empty(url)
    if not url:
        return None
    if url.startswith(("#", "javascript:", "void(")):
        return None
    if url.startswith(("http://", "https://", '{"')):
        return url.replace("\\", "")
    if url.startswith("//"):
        return f"https:{url}".replace("\\", "")
    return urljoin(main_url, url).replace("\\", "")


def fix_url(url: str | None, main_url: str = "") -> str:
    """Eski eklentiler için ``normalize_url``un boş-string uyumlu sarmalayıcısı."""
    return normalize_url(url, main_url) or ""
