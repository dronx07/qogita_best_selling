import asyncio
import logging
import json
from bs4 import BeautifulSoup
from core.login import QogitaLogin
from core.requester import Requester
from dotenv import load_dotenv
import os

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

JSON_FILE = "products.json"


async def qogita_scraper():
    logger.info("Starting Qogita scraper")

    product_data = []
    existing_gtins = set()

    try:
        logger.info("Initializing login process")
        automation = QogitaLogin(
            email=os.getenv("QOGITA_EMAIL"),
            password=os.getenv("QOGITA_PASSWORD"),
            headless=True,
        )
        cookie = await automation.login()
        logger.info("Login successful")

        with open("cookie.txt", "w", encoding="utf-8") as f:
            f.write(cookie)
            
    except Exception as e:
        logger.exception(f"Login failed: {e}")
        return

    for page in range(1, 142):
        logger.info(f"Scraping page {page}")

        try:
            async with Requester(
                url=f"https://www.qogita.com/categories/?size=72&page={page}",
                cookie=cookie,
                proxy=os.getenv("PROXY"),
                referrer="https://www.qogita.com/categories/",
            ) as session:

                html = await session.fetch_get()
                soup = BeautifulSoup(html.text, "lxml")

                names = soup.find_all("a", class_="line-clamp-2")
                prices = soup.find_all(
                    "span",
                    class_="whitespace-nowrap font-figtree text-lg font-semibold text-gray-900",
                )
                gtins = soup.find_all(
                    "p",
                    attrs={"data-dd-action-name": "Product Card GTIN"},
                )

                logger.info(
                    f"Found {len(names)} names, {len(prices)} prices, {len(gtins)} GTINs"
                )

                for name, price, gtin in zip(names, prices, gtins):
                    product_gtin = gtin.text.strip()
                    if product_gtin in existing_gtins:
                        continue

                    data = {
                        "product_name": name.text.strip(),
                        "product_gtin": product_gtin,
                        "supplier_price": price.text.strip(),
                    }

                    product_data.append(data)
                    existing_gtins.add(product_gtin)

        except Exception as e:
            logger.exception(f"Error on page {page}: {e}")
            continue

    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(product_data, f, ensure_ascii=False, indent=4)

    logger.info(f"Scraping finished. Total unique products: {len(product_data)}")


if __name__ == "__main__":
    asyncio.run(qogita_scraper())
