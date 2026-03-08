import sqlite3
import os

def enforce_ignore_list():
    db_path = os.path.join("data", "misreadings.db")
    exclude_path = "exclude_keywords.txt"
    if not os.path.exists(db_path) or not os.path.exists(exclude_path):
        return
        
    with open(exclude_path, "r", encoding="utf-8") as f:
        keywords = [line.strip() for line in f if line.strip()]

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    total_deleted = 0
    for kw in keywords:
        # 原文(original) または 読み(reading) にキーワードが含まれるものを削除
        cursor.execute("DELETE FROM misreadings WHERE original LIKE ? OR reading LIKE ?", (f"%{kw}%", f"%{kw}%"))
        total_deleted += cursor.rowcount
    
    conn.commit()
    conn.close()
    print(f"Cleanup finished: Deleted {total_deleted} rows matching items in exclude_keywords.txt")

if __name__ == "__main__":
    enforce_ignore_list()
