# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from ..Extractor.ExtractorModels import ExtractResult, Subtitle
import asyncio, re


class PluginResultsMixin:
    _SUBTITLE_LANG_KEYWORDS: dict[str, tuple[str, ...]] = {
        "tr" : ("tr", "tur", "turkish", "türkçe", "turkce"),
        "en" : ("en", "eng", "english", "ingilizce", "i̇ngilizce"),
        "fr" : ("fr", "fra", "fre", "french", "fransızca", "fransizca"),
        "de" : ("de", "ger", "deu", "german", "almanca"),
        "es" : ("es", "spa", "spanish", "ispanyolca", "i̇spanyolca"),
        "ru" : ("ru", "rus", "russian", "rusça", "rusca"),
        "uk" : ("uk", "ukr", "ukrainian", "ukraynaca"),
        "ar" : ("ar", "ara", "arabic", "arapça", "arapca"),
        "hi" : ("hi", "hin", "hindi"),
        "zh" : ("zh", "chi", "chinese", "çince", "cince"),
    }

    def collect_results(self, results: list[ExtractResult], data: ExtractResult | list[ExtractResult] | None):
        """
        extract() dönüşünü (tekil, liste veya None) sonuç listesine ekler.
        28+ plugin'de tekrar eden pattern'i ortadan kaldırır.

        Kullanım:
            data = await self.extract(url)
            self.collect_results(results, data)
        """
        if data:
            results.extend(data if isinstance(data, list) else [data])

    @staticmethod
    def deduplicate(results: list[ExtractResult], key: str = "url") -> list[ExtractResult]:
        """
        Sonuç listesinden tekrar eden URL'leri kaldırır.

        Args:
            results : ExtractResult listesi
            key     : Deduplicate anahtarı ("url" veya "url+name")
        """
        seen    = set()
        uniques = []
        for res in results:
            k = (res.url, res.name) if key == "url+name" else res.url
            if k and k not in seen:
                uniques.append(res)
                seen.add(k)
        return uniques

    @staticmethod
    async def gather_with_limit(tasks: list, limit: int = 5):
        """
        Semaphore ile rate-limited paralel çalıştırma.

        Kullanım:
            tasks   = [self.extract(url) for url in urls]
            results = await self.gather_with_limit(tasks, limit=5)
        """
        sem = asyncio.Semaphore(limit)

        async def limited(coro):
            entered = False
            try:
                async with sem:
                    entered = True
                    return await coro
            except asyncio.CancelledError:
                if not entered and asyncio.iscoroutine(coro):
                    coro.close()
                raise

        return await asyncio.gather(*(limited(t) for t in tasks))

    @staticmethod
    def new_subtitle(url: str, name: str = "Altyazı") -> Subtitle:
        """Hızlı Subtitle nesnesi oluşturur."""
        return Subtitle(name=name, url=url)

    @classmethod
    def _subtitle_lang_bucket(cls, name: str) -> str:
        """Bir altyazı adından kaba bir dil-grubu anahtarı çıkarır.

        Bilinen bir dile eşleşmezse (ör. "Forced", "Altyazı 3") adın kendisi
        kendi grubu olur - böylece alakasız etiketler birbirine karışıp
        yanlışlıkla aynı "diğer" havuzunda 2'ye düşürülmez.
        """
        lowered = name.lower()
        # " (2)" gibi sync_subtitles'ın kendi eklediği numaralandırmayı yok say.
        base   = re.sub(r"\s*\(\d+\)\s*$", "", lowered)
        tokens = base.replace("|", " ").replace("-", " ").replace("_", " ").split()
        for lang, keywords in cls._SUBTITLE_LANG_KEYWORDS.items():
            for token in tokens:
                if token in keywords:
                    return lang
        return f"other:{base.strip()}"

    @staticmethod
    def sync_subtitles(results: list[ExtractResult], max_per_language: int = 2) -> list[ExtractResult]:
        """
        Tüm ExtractResult'lardaki altyazıları birleştirir ve her sonuca dağıtır.

        - Aynı URL'ye sahip altyazılar tekrarlanmaz.
        - Aynı isme sahip farklı URL'ler "İsim", "İsim (2)" şeklinde numaralandırılır.
        - Her dil grubundan en fazla `max_per_language` altyazı tutulur (çok
          sunuculu eklentilerde onlarca aynı-dilde-farklı-URL altyazı birikmesini
          önler - bkz. `_subtitle_lang_bucket`).
        - Engine tarafından her load_links çağrısından sonra otomatik uygulanır.
        """
        if not results:
            return results

        # 1. Tüm altyazıları URL'ye göre topla (dedup)
        seen_urls: dict[str, Subtitle] = {}
        for res in results:
            for sub in res.subtitles:
                if sub.url not in seen_urls:
                    seen_urls[sub.url] = sub

        if not seen_urls:
            return results

        # 2. Aynı isimli farklı URL'leri numaralandır
        merged                      = list(seen_urls.values())
        name_count : dict[str, int] = {}
        for sub in merged:
            name_count[sub.name] = name_count.get(sub.name, 0) + 1

        name_idx      : dict[str, int] = {}
        numbered_subs : list[Subtitle] = []
        for sub in merged:
            if name_count[sub.name] > 1:
                idx              = name_idx.get(sub.name, 0) + 1
                name_idx[sub.name] = idx
                label            = sub.name if idx == 1 else f"{sub.name} ({idx})"
                numbered_subs.append(Subtitle(name=label, url=sub.url))
            else:
                numbered_subs.append(sub)

        # 3. Dil grubuna göre en fazla `max_per_language` tanesini tut (giriş
        #    sırası = sonuçlardaki server önceliği, o yüzden ilk gelenler kazanır).
        bucket_counts : dict[str, int] = {}
        final_subs    : list[Subtitle] = []
        for sub in numbered_subs:
            bucket = PluginResultsMixin._subtitle_lang_bucket(sub.name)
            count  = bucket_counts.get(bucket, 0)
            if count >= max_per_language:
                continue
            bucket_counts[bucket] = count + 1
            final_subs.append(sub)

        # 4. Birleşik listeyi tüm sonuçlara ata
        for res in results:
            res.subtitles = list(final_subs)

        return results
