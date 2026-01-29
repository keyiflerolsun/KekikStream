# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from ...CLI         import konsol, cikis_yap
from .ExtractorBase import ExtractorBase
from pathlib        import Path
import os, importlib.util, traceback

class ExtractorLoader:
    def __init__(self, extractors_dir: str):
        # Yerel ve global çıkarıcı dizinlerini ayarla
        self.local_extractors_dir  = Path(extractors_dir)
        self.global_extractors_dir = Path(__file__).parent.parent.parent / "Extractors"

        # Dizin kontrolü
        if not self.local_extractors_dir.exists() and not self.global_extractors_dir.exists():
            # konsol.log(f"[red][!] Extractor dizini bulunamadı: {self.global_extractors_dir}[/red]")
            cikis_yap(False)

    def load_all(self) -> list[ExtractorBase]:
        extractors = []

        # Yerel Extractor'lar varsa önce onları yükle (ek/öncelikli yetenekler)
        # Eğer yerel dizin global dizinle aynıysa (örn: doğrudan core'da çalışırken) tekrar yükleme yapma
        if self.local_extractors_dir.exists() and self.local_extractors_dir.resolve() != self.global_extractors_dir.resolve():
            # konsol.log(f"[green][*] Yerel Extractor dizininden yükleniyor: {self.local_extractors_dir}[/green]")
            extractors.extend(self._load_from_directory(self.local_extractors_dir))

        # Global Extractor'ları her zaman yükle (temel yetenekler)
        if self.global_extractors_dir.exists():
            # konsol.log(f"[green][*] Global Extractor dizininden yükleniyor: {self.global_extractors_dir}[/green]")
            extractors.extend(self._load_from_directory(self.global_extractors_dir))

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
                module_extractors = self._load_extractor(directory, module_name)
                if module_extractors:
                    # konsol.log(f"[magenta]Extractor Yüklendi\t: {[e.__name__ for e in module_extractors]}[/magenta]")
                    extractors.extend(module_extractors)

        # konsol.log(f"[yellow]{directory} dizininden yüklenen Extractor'lar: {[e.__name__ for e in extractors]}[/yellow]")
        return extractors

    def _load_extractor(self, directory: Path, module_name: str):
        try:
            # Modül dosyasını bul ve yükle
            path = directory / f"{module_name}.py"
            spec = importlib.util.spec_from_file_location(module_name, path)
            if not spec or not spec.loader:
                return []

            # Modülü içe aktar
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Yalnızca doğru modülden gelen ExtractorBase sınıflarını yükle (TÜM CLASS'LAR)
            extractors = []
            for attr in dir(module):
                obj = getattr(module, attr)
                # isinstance kontrolünü __module__ kontrolünden ÖNCE yap
                if isinstance(obj, type) and issubclass(obj, ExtractorBase) and obj is not ExtractorBase and obj.__module__ == module_name:
                    # konsol.log(f"[green]Yüklenen sınıf\t\t: {module_name}.{obj.__name__} ({obj.__module__}.{obj.__name__})[/green]")
                    extractors.append(obj)
            
            return extractors

        except Exception as hata:
            konsol.log(f"[red][!] Extractor yüklenirken hata oluştu: {module_name}\nHata: {hata}")
            konsol.print(f"[dim]{traceback.format_exc()}[/dim]")

        return []
