# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from pydantic import BaseModel, field_validator, model_validator

class MainPageResult(BaseModel):
    """Ana sayfa sonucunda dönecek veri modeli."""
    category : str
    title    : str
    url      : str
    poster   : str | None = None


class SearchResult(BaseModel):
    """Arama sonucunda dönecek veri modeli."""
    title  : str
    url    : str
    poster : str | None = None


class MovieInfo(BaseModel):
    """Bir medya öğesinin bilgilerini tutan model."""
    url         : str
    poster      : str | None = None
    title       : str | None = None
    description : str | None = None
    tags        : str | None = None
    rating      : str | None = None
    year        : str | None = None
    actors      : str | None = None
    duration    : int | None = None

    @field_validator("tags", "actors", mode="before")
    @classmethod
    def convert_lists(cls, value):
        return ", ".join(value) if isinstance(value, list) else value

    @field_validator("rating", "year", mode="before")
    @classmethod
    def ensure_string(cls, value):
        return str(value) if value is not None else value


class Episode(BaseModel):
    season  : int | None = None
    episode : int | None = None
    title   : str | None = None
    url     : str | None = None

    @model_validator(mode="after")
    def check_title(self) -> "Episode":
        if not self.title:
            self.title = ""

        return self

class SeriesInfo(BaseModel):
    url          : str | None           = None
    poster       : str | None           = None
    title        : str | None           = None
    description  : str | None           = None
    tags         : str | None           = None
    rating       : str | None           = None
    year         : str | None           = None
    actors       : str | None           = None
    duration     : int | None           = None
    episodes     : list[Episode] | None = None

    @field_validator("tags", "actors", mode="before")
    @classmethod
    def convert_lists(cls, value):
        return ", ".join(value) if isinstance(value, list) else value

    @field_validator("rating", "year", mode="before")
    @classmethod
    def ensure_string(cls, value):
        return str(value) if value is not None else value
