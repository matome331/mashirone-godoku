"""
2026/02/19以降の配信データを _all_comments.json と _all_comments.txt から削除するスクリプト
"""
import json
import os
import re
from datetime import datetime, timezone, timedelta

# 日本時間 2026/02/19 00:00:00 のUNIXタイムスタンプ
JST = timezone(timedelta(hours=9))
cutoff_dt = datetime(2026, 2, 19, 0, 0, 0, tzinfo=JST)
cutoff_ts = int(cutoff_dt.timestamp())
print(f"カットオフ日時: {cutoff_dt.strftime('%Y/%m/%d %H:%M:%S')} JST")
print(f"カットオフタイムスタンプ: {cutoff_ts}")

# ファイルパス
json_file = os.path.expandvars(r'%USERPROFILE%\yt-comments\mimy_archive_all\_all_comments.json')
txt_file = os.path.expandvars(r'%USERPROFILE%\yt-comments\mimy_archive_all\_all_comments.txt')

# === JSON ファイルの処理 ===
print(f"\n--- JSON: {json_file} ---")
with open(json_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

original_count = len(data)

# 2026/02/19以降の動画ID一覧を特定
removed_videos = set()
filtered = []
for item in data:
    ts = item.get('timestamp', 0)
    if ts >= cutoff_ts:
        vid = item.get('video_id', '不明')
        title = item.get('video_title', '不明')
        removed_videos.add((vid, title))
    else:
        filtered.append(item)

print(f"元のエントリ数: {original_count}")
print(f"削除されるエントリ数: {original_count - len(filtered)}")
print(f"残るエントリ数: {len(filtered)}")

if removed_videos:
    print("\n削除対象の動画:")
    for vid, title in sorted(removed_videos, key=lambda x: x[0]):
        print(f"  - [{vid}] {title}")

# バックアップ作成
backup_json = json_file + '.bak'
if not os.path.exists(backup_json):
    import shutil
    shutil.copy2(json_file, backup_json)
    print(f"\nバックアップ作成: {backup_json}")

# 上書き保存
with open(json_file, 'w', encoding='utf-8') as f:
    json.dump(filtered, f, ensure_ascii=False, indent=2)
print(f"JSON 更新完了!")

# === TXT ファイルの処理 ===
print(f"\n--- TXT: {txt_file} ---")
if os.path.exists(txt_file):
    with open(txt_file, 'r', encoding='utf-8', errors='ignore') as f:
        txt_content = f.read()

    # バックアップ
    backup_txt = txt_file + '.bak'
    if not os.path.exists(backup_txt):
        import shutil
        shutil.copy2(txt_file, backup_txt)
        print(f"バックアップ作成: {backup_txt}")

    # 動画ごとのセクションを解析して削除
    # TXTファイルの構造: "# 動画: タイトル" でセクション区切り
    lines = txt_content.split('\n')
    output_lines = []
    skip_section = False
    removed_ids = {vid for vid, _ in removed_videos}

    for line in lines:
        # 動画セクションの開始を検出
        if line.startswith('# 動画:'):
            # URLの行からvideo_idを探す（次の行にある）
            skip_section = False  # リセット
            output_lines.append(line)
            continue

        if line.startswith('# URL:'):
            # URLからvideo_idを抽出
            url_match = re.search(r'v=([a-zA-Z0-9_-]+)', line)
            if url_match:
                vid = url_match.group(1)
                if vid in removed_ids:
                    skip_section = True
                    # 直前に追加した "# 動画:" 行も削除
                    if output_lines and output_lines[-1].startswith('# 動画:'):
                        output_lines.pop()
                    print(f"  TXTから削除: {vid}")
                    continue
            if not skip_section:
                output_lines.append(line)
            continue

        if skip_section:
            # 次のセクション開始まで読み飛ばす
            if line.startswith('# 動画:'):
                skip_section = False
                output_lines.append(line)
            continue

        output_lines.append(line)

    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))
    print(f"TXT 更新完了!")
else:
    print(f"TXTファイルが見つかりません: {txt_file}")

print("\n✅ クリーンアップ完了! バックアップは .bak ファイルに保存されています。")
