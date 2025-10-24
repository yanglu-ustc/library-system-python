import psycopg2
import argparse
import os

host = os.getenv("DB_HOST", "localhost")
port = os.getenv("DB_PORT", 5432)
database = os.getenv("DB_NAME", "postgres")
user = os.getenv("DB_USER", "omm")
password = os.getenv("DB_PASSWORD", "password")

config = {
    "host": host,
    "port": port,
    "database": database,
    "user": user,
    "password": password
}

class opengauss_run(object):
    def __init__(self, config, test=False):
        self.config = config
        self.conn = None
        self.cur = None
        self.test = test

    def __enter__(self):
        self.conn = psycopg2.connect(**self.config)
        self.cur = self.conn.cursor()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None or self.test:
            self.conn.rollback()
        else:
            self.conn.commit()
        self.cur.close()
        self.conn.close()

def insert_book_and_boxes(db, title, author, year, price, num_books, buy_date, location, copy_count):
    """
    Insert a book and its copies (book_boxes)
    """
    # Insert book
    db.cur.execute(
        "INSERT INTO books (title, author, year, price, num_books) VALUES (%s, %s, %s, %s, %s) RETURNING book_id;",
        (title, author, year, price, num_books)
    )
    book_id = db.cur.fetchone()[0]
    # print(f"Inserted book: {title} (ID: {book_id})")

    # Insert book_boxes (copies)
    for _ in range(copy_count):
        db.cur.execute(
            "INSERT INTO book_boxes (book_id, buy_date, location) VALUES (%s, %s, %s);",
            (book_id, buy_date, location)
        )
    # print(f"Inserted {copy_count} copies into location {location}")


def main():
    parser = argparse.ArgumentParser(description="Initialize library database schema and data.")
    parser.add_argument(
        "--filename",
        type=str,
        required=True,
        help="Path to the SQL schema file (e.g., library_schema.sql)"
    )
    args = parser.parse_args()

    # Step 1: Run schema
    with open(args.filename, "r", encoding="utf-8") as file:
        schema_sql = file.read()

    with opengauss_run(config) as db:
        db.cur.execute(schema_sql)

    if args.filename == "library_start.sql":
        # Step 2: Insert initial data
        with opengauss_run(config) as db:
            # Fiction
            insert_book_and_boxes(db, 'The Great Gatsby', 'F. Scott Fitzgerald', 1925, 10.99, 2, '2020-01-15', 1, 2)
            insert_book_and_boxes(db, '1984', 'George Orwell', 1949, 8.99, 3, '2019-05-20', 1, 3)
            
            # Non-Fiction
            insert_book_and_boxes(db, 'The Catcher in the Rye', 'J.D. Salinger', 1951, 9.99, 2, '2022-09-10', 2, 2)
            
            # Science
            insert_book_and_boxes(db, 'A Brief History of Time', 'Stephen Hawking', 1988, 15.99, 6, '2021-03-12', 3, 6)
            insert_book_and_boxes(db, 'The Selfish Gene', 'Richard Dawkins', 1976, 12.99, 1, '2017-11-25', 3, 1)


if __name__ == "__main__":
    main()