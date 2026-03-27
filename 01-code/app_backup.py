from __future__ import annotations

import os
import smtplib
import sqlite3
import threading
import time
import math
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
DB_PATH = Path(os.environ.get("DB_PATH", BASE_DIR / "flood.db"))

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me-in-production")

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
ROUTE_GRAPH_LOCK = threading.Lock()
ROUTE_GRAPH = None
ROUTE_GRAPH_TS = 0.0
POI_CACHE = []
POI_CACHE_TS = 0.0

# ...existing code...