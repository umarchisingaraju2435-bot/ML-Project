"""
Fetches 100+ real products from public APIs and scraping sources.
No API key needed.
"""
import requests
from bs4 import BeautifulSoup
import json, re, time, random

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# ── 1. FAKE STORE API (free, no key, 100 real products) ───────────────────────
def fetch_fakestore_products():
    """Fetch all products from FakeStore API — 20 real products with images."""
    try:
        r = requests.get('https://fakestoreapi.com/products', timeout=10)
        data = r.json()
        products = []
        for i, p in enumerate(data):
            products.append({
                'id':          1000 + i,
                'name':        p['title'],
                'price':       round(p['price'], 2),
                'category':    p['category'].title(),
                'description': p['description'][:200],
                'image_url':   p['image'],
                'rating':      round(p['rating']['rate'], 1),
                'review_count':p['rating']['count'],
                'stock':       random.randint(10, 200),
                'seller_id':   2,
                'source':      'FakeStore',
                'badge':       '🏷️ Featured',
            })
        return products
    except Exception as e:
        print(f"[FakeStore] {e}")
        return []

# ── 2. DummyJSON API (100 products with images) ───────────────────────────────
def fetch_dummyjson_products(limit=80):
    """Fetch products from DummyJSON — 100 products with real images."""
    try:
        r = requests.get(f'https://dummyjson.com/products?limit={limit}&skip=0', timeout=10)
        data = r.json()
        products = []
        for i, p in enumerate(data.get('products', [])):
            products.append({
                'id':          2000 + i,
                'name':        p['title'],
                'price':       round(p['price'], 2),
                'category':    p['category'].replace('-', ' ').title(),
                'description': p['description'][:200],
                'image_url':   p['thumbnail'],
                'rating':      round(p.get('rating', 4.0), 1),
                'review_count':p.get('stock', 50),
                'stock':       p.get('stock', 50),
                'seller_id':   2,
                'source':      'DummyJSON',
                'badge':       '⭐ Top Rated' if p.get('rating', 0) >= 4.5 else '',
                'discount':    p.get('discountPercentage', 0),
            })
        return products
    except Exception as e:
        print(f"[DummyJSON] {e}")
        return []

# ── 3. OPEN FOOD FACTS (real food products) ───────────────────────────────────
def fetch_food_products(limit=20):
    """Fetch real food products from Open Food Facts API."""
    try:
        url = 'https://world.openfoodfacts.org/cgi/search.pl?action=process&json=1&page_size=20&sort_by=popularity'
        r   = requests.get(url, headers=HEADERS, timeout=10)
        data = r.json()
        products = []
        for i, p in enumerate(data.get('products', [])[:limit]):
            name = p.get('product_name', '').strip()
            if not name:
                continue
            products.append({
                'id':          3000 + i,
                'name':        name[:60],
                'price':       round(random.uniform(1.99, 29.99), 2),
                'category':    'Food & Grocery',
                'description': p.get('ingredients_text', 'Natural food product.')[:200],
                'image_url':   p.get('image_small_url', ''),
                'rating':      round(random.uniform(3.5, 5.0), 1),
                'review_count':random.randint(10, 500),
                'stock':       random.randint(20, 300),
                'seller_id':   2,
                'source':      'OpenFoodFacts',
                'badge':       '🌿 Organic',
            })
        return products
    except Exception as e:
        print(f"[FoodFacts] {e}")
        return []

# ── 4. COMBINED: fetch all 100+ products ─────────────────────────────────────
_cached_products = None

def fetch_all_products(force_refresh=False):
    """
    Returns 100+ products from multiple sources.
    Cached after first call for performance.
    """
    global _cached_products
    if _cached_products and not force_refresh:
        return _cached_products

    print("[Products] Fetching from APIs...")
    all_products = []
    all_products += fetch_fakestore_products()   # ~20 products
    all_products += fetch_dummyjson_products(80) # ~80 products
    # all_products += fetch_food_products(20)    # optional food products

    if not all_products:
        # Fallback: return built-in products
        all_products = _builtin_products()

    _cached_products = all_products
    print(f"[Products] ✅ Loaded {len(all_products)} products")
    return all_products

def search_products(query='', category='', min_price=0, max_price=99999,
                    sort_by='relevance', page=1, per_page=20):
    """
    Search and filter products like Amazon.
    Returns paginated results.
    """
    products = fetch_all_products()
    q = query.lower().strip()

    # Filter
    filtered = []
    for p in products:
        if q and q not in p['name'].lower() and q not in p['category'].lower() and q not in p['description'].lower():
            continue
        if category and category.lower() not in p['category'].lower():
            continue
        if p['price'] < min_price or p['price'] > max_price:
            continue
        filtered.append(p)

    # Sort
    if sort_by == 'price_low':
        filtered.sort(key=lambda x: x['price'])
    elif sort_by == 'price_high':
        filtered.sort(key=lambda x: x['price'], reverse=True)
    elif sort_by == 'rating':
        filtered.sort(key=lambda x: x['rating'], reverse=True)
    elif sort_by == 'newest':
        filtered.sort(key=lambda x: x['id'], reverse=True)

    # Paginate
    total   = len(filtered)
    start   = (page - 1) * per_page
    end     = start + per_page
    pages   = (total + per_page - 1) // per_page

    return {
        'products':   filtered[start:end],
        'total':      total,
        'page':       page,
        'pages':      pages,
        'per_page':   per_page,
        'query':      query,
        'category':   category,
        'sort_by':    sort_by,
    }

def get_categories():
    """Get all unique categories."""
    products = fetch_all_products()
    cats = sorted(set(p['category'] for p in products if p['category']))
    return cats

def get_product_by_id(pid):
    products = fetch_all_products()
    return next((p for p in products if p['id'] == pid), None)

# ── FALLBACK built-in products ────────────────────────────────────────────────
def _builtin_products():
    categories = ['Electronics', 'Fashion', 'Home & Kitchen', 'Sports', 'Books',
                  'Beauty', 'Toys', 'Automotive', 'Garden', 'Health']
    products = []
    names = [
        'Wireless Headphones Pro', 'Smart Watch Series X', 'Laptop Stand Aluminum',
        'Mechanical Keyboard RGB', 'USB-C Hub 7-in-1', 'Webcam 4K HD',
        'Running Shoes Air Max', 'Yoga Mat Premium', 'Water Bottle Insulated',
        'Backpack Travel 40L', 'Sunglasses Polarized', 'Leather Wallet Slim',
        'Coffee Maker Automatic', 'Air Fryer 5.5L', 'Blender Pro 1200W',
        'Knife Set Professional', 'Cutting Board Bamboo', 'Storage Containers Set',
        'Python Programming Book', 'Machine Learning Guide', 'Data Science Handbook',
        'Face Moisturizer SPF50', 'Vitamin C Serum', 'Hair Dryer Ionic',
        'Resistance Bands Set', 'Dumbbells Adjustable', 'Jump Rope Speed',
        'LEGO Architecture Set', 'Board Game Strategy', 'Puzzle 1000 Pieces',
        'Car Phone Mount', 'Dash Cam 4K', 'Car Vacuum Cleaner',
        'Plant Pot Ceramic Set', 'Garden Tools Kit', 'Seed Starter Kit',
        'Protein Powder Vanilla', 'Multivitamin Daily', 'Sleep Aid Melatonin',
        'Desk Lamp LED', 'Monitor 27 inch 4K', 'Mouse Wireless Ergonomic',
        'Tablet Stand Adjustable', 'Phone Case Premium', 'Screen Protector Glass',
        'Earbuds True Wireless', 'Speaker Bluetooth Portable', 'Power Bank 20000mAh',
    ]
    for i, name in enumerate(names):
        cat = categories[i % len(categories)]
        products.append({
            'id':          4000 + i,
            'name':        name,
            'price':       round(random.uniform(9.99, 299.99), 2),
            'category':    cat,
            'description': f'High quality {name.lower()} with premium features and excellent build quality.',
            'image_url':   '',
            'rating':      round(random.uniform(3.8, 5.0), 1),
            'review_count':random.randint(50, 2000),
            'stock':       random.randint(5, 500),
            'seller_id':   2,
            'source':      'IntelliMarket',
            'badge':       '🔥 Hot Deal' if i % 5 == 0 else '',
            'discount':    random.choice([0, 0, 0, 10, 15, 20, 25]),
        })
    return products
