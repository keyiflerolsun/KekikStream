# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, Subtitle
import yt_dlp, sys, os

class YTDLP(ExtractorBase):
    name     = "yt-dlp"
    main_url = ""  # Universal - tüm siteleri destekler

    def __init__(self):
        pass

    def can_handle_url(self, url: str) -> bool:
        """
        yt-dlp'nin bu URL'yi işleyip işleyemeyeceğini kontrol et
        """
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
                    "ignoreerrors"          : True   # Hataları yoksay
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
            "extract_flat"          : False,  # Tam bilgi al
            "format"                : "best",  # En iyi kalite
            "no_check_certificates" : True
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
