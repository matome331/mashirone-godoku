from core.database import DatabaseManager
from core.extractor import YouTubeExtractor
from core.processor import MisreadingProcessor
import time
import sqlite3

# 真白猫ミミィ / vtuber
CHANNEL_URL = "https://www.youtube.com/@mashi_rone/streams"
TARGET_AUTHOR = "@ageha1st"

def sync_channel():
    db = DatabaseManager()
    extractor = YouTubeExtractor()
    processor = MisreadingProcessor()
    
    # 基準日: 2026/02/20
    THRESHOLD_DATE = "2026/02/20"

    print(f"--- チャンネルの最新動画を確認中: {CHANNEL_URL} ---")
    video_ids = extractor.get_recent_video_ids(CHANNEL_URL, max_results=20)
    
    if not video_ids:
        print("動画が見つかりませんでした。")
        return

    all_found_items = []
    
    for video_id in video_ids:
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        # 1. 動画情報の取得 (メン限や予定地のエラーは内部で処理)
        info = extractor.get_video_info(video_url, silent_error=True)
        if not info:
            continue
            
        title = info.get('title', '')
        
        # 配信予定地・メン限をスキップ
        if info.get('live_status') == 'is_upcoming' or "メン限" in title:
            continue

        upload_date_raw = info.get('upload_date')
        if upload_date_raw and len(upload_date_raw) == 8:
            upload_date = f"{upload_date_raw[:4]}/{upload_date_raw[4:6]}/{upload_date_raw[6:]}"
        else:
            upload_date = "0000/00/00"
        
        # 日付フィルタ (2026/02/20 以降のみ)
        if upload_date < THRESHOLD_DATE:
            continue

        # 履歴があっても「未承認(status=0)」の項目であれば一度消して再解析する
        # これにより、ルールの変更を過去の動画にも適用できます。
        with db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM misreadings WHERE video_id = ? AND status = 0", (video_id,))
            conn.commit()

        print(f"\nScanning: {title} ({upload_date})")
        
        # 2. コメントを抽出
        filtered_comments, total_count = extractor.extract_comments(video_url, target_author=TARGET_AUTHOR)
        
        # 3. その場で解析
        items = processor.parse_comments(filtered_comments)
        
        if items:
            # 動画情報を保存/更新
            db.add_video(video_id, title, video_url, upload_date)
            
            new_added = 0
            for item in items:
                # 重複登録を防ぎつつ追加
                db.add_misreading(video_id, item['timestamp'], item['original'], item['reading'], item['context'])
                all_found_items.append({
                    'video': title,
                    'date': upload_date,
                    'timestamp': item['timestamp'],
                    'original': item['original'],
                    'reading': item['reading']
                })
                new_added += 1
            print(f"  -> {total_count}件のコメント中、誤読候補を {new_added} 件検出しました！")
        else:
            # 誤読がなくても動画の処理済みフラグだけは立てる
            db.add_video(video_id, title, video_url, upload_date)
            if total_count > 0:
                print(f"  -> {total_count}件のコメントをチェックしましたが、該当なし。")

        time.sleep(1)

    # 最終結果の表示
    if all_found_items:
        print("\n" + "="*60)
        print(" 🎉 解析完了：最新の誤読候補は以下の通りです")
        print("="*60)
        # 同じ動画の項目が続く場合は動画タイトルを省略して見やすく表示
        current_video = ""
        for i, item in enumerate(all_found_items, 1):
            if current_video != item['video']:
                print(f"\n 📺 {item['video']}")
                print(f"    ({item['date']})")
                current_video = item['video']
            
            print(f"   {i:2}. {item['timestamp']} | {item['original']} -> {item['reading']}")
        
        print("\n" + "="*60)
        print(" これらの内容をWebアプリに反映させるには、Antigravityに指示してください。")
    else:
        print("\n解析完了：条件に合う新しい誤読候補は見つかりませんでした。")

if __name__ == "__main__":
    sync_channel()
