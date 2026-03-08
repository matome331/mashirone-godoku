import sqlite3
import os
import json

def dump_for_ai():
    db_path = os.path.join("data", "misreadings.db")
    if not os.path.exists(db_path):
        print("Database not found")
        return
        
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 全動画と全誤読データを取得
    cursor.execute("""
        SELECT m.*, v.title, v.upload_date 
        FROM misreadings m 
        JOIN videos v ON m.video_id = v.video_id
        ORDER BY v.upload_date DESC
    """)
    rows = [dict(row) for row in cursor.fetchall()]
    
    with open("db_dump.json", "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
        
    print(f"Successfully dumped {len(rows)} records to db_dump.json")
    conn.close()

if __name__ == "__main__":
    dump_for_ai()
