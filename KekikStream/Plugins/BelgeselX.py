# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode, ExtractResult
from parsel           import Selector
import re

class BelgeselX(PluginBase):
    name        = "BelgeselX"
    language    = "tr"
    main_url    = "https://belgeselx.com"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "2022 yılında son çıkan belgeselleri belgeselx.com'da izle. En yeni belgeseller, türkçe altyazılı yada dublaj olarak 1080p kalitesinde hd belgesel izle."

    main_page   = {
        f"{main_url}/konu/turk-tarihi-belgeselleri&page=" : "Türk Tarihi",
        f"{main_url}/konu/tarih-belgeselleri&page="       : "Tarih",
        f"{main_url}/konu/seyehat-belgeselleri&page="     : "Seyahat",
        f"{main_url}/konu/seri-belgeseller&page="         : "Seri",
        f"{main_url}/konu/savas-belgeselleri&page="       : "Savaş",
        f"{main_url}/konu/sanat-belgeselleri&page="       : "Sanat",
        f"{main_url}/konu/psikoloji-belgeselleri&page="   : "Psikoloji",
        f"{main_url}/konu/polisiye-belgeselleri&page="    : "Polisiye",
        f"{main_url}/konu/otomobil-belgeselleri&page="    : "Otomobil",
        f"{main_url}/konu/nazi-belgeselleri&page="        : "Nazi",
        f"{main_url}/konu/muhendislik-belgeselleri&page=" : "Mühendislik",
        f"{main_url}/konu/kultur-din-belgeselleri&page="  : "Kültür Din",
        f"{main_url}/konu/kozmik-belgeseller&page="       : "Kozmik",
        f"{main_url}/konu/hayvan-belgeselleri&page="      : "Hayvan",
        f"{main_url}/konu/eski-tarih-belgeselleri&page="  : "Eski Tarih",
        f"{main_url}/konu/egitim-belgeselleri&page="      : "Eğitim",
        f"{main_url}/konu/dunya-belgeselleri&page="       : "Dünya",
        f"{main_url}/konu/doga-belgeselleri&page="        : "Doğa",
        f"{main_url}/konu/bilim-belgeselleri&page="       : "Bilim"
    }

    @staticmethod
    def _to_title_case(text: str) -> str:
        """Türkçe için title case dönüşümü."""
        return " ".join(
            word.lower().replace("i", "İ").capitalize() if word.lower().startswith("i") else word.capitalize()
            for word in text.split()
        )

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = self.cloudscraper.get(f"{url}{page}")
        secici = Selector(istek.text)

        results = []
        for item in secici.css("div.gen-movie-contain > div.gen-info-contain > div.gen-movie-info"):
            title  = item.css("div.gen-movie-info > h3 a::text").get()
            href   = item.css("div.gen-movie-info > h3 a::attr(href)").get()
            parent = item.xpath("../../..")
            poster = parent.css("div.gen-movie-img > img::attr(src)").get()

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = self._to_title_case(title.strip()),
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster) if poster else None
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        # Google Custom Search API kullanıyor
        cx = "016376594590146270301:iwmy65ijgrm"

        token_resp = self.cloudscraper.get(f"https://cse.google.com/cse.js?cx={cx}")
        token_text = token_resp.text

        cse_lib_match = re.search(r'cselibVersion": "(.*)"', token_text)
        cse_tok_match = re.search(r'cse_token": "(.*)"', token_text)

        if not cse_lib_match or not cse_tok_match:
            return []

        cse_lib = cse_lib_match.group(1)
        cse_tok = cse_tok_match.group(1)

        search_url = (
            f"https://cse.google.com/cse/element/v1?"
            f"rsz=filtered_cse&num=100&hl=tr&source=gcsc&cselibv={cse_lib}&cx={cx}"
            f"&q={query}&safe=off&cse_tok={cse_tok}&sort=&exp=cc%2Capo&oq={query}"
            f"&callback=google.search.cse.api9969&rurl=https%3A%2F%2Fbelgeselx.com%2F"
        )

        resp = self.cloudscraper.get(search_url)
        resp_text = resp.text

        titles = re.findall(r'"titleNoFormatting": "(.*?)"', resp_text)
        urls   = re.findall(r'"url": "(.*?)"', resp_text)
        images = re.findall(r'"ogImage": "(.*?)"', resp_text)

        results = []
        for i, title in enumerate(titles):
            url_val = urls[i] if i < len(urls) else None
            poster  = images[i] if i < len(images) else None

            if not url_val or "diziresimleri" not in url_val:
                # URL'den belgesel linkini oluştur
                if poster and "diziresimleri" in poster:
                    file_name = poster.rsplit("/", 1)[-1]
                    file_name = re.sub(r"\.(jpe?g|png|webp)$", "", file_name)
                    url_val = f"{self.main_url}/belgeseldizi/{file_name}"
                else:
                    continue

            clean_title = title.split("İzle")[0].strip()
            results.append(SearchResult(
                title  = self._to_title_case(clean_title),
                url    = url_val,
                poster = poster
            ))

        return results

    async def load_item(self, url: str) -> SeriesInfo:
        istek  = await self.httpx.get(url)
        secici = Selector(istek.text)

        title       = secici.css("h2.gen-title::text").get()
        poster      = secici.css("div.gen-tv-show-top img::attr(src)").get()
        description = secici.css("div.gen-single-tv-show-info p::text").get()

        tags = []
        for tag_link in secici.css("div.gen-socail-share a[href*='belgeselkanali']"):
            tag_href = tag_link.css("::attr(href)").get()
            if tag_href:
                tag_name = tag_href.rsplit("/", 1)[-1].replace("-", " ")
                tags.append(self._to_title_case(tag_name))

        episodes = []
        counter  = 0
        for ep_item in secici.css("div.gen-movie-contain"):
            ep_name = ep_item.css("div.gen-movie-info h3 a::text").get()
            ep_href = ep_item.css("div.gen-movie-info h3 a::attr(href)").get()

            if not ep_name or not ep_href:
                continue

            season_text   = ep_item.css("div.gen-single-meta-holder ul li::text").get() or ""
            episode_match = re.search(r"Bölüm (\d+)", season_text)
            season_match  = re.search(r"Sezon (\d+)", season_text)

            ep_episode = int(episode_match.group(1)) if episode_match else counter
            ep_season  = int(season_match.group(1)) if season_match else 1

            counter += 1

            episodes.append(Episode(
                season  = ep_season,
                episode = ep_episode,
                title   = ep_name.strip(),
                url     = self.fix_url(ep_href)
            ))

        return SeriesInfo(
            url         = url,
            poster      = self.fix_url(poster) if poster else None,
            title       = self._to_title_case(title.strip()) if title else None,
            description = description.strip() if description else None,
            tags        = tags,
            episodes    = episodes
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek = await self.httpx.get(url)
        text  = istek.text

        # fnc_addWatch div'inden data-episode ID'sini al
        ep_match = re.search(r'<div[^>]*class=["\'][^"\']*fnc_addWatch[^"\']*["\'][^>]*data-episode=["\'](\d+)["\']', text)
        if not ep_match:
            return []

        episode_id  = ep_match.group(1)
        iframe_url  = f"{self.main_url}/video/data/new4.php?id={episode_id}"

        iframe_resp = await self.httpx.get(iframe_url, headers={"Referer": url})
        iframe_text = iframe_resp.text

        links = []
        for match in re.finditer(r'file:"([^"]+)", label: "([^"]+)"', iframe_text):
            video_url = match.group(1)
            quality   = match.group(2)

            source_name = "Google" if quality == "FULL" else self.name
            quality_str = "1080p" if quality == "FULL" else quality

            links.append(ExtractResult(
                url     = video_url,
                name    = f"{source_name} | {quality_str}",
                referer = url
            ))

        return links
