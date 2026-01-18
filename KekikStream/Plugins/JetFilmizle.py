# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import PluginBase, MainPageResult, SearchResult, MovieInfo, ExtractResult, HTMLHelper

class JetFilmizle(PluginBase):
    name        = "JetFilmizle"
    language    = "tr"
    main_url    = "https://jetfilmizle.website"
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
            # h2-h6 içindeki a linki
            title_text = None
            for h_tag in ["h2", "h3", "h4", "h5", "h6"]:
                title_text = secici.select_text(f"{h_tag} a", veri)
                if title_text:
                    break

            href = secici.select_attr("a", "href", veri)
            poster = secici.select_poster("img", veri)

            title  = self.clean_title(title_text) if title_text else None

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title,
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster) if poster else None,
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
            # h2-h6 içindeki a linki
            title_text = None
            for h_tag in ["h2", "h3", "h4", "h5", "h6"]:
                title_text = secici.select_text(f"{h_tag} a", article)
                if title_text:
                    break

            href = secici.select_attr("a", "href", article)
            poster = secici.select_poster("img", article)

            title  = self.clean_title(title_text) if title_text else None

            if title and href:
                results.append(SearchResult(
                    title  = title,
                    url    = self.fix_url(href),
                    poster = self.fix_url(poster) if poster else None,
                ))

        return results

    async def load_item(self, url: str) -> MovieInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        title    = self.clean_title(secici.select_text("div.movie-exp-title")) if secici.select_text("div.movie-exp-title") else None

        poster = secici.select_poster("section.movie-exp img")
        poster = poster.strip() if poster else None
        
        description = secici.select_text("section.movie-exp p.aciklama")
        
        tags = secici.select_all_text("section.movie-exp div.catss a")
        
        rating = secici.select_text("section.movie-exp div.imdb_puan span")
        
        year = secici.extract_year("div.yap")
        
        actors = secici.select_all_text("div[itemprop='actor'] a span")
        if not actors: # Fallback to img alt
            actors = [img.attrs.get("alt") for img in secici.select("div.oyuncular div.oyuncu img") if img.attrs.get("alt")]

        duration = secici.regex_first(r"(\d+)\s*dk", istek.text)

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster) if poster else None,
            title       = title,
            description = description,
            tags        = tags,
            rating      = rating,
            year        = year,
            actors      = actors,
            duration    = int(duration) if duration else None
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        results = []

        # 1) Ana iframe'leri kontrol et
        for iframe in secici.select("iframe"):
            src = (iframe.attrs.get("src") or 
                   iframe.attrs.get("data-src") or
                   iframe.attrs.get("data-lazy-src"))
            
            if src and src != "about:blank":
                iframe_url = self.fix_url(src)
                data = await self.extract(iframe_url)
                if data:
                    results.append(data)

        # 2) Sayfa numaralarından linkleri topla (Fragman hariç)
        page_links = []
        for link in secici.select("a.post-page-numbers"):
            isim = secici.select_text("span", link) or ""
            if isim != "Fragman":
                href = link.attrs.get("href")
                if href:
                    page_links.append((self.fix_url(href), isim))

        # 3) Her sayfa linkindeki iframe'leri bul
        for page_url, isim in page_links:
            try:
                page_resp = await self.httpx.get(page_url)
                page_sel = HTMLHelper(page_resp.text)
                
                for iframe in page_sel.select("div#movie iframe"):
                    src = (iframe.attrs.get("src") or 
                           iframe.attrs.get("data-src") or
                           iframe.attrs.get("data-lazy-src"))
                    
                    if src and src != "about:blank":
                        iframe_url = self.fix_url(src)
                        data = await self.extract(iframe_url, prefix=isim)
                        if data:
                            results.append(data)
            except Exception:
                continue

        return results
