# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode, ExtractResult, HTMLHelper
from contextlib       import suppress
from urllib.parse     import parse_qs, urlencode, urlsplit, urlunsplit
import json
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
        istek  = await self.async_cf_get(f"{url}{page}")
        secici = HTMLHelper(istek.text)

        results = []
        for container in secici.select("div.gen-movie-contain"):
            poster = container.select_attr("div.gen-movie-img img", "src")
            title  = container.select_text("div.gen-movie-info h3 a")
            href   = container.select_attr("div.gen-movie-info h3 a", "href")

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

        token_resp = await self.async_cf_get(f"https://cse.google.com/cse.js?cx={cx}")
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

        resp      = await self.async_cf_get(search_url)
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
                url    = self.fix_url(url_val),
                poster = poster
            ))

        return results

    async def load_item(self, url: str) -> SeriesInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        title = (
            self._to_title_case(secici.select_text("h2.gen-title")) or
            self._to_title_case(secici.select_attr("meta[property='og:title']", "content").split(" İzle")[0])
        )
        poster = (
            secici.select_poster("div.gen-tv-show-top img") or
            secici.select_attr("meta[property='og:image']", "content")
        )
        description = (
            secici.select_text("div.gen-single-tv-show-info p") or
            secici.select_attr("meta[name='description']", "content")
        )
        tags = [self._to_title_case(t.rsplit("/", 1)[-1].replace("-", " ")) for t in secici.select_attrs("div.gen-socail-share a[href*='belgeselkanali']", "href")]

        # Meta bilgilerinden yıl ve puanı çıkar
        meta_items = secici.select_texts("div.gen-single-meta-holder ul li")
        year       = None
        rating     = None
        for item in meta_items:
            if not year:
                if y_match := secici.regex_first(r"\b((?:19|20)\d{2})\b", item):
                    year = int(y_match)
            if not rating:
                if r_match := secici.regex_first(r"%\s*(\d+)\s*Puan", item):
                    rating = float(r_match) / 10
        rating = rating or None

        episodes        = []
        episode_matches = re.findall(
            r'href="([^"]+)"[^>]+onclick="diziGetir\(\'(\d+)\',\'([^\']+)\',\'([^\']+)\',\'([^\']+)\',\'([^\']*)\',\'[^\']*\',\'[^\']*\',\'([^\']*)\',\'([^\']*)\'',
            istek.text,
            re.I,
        )
        for i, match in enumerate(episode_matches):
            href, bolum_id, ic1, ic2, ic3, baslik, sezon, bolum = match
            params = {
                "bid" : bolum_id,
                "ic1" : ic1,
                "ic2" : ic2,
                "ic3" : ic3,
            }
            final_url = self._with_query(self.fix_url(href), params)

            s, e = secici.extract_season_episode(f"{sezon} {bolum} {baslik}")
            episodes.append(Episode(
                season  = s or 1,
                episode = e or (i + 1),
                title   = baslik or name or f"Bölüm {i + 1}",
                url     = final_url
            ))

        if not episodes:
            seen = set()
            for i, ep_url in enumerate(re.findall(r'https://belgeselx\.com/belgesel/[^"\']+', istek.text), start=1):
                if ep_url in seen:
                    continue
                seen.add(ep_url)
                ep_num = re.search(r'bolum-(\d+)', ep_url)
                ep_val = int(ep_num.group(1)) if ep_num else i
                episodes.append(Episode(
                    season  = 1,
                    episode = ep_val,
                    title   = f"Bölüm {ep_val}",
                    url     = self.fix_url(ep_url),
                ))

        if not episodes:
            for season_blob in self._extract_json_ld_episodes(istek.text):
                episodes.append(season_blob)

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
        query      = parse_qs(urlsplit(url).query)
        episode_id = (query.get("bid") or [""])[0]
        ic_values  = [(query.get(f"ic{i}") or [""])[0] for i in range(1, 4)]
        main_url   = urlsplit(url)._replace(query="").geturl()

        if not episode_id:
            page_resp      = await self.httpx.get(main_url)
            wanted_episode = re.search(r'bolum-(\d+)', url)
            wanted_episode = wanted_episode.group(1) if wanted_episode else None
            candidates     = re.findall(
                r"diziGetir\('(\d+)','([^']+)','([^']+)','([^']+)','([^']*)','[^']*','[^']*','([^']*)','([^']*)'.*?'(\d+)'\)",
                page_resp.text,
                re.I | re.S,
            )

            for bid, ic1, ic2, ic3, baslik, sezon, bolum, sira in candidates:
                if wanted_episode and wanted_episode not in {str(bolum), str(sira)} and wanted_episode not in baslik:
                    continue
                episode_id = bid
                ic_values  = [ic1, ic2, ic3]
                break

        if not episode_id:
            return []

        src_map = {"0": "new5", "2": "new1", "5": "new4", "3": "new2", "4": "new3"}
        results = []

        for idx, ic_val in enumerate(ic_values, start=1):
            endpoint = src_map.get(str(ic_val))
            if not endpoint:
                continue

            player_url  = f"{self.main_url}/video/data/{endpoint}.php?id={episode_id}"
            player_resp = await self.httpx.get(player_url, headers={"Referer": main_url})
            player_html = player_resp.text
            player_sel  = HTMLHelper(player_html)

            extracted_urls = []
            if iframe_src := player_sel.select_attr("iframe", "src"):
                iframe_src = iframe_src.strip()
                if iframe_src and iframe_src.startswith("x"):
                    iframe_src = f"https://www.dailymotion.com/embed/video/{iframe_src}"
                extracted_urls.append(self.fix_url(iframe_src))

            if video_src := player_sel.select_attr("video", "src"):
                extracted_urls.append(self.fix_url(video_src))

            for file_url in player_sel.regex_all(r'file\s*:\s*"([^"]+)"'):
                extracted_urls.append(self.fix_url(file_url))

            for extracted_url in extracted_urls:
                if "belgeselx.php" in extracted_url or "belgeselx2.php" in extracted_url:
                    with suppress(Exception):
                        resp          = await self.httpx.head(extracted_url, headers={"Referer": main_url}, follow_redirects=True)
                        extracted_url = str(resp.url)

                if extracted_url.startswith("http"):
                    if "dailymotion.com/embed/video/" in extracted_url:
                        results.append(ExtractResult(
                            url     = extracted_url,
                            name    = f"{self.name} | Kaynak {idx}",
                            referer = main_url
                        ))
                        continue
                    data = await self.extract(extracted_url, referer=main_url, prefix=f"{self.name} | Kaynak {idx}")
                    if data:
                        self.collect_results(results, data)
                    else:
                        results.append(ExtractResult(
                            url     = extracted_url,
                            name    = f"{self.name} | Kaynak {idx}",
                            referer = main_url
                        ))

        return self.deduplicate(results, key="url+name")

    @staticmethod
    def _with_query(url: str, params: dict[str, str]) -> str:
        parts = list(urlsplit(url))
        parts[3] = urlencode(params)
        return urlunsplit(parts)

    def _extract_json_ld_episodes(self, html_text: str) -> list[Episode]:
        secici   = HTMLHelper(html_text)
        payloads = secici.regex_all(r'<script type="application/ld\+json">\s*([\s\S]*?)</script>')
        episodes = []

        for payload in payloads:
            try:
                data = json.loads(payload)
            except Exception:
                continue

            seasons = data.get("containsSeason", []) if isinstance(data, dict) else []
            for season in seasons:
                for idx, item in enumerate(season.get("episode", []), start=1):
                    episodes.append(Episode(
                        season  = int(season.get("seasonNumber") or 1),
                        episode = int(item.get("episodeNumber") or idx),
                        title   = item.get("name") or f"Bölüm {idx}",
                        url     = self.fix_url(item.get("url", ""))
                    ))

        return episodes
