import sqlite3
import os

def clean_duplicates():
    db_path = os.path.join("data", "misreadings.db")
    if not os.path.exists(db_path):
        return
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 全く同じ内容（video_id, timestamp, original, reading）が複数ある場合、
    # IDが一番小さいもの以外を削除する
    query = """
    DELETE FROM misreadings
    WHERE id NOT IN (
        SELECT MIN(id)
        FROM misreadings
        GROUP BY video_id, timestamp, original, reading
    )
    """
    cursor.execute(query)
    count = cursor.rowcount
    
    conn.commit()
    conn.close()
    print(f"Removed {count} duplicate rows from the database.")

if __name__ == "__main__":
    clean_duplicates()
