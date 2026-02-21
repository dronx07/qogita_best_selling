import asyncio
import logging
import json
from bs4 import BeautifulSoup
from .core.login import QogitaLogin
from .core.requester import Requester
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


async def scrape_page(page, cookie, semaphore):
    async with semaphore:
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

                products = []

                for name, price, gtin in zip(names, prices, gtins):
                    products.append(
                        {
                            "product_name": name.text.strip(),
                            "product_gtin": gtin.text.strip(),
                            "supplier_price": price.text.strip(),
                        }
                    )

                return products

        except Exception as e:
            print(f"Error page {page}: {e}")
            return []


async def qogita_scraper():
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            product_data = json.load(f)
    else:
        product_data = []

    existing_gtins = {p["product_gtin"] for p in product_data}

    automation = QogitaLogin(
        email=os.getenv("QOGITA_EMAIL"),
        password=os.getenv("QOGITA_PASSWORD"),
        headless=True,
    )

    cookie = await automation.login()

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    tasks = [
        scrape_page(page, cookie, semaphore)
        for page in range(1, 142)
    ]

    results = await asyncio.gather(*tasks)

    new_count = 0

    for page_products in results:
        for product in page_products:
            if product["product_gtin"] not in existing_gtins:
                existing_gtins.add(product["product_gtin"])
                product_data.append(product)
                new_count += 1

    print("New products:", new_count)

    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(product_data, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    asyncio.run(qogita_scraper())
