import sqlite3
import os
from datetime import datetime

def fix_2026_02_28_misreadings():
    db_path = os.path.join("data", "misreadings.db")
    if not os.path.exists(db_path):
        print("Database not found")
        return
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. 見本の動画を特定（2026/02/28）
    target_date = "2026/02/28"
    cursor.execute("SELECT video_id FROM videos WHERE upload_date LIKE ?", (target_date + "%",))
    row = cursor.fetchone()
    if not row:
        # もし日付形式が YYYYMMDD の場合
        target_date_raw = "20260228"
        cursor.execute("SELECT video_id FROM videos WHERE upload_date = ?", (target_date_raw,))
        row = cursor.fetchone()
        
    if not row:
        print("Video for 2026/02/28 not found in DB")
        conn.close()
        return
    
    video_id = row[0]
    print(f"Adding misreadings for Video ID: {video_id}")
    
    # 2. 指定された4件の誤読を承認済み(status=1)で追加
    new_items = [
        ("1:16:16", "耐荷重", "たいにじゅう", ""),
        ("1:46:41", "案内板", "あんなんばん", ""),
        ("1:48:11", "狙撃", "だげき", ""),
        ("3:37:11", "暁光", "あかつきひかり", "")
    ]
    
    # 既存のRAWデータ(status=0)があれば消しておくと重複しない
    cursor.execute("DELETE FROM misreadings WHERE video_id = ? AND status = 0", (video_id,))
    
    for ts, orig, reading, ctx in new_items:
        cursor.execute('''
            INSERT INTO misreadings (video_id, timestamp, original, reading, context, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (video_id, ts, orig, reading, ctx, 1, datetime.now().isoformat()))
        
    conn.commit()
    conn.close()
    print("Successfully added 4 misreadings for 2026/02/28.")

if __name__ == "__main__":
    fix_2026_02_28_misreadings()
