# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from .PluginLoader import PluginLoader
from .PluginBase   import PluginBase

class PluginManager:
    def __init__(self, plugin_dir="Plugins"):
        # Eklenti yükleyiciyi başlat ve tüm eklentileri yükle
        self.plugin_loader = PluginLoader(plugin_dir)
        self.plugins       = self.plugin_loader.load_all()

    def get_plugin_names(self):
        # Dizindeki tüm eklenti adlarını listeler ve sıralar
        return sorted(list(self.plugins.keys()))

    def select_plugin(self, plugin_name):
        # Verilen eklenti adını kullanarak eklentiyi seç
        return self.plugins.get(plugin_name)

    async def close_plugins(self):
        # Tüm eklentileri kapat
        for plugin in self.plugins.values():
            if isinstance(plugin, PluginBase):
                await plugin.close()