# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from .CLI      import konsol, cikis_yap, hata_yakala
from .Managers import PluginManager, ExtractorManager, UIManager, MediaManager
from .Core     import PluginBase, ExtractorBase
from asyncio   import run

class KekikStream:
    def __init__(self):
        self.plugin_manager            = PluginManager()
        self.extractor_manager         = ExtractorManager()
        self.ui_manager                = UIManager()
        self.media_manager             = MediaManager()
        self.current_plugin:PluginBase = None

    async def run(self):
        self.ui_manager.clear_console()
        konsol.rule("[bold cyan]KekikStream Başlatılıyor[/bold cyan]")
        if not self.plugin_manager.get_plugin_names():
            konsol.print("[bold red]Hiçbir eklenti bulunamadı![/bold red]")
            return

        try:
            await self.select_plugin()
        finally:
            await self.plugin_manager.close_plugins()

    async def select_plugin(self):
        plugin_name = await self.ui_manager.select_from_list(
            message = "Bir eklenti seçin:",
            choices = self.plugin_manager.get_plugin_names()
        )

        self.current_plugin = self.plugin_manager.select_plugin(plugin_name)

        await self.search()

    async def search(self):
        self.ui_manager.clear_console()
        konsol.rule(f"[bold cyan]{self.current_plugin.name} Eklentisinde Arama Yapın[/bold cyan]")

        query   = await self.ui_manager.prompt_text("Arama sorgusu girin:")
        results = await self.current_plugin.search(query)

        if not results:
            konsol.print("[bold red]Arama sonucu bulunamadı![/bold red]")
            return

        await self.select_result(results)

    async def select_result(self, results):
        selected_url = await self.ui_manager.select_from_list(
            message = "Bir içerik seçin:",
            choices = [{"name": res.title, "value": res.url} for res in results]
        )

        await self.show_details(selected_url)

    async def show_details(self, url):
        media_info = await self.current_plugin.load_item(url)

        self.media_manager.set_title(f"{self.current_plugin.name} | {media_info.title}")

        self.ui_manager.display_media_info(self.current_plugin.name, media_info)

        links = await self.current_plugin.load_links(url)
        await self.show_options(links)

    async def show_options(self, links):
        mapping = self.extractor_manager.map_links_to_extractors(links)
        action  = await self.ui_manager.select_from_list(
            message = "Ne yapmak istersiniz?",
            choices = ["İzle", "Geri Git", "Ana Menü"]
        )

        match action:
            case "İzle":
                selected_link = await self.ui_manager.select_from_list(
                    message = "Bir bağlantı seçin:", 
                    choices = [{"name": extractor_name, "value": link} for link, extractor_name in mapping.items()]
                )
                if selected_link:
                    await self.play_media(selected_link)

            case "Geri Git":
                await self.search()

            case _:
                await self.run()

    async def play_media(self, selected_link):
        extractor:ExtractorBase = self.extractor_manager.find_extractor(selected_link)
        if not extractor:
            konsol.print("[bold red]Uygun Extractor bulunamadı.[/bold red]")
            return

        extract_data = await extractor.extract(selected_link, referer=self.current_plugin.main_url)
        if extract_data.headers.get("Cookie"):
            self.media_manager.set_headers({"Cookie": extract_data.headers.get("Cookie")})

        self.media_manager.set_title(f"{self.media_manager.get_title()} | {extract_data.name}")
        self.media_manager.set_headers({"Referer": extract_data.referer})
        self.media_manager.play_media(extract_data)


def basla():
    try:
        app = KekikStream()
        run(app.run())
        cikis_yap(False)
    except KeyboardInterrupt:
        cikis_yap(True)
    except Exception as hata:
        hata_yakala(hata)