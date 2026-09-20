import sqlite3
import os
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path=None):
        if db_path is None:
            # Default to the data directory in the project root
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(base_dir, "data", "misreadings.db")
        
        self.db_path = db_path
        db_dir = os.path.dirname(os.path.abspath(self.db_path))
        os.makedirs(db_dir, exist_ok=True)
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Initialize the database with necessary tables and constraints."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Videos table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS videos (
                    video_id TEXT PRIMARY KEY,
                    title TEXT,
                    url TEXT,
                    upload_date TEXT,
                    last_processed TEXT,
                    comment_count INTEGER DEFAULT 0
                )
            ''')
            
            # Existing DBs may predate scan-tracking. Add the column in place.
            cursor.execute("PRAGMA table_info(videos)")
            video_columns = {row[1] for row in cursor.fetchall()}
            if "last_comment_scan" not in video_columns:
                cursor.execute("ALTER TABLE videos ADD COLUMN last_comment_scan TEXT")

            # Misreadings table (The core dictionary)
            # status: 0=pending (for review), 1=approved, 2=rejected
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS misreadings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id TEXT,
                    timestamp TEXT,
                    original TEXT,
                    reading TEXT,
                    context TEXT,
                    status INTEGER DEFAULT 0, 
                    created_at TEXT,
                    FOREIGN KEY (video_id) REFERENCES videos (video_id),
                    UNIQUE(video_id, timestamp, original, reading)
                )
            ''')
            
            conn.commit()

    def add_video(self, video_id, title, url, upload_date, comment_count=0):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO videos (video_id, title, url, upload_date, last_processed, comment_count)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (video_id, title, url, upload_date, datetime.now().isoformat(), comment_count))
            conn.commit()

    def get_video_scan_state(self, video_id):
        """Return comment-scan metadata without treating the DB as source of truth."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT comment_count, last_comment_scan FROM videos WHERE video_id = ?",
                (video_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def record_video_scan(self, video_id, title, url, upload_date, comment_count):
        """Record a completed YouTube comment scan for incremental re-checks."""
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO videos
                    (video_id, title, url, upload_date, last_processed, comment_count, last_comment_scan)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(video_id) DO UPDATE SET
                    title = excluded.title,
                    url = excluded.url,
                    upload_date = excluded.upload_date,
                    last_processed = excluded.last_processed,
                    comment_count = excluded.comment_count,
                    last_comment_scan = excluded.last_comment_scan
            ''', (video_id, title, url, upload_date, now, comment_count, now))
            conn.commit()

    def is_video_processed(self, video_id, current_comment_count=None):
        """Check if a video has already been fully processed."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if current_comment_count is not None:
                # コメント数に変化がない場合も「処理済み」とみなす
                cursor.execute('SELECT 1 FROM videos WHERE video_id = ? AND comment_count = ?', (video_id, current_comment_count))
            else:
                cursor.execute('SELECT 1 FROM videos WHERE video_id = ?', (video_id,))
            return cursor.fetchone() is not None

    def has_misreadings(self, video_id):
        """Check if any misreadings are extracted for this video."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM misreadings WHERE video_id = ?', (video_id,))
            return cursor.fetchone() is not None

    def clear_video_record(self, video_id):
        """Remove a video record to allow re-processing."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM videos WHERE video_id = ?', (video_id,))
            conn.commit()

    def add_misreading(self, video_id, timestamp, original, reading, context, status=0):
        """Add a new misreading entry with duplicate prevention."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR IGNORE INTO misreadings (video_id, timestamp, original, reading, context, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (video_id, timestamp, original, reading, context, status, datetime.now().isoformat()))
                conn.commit()
                return cursor.rowcount > 0 # 新しく挿入されたらTrue
        except sqlite3.Error as e:
            print(f"DB Error in add_misreading: {e}")
            return False

    def get_pending_reviews(self):
        """Fetch all misreadings waiting for human approval."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT m.*, v.title as video_title, v.url as video_url 
                FROM misreadings m
                JOIN videos v ON m.video_id = v.video_id
                WHERE m.status = 0
                ORDER BY v.upload_date DESC, m.timestamp ASC
            ''')
            return [dict(row) for row in cursor.fetchall()]

    def update_status(self, misreading_id, status):
        """Approve (1) or Reject (2) a misreading."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE misreadings SET status = ? WHERE id = ?', (status, misreading_id))
            conn.commit()

    def get_approved_data(self):
        """Get all approved misreadings for WebApp generation."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT m.*, v.title as video_title, v.url as video_url, v.upload_date
                FROM misreadings m
                JOIN videos v ON m.video_id = v.video_id
                WHERE m.status = 1
                ORDER BY v.upload_date DESC, m.timestamp ASC
            ''')
            return [dict(row) for row in cursor.fetchall()]

if __name__ == "__main__":
    # Simple test
    db = DatabaseManager()
    print("Database initialized at:", db.db_path)
