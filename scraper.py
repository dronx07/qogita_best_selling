import asyncio
import logging
import json
import os
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from core.login import QogitaLogin
from core.requester import Requester

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

JSON_FILE = "products.json"
BASE_URL = "https://www.qogita.com/categories/?size=72&page={}"


async def scrape_page(page: int, session: Requester):
    url = BASE_URL.format(page)
    logger.info(f"Scraping page {page}...")

    try:
        response = await session.fetch_get(url)
    except Exception as e:
        logger.error(f"Request failed on page {page}: {e}")
        return []

    if not response or response.status_code != 200:
        logger.warning(f"Page {page} returned {getattr(response, 'status_code', None)}")
        return []

    soup = BeautifulSoup(response.text, "lxml")

    names = soup.find_all("a", class_="line-clamp-2")
    prices = soup.find_all(
        "span",
        class_="whitespace-nowrap font-figtree text-lg font-semibold text-gray-900",
    )
    gtins = soup.find_all(
        "p",
        attrs={"data-dd-action-name": "Product Card GTIN"},
    )

    if not names:
        logger.info(f"No products found on page {page}")
        return []

    min_length = min(len(names), len(prices), len(gtins))
    page_products = []

    for idx in range(min_length):
        product_gtin = gtins[idx].get_text(strip=True)
        if not product_gtin:
            continue

        page_products.append(
            {
                "product_name": names[idx].get_text(strip=True),
                "product_gtin": product_gtin,
                "supplier_price": prices[idx].get_text(strip=True),
            }
        )

    logger.info(f"Page {page} scraped ({len(page_products)} items)")
    return page_products


async def qogita_scraper():
    product_data = []
    existing_gtins = set()

    email = os.getenv("QOGITA_EMAIL")
    password = os.getenv("QOGITA_PASSWORD")

    if not email or not password:
        raise ValueError("Missing QOGITA_EMAIL or QOGITA_PASSWORD in .env")

    login = QogitaLogin(
        email=email,
        password=password,
        headless=True,
    )

    logger.info("Logging in...")
    cookies = await login.login()

    if not cookies:
        raise RuntimeError("Login failed. No cookies returned.")

    async with Requester(
        referrer="https://www.qogita.com/categories/",
        cookies=cookies,
        proxy=os.getenv("PROXY"),
    ) as session:

        for page in range(1, 142):
            page_products = await scrape_page(page, session)

            for product in page_products:
                gtin = product["product_gtin"]
                if gtin in existing_gtins:
                    continue
                existing_gtins.add(gtin)
                product_data.append(product)

    try:
        with open(JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(product_data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error(f"Failed to write JSON file: {e}")
        return

    logger.info(f"Finished. Total products: {len(product_data)}")


if __name__ == "__main__":
    asyncio.run(qogita_scraper())
