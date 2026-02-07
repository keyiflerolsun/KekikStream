# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, ExtractResult, HTMLHelper
import asyncio

class JetFilmizle(PluginBase):
    name        = "JetFilmizle"
    language    = "tr"
    main_url    = "https://jetfilmizle.net"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Film izle, Yerli, Yabancı film izle, Türkçe dublaj, alt yazılı seçenekleriyle ödül almış filmleri Full HD kalitesiyle ve jetfilmizle hızıyla donmadan ücretsizce izleyebilirsiniz."

    main_page   = {
        f"{main_url}/page/"                                     : "Son Filmler",
        f"{main_url}/netflix/page/"                             : "Netflix",
        f"{main_url}/editorun-secimi/page/"                     : "Editörün Seçimi",
        f"{main_url}/turk-film-izle/page/"                      : "Türk Filmleri",
        f"{main_url}/cizgi-filmler-izle/page/"                  : "Çizgi Filmler",
        f"{main_url}/kategoriler/yesilcam-filmleri-izlee/page/" : "Yeşilçam Filmleri",
        f"{main_url}/film-turu/aile-filmleri-izle/page/"        : "Aile Filmleri",
        f"{main_url}/film-turu/aksiyon-filmleri/page/"          : "Aksiyon Filmleri",
        f"{main_url}/film-turu/animasyon-filmler-izle/page/"    : "Animasyon Filmleri",
        f"{main_url}/film-turu/bilim-kurgu-filmler/page/"       : "Bilim Kurgu Filmleri",
        f"{main_url}/film-turu/dram-filmleri-izle/page/"        : "Dram Filmleri",
        f"{main_url}/film-turu/fantastik-filmleri-izle/page/"   : "Fantastik Filmler",
        f"{main_url}/film-turu/gerilim-filmleri/page/"          : "Gerilim Filmleri",
        f"{main_url}/film-turu/gizem-filmleri/page/"            : "Gizem Filmleri",
        f"{main_url}/film-turu/komedi-film-full-izle/page/"     : "Komedi Filmleri",
        f"{main_url}/film-turu/korku-filmleri-izle/page/"       : "Korku Filmleri",
        f"{main_url}/film-turu/macera-filmleri/page/"           : "Macera Filmleri",
        f"{main_url}/film-turu/muzikal/page/"                   : "Müzikal Filmler",
        f"{main_url}/film-turu/polisiye/page/"                  : "Polisiye Filmler",
        f"{main_url}/film-turu/romantik-film-izle/page/"        : "Romantik Filmler",
        f"{main_url}/film-turu/savas-filmi-izle/page/"          : "Savaş Filmleri",
        f"{main_url}/film-turu/spor/page/"                      : "Spor Filmleri",
        f"{main_url}/film-turu/suc-filmleri/page/"              : "Suç Filmleri",
        f"{main_url}/film-turu/tarihi-filmler/page/"            : "Tarihi Filmleri",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.httpx.get(f"{url}{page}", follow_redirects=True)
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("article.movie"):
            title_text = None
            for h_tag in ["h2", "h3", "h4", "h5", "h6"]:
                title_text = secici.select_text(f"{h_tag} a", veri)
                if title_text:
                    break

            title  = self.clean_title(title_text) if title_text else None
            href   = secici.select_attr("a", "href", veri)
            poster = secici.select_poster("img", veri)

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title,
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster),
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.post(
            url     = f"{self.main_url}/filmara.php",
            data    = {"s": query},
            headers = {"Referer": f"{self.main_url}/"}
        )
        secici = HTMLHelper(istek.text)

        results = []
        for article in secici.select("article.movie"):
            title_text = None
            for h_tag in ["h2", "h3", "h4", "h5", "h6"]:
                title_text = secici.select_text(f"{h_tag} a", article)
                if title_text:
                    break

            title  = self.clean_title(title_text) if title_text else None
            href   = secici.select_attr("a", "href", article)
            poster = secici.select_poster("img", article)

            if title and href:
                results.append(SearchResult(
                    title  = title,
                    url    = self.fix_url(href),
                    poster = self.fix_url(poster),
                ))

        return results

    async def load_item(self, url: str) -> MovieInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        title       = self.clean_title(secici.select_text("div.movie-exp-title"))
        poster      = secici.select_poster("section.movie-exp img")
        description = secici.select_text("section.movie-exp p.aciklama")
        tags        = secici.select_texts("section.movie-exp div.catss a")
        rating      = secici.select_text("section.movie-exp div.imdb_puan span")
        year        = secici.meta_value("Yayın Yılı")
        actors      = secici.select_texts("div[itemprop='actor'] a span") or [img.attrs.get("alt") for img in secici.select("div.oyuncular div.oyuncu img") if img.attrs.get("alt")]
        duration    = secici.meta_value("Süre")
        duration    = duration.split() if duration else None

        total_minutes = 0
        if duration:
            for i, p in enumerate(duration):
                if p == "saat":
                    total_minutes += int(duration[i-1]) * 60
                elif p == "dakika":
                    total_minutes += int(duration[i-1])

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title,
            description = description,
            tags        = tags,
            rating      = rating,
            year        = year,
            actors      = actors,
            duration    = total_minutes if total_minutes else None
        )

    async def _process_source(self, url: str, name: str, html: str | None) -> list[ExtractResult]:
        results = []
        try:
            if html:
                secici = HTMLHelper(html)
            else:
                resp   = await self.httpx.get(url)
                secici = HTMLHelper(resp.text)

            # Iframe'leri bul
            container = secici.select_first("div#movie") or secici.select_first("div.film-content")

            if container:
                for iframe in secici.select("iframe", container):
                    src = (iframe.attrs.get("src") or
                           iframe.attrs.get("data-src") or
                           iframe.attrs.get("data-lazy-src"))

                    if src and src != "about:blank":
                        iframe_url = self.fix_url(src)
                        # name_override KULLANMA, extractor kendi ismini versin
                        # Sonra biz düzenleriz
                        data = await self.extract(iframe_url)

                        if data:
                            items = data if isinstance(data, list) else [data]

                            for item in items:
                                # Sadece kalite bilgisi içeriyorsa ekle, yoksa sadece buton adını kullan
                                # Özellikle Zeus için kalite önemli (1080p, 720p)
                                # Diğerlerinde plugin adı (Apollo, JetPlay vb.) önemsiz

                                # Kalite kontrolü (basitçe)
                                quality_indicators = ["1080p", "720p", "480p", "360p", "240p", "144p", "4k", "2k"]
                                has_quality = any(q in item.name.lower() for q in quality_indicators)

                                if has_quality:
                                    # Buton Adı | Extractor Adı (Kalite içerdiği için)
                                    # Örn: Zeus | 1080p
                                    # Eğer Extractor adı zaten Buton adını içeriyorsa (Zeus | 1080p -> Zeus) tekrar ekleme
                                    if name.lower() not in item.name.lower():
                                         item.name = f"{name} | {item.name}"
                                else:
                                    # Kalite yoksa sadece Buton adını kullan
                                    # Örn: Apollo | JetTv -> JetTv
                                    item.name = name

                                results.append(item)
            return results
        except Exception:
            return []

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        sources = []
        if film_part := secici.select_first("div.film_part"):
            # Tüm spanları gez
            for span in secici.select("span", film_part):
                # Eğer bu span bir <a> etiketi içinde değilse, aktif kaynaktır
                if span.parent.tag != "a":
                    name = span.text(strip=True)
                    if name:
                        sources.append((url, name, istek.text)) # html content var
                        break

            # Diğer kaynak linkleri
            for link in secici.select("a.post-page-numbers", film_part):
                name = secici.select_text("span", link) or link.text(strip=True)
                href = link.attrs.get("href")
                if name != "Fragman" and href:
                    sources.append((self.fix_url(href), name, None)) # html yok, çekilecek

        # Eğer film_part yoksa, sadece mevcut sayfayı tara (Tek part olabilir)
        if not sources:
            sources.append((url, "JetFilmizle", istek.text))

        tasks = []
        for page_url, source_name, html_content in sources:
            tasks.append(self._process_source(page_url, source_name, html_content))

        return [item for sublist in await asyncio.gather(*tasks) for item in sublist]
