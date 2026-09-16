import sqlite3
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path("data/japan_hunt.db")

def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def now():
    return datetime.now(timezone.utc).isoformat()

def init_db():
    with connect() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS reddit_mentions(
            id TEXT PRIMARY KEY, title TEXT, text TEXT, url TEXT,
            created_utc REAL, query TEXT, product_key TEXT, collected_at TEXT
        );
        CREATE TABLE IF NOT EXISTS products(
            product_id TEXT PRIMARY KEY, name TEXT, price_jpy REAL, url TEXT,
            image TEXT, availability TEXT, is_new INTEGER, is_restock INTEGER,
            is_preorder INTEGER, first_seen TEXT, last_seen TEXT
        );
        CREATE TABLE IF NOT EXISTS product_history(
            id INTEGER PRIMARY KEY AUTOINCREMENT, product_id TEXT, name TEXT,
            price_jpy REAL, availability TEXT, collected_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_mentions_key
        ON reddit_mentions(product_key);
        """)

def save_mention(m):
    with connect() as c:
        c.execute(
            "INSERT OR IGNORE INTO reddit_mentions VALUES(?,?,?,?,?,?,?,?)",
            (m["id"],m["title"],m["text"],m["url"],m["created_utc"],
             m["query"],m["product_key"],now())
        )

def upsert_product(p):
    with connect() as c:
        old = c.execute(
            "SELECT product_id FROM products WHERE product_id=?",
            (p["product_id"],)
        ).fetchone()
        if old:
            c.execute("""
            UPDATE products SET name=?,price_jpy=?,url=?,image=?,
            availability=?,is_new=?,is_restock=?,is_preorder=?,last_seen=?
            WHERE product_id=?
            """, (p["name"],p["price_jpy"],p["url"],p["image"],
                  p["availability"],int(p["is_new"]),int(p["is_restock"]),
                  int(p["is_preorder"]),now(),p["product_id"]))
        else:
            c.execute(
                "INSERT INTO products VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (p["product_id"],p["name"],p["price_jpy"],p["url"],p["image"],
                 p["availability"],int(p["is_new"]),int(p["is_restock"]),
                 int(p["is_preorder"]),now(),now())
            )
        c.execute("""
        INSERT INTO product_history
        (product_id,name,price_jpy,availability,collected_at)
        VALUES(?,?,?,?,?)
        """, (p["product_id"],p["name"],p["price_jpy"],
              p["availability"],now()))

def get_products():
    with connect() as c:
        return [dict(x) for x in c.execute("SELECT * FROM products").fetchall()]

def get_mention_counts():
    with connect() as c:
        return {
            x["product_key"]: x["n"]
            for x in c.execute(
                "SELECT product_key,COUNT(*) n FROM reddit_mentions GROUP BY product_key"
            ).fetchall()
        }
