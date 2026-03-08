import sqlite3
import os
import re

def cleanup_junk():
    db_path = os.path.join("data", "misreadings.db")
    if not os.path.exists(db_path):
        return
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 全データを一度取得して、Python側でゴミ判定を行う
    cursor.execute("SELECT id, reading, original FROM misreadings")
    rows = cursor.fetchall()
    
    # 判定ルール: 読み(reading) または 原文(original) が
    # 「時間(12:34)」や「日付(2/22)」や「単なる数字」だけのものはゴミとする
    junk_pattern = re.compile(r'^[\d:\./ \-]+$')
    
    junk_ids = []
    for row_id, reading, original in rows:
        r_str = str(reading or "")
        o_str = str(original or "")
        
        if junk_pattern.match(r_str) or junk_pattern.match(o_str):
            junk_ids.append(row_id)
        # そもそも文字数が少なすぎる、または空のものも除外
        elif len(r_str) == 0 or len(o_str) == 0:
            junk_ids.append(row_id)

    if junk_ids:
        # 1000件ずつなどに分割せずに一括で削除
        placeholders = ','.join(['?'] * len(junk_ids))
        cursor.execute(f"DELETE FROM misreadings WHERE id IN ({placeholders})", junk_ids)
        print(f"Cleaned up {len(junk_ids)} junk entries (timestamps/titles).")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    cleanup_junk()
