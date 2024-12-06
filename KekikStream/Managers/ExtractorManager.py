# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from ..Core import ExtractorLoader, ExtractorBase

class ExtractorManager:
    def __init__(self, extractor_dir="Extractors"):
        self.extractor_loader = ExtractorLoader(extractor_dir)
        self.extractors       = self.extractor_loader.load_all()

    def find_extractor(self, link):
        for extractor_cls in self.extractors:
            extractor:ExtractorBase = extractor_cls()
            if extractor.can_handle_url(link):
                return extractor

        return None

    def map_links_to_extractors(self, links):
        mapping = {}
        for link in links:
            for extractor_cls in self.extractors:
                extractor:ExtractorBase = extractor_cls()
                if extractor.can_handle_url(link):
                    mapping[link] = f"{extractor.name:<30} » {link.replace(extractor.main_url, '')}"
                    break

        return mapping