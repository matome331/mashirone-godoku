import json
import os
import re
import sys

# 出力エンコーディングを UTF-8 に設定
sys.stdout.reconfigure(encoding='utf-8')

input_file = os.path.expandvars(r'%USERPROFILE%\yt-comments\mimy_archive_all\_all_comments.json')
output_file = os.path.expandvars(r'%USERPROFILE%\yt-comments\mimy_misreadings.txt')

if not os.path.exists(input_file):
    print(f"File not found: {input_file}")
    sys.exit(1)

with open(input_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 漢字の誤読っぽいパターンを正規表現で探す
# 例: 18:16 こうおん（甲乙）
# パターン: [タイムスタンプ] [読み]（[漢字]） または [タイムスタンプ] [漢字]（[読み]）
pattern = re.compile(r'(\d{1,2}:\d{2}(?::\d{2})?)\s*(.+?)[(（](.+?)[)）]')

misreadings = []

for item in data:
    text = item.get('text', '')
    video_title = item.get('video_title', 'Unknown')
    video_url = item.get('video_url', '')
    
    # 1つのコメント内に複数行ある場合がある
    lines = text.split('\n')
    for line in lines:
        match = pattern.search(line)
        if match:
            timestamp = match.group(1)
            part1 = match.group(2).strip()
            part2 = match.group(3).strip()
            
            # クイズ形式っぽく整理
            # part1 か part2 のどちらかが漢字、もう片方が読みであることを想定
            misreadings.append({
                'video': video_title,
                'url': f"{video_url}&t={timestamp.replace(':', 'h', 1).replace(':', 'm', 1) if timestamp.count(':') == 2 else timestamp.replace(':', 'm', 1)}s",
                'timestamp': timestamp,
                'raw': line.strip()
            })

print(f"合計 {len(data)} 件のコメントから、{len(misreadings)} 件の誤読候補が見つかりました。\n")

with open(output_file, 'w', encoding='utf-8') as f:
    f.write(f"真白猫ミミィ 漢字誤読まとめ\n")
    f.write(f"抽出日: {os.popen('date /t').read().strip()}\n")
    f.write("="*60 + "\n\n")
    
    current_video = ""
    for m in misreadings:
        if m['video'] != current_video:
            current_video = m['video']
            f.write(f"\n【動画】{current_video}\n")
            f.write("-" * 40 + "\n")
        
        f.write(f"{m['timestamp']} - {m['raw']}\n")

print(f"結果を {output_file} に保存しました。")

# 最初の10件を表示
print("\n--- 抽出サンプル (最初の10件) ---")
for m in misreadings[:10]:
    print(f"{m['timestamp']} | {m['raw']}")
