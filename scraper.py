import asyncio
import logging
import json
import os
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from core.login import QogitaLogin
from core.requester import Requester
import random

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

JSON_FILE = "products.json"
STATE_FILE = "category_state.json"

CATEGORIES = [
    "https://www.qogita.com/categories/health-beauty/health/?size=72&page={}",
    "https://www.qogita.com/categories/health-beauty/body/?size=72&page={}",
    "https://www.qogita.com/categories/health-beauty/face/?size=72&page={}",
    "https://www.qogita.com/categories/health-beauty/hair/?size=72&page={}",
    "https://www.qogita.com/categories/health-beauty/makeup/?size=72&page={}",
    "https://www.qogita.com/categories/health-beauty/home-lifestyle/?size=72&page={}",
]

def load_state():
    if not os.path.exists(STATE_FILE):
        with open(STATE_FILE, "w") as f:
            json.dump({"current_index": 0}, f)
        return 0
    with open(STATE_FILE, "r") as f:
        data = json.load(f)
        return data.get("current_index", 0)

def save_state(index):
    with open(STATE_FILE, "w") as f:
        json.dump({"current_index": index}, f)

async def qogita_scraper():
    product_data = []
    existing_gtins = set()
    email = os.getenv("QOGITA_EMAIL")
    password = os.getenv("QOGITA_PASSWORD")

    if not email or not password:
        raise ValueError("Missing QOGITA_EMAIL or QOGITA_PASSWORD in .env")

    login = QogitaLogin(email=email, password=password, headless=True)
    logger.info("Logging in...")
    cookies = await login.login()

    if not cookies:
        raise RuntimeError("Login failed. No cookies returned.")

    current_index = load_state()
    category_url_template = CATEGORIES[current_index]
    logger.info(f"Scraping category {current_index + 1}/{len(CATEGORIES)}: {category_url_template}")

    async with Requester(referrer="https://www.qogita.com/categories/", cookies=cookies, proxy=os.getenv("PROXY")) as session:
        page = 1
        while True:
            url = category_url_template.format(page)
            logger.info(f"Scraping page {page}")
            try:
                response = await session.fetch_get(url)
            except Exception as e:
                logger.error(f"Request failed on page {page}: {e}")
                break

            if not response or response.status_code != 200:
                logger.warning(f"Stopping. Status code: {getattr(response, 'status_code', None)}")
                break

            soup = BeautifulSoup(response.text, "lxml")

            names = soup.find_all("a", class_="line-clamp-2 rounded-sm font-light text-gray-900 underline decoration-transparent transition-colors delay-100 duration-300 ease-in-out group-hover/card:decoration-current group-hover/links:decoration-transparent hover:decoration-current")
            prices = soup.find_all("span", attrs={"class": "whitespace-nowrap font-figtree text-lg font-semibold text-gray-900"})
            gtins = soup.find_all("p", attrs={"data-dd-action-name": "Product Card GTIN"})
            brands = soup.find_all("a", attrs={"class": "font-outfit inline-flex cursor-pointer items-center justify-center gap-2 rounded-sm disabled:cursor-not-allowed aria-disabled:cursor-not-allowed underline-offset-4 hover:text-gray-900 disabled:text-gray-500 text-base font-medium text-gray-900 underline decoration-transparent transition-colors delay-100 duration-300 ease-in-out hover:decoration-current"})

            if not names:
                logger.info("No products found. Stopping pagination.")
                break

            min_length = min(len(names), len(prices), len(gtins), len(brands))

            for idx in range(min_length):
                name = names[idx]
                price = prices[idx]
                gtin = gtins[idx]
                brand = brands[idx]

                product_gtin = gtin.get_text(strip=True)
                if not product_gtin or product_gtin in existing_gtins:
                    continue

                product_link = name.get("href")
                if product_link and product_link.startswith("/"):
                    product_link = f"https://www.qogita.com{product_link}"

                product_data.append({
                    "product_name": name.get_text(strip=True),
                    "product_gtin": product_gtin,
                    "supplier_price": price.get_text(strip=True),
                    "product_link": product_link,
                    "brand": brand.get_text(strip=True)
                })
                existing_gtins.add(product_gtin)

            logger.info(f"Collected so far: {len(product_data)} products")
            page += 1
            delay = random.uniform(1.5, 4.0)  
            logger.info(f"Sleeping for {delay:.2f} seconds...")
            await asyncio.sleep(delay)

    try:
        with open(JSON_FILE, "w", encoding="utf-8") as file:
            json.dump(product_data, file, ensure_ascii=False, indent=4)
        logger.info(f"Finished. Total products: {len(product_data)}")
    except Exception as e:
        logger.error(f"Failed to write JSON file: {e}")

    next_index = (current_index + 1) % len(CATEGORIES)
    save_state(next_index)
    logger.info(f"Next category index saved: {next_index}")

if __name__ == "__main__":
    asyncio.run(qogita_scraper())