import sqlite3
import os

def check_videos():
    db_path = os.path.join("data", "mimy_wiki.db")
    if not os.path.exists(db_path):
        print("Database not found")
        return
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT video_id, title, date FROM videos WHERE date LIKE '2026/02/28%'")
    rows = cursor.fetchall()
    for row in rows:
        print(f"ID: {row[0]} | Title: {row[1]} | Date: {row[2]}")
    conn.close()

if __name__ == "__main__":
    check_videos()
