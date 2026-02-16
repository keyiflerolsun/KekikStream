# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from __future__ import annotations
from pydantic   import BaseModel, field_validator, model_validator
from ..Helpers  import clean_title, normalize_empty, normalize_rating


# ========================
# VERİ MODELLERİ
# ========================

class MainPageResult(BaseModel):
    """Ana sayfa sonucunda dönecek veri modeli."""
    category : str
    title    : str
    url      : str
    poster   : str | None = None

    @model_validator(mode="after")
    def auto_normalize(self) -> MainPageResult:
        self.title  = clean_title(self.title) or self.title
        return self

class SearchResult(BaseModel):
    """Arama sonucunda dönecek veri modeli."""
    title  : str
    url    : str
    poster : str | None = None

    @model_validator(mode="after")
    def auto_normalize(self) -> SearchResult:
        self.title  = clean_title(self.title) or self.title
        return self

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

    @model_validator(mode="after")
    def auto_normalize(self) -> MovieInfo:
        self.title = clean_title(self.title)

        for field in ("actors", "tags", "description", "year"):
            setattr(self, field, normalize_empty(getattr(self, field)))
        self.rating = normalize_rating(self.rating)
        if self.duration is not None and self.duration == 0:
            self.duration = None
        return self


class Episode(BaseModel):
    season  : int | None = None
    episode : int | None = None
    title   : str | None = None
    url     : str | None = None

    @model_validator(mode="after")
    def auto_normalize(self) -> Episode:
        if not self.title:
            self.title = ""
        else:
            self.title = " ".join(self.title.split()).strip()

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

    @model_validator(mode="after")
    def auto_normalize(self) -> SeriesInfo:
        self.title  = clean_title(self.title)

        for field in ("actors", "tags", "description", "year"):
            setattr(self, field, normalize_empty(getattr(self, field)))
        self.rating = normalize_rating(self.rating)
        if self.duration is not None and self.duration == 0:
            self.duration = None
        return self
