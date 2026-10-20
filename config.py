import os

# ─────────────────────────────────────────────────────────────────────────────
# PostgreSQL connection settings
# Values are read from environment variables when set (e.g. in Docker),
# and fall back to the local defaults when they are not.
# ─────────────────────────────────────────────────────────────────────────────
DB_HOST     = os.getenv("DB_HOST",     "localhost")
DB_PORT     = int(os.getenv("DB_PORT", 5432))
DB_NAME     = os.getenv("DB_NAME",     "network_monitoring")   # your database name
DB_USER     = os.getenv("DB_USER",     "postgres")             # your PostgreSQL username
DB_PASSWORD = os.getenv("DB_PASSWORD", "samir123")             # your PostgreSQL password

# Flask secret key (used for session/flash messages)
SECRET_KEY = os.urandom(24)
