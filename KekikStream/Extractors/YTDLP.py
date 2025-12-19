# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, Subtitle, get_ytdlp_extractors
from urllib.parse     import urlparse
import yt_dlp, re, sys, os

class YTDLP(ExtractorBase):
    name     = "yt-dlp"
    main_url = ""  # Universal - tüm siteleri destekler

    _FAST_DOMAIN_RE = None  # compiled mega-regex (host üstünden)

    @classmethod
    def _init_fast_domain_regex(cls):
        """
        Fast domain regex'i initialize et
        """
        if cls._FAST_DOMAIN_RE is not None:
            return

        domains = set()

        # Merkezi cache'den extractorları al
        extractors = get_ytdlp_extractors()

        # yt-dlp extractor'larının _VALID_URL regex'lerinden domain yakala
        # Regex metinlerinde domainler genelde "\." şeklinde geçer.
        domain_pat = re.compile(r"(?:[a-z0-9-]+\\\.)+[a-z]{2,}", re.IGNORECASE)

        for ie in extractors:
            valid = getattr(ie, "_VALID_URL", None)
            if not valid or not isinstance(valid, str):
                continue

            for m in domain_pat.findall(valid):
                d = m.replace(r"\.", ".").lower()

                # Çok agresif/şüpheli şeyleri elemek istersen burada filtre koyabilirsin
                # (genelde gerek kalmıyor)
                domains.add(d)

        # Hiç domain çıkmazsa (çok uç durum) fallback: boş regex
        if not domains:
            cls._FAST_DOMAIN_RE = re.compile(r"$^")  # hiçbir şeye match etmez
            return

        # Host eşleştirmesi: subdomain destekli (m.youtube.com, player.vimeo.com vs.)
        # (?:^|.*\.) (domain1|domain2|...) $
        joined = "|".join(sorted(re.escape(d) for d in domains))
        pattern = rf"(?:^|.*\.)(?:{joined})$"
        cls._FAST_DOMAIN_RE = re.compile(pattern, re.IGNORECASE)

    def __init__(self):
        self.__class__._init_fast_domain_regex()

    def can_handle_url(self, url: str) -> bool:
        """
        Fast-path: URL host'unu tek mega-regex ile kontrol et (loop yok)
        Slow-path: gerekirse mevcut extract_info tabanlı kontrolün
        """
        # URL parse + host al
        try:
            parsed = urlparse(url)
            host = (parsed.hostname or "").lower()
        except Exception:
            host = ""

        # Şemasız URL desteği: "youtube.com/..." gibi
        if not host and "://" not in url:
            try:
                parsed = urlparse("https://" + url)
                host = (parsed.hostname or "").lower()
            except Exception:
                host = ""

        # Fast-path
        if host and self.__class__._FAST_DOMAIN_RE.search(host):
            return True

        # SLOW PATH: Diğer siteler için yt-dlp'nin native kontrolü
        try:
            # stderr'ı geçici olarak kapat (hata mesajlarını gizle)
            old_stderr = sys.stderr
            sys.stderr = open(os.devnull, "w")

            try:
                ydl_opts = {
                    "simulate"              : True,  # Download yok, sadece tespit
                    "quiet"                 : True,  # Log kirliliği yok
                    "no_warnings"           : True,  # Uyarı mesajları yok
                    "extract_flat"          : True,  # Minimal işlem
                    "no_check_certificates" : True,
                    "ignoreerrors"          : True,  # Hataları yoksay
                    "socket_timeout"        : 3,
                    "retries"               : 1
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    # URL'yi işleyebiliyor mu kontrol et
                    info = ydl.extract_info(url, download=False, process=False)

                    # Generic extractor ise atla
                    if info and info.get("extractor_key") != "Generic":
                        return True

                    return False
            finally:
                # stderr'ı geri yükle
                sys.stderr.close()
                sys.stderr = old_stderr

        except Exception:
            # yt-dlp işleyemezse False döndür
            return False

    async def extract(self, url: str, referer: str | None = None) -> ExtractResult:
        ydl_opts = {
            "quiet"                 : True,
            "no_warnings"           : True,
            "extract_flat"          : False,   # Tam bilgi al
            "format"                : "best",  # En iyi kalite
            "no_check_certificates" : True,
            "socket_timeout"        : 3,
            "retries"               : 1
        }

        # Referer varsa header olarak ekle
        if referer:
            ydl_opts["http_headers"] = {"Referer": referer}

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            if not info:
                raise ValueError("yt-dlp video bilgisi döndürmedi")

            # Video URL'sini al
            video_url = info.get("url")
            if not video_url:
                # Bazen formatlar listesinde olabilir
                formats = info.get("formats", [])
                if formats:
                    video_url = formats[-1].get("url")  # Son format (genellikle en iyi)

            if not video_url:
                raise ValueError("Video URL bulunamadı")

            # Altyazıları çıkar
            subtitles = []
            if subtitle_data := info.get("subtitles"):
                for lang, subs in subtitle_data.items():
                    for sub in subs:
                        if sub_url := sub.get("url"):
                            subtitles.append(
                                Subtitle(
                                    name=f"{lang} ({sub.get('ext', 'unknown')})",
                                    url=sub_url
                                )
                            )

            # User-Agent al
            user_agent = None
            http_headers = info.get("http_headers", {})
            if http_headers:
                user_agent = http_headers.get("User-Agent")

            return ExtractResult(
                name       = self.name,
                url        = video_url,
                referer    = referer or info.get("webpage_url"),
                user_agent = user_agent,
                subtitles  = subtitles
            )

    async def close(self):
        """yt-dlp için cleanup gerekmez"""
        pass
