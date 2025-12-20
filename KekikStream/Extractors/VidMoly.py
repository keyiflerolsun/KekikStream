# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.
# ! https://github.com/recloudstream/cloudstream/blob/master/library/src/commonMain/kotlin/com/lagradost/cloudstream3/extractors/Vidmoly.kt

from KekikStream.Core import ExtractorBase, ExtractResult, Subtitle
from parsel           import Selector
import re, contextlib, json

class VidMoly(ExtractorBase):
    name     = "VidMoly"
    main_url = "https://vidmoly.to"

    # Birden fazla domain destekle
    supported_domains = ["vidmoly.to", "vidmoly.me", "vidmoly.net"]

    def can_handle_url(self, url: str) -> bool:
        return any(domain in url for domain in self.supported_domains)

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        if referer:
            self.httpx.headers.update({"Referer": referer})

        self.httpx.headers.update({
            "Sec-Fetch-Dest" : "iframe",
        })

        if self.main_url.endswith(".me"):
            self.main_url = self.main_url.replace(".me", ".net")
            url = url.replace(".me", ".net")

        response = await self.httpx.get(url)
        if "Select number" in response.text:
            secici = Selector(response.text)
            response = await self.httpx.post(
                url  = url,
                data = {
                    "op"        : secici.css("input[name='op']::attr(value)").get(),
                    "file_code" : secici.css("input[name='file_code']::attr(value)").get(),
                    "answer"    : secici.css("div.vhint b::text").get(),
                    "ts"        : secici.css("input[name='ts']::attr(value)").get(),
                    "nonce"     : secici.css("input[name='nonce']::attr(value)").get(),
                    "ctok"      : secici.css("input[name='ctok']::attr(value)").get()
                }
            )

        script_match   = re.search(r"sources:\s*\[(.*?)\],", response.text, re.DOTALL)
        script_content = script_match[1] if script_match else None

        if not script_content:
            raise ValueError("Gerekli script bulunamadı.")

        # Video kaynaklarını ayrıştır
        video_data = self._add_marks(script_content, "file")
        try:
            video_sources = json.loads(f"[{video_data}]")
        except json.JSONDecodeError as hata:
            raise ValueError("Video kaynakları ayrıştırılamadı.") from hata

        # Altyazı kaynaklarını ayrıştır
        subtitles = []
        if subtitle_match := re.search(r"tracks:\s*\[(.*?)\]", response.text, re.DOTALL):
            subtitle_data = self._add_marks(subtitle_match[1], "file")
            subtitle_data = self._add_marks(subtitle_data, "label")
            subtitle_data = self._add_marks(subtitle_data, "kind")

            with contextlib.suppress(json.JSONDecodeError):
                subtitle_sources = json.loads(f"[{subtitle_data}]")
                subtitles = [
                    Subtitle(
                        name = sub.get("label"),
                        url  = self.fix_url(sub.get("file")),
                    )
                        for sub in subtitle_sources
                            if sub.get("kind") == "captions"
                ]
        # İlk video kaynağını al
        video_url = None
        for source in video_sources:
            if file_url := source.get("file"):
                video_url = file_url
                break

        if not video_url:
            raise ValueError("Video URL bulunamadı.")

        return ExtractResult(
            name      = self.name,
            url       = video_url,
            referer   = self.main_url,
            subtitles = subtitles
        )

    def _add_marks(self, text: str, field: str) -> str:
        """
        Verilen alanı çift tırnak içine alır.
        """
        return re.sub(rf"\"?{field}\"?", f"\"{field}\"", text)