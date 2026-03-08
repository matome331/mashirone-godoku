import sqlite3
import os

db_path = r"c:\Users\grave\yt-comments\data\misreadings.db"

if not os.path.exists(db_path):
    print(f"Error: Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Count target records
target_date = '2026/02/19'
cursor.execute("SELECT COUNT(*) FROM misreadings WHERE upload_date = ? AND status = 0", (target_date,))
count = cursor.fetchone()[0]

print(f"Target date: {target_date}")
print(f"Count of status=0 (garbage) records: {count}")

# Check status=1 for same date (safety check)
cursor.execute("SELECT COUNT(*) FROM misreadings WHERE upload_date = ? AND status = 1", (target_date,))
confirm_count = cursor.fetchone()[0]
print(f"Count of status=1 (keep) records: {confirm_count}")

conn.close()
