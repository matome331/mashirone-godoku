import sqlite3
import os

def clear_pending():
    db_path = os.path.join("data", "mimy_wiki.db")
    if not os.path.exists(db_path):
        print("データベースが見つかりません。")
        return
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 承認待ち(status=0)の誤読データを削除
    cursor.execute("DELETE FROM misreadings WHERE status = 0")
    deleted_count = cursor.rowcount
    
    # 履歴管理(videos)も一度リセットして再スキャンできるようにする
    cursor.execute("DELETE FROM videos")
    
    conn.commit()
    conn.close()
    print(f"成功: {deleted_count} 件の未承認データを削除し、動画履歴をリセットしました。")

if __name__ == "__main__":
    clear_pending()
