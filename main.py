"""
Improved version of the web scraping code with better organization,
modularity, and consistency.
"""

import pandas as pd
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from bs4 import BeautifulSoup
import logging
import time
import os
from datetime import datetime
import json
import csv

# Constants for configuration
RESULTS_DIR = "results"
LOG_DIR = "logs"
DEBUG_DIR = {"screenshots": "debug_screenshots", "html": "debug_html"}

# Create necessary directories
for directory in [RESULTS_DIR, LOG_DIR] + list(DEBUG_DIR.values()):
    os.makedirs(directory, exist_ok=True)

# News source configuration
NEWS_SOURCES = [
    {"name": "kompas", "url": "https://www.kompas.com/"},
    {"name": "detik", "url": "https://www.detik.com/"},
    {"name": "tribun", "url": "https://www.tribunnews.com/"},
]

# CSS selector mapping using modern approach
HEADLINE_SELECTORS = {
    "kompas": [
        ".read__title",
        ".headline__title",
        ".most__title",
        ".trending__title",
    ],
    "detik": [
        ".detail__title",
        ".media__title",
        ".title",
        "h1.title",
        "h2.title",
    ],
    "tribun": [".hltitle", ".headline-caption", ".newslist-title", "h1.f50"],
}

IMAGE_SELECTORS = {
    "kompas": [".photo__wrap img", ".headline__thumb img", "img.lozad"],
    "detik": [".detail__img-wrap img", ".headline__img img", "picture img"],
    "tribun": [".imgpreview img", ".headline-img img", ".news-image img"],
}


# Set up logging with timestamp in filename
def setup_logging():
    """Configure logging with timestamp in filename"""
    log_filename = os.path.join(
        LOG_DIR, f"scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    )

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_filename), logging.StreamHandler()],
    )

    return log_filename


# Create Chrome webdriver with standard options
def create_chrome_driver():
    """Create and configure Chrome WebDriver with standard options"""
    options = Options()
    options.add_argument("--headless=new")  # Updated headless argument
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")

    # Set user agent to avoid detection
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    )

    service = Service()
    return webdriver.Chrome(service=service, options=options)


def get_international_books():
    """
    Scrapes international books from Gramedia website.
    Returns a list of dictionaries containing book details.
    """
    data = []
    logging.info("Starting to scrape Gramedia international books...")

    driver = None
    try:
        driver = create_chrome_driver()
        driver.set_page_load_timeout(30)  # Set timeout for page load

        url = "https://www.gramedia.com/promo/international-book"
        logging.info(f"Accessing URL: {url}")
        driver.get(url)

        # Wait for the main content to load
        wait = WebDriverWait(driver, 30)
        try:
            wait.until(
                EC.presence_of_element_located(
                    (
                        By.CSS_SELECTOR,
                        "div.ProductCard_cardContent__fawWr, div.product-card",
                    )
                )
            )
            logging.info("Main content loaded successfully")
        except TimeoutException:
            logging.warning(
                "Timeout waiting for main content, will try to proceed anyway"
            )
            # Take screenshot for debugging
            driver.save_screenshot(f"{DEBUG_DIR['screenshots']}/timeout_error.png")

        # Scroll down to load all products (handle lazy loading)
        logging.info("Starting scroll to load all products...")
        scroll_and_collect(driver)

        # Try multiple selectors to find books
        selectors = [
            "div.ProductCard_cardContent__fawWr",
            "div.product-card",
            "div[data-testid='productCard']",
            "div.product-item",
        ]

        books = []
        for selector in selectors:
            books = driver.find_elements(By.CSS_SELECTOR, selector)
            if books:
                logging.info(f"Found {len(books)} books using selector: {selector}")
                break

        if not books:
            logging.error("No books found with any selector")
            # Save page source for debugging
            with open(
                f"{DEBUG_DIR['html']}/page_source.html", "w", encoding="utf-8"
            ) as f:
                f.write(driver.page_source)
            logging.info("Saved page source to page_source.html for debugging")
            return data

        # Process each book
        data = process_book_elements(books)
        logging.info(f"Successfully scraped {len(data)} books")

    except WebDriverException as e:
        logging.error(f"WebDriver error: {str(e)}")
    except Exception as e:
        logging.error(f"Unexpected error during scraping: {str(e)}")
    finally:
        if driver:
            driver.quit()
            logging.info("WebDriver closed")

    return data


def scroll_and_collect(driver):
    """Scroll down page to load all dynamically loaded content"""
    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_count = 0
    max_scrolls = 20  # Limit scrolls to prevent infinite loop

    while scroll_count < max_scrolls:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)  # Wait for content to load
        new_height = driver.execute_script("return document.body.scrollHeight")
        scroll_count += 1

        logging.info(f"Scroll {scroll_count}/{max_scrolls} - Height: {new_height}px")

        if new_height == last_height:
            logging.info("Reached bottom of page")
            break

        last_height = new_height


def process_book_elements(books):
    """Process book elements from Gramedia page"""
    data = []

    # Dictionary of possible selectors for each element
    selectors = {
        "img": [
            "img.object-contain",
            "img.product-image",
            "img[data-testid='productImage']",
        ],
        "title": [
            "h2.text-neutral-700",
            "h2.product-title",
            "div.product-name",
            "[data-testid='productTitle']",
        ],
        "publisher": [
            "div.text-neutral-500",
            "div.publisher",
            "div.product-publisher",
            "[data-testid='productPublisher']",
        ],
        "price": [
            "div.text-s-extrabold",
            "div.product-price",
            "div.price",
            "[data-testid='productPrice']",
        ],
    }

    for i, book in enumerate(books, 1):
        try:
            # Initialize default values
            img, title, publisher, price = "N/A", "N/A", "N/A", "N/A"

            # Try different selectors for each element
            for element_type, selector_list in selectors.items():
                for sel in selector_list:
                    try:
                        element = book.find_element(By.CSS_SELECTOR, sel)

                        if element_type == "img":
                            img = element.get_attribute("src")
                        elif element_type == "title":
                            title = element.get_attribute("title") or element.text
                        elif element_type == "publisher":
                            publisher = element.get_attribute("title") or element.text
                        elif element_type == "price":
                            price = element.text.strip()

                        if locals()[
                            element_type
                        ]:  # If we found a value, break the loop
                            break
                    except NoSuchElementException:
                        continue

            book_data = {
                "Judul": title,
                "Penerbit": publisher,
                "Harga": price,
                "Image URL": img,
            }
            data.append(book_data)

            logging.info(f"Processed book {i}: {title}")

        except Exception as e:
            logging.error(f"Error processing book {i}: {str(e)}")
            continue

    return data


def get_news_with_selenium(media_name, url):
    """
    Uses Selenium to scrape news headlines and images from specified media website.
    This is a more reliable method for JavaScript-heavy websites.
    """
    logging.info(f"Getting headline from {media_name} using Selenium ({url})")

    driver = None
    try:
        driver = create_chrome_driver()
        driver.set_page_load_timeout(30)

        driver.get(url)
        time.sleep(5)  # Give time for JavaScript to execute

        # Save screenshot for debugging
        driver.save_screenshot(
            f"{DEBUG_DIR['screenshots']}/{media_name}_screenshot.png"
        )

        # Use selectors based on media name
        if media_name in HEADLINE_SELECTORS:
            headline_selectors = HEADLINE_SELECTORS[media_name]
        else:
            headline_selectors = ["h1", "h2.title", ".headline", ".title"]

        if media_name in IMAGE_SELECTORS:
            image_selectors = IMAGE_SELECTORS[media_name]
        else:
            image_selectors = ["img"]

        headline_text = None
        image_url = None

        # Try to find headline
        for selector in headline_selectors:
            try:
                element = driver.find_element(By.CSS_SELECTOR, selector)
                headline_text = element.text.strip()
                if headline_text:
                    logging.info(f"Found headline for {media_name} using {selector}")
                    break
            except NoSuchElementException:
                continue

        # Try to find image
        for selector in image_selectors:
            try:
                element = driver.find_element(By.CSS_SELECTOR, selector)
                # Try both src and data-src attributes
                image_url = element.get_attribute("src") or element.get_attribute(
                    "data-src"
                )
                if image_url:
                    logging.info(f"Found image for {media_name} using {selector}")
                    break
            except NoSuchElementException:
                continue

        # Fallback for headline
        if not headline_text:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, "h1, h2, .title")
                if elements:
                    headline_text = elements[0].text.strip()
                    logging.info(
                        f"Found headline for {media_name} using fallback method"
                    )
            except Exception as e:
                logging.error(f"Fallback headline search error: {str(e)}")
                headline_text = "Headline tidak ditemukan"

        # Fallback for image
        if not image_url:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, "img")
                for element in elements:
                    src = element.get_attribute("src")
                    if src and (
                        src.endswith(".jpg")
                        or src.endswith(".png")
                        or src.endswith(".jpeg")
                    ):
                        image_url = src
                        logging.info(
                            f"Found image for {media_name} using fallback method"
                        )
                        break
            except Exception as e:
                logging.error(f"Fallback image search error: {str(e)}")
                image_url = "Image tidak ditemukan"

        return {
            "Media": media_name.capitalize(),
            "Headline": headline_text or "Headline tidak ditemukan",
            "Image": image_url or "Image tidak ditemukan",
            "URL": url,
        }

    except Exception as e:
        logging.error(f"Error scraping {media_name} with Selenium: {str(e)}")
        return {
            "Media": media_name.capitalize(),
            "Headline": f"Error: {str(e)}",
            "Image": "Error",
            "URL": url,
        }
    finally:
        if driver:
            driver.quit()
            logging.info(f"Selenium driver closed for {media_name}")


def get_news(media_name, url):
    """
    Tries to scrape news using requests/BeautifulSoup first,
    and falls back to Selenium if needed.
    """
    logging.info(f"Getting headline from {media_name} ({url})")

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")

        # Debug: Save the HTML
        with open(
            f"{DEBUG_DIR['html']}/{media_name}_debug.html", "w", encoding="utf-8"
        ) as f:
            f.write(str(soup))
        logging.info(f"Saved {media_name} HTML for debugging")

        headline_text = None
        image_url = None

        # Try to find headline
        if media_name in HEADLINE_SELECTORS:
            for selector in HEADLINE_SELECTORS[media_name]:
                headline_elem = soup.select_one(selector)
                if headline_elem:
                    headline_text = headline_elem.get_text(strip=True)
                    logging.info(f"Found headline for {media_name} using {selector}")
                    break

        # Try to find image
        if media_name in IMAGE_SELECTORS:
            for selector in IMAGE_SELECTORS[media_name]:
                img_elem = soup.select_one(selector)
                if img_elem:
                    # Try both src and data-src attributes
                    image_url = img_elem.get("src") or img_elem.get("data-src")
                    if image_url:
                        logging.info(f"Found image for {media_name} using {selector}")
                        break

        # If we couldn't find headlines or images with BeautifulSoup, try with Selenium
        if not headline_text or not image_url:
            logging.info(
                f"Couldn't find full data with BeautifulSoup, trying Selenium for {media_name}"
            )
            return get_news_with_selenium(media_name, url)

        return {
            "Media": media_name.capitalize(),
            "Headline": headline_text or "Headline tidak ditemukan",
            "Image": image_url or "Image tidak ditemukan",
            "URL": url,
        }

    except requests.exceptions.RequestException as e:
        logging.error(f"Request error for {media_name}: {str(e)}")
        # If request fails, try with Selenium as fallback
        logging.info(f"Request failed for {media_name}, trying with Selenium instead")
        return get_news_with_selenium(media_name, url)

    except Exception as e:
        logging.error(f"Error scraping {media_name}: {str(e)}")
        return {
            "Media": media_name.capitalize(),
            "Headline": f"Error: {str(e)}",
            "Image": "N/A",
            "URL": url,
        }


class AniListScraper:
    """Class to scrape trending anime from AniList"""

    def __init__(self):
        self.base_url = "https://anilist.co/search/anime/trending"
        self.graphql_url = "https://graphql.anilist.co"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        }
        self.results = []

    def fetch_page(self):
        """Fetch the trending anime page content"""
        try:
            response = requests.get(self.base_url, headers=self.headers)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"Error fetching the page: {e}")
            return None

    def extract_data_from_html(self, html_content):
        """Extract anime data from the HTML content using BeautifulSoup"""
        if not html_content:
            return

        soup = BeautifulSoup(html_content, "html.parser")

        # Find all anime cards on the page
        anime_cards = soup.select("div.media-card")

        for card in anime_cards:
            try:
                # Extract image URL
                image_element = card.select_one("img.image")
                image_url = (
                    image_element["src"]
                    if image_element and "src" in image_element.attrs
                    else ""
                )

                # Clean up image URL
                if image_url.startswith("//"):
                    image_url = f"https:{image_url}"

                # Extract title
                title_element = card.select_one("div.title")
                title = title_element.get_text(strip=True) if title_element else ""

                # Create anime entry
                anime = {
                    "title": title,
                    "image": image_url,
                    "tag": title,  # Using title as tag as per the example
                }

                self.results.append(anime)
                print(f"Extracted: {title}")

            except Exception as e:
                print(f"Error extracting data from a card: {e}")

    def use_graphql_api(self, page=1, per_page=50):
        """
        Use AniList's GraphQL API to fetch trending anime data
        This is more reliable than scraping the HTML
        """
        # GraphQL query to get trending anime
        query = """
        query ($page: Int, $perPage: Int) {
          Page(page: $page, perPage: $perPage) {
            media(sort: TRENDING_DESC, type: ANIME) {
              id
              title {
                romaji
                english
                native
              }
              coverImage {
                large
                medium
              }
            }
          }
        }
        """

        variables = {"page": page, "perPage": per_page}

        try:
            response = requests.post(
                self.graphql_url, json={"query": query, "variables": variables}
            )
            response.raise_for_status()
            data = response.json()

            if (
                "data" in data
                and "Page" in data["data"]
                and "media" in data["data"]["Page"]
            ):
                for anime in data["data"]["Page"]["media"]:
                    title = (
                        anime["title"]["romaji"]
                        or anime["title"]["english"]
                        or anime["title"]["native"]
                    )
                    image_url = (
                        anime["coverImage"]["large"] or anime["coverImage"]["medium"]
                    )

                    anime_data = {"title": title, "image": image_url, "tag": title}

                    self.results.append(anime_data)
                    print(f"Extracted: {title}")

            return len(self.results)
        except requests.exceptions.RequestException as e:
            print(f"Error with GraphQL API: {e}")
            return 0

    def save_to_json(self, filename="anilist_trending_anime.json"):
        """Save the scraped data to a JSON file"""
        with open(os.path.join(RESULTS_DIR, filename), "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=4)
        print(f"Data saved to {os.path.join(RESULTS_DIR, filename)}")

    def save_to_csv(self, filename="anilist_trending_anime.csv"):
        """Save the scraped data to a CSV file"""
        if not self.results:
            print("No data to save")
            return

        with open(
            os.path.join(RESULTS_DIR, filename), "w", encoding="utf-8", newline=""
        ) as f:
            writer = csv.DictWriter(f, fieldnames=["tag", "image", "title"])
            writer.writeheader()
            writer.writerows(self.results)
        print(f"Data saved to {os.path.join(RESULTS_DIR, filename)}")

    def run(self, use_api=True):
        """Run the scraper"""
        if use_api:
            print("Using GraphQL API to fetch data...")
            count = self.use_graphql_api()
            if count > 0:
                print(f"Successfully extracted {count} anime entries via API")
            else:
                print("API request failed, trying HTML scraping as fallback...")
                html_content = self.fetch_page()
                self.extract_data_from_html(html_content)
        else:
            print("Scraping HTML page...")
            html_content = self.fetch_page()
            self.extract_data_from_html(html_content)

        if self.results:
            print(f"Successfully extracted {len(self.results)} anime entries")
            self.save_to_json()
            self.save_to_csv()
        else:
            print("No data was extracted")


def main():
    """
    Main function to run the scraper and save results to Excel.
    """
    try:
        log_filename = setup_logging()
        logging.info("Starting web scraping process...")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Start with news scraping first (faster and helps identify issues early)
        logging.info("Starting news scraping...")

        news_data = []
        for source in NEWS_SOURCES:
            try:
                result = get_news(source["name"], source["url"])
                news_data.append(result)
                # Print for immediate feedback
                print(
                    f"Scraped {source['name'].capitalize()}: {result['Headline'][:80]}..."
                )
            except Exception as e:
                logging.error(f"Failed to scrape {source['name']}: {str(e)}")
                news_data.append(
                    {
                        "Media": source["name"].capitalize(),
                        "Headline": f"Error: {str(e)}",
                        "Image": "Error",
                        "URL": source["url"],
                    }
                )

        # Get book data
        logging.info("Starting Gramedia book scraping...")
        book_data = get_international_books()

        # Save to Excel
        excel_filename = os.path.join(
            RESULTS_DIR, f"web_scraping_results_{timestamp}.xlsx"
        )
        with pd.ExcelWriter(excel_filename, engine="openpyxl") as writer:
            # News headlines first (for easier debugging)
            pd.DataFrame(news_data).to_excel(
                writer, sheet_name="News Headlines", index=False
            )
            logging.info(f"Saved {len(news_data)} news items to Excel")

            # Then books
            if book_data:
                pd.DataFrame(book_data).to_excel(
                    writer, sheet_name="Gramedia Books", index=False
                )
                logging.info(f"Saved {len(book_data)} books to Excel")
            else:
                pd.DataFrame(
                    columns=["Judul", "Penerbit", "Harga", "Image URL"]
                ).to_excel(writer, sheet_name="Gramedia Books", index=False)
                logging.warning("No book data was saved to Excel")

        logging.info(f"All data successfully saved to {excel_filename}")
        print(f"\nScraped data successfully saved to: {excel_filename}")
        print(f"Log file created at: {log_filename}")

        # Summary report
        print("\nScraping Summary:")
        print(f"- News headlines: {len(news_data)} items")
        print(f"- Gramedia books: {len(book_data)} items")

        # Run AniList scraper
        print("\nStarting AniList scraping...")
        anime_scraper = AniListScraper()
        anime_scraper.run(use_api=True)

    except Exception as e:
        logging.error(f"Error in main function: {str(e)}")
        print(f"An error occurred: {str(e)}")
        print(f"Check log file for details: {log_filename}")


if __name__ == "__main__":
    main()
