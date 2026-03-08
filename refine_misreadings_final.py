import json
import os
import re

dates_path = os.path.expandvars(r'%USERPROFILE%\yt-comments\mimy_archive_all\video_dates_clean.json')
input_file = os.path.expandvars(r'%USERPROFILE%\yt-comments\mimy_archive_all\_all_comments.json')
output_file = os.path.expandvars(r'%USERPROFILE%\yt-comments\mimy_misreadings_refined.txt')

video_dates = {}
if os.path.exists(dates_path):
    with open(dates_path, 'r', encoding='utf-8') as f:
        video_dates = json.load(f)

with open(input_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

pattern = re.compile(r'(\d{1,2}:\d{2}(?::\d{2})?)\s*([ぁ-んーっ]+)[(（](.+?)[)）]')
kanji_re = re.compile(r'[一-龠]')
english_re = re.compile(r'^[a-zA-Z0-9\s\.\-\/]+$')

exclude_keywords = [
    '台パン', '笑', '泣', '内緒', '挨拶', '目標', '予定', 'オチ', 'ギフト', 
    '待機', '告知', '宣伝', '説明', '詳細', '注意', '音', '声', '顔',
    '表情', '表示', '漢字読めない', '宝くじ',
    '手フリフリ', '囁き', '渾身の', '棒', '飛んでった', '悲鳴', '写真', 
    '叫んだ？', '丸目', '大人なレディ', '色気？', '色気ボイス？', 'ガチ恋距離',
    '11/22', '圧', '事故', '清楚風？', '調味料', '宙に浮く腕', '追いかけられてます',
    'game over', 'やるやる詐欺', 'バナナ再び', '才能', 'キラ目', '気付いた',
    '3つ目', '雷', '吹いた？', '早口', '自分の手にビビる', '落ちた', '見つけた',
    '裏返った', '赤スパ', '閉じがち', 'line', '家事', '清楚', '問', '答え合わせ',
    '伸び', '清楚？', '手振り', '違うかも', 'ねばねば系', 'ed流れない', 'BGM無し'
]

refined_list = []
for item in data:
    text = item.get('text', '')
    video_title = item.get('video_title', 'Unknown')
    video_id = item.get('video_id', '')
    
    v_date = video_dates.get(video_id, "日付不明")
    if v_date == "NA": v_date = "日付不明"
    full_title = f"{video_title} ({v_date})"
    
    for line in text.split('\n'):
        match = pattern.search(line)
        if match:
            timestamp, reading, original = match.group(1), match.group(2).strip(), match.group(3).strip()
            if any(kw in original for kw in exclude_keywords): continue
            if (bool(kanji_re.search(original)) or bool(english_re.match(original))) and len(original) <= 15:
                refined_list.append({'full_title': full_title, 'timestamp': timestamp, 'reading': reading, 'original': original})

with open(output_file, 'w', encoding='utf-8') as f:
    f.write("真白猫ミミィ 漢字・英単語誤読まとめ（厳選版 v14 全配信日完全対応）\n")
    f.write("="*60 + "\n\n")
    current_video = ""
    for m in refined_list:
        if m['full_title'] != current_video:
            current_video = m['full_title']
            f.write(f"\n【動画】{current_video}\n" + "-" * 40 + "\n")
        f.write(f"{m['timestamp']} - {m['reading']}（{m['original']}）\n")

print(f"結果: {output_file} に保存しました。")
print(f"抽出数: {len(refined_list)} 件")

# 不明な日付の件数を確認
unknowns = sum(1 for m in refined_list if "日付不明" in m['full_title'])
print(f"うち、日付不明（メンバー限定など）: {unknowns}件")

