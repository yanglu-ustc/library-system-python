from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
import os
from library_ui import LibrarySQL
from sql import config, opengauss_run
from math import ceil
from datetime import date

# ========== Flask App ==========
app = Flask(__name__)
app.secret_key = '09u9j89h7y78t978hn89u823nucod3josk'  # 实际部署需更换为安全密钥

library = LibrarySQL(config)

# ========== Routes ==========

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with opengauss_run(config) as db:
            db.cur.execute("SELECT 1 FROM users WHERE username = %s AND password = %s;", (username, password))
            if db.cur.fetchone():
                session['user'] = username
                flash(f"Welcome, {username}!", "success")
                return redirect(url_for('books'))
            else:
                flash("Invalid username or password.", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

@app.route('/')
def index():
    if 'user' in session:
        return redirect(url_for('books'))
    return redirect(url_for('login'))

# ========== Book Listing ==========
@app.route('/books')
def books():
    if 'user' not in session:
        return redirect(url_for('login'))
    book_list = library.list_books()
    is_admin = session['user'] in library.list_admin_users
    return render_template('books.html', books=book_list, is_admin=is_admin)

# ========== Book Detail (by book_id) ==========
@app.route('/book/<int:book_id>')
def book_detail(book_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    # Reuse list_book_boxes but filter by book_id
    all_boxes = library.list_book_boxes()
    boxes = [b for b in all_boxes if b['book_id'] == book_id]
    if not boxes:
        abort(404)
    # Get book info from first box
    sample = boxes[0]
    return render_template('book_detail.html', book=sample, boxes=boxes)

@app.route('/search', methods=['GET', 'POST'])
def search():
    if 'user' not in session:
        return redirect(url_for('login'))

    current_user = session['user']
    is_admin = current_user in library.list_admin_users

    filters = {}
    if request.method == 'POST':
        filters['title'] = request.form.get('title') or None
        filters['author'] = request.form.get('author') or None
        
        # Safe parsing
        try:
            filters['book_id'] = int(request.form['book_id']) if request.form.get('book_id') else None
        except (ValueError, TypeError):
            filters['book_id'] = None

        try:
            filters['year_min'] = int(request.form['year_min']) if request.form.get('year_min') else None
        except (ValueError, TypeError):
            filters['year_min'] = None

        try:
            filters['year_max'] = int(request.form['year_max']) if request.form.get('year_max') else None
        except (ValueError, TypeError):
            filters['year_max'] = None

        try:
            filters['price_min'] = float(request.form['price_min']) if request.form.get('price_min') else None
        except (ValueError, TypeError):
            filters['price_min'] = None

        try:
            filters['price_max'] = float(request.form['price_max']) if request.form.get('price_max') else None
        except (ValueError, TypeError):
            filters['price_max'] = None

        try:
            filters['location'] = int(request.form['location']) if request.form.get('location') else None
        except (ValueError, TypeError):
            filters['location'] = None

        borrow_str = request.form.get('borrow')
        if borrow_str == 'available':
            filters['borrow'] = False
        elif borrow_str == 'borrowed':
            filters['borrow'] = True
        else:
            filters['borrow'] = None

        # 👇 仅管理员可设置 borrower
        if is_admin:
            filters['borrower'] = request.form.get('borrower') or None
        else:
            filters['borrower'] = None  # 忽略普通用户的输入

        fine_str = request.form.get('fine')
        if fine_str == 'yes':
            filters['fine'] = True
        elif fine_str == 'no':
            filters['fine'] = False
        else:
            filters['fine'] = None

        # ====== 新增：排序参数 ======
        filters['sort_by_1'] = request.form.get('sort_by_1') or None
        filters['sort_order_1'] = request.form.get('sort_order_1') or 'asc'
        filters['sort_by_2'] = request.form.get('sort_by_2') or None
        filters['sort_order_2'] = request.form.get('sort_order_2') or 'asc'
        filters['sort_by_3'] = request.form.get('sort_by_3') or None
        filters['sort_order_3'] = request.form.get('sort_order_3') or 'asc'

        # 安全：只允许对已知字段排序（防止 SQL 注入）
        allowed_sort_fields = {
            'title', 'author', 'year', 'price', 'buy_date', 'section', 'status'
        }
        # 注意：SQL 中的列别名需映射到实际字段
        sort_field_map = {
            'title': 'b.title',
            'author': 'b.author',
            'year': 'b.year',
            'price': 'b.price',
            'buy_date': 'bb.buy_date',
            'section': 'ls.section_name',
            'status': 'bb.be_borrowed'  # 注意：布尔值排序，False (Available) 在前
        }

        # 清洗排序字段
        for i in [1, 2, 3]:
            key = f'sort_by_{i}'
            if filters[key] in sort_field_map:
                filters[key] = sort_field_map[filters[key]]
            else:
                filters[key] = None
            # 清洗排序顺序
            order_key = f'sort_order_{i}'
            if filters[order_key] not in ('asc', 'desc'):
                filters[order_key] = 'asc'

        results, total_count = library.query_books(**filters)
    else:
        results, total_count = [], 0

    # Get sections for location dropdown
    with opengauss_run(config) as db:
        db.cur.execute("SELECT location_id, section_name FROM library_sections;")
        sections = db.cur.fetchall()

    # 传递排序选项给模板（用于下拉框）
    sort_options = [
        ('title', 'Title'),
        ('author', 'Author'),
        ('year', 'Year'),
        ('price', 'Price'),
        ('buy_date', 'Buy Date'),
        ('section', 'Section'),
        ('status', 'Status')
    ]

    return render_template(
        'search.html',
        results=results,
        total_count=total_count,
        sections=sections,
        filters=filters,
        is_admin=is_admin,
        sort_options=sort_options  # 传给模板
    )

# ========== Borrow Records ==========

@app.route('/borrow_records', methods=['GET', 'POST'])
def borrow_records():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    current_user = session['user']
    is_admin = current_user in library.list_admin_users

    # 默认查询目标用户
    target_user = current_user  # 普通用户只能查自己
    if is_admin:
        if request.method == 'POST':
            target_user = request.form.get('username') or None
        else:
            target_user = request.args.get('username') or None  # 支持 URL 参数

    # 获取记录
    if is_admin and target_user is None:
        # 管理员不指定用户 → 查所有
        records = library.list_borrow_records()
    else:
        # 指定用户（包括普通用户查自己）
        records = library.list_borrow_records(user=target_user)

    return render_template(
        'borrow_records.html',
        records=records,
        is_admin=is_admin,
        current_user=current_user,
        target_user=target_user
    )

# ========== Borrow Action ==========
@app.route('/borrow/<int:box_id>', methods=['POST'])
def borrow(box_id):
    if 'user' not in session:
        abort(403)
    borrower = session['user']
    from datetime import date
    today = date.today().isoformat()
    result = library.borrow_book(box_id, borrower, today)
    if result['success']:
        flash(result['message'], "success")
    else:
        flash(result['message'], "danger")
    return redirect(request.referrer or url_for('search'))

# ========== Return Page (Placeholder) ==========
@app.route('/return')
def return_page():
    if 'user' not in session:
        return redirect(url_for('login'))
    username = session['user']
    # 查询当前用户借出且未归还的书（即 be_borrowed = True 且 borrower = username）
    borrowed_boxes, _ = library.query_books(borrower=username, borrow=True)
    return render_template('return.html', borrowed_boxes=borrowed_boxes)

@app.route('/return/confirm/<int:box_id>', methods=['GET', 'POST'])
def return_confirm(box_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    # 先确认这本书确实被当前用户借出且未归还
    username = session['user']
    boxes, _ = library.query_books(borrower=username, borrow=True, book_id=None)
    box = next((b for b in boxes if b['id'] == box_id), None)
    if not box:
        flash("You cannot return this book.", "danger")
        return redirect(url_for('return_page'))

    if request.method == 'POST':
        return_date_str = request.form['return_date']
        condition = request.form['condition']  # 'good' or 'damaged'
        fine = (condition == 'good')  # good → fine=True; damaged → fine=False

        result = library.return_book(box_id, return_date_str, fine=fine)
        if result['success']:
            flash(result['message'], "success")
        else:
            flash(result['message'], "danger")
        return redirect(url_for('return_page'))

    # GET: 显示确认表单，默认今天
    today = date.today().isoformat()
    return render_template('return_confirm.html', box=box, today=today)

# Admin Actions

@app.route('/admin/throw_damaged', methods=['POST'])
def throw_damaged():
    if 'user' not in session or session['user'] not in library.list_admin_users:
        abort(403)
    result = library.throw_away_damaged_books()
    if result['success']:
        flash(result['message'], "success")
        if result.get('thrown'):
            details = ", ".join([f"{item['title']} (ID: {item['book_id']})" for item in result['thrown']])
            flash(f"Thrown books: {details}", "info")
    else:
        flash("Failed to throw away damaged books.", "danger")
    return redirect(url_for('books'))

# Redirect POST to avoid re-submit on refresh
@app.route('/throw_damaged')
def throw_damaged_redirect():
    return redirect(url_for('books'))  # or use POST-only, but better to use form


@app.route('/admin/set_damaged', methods=['GET', 'POST'])
def set_damaged_form():
    if 'user' not in session or session['user'] not in library.list_admin_users:
        abort(403)
    
    if request.method == 'POST':
        try:
            box_id = int(request.form['box_id'])
            result = library.set_damaged(box_id)
            if result['success']:
                flash(result['message'], "success")
            else:
                flash(result['message'], "warning")
        except (ValueError, KeyError):
            flash("Invalid box ID.", "danger")
        return redirect(url_for('set_damaged_form'))
    
    return render_template('set_damaged.html')


# ========== Add Book ==========
@app.route('/admin/add_book', methods=['GET', 'POST'])
def add_book():
    if 'user' not in session or session['user'] not in library.list_admin_users:
        abort(403)

    with opengauss_run(config) as db:
        db.cur.execute("SELECT location_id, section_name FROM library_sections;")
        sections = db.cur.fetchall()

    if request.method == 'POST':
        try:
            book_id_str = request.form.get('book_id')
            location = int(request.form['location'])
            buy_date = request.form['buy_date']

            if book_id_str:  # 添加副本
                book_id = int(book_id_str)
                count = int(request.form['count'])
                result = library.add_book_copies(book_id, count, buy_date, location)
                flash(f"Added {result['added_copies']} copies of '{result['title']}' by {result['author']}.", "success")
            else:  # 添加新书
                title = request.form['title'].strip()
                author = request.form['author'].strip()
                year = int(request.form['year'])
                price = float(request.form['price'])
                if not title or not author:
                    raise ValueError("Title and author cannot be empty.")
                new_id = library.add_book(title, author, year, price, buy_date, location)
                flash(f"New book '{title}' added with ID {new_id}.", "success")

        except Exception as e:
            flash(f"Error: {str(e)}", "danger")
        return redirect(url_for('add_book'))

    return render_template('add_book.html', sections=sections)

# ========== Stats Page ==========
@app.route('/stats')
def stats():
    if 'user' not in session:
        return redirect(url_for('login'))
    stats = library.statistics_all()
    return render_template('stats.html', stats=stats)

# ========== Error Handlers ==========
@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(403)
def forbidden(e):
    return render_template('403.html'), 403

# ========== Run App ==========
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)