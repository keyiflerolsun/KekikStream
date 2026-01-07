# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode, Subtitle, ExtractResult
from selectolax.parser import HTMLParser
import re

class DiziYou(PluginBase):
    name        = "DiziYou"
    language    = "tr"
    main_url    = "https://www.diziyou.one"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Diziyou en kaliteli Türkçe dublaj ve altyazılı yabancı dizi izleme sitesidir. Güncel ve efsanevi dizileri 1080p Full HD kalitede izlemek için hemen tıkla!"

    main_page   = {
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur=Aile"                 : "Aile",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur=Aksiyon"              : "Aksiyon",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur=Animasyon"            : "Animasyon",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur=Belgesel"             : "Belgesel",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur=Bilim+Kurgu"          : "Bilim Kurgu",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur=Dram"                 : "Dram",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur=Fantazi"              : "Fantazi",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur=Gerilim"              : "Gerilim",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur=Gizem"                : "Gizem",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur=Komedi"               : "Komedi",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur=Korku"                : "Korku",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur=Macera"               : "Macera",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur=Sava%C5%9F"           : "Savaş",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur=Su%C3%A7"             : "Suç",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur=Vah%C5%9Fi+Bat%C4%B1" : "Vahşi Batı"
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.httpx.get(f"{url.replace('SAYFA', str(page))}")
        secici = HTMLParser(istek.text)

        results = []
        for veri in secici.css("div.single-item"):
            title_el = veri.css_first("div#categorytitle a")
            img_el   = veri.css_first("img")

            title  = title_el.text(strip=True) if title_el else None
            href   = title_el.attrs.get("href") if title_el else None
            poster = img_el.attrs.get("src") if img_el else None

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title,
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster) if poster else None,
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}/?s={query}")
        secici = HTMLParser(istek.text)

        results = []
        for afis in secici.css("div.incontent div#list-series"):
            title_el = afis.css_first("div#categorytitle a")
            img_el   = afis.css_first("img")

            title  = title_el.text(strip=True) if title_el else None
            href   = title_el.attrs.get("href") if title_el else None
            poster = (img_el.attrs.get("src") or img_el.attrs.get("data-src")) if img_el else None

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
        html_text = istek.text

        # Title - div.title h1 içinde
        title_el = secici.css_first("div.title h1")
        title    = title_el.text(strip=True) if title_el else ""
        
        # Fallback: Eğer title boşsa URL'den çıkar (telif kısıtlaması olan sayfalar için)
        if not title:
            # URL'den slug'ı al: https://www.diziyou.one/jasmine/ -> jasmine -> Jasmine
            slug = url.rstrip('/').split('/')[-1]
            title = slug.replace('-', ' ').title()
        
        # Poster
        poster_el = secici.css_first("div.category_image img")
        poster    = self.fix_url(poster_el.attrs.get("src")) if poster_el else ""

        # Year - regex ile çıkarma (xpath yerine)
        year = None
        year_match = re.search(r"Yapım Yılı.*?(\d{4})", html_text, re.DOTALL | re.IGNORECASE)
        if year_match:
            year = year_match.group(1)

        desc_el = secici.css_first("div.diziyou_desc")
        description = None
        if desc_el:
            # HTML'i al ve script + meta div'lerini temizle
            desc_html = desc_el.html
            # Script taglarını kaldır
            desc_html = re.sub(r"<script.*?</script>", "", desc_html, flags=re.DOTALL)
            # div#icerikcat2 ve sonrasını kaldır (meta bilgileri içeriyor)
            desc_html = re.sub(r"<div id=\"icerikcat2\".*", "", desc_html, flags=re.DOTALL)
            # Kalan HTML'den text çıkar
            clean_sel = HTMLParser(desc_html)
            description = clean_sel.text(strip=True)

        tags = [a.text(strip=True) for a in secici.css("div.genres a") if a.text(strip=True)]

        # Rating - daha spesifik regex ile
        rating = None
        rating_match = re.search(r"IMDB\s*:\s*</span>([0-9.]+)", html_text, re.DOTALL | re.IGNORECASE)
        if rating_match:
            rating = rating_match.group(1)

        # Actors - regex ile
        actors = []
        actors_match = re.search(r"Oyuncular.*?</span>([^<]+)", html_text, re.DOTALL | re.IGNORECASE)
        if actors_match:
            actors = [actor.strip() for actor in actors_match.group(1).split(",") if actor.strip()]

        episodes = []
        # Episodes - bolumust div içeren a linklerini bul
        for link in secici.css("a"):
            bolumust = link.css_first("div.bolumust")
            if not bolumust:
                continue

            baslik_el = link.css_first("div.baslik")
            if not baslik_el:
                continue

            ep_name = baslik_el.text(strip=True)
            ep_href = link.attrs.get("href")
            if not ep_href:
                continue

            # Bölüm ismi varsa al
            bolumismi_el = link.css_first("div.bolumismi")
            ep_name_clean = bolumismi_el.text(strip=True).replace("(", "").replace(")", "").strip() if bolumismi_el else ep_name

            ep_episode_match = re.search(r"(\d+)\. Bölüm", ep_name)
            ep_season_match  = re.search(r"(\d+)\. Sezon", ep_name)

            ep_episode = ep_episode_match.group(1) if ep_episode_match else None
            ep_season  = ep_season_match.group(1) if ep_season_match else None

            if ep_episode and ep_season:
                episode = Episode(
                    season  = ep_season,
                    episode = ep_episode,
                    title   = ep_name_clean,
                    url     = self.fix_url(ep_href),
                )
                episodes.append(episode)

        return SeriesInfo(
            url         = url,
            poster      = poster,
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

        # Title ve episode name - None kontrolü ekle
        title_el = secici.css_first("div.title h1")
        item_title = title_el.text(strip=True) if title_el else ""
        
        ep_name_el = secici.css_first("div#bolum-ismi")
        ep_name = ep_name_el.text(strip=True) if ep_name_el else ""
        
        # Player src'den item_id çıkar
        player_el = secici.css_first("iframe#diziyouPlayer")
        player_src = player_el.attrs.get("src") if player_el else None
        if not player_src:
            return []  # Player bulunamadıysa boş liste döndür
        
        item_id = player_src.split("/")[-1].replace(".html", "")

        subtitles   = []
        stream_urls = []

        for secenek in secici.css("span.diziyouOption"):
            opt_id  = secenek.attrs.get("id")
            op_name = secenek.text(strip=True)

            match opt_id:
                case "turkceAltyazili":
                    subtitles.append(Subtitle(
                        name = op_name,
                        url  = self.fix_url(f"{self.main_url.replace('www', 'storage')}/subtitles/{item_id}/tr.vtt"),
                    ))
                    veri = {
                        "dil": "Orjinal Dil (TR Altyazı)",
                        "url": f"{self.main_url.replace('www', 'storage')}/episodes/{item_id}/play.m3u8"
                    }
                    if veri not in stream_urls:
                        stream_urls.append(veri)
                case "ingilizceAltyazili":
                    subtitles.append(Subtitle(
                        name = op_name,
                        url  = self.fix_url(f"{self.main_url.replace('www', 'storage')}/subtitles/{item_id}/en.vtt"),
                    ))
                    veri = {
                        "dil": "Orjinal Dil (EN Altyazı)",
                        "url": f"{self.main_url.replace('www', 'storage')}/episodes/{item_id}/play.m3u8"
                    }
                    if veri not in stream_urls:
                        stream_urls.append(veri)
                case "turkceDublaj":
                    stream_urls.append({
                        "dil": "Türkçe Dublaj",
                        "url": f"{self.main_url.replace('www', 'storage')}/episodes/{item_id}_tr/play.m3u8"
                    })

        results = []
        for stream in stream_urls:
            results.append(ExtractResult(
                url       = stream.get("url"),
                name      = f"{stream.get('dil')}",
                referer   = url,
                subtitles = subtitles
            ))

        return results