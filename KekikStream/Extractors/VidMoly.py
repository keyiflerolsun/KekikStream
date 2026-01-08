# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.
# ! https://github.com/recloudstream/cloudstream/blob/master/library/src/commonMain/kotlin/com/lagradost/cloudstream3/extractors/Vidmoly.kt

from KekikStream.Core  import ExtractorBase, ExtractResult, Subtitle, HTMLHelper
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
            secici = HTMLHelper(response.text)

            op_val        = secici.select_attr("input[name='op']", "value")
            file_code_val = secici.select_attr("input[name='file_code']", "value")
            answer_val    = secici.select_text("div.vhint b")
            ts_val        = secici.select_attr("input[name='ts']", "value")
            nonce_val     = secici.select_attr("input[name='nonce']", "value")
            ctok_val      = secici.select_attr("input[name='ctok']", "value")

            response = await self.httpx.post(
                url  = url,
                data = {
                    "op"        : op_val,
                    "file_code" : file_code_val,
                    "answer"    : answer_val,
                    "ts"        : ts_val,
                    "nonce"     : nonce_val,
                    "ctok"      : ctok_val
                },
                follow_redirects=True
            )


        # Altyazı kaynaklarını ayrıştır
        subtitles = []
        resp_sec = HTMLHelper(response.text)
        if subtitle_str := resp_sec.regex_first(r"tracks:\s*\[(.*?)\]", flags= re.DOTALL):
            subtitle_data = self._add_marks(subtitle_str, "file")
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

        if script_str := resp_sec.regex_first(r"sources:\s*\[(.*?)\],", flags= re.DOTALL):
            script_content = script_str
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
        if file_match := resp_sec.regex_first(r'file\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']'):
            return ExtractResult(
                name      = self.name,
                url       = file_match,
                referer   = self.main_url,
                subtitles = subtitles
            )
            
        # Fallback 2: Herhangi bir file (m3u8 olma şartı olmadan ama tercihen)
        if file_match := resp_sec.regex_first(r'file\s*:\s*["\']([^"\']+)["\']'):
            url_candidate = file_match
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
        return HTMLHelper(text).regex_replace(rf"\"?{field}\"?", f"\"{field}\"")