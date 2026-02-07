# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

# -- Ana dizine geçip path ekle
import sys, os

script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir   = os.path.dirname(script_dir)
os.chdir(root_dir)
sys.path.append(root_dir)
# ---------------------------------------------------------->

from KekikStream.CLI  import konsol
from asyncio          import run
from KekikStream.Core import PluginManager, ExtractorManager, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, ExtractResult
from random           import choice
from rich.table       import Table
from rich.panel       import Panel
from rich.text        import Text
from copy             import copy

class PluginValidator:
    """Her eklentinin tüm metotlarını ve veri modellerini doğrular."""

    def __init__(self):
        self.ext     = ExtractorManager()
        self.plugins = PluginManager(ex_manager=self.ext)
        self.results = {}

    def validate_model_completeness(self, obj, model_name: str) -> dict:
        """Model alanlarının doluluğunu kontrol eder."""
        issues = []
        fields = {}

        if isinstance(obj, (MovieInfo, SeriesInfo)):
            required_fields = ['url', 'title', 'description', 'tags', 'year', 'actors']
            for field in required_fields:
                value = getattr(obj, field, None)
                fields[field] = value
                if not value or value == "":
                    issues.append(f"{field} boş")

        elif isinstance(obj, Episode):
            if obj.season is None:
                issues.append("season boş")
            if obj.episode is None:
                issues.append("episode boş")
            if not obj.url:
                issues.append("url boş")

        return {"fields": fields, "issues": issues}

    async def test_get_main_page(self, plugin) -> dict:
        """get_main_page metodu test eder."""
        result = {"status": "❌", "message": "", "data": None}

        try:
            if not plugin.main_page:
                result["status"] = "⚠️"
                result["message"] = "main_page tanımlı değil"
                return result

            main_page_items = list(plugin.main_page.items())
            url, category = choice(main_page_items)
            items = await plugin.get_main_page(1, url, category)

            if not items:
                result["status"] = "⚠️"
                result["message"] = "İçerik bulunamadı"
                return result

            # İlk öğeyi kontrol et
            random_item = choice(items)
            konsol.print(random_item)
            if not isinstance(random_item, MainPageResult):
                result["message"] = f"Yanlış tip: {type(random_item).__name__}"
                return result

            # Model doğrulama
            issues = []
            if not random_item.title:
                issues.append("title boş")
            if not random_item.url:
                issues.append("url boş")
            if not random_item.category:
                issues.append("category boş")

            if issues:
                result["status"] = "⚠️"
                result["message"] = ", ".join(issues)
            else:
                result["status"] = "✅"
                result["message"] = f"{len(items)} öğe bulundu"

            result["data"] = random_item

        except Exception as e:
            result["message"] = f"Hata: {str(e)}"

        return result

    async def test_search(self, plugin, query: str = "adam") -> dict:
        """search metodu test eder."""
        result = {"status": "❌", "message": "", "data": None}

        try:
            if not hasattr(plugin, 'search') or not callable(getattr(plugin, 'search', None)):
                result["status"] = "⚠️"
                result["message"] = "search metodu yok"
                return result

            items = await plugin.search(query)

            if not items:
                result["status"] = "⚠️"
                result["message"] = "Sonuç bulunamadı"
                return result

            random_item = choice(items)
            konsol.print(random_item)
            if not isinstance(random_item, SearchResult):
                result["message"] = f"Yanlış tip: {type(random_item).__name__}"
                return result

            issues = []
            if not random_item.title:
                issues.append("title boş")
            if not random_item.url:
                issues.append("url boş")

            if issues:
                result["status"] = "⚠️"
                result["message"] = ", ".join(issues)
            else:
                result["status"] = "✅"
                result["message"] = f"{len(items)} sonuç"

            result["data"] = random_item

        except Exception as e:
            result["message"] = f"Hata: {str(e)}"

        return result

    async def test_load_item(self, plugin, test_url: str) -> dict:
        """load_item metodu test eder."""
        result = {"status": "❌", "message": "", "data": None}

        try:
            item = await plugin.load_item(test_url)

            # Terminal kirliliğini önlemek için SeriesInfo ise tek bölüm göster
            if isinstance(item, SeriesInfo) and item.episodes:
                item_copy = copy(item)
                item_copy.episodes = item.episodes[:1]
                konsol.print(item_copy)
                konsol.print(f"[dim italic]... ({len(item.episodes) - 1} bölüm daha var)[/]")
            else:
                konsol.print(item)

            if not item:
                result["message"] = "Boş sonuç"
                return result

            if not isinstance(item, (MovieInfo, SeriesInfo)):
                result["message"] = f"Yanlış tip: {type(item).__name__}"
                return result

            validation = self.validate_model_completeness(item, type(item).__name__)

            if isinstance(item, SeriesInfo):
                if not item.episodes or len(item.episodes) == 0:
                    validation["issues"].append("episodes boş")

            if validation["issues"]:
                result["status"] = "⚠️"
                result["message"] = ", ".join(validation["issues"])

            else:
                result["status"] = "✅"
                if isinstance(item, SeriesInfo):
                    result["message"] = f"{len(item.episodes)} bölüm"
                else:
                    result["message"] = "Tüm alanlar dolu"

            result["data"] = item

        except Exception as e:
            result["message"] = f"Hata: {str(e)}"

        return result

    async def test_load_links(self, plugin, test_url: str) -> dict:
        """load_links metodu test eder."""
        result = {"status": "❌", "message": "", "data": None}

        try:
            links = await plugin.load_links(test_url)

            if not links:
                result["status"] = "⚠️"
                result["message"] = "Link bulunamadı"
                return result

            first_link = choice(links)

            # ExtractResult objesi
            issues = []
            if not first_link.url:
                issues.append("url boş")
            if not first_link.name:
                issues.append("name boş")

            # Subtitle kontrolü
            subtitle_info = ""
            if first_link.subtitles:
                subtitle_info = f", {len(first_link.subtitles)} altyazı"

            result["message"] = f"{len(links)} link bulundu{subtitle_info}"

            if issues:
                result["status"] = "⚠️"
                result["message"] = ", ".join(issues)
            else:
                result["status"] = "✅"

            result["data"] = first_link

            konsol.print(links)

        except Exception as e:
            result["message"] = f"Hata: {str(e)}"

        return result

    async def validate_plugin(self, plugin_name: str) -> dict:
        """Bir eklentinin tüm metotlarını doğrular."""
        konsol.rule(f"[bold cyan]{plugin_name}")

        plugin = self.plugins.select_plugin(plugin_name)
        validation_results = {
            "plugin_name": plugin_name,
            "get_main_page": None,
            "search": None,
            "load_item": None,
            "load_links": None,
            "overall_status": "✅"
        }

        # 1. get_main_page testi
        konsol.log("[yellow]▶ get_main_page test ediliyor...")
        main_page_result = await self.test_get_main_page(plugin)
        validation_results["get_main_page"] = main_page_result
        konsol.log(f"  {main_page_result['status']} {main_page_result['message']}")

        # 2. search testi
        konsol.log("[yellow]▶ search test ediliyor...")
        search_result = await self.test_search(plugin)
        validation_results["search"] = search_result
        konsol.log(f"  {search_result['status']} {search_result['message']}")

        # 3. load_item testi (main_page sonucundan URL al)
        test_url = None
        if main_page_result["data"]:
            test_url = main_page_result["data"].url
        elif search_result["data"]:
            test_url = search_result["data"].url

        if test_url:
            konsol.log("[yellow]▶ load_item test ediliyor...")
            load_item_result = await self.test_load_item(plugin, test_url)
            validation_results["load_item"] = load_item_result
            konsol.log(f"  {load_item_result['status']} {load_item_result['message']}")

            # 4. load_links testi
            if load_item_result["data"]:
                link_url = test_url
                if isinstance(load_item_result["data"], SeriesInfo):
                    if load_item_result["data"].episodes and len(load_item_result["data"].episodes) > 0:
                        link_url = choice(load_item_result["data"].episodes).url

                if link_url:
                    konsol.log("[yellow]▶ load_links test ediliyor...")
                    konsol.log(f"[dim]URL: {link_url}[/]")
                    load_links_result = await self.test_load_links(plugin, link_url)
                    validation_results["load_links"] = load_links_result
                    konsol.log(f"  {load_links_result['status']} {load_links_result['message']}")

        # Genel durum belirleme
        for key, val in validation_results.items():
            if key == "plugin_name" or key == "overall_status":
                continue
            if val and val["status"] in ["❌", "⚠️"]:
                validation_results["overall_status"] = val["status"]
                if val["status"] == "❌":
                    break

        return validation_results

    def print_summary(self):
        """Tüm sonuçların özetini yazdırır."""
        konsol.rule("[bold green]ÖZET RAPOR")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Eklenti", style="cyan", width=20)
        table.add_column("main_page", justify="center", width=12)
        table.add_column("search", justify="center", width=12)
        table.add_column("load_item", justify="center", width=12)
        table.add_column("load_links", justify="center", width=12)
        table.add_column("Durum", justify="center", width=8)

        stats = {"✅": 0, "⚠️": 0, "❌": 0}

        for plugin_name, results in self.results.items():
            status = results["overall_status"]
            stats[status] = stats.get(status, 0) + 1

            table.add_row(
                plugin_name,
                results["get_main_page"]["status"] if results["get_main_page"] else "➖",
                results["search"]["status"] if results["search"] else "➖",
                results["load_item"]["status"] if results["load_item"] else "➖",
                results["load_links"]["status"] if results["load_links"] else "➖",
                status
            )

        konsol.print(table)
        konsol.print()
        konsol.print(f"[green]✅ Kusursuz: {stats.get('✅', 0)}")
        konsol.print(f"[yellow]⚠️ Eksikli: {stats.get('⚠️', 0)}")
        konsol.print(f"[red]❌ Hatalı: {stats.get('❌', 0)}")

async def main():
    validator = PluginValidator()

    if len(sys.argv) >= 2:
        plugin_name = sys.argv[1].split(",")
        for name in plugin_name:
            if name not in validator.plugins.get_plugin_names():
                continue
            validator.results[name] = await validator.validate_plugin(name)
        validator.print_summary()
        return

    for plugin_name in validator.plugins.get_plugin_names():
        try:
            result = await validator.validate_plugin(plugin_name)
            validator.results[plugin_name] = result
        except Exception as e:
            konsol.log(f"[red]✗ {plugin_name} genel hata: {e}")
            validator.results[plugin_name] = {
                "plugin_name": plugin_name,
                "overall_status": "❌",
                "get_main_page": {"status": "❌", "message": str(e)},
                "search": None,
                "load_item": None,
                "load_links": None
            }

    validator.print_summary()

if __name__ == "__main__":
    run(main())
