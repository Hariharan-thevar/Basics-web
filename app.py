# =============================================================================
# SY TRADERS - Kids Shoes E-Commerce Management System
# app.py - Main Flask Application
# =============================================================================

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
from datetime import datetime
from functools import wraps

# -----------------------------------------------------------------------------
# App Configuration
# -----------------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'sy-traders-secret-key-2024')

DATABASE = 'sy_traders.db'

# -----------------------------------------------------------------------------
# Database Helpers
# -----------------------------------------------------------------------------

def get_db():
    """Open a database connection."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn


def init_db():
    """Initialize database tables and seed default data."""
    conn = get_db()
    cur = conn.cursor()

    # Users table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            created_at TEXT NOT NULL
        )
    ''')

    # Products (kids shoes) table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            brand TEXT NOT NULL,
            category TEXT NOT NULL,
            size TEXT NOT NULL,
            color TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER NOT NULL DEFAULT 0,
            added_by INTEGER,
            created_at TEXT NOT NULL,
            FOREIGN KEY (added_by) REFERENCES users(id)
        )
    ''')

    # Orders table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            total_price REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            placed_by INTEGER,
            created_at TEXT NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products(id),
            FOREIGN KEY (placed_by) REFERENCES users(id)
        )
    ''')

    conn.commit()

    # Seed default admin account
    existing = cur.execute("SELECT id FROM users WHERE email='admin@example.com'").fetchone()
    if not existing:
        cur.execute('''
            INSERT INTO users (name, email, password, role, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            'Admin',
            'admin@example.com',
            generate_password_hash('admin123'),
            'admin',
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))

    # Seed sample products
    product_count = cur.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    if product_count == 0:
        sample_products = [
            ('Bouncy Runner', 'Nike', 'Sports', '3Y', 'Red', 1499.00, 20),
            ('Cloud Walker', 'Adidas', 'Casual', '4Y', 'Blue', 1299.00, 15),
            ('Tiny Steps', 'Bata', 'School', '2Y', 'Black', 799.00, 30),
            ('Splash Buddy', 'Crocs', 'Sandals', '5Y', 'Yellow', 999.00, 25),
            ('Star Kicks', 'Converse', 'Casual', '6Y', 'White', 1799.00, 10),
            ('Flex Pro', 'Puma', 'Sports', '7Y', 'Green', 1599.00, 18),
        ]
        for p in sample_products:
            cur.execute('''
                INSERT INTO products (name, brand, category, size, color, price, stock, added_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
            ''', (*p, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    # Seed sample orders
    order_count = cur.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    if order_count == 0:
        sample_orders = [
            ('Rahul Sharma', 1, 2, 2998.00, 'Delivered'),
            ('Priya Patel', 3, 3, 2397.00, 'Pending'),
            ('Anita Desai', 5, 1, 1799.00, 'Shipped'),
            ('Suresh Kumar', 2, 2, 2598.00, 'Delivered'),
            ('Meena Iyer', 4, 4, 3996.00, 'Processing'),
        ]
        for o in sample_orders:
            cur.execute('''
                INSERT INTO orders (customer_name, product_id, quantity, total_price, status, placed_by, created_at)
                VALUES (?, ?, ?, ?, ?, 1, ?)
            ''', (*o, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    conn.commit()
    conn.close()


# -----------------------------------------------------------------------------
# Auth Decorators
# -----------------------------------------------------------------------------

def login_required(f):
    """Redirect to login if user is not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Restrict route to admin users only."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated


# -----------------------------------------------------------------------------
# Auth Routes
# -----------------------------------------------------------------------------

@app.route('/')
def index():
    """Redirect root to dashboard or login."""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        # Basic validation
        if not email or not password:
            flash('Email and password are required.', 'danger')
            return render_template('login.html')

        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['name'] = user['name']
            session['email'] = user['email']
            session['role'] = user['role']
            flash(f'Welcome back, {user["name"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handle new user registration."""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

        # Validation
        errors = []
        if not name:
            errors.append('Name is required.')
        if not email or '@' not in email:
            errors.append('A valid email is required.')
        if len(password) < 6:
            errors.append('Password must be at least 6 characters.')
        if password != confirm:
            errors.append('Passwords do not match.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('register.html')

        conn = get_db()
        existing = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
        if existing:
            flash('An account with this email already exists.', 'danger')
            conn.close()
            return render_template('register.html')

        conn.execute('''
            INSERT INTO users (name, email, password, role, created_at)
            VALUES (?, ?, ?, 'user', ?)
        ''', (name, email, generate_password_hash(password), datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        conn.close()
        flash('Account created! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/logout')
def logout():
    """Clear session and log out."""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# -----------------------------------------------------------------------------
# Dashboard (User + Admin)
# -----------------------------------------------------------------------------

@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard with analytics."""
    conn = get_db()

    # Statistics
    total_products = conn.execute('SELECT COUNT(*) FROM products').fetchone()[0]
    total_orders = conn.execute('SELECT COUNT(*) FROM orders').fetchone()[0]
    total_revenue = conn.execute('SELECT COALESCE(SUM(total_price), 0) FROM orders WHERE status="Delivered"').fetchone()[0]
    low_stock = conn.execute('SELECT COUNT(*) FROM products WHERE stock < 10').fetchone()[0]

    # User's own products
    products = conn.execute('''
        SELECT p.*, u.name as added_by_name
        FROM products p LEFT JOIN users u ON p.added_by = u.id
        WHERE p.added_by = ? OR ? = 'admin'
        ORDER BY p.created_at DESC LIMIT 10
    ''', (session['user_id'], session['role'])).fetchall()

    # User's own orders
    orders = conn.execute('''
        SELECT o.*, p.name as product_name
        FROM orders o LEFT JOIN products p ON o.product_id = p.id
        WHERE o.placed_by = ? OR ? = 'admin'
        ORDER BY o.created_at DESC LIMIT 10
    ''', (session['user_id'], session['role'])).fetchall()

    # Chart data: sales by category
    category_data = conn.execute('''
        SELECT p.category, SUM(o.quantity) as total_sold
        FROM orders o JOIN products p ON o.product_id = p.id
        GROUP BY p.category
    ''').fetchall()

    # Chart data: monthly revenue (last 6 months)
    monthly_data = conn.execute('''
        SELECT strftime('%Y-%m', created_at) as month, SUM(total_price) as revenue
        FROM orders WHERE status = 'Delivered'
        GROUP BY month ORDER BY month DESC LIMIT 6
    ''').fetchall()

    # Order status breakdown
    status_data = conn.execute('''
        SELECT status, COUNT(*) as count FROM orders GROUP BY status
    ''').fetchall()

    conn.close()

    return render_template('dashboard.html',
        total_products=total_products,
        total_orders=total_orders,
        total_revenue=total_revenue,
        low_stock=low_stock,
        products=products,
        orders=orders,
        category_data=[[r[0], r[1]] for r in category_data],
        monthly_data=[[r[0], r[1]] for r in reversed(list(monthly_data))],
        status_data=[[r[0], r[1]] for r in status_data]
    )


# -----------------------------------------------------------------------------
# Product CRUD
# -----------------------------------------------------------------------------

@app.route('/product/add', methods=['POST'])
@login_required
def add_product():
    """Add a new product."""
    name = request.form.get('name', '').strip()
    brand = request.form.get('brand', '').strip()
    category = request.form.get('category', '').strip()
    size = request.form.get('size', '').strip()
    color = request.form.get('color', '').strip()
    price = request.form.get('price', 0)
    stock = request.form.get('stock', 0)

    if not all([name, brand, category, size, color]):
        flash('All product fields are required.', 'danger')
        return redirect(url_for('dashboard'))

    try:
        price = float(price)
        stock = int(stock)
    except ValueError:
        flash('Price and stock must be valid numbers.', 'danger')
        return redirect(url_for('dashboard'))

    conn = get_db()
    conn.execute('''
        INSERT INTO products (name, brand, category, size, color, price, stock, added_by, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (name, brand, category, size, color, price, stock, session['user_id'],
          datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()
    flash('Product added successfully!', 'success')
    return redirect(url_for('dashboard'))


@app.route('/product/edit/<int:pid>', methods=['POST'])
@login_required
def edit_product(pid):
    """Edit an existing product."""
    conn = get_db()
    product = conn.execute('SELECT * FROM products WHERE id = ?', (pid,)).fetchone()

    # Only owner or admin can edit
    if not product or (product['added_by'] != session['user_id'] and session['role'] != 'admin'):
        flash('Permission denied.', 'danger')
        conn.close()
        return redirect(url_for('dashboard'))

    name = request.form.get('name', '').strip()
    brand = request.form.get('brand', '').strip()
    category = request.form.get('category', '').strip()
    size = request.form.get('size', '').strip()
    color = request.form.get('color', '').strip()
    price = float(request.form.get('price', 0))
    stock = int(request.form.get('stock', 0))

    conn.execute('''
        UPDATE products SET name=?, brand=?, category=?, size=?, color=?, price=?, stock=?
        WHERE id=?
    ''', (name, brand, category, size, color, price, stock, pid))
    conn.commit()
    conn.close()
    flash('Product updated successfully!', 'success')
    return redirect(url_for('dashboard'))


@app.route('/product/delete/<int:pid>', methods=['POST'])
@login_required
def delete_product(pid):
    """Delete a product."""
    conn = get_db()
    product = conn.execute('SELECT * FROM products WHERE id = ?', (pid,)).fetchone()

    if not product or (product['added_by'] != session['user_id'] and session['role'] != 'admin'):
        flash('Permission denied.', 'danger')
        conn.close()
        return redirect(url_for('dashboard'))

    conn.execute('DELETE FROM products WHERE id = ?', (pid,))
    conn.commit()
    conn.close()
    flash('Product deleted.', 'success')
    return redirect(url_for('dashboard'))


# -----------------------------------------------------------------------------
# Order CRUD
# -----------------------------------------------------------------------------

@app.route('/order/add', methods=['POST'])
@login_required
def add_order():
    """Place a new order."""
    customer_name = request.form.get('customer_name', '').strip()
    product_id = request.form.get('product_id')
    quantity = request.form.get('quantity', 1)

    if not customer_name or not product_id:
        flash('Customer name and product are required.', 'danger')
        return redirect(url_for('dashboard'))

    try:
        quantity = int(quantity)
        product_id = int(product_id)
    except ValueError:
        flash('Invalid quantity or product.', 'danger')
        return redirect(url_for('dashboard'))

    conn = get_db()
    product = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()

    if not product:
        flash('Product not found.', 'danger')
        conn.close()
        return redirect(url_for('dashboard'))

    if product['stock'] < quantity:
        flash(f'Insufficient stock. Only {product["stock"]} available.', 'danger')
        conn.close()
        return redirect(url_for('dashboard'))

    total_price = product['price'] * quantity

    conn.execute('''
        INSERT INTO orders (customer_name, product_id, quantity, total_price, status, placed_by, created_at)
        VALUES (?, ?, ?, ?, 'Pending', ?, ?)
    ''', (customer_name, product_id, quantity, total_price, session['user_id'],
          datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    # Reduce stock
    conn.execute('UPDATE products SET stock = stock - ? WHERE id = ?', (quantity, product_id))
    conn.commit()
    conn.close()
    flash('Order placed successfully!', 'success')
    return redirect(url_for('dashboard'))


@app.route('/order/delete/<int:oid>', methods=['POST'])
@login_required
def delete_order(oid):
    """Delete an order."""
    conn = get_db()
    order = conn.execute('SELECT * FROM orders WHERE id = ?', (oid,)).fetchone()

    if not order or (order['placed_by'] != session['user_id'] and session['role'] != 'admin'):
        flash('Permission denied.', 'danger')
        conn.close()
        return redirect(url_for('dashboard'))

    conn.execute('DELETE FROM orders WHERE id = ?', (oid,))
    conn.commit()
    conn.close()
    flash('Order deleted.', 'success')
    return redirect(url_for('dashboard'))


# -----------------------------------------------------------------------------
# Admin Panel
# -----------------------------------------------------------------------------

@app.route('/admin')
@admin_required
def admin():
    """Admin panel - view all users, products, orders."""
    conn = get_db()
    users = conn.execute('SELECT * FROM users ORDER BY created_at DESC').fetchall()
    all_products = conn.execute('''
        SELECT p.*, u.name as added_by_name
        FROM products p LEFT JOIN users u ON p.added_by = u.id
        ORDER BY p.created_at DESC
    ''').fetchall()
    all_orders = conn.execute('''
        SELECT o.*, p.name as product_name, u.name as placed_by_name
        FROM orders o
        LEFT JOIN products p ON o.product_id = p.id
        LEFT JOIN users u ON o.placed_by = u.id
        ORDER BY o.created_at DESC
    ''').fetchall()

    # Admin analytics
    total_users = len(users)
    total_products = len(all_products)
    total_orders = len(all_orders)
    total_revenue = conn.execute(
        "SELECT COALESCE(SUM(total_price),0) FROM orders WHERE status='Delivered'"
    ).fetchone()[0]

    # Brand breakdown for chart
    brand_data = conn.execute('''
        SELECT brand, COUNT(*) as count FROM products GROUP BY brand
    ''').fetchall()

    # Top selling products
    top_products = conn.execute('''
        SELECT p.name, SUM(o.quantity) as total_sold
        FROM orders o JOIN products p ON o.product_id = p.id
        GROUP BY p.id ORDER BY total_sold DESC LIMIT 5
    ''').fetchall()

    conn.close()

    return render_template('admin.html',
        users=users,
        all_products=all_products,
        all_orders=all_orders,
        total_users=total_users,
        total_products=total_products,
        total_orders=total_orders,
        total_revenue=total_revenue,
        brand_data=[[r[0], r[1]] for r in brand_data],
        top_products=[[r[0], r[1]] for r in top_products]
    )


@app.route('/admin/user/delete/<int:uid>', methods=['POST'])
@admin_required
def delete_user(uid):
    """Admin: Delete a user (cannot delete self)."""
    if uid == session['user_id']:
        flash('Cannot delete your own account.', 'danger')
        return redirect(url_for('admin'))

    conn = get_db()
    conn.execute('DELETE FROM users WHERE id = ?', (uid,))
    conn.commit()
    conn.close()
    flash('User deleted.', 'success')
    return redirect(url_for('admin'))


@app.route('/admin/order/status/<int:oid>', methods=['POST'])
@admin_required
def update_order_status(oid):
    """Admin: Update order status."""
    status = request.form.get('status')
    valid_statuses = ['Pending', 'Processing', 'Shipped', 'Delivered', 'Cancelled']
    if status not in valid_statuses:
        flash('Invalid status.', 'danger')
        return redirect(url_for('admin'))

    conn = get_db()
    conn.execute('UPDATE orders SET status = ? WHERE id = ?', (status, oid))
    conn.commit()
    conn.close()
    flash('Order status updated.', 'success')
    return redirect(url_for('admin'))


# -----------------------------------------------------------------------------
# API Endpoints (for live chart refresh)
# -----------------------------------------------------------------------------

@app.route('/api/stats')
@login_required
def api_stats():
    """Return key stats as JSON."""
    conn = get_db()
    data = {
        'total_products': conn.execute('SELECT COUNT(*) FROM products').fetchone()[0],
        'total_orders': conn.execute('SELECT COUNT(*) FROM orders').fetchone()[0],
        'total_revenue': conn.execute(
            "SELECT COALESCE(SUM(total_price),0) FROM orders WHERE status='Delivered'"
        ).fetchone()[0],
        'low_stock': conn.execute('SELECT COUNT(*) FROM products WHERE stock < 10').fetchone()[0],
    }
    conn.close()
    return jsonify(data)


# -----------------------------------------------------------------------------
# App Entry Point
# -----------------------------------------------------------------------------

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
else:
    # Called by gunicorn — still initialize DB
    init_db()
