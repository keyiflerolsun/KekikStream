# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import ExtractorBase, ExtractResult, Subtitle, HTMLHelper

class MolyStream(ExtractorBase):
    name     = "MolyStream"
    main_url = "https://dbx.molystream.org"

    # Birden fazla domain destekle
    supported_domains = [
        "dbx.molystream.org", "ydx.molystream.org",
        "yd.sheila.stream", "ydf.popcornvakti.net",
    ]

    def can_handle_url(self, url: str) -> bool:
        return any(domain in url for domain in self.supported_domains)

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        self.httpx.headers.update({"Referer": referer or self.main_url})

        # Eğer url zaten bir HTML kaynağıysa (doctype html içeriyorsa)
        if "doctype html" in url.lower():
            sel   = HTMLHelper(url)
            v_url = sel.select_attr("video#sheplayer source", "src")
        else:
            v_url = url

        subtitles = []
        for s_url, s_name in HTMLHelper(url).regex_all(r"addSrtFile\(['\"]([^'\"]+\.srt)['\"]\s*,\s*['\"][a-z]{2}['\"]\s*,\s*['\"]([^'\"]+)['\"]"):
            subtitles.append(Subtitle(name=s_name, url=self.fix_url(s_url)))

        return ExtractResult(
            name      = self.name,
            url       = v_url,
            referer   = v_url.replace("/sheila", "") if v_url else None,
            user_agent = "Mozilla/5.0 (X11; Linux x86_64; rv:101.0) Gecko/20100101 Firefox/101.0",
            subtitles = subtitles
        )
