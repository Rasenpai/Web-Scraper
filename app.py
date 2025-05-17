from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import os
import json
import logging
from datetime import datetime

# Import the scraper modules
from main import (
    setup_logging,
    get_news,
    get_international_books,
    NEWS_SOURCES,
    AniListScraper,
    RESULTS_DIR
)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Setup logging
log_filename = setup_logging()
logging.info("Starting Flask API server...")

@app.route('/api/news', methods=['GET'])
def get_news_data():
    """API endpoint to get news headlines from various sources"""
    try:
        logging.info("API request received: /api/news")
        
        # Check if there's a recent Excel file to read from instead of scraping again
        excel_files = [f for f in os.listdir(RESULTS_DIR) if f.endswith('.xlsx')]
        if excel_files:
            # Sort by modification time (newest first)
            latest_file = sorted(
                excel_files,
                key=lambda x: os.path.getmtime(os.path.join(RESULTS_DIR, x)),
                reverse=True
            )[0]
            file_path = os.path.join(RESULTS_DIR, latest_file)
            
            # Check if file is less than 1 hour old
            file_time = os.path.getmtime(file_path)
            if (datetime.now().timestamp() - file_time) < 3600:  # 1 hour in seconds
                logging.info(f"Using cached data from {latest_file}")
                # Read news data from Excel
                news_df = pd.read_excel(file_path, sheet_name="News Headlines")
                return jsonify(news_df.to_dict(orient='records'))
        
        # If no recent file, scrape fresh data
        logging.info("No recent cache found, scraping fresh news data...")
        news_data = []
        for source in NEWS_SOURCES:
            try:
                result = get_news(source["name"], source["url"])
                news_data.append(result)
                logging.info(f"Scraped {source['name']}: {result['Headline'][:50]}...")
            except Exception as e:
                logging.error(f"Failed to scrape {source['name']}: {str(e)}")
                news_data.append({
                    "Media": source["name"].capitalize(),
                    "Headline": f"Error: {str(e)}",
                    "Image": "Error",
                    "URL": source["url"]
                })
        
        return jsonify(news_data)
    
    except Exception as e:
        logging.error(f"Error in /api/news endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/books', methods=['GET'])
def get_books_data():
    """API endpoint to get international books from Gramedia"""
    try:
        logging.info("API request received: /api/books")
        
        # Check for cached data first
        excel_files = [f for f in os.listdir(RESULTS_DIR) if f.endswith('.xlsx')]
        if excel_files:
            latest_file = sorted(
                excel_files,
                key=lambda x: os.path.getmtime(os.path.join(RESULTS_DIR, x)),
                reverse=True
            )[0]
            file_path = os.path.join(RESULTS_DIR, latest_file)
            
            # Check if file is less than 2 hours old
            file_time = os.path.getmtime(file_path)
            if (datetime.now().timestamp() - file_time) < 7200:  # 2 hours in seconds
                logging.info(f"Using cached book data from {latest_file}")
                books_df = pd.read_excel(file_path, sheet_name="Gramedia Books")
                return jsonify(books_df.to_dict(orient='records'))
        
        # If no recent file, scrape fresh data
        logging.info("No recent cache found, scraping fresh book data...")
        book_data = get_international_books()
        return jsonify(book_data)
    
    except Exception as e:
        logging.error(f"Error in /api/books endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/anime', methods=['GET'])
def get_anime_data():
    """API endpoint to get trending anime from AniList"""
    try:
        logging.info("API request received: /api/anime")
        
        # Check for cached JSON data first
        json_file = os.path.join(RESULTS_DIR, "anilist_trending_anime.json")
        if os.path.exists(json_file):
            file_time = os.path.getmtime(json_file)
            # Use cached data if less than 3 hours old
            if (datetime.now().timestamp() - file_time) < 10800:  # 3 hours in seconds
                logging.info(f"Using cached anime data from {json_file}")
                with open(json_file, 'r', encoding='utf-8') as f:
                    anime_data = json.load(f)
                return jsonify(anime_data)
        
        # If no recent file, scrape fresh data
        logging.info("No recent cache found, scraping fresh anime data...")
        anime_scraper = AniListScraper()
        anime_scraper.run(use_api=True)
        
        # Read the freshly created JSON file
        if os.path.exists(json_file):
            with open(json_file, 'r', encoding='utf-8') as f:
                anime_data = json.load(f)
            return jsonify(anime_data)
        else:
            return jsonify([])
    
    except Exception as e:
        logging.error(f"Error in /api/anime endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/scrape-all', methods=['POST'])
def scrape_all():
    """API endpoint to force scrape all data sources"""
    try:
        logging.info("API request received: /api/scrape-all (force refresh)")
        
        # Create timestamp for filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Scrape news
        news_data = []
        for source in NEWS_SOURCES:
            try:
                result = get_news(source["name"], source["url"])
                news_data.append(result)
            except Exception as e:
                logging.error(f"Failed to scrape {source['name']}: {str(e)}")
                news_data.append({
                    "Media": source["name"].capitalize(),
                    "Headline": f"Error: {str(e)}",
                    "Image": "Error",
                    "URL": source["url"]
                })
        
        # Scrape books
        book_data = get_international_books()
        
        # Save to Excel
        excel_filename = os.path.join(RESULTS_DIR, f"web_scraping_results_{timestamp}.xlsx")
        with pd.ExcelWriter(excel_filename, engine="openpyxl") as writer:
            pd.DataFrame(news_data).to_excel(writer, sheet_name="News Headlines", index=False)
            pd.DataFrame(book_data).to_excel(writer, sheet_name="Gramedia Books", index=False)
        
        # Scrape anime
        anime_scraper = AniListScraper()
        anime_scraper.run(use_api=True)
        
        return jsonify({
            "status": "success",
            "message": "All data scraped successfully",
            "news_count": len(news_data),
            "books_count": len(book_data),
            "anime_count": len(anime_scraper.results)
        })
    
    except Exception as e:
        logging.error(f"Error in /api/scrape-all endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/status', methods=['GET'])
def get_status():
    """API endpoint to check server status and data availability"""
    try:
        excel_files = [f for f in os.listdir(RESULTS_DIR) if f.endswith('.xlsx')]
        anime_file = os.path.join(RESULTS_DIR, "anilist_trending_anime.json")
        
        last_update = None
        if excel_files:
            latest_file = sorted(
                excel_files,
                key=lambda x: os.path.getmtime(os.path.join(RESULTS_DIR, x)),
                reverse=True
            )[0]
            last_update = datetime.fromtimestamp(
                os.path.getmtime(os.path.join(RESULTS_DIR, latest_file))
            ).strftime("%Y-%m-%d %H:%M:%S")
        
        return jsonify({
            "status": "online",
            "data_available": {
                "news": len(excel_files) > 0,
                "books": len(excel_files) > 0,
                "anime": os.path.exists(anime_file)
            },
            "last_update": last_update
        })
    
    except Exception as e:
        logging.error(f"Error in /api/status endpoint: {str(e)}")
        return jsonify({"status": "error", "error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)