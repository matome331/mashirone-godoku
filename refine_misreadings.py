import json
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

# ファイルパス
input_file = os.path.expandvars(r'%USERPROFILE%\yt-comments\mimy_archive_all\_all_comments.json')
date_file = os.path.expandvars(r'%USERPROFILE%\yt-comments\mimy_archive_all\video_dates.txt')
output_file = os.path.expandvars(r'%USERPROFILE%\yt-comments\mimy_misreadings_refined.txt')
exclude_file = os.path.expandvars(r'%USERPROFILE%\yt-comments\exclude_keywords.txt')

def load_dates(path):
    dates = {}
    if not os.path.exists(path): 
        print(f"Date file not found: {path}")
        return dates
    
    # ファイルのエンコーディングを自動判別
    encodings = ['utf-8-sig', 'utf-16', 'utf-8', 'cp932']
    content = ""
    for enc in encodings:
        try:
            with open(path, 'r', encoding=enc) as f:
                content = f.read()
                break
        except:
            continue
    
    if not content:
        print("Could not read date file with any encoding.")
        return dates

    for line in content.splitlines():
        line = line.strip()
        if not line: continue
        
        # IDと日付の区切り文字を特定（# または :）
        vid = None
        date_str = None
        if '#' in line:
            vid, date_str = line.split('#', 1)
        elif ':' in line:
            vid, date_str = line.split(':', 1)
            
        if vid and date_str:
            vid = vid.strip()
            # YYYYMMDD 形式を探す
            match = re.search(r'(\d{8})', date_str)
            if match:
                d = match.group(1)
                dates[vid] = f"{d[:4]}/{d[4:6]}/{d[6:]}"
            else:
                dates[vid] = date_str.strip()
                
    return dates

video_dates = load_dates(date_file)
print(f"Loaded {len(video_dates)} dates from {date_file}")

if not os.path.exists(input_file):
    print(f"Input file not found: {input_file}")
    sys.exit(1)

with open(input_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

pattern = re.compile(r'(\d{1,2}:\d{2}(?::\d{2})?)\s*([ぁ-んーっ]+)[(（](.+?)[)）]')
kanji_re = re.compile(r'[一-龠]')
english_re = re.compile(r'^[a-zA-Z0-9\s\.\-\/]+$')

exclude_keywords = []
if os.path.exists(exclude_file):
    with open(exclude_file, 'r', encoding='utf-8') as f:
        exclude_keywords = [line.strip() for line in f if line.strip()]

refined_list = []
for item in data:
    text = item.get('text', '')
    video_title = item.get('video_title', 'Unknown')
    video_id = item.get('video_id', '')
    
    # 配信日を取得（もし不明なら "Unknown"）
    v_date = video_dates.get(video_id, "日付不明")
    full_title = f"{video_title} ({v_date})"
    
    lines = text.split('\n')
    for line in lines:
        match = pattern.search(line)
        if match:
            timestamp, reading, original = match.group(1), match.group(2).strip(), match.group(3).strip()
            if any(kw in original for kw in exclude_keywords): continue
            if (bool(kanji_re.search(original)) or bool(english_re.match(original))) and len(original) <= 15:
                refined_list.append({'full_title': full_title, 'timestamp': timestamp, 'reading': reading, 'original': original})

with open(output_file, 'w', encoding='utf-8') as f:
    f.write(f"真白猫ミミィ 漢字・英単語誤読まとめ（厳選版 v13 配信日修正完了）\n")
    f.write("="*60 + "\n\n")
    current_video = ""
    for m in refined_list:
        if m['full_title'] != current_video:
            current_video = m['full_title']
            f.write(f"\n【動画】{current_video}\n" + "-" * 40 + "\n")
        f.write(f"{m['timestamp']} - {m['reading']}（{m['original']}）\n")

print(f"完了: {output_file}")
print(f"抽出数: {len(refined_list)} 件")

# サンプルの日付がちゃんと出ているか確認
print("\n--- 配信日入り確認サンプル ---")
seen_videos = set()
count = 0
for m in refined_list:
    if m['full_title'] not in seen_videos:
        print(f"動画タイトル: {m['full_title']}")
        seen_videos.add(m['full_title'])
        count += 1
    if count >= 10: break
