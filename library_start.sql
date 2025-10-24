-- Create library_sections table
CREATE TABLE library_sections (
    location_id INTEGER PRIMARY KEY,
    section_name VARCHAR(50) NOT NULL
);

-- Insert initial library sections
INSERT INTO library_sections (location_id, section_name) VALUES
(1, 'Fiction'),
(2, 'Non-Fiction'),
(3, 'Science'),
(4, 'History'),
(5, 'Children');

-- Create books table
CREATE TABLE books (
    book_id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    author VARCHAR(255) NOT NULL,
    year INTEGER,
    price DECIMAL(10, 2),
    num_books INTEGER DEFAULT 0,
    borrowed_count INTEGER DEFAULT 0
);

-- Create book_boxes table
CREATE TABLE book_boxes (
    id SERIAL PRIMARY KEY,
    book_id INTEGER,
    buy_date DATE NOT NULL,
    location INTEGER NOT NULL,
    be_borrowed BOOLEAN DEFAULT FALSE,
    fine BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (book_id) REFERENCES books(book_id),
    FOREIGN KEY (location) REFERENCES library_sections(location_id)
);


CREATE TABLE borrow_records (
    record_id SERIAL PRIMARY KEY,
    book_box_id INTEGER NOT NULL,
    borrower VARCHAR(255) NOT NULL,
    borrow_date DATE NOT NULL,
    return_date DATE DEFAULT NULL,
    FOREIGN KEY (book_box_id) REFERENCES book_boxes(id)
);


CREATE TABLE users (
    username VARCHAR(255) NOT NULL PRIMARY KEY,
    password VARCHAR(255) NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE
);


insert into users (username, password) values
('alice', 'alicepass'),
('bob', 'bobpass'),
('charlie', 'charliepass');

insert into users (username, password, is_admin) values
('admin', 'adminpass', TRUE);
