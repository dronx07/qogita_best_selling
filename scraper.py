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


async def qogita_scraper():
    product_data = []
    existing_gtins = set()

    login = QogitaLogin(
        email=os.getenv("QOGITA_EMAIL"),
        password=os.getenv("QOGITA_PASSWORD"),
        headless=True,
    )

    cookies = await login.login()

    async with Requester(
        referrer="https://www.qogita.com/categories/",
        cookies=cookies,
        proxy=os.getenv("PROXY"),
    ) as session:

        page = 1

        while True:
            url = f"https://www.qogita.com/categories/?size=72&page={page}"
            logger.info(f"Scraping page {page}")

            response = await session.fetch_get(url)

            if response.status_code != 200:
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
                break

            for name, price, gtin in zip(names, prices, gtins):
                product_gtin = gtin.text.strip()
                if product_gtin in existing_gtins:
                    continue

                product_data.append(
                    {
                        "product_name": name.text.strip(),
                        "product_gtin": product_gtin,
                        "supplier_price": price.text.strip(),
                    }
                )
                existing_gtins.add(product_gtin)

            page += 1

    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(product_data, f, ensure_ascii=False, indent=4)

    logger.info(f"Finished. Total products: {len(product_data)}")


if __name__ == "__main__":
    asyncio.run(qogita_scraper())