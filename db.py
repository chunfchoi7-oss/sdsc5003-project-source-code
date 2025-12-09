"""Database connection configuration and helpers."""

from dataclasses import dataclass
import os
import psycopg2
from psycopg2.extensions import connection as PGConnection


@dataclass(frozen=True)
class DBConfig:
    """Represent database settings."""

    dbname: str
    user: str
    password: str
    host: str
    port: int


def load_config() -> DBConfig:
    """Load configuration from environment variables."""

    return DBConfig(
        dbname=os.getenv("POSTGRES_DB", "expense_db"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "123456"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
    )


def get_connection() -> PGConnection:
    """Create a new psycopg2 connection."""

    config = load_config()
    return psycopg2.connect(
        dbname=config.dbname,
        user=config.user,
        password=config.password,
        host=config.host,
        port=config.port,
    )


def db_time() -> str:
    """Fetch current timestamp from the database."""

    conn: PGConnection | None = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT NOW()")
            row = cur.fetchone()
            return str(row[0]) if row else "unknown"
    finally:
        if conn is not None:
            conn.close()
