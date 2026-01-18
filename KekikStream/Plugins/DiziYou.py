# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode, Subtitle, ExtractResult, HTMLHelper

class DiziYou(PluginBase):
    name        = "DiziYou"
    language    = "tr"
    main_url    = "https://www.diziyou.one"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Diziyou en kaliteli Türkçe dublaj ve altyazılı yabancı dizi izleme sitesidir. Güncel ve efsanevi dizileri 1080p Full HD kalitede izlemek için hemen tıkla!"

    main_page   = {
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur=Aile"                 : "Aile",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur=Aksiyon"              : "Aksiyon",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur=Animasyon"            : "Animasyon",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur=Belgesel"             : "Belgesel",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur=Bilim+Kurgu"          : "Bilim Kurgu",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur=Dram"                 : "Dram",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur=Fantazi"              : "Fantazi",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur=Gerilim"              : "Gerilim",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur=Gizem"                : "Gizem",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur=Komedi"               : "Komedi",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur=Korku"                : "Korku",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur=Macera"               : "Macera",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur=Sava%C5%9F"           : "Savaş",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur=Su%C3%A7"             : "Suç",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur=Vah%C5%9Fi+Bat%C4%B1" : "Vahşi Batı"
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.httpx.get(f"{url.replace('SAYFA', str(page))}")
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.single-item"):
            title  = secici.select_text("div#categorytitle a", veri)
            href   = secici.select_attr("div#categorytitle a", "href", veri)
            poster = secici.select_attr("img", "src", veri)

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title,
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster) if poster else None,
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}/?s={query}")
        secici = HTMLHelper(istek.text)

        results = []
        for afis in secici.select("div.incontent div#list-series"):
            title  = secici.select_text("div#categorytitle a", afis)
            href   = secici.select_attr("div#categorytitle a", "href", afis)
            poster = (secici.select_attr("img", "src", afis) or secici.select_attr("img", "data-src", afis))

            if title and href:
                results.append(SearchResult(
                    title  = title,
                    url    = self.fix_url(href),
                    poster = self.fix_url(poster) if poster else None,
                ))

        return results

    async def load_item(self, url: str) -> SeriesInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)
        html_text = istek.text

        # Title - div.title h1 içinde
        title = (secici.select_text("div.title h1") or "").strip()

        # Fallback: Eğer title boşsa URL'den çıkar (telif kısıtlaması olan sayfalar için)
        if not title:
            # URL'den slug'ı al: https://www.diziyou.one/jasmine/ -> jasmine -> Jasmine
            slug = url.rstrip('/').split('/')[-1]
            title = slug.replace('-', ' ').title()

        # Poster
        poster_src = secici.select_attr("div.category_image img", "src") or secici.select_attr("meta[property='og:image']", "content")
        poster = self.fix_url(poster_src) if poster_src else ""

        # Year - regex ile çıkarma (xpath yerine)
        year = secici.regex_first(r"(?is)Yapım Yılı.*?(\d{4})", secici.html)

        description_el = secici.select("div.diziyou_desc") or secici.select("div#icerikcat")
        description = ""
        if description_el:
             # Scriptleri temizle
             for script in secici.select("script", description_el[0]):
                  script.decompose()
             description = secici.select_text(None, description_el[0])

        tags = [secici.select_text(None, a) for a in secici.select("div.genres a") if secici.select_text(None, a)]

        # Rating - daha spesifik regex ile
        rating = secici.regex_first(r"(?is)IMDB\s*:\s*</span>([0-9.]+)", secici.html)

        # Actors - regex ile
        actors_raw = secici.regex_first(r"(?is)Oyuncular.*?</span>([^<]+)", secici.html)
        actors = [actor.strip() for actor in actors_raw.split(",") if actor.strip()] if actors_raw else []

        episodes = []
        # Episodes - div#scrollbar-container a (kısıtlı alan)
        for link in secici.select("div#scrollbar-container a"):
            ep_href = secici.select_attr(None, "href", link)
            if not ep_href:
                continue

            # Link metni veya alt başlık al
            ep_name = (secici.select_text(None, link) or "").strip()
            title_child = secici.select_text("div.baslik", link) or secici.select_text("div.bolumismi", link)
            if title_child:
                ep_name = title_child

            # Önce metin üzerinden sezon/bölüm çıkart
            s_val, e_val = HTMLHelper.extract_season_episode(ep_name)

            # URL bazlı kalıplar: -1-sezon-2-bolum gibi
            if not (s_val or e_val):
                    pairs = HTMLHelper(ep_href).regex_all(r"-(\d+)-sezon-(\d+)-bolum")
                    if pairs:
                        s_val, e_val = int(pairs[0][0]), int(pairs[0][1])
                    else:
                        pairs = HTMLHelper(ep_href).regex_all(r"(\d+)-sezon-(\d+)-bolum")
                        if pairs:
                            s_val, e_val = int(pairs[0][0]), int(pairs[0][1])
                        else:
                            e_val_str = HTMLHelper(ep_href).regex_first(r"(\d+)-bolum")
                            if e_val_str:
                                e_val = int(e_val_str)
            # Metin üzerinden son bir deneme
            if not e_val:
                e_str = HTMLHelper(ep_name).regex_first(r"(\d+)\s*\.\s*[Bb]ölüm")
                if e_str:
                    e_val = int(e_str)
            if not s_val:
                s_str = HTMLHelper(ep_name).regex_first(r"(\d+)\s*\.\s*[Ss]ezon")
                if s_str:
                    s_val = int(s_str)

            if e_val or HTMLHelper(ep_href).regex_first(r"-\d+-sezon-\d+-bolum"):
                episodes.append(Episode(
                    season  = s_val,
                    episode = e_val,
                    title   = ep_name if ep_name else None,
                    url     = self.fix_url(ep_href),
                ))

        return SeriesInfo(
            url         = url,
            poster      = poster,
            title       = title,
            description = description,
            tags        = tags,
            rating      = rating,
            year        = year,
            episodes    = episodes,
            actors      = actors
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        # Title ve episode name - None kontrolü ekle
        item_title = secici.select_text("div.title h1")
        ep_name = secici.select_text("div#bolum-ismi")
        
        # Player src'den item_id çıkar
        # Player src'den item_id çıkar - önce özel player seçicisini dene
        player_src = None
        # Yaygın locatorlar
        for sel in ["iframe#diziyouPlayer", "div.player iframe", "iframe[src*='/player/']", "iframe[src*='/episodes/']", "iframe"]:
            p = secici.select_attr(sel, "src")
            if p and any(x in p.lower() for x in ["/player/", "/episodes/", "diziyou"]):
                player_src = p
                break

        # Eğer hâlâ bulunamadıysa, varsa bir bölüm sayfasına git ve oradan player'ı çek
        if not player_src:
            for a in secici.select("a"):
                href = secici.select_attr("a", "href", a)
                if not href:
                    continue
                if HTMLHelper(href).regex_first(r"(-\d+-sezon-\d+-bolum|/bolum|/episode|/episodes|/play)"):
                        break

        if not player_src:
            return []  # Player bulunamadıysa boş liste döndür

        item_id = player_src.split("/")[-1].replace(".html", "")

        subtitles   = []
        stream_urls = []

        for secenek in secici.select("span.diziyouOption"):
            opt_id  = secici.select_attr("span.diziyouOption", "id", secenek)
            op_name = secici.select_text("span.diziyouOption", secenek)

            match opt_id:
                case "turkceAltyazili":
                    subtitles.append(Subtitle(
                        name = op_name,
                        url  = self.fix_url(f"{self.main_url.replace('www', 'storage')}/subtitles/{item_id}/tr.vtt"),
                    ))
                    veri = {
                        "dil": "Orjinal Dil (TR Altyazı)",
                        "url": f"{self.main_url.replace('www', 'storage')}/episodes/{item_id}/play.m3u8"
                    }
                    if veri not in stream_urls:
                        stream_urls.append(veri)
                case "ingilizceAltyazili":
                    subtitles.append(Subtitle(
                        name = op_name,
                        url  = self.fix_url(f"{self.main_url.replace('www', 'storage')}/subtitles/{item_id}/en.vtt"),
                    ))
                    veri = {
                        "dil": "Orjinal Dil (EN Altyazı)",
                        "url": f"{self.main_url.replace('www', 'storage')}/episodes/{item_id}/play.m3u8"
                    }
                    if veri not in stream_urls:
                        stream_urls.append(veri)
                case "turkceDublaj":
                    stream_urls.append({
                        "dil": "Türkçe Dublaj",
                        "url": f"{self.main_url.replace('www', 'storage')}/episodes/{item_id}_tr/play.m3u8"
                    })

        results = []
        for stream in stream_urls:
            results.append(ExtractResult(
                url       = stream.get("url"),
                name      = f"{stream.get('dil')}",
                referer   = url,
                subtitles = subtitles
            ))

        return results