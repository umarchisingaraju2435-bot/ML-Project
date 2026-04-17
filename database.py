"""
Persistent storage using JSON files.
All data saved to disk — survives app restarts.
"""
import json
import os
import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

# ── FILE PATHS ─────────────────────────────────────────────────────────────────
FILES = {
    'users':           os.path.join(DATA_DIR, 'users.json'),
    'products':        os.path.join(DATA_DIR, 'products.json'),
    'orders':          os.path.join(DATA_DIR, 'orders.json'),
    'reviews':         os.path.join(DATA_DIR, 'reviews.json'),
    'jobs':            os.path.join(DATA_DIR, 'jobs.json'),
    'resumes':         os.path.join(DATA_DIR, 'resumes.json'),
    'applications':    os.path.join(DATA_DIR, 'applications.json'),
    'addresses':       os.path.join(DATA_DIR, 'addresses.json'),
    'notifications':   os.path.join(DATA_DIR, 'notifications.json'),
    'follows':         os.path.join(DATA_DIR, 'follows.json'),
    'wishlist':        os.path.join(DATA_DIR, 'wishlist.json'),
    'messages':        os.path.join(DATA_DIR, 'messages.json'),
}

# ── DEFAULT DATA ───────────────────────────────────────────────────────────────
DEFAULT_USERS = [
    {'id': 1, 'name': 'Admin Owner',      'email': 'owner@site.com',     'password': 'owner123',    'role': 'owner',    'avatar': '🌐', 'joined': '2024-01-01'},
    {'id': 2, 'name': 'Ahmed Electronics','email': 'ahmed@seller.com',   'password': 'seller123',   'role': 'seller',   'avatar': '🏪', 'joined': '2024-01-02', 'shop_name': 'Ahmed Electronics',  'shop_desc': 'Best electronics at lowest prices'},
    {'id': 3, 'name': 'Priya Fashion',    'email': 'priya@seller.com',   'password': 'priya123',    'role': 'seller',   'avatar': '👗', 'joined': '2024-01-03', 'shop_name': 'Priya Fashion Store', 'shop_desc': 'Trendy fashion for everyone'},
    {'id': 4, 'name': 'Ravi Tech Shop',   'email': 'ravi@seller.com',    'password': 'ravi123',     'role': 'seller',   'avatar': '💻', 'joined': '2024-01-04', 'shop_name': 'Ravi Tech Solutions', 'shop_desc': 'Software and tech products'},
    {'id': 5, 'name': 'Meera Beauty',     'email': 'meera@seller.com',   'password': 'meera123',    'role': 'seller',   'avatar': '💄', 'joined': '2024-01-05', 'shop_name': 'Meera Beauty Hub',    'shop_desc': 'Premium beauty and skincare'},
    {'id': 6, 'name': 'Sara Customer',    'email': 'customer@site.com',  'password': 'customer123', 'role': 'customer', 'avatar': '👤', 'joined': '2024-01-06'},
    {'id': 7, 'name': 'John Smith',       'email': 'john@customer.com',  'password': 'john123',     'role': 'customer', 'avatar': '👨', 'joined': '2024-01-07'},
    {'id': 8, 'name': 'Anita Sharma',     'email': 'anita@customer.com', 'password': 'anita123',    'role': 'customer', 'avatar': '👩', 'joined': '2024-01-08'},
    {'id': 9, 'name': 'Raj Kumar',        'email': 'raj@customer.com',   'password': 'raj123',      'role': 'customer', 'avatar': '🧑', 'joined': '2024-01-09'},
]

DEFAULT_PRODUCTS = [
    {'id': 1,  'name': 'Wireless Headphones Pro', 'seller_id': 2, 'price': 79.99,  'category': 'Electronics', 'stock': 50,  'image': '🎧', 'description': 'Premium wireless headphones with noise cancellation and 30hr battery.', 'rating': 4.5, 'review_count': 128, 'discount': 10},
    {'id': 2,  'name': 'Smart Watch Series X',    'seller_id': 2, 'price': 149.99, 'category': 'Electronics', 'stock': 30,  'image': '⌚', 'description': 'Advanced smartwatch with health monitoring and GPS.', 'rating': 4.3, 'review_count': 89,  'discount': 0},
    {'id': 3,  'name': 'Bluetooth Speaker',       'seller_id': 2, 'price': 49.99,  'category': 'Electronics', 'stock': 75,  'image': '🔊', 'description': 'Portable bluetooth speaker with 20hr battery life.', 'rating': 4.6, 'review_count': 203, 'discount': 15},
    {'id': 4,  'name': 'Designer Saree',          'seller_id': 3, 'price': 59.99,  'category': 'Fashion',     'stock': 40,  'image': '👗', 'description': 'Beautiful designer saree with embroidery work.', 'rating': 4.7, 'review_count': 156, 'discount': 0},
    {'id': 5,  'name': 'Casual T-Shirt Pack',     'seller_id': 3, 'price': 29.99,  'category': 'Fashion',     'stock': 200, 'image': '👕', 'description': 'Pack of 3 premium cotton casual t-shirts.', 'rating': 4.2, 'review_count': 312, 'discount': 20},
    {'id': 6,  'name': 'Leather Handbag',         'seller_id': 3, 'price': 89.99,  'category': 'Fashion',     'stock': 25,  'image': '👜', 'description': 'Genuine leather handbag with multiple compartments.', 'rating': 4.8, 'review_count': 78,  'discount': 5},
    {'id': 7,  'name': 'Python Course Bundle',    'seller_id': 4, 'price': 29.99,  'category': 'Education',   'stock': 999, 'image': '🐍', 'description': 'Complete Python programming from beginner to advanced.', 'rating': 4.9, 'review_count': 512, 'discount': 0},
    {'id': 8,  'name': 'ML Starter Kit',          'seller_id': 4, 'price': 49.99,  'category': 'Software',    'stock': 100, 'image': '🤖', 'description': 'Complete machine learning starter kit with tutorials.', 'rating': 4.4, 'review_count': 89,  'discount': 10},
    {'id': 9,  'name': 'Cloud Storage 1TB',       'seller_id': 4, 'price': 9.99,   'category': 'Cloud',       'stock': 999, 'image': '☁️', 'description': '1TB secure cloud storage with 99.9% uptime.', 'rating': 4.3, 'review_count': 341, 'discount': 0},
    {'id': 10, 'name': 'Lipstick Collection',     'seller_id': 5, 'price': 24.99,  'category': 'Beauty',      'stock': 150, 'image': '💄', 'description': 'Set of 6 long-lasting matte lipsticks in trending shades.', 'rating': 4.6, 'review_count': 445, 'discount': 0},
    {'id': 11, 'name': 'Vitamin C Serum',         'seller_id': 5, 'price': 34.99,  'category': 'Beauty',      'stock': 80,  'image': '✨', 'description': 'Brightening vitamin C serum for glowing skin.', 'rating': 4.7, 'review_count': 289, 'discount': 10},
    {'id': 12, 'name': 'Hair Care Kit',           'seller_id': 5, 'price': 44.99,  'category': 'Beauty',      'stock': 60,  'image': '💆', 'description': 'Complete hair care kit with shampoo, conditioner and mask.', 'rating': 4.5, 'review_count': 167, 'discount': 15},
]

DEFAULT_JOBS = [
    {'id': 1, 'title': 'ML Engineer',      'company': 'Ahmed Electronics', 'seller_id': 2, 'salary': '$3000/mo', 'location': 'Remote',    'description': 'Python machine learning TF-IDF NLP scikit-learn deep learning data science', 'posted': '2024-01-10'},
    {'id': 2, 'title': 'Fashion Designer', 'company': 'Priya Fashion',     'seller_id': 3, 'salary': '$2000/mo', 'location': 'Mumbai',    'description': 'Fashion design clothing textile creative design portfolio illustration', 'posted': '2024-01-12'},
    {'id': 3, 'title': 'Web Developer',    'company': 'Ravi Tech',         'seller_id': 4, 'salary': '$2500/mo', 'location': 'Bangalore', 'description': 'Flask Django React JavaScript HTML CSS REST API web development', 'posted': '2024-01-15'},
    {'id': 4, 'title': 'Beauty Advisor',   'company': 'Meera Beauty',      'seller_id': 5, 'salary': '$1500/mo', 'location': 'Delhi',     'description': 'Beauty skincare makeup cosmetics customer service sales retail', 'posted': '2024-01-16'},
]

DEFAULT_REVIEWS = [
    {'id': 1, 'product_id': 1,  'user_id': 6, 'user_name': 'Sara',  'rating': 5, 'review': 'Excellent headphones! Amazing sound quality.', 'date': '2024-01-10'},
    {'id': 2, 'product_id': 1,  'user_id': 7, 'user_name': 'John',  'rating': 4, 'review': 'Good product, comfortable to wear.', 'date': '2024-01-11'},
    {'id': 3, 'product_id': 1,  'user_id': 8, 'user_name': 'Anita', 'rating': 2, 'review': 'Battery life is very disappointing.', 'date': '2024-01-12'},
    {'id': 4, 'product_id': 4,  'user_id': 6, 'user_name': 'Sara',  'rating': 5, 'review': 'Beautiful saree, exactly as shown!', 'date': '2024-01-13'},
    {'id': 5, 'product_id': 7,  'user_id': 9, 'user_name': 'Raj',   'rating': 5, 'review': 'Best Python course ever! Very detailed.', 'date': '2024-01-14'},
    {'id': 6, 'product_id': 10, 'user_id': 6, 'user_name': 'Sara',  'rating': 5, 'review': 'Love the lipstick collection! Long lasting.', 'date': '2024-01-15'},
    {'id': 7, 'product_id': 10, 'user_id': 8, 'user_name': 'Anita', 'rating': 4, 'review': 'Good shades, nice packaging.', 'date': '2024-01-16'},
    {'id': 8, 'product_id': 11, 'user_id': 6, 'user_name': 'Sara',  'rating': 5, 'review': 'Skin is glowing after using this serum!', 'date': '2024-01-17'},
]

DEFAULT_ORDERS = [
    {'id': 1, 'user_id': 6, 'seller_id': 2, 'product_id': 1,  'name': 'Wireless Headphones Pro', 'price': 79.99, 'status': 'Delivered', 'payment': 'COD',  'date': '2024-01-05', 'address': {'full_name': 'Sara Customer', 'phone': '9876543210', 'address': '123 Main Street', 'city': 'Chennai', 'state': 'Tamil Nadu', 'pincode': '600001', 'landmark': 'Near Bus Stop', 'address_type': 'Home'}},
    {'id': 2, 'user_id': 6, 'seller_id': 5, 'product_id': 10, 'name': 'Lipstick Collection',     'price': 24.99, 'status': 'Delivered', 'payment': 'UPI',  'date': '2024-01-06', 'address': {'full_name': 'Sara Customer', 'phone': '9876543210', 'address': '123 Main Street', 'city': 'Chennai', 'state': 'Tamil Nadu', 'pincode': '600001', 'landmark': 'Near Bus Stop', 'address_type': 'Home'}},
    {'id': 3, 'user_id': 7, 'seller_id': 4, 'product_id': 7,  'name': 'Python Course Bundle',    'price': 29.99, 'status': 'Active',    'payment': 'Card', 'date': '2024-01-07', 'address': {'full_name': 'John Smith', 'phone': '9123456789', 'address': '456 Park Avenue', 'city': 'Mumbai', 'state': 'Maharashtra', 'pincode': '400001', 'landmark': 'Near Mall', 'address_type': 'Home'}},
    {'id': 4, 'user_id': 8, 'seller_id': 3, 'product_id': 4,  'name': 'Designer Saree',          'price': 59.99, 'status': 'Processing','payment': 'COD',  'date': '2024-01-08', 'address': {'full_name': 'Anita Sharma', 'phone': '9988776655', 'address': '789 Lake Road', 'city': 'Delhi', 'state': 'Delhi', 'pincode': '110001', 'landmark': 'Near Metro', 'address_type': 'Home'}},
    {'id': 5, 'user_id': 9, 'seller_id': 5, 'product_id': 11, 'name': 'Vitamin C Serum',         'price': 34.99, 'status': 'Shipped',   'payment': 'UPI',  'date': '2024-01-09', 'address': {'full_name': 'Raj Kumar', 'phone': '9765432100', 'address': '321 Hill Street', 'city': 'Bangalore', 'state': 'Karnataka', 'pincode': '560001', 'landmark': 'Near Park', 'address_type': 'Home'}},
]

DEFAULT_ADDRESSES = [
    {'id': 1, 'user_id': 6, 'full_name': 'Sara Customer', 'phone': '9876543210', 'address': '123 Main Street', 'city': 'Chennai',   'state': 'Tamil Nadu',  'pincode': '600001', 'landmark': 'Near Central Bus Stop', 'address_type': 'Home', 'is_default': True},
    {'id': 2, 'user_id': 7, 'full_name': 'John Smith',    'phone': '9123456789', 'address': '456 Park Avenue', 'city': 'Mumbai',    'state': 'Maharashtra', 'pincode': '400001', 'landmark': 'Near Shopping Mall',    'address_type': 'Home', 'is_default': True},
    {'id': 3, 'user_id': 8, 'full_name': 'Anita Sharma',  'phone': '9988776655', 'address': '789 Lake Road',   'city': 'Delhi',     'state': 'Delhi',       'pincode': '110001', 'landmark': 'Near Metro Station',    'address_type': 'Home', 'is_default': True},
    {'id': 4, 'user_id': 9, 'full_name': 'Raj Kumar',     'phone': '9765432100', 'address': '321 Hill Street', 'city': 'Bangalore', 'state': 'Karnataka',   'pincode': '560001', 'landmark': 'Near City Park',        'address_type': 'Home', 'is_default': True},
]

# ── LOAD / SAVE ────────────────────────────────────────────────────────────────
def load(key, default):
    path = FILES[key]
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    # First run — save defaults
    save(key, default)
    return default

def save(key, data):
    with open(FILES[key], 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ── LOAD ALL DATA ──────────────────────────────────────────────────────────────
users_db           = load('users',        DEFAULT_USERS)
products_db        = load('products',     DEFAULT_PRODUCTS)
orders_db          = load('orders',       DEFAULT_ORDERS)
product_reviews_db = load('reviews',      DEFAULT_REVIEWS)
jobs_db            = load('jobs',         DEFAULT_JOBS)
resumes_db         = load('resumes',      [])
applications_db    = load('applications', [])
addresses_db       = load('addresses',    DEFAULT_ADDRESSES)
notifications_db   = load('notifications',[])
follows_db         = load('follows',      [])
wishlist_db        = load('wishlist',     [])
messages_db        = load('messages',     [])
chat_history_db    = {}

stock_db = {
    'AAPL': {'name': 'Apple Inc.',  'prices': [182,185,183,188,190,187,192], 'dates': ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']},
    'GOOGL':{'name': 'Google',      'prices': [140,138,142,145,143,147,150], 'dates': ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']},
    'AMZN': {'name': 'Amazon',      'prices': [178,175,180,182,179,184,186], 'dates': ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']},
    'MSFT': {'name': 'Microsoft',   'prices': [375,378,372,380,382,379,385], 'dates': ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']},
    'TSLA': {'name': 'Tesla',       'prices': [245,238,250,242,255,248,260], 'dates': ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']},
}

# ── AUTO-SAVE HELPERS ──────────────────────────────────────────────────────────
def save_products():    save('products',     products_db)
def save_users():       save('users',        users_db)
def save_orders():      save('orders',       orders_db)
def save_reviews():     save('reviews',      product_reviews_db)
def save_jobs():        save('jobs',         jobs_db)
def save_resumes():     save('resumes',      resumes_db)
def save_applications():save('applications', applications_db)
def save_addresses():   save('addresses',    addresses_db)
def save_notifications():save('notifications',notifications_db)
def save_follows():     save('follows',      follows_db)
def save_wishlist():    save('wishlist',     wishlist_db)
def save_messages():    save('messages',     messages_db)

def save_all():
    for key, data in [
        ('products', products_db), ('users', users_db),
        ('orders', orders_db), ('reviews', product_reviews_db),
        ('jobs', jobs_db), ('resumes', resumes_db),
        ('applications', applications_db), ('addresses', addresses_db),
        ('notifications', notifications_db), ('follows', follows_db),
        ('wishlist', wishlist_db),
    ]:
        save(key, data)

# ── HELPERS ────────────────────────────────────────────────────────────────────
def add_notification(user_id, role, title, message, notif_type='info'):
    notifications_db.append({
        'id':      len(notifications_db) + 1,
        'user_id': user_id, 'role': role,
        'title':   title,   'message': message,
        'type':    notif_type, 'read': False,
        'time':    datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    })
    save_notifications()

def get_notifications(user_id=None, role=None):
    result = [n for n in notifications_db
              if n['user_id'] == user_id or n['role'] == role]
    return list(reversed(result))

def mark_all_read(user_id, role):
    for n in notifications_db:
        if n['user_id'] == user_id or n['role'] == role:
            n['read'] = True
    save_notifications()

def get_user(email, password):
    return next((u for u in users_db if u['email'] == email and u['password'] == password), None)

def register_user(name, email, password, role, avatar='👤'):
    if any(u['email'] == email for u in users_db):
        return None
    user = {
        'id':       len(users_db) + 1,
        'name':     name, 'email': email,
        'password': password, 'role': role,
        'avatar':   avatar,
        'joined':   datetime.date.today().isoformat(),
    }
    if role == 'seller':
        user['shop_name'] = name
        user['shop_desc'] = 'Welcome to my store!'
    users_db.append(user)
    save_users()
    return user

def notify_only_buyer(order_id, title, message, notif_type='info'):
    order = next((o for o in orders_db if o['id'] == order_id), None)
    if order:
        add_notification(order['user_id'], None, title, message, notif_type)

def notify_product_followers(seller_id, product_name, message):
    for f in follows_db:
        if f['seller_id'] == seller_id:
            add_notification(f['user_id'], None,
                f'🆕 New Product: {product_name}', message, 'info')

def is_following(user_id, seller_id):
    return any(f['user_id'] == user_id and f['seller_id'] == seller_id for f in follows_db)

def get_review_summary(product_id):
    reviews = [r for r in product_reviews_db if r['product_id'] == product_id]
    if not reviews:
        return {'avg': 0, 'count': 0, 'reviews': []}
    avg = round(sum(r['rating'] for r in reviews) / len(reviews), 1)
    return {'avg': avg, 'count': len(reviews), 'reviews': reviews}
