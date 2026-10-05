# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from ..Helpers.MethodCache import method_cache


class PluginCacheMixin:
    def _setup_default_method_caches(self):
        self._setup_method_cache(
            "search",
            self._cache_key_search,
            should_cache = self._should_cache_search,
        )
        self._setup_method_cache(
            "get_main_page",
            self._cache_key_get_main_page,
            should_cache = self._should_cache_get_main_page,
        )
        self._setup_method_cache(
            "load_item",
            self._cache_key_load_item,
            should_cache = self._should_cache_load_item,
        )

    def _setup_method_cache(self, method_name: str, key_builder, should_cache=None):
        class_method = getattr(self.__class__, method_name, None)
        if getattr(class_method, "__isabstractmethod__", False):
            return

        original_method = getattr(self, method_name, None)
        if not callable(original_method):
            return
        if getattr(original_method, "__wb_cached_method__", False):
            return

        async def cached_method(*args, **kwargs):
            key = key_builder(*args, **kwargs)
            return await method_cache.run(
                namespace    = self._cache_namespace,
                method_name  = method_name,
                key          = key,
                producer     = lambda: original_method(*args, **kwargs),
                should_cache = should_cache,
                ttl          = self.method_cache_ttl,
                max_entries  = self.method_cache_max_entries
            )

        cached_method.__wb_cached_method__      = True
        cached_method.__wb_cached_method_name__ = method_name
        setattr(self, method_name, cached_method)

    @staticmethod
    def _normalize_cache_key_part(value: object, *, casefold: bool = False) -> str:
        part = " ".join(str(value or "").split()).strip()
        return part.casefold() if casefold else part

    @staticmethod
    def _pick_arg(args: tuple, kwargs: dict, pos: int, names: tuple[str, ...], default: object = "") -> object:
        for name in names:
            if name in kwargs:
                return kwargs[name]
        return args[pos] if len(args) > pos else default

    def _cache_key_search(self, *args, **kwargs) -> str:
        query = self._pick_arg(args, kwargs, 0, ("query",))
        return self._normalize_cache_key_part(query, casefold=True)

    def _cache_key_get_main_page(self, *args, **kwargs) -> str:
        page     = self._pick_arg(args, kwargs, 0, ("page",), 1)
        url      = self._pick_arg(args, kwargs, 1, ("url", "encoded_url"))
        category = self._pick_arg(args, kwargs, 2, ("category", "encoded_category"))
        return (
            f"page={self._normalize_cache_key_part(page)}"
            f"|url={self._normalize_cache_key_part(url)}"
            f"|category={self._normalize_cache_key_part(category)}"
        )

    def _cache_key_load_item(self, *args, **kwargs) -> str:
        url = self._pick_arg(args, kwargs, 0, ("url", "encoded_url"))
        return self._normalize_cache_key_part(url)

    @staticmethod
    def _should_cache_search(payload) -> bool:
        return isinstance(payload, list) and len(payload) > 0

    @staticmethod
    def _should_cache_get_main_page(payload) -> bool:
        return isinstance(payload, list) and len(payload) > 0

    @staticmethod
    def _should_cache_load_item(payload) -> bool:
        if payload is None:
            return False
        if isinstance(payload, dict):
            return bool(payload)
        return True
