# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

import sys, os
from pathlib import Path

# -- Ana dizine geçip path ekle
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir   = str(Path(script_dir).parent.parent)
os.chdir(root_dir)
sys.path.insert(0, root_dir)
# ---------------------------------------------------------->

import asyncio
import json
from KekikStream.CLI  import konsol
from KekikStream.Core import PluginManager, ExtractorManager, PluginBase
from rich.progress    import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn, TaskID
from rich.live        import Live
from rich.panel       import Panel

class PluginAuditor:
    def __init__(self, output_file="audit_results.json", concurrency=10):
        self.output_file = output_file
        self.concurrency = concurrency
        self.semaphore   = asyncio.Semaphore(concurrency)
        self.results     = {}

        if os.path.exists(self.output_file):
            with open(self.output_file, "r", encoding="utf-8") as f:
                try:
                    self.results = json.load(f)
                except json.JSONDecodeError:
                    self.results = {}

    def save_results(self):
        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)

    async def audit_category(self, plugin_name: str, plugin_instance: PluginBase, url: str, category: str, progress: Progress, task_id: TaskID):
        try:
            async with self.semaphore:
                # Sayfa 1 kontrolü
                p1_results = await plugin_instance.get_main_page(page=1, url=url, category=category)
                p1_count   = len(p1_results) if p1_results else 0

                # Sayfa 2 kontrolü
                p2_results = await plugin_instance.get_main_page(page=2, url=url, category=category)
                p2_count   = len(p2_results) if p2_results else 0

                status = "Working" if p1_count > 0 else "Broken/Empty"

                res = {
                    "url"          : url,
                    "category"     : category,
                    "page_1_count" : p1_count,
                    "page_2_count" : p2_count,
                    "status"       : status
                }

                if plugin_name not in self.results:
                    self.results[plugin_name] = {}

                self.results[plugin_name][category] = res

        except Exception as e:
            if plugin_name not in self.results:
                self.results[plugin_name] = {}
            self.results[plugin_name][category] = {
                "url"      : url,
                "category" : category,
                "error"    : str(e),
                "status"   : "Error"
            }
        finally:
            progress.advance(task_id)

    async def audit_plugin(self, plugin_name: str, plugin_instance: PluginBase, progress: Progress):
        if not hasattr(plugin_instance, "main_page") or not plugin_instance.main_page:
            return

        categories = plugin_instance.main_page
        total_cats = len(categories)

        task_id = progress.add_task(f"[cyan]→ {plugin_name}[/]", total=total_cats)

        tasks = []
        for url, category in categories.items():
            tasks.append(self.audit_category(plugin_name, plugin_instance, url, category, progress, task_id))

        await asyncio.gather(*tasks)

        # Batch save after each plugin
        self.save_results()
        progress.remove_task(task_id)

    async def run(self):
        konsol.print(Panel.fit(
            "[bold green]KekikStream Eklenti Denetçisi[/]\n"
            "[dim]Tüm eklentilerdeki kategoriler Sayfa 1 ve 2 için paralel taranıyor...[/]",
            border_style="cyan"
        ))

        # Plugin ve Extractor dizinlerini ayarla (KekikStream paketi içinden)
        base_dir      = os.path.join(root_dir, "KekikStream")
        extractor_dir = os.path.join(base_dir, "Extractors")
        plugin_dir    = os.path.join(base_dir, "Plugins")

        ex_manager     = ExtractorManager(extractor_dir=extractor_dir)
        plugin_manager = PluginManager(plugin_dir=plugin_dir, ex_manager=ex_manager)

        plugin_names = plugin_manager.get_plugin_names()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=40),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console   = konsol,
            transient = True # Alt bar bittikten sonra silinsin
        ) as progress:

            main_task = progress.add_task("[bold magenta]Genel İlerleme[/]", total=len(plugin_names))

            for name in plugin_names:
                instance = plugin_manager.select_plugin(name)
                if instance:
                    await self.audit_plugin(name, instance, progress)
                    await instance.close()
                progress.advance(main_task)

        # Özet Tablosu
        konsol.rule("[bold green]Denetim Tamamlandı")
        self.print_summary()
        konsol.print(f"\n[bold yellow][*][/][green] Detaylı sonuçlar [bold cyan]{self.output_file}[/] dosyasına kaydedildi.[/green]")

    def print_summary(self):
        from rich.table import Table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Eklenti", style="cyan")
        table.add_column("Toplam Kategori", justify="center")
        table.add_column("Çalışan", justify="center", style="green")
        table.add_column("Hatalı/Boş", justify="center", style="red")

        for plugin, items in sorted(self.results.items(), key=lambda x: len(x[1]), reverse=True):
            total   = len(items)
            working = sum(1 for cat in items.values() if cat.get("status") == "Working")
            failed  = total - working
            table.add_row(plugin, str(total), str(working), str(failed))

        konsol.print(table)

if __name__ == "__main__":
    # Concurrency 10-15 arası idealdir, çok yüksek sitelerden ban yemenize sebep olabilir.
    auditor = PluginAuditor(concurrency=10)
    try:
        asyncio.run(auditor.run())
    except KeyboardInterrupt:
        konsol.print("\n[bold red]中止 İptal edildi. Mevcut veriler kaydediliyor...[/]")
        auditor.save_results()
    except Exception as e:
        konsol.print(f"\n[bold red](!) Beklenmedik hata:[/] {e}")
