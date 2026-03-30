# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, Subtitle, HTMLHelper
from urllib.parse     import urlencode
import re, json

class Fembed(ExtractorBase):
    name              = "Fembed"
    main_url          = "https://fembed.online"
    supported_domains = ["fembed.online", "fembed.net", "fembed.com"]

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        headers = {"Referer": referer or self.main_url}

        try:
            resp = await self.async_cf_get(url, headers=headers)
            html = resp.text
        except Exception:
            resp = await self.httpx.get(url=url, headers=headers)
            html = resp.text
        sel  = HTMLHelper(html)

        m3u8_url = None

        # playerSources dizisini JSON olarak çek
        src_match = re.search(r"var\s+playerSources\s*=\s*(\[.*?\]);", html, re.DOTALL)
        if src_match:
            try:
                sources  = json.loads(src_match.group(1))
                for src in sources:
                    f = src.get("file", "")
                    if f and (".m3u8" in f or ".mp4" in f):
                        m3u8_url = f
                        break
            except Exception:
                pass

        # Fallback: regex ile m3u8 bul
        if not m3u8_url:
            m3u8_url = sel.regex_first(r'"file"\s*:\s*"([^"]+\.m3u8[^"]*)"')

        # Yeni JetFilmizle shell'i kaynakları worker API üzerinden yüklüyor.
        if not m3u8_url:
            async_config = sel.regex_first(r"var\s+asyncConfig\s*=\s*(\{.*?\});", group=1)
            if async_config:
                try:
                    config = json.loads(async_config)
                    params = urlencode({
                        "tmdb"    : config.get("tmdbId"),
                        "type"    : config.get("type"),
                        "season"  : config.get("season", 1),
                        "episode" : config.get("episode", 1),
                    })
                    base_url = self.get_base_url(url)

                    api_urls = [
                        f"{base_url}/api_proxy.php?{params}",
                        f"{config.get('workerUrl', '').rstrip('/')}/api/sources?{params}",
                    ]

                    for api_url in api_urls:
                        if not api_url or "None" in api_url:
                            continue

                        try:
                            api_resp = await self.async_cf_get(api_url, headers={"Referer": url})
                        except Exception:
                            api_resp = await self.httpx.get(api_url, headers={"Referer": url})

                        with_sources = api_resp.json() if api_resp.status_code == 200 else None
                        if not isinstance(with_sources, dict):
                            continue

                        sources = with_sources.get("sources") or []
                        if not sources:
                            continue

                        first_source = sources[0]
                        first_url    = first_source.get("url", "")
                        is_mp4       = ".mp4" in first_url or "/mp4/" in first_url
                        worker_url   = (config.get("workerUrl") or "").rstrip("/")

                        if is_mp4:
                            m3u8_url = first_url
                        elif len(sources) > 1 and worker_url:
                            qualities = []
                            streams   = []
                            for source in sources:
                                qualities.append(source.get("quality") or "720p")
                                source_url = source.get("url") or ""
                                # Worker endpointten gelen /stream/ENCRYPTED yolları koru.
                                stream_key = re.sub(r"^.*?/stream/", "", source_url)
                                if not stream_key and source_url.startswith("http"):
                                    stream_key = source_url
                                if stream_key:
                                    streams.append(stream_key)

                            if qualities and streams:
                                m3u8_url = f"{worker_url}/master.m3u8?q={','.join(qualities)}&s={','.join(streams)}"
                        else:
                            m3u8_url = first_url

                        if m3u8_url:
                            break
                except Exception:
                    pass

        if not m3u8_url:
            raise ValueError(f"{self.name}: Video URL bulunamadı. {url}")

        # Altyazıları çek (subtitles dizisinden)
        subtitles = []
        sub_match = re.search(r"var\s+subtitles\s*=\s*(\[.*?\]);", html, re.DOTALL)
        if sub_match:
            try:
                subs = json.loads(sub_match.group(1))
                for sub in subs:
                    s_file  = sub.get("file", "")
                    s_label = sub.get("label", "Altyazı")
                    if s_file and (s_file.startswith("http") or s_file.startswith("/")):
                        sub_url = self.fix_url(s_file)
                        subtitles.append(Subtitle(name=s_label, url=sub_url))
            except Exception:
                pass

        if not subtitles:
            async_config = sel.regex_first(r"var\s+asyncConfig\s*=\s*(\{.*?\});", group=1)
            if async_config:
                try:
                    config     = json.loads(async_config)
                    worker_url = (config.get("workerUrl") or "").rstrip("/")
                    if worker_url:
                        sub_url = (
                            f"{worker_url}/api/subtitles?id={config.get('tmdbId')}&type={config.get('type')}"
                            f"&season={config.get('season', 1)}&episode={config.get('episode', 1)}"
                        )

                        try:
                            sub_resp = await self.async_cf_get(sub_url, headers={"Referer": url})
                        except Exception:
                            sub_resp = await self.httpx.get(sub_url, headers={"Referer": url})

                        sub_data = sub_resp.json() if sub_resp.status_code == 200 else {}
                        for sub in sub_data.get("tracks", []):
                            s_file  = sub.get("file", "")
                            s_label = sub.get("label", "Altyazı")
                            if s_file:
                                subtitles.append(Subtitle(name=s_label, url=self.fix_url(s_file)))
                except Exception:
                    pass

        return ExtractResult(
            name       = self.name,
            url        = self.fix_url(m3u8_url),
            referer    = self.get_base_url(url),
            user_agent = self.httpx.headers.get("User-Agent"),
            subtitles  = subtitles,
        )
