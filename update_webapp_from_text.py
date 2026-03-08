import re
import json
import os

def parse_refined_text(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 動画セクションごとに分割
    sections = re.split(r'【動画】', content)
    dictionary_data = []
    
    for section in sections:
        if not section.strip():
            continue
        
        # タイトルと日付の抽出: 「タイトル (YYYY/MM/DD)」
        title_line_match = re.match(r'(.+?)\s*\((\d{4}/\d{2}/\d{2})\)', section.strip().split('\n')[0])
        if not title_line_match:
            continue
            
        video_title = title_line_match.group(1).strip()
        video_date = title_line_match.group(2)
        
        # URLの抽出
        url_match = re.search(r'URL:\s*(https?://[^\s\n]+)', section)
        if not url_match:
            continue
        video_url_base = url_match.group(1)
        
        # 誤読行の抽出: 「1:23:45 - 読み（正解）」
        # ハイフンの前後のスペースやカッコの種類に対応
        misread_pattern = re.compile(r'(\d{1,2}:\d{2}(?::\d{2})?)\s*-\s*([^（(]+)[（(](.+?)[）)]')
        
        for line in section.split('\n'):
            m = misread_pattern.search(line)
            if m:
                ts_str = m.group(1)
                reading = m.group(2).strip()
                original = m.group(3).strip()
                
                # 数値タイムスタンプの計算
                parts = ts_str.split(':')
                if len(parts) == 3:
                    seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                else:
                    seconds = int(parts[0]) * 60 + int(parts[1])
                
                dictionary_data.append({
                    "video": video_title,
                    "date": video_date,
                    "timestamp_str": ts_str,
                    "timestamp": seconds,
                    "reading": reading,
                    "original": original,
                    "url": f"{video_url_base}&t={seconds}s"
                })
                
    return dictionary_data

def main():
    base_dir = r"c:\Users\grave\yt-comments"
    input_txt = os.path.join(base_dir, "mimy_misreadings_refined.txt")
    output_js = os.path.join(base_dir, "webapp", "data.js")
    
    if not os.path.exists(input_txt):
        print(f"Error: {input_txt} not found.")
        return
        
    print(f"Reading {input_txt}...")
    data = parse_refined_text(input_txt)
    
    # 日付の降順、タイムスタンプの昇順でソート
    data.sort(key=lambda x: (x['date'], x['timestamp']), reverse=False)
    # 全体としては日付が新しい順に見せたいので、最終的に reverse=True にするかはアプリ側に任せるが
    # data.jsの既存の並びを確認すると、2/19が最初に来ている。
    # 既存の data.js は日付の新しい順になっているようなので、reverse=True でソートする。
    data.sort(key=lambda x: (x['date'], x['timestamp']), reverse=True)

    print(f"Parsed {len(data)} items.")
    
    with open(output_js, 'w', encoding='utf-8') as f:
        f.write(f"const dictionaryData = {json.dumps(data, ensure_ascii=False)};")
    
    print(f"Successfully updated {output_js}")

if __name__ == "__main__":
    main()
