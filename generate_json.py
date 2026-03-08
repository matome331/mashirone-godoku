import os
import json
import re

input_file = os.path.expandvars(r'%USERPROFILE%\yt-comments\mimy_misreadings_refined.txt')
output_dir = os.path.expandvars(r'%USERPROFILE%\yt-comments\webapp')
output_file = os.path.join(output_dir, 'data.json')

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

misreadings = []

if not os.path.exists(input_file):
    print(f"Error: {input_file} not found.")
    exit()

with open(input_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

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
        
        # Calculate seconds for timestamp if necessary, but YT accepts &t=12m34s. 
        # The url from our previous script might be like `https://...?t=12:34`.
        # YT requires `t=12m34s` or `t=754s`.
        # Let's cleanly reformat the URL.
        base_url = current_url.split('?t=')[0].split('&t=')[0]
        
        # Parse timestamp to seconds
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

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(misreadings, f, ensure_ascii=False, indent=2)

print(f"Saved to {output_file}")
