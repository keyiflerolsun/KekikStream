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
        seen    = set()

        for card in secici.select("a.px-card[href*='/belgeseldizi/']"):
            card_sel = HTMLHelper(str(card.html))
            href     = card.attributes.get("href")
            title    = card_sel.select_text(".px-card-title") or card_sel.select_attr(".px-card-img", "alt")
            poster   = card_sel.select_attr(".px-card-img", "src")

            if not title or not href or href in seen:
                continue

            seen.add(href)
            results.append(MainPageResult(
                category = category,
                title    = self._clean_title(title),
                url      = self.fix_url(href),
                poster   = self.fix_url(poster)
            ))

        if results:
            return results

        for container in secici.select("div.gen-movie-contain"):
            poster = container.select_attr("div.gen-movie-img img", "src")
            title  = container.select_text("div.gen-movie-info h3 a")
            href   = container.select_attr("div.gen-movie-info h3 a", "href")

            if title and href and href not in seen:
                seen.add(href)
                results.append(MainPageResult(
                    category = category,
                    title    = self._clean_title(title),
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
            url_val = (url_val or "").replace("\\/", "/")
            poster  = (poster or "").replace("\\/", "/")

            if "/belgeseldizi/" not in url_val and "/belgesel/" not in url_val:
                if poster and "diziresimleri" in poster:
                    file_name = poster.rsplit("/", 1)[-1]
                    file_name = HTMLHelper(file_name).regex_replace(r"\.(jpe?g|png|webp)$", "")
                    url_val   = f"{self.main_url}/belgeseldizi/{file_name}"
                else:
                    continue

            clean_title = self._clean_title(title)
            results.append(SearchResult(
                title  = clean_title,
                url    = self.fix_url(url_val),
                poster = self.fix_url(poster)
            ))

        return results

    async def load_item(self, url: str) -> SeriesInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        og_title = secici.select_attr("meta[property='og:title']", "content")
        title    = self._clean_title(
            secici.select_text(".px-dizi-title") or
            secici.select_text(".px-hero-title") or
            secici.select_text("h1") or
            secici.select_text("h2") or
            secici.select_text("h2.gen-title") or
            og_title
        )
        poster = (
            secici.select_attr(".px-dizi-poster img", "src") or
            secici.select_poster("div.gen-tv-show-top img") or
            secici.select_attr("meta[property='og:image']", "content")
        )
        description = (
            secici.select_text(".px-dizi-desc") or
            secici.select_text("div.gen-single-tv-show-info p") or
            secici.select_attr("meta[name='description']", "content")
        )
        type_line = secici.regex_first(r"<strong>\s*Tür\s*:\s*</strong>\s*([^<]+)", flags=re.I)
        tags      = [self._to_title_case(part.strip()) for part in (type_line or "").split(",") if part.strip()]

        if not tags:
            tags = [self._to_title_case(t.rsplit("/", 1)[-1].replace("-", " ")) for t in secici.select_attrs("a[href*='/konu/']", "href")]

        # Meta bilgilerinden yıl ve puanı çıkar
        meta_items = secici.select_texts("div.gen-single-meta-holder ul li")
        if not meta_items:
            meta_items = [
                HTMLHelper(item).regex_replace(r"\s+", " ").strip()
                for item in re.findall(r"<li>\s*<strong>[\s\S]*?</li>", istek.text, re.I)
            ]
        year   = None
        rating = None
        actors = None
        for item in meta_items:
            if not year:
                if y_match := secici.regex_first(r"\b((?:19|20)\d{2})\b", item):
                    year = int(y_match)
            if not rating:
                if r_match := secici.regex_first(r"(?:IMDb\s*Puanı|Puan)\s*:?\s*(\d+(?:\.\d+)?)", item, flags=re.I):
                    rating = float(r_match)
                elif r_match := secici.regex_first(r"%\s*(\d+)\s*Puan", item):
                    rating = float(r_match) / 10
            if not actors:
                if actor_line := secici.regex_first(r"(?:Sunucular|Oyuncular)\s*:?\s*([^<]+)", item, flags=re.I):
                    actor_list = [part.strip() for part in actor_line.split(",") if part.strip()]
                    actors     = ", ".join(actor_list) or None
        rating     = rating or None

        if not actors:
            actor_line = (
                secici.regex_first(r"<strong>\s*(?:Sunucular|Oyuncular|Yayın Kanalı)\s*:\s*</strong>\s*([^<]+)", istek.text, flags=re.I) or
                secici.select_text(".px-dizi-channel span")
            )
            if actor_line:
                actor_list = [part.strip() for part in actor_line.split(",") if part.strip()]
                actors     = ", ".join(actor_list) or None

        episodes        = []

        for i, match in enumerate(self._extract_episode_cards(istek.text), start=1):
            href      = self.fix_url(match["href"])
            bolum_id  = match["bid"]
            sezon     = match["season"]
            bolum     = match["episode"]
            baslik    = match["title"]
            final_url = self._with_query(href, {"bid": bolum_id})

            episodes.append(Episode(
                season  = sezon or 1,
                episode = bolum or i,
                title   = baslik or f"Bölüm {i}",
                url     = final_url
            ))

        if not episodes:
            for i, match in enumerate(self._extract_dizi_getir_calls(istek.text), start=1):
                href     = self.fix_url(match["href"] or url.replace("/belgeseldizi/", "/belgesel/"))
                bolum_id = match["bid"]
                sezon    = match["season"]
                bolum    = match["episode"]
                baslik   = match["title"]
                params   = {"bid": bolum_id}
                if match["ic1"]:
                    params["ic1"] = match["ic1"]
                if match["ic2"]:
                    params["ic2"] = match["ic2"]
                if match["ic3"]:
                    params["ic3"] = match["ic3"]
                final_url = self._with_query(href, params)

                episodes.append(Episode(
                    season  = sezon or 1,
                    episode = bolum or i,
                    title   = baslik or f"Bölüm {i}",
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
            actors      = actors,
            episodes    = episodes
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        query      = parse_qs(urlsplit(url).query)
        episode_id = (query.get("bid") or [""])[0]
        ic_values  = [(query.get(f"ic{i}") or [""])[0] for i in range(1, 4)]
        main_url   = urlsplit(url)._replace(query="").geturl()

        if not episode_id or not any(ic_values):
            page_resp      = await self.httpx.get(main_url)
            wanted_episode = re.search(r'bolum-(\d+)', url)
            wanted_episode = wanted_episode.group(1) if wanted_episode else None
            candidates     = self._extract_dizi_getir_calls(page_resp.text)

            for candidate in candidates:
                bid    = candidate["bid"]
                ic1    = candidate["ic1"]
                ic2    = candidate["ic2"]
                ic3    = candidate["ic3"]
                baslik = candidate["title"]
                bolum  = candidate["episode"]
                sira   = candidate["order"]

                if episode_id and bid != episode_id:
                    continue
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
                    if any(x in extracted_url for x in (
                        "dailymotion.com/embed/video/",
                        "googlevideo.com/videoplayback",
                        "googleusercontent.com/",
                        ".mp4",
                        ".m3u8"
                    )):
                        _parts = urlsplit(extracted_url).netloc.removeprefix("www.").split(".")
                        _sld   = _parts[-2]
                        domain = _sld if len(_sld) >= 5 else f"{_sld}.{_parts[-1]}"
                        results.append(ExtractResult(
                            url     = extracted_url,
                            name    = domain,
                            referer = main_url
                        ))
                        continue
                    data = await self.extract(extracted_url, referer=main_url)
                    if data:
                        self.collect_results(results, data)

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

    def _clean_title(self, text: str | None) -> str:
        if not text:
            return ""

        cleaned = HTMLHelper(text).regex_replace(r"\s+", " ").strip()
        cleaned = re.split(r"\s+İzle(?:\s+\||$)", cleaned, 1)[0].strip()
        cleaned = re.split(r"\s+[|—-]\s+belgeselx\.com", cleaned, 1, flags=re.I)[0].strip()
        return self._to_title_case(cleaned)

    def _extract_episode_cards(self, html_text: str) -> list[dict[str, str | int | None]]:
        matches = re.findall(
            r'<a[^>]+class="[^"]*px-ep-card[^"]*"[^>]+href="([^"]+)"[^>]+onclick="butonKaydet\(\'(\d+)\'\)"[\s\S]*?'
            r'<span class="px-ep-title">\s*([^<]*)\s*</span>[\s\S]*?'
            r'<span class="px-ep-num">\s*(\d+)\s*</span>[\s\S]*?'
            r'<span class="px-ep-s">\s*S(\d+)\s*[·.-]\s*B(\d+)\s*</span>',
            html_text,
            re.I,
        )

        return [{
            "href"    : href,
            "bid"     : bid,
            "title"   : self._to_title_case(title),
            "season"  : int(season),
            "episode" : int(episode),
        } for href, bid, title, _display_num, season, episode in matches]

    def _extract_dizi_getir_calls(self, html_text: str) -> list[dict[str, str | int | None]]:
        matches = re.findall(
            r"diziGetir\('([^']+)','([^']*)','([^']*)','([^']*)','([^']*)','[^']*','[^']*','([^']*)','([^']*)','[^']*','([^']*)','[^']*','[^']*','[^']*','([^']*)'\)",
            html_text,
            re.I,
        )

        episodes = []
        for bid, ic1, ic2, ic3, title, season, episode, slug, order in matches:
            episodes.append({
                "href"    : f"{self.main_url}/belgesel/{slug}" if slug else "",
                "bid"     : bid,
                "ic1"     : ic1,
                "ic2"     : ic2,
                "ic3"     : ic3,
                "title"   : self._to_title_case(title),
                "season"  : int(season) if str(season).isdigit() else None,
                "episode" : int(episode) if str(episode).isdigit() else None,
                "order"   : int(order) if str(order).isdigit() else None,
            })

        return episodes
