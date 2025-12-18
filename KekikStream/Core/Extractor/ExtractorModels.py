# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from pydantic import BaseModel

class Subtitle(BaseModel):
    """Altyazı modeli."""
    name : str
    url  : str


class ExtractResult(BaseModel):
    """Extractor'ın döndürmesi gereken sonuç modeli."""
    name       : str
    url        : str
    referer    : str | None     = None
    user_agent : str | None     = None
    subtitles  : list[Subtitle] = []
