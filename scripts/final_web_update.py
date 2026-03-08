import sqlite3
import os
import json
from datetime import datetime

# 1. データベースを「承認済み」に更新
# 2. 最新の全データを取得して webapp/data.js を作成
def update_web():
    db_path = os.path.join("data", "misreadings.db")
    if not os.path.exists(db_path):
        print("Database not found")
        return
        
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 0. 無視リストの読み込み
    exclude_path = "exclude_keywords.txt"
    exclude_keywords = []
    if os.path.exists(exclude_path):
        with open(exclude_path, "r", encoding="utf-8") as f:
            exclude_keywords = [line.strip() for line in f if line.strip()]

    # 1. データベースにある未承認(status=0)のものをすべてチェックして承認
    cursor.execute("SELECT id, original, reading FROM misreadings WHERE status = 0")
    to_approve = cursor.fetchall()
    approve_ids = []
    for row in to_approve:
        if not any(kw in str(row["original"]) or kw in str(row["reading"]) for kw in exclude_keywords):
            approve_ids.append(row["id"])
    
    if approve_ids:
        placeholders = ','.join(['?'] * len(approve_ids))
        cursor.execute(f"UPDATE misreadings SET status = 1 WHERE id IN ({placeholders})", approve_ids)
    conn.commit()
    
    # 全承認済みデータの取得（表示順：日付降順、タイムスタンプ昇順）
    query = """
    SELECT m.timestamp, m.original, m.reading, m.context, v.title as video_title, v.url as video_url, v.upload_date
    FROM misreadings m
    JOIN videos v ON m.video_id = v.video_id
    WHERE m.status = 1
    ORDER BY v.upload_date DESC, m.timestamp ASC
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    
    def get_seconds(ts):
        try:
            parts = ts.split(':')
            if len(parts) == 3: return int(parts[0])*3600 + int(parts[1])*60 + int(parts[2])
            if len(parts) == 2: return int(parts[0])*60 + int(parts[1])
            return int(parts[0])
        except: return 0

    misreadings = []
    for row in rows:
        # 最終的なJS書き出し時にも無視リストをもう一度確認
        if any(kw in str(row["original"]) or kw in str(row["reading"]) for kw in exclude_keywords):
            continue
            
        # タイムスタンプ付きURLの生成
        base_url = str(row["video_url"]).split('&t=')[0].split('?t=')[0]
        timestamp = str(row["timestamp"])
        sec = get_seconds(timestamp)
        sep = "&" if "?" in base_url else "?"
        jump_url = f"{base_url}{sep}t={sec}s"
            
        misreadings.append({
            "timestamp": timestamp,
            "original": row["original"],
            "reading": row["reading"],
            "context": row["context"] or "",
            "videoTitle": row["video_title"],
            "videoUrl": jump_url,
            "date": row["upload_date"]
        })
    
    # webapp/data.js を書き出し (app.js が期待する dictionaryData に合わせる)
    js_content = f"const dictionaryData = {json.dumps(misreadings, ensure_ascii=False, indent=2)};"
    output_path = os.path.join("docs", "data.js")
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(js_content)
    
    print(f"Successfully updated Web data with {len(misreadings)} items.")
    conn.close()

if __name__ == "__main__":
    update_web()
