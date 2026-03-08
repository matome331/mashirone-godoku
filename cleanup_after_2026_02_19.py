"""
2026/02/19の配信（ウミガリ）は残し、それより新しい（02/20以降）データを削除する。
"""
import json
import os
import shutil
from datetime import datetime, timezone, timedelta

# 日本時間 2026/02/20 00:00:00 のUNIXタイムスタンプ（これ以降を削除）
JST = timezone(timedelta(hours=9))
cutoff_dt = datetime(2026, 2, 20, 0, 0, 0, tzinfo=JST)
CUTOFF_TS = int(cutoff_dt.timestamp())

# ファイルパス
JSON_PATH = r"C:\Users\grave\yt-comments\mimy_archive_all\_all_comments.json"
BACKUP_PATH = JSON_PATH + ".bak"

print(f"カットオフ: {cutoff_dt.strftime('%Y/%m/%d %H:%M:%S')} JST")

# バックアップ
if not os.path.exists(BACKUP_PATH):
    shutil.copy2(JSON_PATH, BACKUP_PATH)
    print(f"バックアップ作成: {BACKUP_PATH}")

# 処理
with open(JSON_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

original_len = len(data)
filtered = [item for item in data if item.get("timestamp", 0) < CUTOFF_TS]
removed = [item for item in data if item.get("timestamp", 0) >= CUTOFF_TS]

print(f"元の数: {original_len}")
print(f"削除数: {len(removed)}")
for itm in removed:
    print(f"  - 削除対象: {itm.get('video_title')} ({itm.get('video_date', '日付不明')})")

with open(JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(filtered, f, ensure_ascii=False, indent=2)

print("\nJSONのクリーンアップ完了！")
