from __future__ import annotations

import os
import smtplib
import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests
from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from apscheduler.schedulers.background import BackgroundScheduler
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "flood.db"

app = Flask(__name__)
app.secret_key = "change-me-in-production"

CHENNAI_BOUNDS = {
    "min_lat": 12.80,
    "max_lat": 13.30,
    "min_lon": 80.10,
    "max_lon": 80.35,
}
GRID_STEP = 0.02
CHENNAI_TZ = "Asia/Kolkata"

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASS = os.environ.get("SMTP_PASS")

SEED_LOCK = threading.Lock()
DB_WRITE_LOCK = threading.Lock()


# Database helpers

def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def ensure_column(conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
    existing = {row[1] for row in cols}
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")


def execute_with_retry(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...], retries: int = 3) -> None:
    for attempt in range(retries):
        try:
            conn.execute(sql, params)
            return
        except sqlite3.OperationalError as exc:
            if "locked" in str(exc).lower() and attempt < retries - 1:
                time.sleep(0.2 * (attempt + 1))
                continue
            raise


def init_db() -> None:
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            phone TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            is_admin INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS flood_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            location_query TEXT NOT NULL,
            location_name TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            rainfall_mm REAL NOT NULL,
            elevation_m REAL NOT NULL,
            risk_level TEXT NOT NULL,
            risk_score REAL NOT NULL,
            predicted_time TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            elevation_m REAL NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS user_locations (
            user_id INTEGER NOT NULL,
            location_id INTEGER NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (user_id),
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (location_id) REFERENCES locations (id)
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS hourly_weather (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location_id INTEGER NOT NULL,
            timestamp_hour TEXT NOT NULL,
            rainfall_mm REAL NOT NULL,
            risk_score REAL NOT NULL,
            risk_level TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE (location_id, timestamp_hour),
            FOREIGN KEY (location_id) REFERENCES locations (id)
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            location_id INTEGER NOT NULL,
            risk_level TEXT NOT NULL,
            timestamp_hour TEXT NOT NULL,
            sent_at TEXT NOT NULL,
            UNIQUE (user_id, location_id, timestamp_hour),
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (location_id) REFERENCES locations (id)
        );
        """
    )
    ensure_column(conn, "flood_checks", "location_id", "location_id INTEGER")
    conn.commit()
    conn.close()


# Utility helpers

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_within_chennai(lat: float, lon: float) -> bool:
    return (
        CHENNAI_BOUNDS["min_lat"] <= lat <= CHENNAI_BOUNDS["max_lat"]
        and CHENNAI_BOUNDS["min_lon"] <= lon <= CHENNAI_BOUNDS["max_lon"]
    )


def normalize_location(text: str) -> str:
    return " ".join(text.lower().strip().split())


def risk_score_from(rainfall_mm: float, elevation_m: float) -> float:
    # Heuristic: heavier rainfall and low elevation increase risk.
    elevation_factor = max(0.0, 50.0 - elevation_m) / 50.0
    rainfall_factor = min(rainfall_mm / 50.0, 1.5)
    score = (rainfall_factor * 0.7) + (elevation_factor * 0.3)
    return round(score * 100.0, 2)


def risk_level_from(score: float) -> str:
    if score >= 70:
        return "High"
    if score >= 45:
        return "Moderate"
    return "Low"


def chennai_now() -> datetime:
    return datetime.now(ZoneInfo(CHENNAI_TZ))


def current_hour_iso() -> str:
    return chennai_now().replace(minute=0, second=0, microsecond=0).isoformat(timespec="minutes")


def generate_grid() -> list[tuple[float, float]]:
    points = []
    lat = CHENNAI_BOUNDS["min_lat"]
    while lat <= CHENNAI_BOUNDS["max_lat"] + 1e-6:
        lon = CHENNAI_BOUNDS["min_lon"]
        while lon <= CHENNAI_BOUNDS["max_lon"] + 1e-6:
            points.append((round(lat, 4), round(lon, 4)))
            lon += GRID_STEP
        lat += GRID_STEP
    return points


def seed_locations() -> None:
    with SEED_LOCK:
        conn = get_db()
        existing = conn.execute("SELECT COUNT(*) FROM locations").fetchone()[0]
        if existing:
            conn.close()
            return

        points = generate_grid()
        batch = []
        for lat, lon in points:
            try:
                elevation = fetch_elevation(lat, lon)
            except requests.RequestException:
                elevation = 0.0
            batch.append((lat, lon, elevation, now_iso()))
            if len(batch) >= 200:
                conn.executemany(
                    "INSERT INTO locations (latitude, longitude, elevation_m, created_at) VALUES (?, ?, ?, ?)",
                    batch,
                )
                conn.commit()
                batch.clear()
                time.sleep(0.05)

        if batch:
            conn.executemany(
                "INSERT INTO locations (latitude, longitude, elevation_m, created_at) VALUES (?, ?, ?, ?)",
                batch,
            )
            conn.commit()
        conn.close()


def nearest_location_id(lat: float, lon: float) -> int | None:
    conn = get_db()
    row = conn.execute(
        """
        SELECT id
        FROM locations
        ORDER BY ((latitude - ?) * (latitude - ?) + (longitude - ?) * (longitude - ?)) ASC
        LIMIT 1
        """,
        (lat, lat, lon, lon),
    ).fetchone()
    conn.close()
    return int(row["id"]) if row else None


def fetch_rainfall_current(lat: float, lon: float) -> float:
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "precipitation",
        "forecast_days": 1,
        "timezone": CHENNAI_TZ,
    }
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    precipitation = hourly.get("precipitation", [])
    hour_key = chennai_now().strftime("%Y-%m-%dT%H:00")
    if hour_key in times:
        idx = times.index(hour_key)
        return float(precipitation[idx])
    return float(max(precipitation) if precipitation else 0.0)


def fetch_daily_forecast(lat: float, lon: float) -> list[dict[str, Any]]:
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "precipitation_sum",
        "forecast_days": 7,
        "timezone": CHENNAI_TZ,
    }
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json().get("daily", {})
    days = data.get("time", [])
    precip = data.get("precipitation_sum", [])
    result = []
    for day, rain in zip(days, precip):
        result.append({"date": day, "rainfall_mm": float(rain)})
    return result


def history_based_forecast(location_id: int, elevation_m: float) -> tuple[list[dict[str, Any]], str | None]:
    cutoff = (chennai_now() - timedelta(days=365)).isoformat(timespec="minutes")
    conn = get_db()
    rows = conn.execute(
        """
        SELECT substr(timestamp_hour, 1, 10) AS day, SUM(rainfall_mm) AS total_rain
        FROM hourly_weather
        WHERE location_id = ? AND timestamp_hour >= ?
        GROUP BY day
        """,
        (location_id, cutoff),
    ).fetchall()
    conn.close()

    daily_totals = [float(row["total_rain"] or 0.0) for row in rows]
    avg_daily = sum(daily_totals) / len(daily_totals) if daily_totals else 0.0
    try:
        current_hour_rain = fetch_rainfall_current(
            *next(iter([(loc["latitude"], loc["longitude"]) for loc in []]), (0.0, 0.0))
        )
    except requests.RequestException:
        current_hour_rain = 0.0

    base = max(0.0, avg_daily + (current_hour_rain * 0.2))
    today = chennai_now().date()
    forecast = []
    for i in range(7):
        day = (today + timedelta(days=i)).isoformat()
        score = risk_score_from(base, elevation_m)
        forecast.append({
            "date": day,
            "rainfall_mm": round(base, 2),
            "risk_score": score,
            "risk_level": risk_level_from(score),
        })
    return forecast, "Using historical estimate"


def send_email(to_email: str, subject: str, body: str) -> bool:
    if not SMTP_USER or not SMTP_PASS:
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = to_email
    msg.set_content(body)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
    return True


def notify_users(location_id: int, risk_level: str, timestamp_hour: str) -> None:
    conn = get_db()
    users = conn.execute(
        """
        SELECT users.id, users.email, locations.latitude, locations.longitude
        FROM user_locations
        JOIN users ON users.id = user_locations.user_id
        JOIN locations ON locations.id = user_locations.location_id
        WHERE user_locations.location_id = ?
        """,
        (location_id,),
    ).fetchall()

    for user in users:
        exists = conn.execute(
            """
            SELECT 1 FROM notifications
            WHERE user_id = ? AND location_id = ? AND timestamp_hour = ?
            """,
            (user["id"], location_id, timestamp_hour),
        ).fetchone()
        if exists:
            continue

        subject = f"Flood detection alert: {risk_level} risk"
        body = (
            "High flood risk detected near your saved area in Chennai.\n"
            f"Time: {timestamp_hour}\n"
            f"Location grid: {user['latitude']:.4f}, {user['longitude']:.4f}\n"
            "Please stay alert and follow local advisories."
        )
        if send_email(user["email"], subject, body):
            with DB_WRITE_LOCK:
                execute_with_retry(
                    conn,
                    """
                    INSERT OR IGNORE INTO notifications
                    (user_id, location_id, risk_level, timestamp_hour, sent_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (user["id"], location_id, risk_level, timestamp_hour, now_iso()),
                )
                conn.commit()
    conn.close()


def run_hourly_weather_job() -> None:
    conn = get_db()
    locations = conn.execute(
        "SELECT id, latitude, longitude, elevation_m FROM locations"
    ).fetchall()
    conn.close()

    timestamp_hour = current_hour_iso()
    conn = get_db()
    for loc in locations:
        try:
            rainfall_mm = fetch_rainfall_current(loc["latitude"], loc["longitude"])
        except requests.RequestException:
            continue
        score = risk_score_from(rainfall_mm, loc["elevation_m"])
        level = risk_level_from(score)
        with DB_WRITE_LOCK:
            execute_with_retry(
                conn,
                """
                INSERT OR IGNORE INTO hourly_weather
                (location_id, timestamp_hour, rainfall_mm, risk_score, risk_level, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (loc["id"], timestamp_hour, rainfall_mm, score, level, now_iso()),
            )
            conn.commit()

        if level == "High":
            notify_users(loc["id"], level, timestamp_hour)
    conn.close()

    cutoff = (chennai_now() - timedelta(days=365)).isoformat(timespec="minutes")
    conn = get_db()
    with DB_WRITE_LOCK:
        execute_with_retry(conn, "DELETE FROM hourly_weather WHERE timestamp_hour < ?", (cutoff,))
        execute_with_retry(conn, "DELETE FROM notifications WHERE timestamp_hour < ?", (cutoff,))
        conn.commit()
    conn.close()


scheduler = BackgroundScheduler(timezone=CHENNAI_TZ)
scheduler_started = False


def start_scheduler() -> None:
    global scheduler_started
    if scheduler_started:
        return
    scheduler.add_job(
        run_hourly_weather_job,
        "interval",
        hours=1,
        id="hourly_weather",
        replace_existing=True,
        next_run_time=chennai_now(),
    )
    scheduler.start()
    scheduler_started = True


def fetch_geocode(query: str) -> dict[str, Any] | None:
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": f"{query}, Chennai, India",
        "format": "json",
        "limit": 1,
    }
    resp = requests.get(url, params=params, timeout=10, headers={"User-Agent": "flood-detection-app"})
    resp.raise_for_status()
    data = resp.json()
    if not data:
        return None
    return data[0]


def fetch_reverse(lat: float, lon: float) -> dict[str, Any] | None:
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {"lat": lat, "lon": lon, "format": "json"}
    resp = requests.get(url, params=params, timeout=10, headers={"User-Agent": "flood-detection-app"})
    resp.raise_for_status()
    return resp.json()


def fetch_elevation(lat: float, lon: float) -> float:
    url = "https://api.open-elevation.com/api/v1/lookup"
    resp = requests.get(url, params={"locations": f"{lat},{lon}"}, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    results = data.get("results", [])
    if not results:
        return 0.0
    return float(results[0].get("elevation", 0.0))


def predicted_time() -> str:
    # Simple placeholder for prediction time.
    return datetime.now().strftime("%I:%M %p")


# Routes


@app.route("/")
def index() -> str:
    return render_template("index.html")


@app.route("/register", methods=["POST"])
def register() -> Any:
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    phone = request.form.get("phone", "").strip()
    password = request.form.get("password", "")

    if not name or not email or not phone or not password:
        return render_template("index.html", error="All fields are required.")
    if not phone.startswith("+91"):
        return render_template("index.html", error="Mobile number must start with +91.")

    is_admin = 1 if email == "admin@flood.local" else 0

    conn = get_db()
    try:
        with DB_WRITE_LOCK:
            execute_with_retry(
                conn,
                "INSERT INTO users (name, email, phone, password_hash, is_admin, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (name, email, phone, generate_password_hash(password), is_admin, now_iso()),
            )
            conn.commit()
    except sqlite3.IntegrityError:
        return render_template("index.html", error="Email already registered.")
    finally:
        conn.close()

    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login() -> Any:
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()

    if not user or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="Invalid credentials.")

    session["user_id"] = user["id"]
    session["is_admin"] = bool(user["is_admin"])
    session["name"] = user["name"]

    return redirect(url_for("dashboard"))


@app.route("/logout")
def logout() -> Any:
    session.clear()
    return redirect(url_for("index"))


@app.route("/dashboard")
def dashboard() -> Any:
    if "user_id" not in session:
        return redirect(url_for("login"))

    return render_template("dashboard.html", name=session.get("name", "User"))


@app.route("/admin")
def admin() -> Any:
    if not session.get("is_admin"):
        return redirect(url_for("dashboard"))

    conn = get_db()
    rows = conn.execute(
        """
        SELECT flood_checks.*, users.name AS user_name, users.email AS user_email
        FROM flood_checks
        JOIN users ON users.id = flood_checks.user_id
        ORDER BY flood_checks.created_at DESC
        """
    ).fetchall()
    conn.close()

    return render_template("admin.html", rows=rows)


# API routes


@app.route("/api/reverse")
def api_reverse() -> Any:
    try:
        lat = float(request.args.get("lat", "0"))
        lon = float(request.args.get("lon", "0"))
    except ValueError:
        return jsonify({"error": "Invalid coordinates"}), 400

    data = fetch_reverse(lat, lon)
    name = data.get("display_name", "Unknown location") if data else "Unknown location"

    return jsonify({"location_name": name})


@app.route("/api/geocode")
def api_geocode() -> Any:
    query = request.args.get("query", "").strip()
    if not query:
        return jsonify({"error": "Missing query"}), 400

    data = fetch_geocode(query)
    if not data:
        return jsonify({"error": "Location not found"}), 404

    lat = float(data["lat"])
    lon = float(data["lon"])
    if not is_within_chennai(lat, lon):
        return jsonify({"error": "Outside Chennai"}), 400

    return jsonify({
        "location_name": data.get("display_name", query),
        "lat": lat,
        "lon": lon,
    })


@app.route("/api/precheck")
def api_precheck() -> Any:
    raw_query = request.args.get("query", "").strip()
    if not raw_query:
        return jsonify({"risk_level": "Unknown"})

    try:
        data = fetch_geocode(raw_query)
    except requests.RequestException:
        return jsonify({"risk_level": "Unknown"})
    if not data:
        return jsonify({"risk_level": "Unknown"})

    lat = float(data["lat"])
    lon = float(data["lon"])
    if not is_within_chennai(lat, lon):
        return jsonify({"risk_level": "Unknown"})

    location_id = nearest_location_id(lat, lon)
    conn = get_db()
    row = None
    if location_id:
        row = conn.execute(
            """
            SELECT risk_level, timestamp_hour
            FROM hourly_weather
            WHERE location_id = ? AND risk_level = 'High'
            ORDER BY timestamp_hour DESC
            LIMIT 1
            """,
            (location_id,),
        ).fetchone()

    if not row:
        query = normalize_location(raw_query)
        row = conn.execute(
            """
            SELECT risk_level, predicted_time, location_name
            FROM flood_checks
            WHERE location_query = ? AND risk_level = 'High'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (query,),
        ).fetchone()
    conn.close()

    if not row:
        return jsonify({"risk_level": "Low"})

    predicted = row["predicted_time"] if "predicted_time" in row.keys() else row["timestamp_hour"]
    return jsonify({
        "risk_level": "High",
        "predicted_time": predicted,
        "location_name": data.get("display_name", raw_query),
    })


@app.route("/api/flood_check", methods=["POST"])
def api_flood_check() -> Any:
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    payload = request.get_json(silent=True) or {}
    query = payload.get("query", "").strip()
    if not query:
        return jsonify({"error": "Missing query"}), 400

    data = fetch_geocode(query)
    if not data:
        return jsonify({"error": "Location not found"}), 404

    lat = float(data["lat"])
    lon = float(data["lon"])
    if not is_within_chennai(lat, lon):
        return jsonify({"error": "Outside Chennai"}), 400

    try:
        rainfall_mm = fetch_rainfall_current(lat, lon)
        elevation_m = fetch_elevation(lat, lon)
    except requests.RequestException:
        return jsonify({"error": "Weather service unavailable"}), 503
    score = risk_score_from(rainfall_mm, elevation_m)
    level = risk_level_from(score)
    pred_time = predicted_time()
    location_id = nearest_location_id(lat, lon)

    conn = get_db()
    with DB_WRITE_LOCK:
        execute_with_retry(
            conn,
            """
            INSERT INTO flood_checks (
                user_id, location_query, location_name, latitude, longitude,
                rainfall_mm, elevation_m, risk_level, risk_score, predicted_time, created_at, location_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session["user_id"],
                normalize_location(query),
                data.get("display_name", query),
                lat,
                lon,
                rainfall_mm,
                elevation_m,
                level,
                score,
                pred_time,
                now_iso(),
                location_id,
            ),
        )
        if location_id:
            execute_with_retry(
                conn,
                """
                INSERT INTO user_locations (user_id, location_id, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET location_id = excluded.location_id, updated_at = excluded.updated_at
                """,
                (session["user_id"], location_id, now_iso()),
            )
        conn.commit()
    conn.close()

    return jsonify({
        "location_name": data.get("display_name", query),
        "lat": lat,
        "lon": lon,
        "rainfall_mm": rainfall_mm,
        "elevation_m": elevation_m,
        "risk_score": score,
        "risk_level": level,
        "predicted_time": pred_time,
    })


@app.route("/api/history")
def api_history() -> Any:
    raw_query = request.args.get("query", "").strip()
    if not raw_query:
        return jsonify({"error": "Missing query"}), 400

    try:
        data = fetch_geocode(raw_query)
    except requests.RequestException:
        return jsonify({"error": "Geo service unavailable"}), 503
    if not data:
        return jsonify({"error": "Location not found"}), 404

    lat = float(data["lat"])
    lon = float(data["lon"])
    if not is_within_chennai(lat, lon):
        return jsonify({"error": "Outside Chennai"}), 400

    location_id = nearest_location_id(lat, lon)
    if not location_id:
        return jsonify({"error": "No grid location"}), 404

    conn = get_db()
    loc = conn.execute(
        "SELECT elevation_m FROM locations WHERE id = ?",
        (location_id,),
    ).fetchone()
    elevation_m = float(loc["elevation_m"]) if loc else 0.0

    now_hour = current_hour_iso()
    cutoff = (chennai_now() - timedelta(days=365)).isoformat(timespec="minutes")
    rows = conn.execute(
        """
        SELECT timestamp_hour, rainfall_mm, risk_score, risk_level
        FROM hourly_weather
        WHERE location_id = ? AND timestamp_hour >= ? AND timestamp_hour <= ?
        ORDER BY timestamp_hour DESC
        """,
        (location_id, cutoff, now_hour),
    ).fetchall()
    conn.close()

    history = [
        {
            "timestamp_hour": row["timestamp_hour"],
            "rainfall_mm": row["rainfall_mm"],
            "risk_score": row["risk_score"],
            "risk_level": row["risk_level"],
        }
        for row in rows
    ]

    forecast_error = None
    forecast = []
    try:
        forecast = fetch_daily_forecast(lat, lon)
    except requests.RequestException:
        forecast = []

    history_forecast, history_note = history_based_forecast(location_id, elevation_m, lat, lon)
    if forecast:
        avg_daily = sum(item["rainfall_mm"] for item in history_forecast) / max(len(history_forecast), 1)
        blended = []
        for item in forecast:
            blended_rain = (0.7 * item["rainfall_mm"]) + (0.3 * avg_daily)
            score = risk_score_from(blended_rain, elevation_m)
            blended.append({
                "date": item["date"],
                "rainfall_mm": round(blended_rain, 2),
                "risk_score": score,
                "risk_level": risk_level_from(score),
            })
        forecast = blended
    else:
        forecast = history_forecast
        forecast_error = history_note

    return jsonify({
        "location_name": data.get("display_name", raw_query),
        "history": history,
        "forecast": forecast,
        "forecast_error": forecast_error,
    })


def bootstrap() -> None:
    init_db()
    if os.environ.get("SKIP_SEED") != "1":
        threading.Thread(target=seed_locations, daemon=True).start()
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
        start_scheduler()


bootstrap()


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
