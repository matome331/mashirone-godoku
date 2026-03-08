from core.database import DatabaseManager
import os
import sys

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def review_loop():
    db = DatabaseManager()
    pending = db.get_pending_reviews()
    
    if not pending:
        print("現在、承認待ちの項目はありません。")
        return

    print(f"--- 承認待ちの項目: {len(pending)} 件 ---\n")
    
    for i, item in enumerate(pending):
        clear_screen()
        print(f"[{i+1}/{len(pending)}] レビュー中")
        print("-" * 40)
        print(f"動画: {item['video_title']}")
        print(f"時間: {item['timestamp']}")
        print(f"原文: {item['original']}")
        print(f"読込: {item['reading']}")
        if item['context']:
            print(f"補足: {item['context']}")
        print("-" * 40)
        
        while True:
            choice = input("\n[A]承認 [R]却下 [S]スキップ [Q]終了: ").lower()
            if choice == 'a':
                db.update_status(item['id'], 1)
                print("承認しました。")
                break
            elif choice == 'r':
                db.update_status(item['id'], 2)
                print("却下しました。")
                break
            elif choice == 's':
                print("スキップしました。")
                break
            elif choice == 'q':
                print("レビューを終了します。")
                return
            else:
                print("無効な入力です。")

    print("\n全てのレビューが完了しました！")

if __name__ == "__main__":
    try:
        review_loop()
    except KeyboardInterrupt:
        print("\n中断されました。")
