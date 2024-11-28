# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from ..Core import PluginLoader

class PluginManager:
    def __init__(self, plugin_dir="Plugins"):
        self.plugin_loader = PluginLoader(plugin_dir)
        self.plugins       = self.plugin_loader.load_all()

    def get_plugin_names(self):
        return list(self.plugins.keys())

    def select_plugin(self, plugin_name):
        return self.plugins.get(plugin_name)

    async def close_plugins(self):
        for plugin in self.plugins.values():
            await plugin.close()