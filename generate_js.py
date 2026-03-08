import os
import json
import re

input_file = os.path.expandvars(r'%USERPROFILE%\yt-comments\mimy_misreadings_refined.txt')
output_js = os.path.expandvars(r'%USERPROFILE%\yt-comments\webapp\data.js')

with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()
    text = text.replace('\x00', '')
    lines = text.splitlines()

misreadings = []
current_video = ""
current_date = ""
current_url = ""

video_pattern = re.compile(r'^【動画】(.*)\s+\((.*?)\)$')
url_pattern = re.compile(r'^URL:\s*(http.*)$')
line_pattern = re.compile(r'^(\d{1,2}:\d{2}(?::\d{2})?)\s*-\s*(.*?)（(.*?)）$')

for line in lines:
    line = line.strip()
    if not line or line.startswith('=') or line.startswith('-') or line.startswith('真白猫ミミィ'):
        continue

    v_match = video_pattern.match(line)
    if v_match:
        current_video = v_match.group(1).strip()
        current_date = v_match.group(2).strip()
        continue
    
    u_match = url_pattern.match(line)
    if u_match:
        current_url = u_match.group(1).strip()
        continue
    
    l_match = line_pattern.match(line)
    if l_match:
        timestamp = l_match.group(1)
        reading = l_match.group(2).strip()
        original = l_match.group(3).strip()
        
        base_url = current_url.split('?t=')[0].split('&t=')[0]
        parts = timestamp.split(':')
        seconds = 0
        if len(parts) == 3:
            seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        elif len(parts) == 2:
            seconds = int(parts[0]) * 60 + int(parts[1])
            
        final_url = f"{base_url}&t={seconds}s" if '?' in base_url else f"{base_url}?t={seconds}s"
        
        misreadings.append({
            'video': current_video,
            'date': current_date,
            'timestamp_str': timestamp,
            'timestamp': seconds,
            'reading': reading,
            'original': original,
            'url': final_url
        })

print(f"Parsed {len(misreadings)} items.")

with open(output_js, 'w', encoding='utf-8') as f:
    # Use ascii fallback or just utf-8. It's safe since encoding='utf-8' and ensure_ascii=False
    f.write('const dictionaryData = ' + json.dumps(misreadings, ensure_ascii=False) + ';\n')
print(f"Saved to {output_js}")
