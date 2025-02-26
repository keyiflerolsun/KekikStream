# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from ...CLI         import konsol, cikis_yap
from .ExtractorBase import ExtractorBase
from pathlib        import Path
import os, importlib.util, traceback

class ExtractorLoader:
    def __init__(self, extractors_dir: str):
        # Yerel ve global çıkarıcı dizinlerini ayarla
        self.local_extractors_dir  = Path(extractors_dir)
        self.global_extractors_dir = Path(__file__).parent.parent.parent / extractors_dir

        # Dizin kontrolü
        if not self.local_extractors_dir.exists() and not self.global_extractors_dir.exists():
            # konsol.log(f"[red][!] Extractor dizini bulunamadı: {self.global_extractors_dir}[/red]")
            cikis_yap(False)

    def load_all(self) -> list[ExtractorBase]:
        extractors = []

        # Global çıkarıcıları yükle
        if self.global_extractors_dir.exists():
            # konsol.log(f"[green][*] Global Extractor dizininden yükleniyor: {self.global_extractors_dir}[/green]")
            global_extractors = self._load_from_directory(self.global_extractors_dir)
            # konsol.log(f"[green]Global Extractor'lar: {[e.__name__ for e in global_extractors]}[/green]")
            extractors.extend(global_extractors)

        # Yerel çıkarıcıları yükle
        if self.local_extractors_dir.exists():
            # konsol.log(f"[green][*] Yerel Extractor dizininden yükleniyor: {self.local_extractors_dir}[/green]")
            local_extractors = self._load_from_directory(self.local_extractors_dir)
            # konsol.log(f"[green]Yerel Extractor'lar: {[e.__name__ for e in local_extractors]}[/green]")
            extractors.extend(local_extractors)

        # Benzersizliği sağlama (modül adı + sınıf adı bazında)
        unique_extractors = []
        seen_names = set()
        for ext in extractors:
            identifier = f"{ext.__module__}.{ext.__name__}"
            if identifier not in seen_names:
                unique_extractors.append(ext)
                seen_names.add(identifier)

        # konsol.log(f"[blue]Sonuç Extractor'lar: {[e.__name__ for e in unique_extractors]}[/blue]")

        if not unique_extractors:
            konsol.log("[yellow][!] Yüklenecek bir Extractor bulunamadı![/yellow]")

        return unique_extractors

    def _load_from_directory(self, directory: Path) -> list[ExtractorBase]:
        extractors = []

        # Dizindeki tüm .py dosyalarını tara
        for file in os.listdir(directory):
            if file.endswith(".py") and not file.startswith("__"):
                module_name = file[:-3] # .py uzantısını kaldır
                # konsol.log(f"[cyan]Okunan Dosya\t\t: {module_name}[/cyan]")
                if extractor := self._load_extractor(directory, module_name):
                    # konsol.log(f"[magenta]Extractor Yüklendi\t: {extractor.__name__}[/magenta]")
                    extractors.append(extractor)

        # konsol.log(f"[yellow]{directory} dizininden yüklenen Extractor'lar: {[e.__name__ for e in extractors]}[/yellow]")
        return extractors

    def _load_extractor(self, directory: Path, module_name: str):
        try:
            # Modül dosyasını bul ve yükle
            path = directory / f"{module_name}.py"
            spec = importlib.util.spec_from_file_location(module_name, path)
            if not spec or not spec.loader:
                return None

            # Modülü içe aktar
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Yalnızca doğru modülden gelen ExtractorBase sınıflarını yükle
            for attr in dir(module):
                obj = getattr(module, attr)
                if obj.__module__ == module_name and isinstance(obj, type) and issubclass(obj, ExtractorBase) and obj is not ExtractorBase:
                    # konsol.log(f"[green]Yüklenen sınıf\t\t: {module_name}.{obj.__name__} ({obj.__module__}.{obj.__name__})[/green]")
                    return obj

        except Exception as hata:
            konsol.log(f"[red][!] Extractor yüklenirken hata oluştu: {module_name}\nHata: {hata}")
            konsol.print(f"[dim]{traceback.format_exc()}[/dim]")

        return None