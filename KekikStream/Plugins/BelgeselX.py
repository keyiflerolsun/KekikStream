# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode, ExtractResult, HTMLHelper
from contextlib       import suppress

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
        if not text:
            return ""

        words     = text.split()
        new_words = []

        for word in words:
            # Önce Türkçe karakterleri koruyarak küçült
            # İ -> i, I -> ı
            word = word.replace("İ", "i").replace("I", "ı").lower()

            # Sonra ilk harfi Türkçe kurallarına göre büyüt
            if word:
                if word[0] == "i":
                    word = "İ" + word[1:]
                elif word[0] == "ı":
                    word = "I" + word[1:]
                else:
                    word = word[0].upper() + word[1:]

            new_words.append(word)

        return " ".join(new_words)

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = self.cloudscraper.get(f"{url}{page}")
        secici = HTMLHelper(istek.text)

        results = []
        for container in secici.select("div.gen-movie-contain"):
            poster = secici.select_attr("div.gen-movie-img img", "src", container)
            title  = secici.select_text("div.gen-movie-info h3 a", container)
            href   = secici.select_attr("div.gen-movie-info h3 a", "href", container)

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = self._to_title_case(title),
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster)
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        # Google Custom Search API kullanıyor
        cx = "016376594590146270301:iwmy65ijgrm"

        token_resp = self.cloudscraper.get(f"https://cse.google.com/cse.js?cx={cx}")
        token_text = token_resp.text

        secici  = HTMLHelper(token_text)
        cse_lib = secici.regex_first(r'cselibVersion": "(.*)"')
        cse_tok = secici.regex_first(r'cse_token": "(.*)"')

        if not cse_lib or not cse_tok:
            return []

        search_url = (
            f"https://cse.google.com/cse/element/v1?"
            f"rsz=filtered_cse&num=100&hl=tr&source=gcsc&cselibv={cse_lib}&cx={cx}"
            f"&q={query}&safe=off&cse_tok={cse_tok}&sort=&exp=cc%2Capo&oq={query}"
            f"&callback=google.search.cse.api9969&rurl=https%3A%2F%2Fbelgeselx.com%2F"
        )

        resp      = self.cloudscraper.get(search_url)
        resp_text = resp.text

        secici2 = HTMLHelper(resp_text)
        titles  = secici2.regex_all(r'"titleNoFormatting": "(.*?)"')
        urls    = secici2.regex_all(r'"url": "(.*?)"')
        images  = secici2.regex_all(r'"ogImage": "(.*?)"')

        results = []
        for i, title in enumerate(titles):
            url_val = urls[i] if i < len(urls) else None
            poster  = images[i] if i < len(images) else None

            if not url_val or "diziresimleri" not in url_val:
                if poster and "diziresimleri" in poster:
                    file_name = poster.rsplit("/", 1)[-1]
                    file_name = HTMLHelper(file_name).regex_replace(r"\.(jpe?g|png|webp)$", "")
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
        secici = HTMLHelper(istek.text)

        title       = self._to_title_case(secici.select_text("h2.gen-title"))
        poster      = secici.select_poster("div.gen-tv-show-top img")
        description = secici.select_text("div.gen-single-tv-show-info p")
        tags        = [self._to_title_case(t.rsplit("/", 1)[-1].replace("-", " ")) for t in secici.select_attrs("div.gen-socail-share a[href*='belgeselkanali']", "href")]

        # Meta bilgilerinden yıl ve puanı çıkar
        meta_items = secici.select_texts("div.gen-single-meta-holder ul li")
        year   = None
        rating = None
        for item in meta_items:
            if not year:
                if y_match := secici.regex_first(r"\b((?:19|20)\d{2})\b", item):
                    year = int(y_match)
            if not rating:
                if r_match := secici.regex_first(r"%\s*(\d+)\s*Puan", item):
                    rating = float(r_match) / 10
        rating = rating or None

        episodes = []
        for i, ep in enumerate(secici.select("div.gen-movie-contain")):
            name    = secici.select_text("div.gen-movie-info h3 a", ep)
            href    = secici.select_attr("div.gen-movie-info h3 a", "href", ep)
            item_id = secici.select_attr("div.gen-movie-info h3 a", "id", ep)
            if name and href:
                s, e = secici.extract_season_episode(secici.select_text("div.gen-single-meta-holder ul li", ep))
                # ID'yi URL'ye ekle ki load_links doğru bölümü çekebilsin
                final_url = self.fix_url(href)
                if item_id:
                    final_url = f"{final_url}?id={item_id}"

                episodes.append(Episode(
                    season  = s or 1,
                    episode = e or (i + 1),
                    title   = name,
                    url     = final_url
                ))

        return SeriesInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title,
            description = description,
            tags        = tags,
            year        = year,
            rating      = rating,
            episodes    = episodes
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        # URL'den ID'yi ayıkla
        params     = dict([x.split('=') for x in url.split('?')[-1].split('&')]) if '?' in url else {}
        episode_id = params.get('id')
        main_url   = url.split('?')[0]

        istek  = await self.httpx.get(main_url)
        secici = HTMLHelper(istek.text)

        if not episode_id:
            episode_id = secici.regex_first(r'data-episode=["\'](\d+)["\']')

        if not episode_id:
            return []

        iframe_resp = await self.httpx.get(f"{self.main_url}/video/data/new4.php?id={episode_id}", headers={"Referer": main_url})
        secici      = HTMLHelper(iframe_resp.text)

        links  = []
        files  = secici.regex_all(r'file:"([^"]+)"')
        labels = secici.regex_all(r'label: "([^"]+)"')

        for i, video_url in enumerate(files):
            quality = labels[i] if i < len(labels) else "HD"
            name    = f"{'Google' if 'google' in video_url.lower() or 'blogspot' in video_url.lower() or quality == 'FULL' else self.name} | {'1080p' if quality == 'FULL' else quality}"

            # belgeselx.php redirect'ini çöz
            if "belgeselx.php" in video_url or "belgeselx2.php" in video_url:
                with suppress(Exception):
                    # HEAD isteği ile lokasyonu alalım
                    resp      = await self.httpx.head(video_url, headers={"Referer": main_url}, follow_redirects=True)
                    video_url = str(resp.url)

            links.append(ExtractResult(
                url     = video_url,
                name    = name,
                referer = main_url
            ))

        return links
