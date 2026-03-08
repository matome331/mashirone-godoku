import json
import os

path = r"c:\Users\grave\yt-comments\mimy_archive_all\_all_comments.json"
with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)

target_date = '2026/02/19'
matching = [item for item in data if item.get('video_date') == target_date]

print(f"Total entries in archive: {len(data)}")
print(f"Entries for {target_date}: {len(matching)}")

if matching:
    print("\nSamples from 2/19 entries:")
    for item in matching[:10]:
        text_brief = item.get('text', '').replace('\n', ' ')[:100]
        print(f" - {text_brief}")
