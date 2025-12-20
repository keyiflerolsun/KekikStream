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

        if ".me" in url:
            url = url.replace(".me", ".net")

        # VidMoly bazen redirect ediyor, takip et
        response = await self.httpx.get(url, follow_redirects=True)
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
                },
                follow_redirects=True
            )


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

        script_match = re.search(r"sources:\s*\[(.*?)\],", response.text, re.DOTALL)
        if script_match:
            script_content = script_match[1]
            # Video kaynaklarını ayrıştır
            video_data = self._add_marks(script_content, "file")
            try:
                video_sources = json.loads(f"[{video_data}]")
                # İlk video kaynağını al
                for source in video_sources:
                    if file_url := source.get("file"):
                        return ExtractResult(
                            name      = self.name,
                            url       = file_url,
                            referer   = self.main_url,
                            subtitles = subtitles
                        )
            except json.JSONDecodeError:
                pass

        # Fallback: Doğrudan file regex ile ara (Kotlin mantığı)
        # file:"..." veya file: "..."
        if file_match := re.search(r'file\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']', response.text):
            return ExtractResult(
                name      = self.name,
                url       = file_match.group(1),
                referer   = self.main_url,
                subtitles = subtitles
            )
            
        # Fallback 2: Herhangi bir file (m3u8 olma şartı olmadan ama tercihen)
        if file_match := re.search(r'file\s*:\s*["\']([^"\']+)["\']', response.text):
            url_candidate = file_match.group(1)
            # Resim dosyalarını hariç tut
            if not url_candidate.endswith(('.jpg', '.png', '.jpeg')):
                return ExtractResult(
                    name      = self.name,
                    url       = url_candidate,
                    referer   = self.main_url,
                    subtitles = subtitles
                )

        raise ValueError("Video URL bulunamadı.")

    def _add_marks(self, text: str, field: str) -> str:
        """
        Verilen alanı çift tırnak içine alır.
        """
        return re.sub(rf"\"?{field}\"?", f"\"{field}\"", text)