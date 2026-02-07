# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from .CLI       import konsol, cikis_yap, hata_yakala, pypi_kontrol_guncelle
from .Core      import PluginManager, ExtractorManager, UIManager, MediaManager, PluginBase, ExtractorBase, SeriesInfo, ExtractResult
from asyncio    import run, TaskGroup, Semaphore
from contextlib import suppress

class KekikStream:
    def __init__(self):
        self.extractor = ExtractorManager()
        self.plugin    = PluginManager(ex_manager=self.extractor)
        self.ui        = UIManager()
        self.media     = MediaManager()

        self.current_plugin: PluginBase = None
        self.is_series                  = False
        self.series_info: SeriesInfo    = None
        self.current_episode_index      = -1
        self.episode_title              = ""

    async def show_header(self, title: str):
        """Konsolu temizle ve başlık göster"""
        self.ui.clear_console()
        konsol.rule(title)

    def update_title(self, new_info: str):
        """Medya başlığına yeni bilgi ekle"""
        if not new_info:
            return
        current = self.media.get_title()
        if new_info not in current:
            self.media.set_title(f"{current} | {new_info}")

    async def load_media_info(self, url: str, retries=3):
        """Medya bilgilerini yükle"""
        for _ in range(retries):
            with suppress(Exception):
                return await self.current_plugin.load_item(url)
        konsol.print("[bold red]Medya bilgileri yüklenemedi![/bold red]")
        return None

    async def start(self):
        """Uygulamayı başlat"""
        await self.show_header("[bold cyan]KekikStream[/bold cyan]")

        if not self.plugin.get_plugin_names():
            konsol.print("[bold red]Eklenti bulunamadı![/bold red]")
            return

        try:
            await self.select_plugin()
        finally:
            await self.plugin.close_plugins()

    async def select_plugin(self):
        """Eklenti seçimi"""
        plugin_name = await self.ui.select_from_fuzzy(
            message = "Eklenti seçin:",
            choices = ["Tüm Eklentilerde Ara", *self.plugin.get_plugin_names()]
        )

        if plugin_name == "Tüm Eklentilerde Ara":
            await self.search_all_plugins()
        else:
            self.current_plugin = self.plugin.select_plugin(plugin_name)
            await self.search_in_plugin()

    async def search_in_plugin(self):
        """Seçili eklentide ara"""
        await self.show_header(f"[bold cyan]{self.current_plugin.name}[/bold cyan]")

        query   = await self.ui.prompt_text("Arama sorgusu:")
        results = await self.current_plugin.search(query)

        if not results:
            konsol.print("[bold red]Sonuç bulunamadı![/bold red]")
            return await self.handle_no_results()

        choice = await self.ui.select_from_fuzzy(
            message = "Sonuç seçin:",
            choices = [{"name": r.title, "value": r.url} for r in results]
        )

        if choice:
            await self.show_media_details({"plugin": self.current_plugin.name, "url": choice})

    async def search_all_plugins(self):
        """Tüm eklentilerde ara"""
        await self.show_header("[bold cyan]Tüm Eklentilerde Ara[/bold cyan]")

        query = await self.ui.prompt_text("Arama sorgusu:")
        all_results = []

        # Maksimum 5 eşzamanlı arama için semaphore
        semaphore = Semaphore(5)

        async def search_plugin(name: str, plugin: PluginBase):
            """Tek bir plugin'de ara (semaphore ile sınırlandırılmış)"""
            async with semaphore:
                konsol.log(f"[yellow][~] {name:<19} aranıyor...[/]")
                try:
                    results = await plugin.search(query)
                    if results:
                        return [
                            {"plugin": name, "title": r.title, "url": r.url, "poster": r.poster}
                            for r in results
                        ]
                except Exception as e:
                    konsol.print(f"[bold red]{name} hatası: {e}[/bold red]")
                return []

        # Tüm plugin'leri paralel olarak ara
        async with TaskGroup() as tg:
            tasks = []
            for name, plugin in self.plugin.plugins.items():
                tasks.append(tg.create_task(search_plugin(name, plugin)))

        # Sonuçları topla
        for task in tasks:
            all_results.extend(task.result())

        if not all_results:
            return await self.handle_no_results()

        choice = await self.ui.select_from_fuzzy(
            message = "Sonuç seçin:",
            choices = [
                {"name": f"[{r['plugin']}]".ljust(21) + f" » {r['title']}", "value": r}
                    for r in all_results
            ]
        )

        if choice:
            await self.show_media_details(choice)

    async def show_media_details(self, choice):
        """Seçilen medyanın detaylarını göster"""
        try:
            if isinstance(choice, dict) and "plugin" in choice:
                self.current_plugin = self.plugin.select_plugin(choice["plugin"])
                url = choice["url"]
            else:
                url = choice

            media_info = await self.load_media_info(url)
            if not media_info:
                return await self.handle_no_results()

        except Exception as e:
            return hata_yakala(e)

        self.media.set_title(f"{self.current_plugin.name} | {media_info.title}")
        self.ui.display_media_info(f"{self.current_plugin.name} | {media_info.title}", media_info)

        if isinstance(media_info, SeriesInfo):
            self.is_series   = True
            self.series_info = media_info
            await self.select_episode(media_info)
        else:
            self.reset_series_state()
            links = await self.current_plugin.load_links(media_info.url)
            await self.show_link_options(links)

    def reset_series_state(self):
        """Dizi durumunu sıfırla"""
        self.is_series             = False
        self.series_info           = None
        self.current_episode_index = -1
        self.episode_title         = ""

    async def select_episode(self, series_info: SeriesInfo):
        """Bölüm seç"""
        selected = await self.ui.select_from_fuzzy(
            message = "Bölüm seçin:",
            choices = [
                {
                    "name"  : f"{ep.season}. Sezon {ep.episode}. Bölüm" +  (f" - {ep.title}" if ep.title else ""),
                    "value" : ep.url
                }
                    for ep in series_info.episodes
            ]
        )

        if not selected:
            return await self.content_finished()

        # Bölüm bilgilerini kaydet
        for idx, ep in enumerate(series_info.episodes):
            if ep.url == selected:
                self.current_episode_index = idx
                self.episode_title = (f"{ep.season}. Sezon {ep.episode}. Bölüm" +  (f" - {ep.title}" if ep.title else ""))
                break

        links = await self.current_plugin.load_links(selected)
        await self.show_link_options(links)

    async def play_next_episode(self):
        """Sonraki bölümü oynat"""
        self.current_episode_index += 1
        next_ep = self.series_info.episodes[self.current_episode_index]
        self.episode_title = (f"{next_ep.season}. Sezon {next_ep.episode}. Bölüm" +  (f" - {next_ep.title}" if next_ep.title else ""))
        links = await self.current_plugin.load_links(next_ep.url)
        await self.show_link_options(links)

    async def ask_next_episode(self):
        """Dizi bittikten sonra ne yapılsın?"""
        await self.show_header(f"[bold cyan]{self.current_plugin.name}[/bold cyan]")
        self.ui.display_media_info(f"{self.current_plugin.name} | {self.series_info.title}",  self.series_info)
        konsol.print(f"[yellow][+][/yellow] [bold green]{self.episode_title}[/bold green] izlendi!")

        options = ["Bölüm Seç", "Ana Menü", "Çıkış"]
        if self.current_episode_index + 1 < len(self.series_info.episodes):
            options.insert(0, "Sonraki Bölüm")
        else:
            konsol.print("[bold yellow]Son bölümdü![/bold yellow]")

        choice = await self.ui.select_from_list("Ne yapmak istersiniz?", options)

        match choice:
            case "Sonraki Bölüm":
                await self.play_next_episode()
            case "Bölüm Seç":
                await self.select_episode(self.series_info)
            case "Ana Menü":
                await self.start()
            case "Çıkış":
                cikis_yap(False)

    async def show_link_options(self, links: list[ExtractResult]):
        """Bağlantı seçeneklerini göster"""
        if not links:
            konsol.print("[bold red]Bağlantı bulunamadı![/bold red]")
            return await self.handle_no_results()

        # Direkt oynatma - tüm pluginlerde artık play metodu var (PluginBase'den miras)
        return await self.play_direct(links)

    async def play_direct(self, links: list[ExtractResult]):
        """Plugin'in kendi metoduyla oynat"""
        selected = await self.ui.select_from_list(
            message = "Bağlantı seçin:",
            choices = [{"name": link.name or "Bilinmiyor", "value": link} for link in links]
        )

        if not selected:
            return await self.content_finished()

        self.update_title(self.episode_title)
        self.update_title(selected.name)

        await self.current_plugin.play(
            name       = self.media.get_title(),
            url        = selected.url,
            user_agent = selected.user_agent,
            referer    = selected.referer,
            subtitles  = selected.subtitles or []
        )
        return await self.content_finished()

    async def play_with_extractor(self, links: list[ExtractResult], mapping: dict):
        """Extractor ile oynat"""
        options = [
            {"name": link.name or mapping.get(link.url, "Bilinmiyor"), "value": link}
                for link in links if link.url in mapping
        ]

        if not options:
            konsol.print("[bold red]İzlenebilir bağlantı yok![/bold red]")
            return await self.content_finished()

        selected = await self.ui.select_from_list("Bağlantı seçin:", options)
        if not selected:
            return await self.content_finished()

        url = selected.url
        extractor: ExtractorBase = self.extractor.find_extractor(url)

        if not extractor:
            konsol.print("[bold red]Extractor bulunamadı![/bold red]")
            return await self.handle_no_results()

        try:
            referer = selected.referer or self.current_plugin.main_url
            extract_data = await extractor.extract(url, referer=referer)
        except Exception as e:
            konsol.print(f"[bold red]{extractor.name} hatası: {e}[/bold red]")
            return await self.handle_no_results()

        # Birden fazla link varsa seç
        if isinstance(extract_data, list):
            extract_data = await self.ui.select_from_list(
                message = "Bağlantı seçin:",
                choices = [{"name": d.name, "value": d} for d in extract_data]
            )

        if not extract_data:
            return await self.content_finished()

        # Başlıkları güncelle ve oynat
        self.update_title(self.episode_title)
        self.update_title(selected.name)
        self.update_title(extract_data.name)

        self.media.play_media(extract_data)
        await self.content_finished()

    async def content_finished(self):
        """İçerik bittiğinde ne yapsın?"""
        if self.is_series:
            await self.ask_next_episode()
        else:
            await self.start()

    async def handle_no_results(self):
        """Sonuç bulunamadığında"""
        choice = await self.ui.select_from_list("Ne yapmak istersiniz?", ["Tüm Eklentilerde Ara", "Ana Menü", "Çıkış"])
        match choice:
            case "Tüm Eklentilerde Ara":
                await self.search_all_plugins()
            case "Ana Menü":
                await self.start()
            case "Çıkış":
                cikis_yap(False)


def basla():
    try:
        # PyPI güncellemelerini kontrol et
        pypi_kontrol_guncelle("KekikStream")

        # Uygulamayı başlat
        app = KekikStream()
        run(app.start())
        cikis_yap(False)
    except KeyboardInterrupt:
        cikis_yap(True)
    except Exception as hata:
        hata_yakala(hata)
