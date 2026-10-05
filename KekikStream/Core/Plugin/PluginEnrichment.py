# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from ...CLI                      import konsol
from ..Helpers                   import extract_imdb_id_text, extract_tmdb_id_text, MetadataHelper, SubtitleHelper, HTMLHelper, PlayabilityHelper
from .PluginModels               import MovieInfo, SeriesInfo
from ..Extractor.ExtractorModels import ExtractResult
import asyncio, httpx


class PluginEnrichmentMixin:
    def _wrap_plugin_methods(self):
        """Plugin subclass metotlarını otomatik olarak zenginleştirici sarmallarla sarar."""
        # 1. load_item sarmalı
        original_load_item = getattr(self, "load_item", None)
        if original_load_item and not getattr(original_load_item, "__wb_wrapped__", False):
            async def wrapped_load_item(url: str) -> MovieInfo | SeriesInfo:
                item = await original_load_item(url)
                if item:
                    item                   = await self.enrich_metadata(item)
                    self._last_loaded_item = item
                return item

            wrapped_load_item.__wb_wrapped__ = True
            wrapped_load_item.__doc__        = getattr(original_load_item, "__doc__", None)
            self.load_item                   = wrapped_load_item

        # 2. load_links sarmalı
        original_load_links = getattr(self, "load_links", None)
        if original_load_links and not getattr(original_load_links, "__wb_wrapped__", False):
            async def wrapped_load_links(url: str) -> list[ExtractResult]:
                main_item_url = url
                for marker in ("/sezon-", "/season-"):
                    if marker in main_item_url:
                        main_item_url = main_item_url.split(marker, 1)[0]
                        if not main_item_url.endswith("/"):
                            main_item_url += "/"
                        break

                cached_item = getattr(self, "_last_loaded_item", None)
                cached_url  = (getattr(cached_item, "url", None) or "").rstrip("/")
                target_url  = main_item_url.rstrip("/")

                if not cached_item or cached_url != target_url:
                    async def _safe_load_item():
                        try:
                            return await self.load_item(main_item_url)
                        except Exception:
                            return None

                    item, results = await asyncio.gather(_safe_load_item(), original_load_links(url))
                else:
                    item    = cached_item
                    results = await original_load_links(url)

                imdb_id = item.imdb_id if item else None
                tmdb_id = item.tmdb_id if item else None

                if results:
                    playability_tasks   = [PlayabilityHelper.is_url_playable(r) for r in results]
                    playability_results = await asyncio.gather(*playability_tasks)

                    results = [item for item, (is_playable, _) in zip(results, playability_results) if is_playable]
                results = await self.finalize_subtitles(results, url=url, imdb_id=imdb_id, tmdb_id=tmdb_id)
                results = self.deduplicate(results)
                if self.result_processor is not None:
                    results = self.result_processor(results)
                results = self.sync_subtitles(results)
                return results

            wrapped_load_links.__wb_wrapped__ = True
            wrapped_load_links.__doc__        = getattr(original_load_links, "__doc__", None)
            self.load_links                   = wrapped_load_links

    async def enrich_metadata(self, info: MovieInfo | SeriesInfo) -> MovieInfo | SeriesInfo:
        """Eksik metadataları TMDB üzerinden tamamlar."""
        lang_map  = {
            "tr" : "tr-TR", "en": "en-US", "fr": "fr-FR", "de": "de-DE", "it": "it-IT",
            "es" : "es-ES", "ru": "ru-RU", "uk": "uk-UA", "zh": "zh-CN", "ja": "ja-JP",
            "ko" : "ko-KR", "ar": "ar-SA", "pt": "pt-BR", "pl": "pl-PL", "az": "az-AZ",
            "ta" : "ta-IN", "ms": "ms-MY", "hi": "hi-IN", "id": "id-ID",
        }
        tmdb_lang = lang_map.get((self.language or "en")[:2].lower(), "en-US")
        return await MetadataHelper.enrich_metadata(info, lang=tmdb_lang)

    async def finalize_subtitles(
        self,
        results: list[ExtractResult],
        url: str | None = None,
        imdb_id: str | None = None,
        tmdb_id: str | None = None,
        season: int | None = None,
        episode: int | None = None
    ) -> list[ExtractResult]:
        """Harici altyazıları çekip sonuçlara ekler."""
        if not results:
            return results

        if self.subtitle_processor is not None:
            results = await self.subtitle_processor(results)

        if not results or self.name == "SolarMovies":
            return results

        # URL'den ID ve Bölüm bilgilerini tahmin etmeye çalış (id paslanmamışsa)
        if not imdb_id and not tmdb_id and url:
            imdb_id = extract_imdb_id_text(url)
            tmdb_id = extract_tmdb_id_text(url)
            season, episode = HTMLHelper.extract_season_episode(url)

        # Eğer hala bulunamadıysa ve referer'lar varsa oradan da tahmin etmeyi deneyelim
        if not imdb_id and not tmdb_id:
            for res in results:
                if res.referer:
                    imdb_id = extract_imdb_id_text(res.referer)
                    tmdb_id = extract_tmdb_id_text(res.referer)
                    season, episode = HTMLHelper.extract_season_episode(res.referer)
                    if imdb_id or tmdb_id:
                        break

        if imdb_id or tmdb_id:
            try:
                ext_subs = await SubtitleHelper.fetch_external_subtitles(
                    imdb_id = imdb_id,
                    tmdb_id = tmdb_id,
                    season  = season,
                    episode = episode
                )
                if ext_subs:
                    for res in results:
                        if res.subtitles is None:
                            res.subtitles = []
                        # Tekrar eden altyazıları eklemeyelim
                        existing_urls = {sub.url for sub in res.subtitles}
                        for sub in ext_subs:
                            if sub.url not in existing_urls:
                                res.subtitles.append(sub)
            except (httpx.HTTPError, ValueError) as e:
                konsol.log(f"[yellow][!] Harici Altyazı Arama Hatası ({self.name}): {e}")

        return results
