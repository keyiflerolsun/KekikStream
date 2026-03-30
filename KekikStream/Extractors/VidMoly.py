# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

# ! https://github.com/recloudstream/cloudstream/blob/master/library/src/commonMain/kotlin/com/lagradost/cloudstream3/extractors/Vidmoly.kt

from KekikStream.Core  import PackedJSExtractor, ExtractResult, Subtitle, HTMLHelper
import contextlib, json, re

class VidMoly(PackedJSExtractor):
    name     = "VidMoly"
    main_url = "https://vidmoly.me"

    # Birden fazla domain destekle
    supported_domains = ["vidmoly.to", "vidmoly.me", "vidmoly.net", "vidmoly.biz", "videobin.co"]

    def can_handle_url(self, url: str) -> bool:
        return "vidmoly" in url or any(domain in url for domain in self.supported_domains)

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        if referer:
            self.httpx.headers.update({"Referer": referer})

        self.httpx.headers.update({"Sec-Fetch-Dest" : "iframe"})

        # Önce orijinal embed sayfasını dene; yeni VidMoly kurulumları kaynakları burada veriyor.
        candidate_urls = [url]

        normalized_url = re.sub(r'https?://vidmoly\.[a-z]+', 'https://vidmoly.me', url)
        if normalized_url not in candidate_urls:
            candidate_urls.append(normalized_url)

        # Eski kurulumlar için /embed-CODE.html → /w/CODE fallback'i koru.
        watch_url = re.sub(r'/embed-([a-z0-9]+)\.html', r'/w/\1', normalized_url)
        if watch_url not in candidate_urls:
            candidate_urls.append(watch_url)

        resp = None
        sel  = None
        for candidate_url in candidate_urls:
            resp = await self.httpx.get(candidate_url, follow_redirects=True)
            sel  = HTMLHelper(resp.text)

            lowered = resp.text.lower()
            if "this video not found" in lowered or "file was deleted" in lowered or "video not found" in lowered:
                raise ValueError(f"VidMoly: Video silinmiş. {candidate_url}")

            if "sources:" in resp.text or ".m3u8" in resp.text or "jwplayer" in resp.text:
                url = candidate_url
                break

        # "Select number" kontrolü (Bot koruması)
        if "Select number" in resp.text or "select the number" in resp.text.lower():
            op_val        = sel.select_attr("input[name='op']", "value")
            file_code_val = sel.select_attr("input[name='file_code']", "value")

            # Answer is sometimes in a different element
            answer_val = sel.select_text("div.vhint b") or \
                         sel.select_text("span.vhint b") or \
                         sel.regex_first(r"Please select (\d+)")

            ts_val    = sel.select_attr("input[name='ts']", "value")
            nonce_val = sel.select_attr("input[name='nonce']", "value")
            ctok_val  = sel.select_attr("input[name='ctok']", "value")

            if op_val and file_code_val and answer_val:
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
                subtitles   = [
                    Subtitle(name=sub.get("label"), url=self.fix_url(sub.get("file")))
                    for sub in sub_sources if sub.get("kind") == "captions"
                ]

        # Video URL Bulma
        video_url = None

        # 1. Packed JS unpacked
        video_url = self.unpack_and_find(resp.text)

        if not video_url and "#EXTM3U" in resp.text:
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
