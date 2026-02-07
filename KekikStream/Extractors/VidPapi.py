# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, Subtitle, HTMLHelper


class VidPapi(ExtractorBase):
    name     = "VidPapi"
    main_url = "https://vidpapi.xyz"

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        ref = referer or self.main_url

        # ID tespiti
        if "video/" in url:
            vid_id = url.split("video/")[-1]
        else:
            vid_id = url.split("?data=")[-1]

        headers = {
            "Content-Type"     : "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With" : "XMLHttpRequest",
            "Referer"          : ref
        }

        # 1. Altyazıları çek
        subtitles = []
        try:
            sub_resp = await self.httpx.post(
                f"{self.main_url}/player/index.php?data={vid_id}",
                headers = headers,
                data    = {"hash": vid_id, "r": ref}
            )
            sel = HTMLHelper(sub_resp.text)
            if raw_subs := sel.regex_first(r'var playerjsSubtitle\s*=\s*"([^"]*)"'):
                for lang, link in HTMLHelper(raw_subs).regex_all(r'\[(.*?)\](https?://[^\s\",]+)'):
                    subtitles.append(Subtitle(name=lang.strip(), url=link.strip()))
        except:
            pass

        # 2. Videoyu çek
        resp = await self.httpx.post(
            f"{self.main_url}/player/index.php?data={vid_id}&do=getVideo",
            headers = headers,
            data    = {"hash": vid_id, "r": ref}
        )
        data = resp.json()

        stream_url = data.get("securedLink") or data.get("videoSource")
        if not stream_url:
            raise ValueError(f"VidPapi: Video URL bulunamadı. {url}")

        return ExtractResult(
            name      = self.name,
            url       = stream_url,
            referer   = ref,
            subtitles = subtitles
        )
