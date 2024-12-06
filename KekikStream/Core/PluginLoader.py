# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from ..CLI       import konsol, cikis_yap
from .PluginBase import PluginBase
from pathlib     import Path
import os, importlib.util, traceback

class PluginLoader:
    def __init__(self, plugins_dir: str):
        self.local_plugins_dir  = Path(plugins_dir).resolve()
        self.global_plugins_dir = Path(__file__).parent.parent / plugins_dir
        if not self.local_plugins_dir.exists() and not self.global_plugins_dir.exists():
            konsol.log(f"[red][!] Extractor dizini bulunamadı: {self.plugins_dir}[/red]")
            cikis_yap(False)

    def load_all(self) -> dict[str, PluginBase]:
        plugins = {}

        if self.global_plugins_dir.exists():
            konsol.log(f"[green][*] Global Plugin dizininden yükleniyor: {self.global_plugins_dir}[/green]")
            plugins |= self._load_from_directory(self.global_plugins_dir)

        if self.local_plugins_dir.exists():
            konsol.log(f"[green][*] Yerel Plugin dizininden yükleniyor: {self.local_plugins_dir}[/green]")
            plugins |= self._load_from_directory(self.local_plugins_dir)

        if not plugins:
            konsol.print("[yellow][!] Yüklenecek bir Plugin bulunamadı![/yellow]")

        return dict(sorted(plugins.items()))

    def _load_from_directory(self, directory: Path) -> dict[str, PluginBase]:
        plugins = {}
        for file in os.listdir(directory):
            if file.endswith(".py") and not file.startswith("__"):
                module_name = file[:-3]
                if plugin := self._load_plugin(directory, module_name):
                    plugins[module_name] = plugin

        return plugins

    def _load_plugin(self, directory: Path, module_name: str):
        try:
            path = directory / f"{module_name}.py"
            spec = importlib.util.spec_from_file_location(module_name, path)
            if not spec or not spec.loader:
                raise ImportError(f"Spec oluşturulamadı: {module_name}")

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            for attr in dir(module):
                obj = getattr(module, attr)
                if isinstance(obj, type) and issubclass(obj, PluginBase) and obj is not PluginBase:
                    return obj()

        except Exception as hata:
            konsol.print(f"[red][!] Plugin yüklenirken hata oluştu: {module_name}\nHata: {hata}")
            konsol.print(f"[dim]{traceback.format_exc()}[/dim]")

        return None