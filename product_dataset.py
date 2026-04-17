"""
Fetch 100+ real products with images from free public APIs.
No API key needed for most sources.
"""
import requests
import random
import time

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                  'AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'
}

# ── 1. DUMMYJSON — 100 products with real images ──────────────────────────────
def fetch_dummyjson(limit=100):
    try:
        r    = requests.get(f'https://dummyjson.com/products?limit={limit}&skip=0', timeout=10)
        data = r.json()
        products = []
        for p in data.get('products', []):
            products.append({
                'name':        p['title'],
                'price':       round(p['price'], 2),
                'category':    p['category'].replace('-',' ').title(),
                'description': p['description'][:300],
                'image_url':   p.get('thumbnail',''),
                'images':      p.get('images', [p.get('thumbnail','')]),
                'rating':      round(p.get('rating', 4.0), 1),
                'stock':       p.get('stock', 50),
                'discount':    int(p.get('discountPercentage', 0)),
                'brand':       p.get('brand',''),
                'source':      'DummyJSON',
            })
        return products
    except Exception as e:
        print(f"[DummyJSON] {e}")
        return []

# ── 2. FAKESTOREAPI — 20 products with real images ────────────────────────────
def fetch_fakestore():
    try:
        r    = requests.get('https://fakestoreapi.com/products', timeout=10)
        data = r.json()
        products = []
        for p in data:
            products.append({
                'name':        p['title'],
                'price':       round(p['price'], 2),
                'category':    p['category'].title(),
                'description': p['description'][:300],
                'image_url':   p['image'],
                'images':      [p['image']],
                'rating':      round(p['rating']['rate'], 1),
                'stock':       random.randint(10, 200),
                'discount':    random.choice([0, 0, 5, 10, 15]),
                'brand':       '',
                'source':      'FakeStore',
            })
        return products
    except Exception as e:
        print(f"[FakeStore] {e}")
        return []

# ── 3. OPEN FOOD FACTS — real food/beauty products ────────────────────────────
def fetch_beauty_products(limit=30):
    """Fetch beauty/skincare products from Open Beauty Facts."""
    try:
        url  = 'https://world.openbeautyfacts.org/cgi/search.pl?action=process&json=1&page_size=30&sort_by=popularity'
        r    = requests.get(url, headers=HEADERS, timeout=10)
        data = r.json()
        products = []
        for p in data.get('products', [])[:limit]:
            name = p.get('product_name','').strip()
            if not name or len(name) < 3:
                continue
            img = p.get('image_url','') or p.get('image_small_url','')
            products.append({
                'name':        name[:60],
                'price':       round(random.uniform(4.99, 49.99), 2),
                'category':    'Beauty & Skincare',
                'description': (p.get('ingredients_text','') or 'Premium beauty product')[:200],
                'image_url':   img,
                'images':      [img] if img else [],
                'rating':      round(random.uniform(3.8, 5.0), 1),
                'stock':       random.randint(20, 300),
                'discount':    random.choice([0, 0, 10, 15]),
                'brand':       p.get('brands','').split(',')[0].strip()[:30],
                'source':      'OpenBeautyFacts',
            })
        return products
    except Exception as e:
        print(f"[Beauty] {e}")
        return []

# ── 4. GENERATE PRODUCT DATASET FOR EACH SELLER ───────────────────────────────
SELLER_CATEGORIES = {
    2: {  # Ahmed Electronics
        'categories': ['Electronics', 'Smartphones', 'Laptops', 'Audio', 'Cameras'],
        'keywords':   ['wireless', 'smart', 'digital', 'bluetooth', 'HD', 'pro', 'ultra'],
        'price_range': (19.99, 999.99),
    },
    3: {  # Priya Fashion
        'categories': ['Fashion', 'Clothing', 'Accessories', 'Footwear', 'Bags'],
        'keywords':   ['designer', 'premium', 'trendy', 'classic', 'elegant', 'stylish'],
        'price_range': (9.99, 299.99),
    },
    4: {  # Ravi Tech
        'categories': ['Software', 'Education', 'Cloud', 'Tools', 'Courses'],
        'keywords':   ['pro', 'advanced', 'complete', 'master', 'expert', 'bundle'],
        'price_range': (4.99, 199.99),
    },
    5: {  # Meera Beauty
        'categories': ['Beauty', 'Skincare', 'Haircare', 'Makeup', 'Wellness'],
        'keywords':   ['organic', 'natural', 'premium', 'luxury', 'pure', 'glow'],
        'price_range': (4.99, 149.99),
    },
}

# Product templates per category
PRODUCT_TEMPLATES = {
    'Electronics': [
        ('Wireless Earbuds Pro {n}', '🎧', 'Premium wireless earbuds with active noise cancellation, 30hr battery life and crystal clear sound.'),
        ('Smart Watch Series {n}', '⌚', 'Advanced smartwatch with health monitoring, GPS, heart rate sensor and 7-day battery.'),
        ('Bluetooth Speaker {n}', '🔊', 'Portable waterproof bluetooth speaker with 360° surround sound and 20hr playtime.'),
        ('USB-C Hub {n} Port', '🔌', 'Multi-port USB-C hub with HDMI, USB 3.0, SD card reader and fast charging.'),
        ('Laptop Stand Pro {n}', '💻', 'Adjustable aluminum laptop stand with ergonomic design and heat dissipation.'),
        ('Mechanical Keyboard {n}', '⌨️', 'RGB mechanical keyboard with tactile switches, anti-ghosting and USB-C connection.'),
        ('Webcam HD {n}K', '📷', 'Ultra HD webcam with auto-focus, noise-cancelling mic and wide-angle lens.'),
        ('Power Bank {n}000mAh', '🔋', 'Fast charging power bank with {n}000mAh capacity, dual USB and LED indicator.'),
        ('Smart Home Hub {n}', '🏠', 'Voice-controlled smart home hub compatible with Alexa, Google Home and Apple HomeKit.'),
        ('Gaming Mouse {n}', '🖱️', 'Precision gaming mouse with {n}6000 DPI, RGB lighting and programmable buttons.'),
    ],
    'Fashion': [
        ('Designer Kurta Set {n}', '👗', 'Elegant designer kurta set with intricate embroidery and premium cotton fabric.'),
        ('Casual T-Shirt Pack {n}', '👕', 'Pack of {n} premium cotton casual t-shirts in trending colors.'),
        ('Leather Handbag {n}', '👜', 'Genuine leather handbag with multiple compartments and gold-tone hardware.'),
        ('Running Shoes {n}', '👟', 'Lightweight running shoes with air cushion sole and breathable mesh upper.'),
        ('Silk Saree {n}', '🥻', 'Pure silk saree with traditional zari border and matching blouse piece.'),
        ('Denim Jacket {n}', '🧥', 'Classic denim jacket with distressed finish and comfortable stretch fabric.'),
        ('Sunglasses UV{n}00', '🕶️', 'Polarized sunglasses with UV{n}00 protection and lightweight titanium frame.'),
        ('Watch Classic {n}', '⌚', 'Classic analog watch with stainless steel case and genuine leather strap.'),
        ('Backpack Travel {n}L', '🎒', '{n}L travel backpack with laptop compartment, USB charging port and waterproof.'),
        ('Ethnic Dress {n}', '👘', 'Beautiful ethnic dress with hand-block print and comfortable cotton fabric.'),
    ],
    'Software': [
        ('Python Masterclass {n}.0', '🐍', 'Complete Python programming course from beginner to advanced with {n}00+ exercises.'),
        ('ML Course Bundle {n}', '🤖', 'Machine learning bundle with {n} courses covering scikit-learn, TensorFlow and PyTorch.'),
        ('Web Dev Bootcamp {n}', '🌐', 'Full-stack web development bootcamp with React, Node.js, MongoDB and deployment.'),
        ('Data Science Pro {n}', '📊', 'Professional data science course with pandas, numpy, matplotlib and real projects.'),
        ('Cloud Storage {n}TB', '☁️', '{n}TB secure cloud storage with 99.9% uptime, auto-backup and file sharing.'),
        ('SEO Toolkit {n}', '🔍', 'Complete SEO analysis toolkit with keyword research, rank tracking and competitor analysis.'),
        ('Design Bundle {n}', '🎨', 'Professional design bundle with {n}000+ templates, fonts and graphic assets.'),
        ('Antivirus Pro {n}', '🛡️', 'Advanced antivirus protection for {n} devices with real-time threat detection.'),
        ('VPN Premium {n}', '🔒', 'Premium VPN service with {n}00+ servers, no-log policy and unlimited bandwidth.'),
        ('Project Manager {n}', '📋', 'Professional project management tool with Gantt charts, team collaboration and reporting.'),
    ],
    'Beauty': [
        ('Vitamin C Serum {n}ml', '✨', '{n}ml brightening vitamin C serum with hyaluronic acid for glowing skin.'),
        ('Lipstick Collection {n}', '💄', 'Set of {n} long-lasting matte lipsticks in trending shades with moisturizing formula.'),
        ('Hair Care Kit {n}', '💆', 'Complete hair care kit with shampoo, conditioner, hair mask and serum for {n} weeks.'),
        ('Face Moisturizer SPF{n}', '🧴', 'Daily face moisturizer with SPF{n} sun protection and anti-aging formula.'),
        ('Eye Shadow Palette {n}', '👁️', '{n}-shade eye shadow palette with matte and shimmer finishes for all occasions.'),
        ('Perfume {n}ml', '🌸', 'Luxury perfume {n}ml with long-lasting floral fragrance and elegant bottle design.'),
        ('Nail Polish Set {n}', '💅', 'Set of {n} chip-resistant nail polishes in seasonal colors with quick-dry formula.'),
        ('Face Mask Pack {n}', '😷', 'Pack of {n} sheet face masks with different ingredients for hydration and brightening.'),
        ('Kajal Eyeliner {n}', '✏️', 'Waterproof kajal eyeliner with smudge-proof formula lasting {n}+ hours.'),
        ('BB Cream SPF{n}', '🌟', 'Multi-tasking BB cream with SPF{n}, coverage, moisturizer and primer in one.'),
    ],
}

def generate_seller_products(seller_id: int, count: int = 100) -> list:
    """Generate 100 products for a specific seller with real-looking data."""
    config    = SELLER_CATEGORIES.get(seller_id, SELLER_CATEGORIES[2])
    templates = []
    for cat in config['categories']:
        cat_key = cat.split()[0] if cat.split()[0] in PRODUCT_TEMPLATES else 'Electronics'
        templates.extend([(t, cat) for t in PRODUCT_TEMPLATES.get(cat_key, PRODUCT_TEMPLATES['Electronics'])])

    # Image pools per category
    IMAGE_POOLS = {
        'Electronics': [
            'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=300',
            'https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=300',
            'https://images.unsplash.com/photo-1585386959984-a4155224a1ad?w=300',
            'https://images.unsplash.com/photo-1491553895911-0055eca6402d?w=300',
            'https://images.unsplash.com/photo-1526170375885-4d8ecf77b99f?w=300',
            'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=300',
            'https://images.unsplash.com/photo-1560343090-f0409e92791a?w=300',
            'https://images.unsplash.com/photo-1585386959984-a4155224a1ad?w=300',
        ],
        'Fashion': [
            'https://images.unsplash.com/photo-1523381210434-271e8be1f52b?w=300',
            'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=300',
            'https://images.unsplash.com/photo-1560343090-f0409e92791a?w=300',
            'https://images.unsplash.com/photo-1491553895911-0055eca6402d?w=300',
            'https://images.unsplash.com/photo-1526170375885-4d8ecf77b99f?w=300',
            'https://images.unsplash.com/photo-1585386959984-a4155224a1ad?w=300',
        ],
        'Software': [
            'https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=300',
            'https://images.unsplash.com/photo-1555066931-4365d14bab8c?w=300',
            'https://images.unsplash.com/photo-1461749280684-dccba630e2f6?w=300',
            'https://images.unsplash.com/photo-1504639725590-34d0984388bd?w=300',
        ],
        'Beauty': [
            'https://images.unsplash.com/photo-1596462502278-27bfdc403348?w=300',
            'https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=300',
            'https://images.unsplash.com/photo-1571781926291-c477ebfd024b?w=300',
            'https://images.unsplash.com/photo-1583241475880-083f84372725?w=300',
            'https://images.unsplash.com/photo-1599305445671-ac291c95aaa9?w=300',
        ],
    }

    products = []
    min_p, max_p = config['price_range']

    for i in range(count):
        tmpl_data, category = templates[i % len(templates)]
        name_tmpl, emoji, desc_tmpl = tmpl_data
        n       = i + 1
        name    = name_tmpl.replace('{n}', str(n % 10 + 1))
        desc    = desc_tmpl.replace('{n}', str(n % 10 + 1))
        price   = round(random.uniform(min_p, max_p), 2)
        cat_key = category.split()[0] if category.split()[0] in IMAGE_POOLS else 'Electronics'
        img_pool= IMAGE_POOLS.get(cat_key, IMAGE_POOLS['Electronics'])
        img_url = img_pool[i % len(img_pool)]

        products.append({
            'name':        name,
            'price':       price,
            'category':    category,
            'description': desc,
            'image_url':   img_url,
            'images':      [img_url],
            'rating':      round(random.uniform(3.5, 5.0), 1),
            'review_count':random.randint(10, 500),
            'stock':       random.randint(5, 500),
            'discount':    random.choice([0, 0, 0, 5, 10, 15, 20, 25]),
            'brand':       config['keywords'][i % len(config['keywords'])].title(),
            'seller_id':   seller_id,
            'image':       emoji,
            'source':      'Generated',
        })

    return products

def load_100_products_for_seller(seller_id: int) -> list:
    """
    Load 100 products for a seller.
    First tries real API, falls back to generated data.
    """
    print(f"[Products] Loading 100 products for seller {seller_id}...")

    # Try real API first
    real_products = []
    if seller_id == 2:  # Electronics seller
        real_products = fetch_dummyjson(80)
        real_products = [p for p in real_products
                        if p['category'].lower() in
                        ['smartphones','laptops','fragrances','skincare','home-decoration',
                         'furniture','tops','womens-dresses','mens-shirts','sunglasses']][:40]
    elif seller_id == 5:  # Beauty seller
        real_products = fetch_beauty_products(30)

    # Fill remaining with generated products
    generated = generate_seller_products(seller_id, 100 - len(real_products))

    all_products = real_products + generated
    print(f"[Products] ✅ Loaded {len(all_products)} products for seller {seller_id}")
    return all_products[:100]
