import re
import psycopg2
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import config

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

# ─────────────────────────────────────────────────────────────────────────────
# Database connection helper
# ─────────────────────────────────────────────────────────────────────────────
def get_db_connection():
    conn = psycopg2.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        dbname=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD
    )
    return conn


# ─────────────────────────────────────────────────────────────────────────────
# Create the users table if it does not exist
# ─────────────────────────────────────────────────────────────────────────────
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            SERIAL PRIMARY KEY,
            full_name     VARCHAR(255)  NOT NULL,
            email         VARCHAR(255)  UNIQUE NOT NULL,
            password_hash TEXT          NOT NULL,
            created_at    TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    cur.close()
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Create the device_metrics table if it does not exist
# This table stores all metrics sent by monitored devices (PC-01 etc.)
# ─────────────────────────────────────────────────────────────────────────────
def init_metrics_db():
    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS device_metrics (
            id            SERIAL PRIMARY KEY,
            device_name   VARCHAR(100)  NOT NULL,
            device_type   VARCHAR(100),
            timestamp     VARCHAR(50),
            status        VARCHAR(50),
            cpu_usage     NUMERIC(5, 2),
            memory_usage  NUMERIC(5, 2),
            net_sent_mb   NUMERIC(10, 3),
            net_recv_mb   NUMERIC(10, 3),
            latency_ms    NUMERIC(8, 2),
            packet_loss   NUMERIC(5, 2),
            received_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    cur.close()
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Email validation helper
# ─────────────────────────────────────────────────────────────────────────────
EMAIL_REGEX = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')

def is_valid_email(email: str) -> bool:
    return bool(EMAIL_REGEX.match(email))


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return redirect(url_for('register'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name        = request.form.get('full_name', '').strip()
        email            = request.form.get('email', '').strip().lower()
        password         = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # ── Validation ────────────────────────────────────────────────────────
        if not all([full_name, email, password, confirm_password]):
            flash('All fields are required.', 'error')
            return render_template('register.html')

        if not is_valid_email(email):
            flash('Please enter a valid email address.', 'error')
            return render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return render_template('register.html')

        # ── Database checks & insert ──────────────────────────────────────────
        try:
            conn = get_db_connection()
            cur  = conn.cursor()

            # Check for duplicate email
            cur.execute("SELECT id FROM users WHERE email = %s;", (email,))
            if cur.fetchone():
                flash('An account with this email already exists. Please log in.', 'error')
                cur.close()
                conn.close()
                return render_template('register.html')

            # Hash password — never store plain text
            hashed_password = generate_password_hash(password)

            # Insert new user
            cur.execute(
                "INSERT INTO users (full_name, email, password_hash) VALUES (%s, %s, %s);",
                (full_name, email, hashed_password)
            )
            conn.commit()
            cur.close()
            conn.close()

            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))

        except psycopg2.OperationalError as e:
            flash(f'Database connection error: {e}', 'error')
            return render_template('register.html')

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        # ── Basic presence check ───────────────────────────────────────────
        if not email or not password:
            flash('Please enter both email and password.', 'error')
            return render_template('login.html')

        # ── Look up the user in PostgreSQL ─────────────────────────────────
        try:
            conn = get_db_connection()
            cur  = conn.cursor()
            cur.execute(
                "SELECT id, full_name, password_hash FROM users WHERE email = %s;",
                (email,)
            )
            user = cur.fetchone()
            cur.close()
            conn.close()
        except psycopg2.OperationalError as e:
            flash(f'Database connection error: {e}', 'error')
            return render_template('login.html')

        # ── Verify credentials ─────────────────────────────────────────────
        if user is None or not check_password_hash(user[2], password):
            flash('Invalid email or password. Please try again.', 'error')
            return render_template('login.html')

        # ── Create session and redirect ────────────────────────────────────
        session['user_id']   = user[0]
        session['user_name'] = user[1]
        session['email']     = email
        flash(f'Welcome back, {user[1]}!', 'success')
        return redirect(url_for('dashboard'))

    # GET — just render the login page
    return render_template('login.html')


# ─────────────────────────────────────────────────────────────────────────────
# API endpoint — receive metrics from monitored devices
# Devices POST JSON here; we save each reading to device_metrics.
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/api/metrics', methods=['POST'])
def receive_metrics():
    # Read the JSON body sent by the device
    data = request.get_json(silent=True)

    # Reject requests that are not valid JSON
    if not data:
        return jsonify({"error": "Invalid or missing JSON body"}), 400

    # Extract each field; use None as the default if a field is missing
    device_name  = data.get("device_name")
    device_type  = data.get("device_type")
    timestamp    = data.get("timestamp")
    status       = data.get("status")
    cpu_usage    = data.get("cpu_usage")
    memory_usage = data.get("memory_usage")
    net_sent_mb  = data.get("net_sent_mb")
    net_recv_mb  = data.get("net_recv_mb")
    latency_ms   = data.get("latency_ms")
    packet_loss  = data.get("packet_loss")

    # device_name is the minimum required field
    if not device_name:
        return jsonify({"error": "device_name is required"}), 400

    # Save the reading to PostgreSQL
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute("""
            INSERT INTO device_metrics
                (device_name, device_type, timestamp, status,
                 cpu_usage, memory_usage, net_sent_mb, net_recv_mb,
                 latency_ms, packet_loss)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """, (device_name, device_type, timestamp, status,
              cpu_usage, memory_usage, net_sent_mb, net_recv_mb,
              latency_ms, packet_loss))
        conn.commit()
        cur.close()
        conn.close()
    except psycopg2.OperationalError as e:
        return jsonify({"error": f"Database error: {e}"}), 500

    return jsonify({"status": "ok", "message": "Metrics saved"}), 201


# ─────────────────────────────────────────────────────────────────────────────
# API endpoint — get latest metrics for PC-01 (protected route)
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/api/devices/PC-01/latest', methods=['GET'])
def get_pc01_latest():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT device_name, device_type, status, cpu_usage, memory_usage,
                   net_sent_mb, net_recv_mb, latency_ms, packet_loss, timestamp
            FROM device_metrics
            WHERE device_name = %s
            ORDER BY id DESC
            LIMIT 1;
        """, ('PC-01',))
        row = cur.fetchone()

        if not row:
            return jsonify({"error": "No metrics found for PC-01"}), 404

        return jsonify({
            "device_name": row[0],
            "device_type": row[1],
            "status": row[2],
            "cpu_usage": float(row[3]) if row[3] is not None else None,
            "memory_usage": float(row[4]) if row[4] is not None else None,
            "net_sent_mb": float(row[5]) if row[5] is not None else None,
            "net_recv_mb": float(row[6]) if row[6] is not None else None,
            "latency_ms": float(row[7]) if row[7] is not None else None,
            "packet_loss": float(row[8]) if row[8] is not None else None,
            "timestamp": row[9]
        }), 200

    except psycopg2.OperationalError as e:
        return jsonify({"error": f"Database error: {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# API endpoint — get latest metrics for all devices (PC-01 & PC-02) (protected)
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/api/devices/latest', methods=['GET'])
def get_devices_latest():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT ON (device_name)
                   device_name, device_type, status, cpu_usage, memory_usage,
                   net_sent_mb, net_recv_mb, latency_ms, packet_loss, timestamp
            FROM device_metrics
            WHERE device_name IN (%s, %s, %s, %s)
            ORDER BY device_name, id DESC;
        """, ('PC-01', 'PC-02', 'PC-03', 'PC-04'))
        rows = cur.fetchall()

        devices = []
        for row in rows:
            devices.append({
                "device_name": row[0],
                "device_type": row[1],
                "status": row[2],
                "cpu_usage": float(row[3]) if row[3] is not None else None,
                "memory_usage": float(row[4]) if row[4] is not None else None,
                "net_sent_mb": float(row[5]) if row[5] is not None else None,
                "net_recv_mb": float(row[6]) if row[6] is not None else None,
                "latency_ms": float(row[7]) if row[7] is not None else None,
                "packet_loss": float(row[8]) if row[8] is not None else None,
                "timestamp": row[9]
            })

        return jsonify(devices), 200

    except psycopg2.OperationalError as e:
        return jsonify({"error": f"Database error: {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Logout (clear the authenticated session)
@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    flash('You have been signed out successfully.', 'success')
    return redirect(url_for('login'))


# Dashboard (protected route)
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please log in to access the dashboard.', 'error')
        return redirect(url_for('login'))
    return render_template('dashboard.html', user_name=session.get('user_name', 'User'))


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    init_db()           # create the users table if needed
    init_metrics_db()   # create the device_metrics table if needed
    app.run(host="0.0.0.0", port=5000, debug=True)
