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
MAX_CONCURRENT_REQUESTS = 10


async def scrape_page(page, cookie, semaphore, existing_gtins):
    async with semaphore:
        try:
            async with Requester(
                url="https://www.qogita.com/categories/?size=72&page={}".format(page),
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

                new_products = []

                for name, price, gtin in zip(names, prices, gtins):
                    product_gtin = gtin.text.strip()

                    if product_gtin in existing_gtins:
                        continue

                    existing_gtins.add(product_gtin)

                    new_products.append(
                        {
                            "product_name": name.text.strip(),
                            "product_gtin": product_gtin,
                            "supplier_price": price.text.strip(),
                        }
                    )

                return new_products

        except Exception:
            return []


async def qogita_scraper():
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            product_data = json.load(f)
        existing_gtins = {p["product_gtin"] for p in product_data}
    else:
        product_data = []
        existing_gtins = set()

    try:
        automation = QogitaLogin(
            email=os.getenv("QOGITA_EMAIL"),
            password=os.getenv("QOGITA_PASSWORD"),
            headless=True,
        )
        cookie = await automation.login()
    except Exception:
        return

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    tasks = [
        scrape_page(page, cookie, semaphore, existing_gtins)
        for page in range(1, 142)
    ]

    results = await asyncio.gather(*tasks)

    for page_products in results:
        product_data.extend(page_products)

    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(product_data, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    asyncio.run(qogita_scraper())
