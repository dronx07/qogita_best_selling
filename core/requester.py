from curl_cffi.requests import AsyncSession
from curl_cffi import Response
from typing import Optional


class Requester:
    def __init__(
        self,
        referrer: str,
        cookies: Optional[dict] = None,
        proxy: Optional[str] = None,
    ) -> None:
        self.session: AsyncSession | None = None
        self.cookies = cookies or {}
        self.proxy = proxy
        self.headers = {
            "Accept": "*/*",
            "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
            "Referer": referrer,
        }

    async def __aenter__(self):
        self.session = AsyncSession(
            impersonate="chrome142",
            http_version="v2",
            allow_redirects=True,
            headers=self.headers,
            proxy=self.proxy,
            timeout=60
        )
        await self.session.__aenter__()
        self.session.cookies.update(self.cookies)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.session:
            await self.session.__aexit__(exc_type, exc, tb)

    async def fetch_get(self, url: str) -> Optional[Response]:
        return await self.session.get(url)
