# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from .CLI       import konsol, cikis_yap, hata_yakala, pypi_kontrol_guncelle
from .Core      import PluginManager, ExtractorManager, UIManager, MediaManager, PluginBase, ExtractorBase, SeriesInfo
from asyncio    import run
from contextlib import suppress

class KekikStream:
    def __init__(self):
        # Yönetici sınıflarını başlat
        self.eklentiler_yonetici        = PluginManager()
        self.cikaricilar_yonetici       = ExtractorManager()
        self.arayuz_yonetici            = UIManager()
        self.medya_yonetici             = MediaManager()
        self.suanki_eklenti: PluginBase = None

    async def baslat(self):
        # Konsolu temizle ve başlık göster
        self.arayuz_yonetici.clear_console()
        konsol.rule("[bold cyan]KekikStream Başlatılıyor[/bold cyan]")

        # Eklenti kontrolü
        if not self.eklentiler_yonetici.get_plugin_names():
            return konsol.print("[bold red]Hiçbir eklenti bulunamadı![/bold red]")

        try:
            await self.eklenti_secimi()
        finally:
            # Program kapanırken tüm eklentileri kapat
            await self.eklentiler_yonetici.close_plugins()

    async def sonuc_bulunamadi(self):
        # Sonuç bulunamadığında kullanıcıya seçenekler sun
        secim = await self.arayuz_yonetici.select_from_list(
            message = "Ne yapmak istersiniz?",
            choices = ["Tüm Eklentilerde Ara", "Ana Menü", "Çıkış"]
        )

        match secim:
            case "Tüm Eklentilerde Ara":
                await self.tum_eklentilerde_arama()
            case "Ana Menü":
                await self.baslat()
            case "Çıkış":
                cikis_yap(False)

    async def eklenti_secimi(self):
        # Fuzzy ile eklenti seçimi yap
        eklenti_adi = await self.arayuz_yonetici.select_from_fuzzy(
            message = "Arama yapılacak eklentiyi seçin:",
            choices = ["Tüm Eklentilerde Ara", *self.eklentiler_yonetici.get_plugin_names()]
        )

        if eklenti_adi == "Tüm Eklentilerde Ara":
            await self.tum_eklentilerde_arama()
        else:
            self.suanki_eklenti = self.eklentiler_yonetici.select_plugin(eklenti_adi)
            await self.eklenti_ile_arama()

    async def eklenti_ile_arama(self):
        # Seçilen eklentide arama yap
        self.arayuz_yonetici.clear_console()
        konsol.rule(f"[bold cyan]{self.suanki_eklenti.name} Eklentisinde Arama Yapın[/bold cyan]")

        # Kullanıcıdan sorgu al ve ara
        sorgu    = await self.arayuz_yonetici.prompt_text("Arama sorgusu girin:")
        sonuclar = await self.suanki_eklenti.search(sorgu)

        if not sonuclar:
            konsol.print("[bold red]Arama sonucu bulunamadı![/bold red]")
            return await self.sonuc_bulunamadi()

        if secilen_sonuc := await self.eklenti_sonuc_secimi(sonuclar):
            await self.sonuc_detaylari_goster({"plugin": self.suanki_eklenti.name, "url": secilen_sonuc})

    async def eklenti_sonuc_secimi(self, sonuclar):
        # Arama sonuçlarından birini seç
        return await self.arayuz_yonetici.select_from_fuzzy(
            message = "İçerik sonuçlarından birini seçin:",
            choices = [{"name": sonuc.title, "value": sonuc.url} for sonuc in sonuclar]
        )

    async def tum_eklentilerde_arama(self):
        # Tüm eklentilerde arama yap
        self.arayuz_yonetici.clear_console()
        konsol.rule("[bold cyan]Tüm Eklentilerde Arama Yapın[/bold cyan]")

        sorgu    = await self.arayuz_yonetici.prompt_text("Arama sorgusu girin:")
        sonuclar = await self.tum_eklentilerde_arama_sorgula(sorgu)

        if not sonuclar:
            return await self.sonuc_bulunamadi()

        secilen_sonuc = await self.tum_sonuc_secimi(sonuclar)

        if secilen_sonuc:
            return await self.sonuc_detaylari_goster(secilen_sonuc)

    async def tum_eklentilerde_arama_sorgula(self, sorgu: str) -> list:
        tum_sonuclar = []

        # Her eklentide arama yap
        for eklenti_adi, eklenti in self.eklentiler_yonetici.plugins.items():
            # Eklenti türü kontrolü
            if not isinstance(eklenti, PluginBase):
                konsol.print(f"[yellow][!] {eklenti_adi} geçerli bir PluginBase değil, atlanıyor...[/yellow]")
                continue

            konsol.log(f"[yellow][~] {eklenti_adi:<19} aranıyor...[/]")
            try:
                sonuclar = await eklenti.search(sorgu)
                if sonuclar:
                    # Sonuçları listeye ekle
                    tum_sonuclar.extend(
                        [{"plugin": eklenti_adi, "title": sonuc.title, "url": sonuc.url, "poster": sonuc.poster} for sonuc in sonuclar]
                    )
            except Exception as hata:
                konsol.print(f"[bold red]{eklenti_adi} » hata oluştu: {hata}[/bold red]")

        if not tum_sonuclar:
            konsol.print("[bold red]Hiçbir sonuç bulunamadı![/bold red]")
            await self.sonuc_bulunamadi()
            return []

        return tum_sonuclar

    async def tum_sonuc_secimi(self, sonuclar):
        # Tüm sonuçlardan birini seç
        secenekler = [
            {"name": f"[{sonuc['plugin']}]".ljust(21) + f" » {sonuc['title']}", "value": sonuc}
                for sonuc in sonuclar
        ]

        return await self.arayuz_yonetici.select_from_fuzzy(
            message = "Arama sonuçlarından bir içerik seçin:",
            choices = secenekler
        )

    async def sonuc_detaylari_goster(self, secilen_sonuc):
        try:
            # Seçilen sonucun detaylarını al
            if isinstance(secilen_sonuc, dict) and "plugin" in secilen_sonuc:
                eklenti_adi = secilen_sonuc["plugin"]
                url         = secilen_sonuc["url"]

                self.suanki_eklenti = self.eklentiler_yonetici.select_plugin(eklenti_adi)
            else:
                url = secilen_sonuc

            # Medya bilgilerini yükle (3 deneme hakkı)
            medya_bilgi = None
            for _ in range(3):
                with suppress(Exception):
                    medya_bilgi = await self.suanki_eklenti.load_item(url)
                    break
                if not medya_bilgi:
                    konsol.print("[bold red]Medya bilgileri yüklenemedi![/bold red]")
                    return await self.sonuc_bulunamadi()

        except Exception as hata:
            konsol.log(secilen_sonuc)
            return hata_yakala(hata)

        # Medya başlığını ayarla ve bilgileri göster
        self.medya_yonetici.set_title(f"{self.suanki_eklenti.name} | {medya_bilgi.title}")
        self.arayuz_yonetici.display_media_info(f"{self.suanki_eklenti.name} | {medya_bilgi.title}", medya_bilgi)

        # Dizi ise bölüm seçimi yap
        if isinstance(medya_bilgi, SeriesInfo):
            secilen_bolum = await self.arayuz_yonetici.select_from_fuzzy(
                message = "İzlemek istediğiniz bölümü seçin:",
                choices = [
                    {"name": f"{bolum.season}. Sezon {bolum.episode}. Bölüm - {bolum.title}", "value": bolum.url}
                        for bolum in medya_bilgi.episodes
                ]
            )
            if secilen_bolum:
                baglantilar = await self.suanki_eklenti.load_links(secilen_bolum)
                await self.baglanti_secenekleri_goster(baglantilar)
        else:
            baglantilar = await self.suanki_eklenti.load_links(medya_bilgi.url)
            await self.baglanti_secenekleri_goster(baglantilar)

    async def baglanti_secenekleri_goster(self, baglantilar):
        if not baglantilar:
            konsol.print("[bold red]Hiçbir bağlantı bulunamadı![/bold red]")
            return await self.sonuc_bulunamadi()

        # Bağlantıları çıkarıcılarla eşleştir
        haritalama = self.cikaricilar_yonetici.map_links_to_extractors(baglantilar)
        play_fonksiyonu_var = hasattr(self.suanki_eklenti, "play") and callable(getattr(self.suanki_eklenti, "play", None))
        # ! DEBUG
        # konsol.print(baglantilar)

        # Uygun çıkarıcı kontrolü
        if not haritalama and not play_fonksiyonu_var:
            konsol.print("[bold red]Hiçbir Extractor bulunamadı![/bold red]")
            konsol.print(baglantilar)
            return await self.sonuc_bulunamadi()

        # Doğrudan oynatma seçeneği
        if not haritalama:
            secilen_link = await self.arayuz_yonetici.select_from_list(
                message = "Doğrudan oynatmak için bir bağlantı seçin:",
                choices = [{"name": value["ext_name"], "value": key} for key, value in self.suanki_eklenti._data.items() if key in baglantilar]
            )
            if secilen_link:
                await self.medya_oynat(secilen_link)
            return

        # Kullanıcı seçenekleri
        secim = await self.arayuz_yonetici.select_from_list(
            message = "Ne yapmak istersiniz?",
            choices = ["İzle", "Tüm Eklentilerde Ara", "Ana Menü"]
        )

        match secim:
            case "İzle":
                secilen_link = await self.arayuz_yonetici.select_from_list(
                    message = "İzlemek için bir bağlantı seçin:",
                    choices = [{"name": cikarici_adi, "value": link} for link, cikarici_adi in haritalama.items()]
                )
                if secilen_link:
                    await self.medya_oynat(secilen_link)

            case "Tüm Eklentilerde Ara":
                await self.tum_eklentilerde_arama()

            case _:
                await self.baslat()

    async def medya_oynat(self, secilen_link):
        # Eklentinin kendi oynatıcısı varsa onu kullan
        if hasattr(self.suanki_eklenti, "play") and callable(self.suanki_eklenti.play):
            konsol.log(f"[yellow][»] Oynatılıyor : {secilen_link}")
            return await self.suanki_eklenti.play(
                name      = self.suanki_eklenti._data[secilen_link]["name"],
                url       = secilen_link,
                referer   = self.suanki_eklenti._data[secilen_link]["referer"],
                subtitles = self.suanki_eklenti._data[secilen_link]["subtitles"]
            )

        # Uygun çıkarıcıyı bul
        cikarici: ExtractorBase = self.cikaricilar_yonetici.find_extractor(secilen_link)
        if not cikarici:
            return konsol.print("[bold red]Uygun Extractor bulunamadı.[/bold red]")

        try:
            # Medya bilgilerini çıkar
            extract_data = await cikarici.extract(secilen_link, referer=self.suanki_eklenti.main_url)
        except Exception as hata:
            konsol.print(f"[bold red]{cikarici.name} » hata oluştu: {hata}[/bold red]")
            return await self.sonuc_bulunamadi()

        # Birden fazla bağlantı varsa seçim yap
        if isinstance(extract_data, list):
            secilen_data = await self.arayuz_yonetici.select_from_list(
                message = "Birden fazla bağlantı bulundu, lütfen birini seçin:",
                choices = [{"name": data.name, "value": data} for data in extract_data]
            )
        else:
            secilen_data = extract_data

        # Cookie varsa ayarla
        if secilen_data.headers.get("Cookie"):
            self.medya_yonetici.set_headers({"Cookie": secilen_data.headers.get("Cookie")})

        # Başlık ve referrer ayarla
        self.medya_yonetici.set_title(f"{self.medya_yonetici.get_title()} | {secilen_data.name}")
        self.medya_yonetici.set_headers({"Referer": secilen_data.referer})
        konsol.log(f"[yellow][»] Oynatılıyor : {secilen_data.url}")
        self.medya_yonetici.play_media(secilen_data)

def basla():
    try:
        # PyPI güncellemelerini kontrol et
        pypi_kontrol_guncelle("KekikStream")

        # Uygulamayı başlat
        app = KekikStream()
        run(app.baslat())
        cikis_yap(False)
    except KeyboardInterrupt:
        cikis_yap(True)
    except Exception as hata:
        hata_yakala(hata)