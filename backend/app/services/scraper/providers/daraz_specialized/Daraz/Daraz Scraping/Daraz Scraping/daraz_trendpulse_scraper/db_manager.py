import sqlite3
import json
from config import DB_FILENAME
from logger import logger

class DatabaseManager:
    """Manages SQLite persistence, deduplication checkpoints, and queue state."""
    def __init__(self, db_path=DB_FILENAME):
        self.conn = sqlite3.connect(db_path)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS crawled_products (
                product_id TEXT PRIMARY KEY,
                url TEXT UNIQUE,
                title TEXT,
                current_price TEXT,
                brand TEXT,
                seller_name TEXT,
                seller_id TEXT,
                raw_json TEXT,
                crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS crawl_queue (
                url TEXT PRIMARY KEY,
                status TEXT DEFAULT 'PENDING',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

    def is_already_crawled(self, product_id: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM crawled_products WHERE product_id = ?", (product_id,))
        return cursor.fetchone() is not None

    def save_product(self, product_data: dict):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO crawled_products (product_id, url, title, current_price, brand, seller_name, seller_id, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            product_data.get("product_id", "UNKNOWN"),
            product_data.get("url", ""),
            product_data.get("title", ""),
            product_data.get("current_price", ""),
            product_data.get("brand", ""),
            product_data.get("seller_name", ""),
            product_data.get("seller_id", "N/A"),
            json.dumps(product_data, ensure_ascii=False)
        ))
        self.conn.commit()
        logger.info(f"Product checkpoint saved: ID {product_data.get('product_id')}")

    # =====================================================================
    # QUEUE & RESUME RESILIENCY IMPLEMENTATION
    # =====================================================================
    def queue_product_url(self, url):
        """Queues a URL for crawling. De-duplicates via SQLite constraints."""
        cursor = self.conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO crawl_queue (url, status) VALUES (?, 'PENDING')", (url,))
        self.conn.commit()

    def get_next_queued_url(self):
        """Fetches the next pending product URL."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT url FROM crawl_queue WHERE status = 'PENDING' LIMIT 1")
        row = cursor.fetchone()
        return row[0] if row else None

    def update_queue_status(self, url, status):
        """Updates the queue status (PENDING/COMPLETED/FAILED)."""
        cursor = self.conn.cursor()
        cursor.execute("UPDATE crawl_queue SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE url = ?", (status.upper(), url))
        self.conn.commit()

    def get_queue_stats(self):
        """Returns statistics of the current queue."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT status, COUNT(*) FROM crawl_queue GROUP BY status")
        stats = dict(cursor.fetchall())
        return {
            "pending": stats.get("PENDING", 0),
            "completed": stats.get("COMPLETED", 0),
            "failed": stats.get("FAILED", 0)
        }

    def clear_queue(self):
        """Clears the queue table."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM crawl_queue")
        self.conn.commit()

    def get_all_crawled_products(self):
        """Retrieves raw_json content for all products scraped."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT raw_json FROM crawled_products")
        return [json.loads(row[0]) for row in cursor.fetchall()]

    def close(self):
        self.conn.close()
