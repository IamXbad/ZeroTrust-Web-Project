import sqlite3
from werkzeug.security import generate_password_hash

conn = sqlite3.connect("users.db")
c = conn.cursor()

# ---------------- USERS TABLE ----------------
c.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL
)
""")

# ---------------- DEVICES TABLE ----------------
# device_id must be globally unique
c.execute("""
CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    device_id TEXT UNIQUE NOT NULL,
    FOREIGN KEY (username) REFERENCES users(username)
)
""")

# ---------------- IOT DATA TABLE ----------------
c.execute("""
CREATE TABLE IF NOT EXISTS iot_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    device_id TEXT,
    data TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES devices(device_id)
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS login_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    ip_address TEXT,
    user_agent TEXT,
    login_time TEXT
)
""")

# ---------------- CREATE ADMIN ----------------
c.execute("""
INSERT OR IGNORE INTO users (username, password, role)
VALUES (?, ?, ?)
""", ("admin", generate_password_hash("admin123"), "admin"))

conn.commit()
conn.close()

print("✅ Database initialized successfully")

