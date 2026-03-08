"""
間違って削除されたウミガリを保護しつつ、2/22, 2/23のデータだけを完全に消去する。
"""
import json
import os

# パス
BAK_PATH = r"C:\Users\grave\yt-comments\mimy_archive_all\_all_comments.json.bak"
JSON_PATH = r"C:\Users\grave\yt-comments\mimy_archive_all\_all_comments.json"

# 削除したいビデオID
BAD_VIDEO_IDS = ["bPaRFS2MsOA", "VbdtgGNe5CQ"]

print(f"復元・修正中: {JSON_PATH}")

# バックアップを読み込む
with open(BAK_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

# フィルタリング (BAD_VIDEO_IDS に含まれないものだけ残す)
original_len = len(data)
filtered = [item for item in data if item.get("video_id") not in BAD_VIDEO_IDS]
removed = [item for item in data if item.get("video_id") in BAD_VIDEO_IDS]

print(f"元の数: {original_len}")
print(f"削除数: {len(removed)}")
for itm in removed:
    print(f"  - 削除成功: {itm.get('video_title')} ({itm.get('video_date', '日付不明')})")

# 保存
with open(JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(filtered, f, ensure_ascii=False, indent=2)

print("\n完了！これで2/19のウミガリは無事に残っているはずです。")
