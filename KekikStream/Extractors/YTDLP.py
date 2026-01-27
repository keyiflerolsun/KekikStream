# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, Subtitle, get_ytdlp_extractors
from urllib.parse     import urlparse
import yt_dlp, re, sys, os

class YTDLP(ExtractorBase):
    name     = "yt-dlp"
    main_url = ""  # Universal - tüm siteleri destekler

    _FAST_DOMAIN_RE = None  # compiled mega-regex (host üstünden)

    _POPULAR_TLDS = {
        "com", "net", "org", "tv", "io", "co", "me", "ly", "ru", "fr", "de", "es", "it",
        "nl", "be", "ch", "at", "uk", "ca", "au", "jp", "kr", "cn", "in", "br", "mx",
        "ar", "tr", "gov", "edu", "mil", "int", "info", "biz", "name", "pro", "aero",
        "coop", "museum", "onion"
    }

    # 1. Literal TLD Regex: youtube\.com, vimeo\.com
    # sorted by reverse length to prevent partial matches (e.g. 'co' matching 'com')
    _LITERAL_TLD_RE = re.compile(
        rf"([a-z0-9][-a-z0-9]*(?:\\\.[-a-z0-9]+)*\\\.(?:{'|'.join(sorted(_POPULAR_TLDS, key=len, reverse=True))}))",
        re.IGNORECASE
    )

    # 2. Regex TLD Regex: dailymotion\.[a-z]{2,3}
    _REGEX_TLD_RE = re.compile(
        r"([a-z0-9][-a-z0-9]*)\\\.\[a-z\]\{?\d*,?\d*\}?",
        re.IGNORECASE
    )

    # 3. Alternation TLD Regex: \.(?:com|net|org)
    _ALT_TLD_RE = re.compile(
        r"\\\.\(\?:([a-z|]+)\)",
        re.IGNORECASE
    )

    # Kelime yakalayıcı (domain bulmak için)
    _DOMAIN_WORD_RE = re.compile(
        r"([a-z0-9][-a-z0-9]*)",
        re.IGNORECASE
    )

    @classmethod
    def _extract_literal_domains(cls, valid_url: str) -> set[str]:
        """Pattern 1: Literal TLD domainlerini (youtube.com) çıkarır."""
        return {
            m.replace(r"\.", ".").lower()
            for m in cls._LITERAL_TLD_RE.findall(valid_url)
        }

    @classmethod
    def _extract_regex_tld_domains(cls, valid_url: str) -> set[str]:
        """Pattern 2: Regex TLD domainlerini (dailymotion.[...]) çıkarır ve popüler TLD'lerle birleştirir."""
        domains = set()
        for base in cls._REGEX_TLD_RE.findall(valid_url):
            base_domain = base.lower()
            for tld in cls._POPULAR_TLDS:
                domains.add(f"{base_domain}.{tld}")
        return domains

    @classmethod
    def _extract_alternation_domains(cls, valid_url: str) -> set[str]:
        """Pattern 3: Alternation TLD domainlerini (pornhub.(?:com|net)) çıkarır."""
        domains = set()
        for m in cls._ALT_TLD_RE.finditer(valid_url):
            tlds = m.group(1).split("|")
            start = m.start()

            # Geriye doğru git ve domain'i bul
            before = valid_url[:start]

            # 1. Named Groups (?P<name> temizle
            before = re.sub(r"\(\?P<[^>]+>", "", before)

            # 2. Simple Non-Capturing Groups (?:xxx)? temizle (sadece alphanumeric ve escape)
            before = re.sub(r"\(\?:[a-z0-9-]+\)\??", "", before)

            # Son domain-like kelimeyi al
            words = cls._DOMAIN_WORD_RE.findall(before)
            if not words:
                continue

            base = words[-1].lower()
            for tld in tlds:
                tld = tld.strip().lower()
                if tld and len(tld) <= 6:
                    domains.add(f"{base}.{tld}")

        return domains

    @classmethod
    def _init_fast_domain_regex(cls):
        """
        Fast domain regex'i initialize et
        """
        if cls._FAST_DOMAIN_RE is not None:
            return

        domains = set()
        extractors = get_ytdlp_extractors()

        for ie in extractors:
            valid = getattr(ie, "_VALID_URL", None)
            if not valid or not isinstance(valid, str):
                continue

            domains |= cls._extract_literal_domains(valid)
            domains |= cls._extract_regex_tld_domains(valid)
            domains |= cls._extract_alternation_domains(valid)

        # Hiç domain çıkmazsa (çok uç durum) fallback: boş regex
        if not domains:
            cls._FAST_DOMAIN_RE = re.compile(r"$^")  # hiçbir şeye match etmez
            return

        joined = "|".join(re.escape(d) for d in sorted(domains))
        cls._FAST_DOMAIN_RE = re.compile(rf"(?:^|.*\.)(?:{joined})$", re.IGNORECASE)

    def __init__(self):
        self.__class__._init_fast_domain_regex()

    def can_handle_url(self, url: str) -> bool:
        """
        Fast-path: URL host'unu tek mega-regex ile kontrol et
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

        # yt-dlp işleyemezse False döndür
        return False

    async def extract(self, url: str, referer: str | None = None) -> ExtractResult:
        ydl_opts = {
            "quiet"                 : True,
            "no_warnings"           : True,
            "extract_flat"          : False,       # Tam bilgi al
            "format"                : "best/all",  # En iyi kalite, yoksa herhangi biri
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
