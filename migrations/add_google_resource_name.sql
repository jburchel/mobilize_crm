-- Create new table with desired structure
CREATE TABLE people_new (
    id INTEGER PRIMARY KEY,
    name TEXT,
    email TEXT,
    phone TEXT,
    address TEXT,
    church_id INTEGER,
    role TEXT,
    google_resource_name TEXT UNIQUE,
    FOREIGN KEY (church_id) REFERENCES churches(id)
);

-- Copy existing data
INSERT INTO people_new (id, name, email, phone, address, church_id, role)
SELECT id, name, email, phone, address, church_id, role FROM people;

-- Drop old table
DROP TABLE people;

-- Rename new table
ALTER TABLE people_new RENAME TO people;