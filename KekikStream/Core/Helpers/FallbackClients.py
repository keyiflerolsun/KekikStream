# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

import httpx, curl_cffi


class FallbackMixin:
    """Proxy ile önce dener; hata alırsa fallback istemciye geçer."""

    _fallback = None

    def set_fallback(self, client):
        self._fallback = client


class FallbackHTTPX(FallbackMixin, httpx.AsyncClient):

    async def request(self, method, url, **kwargs):
        try:
            resp = await super().request(method, url, **kwargs)
            if not (200 <= resp.status_code < 300):
                raise httpx.HTTPStatusError("Non-2xx response", request=resp.request, response=resp)
            return resp
        except Exception:
            if self._fallback:
                return await self._fallback.request(method, url, **kwargs)
            raise

    async def aclose(self):
        if self._fallback:
            await self._fallback.aclose()
        await super().aclose()


class FallbackCF(FallbackMixin, curl_cffi.AsyncSession):

    async def get(self, url, **kwargs):
        try:
            return await super().get(url, **kwargs)
        except Exception:
            if self._fallback:
                return await self._fallback.get(url, **kwargs)
            raise

    async def post(self, url, **kwargs):
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
