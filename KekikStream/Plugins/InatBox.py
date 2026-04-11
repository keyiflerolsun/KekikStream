# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, ExtractResult
import json

class InatBox(PluginBase):
    name        = "InatBox"
    language    = "tr"
    main_url    = "https://diziboxen.help"
    favicon     = "https://inatboxindir.org/wp-content/uploads/2023/01/cropped-inat-box-logo-1-192x192.png"
    description = "Inat Box APK, Türkiye'nin en popüler canlı TV ve dijital platform içeriklerini sunan uygulamasıdır."

    _api_url = "http://sv2-webservisler:2585/api/v1/inatbox"

    main_page = {
        "sinema"       : "Sinema Kanalları",
        "dini"         : "Dini Kanallar",
        "gain"         : "Gain",
        "netflix"      : "Netflix",
        "disney"       : "Disney+",
        "amazon"       : "Amazon Prime",
        "hbo"          : "HBO Max",
        "tabii"        : "Tabii",
        "yabanci-dizi" : "Yabancı Diziler",
        "yerli-dizi"   : "Yerli Diziler",
    }

    async def _api_request(self, q: str) -> str:
        try:
            istek = await self.httpx.get(self._api_url, params={"q": q})
            if istek.status_code == 200:
                return istek.json().get("result", "")
        except Exception:
            pass
        return ""

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        json_resp = await self._api_request(url)
        if not json_resp:
            return []

        try:
            veriler = json.loads(json_resp)
            results = []
            for veri in veriler:
                if veri.get("diziType") == "link" or veri.get("chType") in ("link", "link_mode"):
                    continue
                title  = veri.get("diziName") or veri.get("chName")
                poster = veri.get("diziImg")  or veri.get("chImg")
                if title:
                    results.append(MainPageResult(
                        category = category,
                        title    = title,
                        url      = json.dumps(veri, ensure_ascii=False),
                        poster   = self.fix_url(poster),
                    ))
            return results
        except Exception:
            return []

    async def search(self, query: str) -> list[SearchResult]:
        query    = query.lower()
        tasks    = [self._api_request(slug) for slug in self.main_page]
        yanıtlar = await self.gather_with_limit(tasks)

        results = []
        for json_resp in yanıtlar:
            if not json_resp:
                continue
            try:
                veriler = json.loads(json_resp)
                for veri in veriler:
                    title = veri.get("diziName") or veri.get("chName")
                    if title and query in title.lower():
                        results.append(SearchResult(
                            title  = title,
                            url    = json.dumps(veri, ensure_ascii=False),
                            poster = self.fix_url(veri.get("diziImg") or veri.get("chImg")),
                        ))
            except Exception:
                continue

        return results

    async def load_item(self, url: str) -> MovieInfo | SeriesInfo:
        veri       = json.loads(url)
        ortak_meta = {
            "year"   : "2026",
            "tags"   : ["InatBox", "Dijital"],
            "actors" : ["Inat Sunucuları"],
            "rating" : "10",
        }

        if veri.get("diziType") in ("dizi", "dizi_mode"):
            title  = veri.get("diziName")
            poster = veri.get("diziImg")
            plot   = veri.get("diziDetay") or f"{title} dizisini InatBox farkıyla izleyin."
            d_url  = veri.get("diziUrl")

            json_resp = await self._api_request(d_url)
            if not json_resp:
                return MovieInfo(url=url, title=title, poster=self.fix_url(poster), description=plot, **ortak_meta)

            try:
                sezon_verisi = json.loads(json_resp)
                if isinstance(sezon_verisi, list) and sezon_verisi and "diziUrl" in sezon_verisi[0]:
                    episodes = []
                    for sezon_no, sezon in enumerate(sezon_verisi, start=1):
                        ep_resp = await self._api_request(sezon.get("diziUrl"))
                        if not ep_resp:
                            continue
                        ep_verisi = json.loads(ep_resp)
                        for bolum_no, bolum in enumerate(ep_verisi, start=1):
                            bolum_adi = bolum.get("chName") or f"S{sezon_no:02d} - {bolum_no:02d}.Bölüm"
                            episodes.append(Episode(
                                season  = sezon_no,
                                episode = bolum_no,
                                title   = bolum_adi,
                                url     = json.dumps(bolum, ensure_ascii=False),
                                poster  = bolum.get("chImg"),
                            ))
                else:
                    items    = sezon_verisi if isinstance(sezon_verisi, list) else [sezon_verisi]
                    episodes = [
                        Episode(
                            season  = 1,
                            episode = no,
                            title   = bolum.get("chName") or f"Bölüm {no}",
                            url     = json.dumps(bolum, ensure_ascii=False),
                            poster  = bolum.get("chImg"),
                        )
                        for no, bolum in enumerate(items, start=1)
                    ]

                return SeriesInfo(
                    url         = url,
                    title       = title,
                    poster      = self.fix_url(poster),
                    description = plot,
                    episodes    = episodes,
                    **ortak_meta
                )
            except Exception:
                return MovieInfo(url=url, title=title, poster=self.fix_url(poster), description=plot, **ortak_meta)

        else:
            title  = veri.get("diziName") or veri.get("chName")
            poster = veri.get("diziImg")  or veri.get("chImg")
            plot   = veri.get("diziDetay") or f"{title} içeriğini InatBox farkıyla izleyin."
            return MovieInfo(
                url         = url,
                title       = title,
                poster      = self.fix_url(poster),
                description = plot,
                **ortak_meta
            )

    async def load_links(self, url: str) -> list[ExtractResult]:
        try:
            veri = json.loads(url)
        except Exception:
            return []

        items = veri if isinstance(veri, list) else [veri]

        results = []
        for it in items:
            if it.get("diziUrl") and not it.get("chUrl"):
                json_resp = await self._api_request(it.get("diziUrl"))
                if json_resp:
                    try:
                        ic_veri = json.loads(json_resp)
                        it      = ic_veri[0] if isinstance(ic_veri, list) and ic_veri else ic_veri
                    except Exception:
                        pass

            ch_type = it.get("chType", "")
            if ch_type in ("tekli_regex_lb_sh_3", "tekli_regex_lb_sh_3_mode"):
                json_resp = await self._api_request(it.get("chUrl"))
                if json_resp:
                    try:
                        it = json.loads(json_resp)
                    except Exception:
                        pass

            kaynak_url = it.get("chUrl")
            if not kaynak_url:
                continue

            if kaynak_url.startswith("act"):
                kaynak_url = f"https://vk.com/al_video.php?{kaynak_url}"

            headers    = {}
            ch_headers = it.get("chHeaders")
            if ch_headers and ch_headers != "null":
                try:
                    h_json = json.loads(ch_headers) if isinstance(ch_headers, str) else ch_headers
                    if isinstance(h_json, list) and h_json:
                        headers.update(h_json[0])
                    elif isinstance(h_json, dict):
                        headers.update(h_json)
                except Exception:
                    pass

            ch_reg = it.get("chReg")
            if ch_reg and ch_reg != "null":
                try:
                    r_json = json.loads(ch_reg) if isinstance(ch_reg, str) else ch_reg
                    if isinstance(r_json, list) and r_json:
                        cookie = r_json[0].get("playSH2")
                        if cookie:
                            headers["Cookie"] = cookie
                except Exception:
                    pass

            ua  = headers.get("UserAgent") or headers.get("User-Agent")
            ref = headers.get("Referer")

            extracted = await self.extract(kaynak_url, referer=ref)
            if extracted:
                items_ext = extracted if isinstance(extracted, list) else [extracted]
                for ie in items_ext:
                    ie.name = it.get("chName") or ie.name
                    if ua:
                        ie.user_agent = ua
                    if ref:
                        ie.referer = ref
                self.collect_results(results, extracted)
            else:
                results.append(ExtractResult(
                    url        = kaynak_url,
                    name       = it.get("chName"),
                    referer    = ref,
                    user_agent = ua,
                ))

        return results
