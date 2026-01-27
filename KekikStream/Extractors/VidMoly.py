# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.
# ! https://github.com/recloudstream/cloudstream/blob/master/library/src/commonMain/kotlin/com/lagradost/cloudstream3/extractors/Vidmoly.kt

from KekikStream.Core  import ExtractorBase, ExtractResult, Subtitle, HTMLHelper
import re, contextlib, json

class VidMoly(ExtractorBase):
    name     = "VidMoly"
    main_url = "https://vidmoly.to"

    # Birden fazla domain destekle
    supported_domains = ["vidmoly.to", "vidmoly.me", "vidmoly.net", "vidmoly.biz"]

    def can_handle_url(self, url: str) -> bool:
        return any(domain in url for domain in self.supported_domains)

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        if referer:
            self.httpx.headers.update({"Referer": referer})

        self.httpx.headers.update({"Sec-Fetch-Dest" : "iframe"})

        # Domain normalleştirme
        url = url.replace(".me", ".net").replace(".to", ".net")

        resp = await self.httpx.get(url, follow_redirects=True)
        sel  = HTMLHelper(resp.text)

        # "Select number" kontrolü (Bot koruması)
        if "Select number" in resp.text:
            op_val        = sel.select_attr("input[name='op']", "value")
            file_code_val = sel.select_attr("input[name='file_code']", "value")
            answer_val    = sel.select_text("div.vhint b")
            ts_val        = sel.select_attr("input[name='ts']", "value")
            nonce_val     = sel.select_attr("input[name='nonce']", "value")
            ctok_val      = sel.select_attr("input[name='ctok']", "value")

            resp = await self.httpx.post(url, data={
                "op"        : op_val,
                "file_code" : file_code_val,
                "answer"    : answer_val,
                "ts"        : ts_val,
                "nonce"     : nonce_val,
                "ctok"      : ctok_val
            }, follow_redirects=True)
            sel = HTMLHelper(resp.text)

        # Altyazı kaynaklarını ayrıştır
        subtitles = []
        if sub_str := sel.regex_first(r"(?s)tracks:\s*\[(.*?)\]"):
            sub_data = self._add_marks(sub_str, "file")
            sub_data = self._add_marks(sub_data, "label")
            sub_data = self._add_marks(sub_data, "kind")

            with contextlib.suppress(json.JSONDecodeError):
                sub_sources = json.loads(f"[{sub_data}]")
                subtitles = [
                    Subtitle(name=sub.get("label"), url=self.fix_url(sub.get("file")))
                    for sub in sub_sources if sub.get("kind") == "captions"
                ]

        # Video URL Bulma
        video_url = None
        if "#EXTM3U" in resp.text:
            for line in resp.text.splitlines():
                if line.strip().startswith("http"):
                    video_url = line.strip().replace('"', '').replace("'", "")
                    break

        if not video_url:
            if src_str := sel.regex_first(r"(?s)sources:\s*\[(.*?)\],"):
                vid_data = self._add_marks(src_str, "file")
                with contextlib.suppress(json.JSONDecodeError):
                    vid_sources = json.loads(f"[{vid_data}]")
                    for source in vid_sources:
                        if source.get("file"):
                            video_url = source.get("file")
                            break

        if not video_url:
            video_url = sel.regex_first(r'file\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']') or \
                        sel.regex_first(r'file\s*:\s*["\']([^"\']+\.mp4[^"\']*)["\']')

        if not video_url:
            raise ValueError(f"VidMoly: Video URL bulunamadı. {url}")

        return ExtractResult(
            name      = self.name,
            url       = video_url,
            referer   = f"{self.get_base_url(url)}/",
            subtitles = subtitles
        )

    def _add_marks(self, text: str, field: str) -> str:
        """
        Verilen alanı çift tırnak içine alır.
        """
        return HTMLHelper(text).regex_replace(rf"\"?{field}\"?", f"\"{field}\"")