# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

import httpx, curl_cffi


class FallbackMixin:
    """Proxy ile önce dener; hata alırsa fallback istemciye geçer."""

    _fallback = None
    main_url  = None

    def set_fallback(self, client):
        self._fallback = client


def sanitize_url(url: str, main_url: str = None) -> str:
    if not url:
        return ""
    url = url.strip()
    # 1. Protokol ve bağıl yol kontrolü
    if url.startswith("//"):
        url = f"https:{url}"
    elif url.startswith("/"):
        if main_url:
            url = f"{main_url.rstrip('/')}{url}"
    elif not url.startswith(("http://", "https://")):
        if main_url:
            url = f"{main_url.rstrip('/')}/{url}"
        else:
            url = f"https://{url}"

    # 2. Query string içerisindeki köşeli parantezleri ve süslü parantezleri encode et (libcurl / curl_cffi kurtarmak için)
    if "?" in url:
        base, query = url.split("?", 1)
        query = query.replace("[", "%5B").replace("]", "%5D").replace("{", "%7B").replace("}", "%7D")
        url   = f"{base}?{query}"
    return url


class FallbackHTTPX(FallbackMixin, httpx.AsyncClient):

    # 4xx aralığında (403/429 hariç - bunlar çoğunlukla anti-bot/rate-limit işareti) kesin
    # istemci hatalarında fallback denemeyelim - boşuna ikinci bir istek atmayalım.
    _NON_RETRYABLE_STATUS = frozenset(range(400, 500)) - {403, 429}

    async def request(self, method, url, **kwargs):
        if isinstance(url, str):
            url = sanitize_url(url, self.main_url)
        try:
            resp = await super().request(method, url, **kwargs)
            if not (200 <= resp.status_code < 300):
                raise httpx.HTTPStatusError("Non-2xx response", request=resp.request, response=resp)
            return resp
        except httpx.HTTPStatusError as e:
            if e.response is not None and e.response.status_code in self._NON_RETRYABLE_STATUS:
                raise
            if self._fallback:
                return await self._fallback.request(method, url, **kwargs)
            raise
        except Exception:
            if self._fallback:
                return await self._fallback.request(method, url, **kwargs)
            raise

    async def aclose(self):
        if self._fallback:
            await self._fallback.aclose()
        await super().aclose()


class FallbackCF(FallbackMixin, curl_cffi.AsyncSession):

    async def request(self, method, url, **kwargs):
        if isinstance(url, str):
            url = sanitize_url(url, self.main_url)
        try:
            return await super().request(method, url, **kwargs)
        except Exception:
            if self._fallback:
                return await self._fallback.request(method, url, **kwargs)
            raise

    async def get(self, url, **kwargs):
        if isinstance(url, str):
            url = sanitize_url(url, self.main_url)
        try:
            return await super().get(url, **kwargs)
        except Exception:
            if self._fallback:
                return await self._fallback.get(url, **kwargs)
            raise

    async def post(self, url, **kwargs):
        if isinstance(url, str):
            url = sanitize_url(url, self.main_url)
        try:
            return await super().post(url, **kwargs)
        except Exception:
            if self._fallback:
                return await self._fallback.post(url, **kwargs)
            raise

    async def close(self):
        if self._fallback:
            await self._fallback.close()
        await super().close()
