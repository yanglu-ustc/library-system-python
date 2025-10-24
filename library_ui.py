from sql import opengauss_run

class LibrarySQL(object):
    def __init__(self, config):
        self.config = config
        self.list_admin_users = []
        with opengauss_run(self.config) as db:
            db.cur.execute("SELECT username FROM users WHERE is_admin = TRUE;")
            rows = db.cur.fetchall()
            self.list_admin_users = [row[0] for row in rows]

    # ========== Listing ==========
    def list_books(self):
        sql = """
            SELECT DISTINCT b.book_id, b.title, b.author, b.year, b.price, b.num_books, b.borrowed_count
            FROM books b
        """
        with opengauss_run(self.config) as db:
            db.cur.execute(sql)
            rows = db.cur.fetchall()
        result = []
        for row in rows:
            book_id, title, author, year, price, num_books, borrowed_count = row
            result.append({
                'book_id': book_id,
                'title': title,
                'author': author,
                'year': year,
                'price': price,
                'num_books': num_books,
                'borrowed_count': borrowed_count
            })
        return result

    def list_book_boxes(self):
        sql = """
            SELECT b.book_id, b.title, b.author, bb.buy_date, ls.section_name, bb.be_borrowed,
                   bb.fine, b.year, b.price, bb.id
            FROM book_boxes bb
            JOIN books b ON bb.book_id = b.book_id
            JOIN library_sections ls ON bb.location = ls.location_id
        """
        with opengauss_run(self.config) as db:
            db.cur.execute(sql)
            book_boxes = db.cur.fetchall()
        result = []
        for box in book_boxes:
            (book_id, title, author, buy_date, section_name, be_borrowed,
             fine, year, price, id_) = box
            status = "Borrowed" if be_borrowed else "Available"
            fine_status = "Yes" if fine else "No(wait to throw away)"
            result.append({
                'book_id': book_id,
                'title': title,
                'author': author,
                'year': year,
                'price': price,
                'buy_date': buy_date,
                'section': section_name,
                'status': status,
                'fine': fine_status,
                'fine_bool': fine,
                'id': id_
            })
        return result

    # ========== Operations ==========
    def add_book(self, title: str, author: str, year: int, price: float, buy_date: str, location: int):
        # make sure location exists
        with opengauss_run(self.config) as db:
            db.cur.execute("SELECT 1 FROM library_sections WHERE location_id = %s;", (location,))
            if not db.cur.fetchone():
                raise ValueError("Invalid location")

        with opengauss_run(self.config) as db:
            # no need, because we have book_id as primary key
            # db.cur.execute("SELECT 1 FROM books WHERE title = %s AND author = %s;", (title, author))
            # if db.cur.fetchone():
            #     raise ValueError("Book already exists")
            sql = "INSERT INTO books (title, author, year, price, num_books) VALUES (%s, %s, %s, %s, 1) RETURNING book_id;"
            db.cur.execute(sql, (title, author, year, price))
            book_id = db.cur.fetchone()[0]
            
            sql = "INSERT INTO book_boxes (book_id, buy_date, location) VALUES (%s, %s, %s);"
            db.cur.execute(sql, (book_id, buy_date, location))
        return book_id

    def add_book_copies(self, book_id: int, count: int, buy_date: str, location: int):
        with opengauss_run(self.config) as db:
            db.cur.execute("SELECT title, author FROM books WHERE book_id = %s;", (book_id,))
            result = db.cur.fetchone()
            if not result:
                raise ValueError("Book not found")
            title, author = result

        with opengauss_run(self.config) as db:
            values = [(book_id, buy_date, location)] * count
            db.cur.executemany("INSERT INTO book_boxes (book_id, buy_date, location) VALUES (%s, %s, %s)", values)
            db.cur.execute("UPDATE books SET num_books = num_books + %s WHERE book_id = %s;", (count, book_id))
        return {"title": title, "author": author, "added_copies": count}

    def borrow_book(self, id_: int, borrower: str, borrow_date: str):
        with opengauss_run(self.config) as db:

            # no need, because be_borrowed is checked before inserting in the web
            # db.cur.execute("SELECT be_borrowed FROM book_boxes WHERE id = %s;", (id_,))
            # result = db.cur.fetchone()
            # if not result:
            #     return {"success": False, "message": f"Book with ID {id_} not found."}
            # if result[0]:
            #     return {"success": False, "message": f"Book with ID {id_} is already borrowed."}

            sql = "INSERT INTO borrow_records (book_box_id, borrower, borrow_date) VALUES (%s, %s, %s);"
            db.cur.execute(sql, (id_, borrower, borrow_date))
            sql = "UPDATE book_boxes SET be_borrowed = TRUE WHERE id = %s;"
            db.cur.execute(sql, (id_,))
            db.cur.execute("""
                UPDATE books
                SET borrowed_count = borrowed_count + 1
                WHERE book_id = (SELECT book_id FROM book_boxes WHERE id = %s);
            """, (id_,))

        return {"success": True, "message": f"Book with ID {id_} borrowed by {borrower} on {borrow_date}."}

    def return_book(self, id_: int, return_date: str, fine: bool = True):
        with opengauss_run(self.config) as db:
            db.cur.execute("SELECT be_borrowed FROM book_boxes WHERE id = %s;", (id_,))
            result = db.cur.fetchone()
            if not result or not result[0]:
                return {"success": False, "message": f"The book with ID {id_} is not currently borrowed."}

            sql = "UPDATE borrow_records SET return_date = %s WHERE book_box_id = %s AND return_date IS NULL;"
            db.cur.execute(sql, (return_date, id_))
            sql = "UPDATE book_boxes SET be_borrowed = FALSE, fine = %s WHERE id = %s;"
            db.cur.execute(sql, (fine, id_))
            sql = "UPDATE books SET borrowed_count = GREATEST(borrowed_count - 1, 0) WHERE book_id = (SELECT book_id FROM book_boxes WHERE id = %s);"
            db.cur.execute(sql, (id_,))
        return {"success": True, "message": f"Book with ID {id_} returned on {return_date}. Fine: {'Yes' if fine else 'No'}."}

    def set_damaged(self, id_: int):
        with opengauss_run(self.config) as db:
            db.cur.execute("SELECT fine FROM book_boxes WHERE id = %s and fine = TRUE and be_borrowed = FALSE;", (id_,))
            result = db.cur.fetchone()
            if not result:
                return {"success": False, "message": f"Book with ID {id_} not found."}
            if not result[0]:
                return {"success": False, "message": f"Book with ID {id_} already damaged."}

            db.cur.execute("UPDATE book_boxes SET fine = FALSE WHERE id = %s;", (id_,))
        return {"success": True, "message": f"Book with ID {id_} marked as damaged."}

    def throw_away_damaged_books(self):
        with opengauss_run(self.config) as db:
            db.cur.execute("SELECT bb.id, b.title, b.author, b.book_id FROM book_boxes bb JOIN books b ON bb.book_id = b.book_id WHERE bb.fine = FALSE;")
            damaged = db.cur.fetchall()
            if not damaged:
                return {"success": True, "message": "No damaged books to throw away.", "thrown": []}

            db.cur.execute("""DELETE FROM borrow_records WHERE book_box_id IN (
                SELECT id FROM book_boxes WHERE fine = FALSE
            );""")
            
            db.cur.execute("DELETE FROM book_boxes WHERE fine = FALSE;")
            thrown = []
            for id_, title, author, book_id in damaged:
                thrown.append({'title': title, 'book_id': book_id})
                db.cur.execute("UPDATE books SET num_books = num_books - 1 WHERE book_id = %s;", (book_id,))

            db.cur.execute("DELETE FROM books WHERE num_books <= 0;")
        return {"success": True, "message": f"Threw away {len(thrown)} damaged books.", "thrown": thrown}

    # ========== Advanced Querying ==========
    def query_books(self, title=None, author=None, book_id=None, year_min=None, year_max=None, price_min=None, price_max=None,
                    location=None, borrow=None, borrower=None, fine=None,
                    # Sorting with up to 3 levels
                    sort_by_1=None, sort_order_1='asc', sort_by_2=None, sort_order_2='asc', sort_by_3=None, sort_order_3='asc'):
        sql = """
            SELECT b.title, b.author, b.book_id, bb.buy_date, ls.section_name, bb.be_borrowed,
                   bb.fine, b.year, b.price, bb.id, br.borrow_date
            FROM book_boxes bb
            JOIN books b ON bb.book_id = b.book_id
            JOIN library_sections ls ON bb.location = ls.location_id
            LEFT JOIN borrow_records br ON bb.id = br.book_box_id AND br.return_date IS NULL
            WHERE 1=1
        """
        params = []
        if title:
            sql += " AND b.title = %s"
            params.append(title)
        if author:
            sql += " AND b.author = %s"
            params.append(author)
        if book_id:
            sql += " AND b.book_id = %s"
            params.append(book_id)
        if year_min is not None:
            sql += " AND b.year >= %s"
            params.append(year_min)
        if year_max is not None:
            sql += " AND b.year <= %s"
            params.append(year_max)
        if price_min is not None:
            sql += " AND b.price >= %s"
            params.append(price_min)
        if price_max is not None:
            sql += " AND b.price <= %s"
            params.append(price_max)
        if location:
            sql += " AND bb.location = %s"
            params.append(location)
        if borrow is not None:
            sql += " AND bb.be_borrowed = %s"
            params.append(borrow)
        if borrower:
            sql += " AND br.borrower = %s AND br.return_date IS NULL"
            params.append(borrower)
        if fine is not None:
            sql += " AND bb.fine = %s"
            params.append(fine)

        # Sorting
        if sort_by_1:
            sql += f" ORDER BY {sort_by_1} {sort_order_1.upper()}"
            if sort_by_2:
                sql += f", {sort_by_2} {sort_order_2.upper()}"
                if sort_by_3:
                    sql += f", {sort_by_3} {sort_order_3.upper()}"

        with opengauss_run(self.config) as db:
            db.cur.execute(sql, params)
            rows = db.cur.fetchall()
        result = []
        for row in rows:
            (title, author, book_id, buy_date, section, be_borrowed,
             fine, year, price, id_, borrow_date) = row
            result.append({
                'title': title,
                'author': author,
                'book_id': book_id,
                'year': year,
                'price': price,
                'buy_date': buy_date,
                'section': section,
                'status': 'Borrowed' if be_borrowed else 'Available',
                'fine': 'Yes' if fine else 'No(wait to throw away)',
                'fine_bool': fine,
                'id': id_,
                'borrow_date': borrow_date
            })
        return result, len(result)

    # ========== Borrow Records ==========
    def list_borrow_records(self, user: str = None):
        if user is not None:
            sql = """
                SELECT 
                    br.record_id,
                    br.borrower,
                    br.borrow_date,
                    br.return_date,
                    bb.id AS box_id,
                    b.title,
                    b.author,
                    ls.section_name,
                    bb.fine
                FROM borrow_records br
                JOIN book_boxes bb ON br.book_box_id = bb.id
                JOIN books b ON bb.book_id = b.book_id
                JOIN library_sections ls ON bb.location = ls.location_id
                WHERE br.borrower = %s
                ORDER BY br.borrow_date DESC, br.record_id DESC;
            """
            with opengauss_run(self.config) as db:
                db.cur.execute(sql, (user,))
                rows = db.cur.fetchall()
        else:
            sql = """
                SELECT 
                    br.record_id,
                    br.borrower,
                    br.borrow_date,
                    br.return_date,
                    bb.id AS box_id,
                    b.title,
                    b.author,
                    ls.section_name,
                    bb.fine
                FROM borrow_records br
                JOIN book_boxes bb ON br.book_box_id = bb.id
                JOIN books b ON bb.book_id = b.book_id
                JOIN library_sections ls ON bb.location = ls.location_id
                ORDER BY br.borrow_date DESC, br.record_id DESC;
            """
            with opengauss_run(self.config) as db:
                db.cur.execute(sql)
                rows = db.cur.fetchall()

        result = []
        for row in rows:
            record_id, borrower, borrow_date, return_date, box_id, title, author, section_name, fine = row
            status = "Returned" if return_date else "Borrowed"
            result.append({
                'record_id': record_id,
                'borrower': borrower,
                'borrow_date': borrow_date,
                'return_date': return_date,
                'box_id': box_id,
                'title': title,
                'author': author,
                'section': section_name,
                'status': status,
                'fine': fine
            })
        return result

    # ========= Overview Statistics ==========
    def get_overview_stats(self, group_by: str = None):
        """获取系统概览统计"""
        sql = """
            SELECT 
                COUNT(DISTINCT b.book_id) AS total_titles,
                AVG(b.price) AS avg_price,
                SUM(b.price) AS total_value,
                COUNT(bb.id) AS total_copies
        """
        if group_by == 'location':
            sql += ", ls.section_name"
        elif group_by == 'author':
            sql += ", b.author"
        elif group_by == 'year':
            sql += ", b.year"
        elif group_by == 'status':
            sql += ", bb.be_borrowed"
        elif group_by == 'fine':
            sql += ", bb.fine"
        elif group_by == 'borrower':
            sql += ", br.borrower"
        elif group_by == "buy_date":
            sql += ", TO_CHAR(bb.buy_date, 'YYYY-MM-DD')"

        sql += """
            FROM books b
            JOIN book_boxes bb ON b.book_id = bb.book_id
            JOIN library_sections ls ON bb.location = ls.location_id
            LEFT JOIN borrow_records br ON bb.id = br.book_box_id AND br.return_date IS NULL
        """
        if group_by == 'location':
            sql += " GROUP BY ls.section_name"
        elif group_by == 'author':
            sql += " GROUP BY b.author"
        elif group_by == 'year':
            sql += " GROUP BY b.year"
        elif group_by == 'status':
            sql += " GROUP BY bb.be_borrowed"
        elif group_by == 'fine':
            sql += " GROUP BY bb.fine"
        elif group_by == 'borrower':
            sql += " GROUP BY br.borrower"
        elif group_by == "buy_date":
            sql += " GROUP BY bb.buy_date"
        sql += ";"
        with opengauss_run(self.config) as db:
            db.cur.execute(sql)
            rows = db.cur.fetchall()
        result = []
        for row in rows:
            (total_titles, avg_price, total_value, total_copies) = row[:4]
            result.append({
                'total_titles': total_titles,
                'avg_price': avg_price,
                'total_value': total_value,
                'total_copies': total_copies,
                'group_key': row[4] if group_by else 'overall'
            })
        return result

    def statistics_all(self):
        group_bys = [None, 'location', 'author', 'year', 'status', 'fine', 'borrower', 'buy_date']
        stats = {}
        for group in group_bys:
            stats[group if group else 'overall'] = self.get_overview_stats(group_by=group)

        return stats
