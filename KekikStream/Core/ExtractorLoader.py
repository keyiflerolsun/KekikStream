# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from ..CLI          import konsol, cikis_yap
from .ExtractorBase import ExtractorBase
from pathlib        import Path
import importlib.util
import os

class ExtractorLoader:
    def __init__(self, extractors_dir: str):
        self.local_extractors_dir  = Path(extractors_dir)
        self.global_extractors_dir = Path(__file__).parent.parent / extractors_dir
        if not self.local_extractors_dir.exists() and not self.global_extractors_dir.exists():
            konsol.log(f"[red][!] Extractor dizini bulunamadı: {self.extractors_dir}[/red]")
            cikis_yap(False)

    def load_all(self) -> list[ExtractorBase]:
        extractors = []

        if self.global_extractors_dir.exists():
            konsol.log(f"[green][*] Global Extractor dizininden yükleniyor: {self.global_extractors_dir}[/green]")
            extractors.extend(self._load_from_directory(self.global_extractors_dir))

        if self.local_extractors_dir.exists():
            konsol.log(f"[green][*] Yerel Extractor dizininden yükleniyor: {self.local_extractors_dir}[/green]")
            extractors.extend(self._load_from_directory(self.local_extractors_dir))

        if not extractors:
            konsol.print("[yellow][!] Yüklenecek bir Extractor bulunamadı![/yellow]")

        return extractors

    def _load_from_directory(self, directory: Path) -> list[ExtractorBase]:
        extractors = []
        for file in os.listdir(directory):
            if file.endswith(".py") and not file.startswith("__"):
                module_name = file[:-3]
                if extractor := self._load_extractor(directory, module_name):
                    extractors.append(extractor)

        return extractors

    def _load_extractor(self, directory: Path, module_name: str):
        try:
            path = directory / f"{module_name}.py"
            spec = importlib.util.spec_from_file_location(module_name, path)
            if not spec or not spec.loader:
                return None

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            for attr in dir(module):
                obj = getattr(module, attr)
                if isinstance(obj, type) and issubclass(obj, ExtractorBase) and obj is not ExtractorBase:
                    return obj

        except Exception as hata:
            konsol.print(f"[red][!] Extractor yüklenirken hata oluştu: {module_name}\nHata: {hata}")

        return None