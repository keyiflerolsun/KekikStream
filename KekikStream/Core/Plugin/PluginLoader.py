# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from ...CLI      import konsol, cikis_yap
from .PluginBase import PluginBase
from pathlib     import Path
import os, importlib.util, traceback

class PluginLoader:
    def __init__(self, plugins_dir: str):
        # Yerel ve global eklenti dizinlerini ayarla
        self.local_plugins_dir  = Path(plugins_dir).resolve()
        self.global_plugins_dir = Path(__file__).parent.parent.parent / plugins_dir

        # Dizin kontrolü
        if not self.local_plugins_dir.exists() and not self.global_plugins_dir.exists():
            # konsol.log(f"[red][!] Eklenti dizini bulunamadı: {plugins_dir}[/red]")
            cikis_yap(False)

    def load_all(self) -> dict[str, PluginBase]:
        plugins = {}

        # Global eklentileri yükle
        if self.global_plugins_dir.exists():
            # konsol.log(f"[green][*] Global Eklenti dizininden yükleniyor: {self.global_plugins_dir}[/green]")
            plugins |= self._load_from_directory(self.global_plugins_dir)

        # Yerel eklentileri yükle
        if self.local_plugins_dir.exists():
            # konsol.log(f"[green][*] Yerel Eklenti dizininden yükleniyor: {self.local_plugins_dir}[/green]")
            plugins |= self._load_from_directory(self.local_plugins_dir)

        if not plugins:
            konsol.print("[yellow][!] Yüklenecek bir Eklenti bulunamadı![/yellow]")

        return dict(sorted(plugins.items()))

    def _load_from_directory(self, directory: Path) -> dict[str, PluginBase]:
        plugins = {}

        # Dizindeki tüm .py dosyalarını tara
        for file in os.listdir(directory):
            if file.endswith(".py") and not file.startswith("__"):
                module_name = file[:-3] # .py uzantısını kaldır
                # konsol.log(f"[cyan]Okunan Dosya\t\t: {module_name}[/cyan]")
                if plugin := self._load_plugin(directory, module_name):
                    # konsol.log(f"[magenta]Eklenti Yüklendi\t: {plugin.name}[/magenta]")
                    plugins[module_name] = plugin

        # konsol.log(f"[yellow]{directory} dizininden yüklenen Eklentiler: {list(plugins.keys())}[/yellow]")
        return plugins

    def _load_plugin(self, directory: Path, module_name: str):
        try:
            # Modül dosyasını bul ve yükle
            path = directory / f"{module_name}.py"
            spec = importlib.util.spec_from_file_location(module_name, path)
            if not spec or not spec.loader:
                raise ImportError(f"Spec oluşturulamadı: {module_name}")

            # Modülü içe aktar
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Yalnızca doğru modülden gelen PluginBase sınıflarını yükle
            for attr in dir(module):
                obj = getattr(module, attr)
                if isinstance(obj, type) and issubclass(obj, PluginBase) and obj is not PluginBase:
                    # konsol.log(f"[yellow]Yüklenen sınıf\t\t: {module_name}.{obj.__name__} ({obj.__module__}.{obj.__name__})[/yellow]")
                    return obj()

        except Exception as hata:
            konsol.print(f"[red][!] Eklenti yüklenirken hata oluştu: {module_name}\nHata: {hata}")
            konsol.print(f"[dim]{traceback.format_exc()}[/dim]")

        return None