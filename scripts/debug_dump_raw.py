import sqlite3
import os

def dump_raw_comments():
    db_path = os.path.join("data", "misreadings.db")
    if not os.path.exists(db_path):
        print("Database not found")
        return
        
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 2/28のビデオIDを取得
    cursor.execute("SELECT video_id FROM videos WHERE upload_date LIKE '2026/02/28%'")
    row = cursor.fetchone()
    if not row:
        print("Video not found")
        return
    video_id = row[0]
    
    # RAWコメントを表示
    print(f"--- Raw Comments in DB (Video: {video_id}) ---")
    cursor.execute("SELECT original FROM misreadings WHERE video_id = ? AND context = 'RAW'", (video_id,))
    comments = cursor.fetchall()
    for c in comments:
        print(c['original'])
    conn.close()

if __name__ == "__main__":
    dump_raw_comments()
