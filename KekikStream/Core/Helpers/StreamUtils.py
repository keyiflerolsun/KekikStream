# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from urllib.parse import urlparse

# Doğrudan oynatılabilir medya uzantıları (embed/player HTML sayfası DEĞİL).
_MEDIA_EXT = (".m3u8", ".mp4", ".ts", ".mkv", ".m4s", ".webm", ".mpd", ".m4v", ".mov")


def is_direct_stream(url: str) -> bool:
    """URL doğrudan bir medya akışı mı? (embed/iframe/player HTML sayfası ise False.)

    Extractor bir embed'i ÇÖZEMEDİĞİNDE plugin'ler ham URL'i fallback döndürüyordu;
    bu URL bir HTML player sayfasıysa (voe.sx/e/…, uqload.io/embed-…, *.html) oynatıcıda
    oynamıyor ve sonucu kirletiyor. Fallback SADECE bu True dönerse eklenmeli.
    """
    if not url or not url.startswith("http"):
        return False
    path = urlparse(url).path.lower()
    return path.endswith(_MEDIA_EXT)
