# requester.py

from curl_cffi.requests import AsyncSession
from curl_cffi import Response
from typing import Optional


class Requester:
    """
    An asynchronous requester built with curl_cffi AsyncSession.
    """

    def __init__(self, url: str, referrer: str , cookie: Optional[str] = None, proxy: Optional[str] = None) -> None:
        """
        Initialize the scraper.

        :param url: Target URL to scrape.
        """
        self.url = url
        self.session: AsyncSession | None = None
        self.headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
            "Cookie": cookie,
            "Referer": referrer
        }
        self.proxy = proxy


    async def __aenter__(self):
        """
        Create async session context.
        """
        self.session = AsyncSession(impersonate="chrome142",
                                          http_version="v2",
                                          allow_redirects=True,
                                          headers=self.headers,
                                          proxy=self.proxy)
        await self.session.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        """
        Close async session context.
        """
        if self.session:
            await self.session.__aexit__(exc_type, exc, tb)

    async def fetch_get(self) -> Optional[Response]:
        """
        Fetch content through GET.
        """
        target = self.url
        response = await self.session.get(target)
        return response

    async def fetch_post(self, data: dict) -> Optional[Response]:
        """
        Fetch content through POST.
        """
        target = self.url
        response = await self.session.post(target, json=data)
        return response
