# config.py
# Runtime configuration: ALL secrets come from environment variables.
# Optional: a local .env can be used in development; it must NOT be committed.
import os
from pathlib import Path

# Load variables from a local .env if it exists (dev convenience only).
if Path(".env").exists():
    try:
        from dotenv import load_dotenv  # pip install python-dotenv (optional)
        load_dotenv()
    except Exception:
        # Ignore if python-dotenv is missing; real env must be set in prod.
        pass

# --- REQUIRED SECRETS ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN is not set")

# --- OPTIONAL SETTINGS ---
# DB: override with DATABASE_URL in env; fallback to local SQLite for dev
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///aquarium_bot.db")

# Timezone: default to Kazan (MSK, UTC+3)
TZ = os.getenv("TZ", "Europe/Moscow")