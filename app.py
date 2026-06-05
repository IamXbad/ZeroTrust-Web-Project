from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = "zero_trust_secret"

DB = "users.db"
EDGE_LOG = "edge_logs.txt"


# -------------------- DB INIT --------------------
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS devices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        device_id TEXT UNIQUE NOT NULL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS iot_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        device_id TEXT,
        data TEXT,
        timestamp TEXT
    )
    """)

    # admin account
    c.execute("""
    INSERT OR IGNORE INTO users (username,password,role)
    VALUES (?,?,?)
    """, ("admin", generate_password_hash("admin123"), "admin"))

    conn.commit()
    conn.close()


# -------------------- LOGIN --------------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT password, role FROM users WHERE username=?", (u,))
        row = c.fetchone()

        if row and check_password_hash(row[0], p):

            # Create session
            session["username"] = u
            session["role"] = row[1]

            # -------- LOGIN LOGGING --------
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ip = request.remote_addr
            agent = request.headers.get("User-Agent")

            c.execute("""
                INSERT INTO login_logs (username, ip_address, user_agent, login_time)
                VALUES (?, ?, ?, ?)
            """, (u, ip, agent, ts))

            conn.commit()
            conn.close()

            return redirect(url_for("dashboard"))

        conn.close()
        return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")


# -------------------- REGISTER --------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        u = request.form["username"]
        p = generate_password_hash(request.form["password"])

        try:
            conn = sqlite3.connect(DB)
            c = conn.cursor()
            c.execute(
                "INSERT INTO users (username,password,role) VALUES (?,?,?)",
                (u, p, "user")
            )
            conn.commit()
            conn.close()
            return redirect(url_for("login"))
        except:
            return render_template("register.html", error="Username already exists")

    return render_template("register.html")


# -------------------- DASHBOARD --------------------
@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        return redirect(url_for("login"))

    from_t = request.args.get("from_time")
    to_t = request.args.get("to_time")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute(
    "SELECT id, device_id FROM devices WHERE username=? ORDER BY id ASC",
    (session["username"],)
    )
    devices = c.fetchall()

    query = "SELECT username,device_id,data,timestamp FROM iot_data"
    params = []

    if from_t and to_t:
        query += " WHERE timestamp BETWEEN ? AND ?"
        params = [from_t, to_t]

    query += " ORDER BY timestamp DESC LIMIT 100"
    c.execute(query, params)
    records = c.fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        user=session["username"],
        role=session["role"],
        devices=devices,
        records=records
    )


# -------------------- ADD DEVICE --------------------
@app.route("/add_device", methods=["GET", "POST"])
def add_device():
    if "username" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        d = request.form["device_id"]

        conn = sqlite3.connect(DB)
        c = conn.cursor()

        try:
            c.execute(
                "INSERT INTO devices (username,device_id) VALUES (?,?)",
                (session["username"], d)
            )
            conn.commit()
            conn.close()
            return redirect(url_for("dashboard"))

        except sqlite3.IntegrityError:
            conn.close()
            return render_template(
                "add_device.html",
                error="Device already registered!"
            )

    return render_template("add_device.html")


# -------------------- ADMIN: USERS + DEVICES --------------------
@app.route("/admin/users")
def admin_users():
    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # Get all users
    c.execute("SELECT id, username, role FROM users")
    users = c.fetchall()

    user_devices = {}

    for u in users:
        c.execute(
            "SELECT id, device_id FROM devices WHERE username=?",
            (u[1],)
        )
        user_devices[u[1]] = c.fetchall()

    conn.close()

    return render_template(
        "admin_users.html",
        users=users,
        user_devices=user_devices
    )

# -------------------- ADMIN: DELETE DEVICE --------------------
@app.route("/admin/delete_device/<int:device_id>")
def delete_device(device_id):
    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM devices WHERE id=?", (device_id,))
    conn.commit()
    conn.close()

    return redirect(url_for("admin_users"))



# -------------------- ADMIN: DELETE USER --------------------
@app.route("/admin/delete_user/<int:user_id>")
def admin_delete_user(user_id):
    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # Get username (to delete devices & data)
    c.execute("SELECT username FROM users WHERE id=?", (user_id,))
    row = c.fetchone()

    if row:
        username = row[0]

        # Delete user's devices
        c.execute("DELETE FROM devices WHERE username=?", (username,))

        # Delete user's IoT data
        c.execute("DELETE FROM iot_data WHERE username=?", (username,))

        # Delete user
        c.execute("DELETE FROM users WHERE id=?", (user_id,))

    conn.commit()
    conn.close()

    return redirect(url_for("admin_users"))


# -------------------- ADMIN: EDGE LOGS --------------------
@app.route("/admin/logs")
def admin_logs():
    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))

    if not os.path.exists(EDGE_LOG):
        logs = []
    else:
        with open(EDGE_LOG) as f:
            logs = f.readlines()[::-1]

    return render_template("admin_logs.html", logs=logs)



# -------------------- ADMIN: LOGIN LOGS --------------------
@app.route("/admin/login_logs")
def admin_login_logs():
    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
        SELECT username, ip_address, user_agent, login_time 
        FROM login_logs 
        ORDER BY login_time DESC
    """)
    logs = c.fetchall()

    conn.close()

    return render_template("admin_login_logs.html", logs=logs)

# -------------------- HARDWARE API (ESP32) --------------------
from flask import jsonify

@app.route("/edge_data", methods=["POST"])
def edge_data():
    incoming = request.get_json()

    device_id = incoming.get("device_id")
    temperature = incoming.get("temperature")

    if not device_id or temperature is None:
        return jsonify({"error": "Invalid data"}), 400

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # 🔎 Check if device is registered
    c.execute("SELECT * FROM devices WHERE device_id=?", (device_id,))
    device = c.fetchone()

    if not device:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(EDGE_LOG, "a") as f:
            f.write(f"[{ts}] ❌ Unauthorized device attempt: {device_id}\n")

        conn.close()
        return jsonify({"error": "Device not registered"}), 403

    # If device exists → accept
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if temperature > 31:
       data = f"⚠️ ALERT! High Temperature = {temperature}C"

       # Optional: also log alert
       with open(EDGE_LOG, "a") as f:
            f.write(f"[{ts}] ⚠️ High temperature from {device_id}\n")
    else:
        data = f"Temperature = {temperature}C"

    c.execute(
        "INSERT INTO iot_data (username,device_id,data,timestamp) VALUES (?,?,?,?)",
        (device[1], device_id, data, ts)  # device[1] = username
    )

    conn.commit()
    conn.close()

    with open(EDGE_LOG, "a") as f:
        f.write(f"[{ts}] ✅ Data accepted from {device_id}\n")

    return jsonify({"status": "success"})
# -------------------- LOGOUT --------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5001, debug=True)