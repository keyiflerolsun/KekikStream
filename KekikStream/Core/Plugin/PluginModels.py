# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from pydantic import BaseModel, field_validator, model_validator
from typing   import List, Optional

class MainPageResult(BaseModel):
    """Ana sayfa sonucunda dönecek veri modeli."""
    category : str
    title    : str
    url      : str
    poster   : Optional[str] = None


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

    @field_validator("tags", "actors", mode="before")
    @classmethod
    def convert_lists(cls, value):
        return ", ".join(value) if isinstance(value, list) else value

    @field_validator("rating", "year", mode="before")
    @classmethod
    def ensure_string(cls, value):
        return str(value) if value is not None else value


class Episode(BaseModel):
    season  : Optional[int] = None
    episode : Optional[int] = None
    title   : Optional[str] = None
    url     : Optional[str] = None

    @model_validator(mode="after")
    def check_title(self) -> "Episode":
        if not self.title:
            self.title = ""

        if any(keyword in self.title.lower() for keyword in ["bölüm", "sezon", "episode"]):
            self.title = ""

        return self

class SeriesInfo(BaseModel):
    url          : Optional[str]           = None
    poster       : Optional[str]           = None
    title        : Optional[str]           = None
    description  : Optional[str]           = None
    tags         : Optional[str]           = None
    rating       : Optional[str]           = None
    year         : Optional[str]           = None
    actors       : Optional[str]           = None
    episodes     : Optional[List[Episode]] = None

    @field_validator("tags", "actors", mode="before")
    @classmethod
    def convert_lists(cls, value):
        return ", ".join(value) if isinstance(value, list) else value

    @field_validator("rating", "year", mode="before")
    @classmethod
    def ensure_string(cls, value):
        return str(value) if value is not None else value