"""
Data Fetcher — scrapes real data from public sources.
No API key needed. Uses requests + BeautifulSoup.
"""
import requests
from bs4 import BeautifulSoup
import json
import re
import time

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/120.0.0.0 Safari/537.36'
}

# ── 1. STOCK PRICES (Yahoo Finance) ───────────────────────────────────────────
def fetch_stock_price(ticker: str) -> dict:
    """Fetch real stock price from Yahoo Finance."""
    url = f"https://finance.yahoo.com/quote/{ticker}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=8)
        soup = BeautifulSoup(r.text, 'html.parser')

        # Current price
        price_tag = soup.find('fin-streamer', {'data-field': 'regularMarketPrice'})
        price = float(price_tag['value']) if price_tag and price_tag.get('value') else None

        # Change
        change_tag = soup.find('fin-streamer', {'data-field': 'regularMarketChange'})
        change = float(change_tag['value']) if change_tag and change_tag.get('value') else 0

        # Percent change
        pct_tag = soup.find('fin-streamer', {'data-field': 'regularMarketChangePercent'})
        pct = round(float(pct_tag['value']), 2) if pct_tag and pct_tag.get('value') else 0

        if price:
            return {
                'ticker': ticker,
                'price': price,
                'change': round(change, 2),
                'pct': pct,
                'trend': 'Rising' if change > 0 else ('Falling' if change < 0 else 'Stable'),
                'source': 'Yahoo Finance'
            }
    except Exception as e:
        print(f"[Stock] {ticker} error: {e}")
    return None

def fetch_all_stocks(tickers: list) -> dict:
    """Fetch multiple stocks. Returns dict keyed by ticker."""
    results = {}
    for ticker in tickers:
        data = fetch_stock_price(ticker)
        if data:
            results[ticker] = data
            time.sleep(0.5)  # polite delay
    return results

# ── 2. JOBS (RemoteOK public API — no key needed) ─────────────────────────────
def fetch_remote_jobs(keyword: str = 'python', limit: int = 10) -> list:
    """Fetch real remote jobs from RemoteOK public API."""
    try:
        url = "https://remoteok.com/api"
        r = requests.get(url, headers={**HEADERS, 'Accept': 'application/json'}, timeout=10)
        data = r.json()
        jobs = []
        for item in data[1:]:  # first item is metadata
            if not isinstance(item, dict):
                continue
            title = item.get('position', '')
            desc  = item.get('description', '') or item.get('tags', [])
            if isinstance(desc, list):
                desc = ' '.join(desc)
            # Filter by keyword
            if keyword.lower() in title.lower() or keyword.lower() in desc.lower():
                jobs.append({
                    'title':       title,
                    'company':     item.get('company', 'Unknown'),
                    'location':    item.get('location', 'Remote'),
                    'salary':      item.get('salary', 'Competitive'),
                    'description': re.sub(r'<[^>]+>', '', desc)[:300],
                    'url':         item.get('url', ''),
                    'posted':      item.get('date', '')[:10] if item.get('date') else '',
                    'source':      'RemoteOK'
                })
            if len(jobs) >= limit:
                break
        return jobs
    except Exception as e:
        print(f"[Jobs] error: {e}")
        return []

# ── 3. PRODUCT REVIEWS (Books to Scrape — public demo site) ──────────────────
def fetch_product_reviews(category: str = 'mystery', limit: int = 8) -> list:
    """Scrape product data from books.toscrape.com (legal demo scraping site)."""
    try:
        url = f"https://books.toscrape.com/catalogue/category/books/{category}_3/index.html"
        r   = requests.get(url, headers=HEADERS, timeout=8)
        soup = BeautifulSoup(r.text, 'html.parser')
        products = []
        for article in soup.select('article.product_pod')[:limit]:
            name  = article.select_one('h3 a')['title']
            price = article.select_one('.price_color').text.strip().replace('Â','')
            rating_map = {'One':1,'Two':2,'Three':3,'Four':4,'Five':5}
            rating_word = article.select_one('.star-rating')['class'][1]
            rating = rating_map.get(rating_word, 3)
            products.append({
                'name':   name,
                'price':  price,
                'rating': rating,
                'stars':  '⭐' * rating,
                'source': 'BooksToScrape'
            })
        return products
    except Exception as e:
        print(f"[Products] error: {e}")
        return []

# ── 4. TECH NEWS (Hacker News public API — no key needed) ────────────────────
def fetch_tech_news(limit: int = 8) -> list:
    """Fetch top tech stories from Hacker News API."""
    try:
        ids_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
        ids = requests.get(ids_url, timeout=8).json()[:limit]
        stories = []
        for sid in ids:
            item = requests.get(
                f"https://hacker-news.firebaseio.com/v0/item/{sid}.json",
                timeout=5
            ).json()
            if item and item.get('title'):
                stories.append({
                    'title':  item['title'],
                    'url':    item.get('url', f"https://news.ycombinator.com/item?id={sid}"),
                    'score':  item.get('score', 0),
                    'source': 'Hacker News'
                })
        return stories
    except Exception as e:
        print(f"[News] error: {e}")
        return []

# ── 5. CRYPTO PRICES (CoinGecko public API — no key needed) ──────────────────
def fetch_crypto_prices() -> list:
    """Fetch top crypto prices from CoinGecko free API."""
    try:
        url = ("https://api.coingecko.com/api/v3/coins/markets"
               "?vs_currency=usd&order=market_cap_desc&per_page=6&page=1")
        r    = requests.get(url, headers=HEADERS, timeout=8)
        data = r.json()
        result = []
        for coin in data:
            pct = coin.get('price_change_percentage_24h', 0) or 0
            result.append({
                'name':    coin['name'],
                'symbol':  coin['symbol'].upper(),
                'price':   coin['current_price'],
                'change':  round(pct, 2),
                'trend':   'Rising' if pct > 0 else ('Falling' if pct < 0 else 'Stable'),
                'image':   coin.get('image', ''),
                'source':  'CoinGecko'
            })
        return result
    except Exception as e:
        print(f"[Crypto] error: {e}")
        return []

# ── 6. GENERATE FAKE REVIEWS for sentiment demo ───────────────────────────────
def fetch_sample_reviews(product_name: str = 'product') -> list:
    """Returns realistic sample reviews for ML sentiment demo."""
    return [
        f"Absolutely love this {product_name}! Works perfectly.",
        f"The {product_name} quality is outstanding. Highly recommend!",
        f"Fast delivery and great packaging for the {product_name}.",
        f"Terrible {product_name}. Broke after 2 days. Waste of money.",
        f"Poor quality {product_name}. Not as described at all.",
        f"Average {product_name}. Nothing special but does the job.",
        f"Best {product_name} I've ever bought. 5 stars!",
        f"Disappointed with the {product_name}. Expected much better.",
    ]
