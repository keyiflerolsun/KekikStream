# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from pydantic import BaseModel
from typing   import List, Optional


class Subtitle(BaseModel):
    """Altyazı modeli."""
    name : str
    url  : str


class ExtractResult(BaseModel):
    """Extractor'ın döndürmesi gereken sonuç modeli."""
    name      : str
    url       : str
    referer   : str
    headers   : Optional[dict] = {}
    subtitles : List[Subtitle] = []