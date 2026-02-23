# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode, ExtractResult
import re

class AnimeciX(PluginBase):
    name        = "AnimeciX"
    language    = "tr"
    main_url    = "https://animecix.tv"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "AnimeciX - Türkçe anime izleme platformu."

    main_page   = {
        f"{main_url}/secure/last-episodes"                          : "Son Eklenen Bölümler",
        f"{main_url}/secure/titles?type=series&onlyStreamable=true" : "Seriler",
        f"{main_url}/secure/titles?type=movie&onlyStreamable=true"  : "Filmler",
    }

    _XEH = "7Y2ozlO+QysR5w9Q6Tupmtvl9jJp7ThFH8SB+Lo7NvZjgjqRSqOgcT2v4ISM9sP10LmnlYI8WQ==.xrlyOBFS5BHjQ2Lk"

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        results = []

        if "/last-episodes" in url:
            resp = await self.httpx.get(
                f"{self.main_url}/secure/last-episodes?page={page}&perPage=10",
                headers={"x-e-h": self._XEH},
            )
            data_list = resp.json().get("data", [])

            for item in data_list:
                title_name = item.get("title_name", "")
                s_num      = item.get("season_number", 0)
                e_num      = item.get("episode_number", 0)
                title_id   = item.get("title_id", "")
                poster     = item.get("title_poster")

                title = f"S{s_num}B{e_num} - {title_name}"
                results.append(MainPageResult(
                    category = category,
                    title    = title,
                    url      = f"{self.main_url}/secure/titles/{title_id}?titleId={title_id}",
                    poster   = self.fix_url(poster),
                ))
        else:
            sep  = "&" if "?" in url else "?"
            resp = await self.httpx.get(
                f"{url}{sep}page={page}&perPage=16",
                headers={"x-e-h": self._XEH},
            )
            data  = resp.json()
            items = data.get("pagination", {}).get("data", [])

            for item in items:
                title    = item.get("name", "")
                title_id = item.get("id", "")
                poster   = item.get("poster")

                if title and title_id:
                    results.append(MainPageResult(
                        category = category,
                        title    = title,
                        url      = f"{self.main_url}/secure/titles/{title_id}?titleId={title_id}",
                        poster   = self.fix_url(poster),
                    ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        resp = await self.httpx.get(f"{self.main_url}/secure/search/{query}?limit=20")
        data = resp.json()

        results = []
        for item in data.get("results", []):
            title    = item.get("name", "")
            title_id = item.get("id", "")
            poster   = item.get("poster")

            if title and title_id:
                results.append(SearchResult(
                    title  = title,
                    url    = f"{self.main_url}/secure/titles/{title_id}?titleId={title_id}",
                    poster = self.fix_url(poster),
                ))

        return results

    async def load_item(self, url: str) -> SeriesInfo:
        resp = await self.httpx.get(url, headers={"x-e-h": self._XEH})
        data = resp.json().get("title", {})

        title_id   = data.get("id", "")
        title      = data.get("name", "")
        poster     = data.get("poster")
        desc       = data.get("description")
        year       = data.get("year")
        tags       = [g.get("display_name", "") for g in data.get("genres", [])]
        title_type = data.get("title_type", "anime")

        episodes = []

        if title_type == "anime":
            for season in data.get("seasons", []):
                s_num    = season.get("number", 1)
                vid_resp = await self.httpx.get(
                    f"{self.main_url}/secure/related-videos?episode=1&season={s_num}&videoId=0&titleId={title_id}"
                )
                vid_data = vid_resp.json()
                for video in vid_data.get("videos", []):
                    ep_num = video.get("episode_num")
                    s_n    = video.get("season_num", s_num)
                    ep_url = video.get("url", "")

                    episodes.append(Episode(
                        season  = s_n,
                        episode = ep_num,
                        title   = f"{s_n}. Sezon {ep_num}. Bölüm",
                        url     = ep_url,
                    ))
        else:
            videos = data.get("videos", [])
            if videos:
                episodes.append(Episode(
                    season  = 1,
                    episode = 1,
                    title   = "Filmi İzle",
                    url     = videos[0].get("url", ""),
                ))

        return SeriesInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title,
            description = desc,
            tags        = tags,
            year        = str(year) if year else None,
            episodes    = episodes,
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        page_url = f"{self.main_url}/{url}" if not url.startswith("http") else url

        resp        = await self.httpx.get(page_url, follow_redirects=True, headers={"Referer": f"{self.main_url}/"})
        iframe_link = str(resp.url)

        # Çift URL düzeltme
        double_match = re.search(r"https://animecix\.tv/(https://animecix\.tv/secure/\S+)", iframe_link)
        if double_match:
            iframe_link = double_match.group(1)

        # best-video redirect takibi
        if "/secure/best-video" in iframe_link:
            redir_resp  = await self.httpx.get(iframe_link, follow_redirects=True, headers={"Referer": f"{self.main_url}/"})
            iframe_link = str(redir_resp.url)

        return await self.extract(iframe_link, referer=f"{self.main_url}/")
