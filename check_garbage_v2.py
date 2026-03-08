import sqlite3
import os

db_path = r"c:\Users\grave\yt-comments\data\misreadings.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

target_date = '2026/02/19'

# Count status=0 for target date
cursor.execute("""
    SELECT COUNT(*) 
    FROM misreadings m 
    JOIN videos v ON m.video_id = v.video_id 
    WHERE v.upload_date = ? AND m.status = 0
""", (target_date,))
count = cursor.fetchone()[0]

# Count status=1 for target date
cursor.execute("""
    SELECT COUNT(*) 
    FROM misreadings m 
    JOIN videos v ON m.video_id = v.video_id 
    WHERE v.upload_date = ? AND m.status = 1
""", (target_date,))
confirm_count = cursor.fetchone()[0]

print(f"Target date: {target_date}")
print(f"Status=0 (garbage) count: {count}")
print(f"Status=1 (keep) count: {confirm_count}")

# List some garbage for manual verification
cursor.execute("""
    SELECT m.original, m.reading, v.title
    FROM misreadings m 
    JOIN videos v ON m.video_id = v.video_id 
    WHERE v.upload_date = ? AND m.status = 0
    LIMIT 5
""", (target_date,))
garbage_samples = cursor.fetchall()
print("\nGarbage samples:")
for g in garbage_samples:
    print(f" - {g[0]} -> {g[1]} ({g[2]})")

conn.close()
