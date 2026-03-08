import sqlite3
import os

def cleanup_db():
    db_path = os.path.join("data", "misreadings.db")
    if not os.path.exists(db_path):
        return
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 未承認(status=0)のデータをすべて削除して、次の解析でクリーンな状態にする
    cursor.execute("DELETE FROM misreadings WHERE status = 0")
    
    # レポートファイルも一度空にする（追記モードなので、以前の誤った解析結果を消すため）
    report_path = "misreadings_report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("【真白猫ミミィ 誤読解析レポート（再解析版）】\n\n")

    conn.commit()
    conn.close()
    print("Database and report cleared for re-analysis.")

if __name__ == "__main__":
    cleanup_db()
