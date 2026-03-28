# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

import asyncio
import os
import sys
import json
from pathlib     import Path
from random      import choice
from collections import deque

# -- Ana dizine geçip path ekle
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir   = str(Path(script_dir).parent.parent)
os.chdir(root_dir)
sys.path.insert(0, root_dir)

from KekikStream.CLI  import konsol
from KekikStream.Core import PluginManager, ExtractorManager, PluginBase, MainPageResult, SearchResult
from rich.progress    import Progress, SpinnerColumn, TextColumn, BarColumn, TaskID
from rich.live        import Live
from rich.table       import Table
from rich.panel       import Panel
from rich.console     import Group
from rich.columns     import Columns

class MasterAuditor:
    def __init__(self, concurrency=10):
        self.concurrency = concurrency
        self.semaphore   = asyncio.Semaphore(concurrency)
        self.results     = {}
        self.active      = set()
        self.recent      = deque(maxlen=12)

        base_dir      = os.path.join(root_dir, "KekikStream")
        extractor_dir = os.path.join(base_dir, "Extractors")
        plugin_dir    = os.path.join(base_dir, "Plugins")

        self.ex_manager     = ExtractorManager(extractor_dir=extractor_dir)
        self.plugin_manager = PluginManager(plugin_dir=plugin_dir, ex_manager=self.ex_manager)

    async def check_category(self, instance, url, category):
        """Tek bir kategoriyi test eder."""
        try:
            # 5 saniyelik katı zaman aşımı
            res = await asyncio.wait_for(instance.get_main_page(page=1, url=url, category=category), timeout=7)
            return len(res) if res else 0
        except:
            return 0

    async def audit_plugin(self, name: str, progress: Progress, task_id: TaskID, live: Live):
        async with self.semaphore:
            self.active.add(name)
            report = {
                "categories" : {"total": 0, "working": 0, "broken": 0},
                "lifecycle"  : {"main_page": "⏳", "search": "⏳", "load_item": "⏳", "load_links": "⏳"},
                "item_count" : 0
            }
            self.results[name] = report
            live.update(self.make_layout(progress))

            try:
                instance = self.plugin_manager.select_plugin(name)
                if not instance:
                    self.results[name]["status"] = "FAILED"
                    return

                # 1. Kategori Taraması (PARALEL)
                cats = instance.main_page
                report["categories"]["total"] = len(cats)

                # Çalışan kategorileri takip et
                working_cats = []

                async def check_and_track(u, n):
                    count = await self.check_category(instance, u, n)
                    if count > 0:
                        working_cats.append((u, n))
                    return count

                cat_tasks   = [check_and_track(url, cat_name) for url, cat_name in cats.items()]
                cat_results = await asyncio.gather(*cat_tasks)

                for count in cat_results:
                    if count > 0:
                        report["categories"]["working"] += 1
                        report["item_count"] += count
                    else:
                        report["categories"]["broken"] += 1

                live.update(self.make_layout(progress))

                # 2. Yaşam Döngüsü (Hızlı Kontrol)
                if working_cats:
                    test_url, test_cat = choice(working_cats)
                elif cats:
                    test_url = list(cats.keys())[0]
                    test_cat = cats[test_url]
                else:
                    test_url = None

                if test_url:
                    try:
                        # Main Page
                        main_res = await asyncio.wait_for(instance.get_main_page(page=1, url=test_url, category=test_cat), timeout=10)
                        if main_res:
                            report["lifecycle"]["main_page"] = "✅"
                            target = main_res[0]

                            # Load Item
                            item_info = await asyncio.wait_for(instance.load_item(target.url), timeout=10)
                            if item_info and (getattr(item_info, 'title', None) or getattr(item_info, 'description', None)):
                                report["lifecycle"]["load_item"] = "✅"

                                # Load Links
                                links = await asyncio.wait_for(instance.load_links(item_info.url), timeout=15)
                                report["lifecycle"]["load_links"] = "✅" if links else "❌"
                            else:
                                report["lifecycle"]["load_item"] = "❌"
                        else:
                            report["lifecycle"]["main_page"] = "❌"
                    except:
                        report["lifecycle"]["main_page"] = "❌"
                else:
                    report["lifecycle"]["main_page"] = "❌"

                live.update(self.make_layout(progress))

                # 3. Search
                try:
                    s_res = await asyncio.wait_for(instance.search("love"), timeout=10)
                    report["lifecycle"]["search"] = "✅" if s_res else "❌"
                except:
                    report["lifecycle"]["search"] = "❌"

                await instance.close()

            except Exception as e:
                report["error"] = str(e)
            finally:
                self.active.discard(name)
                self.recent.append(name)
                progress.advance(task_id)
                live.update(self.make_layout(progress))

    def generate_table(self, limit_view=True):
        table = Table(expand=True, box=None, show_edge=False, border_style="dim")
        table.add_column("Eklenti", style="cyan", width=20)
        table.add_column("Kategoriler", justify="center", width=15)
        table.add_column("Ana Sayfa", justify="center", width=10)
        table.add_column("Arama", justify="center", width=10)
        table.add_column("Detay", justify="center", width=10)
        table.add_column("Linkler", justify="center", width=10)
        table.add_column("Durum", justify="right")

        if limit_view:
            names_to_show = list(self.active) + [n for n in list(self.recent) if n not in self.active]
            names_to_show = sorted(names_to_show)
        else:
            def sort_key(n):
                r    = self.results.get(n, {})
                cats = r.get("categories", {"working":0})
                lc   = r.get("lifecycle", {})
                return cats["working"] + sum(2 for v in lc.values() if v == "✅")
            names_to_show = sorted(self.results.keys(), key=sort_key, reverse=True)

        for name in names_to_show:
            r = self.results.get(name)
            if not r: continue
            cats    = r.get("categories", {"working":0, "total":0})
            lc      = r.get("lifecycle", {})
            cat_str = f"{cats['working']}/{cats['total']}"
            if cats.get('broken', 0) > 0: cat_str = f"[yellow]{cat_str}[/]"

            if name in self.active:
                status = "[bold pulse blue]Taranıyor...[/]"
            elif r.get("status") == "FAILED":
                status = "[bold red]HATA[/]"
            elif cats['working'] == 0:
                status = "[bold red]KRİTİK[/]"
            elif "❌" in lc.values():
                status = "[bold yellow]Bakım[/]"
            else:
                status = "[bold green]Stabil[/]"

            table.add_row(name, cat_str, lc.get("main_page", "-"), lc.get("search", "-"), lc.get("load_item", "-"), lc.get("load_links", "-"), status)
        return table

    def make_stats(self):
        total   = len(self.results)
        working = sum(1 for r in self.results.values() if r.get("categories", {}).get("working", 0) > 0)
        perfect = sum(1 for r in self.results.values() if all(v == "✅" for v in r.get("lifecycle", {}).values()))
        stats   = [
            Panel(f"[bold white]{total}[/]\n[dim]Eklenti[/]", border_style="cyan"),
            Panel(f"[bold green]{working}[/]\n[dim]Çalışan[/]", border_style="green"),
            Panel(f"[bold gold1]{perfect}[/]\n[dim]Kusursuz[/]", border_style="gold1"),
        ]
        return Columns(stats, expand=True)

    def make_layout(self, progress: Progress):
        return Panel(Group(self.make_stats(), self.generate_table(limit_view=True), Panel(progress, border_style="dim")), title="[bold green]KekikStream Master Audit[/]", border_style="cyan")

    async def run(self):
        plugin_names   = self.plugin_manager.get_plugin_names()
        original_quiet = konsol.quiet
        konsol.quiet   = True
        progress       = Progress(SpinnerColumn(), TextColumn("[bold yellow]{task.description}"), BarColumn(bar_width=None), TextColumn("[progress.percentage]{task.percentage:>3.0f}%"))
        task_id        = progress.add_task("Eklentiler taranıyor...", total=len(plugin_names))

        with Live(self.make_layout(progress), refresh_per_second=10) as live:
            tasks = [self.audit_plugin(name, progress, task_id, live) for name in plugin_names]
            await asyncio.gather(*tasks)

        konsol.quiet = original_quiet
        konsol.print("\n[bold green]─ Denetim Tamamlandı ─[/]\n", self.generate_table(limit_view=False))
        with open("master_audit_results.json", "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        konsol.print(f"\n[*] Detaylı rapor [bold cyan]master_audit_results.json[/] dosyasına kaydedildi.")

if __name__ == "__main__":
    auditor = MasterAuditor()
    try:
        asyncio.run(auditor.run())
    except KeyboardInterrupt:
        pass
