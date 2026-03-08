import sqlite3
import os
import re

def analyze():
    db_path = os.path.join("data", "misreadings.db")
    exclude_path = "exclude_keywords.txt"
    
    if not os.path.exists(db_path):
        print("Database not found.")
        return

    # 除外キーワードの読み込み
    exclude_keywords = []
    if os.path.exists(exclude_path):
        with open(exclude_path, "r", encoding="utf-8") as f:
            exclude_keywords = [line.strip() for line in f if line.strip()]

    # 正規表現: タイムスタンプ ひらがな (元の言葉)
    pattern = re.compile(
        r'(?P<timestamp>\d{1,2}:\d{2}(?::\d{2})?)'           # タイムスタンプ
        r'\s+'                                               # スペース
        r'(?P<reading>[ぁ-んー]+)'                             # 読み（ひらがな限定）
        r'\s*[\(（]'                                         # 括弧
        r'(?P<original>[^）\)\s]+)'                           # 原文
        r'[\)）]'                                            # 閉じ
    )

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # RAWデータ（status=0 かつ context='RAW'）を取得
    cursor.execute("""
        SELECT m.id, v.title, m.original as raw_text, v.upload_date, m.video_id
        FROM misreadings m
        JOIN videos v ON m.video_id = v.video_id
        WHERE m.status = 0 AND m.context = 'RAW'
        ORDER BY v.upload_date DESC
    """)
    rows = cursor.fetchall()

    results = []
    for row in rows:
        lines = row['raw_text'].split('\n')
        for line in lines:
            line = line.strip()
            if not line: continue
            
            # 除外キーワードチェック
            if any(kw in line for kw in exclude_keywords):
                continue
                
            match = pattern.search(line)
            if match:
                results.append({
                    'id': row['id'],
                    'video': row['title'],
                    'date': row['upload_date'],
                    'timestamp': match.group('timestamp'),
                    'reading': match.group('reading'),
                    'original': match.group('original')
                })

    conn.close()

    # 表示
    if not results:
        print("MATCH_NOT_FOUND")
        return

    current_video = ""
    for item in results:
        if current_video != item['video']:
            print(f"\n📺 {item['video']} ({item['date']})")
            current_video = item['video']
        print(f"  - {item['timestamp']} | {item['original']} -> {item['reading']}")

if __name__ == "__main__":
    analyze()
