# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, ExtractResult, HTMLHelper
import re
from json import loads
from urllib.parse import unquote

class Filmatek(PluginBase):
    name        = "Filmatek"
    language    = "tr"
    main_url    = "https://filmatek.net"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Sosyalizmin Sineması Veritabanı"

    # Main page categories
    main_page = {
        f"{main_url}/tur/aile/page"             : "Aile",
        f"{main_url}/tur/aksiyon/page"          : "Aksiyon",
        f"{main_url}/tur/animasyon/page"        : "Animasyon",
        f"{main_url}/tur/bilim-kurgu/page"      : "Bilim Kurgu",
        f"{main_url}/tur/komedi/page"           : "Komedi",
        f"{main_url}/tur/korku/page"            : "Korku",
        f"{main_url}/tur/macera/page"           : "Macera",
        f"{main_url}/tur/romantik/page"         : "Romantik",
        f"{main_url}/tur/suc/page"              : "Suç",
        f"{main_url}/tur/yerli-filmler/page"    : "Yerli Filmler",
        f"{main_url}/film-arsivi/page"          : "Tüm Filmler",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        target_url = f"{url}/{page}/"
        istek = await self.httpx.get(target_url)
        helper = HTMLHelper(istek.text)

        items = helper.select("div.items article, #archive-content article")
        results = []

        for item in items:
            title_el = helper.select_first("div.data h3 a, h3 a", item)
            if not title_el: continue

            title = title_el.text(strip=True)
            href = self.fix_url(title_el.attrs.get("href"))
            
            img_el = helper.select_first("img", item)
            poster = self.fix_url(img_el.attrs.get("data-src") or img_el.attrs.get("src")) if img_el else None

            results.append(MainPageResult(
                category = category,
                title    = title,
                url      = href,
                poster   = poster
            ))
            
        return results

    async def search(self, query: str) -> list[SearchResult]:
        url = f"{self.main_url}/?s={query}"
        istek = await self.httpx.get(url)
        helper = HTMLHelper(istek.text)

        items = helper.select("div.result-item")
        results = []

        for item in items:
            title_el = helper.select_first("div.title a", item)
            if not title_el: continue

            title = title_el.text(strip=True)
            href = self.fix_url(title_el.attrs.get("href"))
            
            img_el = helper.select_first("div.image img", item)
            poster = self.fix_url(img_el.attrs.get("src")) if img_el else None

            results.append(SearchResult(
                title  = title,
                url    = href,
                poster = poster
            ))

        return results

    async def load_item(self, url: str) -> MovieInfo:
        istek  = await self.httpx.get(url)
        helper = HTMLHelper(istek.text)

        title       = self.clean_title(helper.select_text("div.data h1, h1"))
        poster      = helper.select_poster("div.poster img") or helper.select_attr("meta[property='og:image']", "content")
        description = helper.select_text("div.wp-content p") or helper.select_attr("meta[property='og:description']", "content")
        year        = helper.extract_year("span.date")
        rating      = helper.select_text("span.dt_rating_vgs") or helper.select_text("span.dt_rating_vmanual")
        duration    = helper.regex_first(r"(\d+)", helper.select_text("span.runtime"))
        tags        = helper.select_texts("div.sgeneros a")
        actors      = helper.select_texts("div.person div.name a")

        return MovieInfo(
            url         = url,
            title       = title or "Bilinmiyor",
            description = description,
            poster      = self.fix_url(poster) if poster else None,
            year        = str(year) if year else None,
            rating      = rating,
            duration    = int(duration) if duration else None,
            tags        = tags,
            actors      = actors
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek = await self.httpx.get(url)
        html = istek.text
        helper = HTMLHelper(html)

        # Get Post ID from body class usually "postid-123"
        body_class = helper.select_attr("body", "class") or ""
        post_id_match = re.search(r"postid-(\d+)", body_class)
        
        results = []
        
        if post_id_match:
            post_id = post_id_match.group(1)
            
            # AJAX request for player
            ajax_url = f"{self.main_url}/wp-admin/admin-ajax.php"
            data = {
                "action": "doo_player_ajax",
                "post": post_id,
                "nume": "1", # Usually implies source number 1? Kotlin uses "1" hardcoded.
                "type": "movie"
            }
            
            headers = {
                "X-Requested-With": "XMLHttpRequest",
                "Referer": url,
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            try:
                # Need to use post with data
                player_resp = await self.httpx.post(ajax_url, data=data, headers=headers)
                
                # Kotlin parses it as text and cleans slashes
                content = player_resp.text.replace(r"\/", "/")
                
                # Regex for URL
                # Kotlin: (?:src|url)["']?\s*[:=]\s*["']([^"']+)["']
                src_match = re.search(r'(?:src|url)["\']?\s*[:=]\s*["\']([^"\']+)["\']', content)
                
                if src_match:
                    iframe_url = src_match.group(1)
                    if iframe_url.startswith("/"):
                        iframe_url = self.main_url + iframe_url
                        
                    iframe_url = self.fix_url(iframe_url)
                    
                    # Unwrap internal JWPlayer
                    if "jwplayer/?source=" in iframe_url:
                        try:
                            raw_source = iframe_url.split("source=")[1].split("&")[0]
                            iframe_url = unquote(raw_source)
                        except:
                            pass
                    
                    extracted = await self.extract(iframe_url)
                    if extracted:
                        if isinstance(extracted, list):
                            results.extend(extracted)
                        else:
                            results.append(extracted)
                    else:
                        results.append(ExtractResult(
                            name = "Filmatek | External",
                            url  = iframe_url,
                            referer = url
                        ))
            except Exception as e:
                # print(f"Filmatek Error: {e}")
                pass

        return results
