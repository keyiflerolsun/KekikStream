# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import PluginBase, MainPageResult, SearchResult, MovieInfo, ExtractResult
from selectolax.parser import HTMLParser
from Kekik.Sifreleme   import StringCodec
import json, re

class FullHDFilmizlesene(PluginBase):
    name        = "FullHDFilmizlesene"
    language    = "tr"
    main_url    = "https://www.fullhdfilmizlesene.tv"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Türkiye'nin ilk ve lider HD film izleme platformu, kaliteli ve sorunsuz hizmetiyle sinema keyfini zirveye taşır."

    main_page   = {
        f"{main_url}/en-cok-izlenen-hd-filmler/"            : "En Çok izlenen Filmler",
        f"{main_url}/filmizle/aile-filmleri-hdf-izle/"      : "Aile Filmleri",
        f"{main_url}/filmizle/aksiyon-filmleri-hdf-izle/"   : "Aksiyon Filmleri",
        f"{main_url}/filmizle/animasyon-filmleri-izle/"     : "Animasyon Filmleri",
        f"{main_url}/filmizle/belgesel-filmleri-izle/"      : "Belgeseller",
        f"{main_url}/filmizle/bilim-kurgu-filmleri-izle-2/" : "Bilim Kurgu Filmleri",
        f"{main_url}/filmizle/bluray-filmler-izle/"         : "Blu Ray Filmler",
        f"{main_url}/filmizle/cizgi-filmler-fhd-izle/"      : "Çizgi Filmler",
        f"{main_url}/filmizle/dram-filmleri-hd-izle/"       : "Dram Filmleri",
        f"{main_url}/filmizle/fantastik-filmler-hd-izle/"   : "Fantastik Filmler",
        f"{main_url}/filmizle/gerilim-filmleri-fhd-izle/"   : "Gerilim Filmleri",
        f"{main_url}/filmizle/gizem-filmleri-hd-izle/"      : "Gizem Filmleri",
        f"{main_url}/filmizle/hint-filmleri-fhd-izle/"      : "Hint Filmleri",
        f"{main_url}/filmizle/komedi-filmleri-fhd-izle/"    : "Komedi Filmleri",
        f"{main_url}/filmizle/korku-filmleri-izle-3/"       : "Korku Filmleri",
        f"{main_url}/filmizle/macera-filmleri-fhd-izle/"    : "Macera Filmleri",
        f"{main_url}/filmizle/muzikal-filmler-izle/"        : "Müzikal Filmler",
        f"{main_url}/filmizle/polisiye-filmleri-izle/"      : "Polisiye Filmleri",
        f"{main_url}/filmizle/psikolojik-filmler-izle/"     : "Psikolojik Filmler",
        f"{main_url}/filmizle/romantik-filmler-fhd-izle/"   : "Romantik Filmler",
        f"{main_url}/filmizle/savas-filmleri-fhd-izle/"     : "Savaş Filmleri",
        f"{main_url}/filmizle/suc-filmleri-izle/"           : "Suç Filmleri",
        f"{main_url}/filmizle/tarih-filmleri-fhd-izle/"     : "Tarih Filmleri",
        f"{main_url}/filmizle/western-filmler-hd-izle-3/"   : "Western Filmler",
        f"{main_url}/filmizle/yerli-filmler-hd-izle/"       : "Yerli Filmler"
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = self.cloudscraper.get(f"{url}{page}")
        secici = HTMLParser(istek.text)

        results = []
        for veri in secici.css("li.film"):
            title_el = veri.css_first("span.film-title")
            link_el  = veri.css_first("a")
            img_el   = veri.css_first("img")

            title  = title_el.text(strip=True) if title_el else None
            href   = link_el.attrs.get("href") if link_el else None
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
        istek  = await self.httpx.get(f"{self.main_url}/arama/{query}")
        secici = HTMLParser(istek.text)

        results = []
        for film in secici.css("li.film"):
            title_el = film.css_first("span.film-title")
            link_el  = film.css_first("a")
            img_el   = film.css_first("img")

            title  = title_el.text(strip=True) if title_el else None
            href   = link_el.attrs.get("href") if link_el else None
            poster = img_el.attrs.get("data-src") if img_el else None

            if title and href:
                results.append(SearchResult(
                    title  = title,
                    url    = self.fix_url(href),
                    poster = self.fix_url(poster) if poster else None,
                ))

        return results

    async def load_item(self, url: str) -> MovieInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLParser(istek.text)
        html_text = istek.text

        # Title: normalize-space yerine doğrudan class ile
        title_el = secici.css_first("div.izle-titles")
        title    = title_el.text(strip=True) if title_el else ""

        img_el = secici.css_first("div img[data-src]")
        poster = img_el.attrs.get("data-src", "").strip() if img_el else ""

        desc_el     = secici.css_first("div.ozet-ic p")
        description = desc_el.text(strip=True) if desc_el else ""

        tags = [a.text(strip=True) for a in secici.css("a[rel='category tag']") if a.text(strip=True)]

        # Rating: normalize-space yerine doğrudan class ile ve son kelimeyi al
        rating_el = secici.css_first("div.puanx-puan")
        rating = None
        if rating_el:
            rating_text = rating_el.text(strip=True)
            if rating_text:
                parts = rating_text.split()
                rating = parts[-1] if parts else None

        # Year: ilk yıl formatında değer
        year_el = secici.css_first("div.dd a.category")
        year = None
        if year_el:
            year_text = year_el.text(strip=True)
            if year_text:
                parts = year_text.split()
                year = parts[0] if parts else None

        # Actors: nth-child yerine tüm li'leri alıp 2. index
        lis = secici.css("div.film-info ul li")
        actors = []
        if len(lis) >= 2:
            actors = [a.text(strip=True) for a in lis[1].css("a > span") if a.text(strip=True)]

        duration_el = secici.css_first("span.sure")
        duration = "0"
        if duration_el:
            duration_text = duration_el.text(strip=True)
            duration_parts = duration_text.split()
            duration = duration_parts[0] if duration_parts else "0"

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster) if poster else None,
            title       = title,
            description = description,
            tags        = tags,
            rating      = rating,
            year        = year,
            actors      = actors,
            duration    = duration
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        secici = HTMLParser(istek.text)
        html_text = istek.text

        # İlk script'i al (xpath (//script)[1] yerine)
        scripts = secici.css("script")
        script_content = scripts[0].text() if scripts else ""

        scx_match = re.search(r"scx = (.*?);", script_content)
        if not scx_match:
            return []

        scx_data = json.loads(scx_match.group(1))
        scx_keys = list(scx_data.keys())

        link_list = []
        for key in scx_keys:
            t = scx_data[key]["sx"]["t"]
            if isinstance(t, list):
                link_list.extend(StringCodec.decode(elem) for elem in t)
            if isinstance(t, dict):
                link_list.extend(StringCodec.decode(v) for k, v in t.items())

        response = []
        for link in link_list:
            link = f"https:{link}" if link.startswith("//") else link
            data = await self.extract(link)
            if data:
                response.append(data)

        return response