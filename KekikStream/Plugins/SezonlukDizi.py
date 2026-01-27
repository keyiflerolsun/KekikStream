# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode, ExtractResult, HTMLHelper
import asyncio, contextlib

class SezonlukDizi(PluginBase):
    name        = "SezonlukDizi"
    language    = "tr"
    main_url    = "https://sezonlukdizi8.com"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Güncel ve eski dizileri en iyi görüntü kalitesiyle bulabileceğiniz yabancı dizi izleme siteniz."

    main_page   = {
        f"{main_url}/diziler.asp?siralama_tipi=id&s="          : "Son Eklenenler",
        f"{main_url}/diziler.asp?siralama_tipi=id&tur=mini&s=" : "Mini Diziler",
        f"{main_url}/diziler.asp?siralama_tipi=id&kat=2&s="    : "Yerli Diziler",
        f"{main_url}/diziler.asp?siralama_tipi=id&kat=1&s="    : "Yabancı Diziler",
        f"{main_url}/diziler.asp?siralama_tipi=id&kat=3&s="    : "Asya Dizileri",
        f"{main_url}/diziler.asp?siralama_tipi=id&kat=4&s="    : "Animasyonlar",
        f"{main_url}/diziler.asp?siralama_tipi=id&kat=5&s="    : "Animeler",
        f"{main_url}/diziler.asp?siralama_tipi=id&kat=6&s="    : "Belgeseller",
        f"{main_url}/diziler.asp?siralama_tipi=id&tur=aile&s="       : "Aile",
        f"{main_url}/diziler.asp?siralama_tipi=id&tur=aksiyon&s="    : "Aksiyon",
        f"{main_url}/diziler.asp?siralama_tipi=id&tur=bilimkurgu&s=" : "Bilim Kurgu",
        f"{main_url}/diziler.asp?siralama_tipi=id&tur=biyografik&s=" : "Biyografi",
        f"{main_url}/diziler.asp?siralama_tipi=id&tur=dram&s="       : "Dram",
        f"{main_url}/diziler.asp?siralama_tipi=id&tur=fantastik&s="  : "Fantastik",
        f"{main_url}/diziler.asp?siralama_tipi=id&tur=gerilim&s="    : "Gerilim",
        f"{main_url}/diziler.asp?siralama_tipi=id&tur=gizem&s="      : "Gizem",
        f"{main_url}/diziler.asp?siralama_tipi=id&tur=korku&s="      : "Korku",
        f"{main_url}/diziler.asp?siralama_tipi=id&tur=komedi&s="     : "Komedi",
        f"{main_url}/diziler.asp?siralama_tipi=id&tur=macera&s="     : "Macera",
        f"{main_url}/diziler.asp?siralama_tipi=id&tur=muzikal&s="    : "Müzikal",
        f"{main_url}/diziler.asp?siralama_tipi=id&tur=suc&s="        : "Suç",
        f"{main_url}/diziler.asp?siralama_tipi=id&tur=romantik&s="   : "Romantik",
        f"{main_url}/diziler.asp?siralama_tipi=id&tur=savas&s="      : "Savaş",
        f"{main_url}/diziler.asp?siralama_tipi=id&tur=tarihi&s="     : "Tarihi",
        f"{main_url}/diziler.asp?siralama_tipi=id&tur=western&s="    : "Western"
    }

    async def _get_asp_data(self) -> dict:
        js_req = await self.httpx.get(f"{self.main_url}/js/site.min.js")
        js     = HTMLHelper(js_req.text)
        alt    = js.regex_first(r"dataAlternatif(.*?)\.asp")
        emb    = js.regex_first(r"dataEmbed(.*?)\.asp")

        return {
            "alternatif": alt or "",
            "embed":      emb or ""
        }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.httpx.get(f"{url}{page}")
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.afis a"):
            title  = secici.select_text("div.description", veri)
            href   = secici.select_attr("a", "href", veri)
            poster = secici.select_attr("img", "data-src", veri)

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title,
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster),
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}/diziler.asp?q={query}")
        secici = HTMLHelper(istek.text)

        results = []
        for afis in secici.select("div.afis a"):
            title  = secici.select_text("div.description", afis)
            href   = secici.select_attr("a", "href", afis)
            poster = secici.select_attr("img", "data-src", afis)

            if title and href:
                results.append(SearchResult(
                    title  = title,
                    url    = self.fix_url(href),
                    poster = self.fix_url(poster),
                ))

        return results

    async def load_item(self, url: str) -> SeriesInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        title       = secici.select_text("div.header") or ""
        poster      = secici.select_poster("div.image img")
        year        = secici.extract_year("div.extra span")
        description = secici.select_text("span#tartismayorum-konu")
        tags        = secici.select_texts("div.labels a[href*='tur']")
        rating      = secici.regex_first(r"[\d.,]+", secici.select_text("div.dizipuani a div"))

        # Actors extraction
        id_slug = url.split('/')[-1]
        a_resp  = await self.httpx.get(f"{self.main_url}/oyuncular/{id_slug}")
        a_sel   = HTMLHelper(a_resp.text)
        actors  = a_sel.select_texts("div.doubling div.ui div.header")

        # Episodes extraction
        e_resp   = await self.httpx.get(f"{self.main_url}/bolumler/{id_slug}")
        e_sel    = HTMLHelper(e_resp.text)
        episodes = []
        for row in e_sel.select("table.unstackable tbody tr"):
            tds = e_sel.select("td", row)
            if len(tds) >= 4:
                name = e_sel.select_text("a", tds[3])
                href = e_sel.select_attr("a", "href", tds[3])
                if name and href:
                    s, e = e_sel.extract_season_episode(f"{tds[1].text(strip=True)} {tds[2].text(strip=True)}")
                    episodes.append(Episode(
                        season  = s or 1,
                        episode = e or 1,
                        title   = name,
                        url     = self.fix_url(href)
                    ))

        return SeriesInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title,
            description = description,
            tags        = tags,
            rating      = rating,
            year        = year,
            episodes    = episodes,
            actors      = actors
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek    = await self.httpx.get(url)
        secici   = HTMLHelper(istek.text)
        asp_data = await self._get_asp_data()

        bid = secici.select_attr("div#dilsec", "data-id")
        if not bid:
            return []

        semaphore = asyncio.Semaphore(5)
        tasks = []

        async def fetch_and_extract(veri, dil_etiketi) -> list[ExtractResult]:
            async with semaphore:
                try:
                    embed_resp = await self.httpx.post(
                        url     = f"{self.main_url}/ajax/dataEmbed{asp_data['embed']}.asp",
                        headers = {"X-Requested-With": "XMLHttpRequest"},
                        data    = {"id": str(veri.get("id"))}
                    )
                    embed_secici = HTMLHelper(embed_resp.text)
                    iframe_src   = embed_secici.select_attr("iframe", "src") or embed_secici.regex_first(r'src="(.*?)"')

                    if not iframe_src:
                        return []

                    iframe_url = self.fix_url(iframe_src)

                    real_url = iframe_url
                    if "url=" in iframe_url:
                        real_url = HTMLHelper(iframe_url).regex_first(r"url=([^&]+)")
                        if real_url:
                            real_url = self.fix_url(real_url)

                    source_name = veri.get('baslik') or "SezonlukDizi"
                    full_name   = f"{dil_etiketi} - {source_name}"

                    extracted = await self.extract(real_url, referer=f"{self.main_url}/")

                    if not extracted:
                         return []

                    results = []
                    items   = extracted if isinstance(extracted, list) else [extracted]
                    for item in items:
                        item.name = full_name
                        results.append(item)
                    return results

                except Exception:
                    return []

        for dil_kodu, dil_etiketi in [("1", "Altyazı"), ("0", "Dublaj")]:
            with contextlib.suppress(Exception):
                altyazi_resp = await self.httpx.post(
                    url     = f"{self.main_url}/ajax/dataAlternatif{asp_data['alternatif']}.asp",
                    headers = {"X-Requested-With": "XMLHttpRequest"},
                    data    = {"bid": bid, "dil": dil_kodu}
                )

                data_json = altyazi_resp.json()
                if data_json.get("status") == "success" and data_json.get("data"):
                    for veri in data_json["data"]:
                        tasks.append(fetch_and_extract(veri, dil_etiketi))

        results_groups = await asyncio.gather(*tasks)

        final_results = []
        for group in results_groups:
             if group:
                 final_results.extend(group)

        return final_results
