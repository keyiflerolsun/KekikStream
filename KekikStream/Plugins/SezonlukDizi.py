# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode, ExtractResult, HTMLHelper
import asyncio

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
        js = HTMLHelper(js_req.text)
        alt = js.regex_first(r"dataAlternatif(.*?)\.asp")
        emb = js.regex_first(r"dataEmbed(.*?)\.asp")
        
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
                    poster   = self.fix_url(poster) if poster else None,
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}/diziler.asp?adi={query}")
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
                    poster = self.fix_url(poster) if poster else None,
                ))

        return results

    async def load_item(self, url: str) -> SeriesInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        title    = secici.select_text("div.header") or ""

        poster    = secici.select_attr("div.image img", "data-src") or ""

        # year: re_first yerine re.search
        year_text = secici.select_text("div.extra span") or ""
        year = secici.regex_first(r"(\d{4})", year_text)

        # xpath normalized-space yerine doğrudan ID ile element bulup text al
        description = secici.select_text("span#tartismayorum-konu") or ""

        tags = [a.text(strip=True) for a in secici.select("div.labels a[href*='tur']") if a.text(strip=True)]

        # rating: regex ile çıkar
        rating_text = secici.select_text("div.dizipuani a div") or ""
        rating = secici.regex_first(r"[\d.,]+", rating_text)

        actors = []

        actors_istek  = await self.httpx.get(f"{self.main_url}/oyuncular/{url.split('/')[-1]}")
        actors_secici = HTMLHelper(actors_istek.text)
        for actor in actors_secici.select("div.doubling div.ui"):
            header_text = actors_secici.select_text("div.header", actor)
            if header_text:
                actors.append(header_text)

        episodes_istek  = await self.httpx.get(f"{self.main_url}/bolumler/{url.split('/')[-1]}")
        episodes_secici = HTMLHelper(episodes_istek.text)
        episodes        = []

        for sezon in episodes_secici.select("table.unstackable"):
            for bolum in episodes_secici.select("tbody tr", sezon):
                # td:nth-of-type selectolax'ta desteklenmiyor, alternatif yol: tüm td'leri alıp indexle
                tds = episodes_secici.select("td", bolum)
                if len(tds) < 4:
                    continue

                # 4. td'den isim ve href
                ep_name    = episodes_secici.select_text("a", tds[3])
                ep_href    = episodes_secici.select_attr("a", "href", tds[3])

                # 3. td'den episode (re_first yerine regex)
                ep_episode_text = episodes_secici.select_text("a", tds[2]) or ""
                ep_episode = episodes_secici.regex_first(r"(\d+)", ep_episode_text)

                # 2. td'den season (re_first yerine regex)
                ep_season_text = tds[1].text(strip=True) if tds[1] else ""
                ep_season = secici.regex_first(r"(\d+)", ep_season_text)

                if ep_name and ep_href:
                    episode = Episode(
                        season  = ep_season,
                        episode = ep_episode,
                        title   = ep_name,
                        url     = self.fix_url(ep_href),
                    )
                    episodes.append(episode)

        return SeriesInfo(
            url         = url,
            poster      = self.fix_url(poster) if poster else None,
            title       = title,
            description = description,
            tags        = tags,
            rating      = rating,
            year        = year,
            episodes    = episodes,
            actors      = actors
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)
        asp_data = await self._get_asp_data()
        
        bid = secici.select_attr("div#dilsec", "data-id")
        if not bid:
            return []

        semaphore = asyncio.Semaphore(5)
        tasks = []

        async def fetch_and_extract(veri, dil_etiketi):
            async with semaphore:
                try:
                    embed_resp = await self.httpx.post(
                        f"{self.main_url}/ajax/dataEmbed{asp_data['embed']}.asp",
                        headers = {"X-Requested-With": "XMLHttpRequest"},
                        data    = {"id": str(veri.get("id"))}
                    )
                    embed_secici = HTMLHelper(embed_resp.text)
                    iframe_src = embed_secici.select_attr("iframe", "src")
                    
                    if iframe_src:
                        if "link.asp" in iframe_src:
                            return None
                            
                        iframe_url = self.fix_url(iframe_src)
                        return await self.extract(iframe_url, referer=f"{self.main_url}/", prefix=f"{dil_etiketi} - {veri.get('baslik')}")
                except:
                    pass
                return None

        for dil_kodu, dil_etiketi in [("1", "Altyazı"), ("0", "Dublaj")]:
            altyazi_resp = await self.httpx.post(
                f"{self.main_url}/ajax/dataAlternatif{asp_data['alternatif']}.asp",
                headers = {"X-Requested-With": "XMLHttpRequest"},
                data    = {"bid": bid, "dil": dil_kodu}
            )
            
            try:
                data_json = altyazi_resp.json()
                if data_json.get("status") == "success" and data_json.get("data"):
                    for veri in data_json["data"]:
                        tasks.append(fetch_and_extract(veri, dil_etiketi))
            except:
                continue

        results = await asyncio.gather(*tasks)
        return [r for r in results if r]