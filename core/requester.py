import httpx
from typing import Optional


class Requester:
    def __init__(
        self,
        referrer: str,
        cookies: Optional[dict] = None,
        proxy: Optional[str] = None,
    ) -> None:
        self.client: httpx.AsyncClient | None = None
        self.cookies = cookies or {}
        self.proxy = proxy

        self.headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/142.0.0.0 Safari/537.36"
            ),
            "Referer": referrer,
        }

    async def __aenter__(self):
        self.client = httpx.AsyncClient(
            headers=self.headers,
            cookies=self.cookies,
            proxies=self.proxy,
            http2=True,
            follow_redirects=True,
            timeout=httpx.Timeout(30.0),
        )
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.client:
            await self.client.aclose()

    async def fetch_get(self, url: str) -> Optional[httpx.Response]:
        if not self.client:
            raise RuntimeError("Client not initialized. Use 'async with'.")
        return await self.client.get(url)
