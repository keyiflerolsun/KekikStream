# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from .ExtractorLoader import ExtractorLoader
from .ExtractorBase   import ExtractorBase

class ExtractorManager:
    def __init__(self, extractor_dir="Extractors"):
        # Çıkarıcı yükleyiciyi başlat ve tüm çıkarıcıları yükle
        self.extractor_loader = ExtractorLoader(extractor_dir)
        self.extractors       = self.extractor_loader.load_all()

    def find_extractor(self, link) -> ExtractorBase:
        # Verilen bağlantıyı işleyebilecek çıkarıcıyı bul
        for extractor_cls in self.extractors:
            extractor:ExtractorBase = extractor_cls()
            if extractor.can_handle_url(link):
                return extractor

        return None

    def map_links_to_extractors(self, links) -> dict:
        # Bağlantıları uygun çıkarıcılarla eşleştir
        mapping = {}
        for link in links:
            for extractor_cls in self.extractors:
                extractor:ExtractorBase = extractor_cls()
                if extractor.can_handle_url(link):
                    mapping[link] = f"{extractor.name:<30} » {link.replace(extractor.main_url, '')}"
                    break

        return mapping