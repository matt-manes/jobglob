CREATE TABLE IF NOT EXISTS
    boards (
        board_id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT UNIQUE,
        date_added TIMESTAMP
    );

CREATE TABLE IF NOT EXISTS
    companies (
        company_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        url TEXT DEFAULT NULL,
        board_id INTEGER DEFAULT NULL,
        date_added TIMESTAMP
    );

CREATE TABLE IF NOT EXISTS
    listings (
        listing_id INTEGER PRIMARY KEY AUTOINCREMENT,
        position TEXT,
        company_id INTEGER,
        url TEXT,
        xpath TEXT,
        found_on TEXT NULL,
        date_added TIMESTAMP,
        date_removed TIMESTAMP DEFAULT NULL,
        alive INTEGER DEFAULT 1
    );

CREATE TABLE IF NOT EXISTS
    applications (
        application_id INTEGER PRIMARY KEY AUTOINCREMENT,
        listing_id INTEGER,
        date_applied TIMESTAMP,
        wrote_cover_letter INTEGER DEFAULT NULL,
        rejected INTEGER DEFAULT 0,
        date_rejected TIMESTAMP DEFAULT NULL
    );