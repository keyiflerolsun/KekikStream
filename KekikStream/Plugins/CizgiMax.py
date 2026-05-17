# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode, ExtractResult, HTMLHelper
import re

class CizgiMax(PluginBase):
    name        = "CizgiMax"
    language    = "tr"
    main_url    = "https://cizgimax.online"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "ÇizgiMax ile Çizgi Film izlemek artık daha kolay, donmadan full hd ve reklamsız bir sitedir, içerisinde 500 den fazla çizgi film olan, Bu site bu işi profesyonelce yapıyor."

    main_page   = {
        f"{main_url}/diziler?orderby=date&order=DESC"                                   : "Son Eklenenler",
        f"{main_url}/diziler?s_type&tur[0]=aile&orderby=date&order=DESC"                : "Aile",
        f"{main_url}/diziler?s_type&tur[0]=aksiyon-macera&orderby=date&order=DESC"      : "Aksiyon & Macera",
        f"{main_url}/diziler?s_type&tur[0]=animasyon&orderby=date&order=DESC"           : "Animasyon",
        f"{main_url}/diziler?s_type&tur[0]=belgesel&orderby=date&order=DESC"            : "Belgesel",
        f"{main_url}/diziler?s_type&tur[0]=bilim-kurgu-fantazi&orderby=date&order=DESC" : "Bilim Kurgu & Fantazi",
        f"{main_url}/diziler?s_type&tur[0]=cocuklar&orderby=date&order=DESC"            : "Çocuklar",
        f"{main_url}/diziler?s_type&tur[0]=dram&orderby=date&order=DESC"                : "Dram",
        f"{main_url}/diziler?s_type&tur[0]=gizem&orderby=date&order=DESC"               : "Gizem",
        f"{main_url}/diziler?s_type&tur[0]=komedi&orderby=date&order=DESC"              : "Komedi",
        f"{main_url}/diziler?s_type&tur[0]=pembe-dizi&orderby=date&order=DESC"          : "Pembe Dizi",
        f"{main_url}/diziler?s_type&tur[0]=suc&orderby=date&order=DESC"                 : "Suç",
        f"{main_url}/diziler?s_type&tur[0]=talk&orderby=date&order=DESC"                : "Talk",
        f"{main_url}/diziler?s_type&tur[0]=vahsi-bati&orderby=date&order=DESC"          : "Vahşi Batı",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        page_url = url if page <= 1 else f"{url}/page/{page}"
        # URL'de /diziler varsa ve /page/ ekleniyorsa düzeltme gerekebilir.
        # Sitede /diziler/anime/page/2 gibi bir yapı var.
        if "/diziler" in url and page > 1:
            base     = url.split("?")[0].rstrip("/")
            query    = f"?{url.split('?')[1]}" if "?" in url else ""
            page_url = f"{base}/page/{page}/{query}"

        istek  = await self.async_cf_get(page_url)
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.film-item"):
            title  = veri.select_text("a.film-name")
            href   = veri.select_attr("a.film-name", "href")
            poster = veri.select_attr("a.poster img", "src") or veri.select_attr("a.poster img", "data-src")

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title.strip(),
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster),
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        # AJAX search yerine HTML search kullanıyoruz
        istek  = await self.async_cf_get(f"{self.main_url}/ara/?q={query}")
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.film-item"):
            title  = veri.select_text("a.film-name")
            href   = veri.select_attr("a.film-name", "href")
            poster = veri.select_attr("a.poster img", "src") or veri.select_attr("a.poster img", "data-src")

            if title and href:
                results.append(SearchResult(
                    title  = title.strip(),
                    url    = self.fix_url(href),
                    poster = self.fix_url(poster),
                ))

        return results

    async def load_item(self, url: str) -> SeriesInfo:
        istek  = await self.async_cf_get(url)
        secici = HTMLHelper(istek.text)

        title       = secici.select_text("h1.page-title") or secici.select_text("h1") or ""
        poster      = secici.select_attr("img.series-profile-thumb", "src") or secici.meta_value("og:image")
        description = secici.select_text("#tv-series-desc") or secici.select_text(".anime-desc") or secici.meta_value("og:description")
        tags        = secici.select_texts("div.genre-item a") or secici.select_texts(".anime-meta-grid a")

        episodes = []
        # Yeni yapı: ep-num-btn linkleri
        for veri in secici.select("a.ep-num-btn"):
            ep_href = veri.attrs.get("href")
            ep_text = veri.text(strip=True)  # Genelde "1", "2" gibi sadece sayı veya "1. Bölüm"

            if not ep_href:
                continue

            # Sezon ve bölüm bilgisini URL'den veya text'ten çıkar
            # Örn: /devil-may-cry-2-sezon-8-bolum-izle/
            season, episode = secici.extract_season_episode(ep_href)

            # Eğer URL'den çıkmazsa text'i dene
            if not episode:
                episode = ep_text

            episodes.append(Episode(
                season  = season or 1,
                episode = episode,
                title   = f"{episode}. Bölüm",
                url     = self.fix_url(ep_href),
            ))

        return SeriesInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title.strip(),
            description = description,
            tags        = tags,
            episodes    = episodes,
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        import base64, json
        istek = await self.async_cf_get(url)
        text  = istek.text

        response = []

        # Base64 encoded server listesini bul
        match = re.search(r'servers\s*=\s*JSON\.parse\(atob\("([^"]+)"\)\)', text)
        if not match:
            # Alternatif: serversByLang da olabilir
            match = re.search(r'serversByLang\s*=\s*JSON\.parse\(atob\("([^"]+)"\)\)', text)

        if not match:
            # En genel haliyle atob bulmaya çalış
            match = re.search(r'atob\("([^"]+)"\)', text)

        if match:
            try:
                encoded = match.group(1)
                decoded = base64.b64decode(encoded).decode('utf-8')
                servers = json.loads(decoded)

                # serversByLang ise dict olabilir, listeye çevir
                if isinstance(servers, dict):
                    all_servers = []
                    for lang_list in servers.values():
                        if isinstance(lang_list, list):
                            all_servers.extend(lang_list)
                    servers = all_servers

                for s in servers:
                    name = s.get("label", "CizgiMax")

                    if s.get("type") == "iframe":
                        src = s.get("src")
                        if src:
                            src_url = self.fix_url(src)
                            if "/oynat/" in src_url:
                                try:
                                    oynat_req  = await self.async_cf_get(src_url, headers={"Referer": url})
                                    oynat_html = oynat_req.text
                                    found_urls = re.findall(r'(https?://[^\s\"\'\<\>]+)', oynat_html)
                                    resolved   = False
                                    for u in found_urls:
                                        u_clean = u.rstrip("/").rstrip("&").rstrip("?")
                                        if any(domain in u_clean for domain in ("dzen.ru", "mail.ru", "ok.ru", "vk.com", "uqload", "voe.sx", "filemoon", "sibnet", "vidmoly", "rapidvid")):
                                            data = await self.extract(u_clean, referer=src_url, prefix=name)
                                            if data:
                                                self.collect_results(response, data)
                                                resolved = True
                                                break
                                    if not resolved:
                                        data = await self.extract(src_url, referer=url, prefix=name)
                                        self.collect_results(response, data)
                                except Exception:
                                    pass
                            else:
                                data = await self.extract(src_url, referer=url, prefix=name)
                                self.collect_results(response, data)
                    elif s.get("streamUrl"):
                        # Direkt stream URL (genelde sibnet/vidmoly api endpointi)
                        stream_url = self.fix_url(s.get("streamUrl"))
                        response.append(ExtractResult(
                            name    = name,
                            url     = stream_url,
                            referer = url
                        ))
                    elif s.get("resolveUrl"):
                        # Yeni yapı: resolveUrl (genelde dzen vb. için)
                        resolve_url = self.fix_url(s.get("resolveUrl"))
                        data        = await self.extract(resolve_url, referer=url, prefix=name)
                        if data:
                            self.collect_results(response, data)
                        else:
                            response.append(ExtractResult(url=resolve_url, name=name, referer=url))

            except Exception:
                pass

        if not response:
            # Klasik yöntem denemesi
            secici = HTMLHelper(text)
            for li in secici.select("ul.linkler li"):
                iframe = li.select_attr("a", "data-frame")
                if iframe:
                    data = await self.extract(self.fix_url(iframe.strip()), referer=url)
                    self.collect_results(response, data)

        return response
