# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.
# ! https://github.com/recloudstream/cloudstream/blob/master/library/src/commonMain/kotlin/com/lagradost/cloudstream3/extractors/Vidmoly.kt

from KekikStream.Core  import ExtractorBase, ExtractResult, Subtitle
from selectolax.parser import HTMLParser
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
            secici = HTMLParser(response.text)

            op_el        = secici.css_first("input[name='op']")
            file_code_el = secici.css_first("input[name='file_code']")
            answer_el    = secici.css_first("div.vhint b")
            ts_el        = secici.css_first("input[name='ts']")
            nonce_el     = secici.css_first("input[name='nonce']")
            ctok_el      = secici.css_first("input[name='ctok']")

            response = await self.httpx.post(
                url  = url,
                data = {
                    "op"        : op_el.attrs.get("value") if op_el else None,
                    "file_code" : file_code_el.attrs.get("value") if file_code_el else None,
                    "answer"    : answer_el.text(strip=True) if answer_el else None,
                    "ts"        : ts_el.attrs.get("value") if ts_el else None,
                    "nonce"     : nonce_el.attrs.get("value") if nonce_el else None,
                    "ctok"      : ctok_el.attrs.get("value") if ctok_el else None
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