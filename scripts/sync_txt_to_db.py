import re
import json
import os
import sqlite3
from datetime import datetime
from core.database import DatabaseManager

def sync_txt_to_db():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    refined_path = os.path.join(base_dir, "mimy_misreadings_refined.txt")
    db = DatabaseManager()
    
    if not os.path.exists(refined_path):
        print(f"Error: {refined_path} not found.")
        return

    with open(refined_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 動画セクションごとに分割
    sections = re.split(r'【動画】', content)
    
    # 1. 既存の承認済みデータを一旦すべて非承認(status=0)にするか、
    # あるいはシンプルに「テキストにあるものを status=1 に更新、ないものは status=0 に戻す」
    # ここでは「テキストにあるもの＝正解」として同期する
    
    with db._get_connection() as conn:
        cursor = conn.cursor()
        # 一旦すべての承認済み(1)を保留(0)にリセット
        cursor.execute("UPDATE misreadings SET status = 0 WHERE status = 1")
        
        count = 0
        for section in sections:
            if not section.strip(): continue
            
            # タイトルと日付
            lines = section.strip().split('\n')
            title_line = lines[0]
            title_match = re.search(r'(.+?)\s*\((\d{4}/\d{2}/\d{2})\)', title_line)
            if not title_match: continue
            
            video_title = title_match.group(1).strip()
            video_date = title_match.group(2)
            
            # URL抽出
            url_match = re.search(r'URL:\s*(https?://[^\s\n]+)', section)
            if not url_match: continue
            video_url = url_match.group(1).split('&t=')[0].split('?t=')[0]
            video_id_match = re.search(r'v=([^&]+)', video_url)
            video_id = video_id_match.group(1) if video_id_match else video_url
            
            # 動画情報を更新
            cursor.execute('''
                INSERT OR REPLACE INTO videos (video_id, title, url, upload_date, last_processed)
                VALUES (?, ?, ?, ?, ?)
            ''', (video_id, video_title, video_url, video_date, datetime.now().isoformat()))
            
            # 誤読行の抽出
            misread_pattern = re.compile(r'(\d{1,2}:\d{2}(?::\d{2})?)\s*-\s*([^（(]+)[（(](.+?)[）)]')
            
            for line in lines:
                m = misread_pattern.search(line)
                if m:
                    ts = m.group(1)
                    reading = m.group(2).strip()
                    original = m.group(3).strip()
                    
                    cursor.execute("""
                        INSERT INTO misreadings (video_id, timestamp, original, reading, status, created_at)
                        VALUES (?, ?, ?, ?, 1, ?)
                        ON CONFLICT(video_id, timestamp, original, reading) 
                        DO UPDATE SET status = 1
                    """, (video_id, ts, original, reading, datetime.now().isoformat()))
                    count += 1

        conn.commit()
    
    print(f"[SUCCESS] データベース更新完了: {count} 件の誤読を承認済み(status=1)に設定しました。")
    
    # 2. Webアプリ用 data.js の生成
    approved_data = db.get_approved_data()
    
    def get_seconds(ts):
        try:
            parts = ts.split(':')
            if len(parts) == 3: return int(parts[0])*3600 + int(parts[1])*60 + int(parts[2])
            return int(parts[0])*60 + int(parts[1])
        except: return 0

    web_list = []
    for row in approved_data:
        # URLの再構成（タイムスタンプ付き）
        sec = get_seconds(row['timestamp'])
        jump_url = f"{row['video_url']}&t={sec}s"
        
        web_list.append({
            "timestamp": row['timestamp'],
            "original": row['original'],
            "reading": row['reading'],
            "context": row['context'] or "",
            "videoTitle": row['video_title'],
            "videoUrl": jump_url,
            "date": row['upload_date']
        })
    
    js_content = f"const dictionaryData = {json.dumps(web_list, ensure_ascii=False, indent=2)};"
    output_path = os.path.join(base_dir, "webapp", "data.js")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(js_content)
    
    print(f"[SUCCESS] Webアプリ更新完了: {len(web_list)} 件のデータを公開しました。")

if __name__ == "__main__":
    sync_txt_to_db()
