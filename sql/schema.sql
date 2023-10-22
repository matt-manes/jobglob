CREATE TABLE IF NOT EXISTS
    companies (
        company_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        date_added TIMESTAMP
    );

CREATE TABLE IF NOT EXISTS
    boards (
        board_id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT UNIQUE,
        company_id INTEGER REFERENCES companies (company_id) ON DELETE CASCADE ON UPDATE CASCADE,
        date_added TIMESTAMP
    );

CREATE TABLE IF NOT EXISTS
    listings (
        listing_id INTEGER PRIMARY KEY AUTOINCREMENT,
        position TEXT,
        location TEXT DEFAULT "Remote",
        url TEXT UNIQUE,
        company_id INTEGER REFERENCES companies (company_id) ON DELETE CASCADE ON UPDATE CASCADE,
        alive INTEGER DEFAULT 1,
        date_added TIMESTAMP,
        date_removed TIMESTAMP DEFAULT NULL
    );

CREATE TABLE IF NOT EXISTS
    seen_listings (
        seen_id INTEGER PRIMARY KEY AUTOINCREMENT,
        listing_id INTEGER REFERENCES listings (listing_id) ON DELETE CASCADE ON UPDATE CASCADE
    );

CREATE TABLE IF NOT EXISTS
    pinned_listings (
        pinned_id INTEGER PRIMARY KEY AUTOINCREMENT,
        listing_id INTEGER REFERENCES listings (listing_id) ON DELETE CASCADE ON UPDATE CASCADE
    );

CREATE TABLE IF NOT EXISTS
    applications (
        application_id INTEGER PRIMARY KEY AUTOINCREMENT,
        listing_id INTEGER REFERENCES listings (listing_id) ON DELETE CASCADE ON UPDATE CASCADE,
        date_applied TIMESTAMP
    );

CREATE TABLE IF NOT EXISTS
    rejections (
        rejection_id INTEGER PRIMARY KEY AUTOINCREMENT,
        application_id INTEGER REFERENCES applications (application_id) ON DELETE CASCADE ON UPDATE CASCADE,
        date_rejected TIMESTAMP
    );