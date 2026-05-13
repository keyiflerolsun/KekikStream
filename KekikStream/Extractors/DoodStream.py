# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult
import re, time


class DoodStream(ExtractorBase):
    name     = "DoodStream"
    main_url = "https://doodstream.com"

    supported_domains = [
        "doodstream.com",
        "dood.re",
        "dood.wf",
        "dood.la",
        "dood.to",
        "dood.so",
        "dood.sh",
        "dood.pm",
        "dood.watch",
        "dood.video",
        "dood.ws",
        "dood.cx",
        "dood.yt",
        "dood.li",
        "dood.io",
        "dood.me",
        "dood.yt",
        "dood.cloud",
        "ds2video.com",
        "dooood.com",
        "dood.cc",
        "dooodster.com",
        "myvidplay.com",
        "dsvplay.com",
    ]

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        original_url = url
        url          = url.replace("/e/", "/d/") if "/e/" in url else url
        base         = self.get_base_url(url)
        headers      = {"Referer": referer or base}

        resp = await self.httpx.get(url, headers=headers)
        html = resp.text

        if "Video not found" in html or "File was deleted" in html:
            raise ValueError(f"{self.name}: Video silinmiş.")

        # DoodStream token/key parsing
        pass_key = re.search(r"/(?:pass_md5|pass_key)/([^'\"]+)", html)
        if not pass_key:
            pass_key = re.search(r"/(?:pass_md5|pass_key)/([^'\"]+)", html, re.IGNORECASE)

        if not pass_key:
            # Try finding it in script calls
            pass_key = re.search(r"\.get\(['\"]/([^'\"]+)['\"]", html)

        if not pass_key:
            # /d/ sürümünde bulamazsak /e/ sürümünü dene
            if "/d/" in url:
                return await self.extract(url.replace("/d/", "/e/"), referer=referer)
            if "/e/" in url:
                return await self.extract(url.replace("/e/", "/d/"), referer=referer)
            raise ValueError(f"{self.name}: Pass key bulunamadı.")

        pk_val   = pass_key.group(1)
        pass_url = f"{base}/{pk_val.lstrip('/')}"

        # Second request to get the final link part
        pass_resp = await self.httpx.get(pass_url, headers={"Referer": url})

        if not pass_resp.text:
             raise ValueError(f"{self.name}: Pass response empty.")

        # Final URL construction
        token  = pk_val.split("/")[-1]
        expiry = int(time.time() * 1000)

        # random characters (usually 10)
        random_str = "".join(re.findall(r"[a-zA-Z0-9]", pk_val))[:10]
        if len(random_str) < 10:
            random_str = "kekikstream"

        final_url = f"{pass_resp.text}{random_str}?token={token}&expiry={expiry}"

        return ExtractResult(name=self.name, url=final_url, referer=url)
