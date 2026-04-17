import os
import io
import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename
import PyPDF2
import docx
from authlib.integrations.flask_client import OAuth

from ml.sentiment import analyze_sentiment
from ml.bert_sentiment import analyze_reviews_bert
from ml.fake_review_detector import analyze_fake_reviews, detect_fake_review
from ml.product_dataset import load_100_products_for_seller, generate_seller_products
from ml.resume_matcher import match_resumes, suggest_resume_improvements
from ml.price_trend import analyze_price_trend
from ml.agent import generate_strategy
from ml.interview_gen import generate_interview_questions
from database import (
    users_db, resumes_db, jobs_db, products_db,
    notifications_db, orders_db, applications_db, stock_db, addresses_db,
    add_notification, get_notifications, mark_all_read,
    get_user, register_user, notify_only_buyer, notify_product_followers,
    follows_db, product_reviews_db, wishlist_db, messages_db,
    save_products, save_users, save_orders, save_reviews,
    save_jobs, save_resumes, save_applications, save_addresses,
    save_notifications, save_follows, save_wishlist, save_messages, save_all
)
from translations import t, get_dir, get_lang, TRANSLATIONS
from ml.data_fetcher import (
    fetch_all_stocks, fetch_remote_jobs, fetch_product_reviews,
    fetch_tech_news, fetch_crypto_prices, fetch_sample_reviews
)
from ml.product_fetcher import search_products, get_categories, get_product_by_id, fetch_all_products

app = Flask(__name__)
app.secret_key = 'intellimarket_secret_2024'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

# ── GOOGLE OAUTH SETUP ────────────────────────────────────────────────────────
# To use real Google OAuth:
# 1. Go to https://console.cloud.google.com
# 2. Create OAuth 2.0 credentials
# 3. Set redirect URI: http://127.0.0.1:5001/auth/google/callback
# 4. Replace below with your real credentials
GOOGLE_CLIENT_ID     = os.environ.get('GOOGLE_CLIENT_ID',     'YOUR_GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', 'YOUR_GOOGLE_CLIENT_SECRET')

oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)

ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt'}
IMAGE_EXTENSIONS   = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER_IMAGES'] = os.path.join('static', 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER_IMAGES'], exist_ok=True)

def allowed_image(f):
    return '.' in f and f.rsplit('.', 1)[1].lower() in IMAGE_EXTENSIONS

def save_image(file):
    if file and allowed_image(file.filename):
        ext      = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')}.{ext}"
        path     = os.path.join(app.config['UPLOAD_FOLDER_IMAGES'], filename)
        file.save(path)
        return f"/static/uploads/{filename}"
    return None

# ── HELPERS ────────────────────────────────────────────────────────────────────
def allowed_file(f):
    return '.' in f and f.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text(file):
    fn = file.filename.lower()
    data = file.read()
    if fn.endswith('.pdf'):
        reader = PyPDF2.PdfReader(io.BytesIO(data))
        return ' '.join(p.extract_text() or '' for p in reader.pages)
    elif fn.endswith('.docx'):
        doc = docx.Document(io.BytesIO(data))
        return ' '.join(p.text for p in doc.paragraphs)
    return data.decode('utf-8', errors='ignore')

def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please login first.', 'error')
                return redirect(url_for('login'))
            if role and session.get('role') != role:
                flash('Access denied.', 'error')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return wrapper
    return decorator

def ctx():
    """Common template context."""
    uid = session.get('user_id')
    role = session.get('role')
    unread = len([n for n in notifications_db
                  if (n['user_id'] == uid or n['role'] == role) and not n['read']])
    return {
        'tr': lambda k: t(session, k),
        'dir': get_dir(session),
        'lang': get_lang(session),
        'langs': TRANSLATIONS,
        'current_user': session.get('name'),
        'current_role': role,
        'unread_count': unread,
    }

# ── LANGUAGE ───────────────────────────────────────────────────────────────────
@app.route('/set_lang/<lang>')
def set_lang(lang):
    if lang in TRANSLATIONS:
        session['lang'] = lang
    return redirect(request.referrer or url_for('index'))

# ── AUTH ───────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('landing.html', **ctx())

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = get_user(request.form['email'], request.form['password'])
        if user:
            session['user_id'] = user['id']
            session['name']    = user['name']
            session['role']    = user['role']
            session['email']   = user['email']
            return redirect(url_for('dashboard'))
        flash('Invalid email or password.', 'error')
    return render_template('login.html', **ctx())

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user = register_user(
            request.form['name'],
            request.form['email'],
            request.form['password'],
            request.form['role']
        )
        if user:
            session['user_id'] = user['id']
            session['name']    = user['name']
            session['role']    = user['role']
            session['email']   = user['email']
            flash(f"Welcome {user['name']}!", 'success')
            return redirect(url_for('dashboard'))
        flash('Email already registered.', 'error')
    return render_template('register.html', **ctx())

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ── DASHBOARD (role-based) ─────────────────────────────────────────────────────
@app.route('/dashboard')
@login_required()
def dashboard():
    role = session['role']
    uid  = session['user_id']
    notifs = get_notifications(uid, role)[:5]
    c = ctx()

    if role == 'seller':
        my_jobs     = [j for j in jobs_db if j['seller_id'] == uid]
        my_products = [p for p in products_db if p['seller_id'] == uid]
        my_apps     = [a for a in applications_db if a['seller_id'] == uid]
        # Check product loss
        for p in my_products:
            if p['stock'] < 10:
                add_notification(uid, 'seller',
                    t(session,'product_loss_alert'),
                    f"Product '{p['name']}' has only {p['stock']} units left!", 'warning')
        return render_template('seller/dashboard.html',
            jobs=my_jobs, products=my_products,
            applications=my_apps, notifications=notifs, **c)

    elif role == 'customer':
        my_resumes = [r for r in resumes_db if r['user_id'] == uid]
        my_orders  = [o for o in orders_db  if o['user_id'] == uid]
        my_apps    = [a for a in applications_db if a['user_id'] == uid]
        return render_template('customer/dashboard.html',
            resumes=my_resumes, orders=my_orders,
            applications=my_apps, notifications=notifs,
            jobs=jobs_db[:3], products=products_db[:3], **c)

    else:  # owner
        total_users    = len(users_db)
        total_resumes  = len(resumes_db)
        total_jobs     = len(jobs_db)
        total_products = len(products_db)
        total_orders   = len(orders_db)
        return render_template('owner/dashboard.html',
            total_users=total_users, total_resumes=total_resumes,
            total_jobs=total_jobs, total_products=total_products,
            total_orders=total_orders, notifications=notifs,
            users=users_db, **c)

# ── NOTIFICATIONS ──────────────────────────────────────────────────────────────
@app.route('/notifications')
@login_required()
def notifications():
    uid  = session['user_id']
    role = session['role']
    mark_all_read(uid, role)
    notifs = get_notifications(uid, role)
    return render_template('notifications.html', notifications=notifs, **ctx())

@app.route('/notifications/count')
@login_required()
def notif_count():
    uid  = session['user_id']
    role = session['role']
    count = len([n for n in notifications_db
                 if (n['user_id'] == uid or n['role'] == role) and not n['read']])
    return jsonify({'count': count})

# ── SELLER: MARKET ANALYSIS ────────────────────────────────────────────────────
@app.route('/seller/market', methods=['GET', 'POST'])
@login_required('seller')
def seller_market():
    results = None
    if request.method == 'POST':
        reviews_raw = request.form.get('reviews', '')
        reviews     = [r.strip() for r in reviews_raw.split('\n') if r.strip()]
        your_price  = float(request.form.get('your_price', 100))

        sentiment_result = analyze_sentiment(reviews) if reviews else {'score': 0, 'summary': {}, 'results': []}
        session['last_sentiment_score'] = sentiment_result['score']

        comp_names      = request.form.getlist('comp_name')
        comp_prices_raw = request.form.getlist('comp_prices')
        competitor_data = []
        for name, ps in zip(comp_names, comp_prices_raw):
            try:
                prices = [float(x.strip()) for x in ps.split(',') if x.strip()]
                if prices:
                    competitor_data.append({'name': name, 'prices': prices})
            except ValueError:
                continue

        if not competitor_data:
            competitor_data = [
                {'name': 'Competitor A', 'prices': [95, 92, 88, 85]},
                {'name': 'Competitor B', 'prices': [110, 112, 115, 118]},
            ]

        trends   = analyze_price_trend(competitor_data)
        strategy = generate_strategy(sentiment_result['score'], trends, your_price)

        # Notify seller if loss detected
        for s in strategy:
            if s['priority'] in ('CRITICAL', 'HIGH'):
                add_notification(session['user_id'], 'seller',
                    t(session, 'product_loss_alert'), s['suggestion'], 'warning')

        results = {'sentiment': sentiment_result, 'trends': trends,
                   'strategy': strategy, 'your_price': your_price}

    return render_template('seller/market.html', results=results, **ctx())

# ── SELLER: STOCK MARKET ───────────────────────────────────────────────────────
@app.route('/seller/stocks')
@login_required('seller')
def seller_stocks():
    analysis = []
    for ticker, data in stock_db.items():
        prices  = data['prices']
        change  = round(prices[-1] - prices[0], 2)
        pct     = round((change / prices[0]) * 100, 1)
        trend   = 'Rising' if change > 0 else ('Falling' if change < 0 else 'Stable')
        if trend == 'Falling' and abs(pct) > 3:
            add_notification(session['user_id'], 'seller',
                t(session, 'stock_alert'),
                f"{data['name']} dropped {abs(pct)}% — consider reviewing your strategy.", 'danger')
        analysis.append({'ticker': ticker, 'name': data['name'],
                         'prices': prices, 'dates': data['dates'],
                         'current': prices[-1], 'change': change,
                         'pct': pct, 'trend': trend})
    return render_template('seller/stocks.html', stocks=analysis, **ctx())

# ── SELLER: JOBS ───────────────────────────────────────────────────────────────
@app.route('/seller/jobs')
@login_required('seller')
def seller_jobs():
    my_jobs = [j for j in jobs_db if j['seller_id'] == session['user_id']]
    apps    = [a for a in applications_db if a['seller_id'] == session['user_id']]
    return render_template('seller/jobs.html', jobs=my_jobs, applications=apps, **ctx())

@app.route('/seller/jobs/post', methods=['GET', 'POST'])
@login_required('seller')
def post_job():
    if request.method == 'POST':
        job = {
            'id':          len(jobs_db) + 1,
            'title':       request.form['title'],
            'company':     request.form['company'],
            'seller_id':   session['user_id'],
            'salary':      request.form['salary'],
            'location':    request.form['location'],
            'description': request.form['description'],
            'posted':      datetime.date.today().isoformat(),
        }
        jobs_db.append(job)
        add_notification(0, 'customer', '💼 New Job Posted!',
            f"{job['title']} at {job['company']} — {job['location']} | {job['salary']}", 'info')
        save_jobs()
        flash('Job posted successfully!', 'success')
        return redirect(url_for('seller_jobs'))
    return render_template('seller/post_job.html', **ctx())

@app.route('/seller/resume/<int:resume_id>')
@login_required('seller')
def view_resume(resume_id):
    resume = next((r for r in resumes_db if r['id'] == resume_id), None)
    if not resume:
        flash('Resume not found.', 'error')
        return redirect(url_for('seller_jobs'))
    return render_template('seller/view_resume.html', resume=resume, jobs=jobs_db, **ctx())

@app.route('/seller/match/<int:job_id>')
@login_required('seller')
def seller_match(job_id):
    job = next((j for j in jobs_db if j['id'] == job_id), None)
    if not job or not resumes_db:
        flash('No resumes yet or job not found.', 'error')
        return redirect(url_for('seller_jobs'))
    ranked = match_resumes(job['description'], resumes_db)
    return render_template('seller/match_results.html', job=job, ranked=ranked, **ctx())

# ── CUSTOMER: RESUME ───────────────────────────────────────────────────────────
@app.route('/customer/resume', methods=['GET', 'POST'])
@login_required('customer')
def customer_resume():
    uid        = session['user_id']
    my_resumes = [r for r in resumes_db if r['user_id'] == uid]

    if request.method == 'POST':
        file        = request.files.get('resume_file')
        manual_text = request.form.get('resume_text', '').strip()
        skills      = request.form.get('skills', '').strip()
        experience  = request.form.get('experience', '').strip()

        resume_text = ''
        if file and file.filename and allowed_file(file.filename):
            resume_text = extract_text(file)
        elif manual_text:
            resume_text = manual_text

        if not resume_text:
            resume_text = f"Skills: {skills}\nExperience: {experience}"

        action = request.form.get('action', 'upload')

        if action == 'update' and my_resumes:
            # Update existing resume
            for r in resumes_db:
                if r['user_id'] == uid:
                    r['text']       = resume_text
                    r['skills']     = skills
                    r['experience'] = experience
                    r['updated']    = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
                    break
            # Notify all sellers
            for u in users_db:
                if u['role'] == 'seller':
                    add_notification(u['id'], 'seller',
                        '🔄 Resume Updated!',
                        f"{session['name']} updated their resume. Check it out!", 'info')
            flash(t(session, 'resume_uploaded'), 'success')
        else:
            # New upload
            resume = {
                'id':         len(resumes_db) + 1,
                'user_id':    uid,
                'name':       session['name'],
                'email':      session['email'],
                'text':       resume_text,
                'skills':     skills,
                'experience': experience,
                'updated':    datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
            }
            resumes_db.append(resume)
            # Notify ALL sellers
            for u in users_db:
                if u['role'] == 'seller':
                    add_notification(u['id'], 'seller',
                        t(session, 'new_resume_alert'),
                        f"{session['name']} submitted a new resume. Click to view!", 'success')
            # Notify owner
            add_notification(0, 'owner', '📄 New Resume on Platform',
                f"{session['name']} uploaded a resume.", 'info')
            save_resumes()
            flash(t(session, 'resume_uploaded'), 'success')

        return redirect(url_for('customer_resume'))

    return render_template('customer/resume.html',
                           my_resumes=my_resumes, jobs=jobs_db, **ctx())

# ── CUSTOMER: JOBS ─────────────────────────────────────────────────────────────
@app.route('/customer/jobs')
@login_required('customer')
def customer_jobs():
    query = request.args.get('q', '').lower()
    filtered = [j for j in jobs_db if query in j['title'].lower()
                or query in j['description'].lower()] if query else jobs_db
    my_apps = [a['job_id'] for a in applications_db if a['user_id'] == session['user_id']]
    return render_template('customer/jobs.html',
                           jobs=filtered, my_apps=my_apps, query=query, **ctx())

@app.route('/customer/apply/<int:job_id>', methods=['GET', 'POST'])
@login_required('customer')
def apply_job(job_id):
    uid = session['user_id']
    job = next((j for j in jobs_db if j['id'] == job_id), None)
    if not job:
        flash('Job not found.', 'error')
        return redirect(url_for('customer_jobs'))

    already = any(a['user_id'] == uid and a['job_id'] == job_id for a in applications_db)
    if already:
        flash('You already applied for this job.', 'error')
        return redirect(url_for('customer_jobs'))

    my_resumes = [r for r in resumes_db if r['user_id'] == uid]

    if request.method == 'POST':
        resume_id = int(request.form.get('resume_id', 0))
        resume    = next((r for r in resumes_db if r['id'] == resume_id), None)
        app_entry = {
            'id':        len(applications_db) + 1,
            'user_id':   uid,
            'job_id':    job_id,
            'seller_id': job['seller_id'],
            'name':      session['name'],
            'email':     session['email'],
            'resume_id': resume_id,
            'status':    'Applied',
            'applied':   datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
        }
        applications_db.append(app_entry)
        # Notify seller
        add_notification(job['seller_id'], 'seller',
            '📩 New Job Application!',
            f"{session['name']} applied for '{job['title']}'. Review their resume!", 'success')
        save_applications()
        flash('Application submitted successfully!', 'success')
        return redirect(url_for('customer_jobs'))

    return render_template('customer/apply_job.html',
                           job=job, my_resumes=my_resumes, **ctx())

# ── CUSTOMER: PRODUCTS ─────────────────────────────────────────────────────────
@app.route('/customer/products')
@login_required('customer')
def customer_products():
    query    = request.args.get('q', '').lower()
    filtered = [p for p in products_db if query in p['name'].lower()
                or query in p['category'].lower()] if query else products_db
    return render_template('customer/products.html',
                           products=filtered, query=query, **ctx())

@app.route('/customer/buy/<int:product_id>')
@login_required('customer')
def buy_product(product_id):
    product = next((p for p in products_db if p['id'] == product_id), None)
    if not product or product['stock'] < 1:
        flash('Product not available.', 'error')
        return redirect(url_for('customer_products'))
    order = {
        'id':         len(orders_db) + 1,
        'user_id':    session['user_id'],
        'product_id': product_id,
        'name':       product['name'],
        'price':      product['price'],
        'status':     'Confirmed',
        'date':       datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
    }
    orders_db.append(order)
    product['stock'] -= 1
    add_notification(product['seller_id'], 'seller',
        '🛒 New Order!',
        f"{session['name']} purchased '{product['name']}' for ${product['price']}", 'success')
    flash(f"Order placed for {product['name']}!", 'success')
    return redirect(url_for('customer_products'))

# ── CUSTOMER: INTERVIEW ────────────────────────────────────────────────────────
@app.route('/customer/interview/<int:resume_id>/<int:job_id>', methods=['GET', 'POST'])
@login_required('customer')
def customer_interview(resume_id, job_id):
    resume = next((r for r in resumes_db if r['id'] == resume_id), None)
    job    = next((j for j in jobs_db    if j['id'] == job_id),    None)
    if not resume or not job:
        flash('Not found.', 'error')
        return redirect(url_for('customer_resume'))
    questions = generate_interview_questions(job['description'], resume['text'], job['company'])
    if request.method == 'POST':
        answers  = {q['question']: request.form.get(f'ans_{i}', '') for i, q in enumerate(questions)}
        answered = sum(1 for a in answers.values() if a.strip())
        score    = round((answered / len(questions)) * 100)
        return render_template('customer/interview_result.html',
                               resume=resume, job=job, answers=answers,
                               score=score, total=len(questions), **ctx())
    return render_template('customer/interview.html',
                           resume=resume, job=job, questions=questions, **ctx())

# ── OWNER: ANALYTICS ──────────────────────────────────────────────────────────
@app.route('/owner/analytics')
@login_required('owner')
def owner_analytics():
    stock_analysis = []
    for ticker, data in stock_db.items():
        prices = data['prices']
        change = round(prices[-1] - prices[0], 2)
        pct    = round((change / prices[0]) * 100, 1)
        stock_analysis.append({
            'ticker': ticker, 'name': data['name'],
            'prices': prices, 'dates': data['dates'],
            'current': prices[-1], 'change': change, 'pct': pct,
            'trend': 'Rising' if change > 0 else ('Falling' if change < 0 else 'Stable')
        })
    return render_template('owner/analytics.html',
                           stocks=stock_analysis,
                           users=users_db,
                           resumes=resumes_db,
                           jobs=jobs_db,
                           products=products_db,
                           orders=orders_db,
                           applications=applications_db,
                           **ctx())

@app.route('/owner/users')
@login_required('owner')
def owner_users():
    return render_template('owner/users.html', users=users_db, **ctx())

# ── SELLER: BULK ADD PRODUCTS ───────────────────────────────────────────────

@app.route('/seller/products/bulk', methods=['GET','POST'])
@login_required('seller')
def seller_bulk_add():
    if request.method == 'POST':
        added = 0
        # Method 1: CSV file upload
        csv_file = request.files.get('csv_file')
        if csv_file and csv_file.filename.endswith('.csv'):
            import csv, io as _io
            content = csv_file.read().decode('utf-8')
            reader  = csv.DictReader(_io.StringIO(content))
            for row in reader:
                try:
                    p = {
                        'id':          len(products_db) + 1,
                        'seller_id':   session['user_id'],
                        'name':        row.get('name','').strip(),
                        'price':       float(row.get('price', 0)),
                        'category':    row.get('category','General').strip(),
                        'description': row.get('description','').strip(),
                        'stock':       int(row.get('stock', 0)),
                        'image':       row.get('image','📦').strip(),
                        'discount':    int(row.get('discount', 0)),
                        'rating':      0.0,
                        'review_count':0,
                    }
                    if p['name'] and p['price'] > 0:
                        products_db.append(p)
                        added += 1
                except:
                    continue

        # Method 2: Quick multi-form
        names        = request.form.getlist('name')
        prices       = request.form.getlist('price')
        categories   = request.form.getlist('category')
        descriptions = request.form.getlist('description')
        stocks       = request.form.getlist('stock')
        images       = request.form.getlist('image')
        discounts    = request.form.getlist('discount')

        for i in range(len(names)):
            try:
                name  = names[i].strip()
                price = float(prices[i]) if i < len(prices) else 0
                if not name or price <= 0:
                    continue
                p = {
                    'id':          len(products_db) + 1,
                    'seller_id':   session['user_id'],
                    'name':        name,
                    'price':       price,
                    'category':    categories[i].strip() if i < len(categories) else 'General',
                    'description': descriptions[i].strip() if i < len(descriptions) else '',
                    'stock':       int(stocks[i]) if i < len(stocks) and stocks[i] else 0,
                    'image':       images[i].strip() if i < len(images) and images[i] else '📦',
                    'discount':    int(discounts[i]) if i < len(discounts) and discounts[i] else 0,
                    'rating':      0.0,
                    'review_count':0,
                }
                products_db.append(p)
                added += 1
            except:
                continue

        if added > 0:
            add_notification(session['user_id'], 'seller',
                f'✅ {added} Products Added!',
                f'Successfully added {added} new products to your store.', 'success')
            add_notification(0, 'customer', f'🆕 {added} New Products Available!',
                'New products just added to the store. Check them out!', 'info')
            save_products()
            flash(f'✅ {added} products added successfully!', 'success')
        else:
            flash('No valid products found. Check your data.', 'error')
        return redirect(url_for('seller_products'))

    return render_template('seller/bulk_add.html', **ctx())

@app.route('/seller/products/duplicate/<int:product_id>')
@login_required('seller')
def seller_duplicate_product(product_id):
    original = next((p for p in products_db
                     if p['id'] == product_id and p['seller_id'] == session['user_id']), None)
    if original:
        import copy
        new_p = copy.deepcopy(original)
        new_p['id']   = len(products_db) + 1
        new_p['name'] = original['name'] + ' (Copy)'
        products_db.append(new_p)
        flash(f"Product duplicated as '{new_p['name']}'!", 'success')
    return redirect(url_for('seller_products'))

# ── SELLER: PRODUCTS (Add / Edit / Update Stock) ─────────────────────────────

@app.route('/seller/products')
@login_required('seller')
def seller_products():
    uid         = session['user_id']
    my_products = [p for p in products_db if p['seller_id'] == uid]
    my_orders   = [o for o in orders_db if any(p['id'] == o['product_id'] for p in my_products)]
    total_revenue = round(sum(o['price'] for o in my_orders), 2)
    from database import product_reviews_db
    return render_template('seller/products.html',
                           products=my_products,
                           orders=my_orders,
                           total_revenue=total_revenue,
                           product_reviews=product_reviews_db,
                           **ctx())

@app.route('/seller/products/add', methods=['GET','POST'])
@login_required('seller')
def seller_add_product():
    if request.method == 'POST':
        img_file = request.files.get('image_file')
        img_url  = save_image(img_file) if img_file and img_file.filename else None
        p = {
            'id':          len(products_db) + 1,
            'seller_id':   session['user_id'],
            'name':        request.form['name'],
            'price':       float(request.form['price']),
            'category':    request.form['category'],
            'description': request.form['description'],
            'stock':       int(request.form['stock']),
            'image':       request.form.get('image','📦'),
            'image_url':   img_url,
            'rating':      0.0,
            'review_count':0,
            'discount':    int(request.form.get('discount', 0)),
        }
        products_db.append(p)
        add_notification(session['user_id'], 'seller',
            '✅ Product Added!', f"'{p['name']}' is now live in the store.", 'success')
        add_notification(0, 'customer', '🆕 New Product Available!',
            f"{p['name']} — ${p['price']} | {p['category']}", 'info')
        save_products()
        flash(f"Product '{p['name']}' added successfully!", 'success')
        return redirect(url_for('seller_products'))
    return render_template('seller/add_product.html', **ctx())

@app.route('/seller/products/edit/<int:product_id>', methods=['GET','POST'])
@login_required('seller')
def seller_edit_product(product_id):
    product = next((p for p in products_db if p['id'] == product_id
                    and p['seller_id'] == session['user_id']), None)
    if not product:
        flash('Product not found.', 'error')
        return redirect(url_for('seller_products'))
    if request.method == 'POST':
        product['name']        = request.form['name']
        product['price']       = float(request.form['price'])
        product['category']    = request.form['category']
        product['description'] = request.form['description']
        product['stock']       = int(request.form['stock'])
        product['discount']    = int(request.form.get('discount', 0))
        save_products()
        flash('Product updated!', 'success')
        return redirect(url_for('seller_products'))
    return render_template('seller/edit_product.html', product=product, **ctx())

@app.route('/seller/products/stock/<int:product_id>', methods=['POST'])
@login_required('seller')
def seller_update_stock(product_id):
    product = next((p for p in products_db if p['id'] == product_id), None)
    if product:
        new_stock = int(request.form.get('stock', 0))
        old_stock = product['stock']
        product['stock'] = new_stock
        add_notification(session['user_id'], 'seller',
            '📦 Stock Updated',
            f"'{product['name']}' stock: {old_stock} → {new_stock}", 'info')
        save_products()
        flash(f"Stock updated to {new_stock}!", 'success')
    return redirect(url_for('seller_products'))

@app.route('/seller/products/delete/<int:product_id>')
@login_required('seller')
def seller_delete_product(product_id):
    global products_db
    products_db = [p for p in products_db if not
                   (p['id'] == product_id and p['seller_id'] == session['user_id'])]
    save_products()
    flash('Product deleted.', 'success')
    return redirect(url_for('seller_products'))

@app.route('/seller/products/view/<int:product_id>')
@login_required('seller')
def seller_view_product(product_id):
    product = next((p for p in products_db if p['id'] == product_id), None)
    if not product:
        flash('Product not found.', 'error')
        return redirect(url_for('seller_products'))
    from database import product_reviews_db
    reviews     = [r for r in product_reviews_db if r['product_id'] == product_id]
    bert_result = None
    if reviews:
        bert_result = analyze_reviews_bert([r['review'] for r in reviews])
        # Send 12-hour report notification
        last_notif = next((n for n in reversed(notifications_db)
                           if n['user_id'] == session['user_id']
                           and '12-Hour' in n['title']), None)
        should_notify = True
        if last_notif:
            last_time = datetime.datetime.strptime(last_notif['time'], '%Y-%m-%d %H:%M')
            if (datetime.datetime.now() - last_time).seconds < 43200:  # 12 hours
                should_notify = False
        if should_notify:
            add_notification(session['user_id'], 'seller',
                f"📊 12-Hour Review Report — {product['name']}",
                f"Good: {bert_result['summary'].get('Good Review',0)} | "
                f"Bad: {bert_result['summary'].get('Bad Review',0)} | "
                f"Stars: {bert_result['star_rating']}/5", 'info')
    product_orders = [o for o in orders_db if o['product_id'] == product_id]
    return render_template('seller/view_product.html',
                           product=product,
                           reviews=reviews,
                           bert_result=bert_result,
                           product_orders=product_orders,
                           **ctx())

# ── SELLER: AI CHATBOT (Strategy) ─────────────────────────────────────────────

@app.route('/seller/chatbot', methods=['GET','POST'])
@login_required('seller')
def seller_chatbot():
    from database import chat_history_db, product_reviews_db
    uid = session['user_id']
    if uid not in chat_history_db:
        chat_history_db[uid] = []
    history = chat_history_db[uid]

    if request.method == 'POST':
        user_msg = request.form.get('message','').strip()
        if user_msg:
            # Build context from seller's data
            my_products = [p for p in products_db if p['seller_id'] == uid]
            my_orders   = [o for o in orders_db
                           if any(p['id'] == o['product_id'] for p in my_products)]
            revenue     = round(sum(o['price'] for o in my_orders), 2)
            low_stock   = [p for p in my_products if p['stock'] < 10]
            all_reviews = [r['review'] for r in product_reviews_db
                           if any(p['id'] == r['product_id'] for p in my_products)]

            # Build AI response using rule-based strategy
            bot_reply = _chatbot_reply(user_msg, my_products, my_orders,
                                       revenue, low_stock, all_reviews)
            history.append({'role': 'user',  'text': user_msg})
            history.append({'role': 'bot',   'text': bot_reply})
            chat_history_db[uid] = history[-20:]  # keep last 20 messages

    my_products = [p for p in products_db if p['seller_id'] == uid]
    return render_template('seller/chatbot.html',
                           history=history,
                           products=my_products,
                           **ctx())

def _chatbot_reply(msg, products, orders, revenue, low_stock, reviews):
    """Rule-based AI chatbot with strategy intelligence."""
    msg_lower = msg.lower()
    total_products = len(products)
    total_orders   = len(orders)

    # Analyze reviews with BERT if available
    bert_summary = None
    if reviews:
        try:
            bert_summary = analyze_reviews_bert(reviews[:10])
        except:
            pass

    # Strategy questions
    if any(w in msg_lower for w in ['strategy','plan','improve','grow','increase','sales']):
        tips = []
        if low_stock:
            tips.append(f"⚠️ Restock {len(low_stock)} low-stock products immediately.")
        if bert_summary and bert_summary['score'] < 0:
            tips.append("❌ Customer reviews are mostly negative — fix product quality first.")
        elif bert_summary and bert_summary['score'] > 0.3:
            tips.append("✅ Reviews are positive — great time to increase prices by 5-10%.")
        tips.append("📢 Run a discount campaign on slow-moving products.")
        tips.append("🎯 Focus marketing on your top-rated products.")
        tips.append("📊 Analyze competitor prices weekly and adjust accordingly.")
        return "🤖 AI Strategy Plan:\n\n" + "\n".join(tips)

    elif any(w in msg_lower for w in ['review','rating','customer','feedback']):
        if bert_summary:
            return (f"🧠 BERT Review Analysis:\n"
                    f"✅ Good Reviews: {bert_summary['summary'].get('Good Review',0)}\n"
                    f"❌ Bad Reviews: {bert_summary['summary'].get('Bad Review',0)}\n"
                    f"⭐ Star Rating: {bert_summary['star_rating']}/5\n"
                    f"📌 {bert_summary['verdict']}")
        return "No reviews available yet. Ask customers to leave reviews!"

    elif any(w in msg_lower for w in ['stock','inventory','restock']):
        if low_stock:
            names = ', '.join(p['name'] for p in low_stock)
            return f"⚠️ Low Stock Alert!\nProducts needing restock: {names}\n💡 Restock immediately to avoid lost sales."
        return "✅ All products have sufficient stock levels."

    elif any(w in msg_lower for w in ['revenue','sales','money','earning','profit']):
        return (f"💰 Revenue Summary:\n"
                f"Total Orders: {total_orders}\n"
                f"Total Revenue: ${revenue}\n"
                f"Products Listed: {total_products}\n"
                f"Avg Order Value: ${round(revenue/max(total_orders,1),2)}")

    elif any(w in msg_lower for w in ['competitor','competition','market','price']):
        return ("📊 Competitor Analysis Tips:\n"
                "1. Check competitor prices weekly\n"
                "2. If competitor drops price >10%, match or offer bundle deals\n"
                "3. Monitor their reviews for weaknesses you can exploit\n"
                "4. Use the Market Analysis page for detailed competitor tracking")

    elif any(w in msg_lower for w in ['product','add','list','catalog']):
        names = ', '.join(p['name'] for p in products[:5])
        return (f"📦 Your Products ({total_products} total):\n{names}...\n"
                f"💡 Go to Products page to add more or update stock.")

    elif any(w in msg_lower for w in ['hello','hi','hey','help']):
        return ("👋 Hello! I'm your AI Business Assistant.\n\n"
                "I can help you with:\n"
                "📊 Sales strategy & growth plans\n"
                "⭐ Customer review analysis\n"
                "📦 Stock & inventory management\n"
                "💰 Revenue & profit insights\n"
                "🏆 Competitor analysis\n\n"
                "Just ask me anything about your business!")

    else:
        return (f"🤖 I analyzed your business data:\n"
                f"• {total_products} products listed\n"
                f"• {total_orders} total orders\n"
                f"• ${revenue} total revenue\n"
                f"• {len(low_stock)} products need restocking\n\n"
                f"Ask me about: strategy, reviews, stock, revenue, or competitors!")

# ── SELLER: COMPETITOR ANALYSIS ───────────────────────────────────────────────

@app.route('/seller/competitor', methods=['GET','POST'])
@login_required('seller')
def seller_competitor():
    results = None
    if request.method == 'POST':
        your_price      = float(request.form.get('your_price', 100))
        your_product    = request.form.get('your_product', 'My Product')
        comp_names      = request.form.getlist('comp_name')
        comp_prices_raw = request.form.getlist('comp_prices')
        reviews_raw     = request.form.get('reviews', '')
        reviews         = [r.strip() for r in reviews_raw.split('\n') if r.strip()]

        competitor_data = []
        for name, ps in zip(comp_names, comp_prices_raw):
            try:
                prices = [float(x.strip()) for x in ps.split(',') if x.strip()]
                if prices:
                    competitor_data.append({'name': name, 'prices': prices})
            except ValueError:
                continue

        if not competitor_data:
            competitor_data = [
                {'name': 'Competitor A', 'prices': [95, 92, 88, 85, 83]},
                {'name': 'Competitor B', 'prices': [110, 112, 115, 118, 120]},
                {'name': 'Competitor C', 'prices': [78, 76, 74, 72, 70]},
            ]

        trends   = analyze_price_trend(competitor_data)
        sentiment_result = analyze_sentiment(reviews) if reviews else {'score': 0, 'summary': {}, 'results': []}
        strategy = generate_strategy(sentiment_result['score'], trends, your_price)

        # Auto notify on critical findings
        for s in strategy:
            if s['priority'] in ('CRITICAL','HIGH'):
                add_notification(session['user_id'], 'seller',
                    '🚨 Competitor Alert!', s['suggestion'], 'warning')

        results = {
            'your_product':  your_product,
            'your_price':    your_price,
            'trends':        trends,
            'sentiment':     sentiment_result,
            'strategy':      strategy,
        }
    return render_template('seller/competitor.html', results=results, **ctx())

# ── BERT REVIEW ANALYSIS ──────────────────────────────────────────────────

@app.route('/seller/reviews', methods=['GET', 'POST'])
@login_required('seller')
def seller_reviews():
    result = None
    product_id = request.args.get('product_id', type=int)

    # Load reviews for a specific product from DB
    if product_id:
        from database import product_reviews_db
        db_reviews = [r['review'] for r in product_reviews_db
                      if r['product_id'] == product_id]
        if db_reviews:
            result = analyze_reviews_bert(db_reviews)
            result['source'] = 'product_db'
            result['product_id'] = product_id

    if request.method == 'POST':
        raw     = request.form.get('reviews', '')
        reviews = [r.strip() for r in raw.split('\n') if r.strip()]
        if reviews:
            result = analyze_reviews_bert(reviews)
            result['source'] = 'manual'
            # Notify seller with summary every 12 hours (simplified: on each analysis)
            add_notification(
                session['user_id'], 'seller',
                '📊 12-Hour Review Report',
                f"BERT Analysis: {result['summary'].get('Good Review',0)} Good, "
                f"{result['summary'].get('Bad Review',0)} Bad reviews. "
                f"Star Rating: {result['star_rating']}/5",
                'info'
            )

    from database import products_db as pdb, product_reviews_db
    my_products = [p for p in pdb if p['seller_id'] == session['user_id']]
    return render_template('seller/reviews.html',
                           result=result,
                           my_products=my_products,
                           product_reviews=product_reviews_db,
                           **ctx())

# ── AMAZON-LIKE PRODUCT STORE ──────────────────────────────────────────────────

@app.route('/store')
@login_required()
def store():
    query      = request.args.get('q', '')
    category   = request.args.get('cat', '')
    sort_by    = request.args.get('sort', 'relevance')
    page       = request.args.get('page', 1, type=int)
    min_price  = request.args.get('min_price', 0, type=float)
    max_price  = request.args.get('max_price', 99999, type=float)

    result     = search_products(query, category, min_price, max_price, sort_by, page, per_page=20)
    categories = get_categories()

    return render_template('store/index.html',
                           result=result,
                           categories=categories,
                           **ctx())

@app.route('/store/product/<int:product_id>')
@login_required()
def store_product(product_id):
    product = get_product_by_id(product_id)
    if not product:
        flash('Product not found.', 'error')
        return redirect(url_for('store'))
    # Get related products (same category)
    all_p   = fetch_all_products()
    related = [p for p in all_p if p['category'] == product['category']
               and p['id'] != product_id][:6]
    return render_template('store/product.html',
                           product=product, related=related, **ctx())

@app.route('/store/buy/<int:product_id>')
@login_required()
def store_buy(product_id):
    product = get_product_by_id(product_id)
    if not product:
        flash('Product not found.', 'error')
        return redirect(url_for('store'))
    order = {
        'id':         len(orders_db) + 1,
        'user_id':    session['user_id'],
        'product_id': product_id,
        'name':       product['name'],
        'price':      product['price'],
        'status':     'Confirmed',
        'date':       datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
    }
    orders_db.append(order)
    add_notification(product['seller_id'], 'seller',
        '🛒 New Store Order!',
        f"{session['name']} bought '{product['name']}' for ${product['price']}", 'success')
    flash(f"✅ Order placed for {product['name']}!", 'success')
    return redirect(url_for('store_product', product_id=product_id))

@app.route('/store/review/<int:product_id>', methods=['POST'])
@login_required()
def store_review(product_id):
    from database import product_reviews_db
    review_text = request.form.get('review', '').strip()
    rating      = int(request.form.get('rating', 5))
    if review_text:
        product_reviews_db.append({
            'id':         len(product_reviews_db) + 1,
            'product_id': product_id,
            'user_id':    session['user_id'],
            'user_name':  session['name'],
            'rating':     rating,
            'review':     review_text,
            'date':       datetime.datetime.now().strftime('%Y-%m-%d'),
        })
        # Notify seller
        add_notification(2, 'seller', '⭐ New Product Review!',
            f"{session['name']} left a {rating}-star review.", 'info')
        flash('Review submitted!', 'success')
    return redirect(url_for('store_product', product_id=product_id))

# ── LIVE DATA ROUTES ──────────────────────────────────────────────────────────

@app.route('/live/stocks')
@login_required()
def live_stocks():
    tickers = ['AAPL', 'GOOGL', 'AMZN', 'MSFT', 'TSLA', 'META']
    stocks  = fetch_all_stocks(tickers)
    crypto  = fetch_crypto_prices()
    news    = fetch_tech_news(6)
    return render_template('live/stocks.html',
                           stocks=stocks, crypto=crypto, news=news, **ctx())

@app.route('/live/jobs')
@login_required()
def live_jobs():
    keyword = request.args.get('q', 'python')
    jobs    = fetch_remote_jobs(keyword, limit=12)
    return render_template('live/jobs.html', jobs=jobs, keyword=keyword, **ctx())

@app.route('/live/products')
@login_required()
def live_products():
    category = request.args.get('cat', 'mystery')
    products = fetch_product_reviews(category, limit=8)
    reviews  = fetch_sample_reviews(category)
    sentiment_result = analyze_sentiment(reviews)
    return render_template('live/products.html',
                           products=products, category=category,
                           sentiment=sentiment_result, **ctx())

@app.route('/api/stocks')
@login_required()
def api_stocks():
    tickers = request.args.get('t', 'AAPL,GOOGL,TSLA').split(',')
    data    = fetch_all_stocks(tickers)
    return jsonify(data)

@app.route('/api/crypto')
@login_required()
def api_crypto():
    return jsonify(fetch_crypto_prices())

# ── NOTIFICATIONS: mark single read ───────────────────────────────────────────────

@app.route('/notifications/read/<int:notif_id>')
@login_required()
def mark_one_read(notif_id):
    for n in notifications_db:
        if n['id'] == notif_id:
            n['read'] = True
    return redirect(request.referrer or url_for('notifications'))

@app.route('/notifications/read_all')
@login_required()
def mark_all_read_route():
    mark_all_read(session['user_id'], session['role'])
    flash('All notifications marked as read.', 'success')
    return redirect(url_for('notifications'))

# ── ADDRESS MANAGEMENT ───────────────────────────────────────────────────────────────

@app.route('/customer/addresses', methods=['GET','POST'])
@login_required('customer')
def customer_addresses():
    uid = session['user_id']
    my_addresses = [a for a in addresses_db if a['user_id'] == uid]
    if request.method == 'POST':
        addr = {
            'id':         len(addresses_db) + 1,
            'user_id':    uid,
            'full_name':  request.form['full_name'],
            'phone':      request.form['phone'],
            'address':    request.form['address'],
            'city':       request.form['city'],
            'state':      request.form['state'],
            'pincode':    request.form['pincode'],
            'landmark':   request.form.get('landmark',''),
            'address_type': request.form.get('address_type','Home'),
            'is_default': len(my_addresses) == 0,
        }
        addresses_db.append(addr)
        save_addresses()
        flash('Address saved!', 'success')
        return redirect(url_for('customer_addresses'))
    return render_template('customer/addresses.html', addresses=my_addresses, **ctx())

@app.route('/customer/addresses/default/<int:addr_id>')
@login_required('customer')
def set_default_address(addr_id):
    uid = session['user_id']
    for a in addresses_db:
        if a['user_id'] == uid:
            a['is_default'] = (a['id'] == addr_id)
    flash('Default address updated!', 'success')
    return redirect(url_for('customer_addresses'))

@app.route('/customer/addresses/delete/<int:addr_id>')
@login_required('customer')
def delete_address(addr_id):
    global addresses_db
    addresses_db = [a for a in addresses_db
                    if not (a['id'] == addr_id and a['user_id'] == session['user_id'])]
    flash('Address deleted.', 'success')
    return redirect(url_for('customer_addresses'))

# ── AMAZON-STYLE CHECKOUT ───────────────────────────────────────────────────────────────


@app.route('/checkout/<int:product_id>', methods=['GET','POST'])
@login_required('customer')
def checkout(product_id):
    import json as _json
    uid     = session['user_id']
    product = next((p for p in products_db if p['id'] == product_id), None)
    if not product:
        flash('Product not found.', 'error')
        return redirect(url_for('shop'))

    my_addresses = [a for a in addresses_db if a['user_id'] == uid]
    seller       = next((u for u in users_db if u['id'] == product['seller_id']), None)
    seller_name  = seller.get('shop_name', seller['name']) if seller else 'Unknown'
    final_price  = round(product['price'] * (1 - product.get('discount',0)/100), 2)

    if request.method == 'GET':
        return render_template('customer/checkout.html',
                               product=product, addresses=my_addresses,
                               seller_name=seller_name, final_price=final_price,
                               step=1, address=None, addr_json='', **ctx())

    step = request.form.get('step', '1')

    if step == '2':
        addr_id = request.form.get('addr_id')
        if addr_id and addr_id != 'new':
            address = next((a for a in addresses_db if a['id'] == int(addr_id)), None)
        else:
            address = {
                'id':           len(addresses_db) + 1,
                'user_id':      uid,
                'full_name':    request.form.get('full_name',''),
                'phone':        request.form.get('phone',''),
                'address':      request.form.get('address',''),
                'city':         request.form.get('city',''),
                'state':        request.form.get('state',''),
                'pincode':      request.form.get('pincode',''),
                'landmark':     request.form.get('landmark',''),
                'address_type': request.form.get('address_type','Home'),
                'is_default':   len(my_addresses) == 0,
            }
            if request.form.get('save_address'):
                addresses_db.append(address)
                save_addresses()
        addr_json = _json.dumps(address)
        return render_template('customer/checkout.html',
                               product=product, addresses=my_addresses,
                               seller_name=seller_name, final_price=final_price,
                               step=2, address=address,
                               addr_json=addr_json, **ctx())

    elif step == '3':
        addr_json = request.form.get('addr_data', '{}')
        address   = _json.loads(addr_json)
        return render_template('customer/checkout.html',
                               product=product, addresses=my_addresses,
                               seller_name=seller_name, final_price=final_price,
                               step=3, address=address,
                               addr_json=addr_json, **ctx())

    elif step == 'confirm':
        addr_json = request.form.get('addr_data', '{}')
        address   = _json.loads(addr_json)
        payment   = request.form.get('payment', 'COD')
        order = {
            'id':         len(orders_db) + 1,
            'user_id':    uid,
            'seller_id':  product['seller_id'],
            'product_id': product_id,
            'name':       product['name'],
            'price':      final_price,
            'status':     'Confirmed',
            'payment':    payment,
            'date':       datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
            'address':    address,
        }
        orders_db.append(order)
        if product['stock'] > 0:
            product['stock'] -= 1
        save_orders()
        save_products()
        notify_only_buyer(order['id'], '\u2705 Order Confirmed!',
            f"Your order for \'{product['name']}\' is confirmed! "
            f"Delivering to {address.get('city','')}, {address.get('state','')}. "
            f"Payment: {payment}", 'success')
        add_notification(product['seller_id'], 'seller',
            '\ud83d\uded2 New Order Received!',
            f"{session['name']} ordered \'{product['name']}\' \u2014 "
            f"${final_price} | {address.get('city','')}, {address.get('state','')}",
            'success')
        flash('\u2705 Order placed successfully!', 'success')
        return redirect(url_for('order_success', order_id=order['id']))

    return redirect(url_for('shop'))


@app.route('/order/success/<int:order_id>')
@login_required('customer')
def order_success(order_id):
    order = next((o for o in orders_db if o['id'] == order_id
                  and o['user_id'] == session['user_id']), None)
    if not order:
        return redirect(url_for('customer_products'))
    return render_template('customer/order_success.html', order=order, **ctx())

@app.route('/customer/orders')
@login_required('customer')
def customer_orders():
    uid    = session['user_id']
    orders = [o for o in orders_db if o['user_id'] == uid]
    return render_template('customer/orders.html',
                           orders=list(reversed(orders)), **ctx())

# ── SELLER: PRODUCT LAUNCH NOTIFICATION ───────────────────────────────────────────

@app.route('/seller/launch/<int:product_id>')
@login_required('seller')
def seller_launch_product(product_id):
    product = next((p for p in products_db if p['id'] == product_id), None)
    if not product:
        flash('Product not found.', 'error')
        return redirect(url_for('seller_products'))
    # Notify ONLY followers of this seller
    notify_product_followers(
        session['user_id'],
        product['name'],
        f"🆕 {product['name']} is now available! "
        f"Price: ${product['price']} | Category: {product['category']}"
    )
    # Also notify all customers if no followers yet
    follower_ids = [f['user_id'] for f in follows_db if f['seller_id'] == session['user_id']]
    if not follower_ids:
        add_notification(0, 'customer',
            f'🆕 New Launch: {product["name"]}',
            f"${product['price']} | {product['category']} — Check it out!", 'info')
    flash(f"Launch notification sent for '{product['name']}'!", 'success')
    return redirect(url_for('seller_view_product', product_id=product_id))

# ── FOLLOW / UNFOLLOW SELLER ───────────────────────────────────────────────────────────────

@app.route('/follow/<int:seller_id>')
@login_required('customer')
def follow_seller(seller_id):
    uid = session['user_id']
    already = any(f['user_id'] == uid and f['seller_id'] == seller_id for f in follows_db)
    if not already:
        seller = next((u for u in users_db if u['id'] == seller_id), None)
        follows_db.append({'user_id': uid, 'seller_id': seller_id,
                           'company': seller['name'] if seller else 'Unknown'})
        add_notification(seller_id, 'seller', '👥 New Follower!',
            f"{session['name']} is now following your store!", 'info')
        save_follows()
        flash('You are now following this seller!', 'success')
    return redirect(request.referrer or url_for('customer_products'))

@app.route('/unfollow/<int:seller_id>')
@login_required('customer')
def unfollow_seller(seller_id):
    global follows_db
    follows_db = [f for f in follows_db
                  if not (f['user_id'] == session['user_id'] and f['seller_id'] == seller_id)]
    flash('Unfollowed.', 'success')
    return redirect(request.referrer or url_for('customer_products'))

# ── SELLER: UPDATE ORDER STATUS ────────────────────────────────────────────────────────────

@app.route('/seller/order/update/<int:order_id>', methods=['POST'])
@login_required('seller')
def seller_update_order(order_id):
    order = next((o for o in orders_db if o['id'] == order_id), None)
    if order:
        new_status = request.form.get('status')
        old_status = order['status']
        order['status'] = new_status
        # Notify ONLY the buyer of this order
        notify_only_buyer(order_id,
            f'📦 Order #{order_id} Status Updated',
            f"Your order '{order['name']}' status: {old_status} → {new_status}",
            'success' if new_status == 'Delivered' else 'info')
        flash(f'Order status updated to {new_status}!', 'success')
    return redirect(url_for('seller_products'))

# ── PROFILE UPDATE + 100 PRODUCTS ──────────────────────────────────────────────────

@app.route('/profile', methods=['GET','POST'])
@login_required()
def profile():
    uid  = session['user_id']
    user = next((u for u in users_db if u['id'] == uid), None)
    if request.method == 'POST':
        # Update basic info
        user['name']  = request.form.get('name', user['name']).strip()
        user['email'] = request.form.get('email', user['email']).strip()
        # Update password
        new_pass = request.form.get('new_password','').strip()
        old_pass = request.form.get('old_password','').strip()
        if new_pass and old_pass:
            if old_pass == user['password']:
                user['password'] = new_pass
                flash('✅ Password updated!', 'success')
            else:
                flash('❌ Old password incorrect.', 'error')
                return redirect(url_for('profile'))
        # Update seller shop info
        if session['role'] == 'seller':
            user['shop_name'] = request.form.get('shop_name', user.get('shop_name','')).strip()
            user['shop_desc'] = request.form.get('shop_desc', user.get('shop_desc','')).strip()
            user['avatar']    = request.form.get('avatar', user.get('avatar','🏪')).strip()
        # Update profile picture
        img_file = request.files.get('profile_pic')
        if img_file and img_file.filename:
            img_url = save_image(img_file)
            if img_url:
                user['profile_pic'] = img_url
        session['name'] = user['name']
        save_users()
        flash('✅ Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
    return render_template('profile.html', user=user,
                           products_db=products_db,
                           orders_db=orders_db,
                           resumes_db=resumes_db,
                           **ctx())

@app.route('/seller/load-products', methods=['GET','POST'])
@login_required('seller')
def seller_load_products():
    """Load 100 products with images for this seller."""
    uid = session['user_id']
    if request.method == 'POST':
        source = request.form.get('source', 'generated')
        count  = int(request.form.get('count', 100))
        # Remove existing products for this seller
        existing = [p for p in products_db if p['seller_id'] != uid]
        new_products = generate_seller_products(uid, count)
        # Assign proper IDs
        max_id = max((p['id'] for p in existing), default=0)
        for i, p in enumerate(new_products):
            p['id']        = max_id + i + 1
            p['seller_id'] = uid
            p['rating']    = p.get('rating', 4.0)
            p['review_count'] = p.get('review_count', 0)
        products_db.clear()
        products_db.extend(existing + new_products)
        save_products()
        # Notify customers
        add_notification(0, 'customer',
            f'🆕 {count} New Products Added!',
            f"{session['name']} just added {count} new products. Check them out!",
            'info')
        flash(f'✅ {count} products loaded successfully with images!', 'success')
        return redirect(url_for('seller_products'))
    # Count current products
    my_count = len([p for p in products_db if p['seller_id'] == uid])
    return render_template('seller/load_products.html',
                           my_count=my_count, **ctx())

# ── PHASE 2: FAKE REVIEW DETECTION ──────────────────────────────────────────────────

@app.route('/seller/fake-reviews', methods=['GET','POST'])
@login_required('seller')
def seller_fake_reviews():
    result     = None
    product_id = request.args.get('product_id', type=int)

    # Auto-analyze product reviews from DB
    if product_id:
        reviews = [r for r in product_reviews_db if r['product_id'] == product_id]
        if reviews:
            texts   = [r['review'] for r in reviews]
            ratings = [r['rating'] for r in reviews]
            result  = analyze_fake_reviews(texts, ratings)
            result['source']     = 'product_db'
            result['product_id'] = product_id

    if request.method == 'POST':
        raw     = request.form.get('reviews', '')
        ratings_raw = request.form.get('ratings', '')
        reviews = [r.strip() for r in raw.split('\n') if r.strip()]
        try:
            ratings = [int(x.strip()) for x in ratings_raw.split(',') if x.strip()]
        except:
            ratings = [5] * len(reviews)
        # Pad ratings if needed
        while len(ratings) < len(reviews):
            ratings.append(5)
        if reviews:
            result = analyze_fake_reviews(reviews, ratings)
            result['source'] = 'manual'
            # Notify seller
            fake_count = result['summary'].get('Fake', 0)
            if fake_count > 0:
                add_notification(session['user_id'], 'seller',
                    f'🚨 {fake_count} Fake Review(s) Detected!',
                    f"{result['verdict']} — {fake_count} fake, "
                    f"{result['summary'].get('Genuine',0)} genuine out of "
                    f"{result['summary']['Total']} reviews.", 'warning')

    my_products = [p for p in products_db if p['seller_id'] == session['user_id']]
    return render_template('seller/fake_reviews.html',
                           result=result,
                           my_products=my_products,
                           product_reviews=product_reviews_db,
                           **ctx())

# ── PHASE 1: AUTO-UPDATE RATING AFTER REVIEW ──────────────────────────────────────────────────
def update_product_rating(product_id):
    """Recalculate product rating from all reviews."""
    reviews = [r for r in product_reviews_db if r['product_id'] == product_id]
    product = next((p for p in products_db if p['id'] == product_id), None)
    if product and reviews:
        avg = round(sum(r['rating'] for r in reviews) / len(reviews), 1)
        product['rating']       = avg
        product['review_count'] = len(reviews)
        save_products()

# ── SHOP ROUTES ───────────────────────────────────────────────────────────────

@app.route('/shop')
def shop():
    q         = request.args.get('q', '').lower()
    cat       = request.args.get('cat', '')
    sort      = request.args.get('sort', 'popular')
    min_p     = request.args.get('min_price', 0, type=float)
    max_p     = request.args.get('max_price', 99999, type=float)
    seller_id = request.args.get('seller', 0, type=int)

    prods = list(products_db)
    if q:         prods = [p for p in prods if q in p['name'].lower() or q in p.get('description','').lower() or q in p.get('category','').lower()]
    if cat:       prods = [p for p in prods if p.get('category','') == cat]
    if seller_id: prods = [p for p in prods if p['seller_id'] == seller_id]
    prods = [p for p in prods if min_p <= p['price'] <= max_p]

    if sort == 'price_low':  prods.sort(key=lambda x: x['price'])
    elif sort == 'price_high': prods.sort(key=lambda x: x['price'], reverse=True)
    elif sort == 'rating':   prods.sort(key=lambda x: x.get('rating', 0), reverse=True)
    elif sort == 'newest':   prods.sort(key=lambda x: x['id'], reverse=True)
    elif sort == 'discount': prods.sort(key=lambda x: x.get('discount', 0), reverse=True)

    all_cats    = sorted(set(p.get('category','') for p in products_db if p.get('category')))
    all_sellers = [u for u in users_db if u['role'] == 'seller']
    from database import wishlist_db
    uid      = session.get('user_id')
    wishlist = [w['product_id'] for w in wishlist_db if w['user_id'] == uid] if uid else []

    return render_template('shop/index.html',
                           products=prods, all_cats=all_cats,
                           all_sellers=all_sellers, wishlist=wishlist,
                           q=q, cat=cat, sort=sort,
                           min_p=min_p, max_p=max_p,
                           seller_id=seller_id,
                           total=len(prods),
                           products_db=products_db, **ctx())

@app.route('/shop/product/<int:product_id>')
def shop_product(product_id):
    product = next((p for p in products_db if p['id'] == product_id), None)
    if not product:
        flash('Product not found.', 'error')
        return redirect(url_for('shop'))
    seller   = next((u for u in users_db if u['id'] == product['seller_id']), None)
    reviews  = [r for r in product_reviews_db if r['product_id'] == product_id]
    related  = [p for p in products_db if p.get('category') == product.get('category') and p['id'] != product_id][:6]
    avg_rating = round(sum(r['rating'] for r in reviews) / len(reviews), 1) if reviews else 0
    from database import wishlist_db
    uid        = session.get('user_id')
    wishlist   = [w['product_id'] for w in wishlist_db if w['user_id'] == uid] if uid else []
    following  = any(f['user_id'] == uid and f['seller_id'] == product['seller_id'] for f in follows_db) if uid else False
    return render_template('shop/product.html',
                           product=product, seller=seller,
                           reviews=reviews, related=related,
                           avg_rating=avg_rating, wishlist=wishlist,
                           following=following, **ctx())

@app.route('/shop/review/<int:product_id>', methods=['POST'])
@login_required('customer')
def shop_review(product_id):
    text   = request.form.get('review', '').strip()
    rating = int(request.form.get('rating', 5))
    if text:
        product_reviews_db.append({
            'id':         len(product_reviews_db) + 1,
            'product_id': product_id,
            'user_id':    session['user_id'],
            'user_name':  session['name'],
            'rating':     rating,
            'review':     text,
            'date':       datetime.datetime.now().strftime('%Y-%m-%d'),
        })
        prod = next((p for p in products_db if p['id'] == product_id), None)
        if prod:
            add_notification(prod['seller_id'], 'seller',
                f'⭐ New {rating}-Star Review!',
                f"{session['name']}: \"{text[:60]}...\"", 'info')
        save_reviews()
        update_product_rating(product_id)
        # Auto fake check
        fake_result = detect_fake_review(text, rating)
        if fake_result['label'] == 'Fake Review':
            add_notification(2, 'seller', '🚨 Possible Fake Review Detected!',
                f"Review by {session['name']} flagged as fake (score: {fake_result['fake_score']}%). "
                f"Reason: {fake_result['reasons'][0]}", 'warning')
        flash('Review submitted!', 'success')
    return redirect(url_for('shop_product', product_id=product_id))

@app.route('/shop/wishlist/toggle/<int:product_id>')
def wishlist_toggle(product_id):
    uid = session.get('user_id')
    if not uid:
        flash('Please login to add to wishlist.', 'error')
        return redirect(url_for('login'))
    # Use persistent DB wishlist
    from database import wishlist_db, save_wishlist
    entry = next((w for w in wishlist_db if w['user_id']==uid and w['product_id']==product_id), None)
    if entry:
        wishlist_db.remove(entry)
        save_wishlist()
        flash('Removed from wishlist.', 'success')
    else:
        wishlist_db.append({'user_id': uid, 'product_id': product_id})
        save_wishlist()
        flash('Added to wishlist! ❤️', 'success')
    return redirect(request.referrer or url_for('shop'))

@app.route('/shop/wishlist')
def wishlist_page():
    uid = session.get('user_id')
    from database import wishlist_db
    wl_ids   = [w['product_id'] for w in wishlist_db if w['user_id'] == uid] if uid else []
    products = [p for p in products_db if p['id'] in wl_ids]
    return render_template('shop/wishlist.html', products=products, wl_ids=wl_ids,
                           users_db=users_db, products_db=products_db, **ctx())

@app.route('/shop/seller/<int:seller_id>')
def shop_seller(seller_id):
    seller   = next((u for u in users_db if u['id'] == seller_id), None)
    if not seller:
        flash('Seller not found.', 'error')
        return redirect(url_for('shop'))
    prods    = [p for p in products_db if p['seller_id'] == seller_id]
    reviews  = [r for r in product_reviews_db if any(p['id'] == r['product_id'] for p in prods)]
    uid      = session.get('user_id')
    following= any(f['user_id'] == uid and f['seller_id'] == seller_id for f in follows_db) if uid else False
    followers= len([f for f in follows_db if f['seller_id'] == seller_id])
    return render_template('shop/seller.html',
                           seller=seller, products=prods,
                           reviews=reviews, following=following,
                           followers=followers, **ctx())

@app.route('/shop/cart/add/<int:product_id>')
@login_required('customer')
def cart_add(product_id):
    cart = session.get('cart', {})
    key  = str(product_id)
    cart[key] = cart.get(key, 0) + 1
    session['cart'] = cart
    flash('Added to cart! 🛒', 'success')
    return redirect(request.referrer or url_for('shop'))

@app.route('/shop/cart')
@login_required('customer')
def cart_page():
    cart  = session.get('cart', {})
    items = []
    total = 0
    for pid, qty in cart.items():
        p = next((x for x in products_db if x['id'] == int(pid)), None)
        if p:
            items.append({'product': p, 'qty': qty, 'subtotal': round(p['price'] * qty, 2)})
            total += p['price'] * qty
    return render_template('shop/cart.html', items=items, total=round(total, 2), **ctx())

@app.route('/shop/cart/remove/<int:product_id>')
@login_required('customer')
def cart_remove(product_id):
    cart = session.get('cart', {})
    cart.pop(str(product_id), None)
    session['cart'] = cart
    flash('Removed from cart.', 'success')
    return redirect(url_for('cart_page'))

@app.route('/shop/cart/checkout', methods=['GET', 'POST'])
@login_required('customer')
def cart_checkout():
    uid  = session['user_id']
    cart = session.get('cart', {})
    if not cart:
        flash('Your cart is empty.', 'error')
        return redirect(url_for('shop'))
    my_addresses = [a for a in addresses_db if a['user_id'] == uid]
    items = []
    total = 0
    for pid, qty in cart.items():
        p = next((x for x in products_db if x['id'] == int(pid)), None)
        if p:
            items.append({'product': p, 'qty': qty, 'subtotal': round(p['price'] * qty, 2)})
            total += p['price'] * qty

    if request.method == 'POST':
        addr_id = request.form.get('addr_id')
        if addr_id and addr_id != 'new':
            address = next((a for a in addresses_db if a['id'] == int(addr_id)), None)
        else:
            address = {
                'id':           len(addresses_db) + 1,
                'user_id':      uid,
                'full_name':    request.form.get('full_name', ''),
                'phone':        request.form.get('phone', ''),
                'address':      request.form.get('address', ''),
                'city':         request.form.get('city', ''),
                'state':        request.form.get('state', ''),
                'pincode':      request.form.get('pincode', ''),
                'landmark':     request.form.get('landmark', ''),
                'address_type': request.form.get('address_type', 'Home'),
                'is_default':   len(my_addresses) == 0,
            }
            if request.form.get('save_address'):
                addresses_db.append(address)

        payment = request.form.get('payment', 'COD')
        for item in items:
            p   = item['product']
            qty = item['qty']
            order = {
                'id':         len(orders_db) + 1,
                'user_id':    uid,
                'seller_id':  p['seller_id'],
                'product_id': p['id'],
                'name':       p['name'],
                'price':      round(p['price'] * qty, 2),
                'qty':        qty,
                'status':     'Confirmed',
                'payment':    payment,
                'date':       datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
                'address':    address,
            }
            orders_db.append(order)
            if p['stock'] >= qty:
                p['stock'] -= qty
            add_notification(p['seller_id'], 'seller',
                '🛒 New Cart Order!',
                f"{session['name']} ordered {qty}x '{p['name']}' — ${order['price']}", 'success')
            notify_only_buyer(order['id'], '✅ Order Confirmed!',
                f"'{p['name']}' x{qty} ordered. Payment: {payment}", 'success')

        session['cart'] = {}
        flash(f'✅ {len(items)} item(s) ordered successfully!', 'success')
        return redirect(url_for('customer_orders'))

    return render_template('shop/cart_checkout.html',
                           items=items, total=round(total, 2),
                           addresses=my_addresses, **ctx())

# ── PHASE 1: CUSTOMER-SELLER CHAT ──────────────────────────────────────────────────
from database import messages_db, save_messages

@app.route('/chat/<int:seller_id>', methods=['GET','POST'])
@login_required('customer')
def chat_with_seller(seller_id):
    seller = next((u for u in users_db if u['id'] == seller_id), None)
    if not seller:
        flash('Seller not found.', 'error')
        return redirect(url_for('shop'))
    uid  = session['user_id']
    room = f"{min(uid,seller_id)}_{max(uid,seller_id)}"
    msgs = [m for m in messages_db if m['room'] == room]
    if request.method == 'POST':
        text = request.form.get('message','').strip()
        if text:
            messages_db.append({
                'id':        len(messages_db)+1,
                'room':      room,
                'sender_id': uid,
                'sender':    session['name'],
                'text':      text,
                'time':      datetime.datetime.now().strftime('%H:%M'),
                'date':      datetime.datetime.now().strftime('%Y-%m-%d'),
            })
            save_messages()
            add_notification(seller_id, 'seller', f'💬 Message from {session["name"]}',
                text[:60], 'info')
    msgs = [m for m in messages_db if m['room'] == room]
    return render_template('chat.html', seller=seller, msgs=msgs, room=room, **ctx())

@app.route('/seller/chat/<int:customer_id>', methods=['GET','POST'])
@login_required('seller')
def seller_chat(customer_id):
    customer = next((u for u in users_db if u['id'] == customer_id), None)
    if not customer:
        flash('Customer not found.', 'error')
        return redirect(url_for('seller_products'))
    uid  = session['user_id']
    room = f"{min(uid,customer_id)}_{max(uid,customer_id)}"
    if request.method == 'POST':
        text = request.form.get('message','').strip()
        if text:
            messages_db.append({
                'id':        len(messages_db)+1,
                'room':      room,
                'sender_id': uid,
                'sender':    session['name'],
                'text':      text,
                'time':      datetime.datetime.now().strftime('%H:%M'),
                'date':      datetime.datetime.now().strftime('%Y-%m-%d'),
            })
            save_messages()
            add_notification(customer_id, None, f'💬 Message from {session["name"]}',
                text[:60], 'info')
    msgs = [m for m in messages_db if m['room'] == room]
    return render_template('chat.html', seller=customer, msgs=msgs, room=room, **ctx())

@app.route('/seller/messages')
@login_required('seller')
def seller_messages():
    uid = session['user_id']
    # Get all unique customers who messaged this seller
    rooms    = set()
    contacts = []
    for m in messages_db:
        parts = m['room'].split('_')
        if str(uid) in parts:
            other_id = int(parts[0]) if int(parts[1]) == uid else int(parts[1])
            if other_id not in rooms:
                rooms.add(other_id)
                user = next((u for u in users_db if u['id'] == other_id), None)
                if user:
                    last_msg = next((x for x in reversed(messages_db) if x['room'] == m['room']), None)
                    contacts.append({'user': user, 'last_msg': last_msg})
    return render_template('seller/messages.html', contacts=contacts, **ctx())

# ── PHASE 2: SBERT RESUME MATCHING ──────────────────────────────────────────────────

@app.route('/seller/match/sbert/<int:job_id>')
@login_required('seller')
def seller_match_sbert(job_id):
    job = next((j for j in jobs_db if j['id'] == job_id), None)
    if not job or not resumes_db:
        flash('No resumes yet.', 'error')
        return redirect(url_for('seller_jobs'))
    try:
        from sentence_transformers import SentenceTransformer, util
        model   = SentenceTransformer('all-MiniLM-L6-v2')
        jd_emb  = model.encode(job['description'], convert_to_tensor=True)
        ranked  = []
        for r in resumes_db:
            r_emb = model.encode(r['text'], convert_to_tensor=True)
            score = round(float(util.cos_sim(jd_emb, r_emb)[0][0]) * 100, 1)
            grade = 'Excellent' if score>=70 else 'Good' if score>=50 else 'Partial' if score>=30 else 'Low'
            ranked.append({**r, 'score': score, 'grade': grade,
                           'text_preview': r['text'][:200],
                           'model': 'SBERT'})
        ranked.sort(key=lambda x: x['score'], reverse=True)
        return render_template('seller/match_results.html',
                               job=job, ranked=ranked, model='SBERT (~95% accuracy)', **ctx())
    except Exception as e:
        flash(f'SBERT error: {e}. Using TF-IDF instead.', 'error')
        from ml.resume_matcher import match_resumes
        ranked = match_resumes(job['description'], resumes_db)
        return render_template('seller/match_results.html',
                               job=job, ranked=ranked, model='TF-IDF', **ctx())

# ── PHASE 2: PRODUCT RECOMMENDATIONS ──────────────────────────────────────────────────

def get_recommendations(user_id, n=6):
    """Collaborative filtering: recommend products based on order history."""
    user_orders  = [o['product_id'] for o in orders_db if o['user_id'] == user_id]
    if not user_orders:
        return sorted(products_db, key=lambda x: x.get('rating',0), reverse=True)[:n]
    # Find users with similar orders
    similar_users = []
    for u in users_db:
        if u['id'] == user_id or u['role'] != 'customer':
            continue
        u_orders = [o['product_id'] for o in orders_db if o['user_id'] == u['id']]
        common   = len(set(user_orders) & set(u_orders))
        if common > 0:
            similar_users.append((u['id'], common))
    similar_users.sort(key=lambda x: x[1], reverse=True)
    # Get products ordered by similar users but not by current user
    recommended_ids = []
    for uid, _ in similar_users[:5]:
        for o in orders_db:
            if o['user_id'] == uid and o['product_id'] not in user_orders:
                if o['product_id'] not in recommended_ids:
                    recommended_ids.append(o['product_id'])
    recs = [p for p in products_db if p['id'] in recommended_ids][:n]
    if len(recs) < n:
        top = sorted(products_db, key=lambda x: x.get('rating',0), reverse=True)
        for p in top:
            if p['id'] not in recommended_ids and p['id'] not in user_orders:
                recs.append(p)
            if len(recs) >= n:
                break
    return recs

@app.route('/recommendations')
@login_required('customer')
def recommendations():
    recs = get_recommendations(session['user_id'])
    return render_template('recommendations.html', products=recs, **ctx())

# ── PHASE 6: RAZORPAY PAYMENT ──────────────────────────────────────────────────
# Set your Razorpay keys here (get free test keys from razorpay.com)
RAZORPAY_KEY_ID     = os.environ.get('RAZORPAY_KEY_ID',     'rzp_test_YOUR_KEY')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', 'YOUR_SECRET')

@app.route('/payment/razorpay/<int:order_id>')
@login_required('customer')
def razorpay_payment(order_id):
    order = next((o for o in orders_db if o['id'] == order_id
                  and o['user_id'] == session['user_id']), None)
    if not order:
        flash('Order not found.', 'error')
        return redirect(url_for('customer_orders'))
    amount_paise = int(order['price'] * 100)  # Razorpay uses paise
    return render_template('payment/razorpay.html',
                           order=order,
                           amount=amount_paise,
                           key_id=RAZORPAY_KEY_ID,
                           **ctx())

@app.route('/payment/success', methods=['POST'])
@login_required('customer')
def payment_success():
    order_id   = request.form.get('order_id', type=int)
    payment_id = request.form.get('razorpay_payment_id', 'DEMO')
    order = next((o for o in orders_db if o['id'] == order_id), None)
    if order:
        order['status']     = 'Paid'
        order['payment_id'] = payment_id
        order['payment']    = 'Razorpay'
        save_orders()
        notify_only_buyer(order_id, '✅ Payment Successful!',
            f"Payment of ${order['price']} confirmed. ID: {payment_id}", 'success')
        add_notification(order['seller_id'], 'seller', '💰 Payment Received!',
            f"${order['price']} paid via Razorpay for '{order['name']}'", 'success')
        flash('✅ Payment successful!', 'success')
    return redirect(url_for('customer_orders'))

if __name__ == '__main__':
    os.makedirs('uploads', exist_ok=True)
    app.run(debug=True, port=5001)
