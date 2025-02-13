# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, SearchResult, MovieInfo, Episode, SeriesInfo, ExtractResult, Subtitle

from Kekik.unicode_tr import unicode_tr
import re, json, base64

async def extract_next_f_push_data(source_code):
    """
    Kaynak kod içerisindeki self.__next_f.push(...) çağrılarını yakalayıp,
    içlerindeki key-value bilgilerini tek bir sözlükte birleştirir.
    """
    # self.__next_f.push( ... ) içindeki array'i yakalayan regex (DOTALL ile çok satırlı aramalarda)
    pattern = r"self\.__next_f\.push\(\s*(\[[\s\S]*?\])\s*\)"
    matches = re.findall(pattern, source_code, re.DOTALL)
    
    combined = {}
    
    for match in matches:
        try:
            # Yakalanan array'i JSON olarak ayrıştırıyoruz
            arr = json.loads(match)
        except json.JSONDecodeError as e:
            print("JSON ayrıştırma hatası:", e)
            continue
        
        # Eğer push çağrısı iki elemanlı ve ikinci eleman string ise işleme alalım.
        if isinstance(arr, list) and len(arr) == 2 and isinstance(arr[1], str):
            data_str = arr[1]
            # String içerisindeki satırları ayırıyoruz
            for line in data_str.splitlines():
                line = line.strip()
                if not line:
                    continue
                # Beklenen format: key:değer şeklinde
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Eğer değer HL[...] veya I[...] gibi bir formatta ise
                    m = re.match(r'^(HL|I)(\[[\s\S]*\])$', value)
                    if m:
                        prefix = m.group(1)
                        json_part = m.group(2)
                        try:
                            parsed_val = json.loads(json_part)
                            value = {prefix: parsed_val}
                        except json.JSONDecodeError:
                            # Ayrıştırılamazsa orijinal değeri bırakıyoruz.
                            pass
                    else:
                        # Değerin tamamı [ ... ] veya { ... } şeklinde ise JSON ayrıştırmayı deniyoruz.
                        if (value.startswith('[') and value.endswith(']')) or (value.startswith('{') and value.endswith('}')):
                            try:
                                value = json.loads(value)
                            except json.JSONDecodeError:
                                pass
                    # Eğer aynı anahtar daha önce varsa üzerine yazar.
                    combined[key] = value
        # Eğer push çağrısı farklı bir formatta ise (örneğin [0] veya [2, null]),
        # ihtiyaca göre burada ek işleme yapabilirsiniz.
    
    return combined

class Shorten(PluginBase):
    name     = "Shorten"
    main_url = "http://localhost:8080"
    token    = None

    async def __giris(self):
        await self.oturum.get("https://shorten.com/tr", follow_redirects=True)

        self.token = await self.oturum.get("https://shorten.com/api/session")
        self.token = self.token.json().get("token")

        self.oturum.headers.update({"Authorization": f"Bearer {self.token}"})

    async def raw_diziler(self):
        if not self.token:
            await self.__giris()

        veriler = await self.oturum.get("https://api.shorten.watch/api/series/you-might-like?page=1&per_page=100")
        veriler = veriler.json()

        return [
            {
                "title" : unicode_tr(veri.get("title")).title(),
                "slug"  : veri.get("slug"),
            } for veri in veriler.get("data")
        ]

    async def raw_bolumler(self, slug):
        if not self.token:
            await self.__giris()

        istek   = await self.oturum.get(f"https://shorten.com/tr/series/{slug}", follow_redirects=True)
        veriler = await extract_next_f_push_data(istek.text)
        veriler = veriler["8"][-1]["children"][-2][-1]["children"][-1]["data"]
        return [
            {
                "number" : veri.get("number"),
                "hash"   : veri.get("hash")
            } for veri in veriler.get("episodes")
        ]

    async def bolumler(self, slug):
        if not self.token:
            await self.__giris()

        raw_req       = await self.raw_bolumler(slug)
        number, _hash = raw_req[0].values()

        istek   = await self.oturum.get(f"https://shorten.com/tr/series/{slug}/episode-{number}-{_hash}", follow_redirects=True)
        veriler = await extract_next_f_push_data(istek.text)
        veriler = veriler["b"][3]["children"][1][3]["children"][3]["children"][3]["children"][-1]

        for index, video in enumerate(veriler["videos"]):
            copy = veriler["data"]["episodes"][index].copy()
            for key in copy.keys():
                del veriler["data"]["episodes"][index][key]

            for sub in copy.get("subtitles"):
                for sil in ["id", "format", "sub_id"]:
                    del sub[sil]
                sub["url"] = f"https://cdn.shorten.watch/{sub['url']}"

            token = base64.b64decode(video["hashHls"]).decode("utf-8")
            token = json.loads(token).get("GetPlayInfoToken")
            veriler["data"]["episodes"][index] = {
                "number"    : copy.get("number"),
                "image"     : copy.get("cover_image"),
                "hls"       : f"https://api.ramsan.tr/shorten/m3u/proxy/?{token}",
                "subtitles" : copy.get("subtitles")
            }

        veriler["data"]["episode"] = veriler["data"]["episode"]["total"]
        del veriler["data"]["is_favorite"]

        veriler["data"]["title"] = unicode_tr(veriler["data"]["title"]).title()

        return veriler["data"]

    async def search(self, query: str) -> list[SearchResult]:
        veriler = await self.raw_diziler()

        return [
            SearchResult(
                title  = veri.get("title"),
                url    = veri.get("slug"),
                poster = "",
            )
                for veri in veriler
        ]

    async def load_item(self, url: str) -> MovieInfo:
        veri = await self.bolumler(url)

        episodes = []
        for episode in veri.get("episodes"):
            episode["name"] = veri["title"]

            ep_model = Episode(
                season  = 1,
                episode = episode.get("number"),
                title   = f"{episode.get('number')}. Bölüm",
                url     = json.dumps(episode),
            )

            episodes.append(ep_model)
            subtitles = [
                Subtitle(
                    name = subtitle.get("language"),
                    url  = subtitle.get("url"),
                )
                    for subtitle in episode.get("subtitles")
            ]

            self._data[ep_model.url] = {
                "ext_name"  : self.name,
                "name"      : f"{ep_model.title}",
                "referer"   : "https://shorten.com/tr",
                "subtitles" : subtitles
            }

        return SeriesInfo(
            url         = url,
            poster      = veri.get("image"),
            title       = veri.get("title"),
            description = veri.get("description"),
            tags        = [genre.get("static_key") for genre in veri.get("categories")],
            rating      = 0,
            year        = 0,
            actors      = [],
            episodes    = episodes,
        )

    async def load_links(self, url: str) -> list[str]:
        return [url]

    async def play(self, name: str, url: str, referer: str, subtitles: list[Subtitle]):
        veri = json.loads(url)
        name = veri.get("name")
        url = veri.get("hls")
        subtitles = [
            Subtitle(
                name = subtitle.get("language"),
                url  = subtitle.get("url"),
            )
                for subtitle in veri.get("subtitles")
        ]
        extract_result = ExtractResult(name=name, url=url, referer=referer, subtitles=subtitles)
        self.media_handler.title = name
        self.media_handler.play_media(extract_result)