import asyncio
import logging
import json
import os
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from core.login import QogitaLogin
from core.requester import Requester
import shutil

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

JSON_FILE = "products.json"
TEMP_JSON_FILE = "products_temp.json"

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

        for i in range(1, 142):
            url = f"https://www.qogita.com/categories/?size=72&page={i}"
            logger.info(f"Scraping page {i}")

            try:
                response = await session.fetch_get(url)
            except Exception as e:
                logger.error(f"Request failed on page {i}: {e}")
                break

            if not response or response.status_code != 200:
                logger.warning(f"Stopping. Status code: {getattr(response, 'status_code', None)}")
                break

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
                logger.info("No products found. Stopping pagination.")
                break

            min_length = min(len(names), len(prices), len(gtins))

            for idx in range(min_length):
                name = names[idx]
                price = prices[idx]
                gtin = gtins[idx]

                product_gtin = gtin.get_text(strip=True)

                if not product_gtin or product_gtin in existing_gtins:
                    continue

                product_data.append(
                    {
                        "product_name": name.get_text(strip=True),
                        "product_gtin": product_gtin,
                        "supplier_price": price.get_text(strip=True),
                    }
                )

                existing_gtins.add(product_gtin)

            logger.info(f"Collected so far: {len(product_data)} products")

    try:
        with open(TEMP_JSON_FILE, "w", encoding="utf-8") as temp_file:
            json.dump(product_data, temp_file, ensure_ascii=False, indent=4)

        shutil.move(TEMP_JSON_FILE, JSON_FILE)
        logger.info(f"Finished. Total products: {len(product_data)}")

    except Exception as e:
        logger.error(f"Failed to write JSON file: {e}")
        if os.path.exists(TEMP_JSON_FILE):
            os.remove(TEMP_JSON_FILE)

if __name__ == "__main__":
    asyncio.run(qogita_scraper())
