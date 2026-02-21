# login.py

import asyncio
from playwright.async_api import async_playwright


class QogitaLogin:
    """
    A class to perform login on Qogita and return session cookies and headers.
    """

    def __init__(self, email: str, password: str, headless: bool = True):
        """
        Initialize login credentials and browser mode.

        :param email: Account email.
        :param password: Account password.
        :param headless: Whether to run browser in headless mode.
        """
        self.login_url = "https://www.qogita.com/login/"
        self.email = email
        self.password = password
        self.headless = headless

    async def login(self) -> str:
        """
        Perform login and return cookies and headers.

        :return: Dictionary containing cookies and headers.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.headless,
                args=["--disable-blink-features=AutomationControlled"],
                slow_mo=1000
            )

            context = await browser.new_context()
            page = await context.new_page()

            await page.goto(self.login_url, wait_until="load")
            await page.fill("input[type='email']", self.email)
            await page.fill("input[type='password']", self.password)
            await page.click("button[type='submit']")
            await page.wait_for_load_state("load")

            await asyncio.sleep(10)

            cookies = await context.cookies()

            await browser.close()

            return "; ".join(f"{c['name']}={c['value']}" for c in cookies)
