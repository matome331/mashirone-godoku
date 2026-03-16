import yt_dlp
import os
import time
import re
from core.database import DatabaseManager

# 設定
CHANNEL_URL = "https://www.youtube.com/@mashi_rone/streams"
TARGET_AUTHOR = "@ageha1st"
THRESHOLD_DATE = "2026/02/20"

def collect_and_analyze():
    db = DatabaseManager()
    
    # 除外キーワードのロード
    exclude_keywords = []
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    exclude_path = os.path.join(base_dir, "exclude_keywords.txt")
    if os.path.exists(exclude_path):
        with open(exclude_path, "r", encoding="utf-8") as f:
            exclude_keywords = [line.strip() for line in f if line.strip()]

    # 追加のゴミキーワード（自動除外）
    auto_exclude = ["潔癖症", "接続確認", "答え", "└", "えっ？", "忘れない", "不具合", "設定忘れ", "録画ミス"]

    refined_path = os.path.join(base_dir, "mimy_misreadings_refined.txt")
    
    # 判定ルール
    pattern = re.compile(
        r'(?P<timestamp>\d{1,2}:\d{2}(?::\d{2})?)'           # タイムスタンプ
        r'\s+'                                               # スペース
        r'(?P<reading>[ぁ-んー]+)'                             # 読み（ひらがな限定）
        r'\s*[\(（]'                                         # 括弧
        r'(?P<original>[^）\)\s]+)'                           # 原文
        r'[\)）]'                                            # 閉じ
    )

    ydl_opts = {
        'getcomments': True,
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
    }
    
    print(f"--- チャンネルの最新動画を確認中: {CHANNEL_URL} ---")
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            channel_info = ydl.extract_info(CHANNEL_URL, download=False, process=False)
            entries = list(channel_info.get('entries', []))[:15]
            
            new_findings_text = ""
            total_found = 0
            
            for entry in entries:
                # 配信予定地 または 【現在配信中】 であれば、詳細情報を取る前にスキップ
                live_status = entry.get('live_status')
                if live_status in ['is_upcoming', 'is_live'] or "予定" in (entry.get('title') or ""):
                    continue

                # IDの正規化
                raw_video_id = entry.get('id')
                video_id = re.split(r'[&?]', raw_video_id)[0] if raw_video_id else None
                if not video_id: continue

                video_url = f"https://www.youtube.com/watch?v={video_id}"
                
                comments = info.get('comments', [])
                comment_count = len(comments)
                
                # スキップ判定（DBに登録済みかつコメント数取得が可能なら比較）
                if db.is_video_processed(video_id, current_comment_count=comment_count):
                    # print(f"Skipping (already processed or no new comments): {video_id}")
                    continue

                try:
                    info = ydl.extract_info(video_url, download=False)
                except Exception:
                    continue
                    
                title = info.get('title', '')
                # メン限チェック
                if "メン限" in title or info.get('live_status') == 'is_live':
                    continue
                
                upload_date_raw = info.get('upload_date', '00000000')
                upload_date = f"{upload_date_raw[:4]}/{upload_date_raw[4:6]}/{upload_date_raw[6:]}"
                if upload_date < THRESHOLD_DATE: continue

                print(f"Scanning: {title} ({upload_date})")
                
                target_clean = TARGET_AUTHOR.lower().lstrip('@')
                
                video_new_text = ""
                found_for_this_video = 0
                
                for c in comments:
                    text = c.get('text', '')
                    author = c.get('author', '').lower().lstrip('@')
                    author_id = c.get('author_id', '').lower().lstrip('@')
                    
                    if target_clean in author or target_clean in author_id:
                        lines = text.split('\n')
                        for line in lines:
                            line = line.strip()
                            if not line: continue
                            
                            # 除外キーワード
                            if any(kw in line for kw in exclude_keywords + auto_exclude):
                                continue
                            
                            match = pattern.search(line)
                            if match:
                                ts = match.group('timestamp')
                                rd = match.group('reading')
                                og = match.group('original')
                                
                                # ゴミ判定
                                if re.match(r'^[\d:\./ \-]+$', rd) or re.match(r'^[\d:\./ \-]+$', og):
                                    continue
                                if len(rd) < 1 or len(og) < 1:
                                    continue

                                # DBに既にある（承認済み）ものは出さない
                                # (ここでDB問い合わせは重いかもしれないが、新規確認のためには必要)
                                with db._get_connection() as conn:
                                    cursor = conn.cursor()
                                    cursor.execute("SELECT 1 FROM misreadings WHERE video_id = ? AND timestamp = ? AND original = ? AND status = 1", (video_id, ts, og))
                                    if cursor.fetchone():
                                        continue

                                video_new_text += f"{ts} - {rd}（{og}）\n"
                                found_for_this_video += 1

                if video_new_text:
                    # refined.txt に追記するためのブロックを作成
                    new_findings_text += f"\n【動画】{title} ({upload_date})\n"
                    new_findings_text += f"URL: {video_url}\n"
                    new_findings_text += "-" * 40 + "\n"
                    new_findings_text += video_new_text
                    new_findings_text += "\n"
                    total_found += found_for_this_video
                
                # スキャンした動画はDBに「解析済み」として仮登録（コメント数も記録）
                # これにより次回の起動時にスキップされる
                db.add_video(video_id, title, video_url, upload_date, comment_count)
                time.sleep(1)

            if total_found > 0:
                # refined.txt の先頭に追記する
                if os.path.exists(refined_path):
                    with open(refined_path, "r", encoding="utf-8") as f:
                        old_content = f.read()
                else:
                    old_content = ""

                # ヘッダーがあれば保持し、その直後に差し込む
                header_match = re.match(r"(^真白猫ミミィ.*?\n=+\n\n)", old_content, re.DOTALL)
                if header_match:
                    header = header_match.group(1)
                    body = old_content[len(header):]
                    final_content = header + new_findings_text + body
                else:
                    final_content = new_findings_text + "\n" + old_content

                with open(refined_path, "w", encoding="utf-8") as f:
                    f.write(final_content)

                print(f"\n✅ 解析完了: {total_found}件の新規候補を「mimy_misreadings_refined.txt」の先頭に追記しました。")
                print(" ファイルを確認・編集してください。")
            else:
                print("\n新しい誤読候補は見つかりませんでした。")
                
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    collect_and_analyze()
