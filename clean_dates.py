import json
import os
import re

dates_path = os.path.expandvars(r'%USERPROFILE%\yt-comments\mimy_archive_all\video_dates.txt')

all_content = b""
with open(dates_path, 'rb') as f:
    all_content = f.read()

# Replace any null bytes or BOMs
cleaned = all_content.decode('utf-8', errors='ignore').replace('\ufeff', '')

video_dates = {}
for line in cleaned.splitlines():
    line = line.strip()
    if not line: continue
    vid = None; date_str = None
    if '#' in line: vid, date_str = line.split('#', 1)
    elif ':' in line: vid, date_str = line.split(':', 1)
    
    if vid and date_str:
        vid = vid.strip()
        match = re.search(r'(\d{8})', date_str)
        if match:
            d = match.group(1)
            video_dates[vid] = f"{d[:4]}/{d[4:6]}/{d[6:]}"
        else:
            video_dates[vid] = date_str.strip()

print(f"Total dates parsed: {len(video_dates)}")
# Dump clean dates
with open(os.path.expandvars(r'%USERPROFILE%\yt-comments\mimy_archive_all\video_dates_clean.json'), 'w', encoding='utf-8') as f:
    json.dump(video_dates, f)
