# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, ExtractResult, HTMLHelper
import re
import asyncio


class Kinogo(PluginBase):
    name        = "Kinogo"
    language    = "ru"
    main_url    = "https://kinogo.online"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Смотреть фильмы и сериалы онлайн бесплатно на официальном КИНОГО в хорошем качестве."

    main_page = {
        f"{main_url}/filmy/page/"            : "Все фильмы",
        f"{main_url}/serialy/page/"          : "Сериалы",
        f"{main_url}/multfilmy/page/"        : "Мультфильмы",
        f"{main_url}/anime/page/"            : "Аниме",
        f"{main_url}/novinki/page/"          : "Новинки",
        f"{main_url}/fantastika/page/"       : "Фантастика",
        f"{main_url}/fjentezi/page/"         : "Фэнтези",
        f"{main_url}/nuar/page/"             : "Нуар",
        f"{main_url}/uzhasy/page/"           : "Ужасы",
        f"{main_url}/triller/page/"          : "Триллер",
        f"{main_url}/sport/page/"            : "Спорт",
        f"{main_url}/prikljuchenija/page/"   : "Приключения",
        f"{main_url}/istoricheskie/page/"    : "Исторические",
        f"{main_url}/mjuzikl/page/"          : "Мюзикл",
        f"{main_url}/melodrama/page/"        : "Мелодрама",
        f"{main_url}/korotkometrazhka/page/" : "Короткометражка",
        f"{main_url}/kriminal/page/"         : "Криминал",
        f"{main_url}/drama/page/"            : "Драма",
        f"{main_url}/komedija/page/"         : "Комедия",
        f"{main_url}/dokumentalnye/page/"    : "Документальные",
        f"{main_url}/detektiv/page/"         : "Детектив",
        f"{main_url}/detskij/page/"          : "Детский",
        f"{main_url}/voennyj/page/"          : "Военный",
        f"{main_url}/vestern/page/"          : "Вестерн",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.async_cf_get(f"{url}{page}/")
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select(".shortStory"):
            title = veri.select_attr("a", "title") or veri.select_attr("img", "alt")
            href  = veri.select_attr("a", "href")
            img   = veri.select_poster("img")

            if title and href:
                results.append(
                    MainPageResult(
                        category = category,
                        title    = title,
                        url      = self.fix_url(href),
                        poster   = self.fix_url(img),
                    )
                )

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.async_cf_get(f"{self.main_url}/index.php?do=search&subaction=search&story={query}")
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select(".shortStory"):
            title = veri.select_attr("a", "title") or veri.select_attr("img", "alt")
            href  = veri.select_attr("a", "href")
            img   = veri.select_poster("img")

            if title and href:
                results.append(
                    SearchResult(
                        title  = title,
                        url    = self.fix_url(href),
                        poster = self.fix_url(img),
                    )
                )

        return results

    async def load_item(self, url: str) -> MovieInfo | SeriesInfo:
        istek  = await self.async_cf_get(url)
        secici = HTMLHelper(istek.text)

        poster = self.fix_url(
            secici.select_poster("div.sPoster img") or secici.select_poster("div.fullstoryPoster img") or secici.select_poster("div.fposter img") or secici.select_attr("meta[property='og:image']", "content")
        )
        description = secici.select_attr("meta[property='og:description']", "content")
        title       = secici.select_text("h1")

        year         = secici.meta_value("Год выпуска") or secici.meta_value("Год")
        rating       = secici.meta_value("IMDB") or secici.meta_value("КиноПоиск")
        duration_raw = secici.meta_value("Продолжительность")
        if duration_raw:
            parts    = duration_raw.split()
            duration = int(parts[0]) if parts[0].isdigit() else None
        else:
            duration = None

        tags   = secici.meta_list("Жанр")
        actors = secici.meta_list("Актеры") or secici.meta_list("В ролях")

        iframes = []
        for i_src in secici.select_attrs("iframe", "src") + secici.select_attrs("iframe", "data-src"):
            if i_src and "youtube" not in i_src and "facebook" not in i_src and "vk.com" not in i_src:
                iframes.append(i_src)

        for p_src in secici.select_attrs("li", "data-src"):
            if p_src and "youtube" not in p_src and "facebook" not in p_src and "vk.com" not in p_src:
                iframes.append(p_src)

        if not iframes:
            i = secici.regex_first(r"<iframe[^>]+src=[\"\']([^\"\']+)[\"\']")
            if i and "youtube" not in i and "facebook" not in i and "vk.com" not in i:
                iframes.append(i)

        iframes  = list(set([self.fix_url(i) for i in iframes]))
        episodes = []

        if iframes:
            for iframe in iframes:
                extractor = self.ex_manager.find_extractor(iframe)
                if extractor and hasattr(extractor, "get_playlist"):
                    playlist = await extractor.get_playlist(iframe, url)
                    if playlist:
                        for ep_data in playlist:
                            if ep_data.get("type") == "series":
                                s_num = ep_data["season"]
                                e_num = ep_data["episode"]
                                episodes.append(Episode(season=s_num, episode=e_num, title=f"Серия {e_num}", url=f"{url}#season={s_num}&episode={e_num}"))
                        if episodes:
                            break

        if episodes:
            return SeriesInfo(url=url, poster=poster, title=title, description=description, tags=tags, rating=rating, year=year, duration=duration, actors=actors, episodes=episodes)

        return MovieInfo(url=url, poster=poster, title=title, description=description, tags=tags, rating=rating, year=year, duration=duration, actors=actors)

    async def load_links(self, url: str) -> list[ExtractResult]:
        target_season  = None
        target_episode = None

        if "#season=" in url:
            parts    = url.split("#season=")
            real_url = parts[0]
            se_parts = parts[1].split("&episode=")
            if len(se_parts) == 2:
                target_season  = int(se_parts[0])
                target_episode = int(se_parts[1])

            url = real_url

        istek  = await self.async_cf_get(url)
        secici = HTMLHelper(istek.text)

        iframes = []
        for i_src in secici.select_attrs("iframe", "src") + secici.select_attrs("iframe", "data-src"):
            if i_src and "youtube" not in i_src and "facebook" not in i_src and "vk.com" not in i_src:
                iframes.append(i_src)

        for p_src in secici.select_attrs("li", "data-src"):
            if p_src and "youtube" not in p_src and "facebook" not in p_src and "vk.com" not in p_src:
                iframes.append(p_src)

        if not iframes:
            i = secici.regex_first(r"<iframe[^>]+src=[\"\']([^\"\']+)[\"\']")
            if i and "youtube" not in i and "facebook" not in i and "vk.com" not in i:
                iframes.append(i)

        iframes = list(set([self.fix_url(i) for i in iframes]))
        results = []

        if target_season is not None and target_episode is not None and iframes:
            for iframe in iframes:
                extractor = self.ex_manager.find_extractor(iframe)
                if extractor and hasattr(extractor, "get_playlist"):
                    playlist = await extractor.get_playlist(iframe, url)
                    for ep_data in playlist:
                        if ep_data.get("type") == "series" and ep_data["season"] == target_season and ep_data["episode"] == target_episode:
                            for v in ep_data["voices"]:
                                clean_title = re.sub(r"<[^>]+>", "", v["title"]).strip()
                                c_name      = clean_title if clean_title else "Kinogo"

                                link_str = v.get("link", "")
                                for l in link_str.split(","):
                                    m = re.search(r"\[(.*?)\](.*)", l)
                                    if m:
                                        results.append(ExtractResult(name=f"{c_name} {m.group(1)}", url=self.fix_url(m.group(2)), referer=self.main_url))
                                    else:
                                        results.append(ExtractResult(name=c_name, url=self.fix_url(l), referer=self.main_url))
                    if results:
                        break
            return results

        if not iframes:
            return []

        # Movie parsing via Extractors
        tasks          = [self.extract(self.fix_url(i), referer=url) for i in iframes]
        extracted_data = await asyncio.gather(*tasks)

        for data in extracted_data:
            if data:
                self.collect_results(results, data)

        return results
