import sqlite3
import os

db_path = r"c:\Users\grave\yt-comments\data\misreadings.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("Sample from videos table:")
cursor.execute("SELECT video_id, title, upload_date FROM videos LIMIT 5")
for row in cursor.fetchall():
    print(row)

print("\nSample from misreadings table:")
cursor.execute("SELECT video_id, status FROM misreadings LIMIT 5")
for row in cursor.fetchall():
    print(row)

conn.close()
