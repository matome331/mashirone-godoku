import sqlite3
import os

db_path = r"c:\Users\grave\yt-comments\data\misreadings.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

vid = "_Pw0MkEp0do"
cursor.execute("SELECT upload_date, title FROM videos WHERE video_id = ?", (vid,))
row = cursor.fetchone()
print(f"Video ID: {vid}")
if row:
    print(f"Upload Date: {row[0]}")
    print(f"Title: {row[1]}")
else:
    print("Not found in videos table")

# Check if it exists in misreadings table
cursor.execute("SELECT COUNT(*), status FROM misreadings WHERE video_id = ? GROUP BY status", (vid,))
rows = cursor.fetchall()
print(f"\nIn misreadings table for {vid}:")
for r in rows:
    print(f" Count: {r[0]}, Status: {r[1]}")

conn.close()
