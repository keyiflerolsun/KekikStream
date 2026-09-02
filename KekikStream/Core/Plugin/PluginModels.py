# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from ..Helpers import clean_title, strip_title_episode_marker, clean_episode_title, EPISODE_DISPLAY_PREFIX, GENERIC_EPISODE_TITLE, normalize_description, normalize_empty, normalize_rating, normalize_year
from pydantic  import BaseModel, field_validator, model_validator


class MainPageResult(BaseModel):
    """Ana sayfa sonucunda dönecek veri modeli."""
    category : str
    title    : str
    url      : str
    poster   : str | None = None

    @model_validator(mode="after")
    def normalize_title(self):
        self.title = clean_title(self.title) or self.title
        return self


class SearchResult(BaseModel):
    """Arama sonucunda dönecek veri modeli."""

    title  : str
    url    : str
    poster : str | None = None

    @model_validator(mode="after")
    def normalize_title(self):
        self.title = clean_title(self.title) or self.title
        return self


class _MetadataInfo(BaseModel):
    """Film ve dizi modellerinin ortak, gerçek-değer normalizasyonu."""

    poster      : str | None = None
    title       : str | None = None
    description : str | None = None
    tags        : str | None = None
    rating      : str | None = None
    year        : str | None = None
    actors      : str | None = None
    duration    : int | None = None
    imdb_id     : str | None = None
    tmdb_id     : str | None = None

    @field_validator("tags", "actors", mode="before")
    @classmethod
    def join_values(cls, value):
        if isinstance(value, list):
            return ", ".join(str(item) for item in value if item) or None
        return value

    @field_validator("rating", "year", mode="before")
    @classmethod
    def stringify(cls, value):
        return str(value) if value is not None else None

    @model_validator(mode="after")
    def normalize_metadata(self):
        self.title = strip_title_episode_marker(clean_title(self.title))
        for field in ("actors", "tags"):
            setattr(self, field, normalize_empty(getattr(self, field)))
        self.description = normalize_description(self.description, self.title)
        self.year        = normalize_year(self.year)
        self.rating      = normalize_rating(self.rating)
        if self.duration == 0:
            self.duration = None
        return self


class MovieInfo(_MetadataInfo):
    """Bir medya öğesinin bilgilerini tutan model."""

    url: str


class Episode(BaseModel):
    season  : int | None = None
    episode : int | None = None
    title   : str | None = None
    url     : str | None = None

    @model_validator(mode="after")
    def normalize_fields(self):
        if not self.season:
            self.season = 1

        self.title = normalize_empty(self.title)
        if self.title:
            self.title = " ".join(self.title.split())
            if match := EPISODE_DISPLAY_PREFIX.fullmatch(self.title):
                self.title = match.group("title").strip() or None
            if self.title and GENERIC_EPISODE_TITLE.fullmatch(self.title):
                self.title = None

        return self


class SeriesInfo(_MetadataInfo):
    url      : str | None           = None
    episodes : list[Episode] | None = None

    @model_validator(mode="after")
    def normalize_episodes(self):
        if not self.episodes:
            return self
        for episode in self.episodes:
            episode.title = clean_episode_title(self.title, episode.title)
        self.episodes.sort(key=lambda ep: (ep.season or 0, ep.episode or 0))
        return self
