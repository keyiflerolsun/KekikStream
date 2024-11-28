# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from pydantic import BaseModel, validator
from typing   import Optional


class SearchResult(BaseModel):
    """Arama sonucunda dönecek veri modeli."""
    title  : str
    url    : str
    poster : Optional[str] = None


class MovieInfo(BaseModel):
    """Bir medya öğesinin bilgilerini tutan model."""
    url         : str
    poster      : Optional[str] = None
    title       : Optional[str] = None
    description : Optional[str] = None
    tags        : Optional[str] = None
    rating      : Optional[str] = None
    year        : Optional[str] = None
    actors      : Optional[str] = None
    duration    : Optional[int] = None

    @validator("tags", pre=True)
    def convert_tags(cls, value):
        return ", ".join(value) if isinstance(value, list) else value

    @validator("actors", pre=True)
    def convert_actors(cls, value):
        return ", ".join(value) if isinstance(value, list) else value