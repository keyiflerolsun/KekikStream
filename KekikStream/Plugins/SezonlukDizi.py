# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode, ExtractResult
from selectolax.parser import HTMLParser
import re, asyncio

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
        alt_match   = re.search(r"dataAlternatif(.*?)\.asp", js_req.text)
        embed_match = re.search(r"dataEmbed(.*?)\.asp", js_req.text)
        
        return {
            "alternatif": alt_match.group(1) if alt_match else "",
            "embed":      embed_match.group(1) if embed_match else ""
        }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.httpx.get(f"{url}{page}")
        secici = HTMLParser(istek.text)

        results = []
        for veri in secici.css("div.afis a"):
            desc_el = veri.css_first("div.description")
            img_el  = veri.css_first("img")

            title  = desc_el.text(strip=True) if desc_el else None
            href   = veri.attrs.get("href")
            poster = img_el.attrs.get("data-src") if img_el else None

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
        secici = HTMLParser(istek.text)

        results = []
        for afis in secici.css("div.afis a"):
            desc_el = afis.css_first("div.description")
            img_el  = afis.css_first("img")

            title  = desc_el.text(strip=True) if desc_el else None
            href   = afis.attrs.get("href")
            poster = img_el.attrs.get("data-src") if img_el else None

            if title and href:
                results.append(SearchResult(
                    title  = title,
                    url    = self.fix_url(href),
                    poster = self.fix_url(poster) if poster else None,
                ))

        return results

    async def load_item(self, url: str) -> SeriesInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLParser(istek.text)

        title_el = secici.css_first("div.header")
        title    = title_el.text(strip=True) if title_el else ""

        poster_el = secici.css_first("div.image img")
        poster    = poster_el.attrs.get("data-src", "").strip() if poster_el else ""

        # year: re_first yerine re.search
        year_el = secici.css_first("div.extra span")
        year_text = year_el.text(strip=True) if year_el else ""
        year_match = re.search(r"(\d{4})", year_text)
        year = year_match.group(1) if year_match else None

        # xpath normalized-space yerine doğrudan ID ile element bulup text al
        desc_el = secici.css_first("span#tartismayorum-konu")
        description = desc_el.text(strip=True) if desc_el else ""

        tags = [a.text(strip=True) for a in secici.css("div.labels a[href*='tur']") if a.text(strip=True)]

        # rating: re_first yerine re.search
        rating_el = secici.css_first("div.dizipuani a div")
        rating_text = rating_el.text(strip=True) if rating_el else ""
        rating_match = re.search(r"[\d.,]+", rating_text)
        rating = rating_match.group() if rating_match else None

        actors = []

        actors_istek  = await self.httpx.get(f"{self.main_url}/oyuncular/{url.split('/')[-1]}")
        actors_secici = HTMLParser(actors_istek.text)
        for actor in actors_secici.css("div.doubling div.ui"):
            header_el = actor.css_first("div.header")
            if header_el and header_el.text(strip=True):
                actors.append(header_el.text(strip=True))

        episodes_istek  = await self.httpx.get(f"{self.main_url}/bolumler/{url.split('/')[-1]}")
        episodes_secici = HTMLParser(episodes_istek.text)
        episodes        = []

        for sezon in episodes_secici.css("table.unstackable"):
            for bolum in sezon.css("tbody tr"):
                # td:nth-of-type selectolax'ta desteklenmiyor, alternatif yol: tüm td'leri alıp indexle
                tds = bolum.css("td")
                if len(tds) < 4:
                    continue

                # 4. td'den isim ve href
                ep_name_el = tds[3].css_first("a")
                ep_name    = ep_name_el.text(strip=True) if ep_name_el else None
                ep_href    = ep_name_el.attrs.get("href") if ep_name_el else None

                # 3. td'den episode (re_first yerine re.search)
                ep_episode_el = tds[2].css_first("a")
                ep_episode_text = ep_episode_el.text(strip=True) if ep_episode_el else ""
                ep_episode_match = re.search(r"(\d+)", ep_episode_text)
                ep_episode = ep_episode_match.group(1) if ep_episode_match else None

                # 2. td'den season (re_first yerine re.search)
                ep_season_text = tds[1].text(strip=True) if tds[1] else ""
                ep_season_match = re.search(r"(\d+)", ep_season_text)
                ep_season = ep_season_match.group(1) if ep_season_match else None

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
        secici = HTMLParser(istek.text)
        asp_data = await self._get_asp_data()
        
        bid = secici.css_first("div#dilsec").attrs.get("data-id") if secici.css_first("div#dilsec") else None
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
                    embed_secici = HTMLParser(embed_resp.text)
                    iframe_el = embed_secici.css_first("iframe")
                    iframe_src = iframe_el.attrs.get("src") if iframe_el else None
                    
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