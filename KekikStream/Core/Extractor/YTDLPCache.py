# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from Kekik.cli        import konsol
from yt_dlp.extractor import gen_extractors

# Global cache (module-level singleton)
_YTDLP_EXTRACTORS_CACHE = None
_CACHE_INITIALIZED      = False

def get_ytdlp_extractors() -> list:
    """
    yt-dlp extractorlarını cache'le ve döndür

    Returns:
        list: yt-dlp extractor sınıfları
    """
    global _YTDLP_EXTRACTORS_CACHE, _CACHE_INITIALIZED

    if _CACHE_INITIALIZED:
        return _YTDLP_EXTRACTORS_CACHE

    try:
        extractors = list(gen_extractors())
        extractors = [ie for ie in extractors if ie.ie_key() != 'Generic']

        _YTDLP_EXTRACTORS_CACHE = extractors
        _CACHE_INITIALIZED      = True

        return extractors

    except Exception as e:
        konsol.log(f"[red][⚠] yt-dlp extractor cache hatası: {e}[/red]")
        _YTDLP_EXTRACTORS_CACHE = []
        _CACHE_INITIALIZED      = True
        return []
