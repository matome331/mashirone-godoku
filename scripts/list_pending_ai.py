import sqlite3
import os

def get_pending_items():
    db_path = os.path.join("data", "mimy_wiki.db")
    if not os.path.exists(db_path):
        return []
        
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 未承認(status=0)のデータを取得（動画情報も結合）
    query = """
    SELECT m.id, v.title, m.timestamp, m.original, m.reading, m.context, v.date
    FROM misreadings m
    JOIN videos v ON m.video_id = v.video_id
    WHERE m.status = 0
    ORDER BY v.date DESC, m.timestamp ASC
    """
    cursor.execute(query)
    items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return items

if __name__ == "__main__":
    items = get_pending_items()
    for item in items:
        print(f"ID:{item['id']} | {item['date']} | {item['timestamp']} | {item['original']} -> {item['reading']} | {item['title']}")
