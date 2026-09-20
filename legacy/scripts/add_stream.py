from core.database import DatabaseManager
from core.extractor import YouTubeExtractor
from core.processor import MisreadingProcessor
import sys
import os

def main(video_url):
    db = DatabaseManager()
    extractor = YouTubeExtractor()
    processor = MisreadingProcessor()

    print(f"--- 動画情報の取得中: {video_url} ---")
    info = extractor.get_video_info(video_url)
    if not info:
        print("エラー: 動画情報を取得できませんでした。")
        return

    video_id = info.get('id')
    title = info.get('title')
    upload_date = info.get('upload_date') # YYYYMMDD
    # Format to YYYY/MM/DD
    if upload_date and len(upload_date) == 8:
        upload_date = f"{upload_date[:4]}/{upload_date[4:6]}/{upload_date[6:]}"

    db.add_video(video_id, title, video_url, upload_date)
    print(f"タイトル: {title}")
    
    print("\n--- コメント抽出中 (@ageha1st を検索) ---")
    comments = extractor.extract_comments(video_url, target_author="@ageha1st")
    print(f"抽出されたコメント数: {len(comments)}")

    print("\n--- 誤読のパース中 ---")
    items = processor.parse_comments(comments)
    print(f"検出された誤読候補: {len(items)}")

    # Add to DB as pending
    for item in items:
        db.add_misreading(
            video_id=video_id,
            timestamp=item['timestamp'],
            original=item['original'],
            reading=item['reading'],
            context=item['context']
        )
    
    print(f"\n成功: {len(items)} 件の候補をレビュー待ちに追加しました。")
    print(" 'python scripts/review_items.py' を実行して承認を行ってください。")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用法: python scripts/add_stream.py <URL>")
    else:
        main(sys.argv[1])
