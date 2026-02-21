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

    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            product_data = json.load(f)
        logger.info(f"Loaded {len(product_data)} existing products")

        existing_gtins = {product["product_gtin"] for product in product_data}
    else:
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
    except Exception as e:
        logger.exception(f"Login failed: {e}")
        return

    for page in range(1, 142):
        logger.info(f"Scraping page {page}")

        try:
            async with Requester(
                url=os.getenv("QOGITA_URL").format(page),
                cookie=cookie,
                proxy=os.getenv("PROXY"),
                referrer=os.getenv("QOGITA_REFERRER"),
            ) as session:

                html = await session.fetch_get()
                soup = BeautifulSoup(html.text, "html.parser")

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

                new_products_count = 0

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
                    new_products_count += 1

                with open(JSON_FILE, "w", encoding="utf-8") as f:
                    json.dump(product_data, f, ensure_ascii=False, indent=4)

                logger.info(
                    f"Saved {new_products_count} NEW products from page {page}"
                )

        except Exception as e:
            logger.exception(f"Error on page {page}: {e}")
            continue

    logger.info(f"Scraping finished. Total unique products: {len(product_data)}")


if __name__ == "__main__":
    asyncio.run(qogita_scraper())
