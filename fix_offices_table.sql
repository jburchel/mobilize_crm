BEGIN TRANSACTION;
CREATE TABLE offices_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    address TEXT,
    city TEXT,
    state TEXT,
    zip_code TEXT,
    phone TEXT,
    email TEXT,
    created_at DATETIME,
    updated_at DATETIME
);
INSERT INTO offices_new (name, address, city, state, zip_code, phone, email, created_at, updated_at)
SELECT name, address, city, state, zip_code, phone, email, created_at, updated_at FROM offices;
DROP TABLE offices;
ALTER TABLE offices_new RENAME TO offices;
COMMIT; 