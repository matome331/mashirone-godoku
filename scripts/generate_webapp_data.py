import sqlite3
import os
import json
from datetime import datetime

# 承認されたmisreadingsを取得してweb用のdata.jsを生成
def generate_web_data():
    db_path = os.path.join("data", "misreadings.db")
    if not os.path.exists(db_path):
        print("Database not found")
        return
        
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 承認済み(status=1)の全データを取得
    query = """
    SELECT m.timestamp, m.original, m.reading, m.context, v.title as video_title, v.url as video_url, v.upload_date
    FROM misreadings m
    JOIN videos v ON m.video_id = v.video_id
    WHERE m.status = 1
    ORDER BY v.upload_date DESC, m.timestamp DESC
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    
    misreadings = []
    for row in rows:
        misreadings.append({
            "timestamp": row["timestamp"],
            "original": row["original"],
            "reading": row["reading"],
            "context": row["context"] or "",
            "video_title": row["video_title"],
            "video_url": row["video_url"],
            "video_date": row["upload_date"]
        })
    
    # data.js を書き出し
    js_content = f"const MISREADING_DATA = {json.dumps(misreadings, ensure_ascii=False, indent=2)};"
    output_path = os.path.join("webapp", "data.js")
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(js_content)
    
    print(f"Successfully generated Web data: {len(misreadings)} items.")
    conn.close()

if __name__ == "__main__":
    generate_web_data()
