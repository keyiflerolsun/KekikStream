# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import PluginBase, MainPageResult, SearchResult, MovieInfo, ExtractResult
from selectolax.parser import HTMLParser
import re

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
        secici = HTMLParser(istek.text)

        results = []
        for veri in secici.css("article.movie"):
            # h2-h6 içindeki a linki
            title_link = None
            for h_tag in ["h2", "h3", "h4", "h5", "h6"]:
                title_link = veri.css_first(f"{h_tag} a")
                if title_link:
                    break

            link_el = veri.css_first("a")
            img_el  = veri.css_first("img")

            title  = self.clean_title(title_link.text(strip=True)) if title_link else None
            href   = link_el.attrs.get("href") if link_el else None
            poster = (img_el.attrs.get("data-src") or img_el.attrs.get("src")) if img_el else None

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
        secici = HTMLParser(istek.text)

        results = []
        for article in secici.css("article.movie"):
            # h2-h6 içindeki a linki
            title_link = None
            for h_tag in ["h2", "h3", "h4", "h5", "h6"]:
                title_link = article.css_first(f"{h_tag} a")
                if title_link:
                    break

            link_el = article.css_first("a")
            img_el  = article.css_first("img")

            title  = self.clean_title(title_link.text(strip=True)) if title_link else None
            href   = link_el.attrs.get("href") if link_el else None
            poster = (img_el.attrs.get("data-src") or img_el.attrs.get("src")) if img_el else None

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

        title_el = secici.css_first("div.movie-exp-title")
        title    = self.clean_title(title_el.text(strip=True)) if title_el else None

        img_el     = secici.css_first("section.movie-exp img")
        poster_raw = (img_el.attrs.get("data-src") or img_el.attrs.get("src")) if img_el else None
        poster     = poster_raw.strip() if poster_raw else None
        
        desc_el = secici.css_first("section.movie-exp p.aciklama")
        description = desc_el.text(strip=True) if desc_el else None
        
        tags = [a.text(strip=True) for a in secici.css("section.movie-exp div.catss a") if a.text(strip=True)]
        
        rating_el = secici.css_first("section.movie-exp div.imdb_puan span")
        rating    = rating_el.text(strip=True) if rating_el else None
        
        # Year - div.yap içinde 4 haneli sayı ara (xpath yerine regex)
        year = None
        yap_match = re.search(r'<div class="yap"[^>]*>([^<]*(?:Vizyon|Yapım)[^<]*)</div>', html_text, re.IGNORECASE)
        if yap_match:
            year_match = re.search(r'(\d{4})', yap_match.group(1))
            if year_match:
                year = year_match.group(1)
        
        actors = [a.text(strip=True) for a in secici.css("div[itemprop='actor'] a span") if a.text(strip=True)]

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster) if poster else None,
            title       = title,
            description = description,
            tags        = tags,
            rating      = rating,
            year        = year,
            actors      = actors
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        secici = HTMLParser(istek.text)

        results = []

        # 1) Ana iframe'leri kontrol et
        for iframe in secici.css("iframe"):
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
        for link in secici.css("a.post-page-numbers"):
            span_el = link.css_first("span")
            isim = span_el.text(strip=True) if span_el else ""
            if isim != "Fragman":
                href = link.attrs.get("href")
                if href:
                    page_links.append((self.fix_url(href), isim))

        # 3) Her sayfa linkindeki iframe'leri bul
        for page_url, isim in page_links:
            try:
                page_resp = await self.httpx.get(page_url)
                page_sel = HTMLParser(page_resp.text)
                
                for iframe in page_sel.css("div#movie iframe"):
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
