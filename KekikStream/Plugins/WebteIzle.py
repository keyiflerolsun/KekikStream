# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, ExtractResult, HTMLHelper
import re

class WebteIzle(PluginBase):
    name        = "WebteIzle"
    language    = "tr"
    main_url    = "https://webteizle3.xyz"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Her türlü filmi ister dublaj ister altyazılı, en kaliteli bir şekilde izleyebileceğiniz arşivi en geniş gerçek film izleme siteniz."

    main_page   = {
        f"{main_url}/yeni-filmler/"          : "Son Eklenenler",
        f"{main_url}/imdb/8/"                : "IMDB 8+",
        f"{main_url}/yil/2026/"              : "2026 Filmleri",
        f"{main_url}/yil/2025/"              : "2025 Filmleri",
        f"{main_url}/tavsiye-filmler/"       : "Tavsiye",
        f"{main_url}/filtre?tur=Aksiyon"     : "Aksiyon",
        f"{main_url}/filtre?tur=Animasyon"   : "Animasyon",
        f"{main_url}/filtre?tur=Belgesel"    : "Belgesel",
        f"{main_url}/filtre?tur=Bilim-Kurgu" : "Bilim Kurgu",
        f"{main_url}/filtre?tur=Dram"        : "Dram",
        f"{main_url}/filtre?tur=Fantastik"   : "Fantastik",
        f"{main_url}/filtre?tur=Gerilim"     : "Gerilim",
        f"{main_url}/filtre?tur=Komedi"      : "Komedi",
        f"{main_url}/filtre?tur=Korku"       : "Korku",
        f"{main_url}/filtre?tur=Macera"      : "Macera",
        f"{main_url}/filtre?tur=Romantik"    : "Romantik",
    }

    async def _request(self, url: str, method: str = "GET", **kwargs) -> str:
        """Centralized decoding helper."""
        if method == "POST":
            response = await self.async_cf_post(url, **kwargs)
        else:
            response = await self.async_cf_get(url, **kwargs)
        return response.content.decode("windows-1254", errors="replace")

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        symbol     = "&" if "?" in url else "/"
        candidates = [url if page == 1 else f"{url.rstrip('/')}{symbol}{page}"]

        if page == 1:
            normalized = url.rstrip("/")
            if normalized != url:
                candidates.append(normalized)
            else:
                candidates.append(f"{url}/")

        for request_url in candidates:
            secici  = HTMLHelper(await self._request(request_url))
            results = []
            for veri in secici.select("div.card.golgever"):
                link = veri.select_first("a[href*='/hakkinda/']") or veri.select_first("a.image")
                if not link:
                    continue

                results.append(MainPageResult(
                    category = category,
                    title    = veri.select_text("div.filmname"),
                    url      = self.fix_url(link.attrs.get("href", "")),
                    poster   = self.fix_url(veri.select_attr("img", "data-src") or ""),
                ))

            if results:
                return results

        return []

    async def search(self, query: str) -> list[SearchResult]:
        secici  = HTMLHelper(await self._request(f"{self.main_url}/filtre?a={query}"))
        results = []
        for veri in secici.select("div.card.golgever"):
            link = veri.select_first("a[href*='/hakkinda/']") or veri.select_first("a.image")
            if not link:
                continue

            results.append(SearchResult(
                title  = veri.select_text("div.filmname"),
                url    = self.fix_url(link.attrs.get("href", "")),
                poster = self.fix_url(veri.select_attr("img", "data-src") or ""),
            ))
        return results

    async def load_item(self, url: str) -> MovieInfo:
        secici = HTMLHelper(await self._request(url))
        title  = secici.select_text("h1 a") or secici.select_text("h1")
        if title and title.lower().endswith("izle"):
            title = title[:-4].strip()

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(secici.select_attr("div.card img, div.five.wide img", "data-src") or ""),
            title       = title,
            description = secici.select_text("blockquote[itemprop='description'] p"),
            tags        = secici.meta_list("tür"),
            rating      = secici.select_text("div.filmpuani div.detail"),
            year        = str(secici.extract_year("h1", "table.basic")),
            actors      = [a.strip() for a in [c.select_text("span.content") for c in secici.select("div[data-tab='oyuncular'] div.card")] if a] or None,
            duration    = secici.extract_duration("süre"),
        )

    def _parse_embed(self, embed_html: str) -> list[str]:
        urls = []
        for src in re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', embed_html, re.I):
            src = f"https:{src}" if src.startswith("//") else src
            # Relative URL (örn. /ajax/reCAPTCHADATA.asp) → atla
            if src.startswith("/") or not src.startswith("http"):
                continue
            urls.append(src.replace("bysezoxexe.com", "filemoon.sx").replace("vidmoly.me", "vidmoly.net").replace("hqq.to", "hqq.tv"))

        pts = {
            r"vidmoly\(['\"]([^'\"]+)['\"]"           : "https://vidmoly.net/embed-{}.html",
            r"(?:filemoon|bysezoxexe)\(['\"]([^'\"]+)['\"]" : "https://filemoon.sx/e/{}",
            r"sruby\(['\"]([^'\"]+)['\"]"             : "https://rubyvidhub.com/embed-{}.html",
            r"okru\(['\"]([^'\"]+)['\"]"              : "https://ok.ru/videoembed/{}",
            r"pixel\(['\"]([^'\"]+)['\"]"             : "https://pixeldrain.com/api/file/{}",
            r"mailru\(['\"]([^'\"]+)['\"]"            : "https://my.mail.ru/video/embed/{}",
        }
        for pat, fmt in pts.items():
            if m := re.search(pat, embed_html):
                urls.append(fmt.format(m.group(1).split("|")[0]))
        return urls

    async def load_links(self, url: str) -> list[ExtractResult]:
        slug, results = url.rstrip("/").split("/")[-1], []

        for dil_path, dil_code in [("dublaj", 0), ("altyazi", 1)]:
            izle_url = f"{self.main_url}/izle/{dil_path}/{slug}"
            secici   = HTMLHelper(await self._request(izle_url))

            film_id = secici.select_attr("#dilsec", "data-id")
            if not film_id:
                continue

            alt_res = await self.async_cf_post(
                f"{self.main_url}/ajax/dataAlternatif3.asp",
                data    = {"filmid": film_id, "dil": dil_code, "s": "", "b": "", "bot": 0},
                headers = {"Referer": izle_url, "X-Requested-With": "XMLHttpRequest"}
            )

            try:
                alt_json = alt_res.json()
            except:
                continue

            if alt_json.get("status") != "success":
                continue

            dil_adi = "Dublaj" if dil_code == 0 else "Altyazı"

            async def process_alt(alt):
                aid, abaslik = alt.get("id"), alt.get("baslik", "Bilinmeyen")
                if not aid:
                    return None

                emb_res = await self.async_cf_post(
                    f"{self.main_url}/ajax/dataEmbed.asp",
                    data    = {"id": aid},
                    headers = {"Referer": izle_url, "X-Requested-With": "XMLHttpRequest"}
                )

                sub_results = []
                for ifr in self._parse_embed(emb_res.text):
                    data = await self.extract(ifr, referer=izle_url, prefix=f"{dil_adi} | {abaslik}")
                    self.collect_results(sub_results, data)
                return sub_results

            tasks = [process_alt(a) for a in alt_json.get("data", [])]
            batch = await self.gather_with_limit(tasks, limit=3)
            for b in batch:
                self.collect_results(results, b)

        return results
