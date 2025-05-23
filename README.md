# Web Scraper Project Guide

## Project Overview

This project contains a comprehensive web scraping solution designed to collect data from multiple sources:

1. **News Headlines**: Extracts headlines and images from Indonesian news websites (Kompas, Detik, and Tribun)
2. **International Books**: Collects book data from Gramedia's international books section
3. **Trending Anime**: Retrieves trending anime information from AniList

The scraper is built with robust error handling, fallback mechanisms, and debugging capabilities to ensure reliable data collection even when facing common web scraping challenges.

## Features

- **Multi-source data collection**: Scrapes data from various websites in a single execution
- **Hybrid scraping approach**: Uses both requests/BeautifulSoup and Selenium for maximum reliability
- **Comprehensive error handling**: Fallback mechanisms if primary scraping methods fail
- **Organized output**: Saves results in both Excel (XLSX) and JSON/CSV formats
- **Detailed logging**: Creates timestamped logs for debugging and monitoring
- **Debug artifacts**: Captures screenshots and HTML for troubleshooting

## Requirements

Before running the scraper, ensure you have the following dependencies installed:

```bash
pip install pandas requests selenium beautifulsoup4 openpyxl logging
```

Additionally, you'll need to have Chrome and ChromeDriver installed. The code uses Selenium's Service class, which should automatically find and use the appropriate ChromeDriver for your system.

## Directory Structure

The script automatically creates the following directory structure:

```
├── results/               # Scraped data outputs (Excel, JSON, CSV)
├── logs/                  # Log files with timestamps
└── debug/
    ├── screenshots/       # Browser screenshots for debugging
    └── html/              # Raw HTML snapshots for analysis
```

## How to Use

### Basic Usage

To run the complete scraper with all modules, simply execute the script:

```bash
python main.py
```

This will:
1. Scrape headlines from all configured news sources
2. Collect book data from Gramedia's international section
3. Gather trending anime from AniList
4. Save all results to timestamped files in the `results` directory

### Custom Usage

The script is modular, so you can modify the `main()` function to run only specific parts if needed:

#### News Headlines Only

```python
def main():
    log_filename = setup_logging()
    logging.info("Starting news scraping only...")
    
    news_data = []
    for source in NEWS_SOURCES:
        result = get_news(source["name"], source["url"])
        news_data.append(result)
    
    # Save to Excel
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    excel_filename = os.path.join(RESULTS_DIR, f"news_headlines_{timestamp}.xlsx")
    pd.DataFrame(news_data).to_excel(excel_filename, index=False)
    
    logging.info(f"News data saved to {excel_filename}")
```

#### Books Only

```python
def main():
    log_filename = setup_logging()
    logging.info("Starting book scraping only...")
    
    book_data = get_international_books()
    
    # Save to Excel
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    excel_filename = os.path.join(RESULTS_DIR, f"gramedia_books_{timestamp}.xlsx")
    pd.DataFrame(book_data).to_excel(excel_filename, index=False)
    
    logging.info(f"Book data saved to {excel_filename}")
```

#### Anime Only

```python
def main():
    log_filename = setup_logging()
    logging.info("Starting anime scraping only...")
    
    anime_scraper = AniListScraper()
    anime_scraper.run(use_api=True)
    
    logging.info("Anime data saved to results directory")
```

## Configuration

### News Sources

The scraper is configured to collect headlines from three Indonesian news sites by default:

```python
NEWS_SOURCES = [
    {"name": "kompas", "url": "https://www.kompas.com/"},
    {"name": "detik", "url": "https://www.detik.com/"},
    {"name": "tribun", "url": "https://www.tribunnews.com/"},
]
```

You can modify this list to add or remove sources as needed. For each new source, you may need to add appropriate CSS selectors to the `HEADLINE_SELECTORS` and `IMAGE_SELECTORS` dictionaries.

### Selectors

The project uses CSS selectors to locate elements on web pages. These are defined in dictionaries:

```python
HEADLINE_SELECTORS = {
    "kompas": [".read__title", ".headline__title", ".most__title", ".trending__title"],
    "detik": [".detail__title", ".media__title", ".title", "h1.title", "h2.title"],
    "tribun": [".hltitle", ".headline-caption", ".newslist-title", "h1.f50"],
}

IMAGE_SELECTORS = {
    "kompas": [".photo__wrap img", ".headline__thumb img", "img.lozad"],
    "detik": [".detail__img-wrap img", ".headline__img img", "picture img"],
    "tribun": [".imgpreview img", ".headline-img img", ".news-image img"],
}
```

When adding new sources, research the appropriate selectors by inspecting the target website.

## Understanding the Code

### News Scraping

The news scraping functionality uses a two-tiered approach:

1. First attempts to scrape with `requests` and `BeautifulSoup` (faster, lighter)
2. Falls back to Selenium if the first method fails (more reliable for JS-heavy sites)

This ensures maximum reliability while being efficient when possible.

### Book Scraping

The book scraping module uses Selenium to:

1. Navigate to Gramedia's international books section
2. Handle lazy loading by scrolling the page
3. Extract book details using multiple selector attempts
4. Process and clean the data

### Anime Scraping

The AniList scraper is implemented as a class with two methods:

1. GraphQL API approach (primary, more reliable)
2. HTML scraping fallback

## Troubleshooting

If the scraper encounters issues:

1. **Check the logs**: Detailed logs are saved in the `logs` directory
2. **Examine screenshots**: Browser screenshots in `debug_screenshots` show what the scraper was seeing
3. **Review HTML**: Raw HTML is saved in `debug_html` for analysis

Common issues include:

- **Selector changes**: Websites may update their structure; check and update the selectors
- **Rate limiting**: Add delays or implement proxies if facing rate limits
- **Chrome/ChromeDriver issues**: Ensure both are installed and up to date

## Extending the Project

To add a new scraping module:

1. Create a new function or class following the pattern of existing modules
2. Add appropriate error handling and logging
3. Implement the data extraction logic
4. Update the `main()` function to call your new module
5. Add the new data to the Excel output or create a new output format

## Ethical Considerations

When using this scraper, please:

- Respect robots.txt files on target websites
- Implement reasonable delays between requests
- Consider the load your scraping may place on target servers
- Use the data in compliance with the websites' terms of service
- Do not use for commercial purposes without appropriate permissions

## License

This project is provided for educational purposes. Use responsibly and in accordance with applicable laws and website terms of service.