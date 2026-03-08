import json
import os
import re

dates_path = os.path.expandvars(r'%USERPROFILE%\yt-comments\mimy_archive_all\video_dates_clean.json')
output_file = os.path.expandvars(r'%USERPROFILE%\yt-comments\mimy_misreadings_refined.txt')
input_file = os.path.expandvars(r'%USERPROFILE%\yt-comments\mimy_archive_all\_all_comments.json')
exclude_file = os.path.expandvars(r'%USERPROFILE%\yt-comments\exclude_keywords.txt')

video_dates = {}
if os.path.exists(dates_path):
    with open(dates_path, 'r', encoding='utf-8') as f:
        video_dates = json.load(f)

import sqlite3

def get_seconds(ts):
    try:
        parts = list(map(int, ts.split(':')))
        if len(parts) == 3: return parts[0] * 3600 + parts[1] * 60 + parts[2]
        return parts[0] * 60 + parts[1]
    except: return 0

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "misreadings.db")
if not os.path.exists(db_path):
    print(f"Error: Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# 承認済み(status=1)のデータのみ取得 (DISTINCT を追加して重複を確実に排除)
cursor.execute("""
    SELECT DISTINCT m.timestamp, m.original, m.reading, v.title, v.url as video_url, v.upload_date as date
    FROM misreadings m
    JOIN videos v ON m.video_id = v.video_id
    WHERE m.status = 1
    ORDER BY v.upload_date DESC, v.title ASC, m.timestamp ASC
""")
rows = cursor.fetchall()

refined_list = []
# データの二重取得を防ぐためのセット
seen_items = set()

for r in rows:
    v_date = r['date']
    full_title = f"{r['title']} ({v_date})"
    
    # 完全に同じ内容の項目をセットで管理して、二重出力を防ぐ
    item_key = (full_title, r['timestamp'], r['reading'], r['original'])
    if item_key in seen_items:
        continue
    seen_items.add(item_key)
    
    refined_list.append({
        'full_title': full_title,
        'url': r['video_url'],
        'timestamp': r['timestamp'],
        'reading': r['reading'],
        'original': r['original'],
        'date': v_date
    })

conn.close()

# 念押しでソート（日付降順 → ビデオタイトル → タイムスタンプ昇順）
refined_list.sort(key=lambda x: (
    x['date'] if x['date'] != "日付不明" else "0000/00/00",
    x['full_title'],
    get_seconds(x['timestamp'])
), reverse=False)

# 日付だけ降順にするために特別な処理を行う
# (同じ日付の中でタイトルの並びと時間の並びを制御)
final_list = []
seen_videos = []
v_groups = {}

# まず日付の降順でユニークな日付を取得
dates = sorted(list(set(x['date'] for x in refined_list)), reverse=True)

for d in dates:
    # その日のビデオを取得
    v_in_date = sorted(list(set(x['full_title'] for x in refined_list if x['date'] == d)))
    for v in v_in_date:
        v_data = [x for x in refined_list if x['full_title'] == v]
        v_data.sort(key=lambda x: get_seconds(x['timestamp']))
        final_list.extend(v_data)

with open(output_file, 'w', encoding='utf-8') as f:
    f.write("真白猫ミミィ 漢字・英単語誤読まとめ（厳選版 v16 URL入り）\n")
    f.write("="*60 + "\n\n")
    current_video = ""
    for m in final_list:
        if m['full_title'] != current_video:
            current_video = m['full_title']
            f.write(f"\n【動画】{current_video}\n")
            f.write(f"URL: {m['url']}\n")
            f.write("-" * 40 + "\n")
        f.write(f"{m['timestamp']} - {m['reading']}（{m['original']}）\n")

print(f"結果: {output_file} に保存しました。")
print(f"抽出数: {len(final_list)} 件 (データベースより抽出)")
