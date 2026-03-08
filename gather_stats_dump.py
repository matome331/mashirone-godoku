import json
import os

path = r"c:\Users\grave\yt-comments\db_dump.json"
with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)

target_date = '2026/02/19'
matching = [item for item in data if item.get('upload_date') == target_date]

status0 = [i for i in matching if i.get('status') == 0]
status1 = [i for i in matching if i.get('status') == 1]

print(f"Total entries for {target_date} in db_dump: {len(matching)}")
print(f" Status 0: {len(status0)}")
print(f" Status 1: {len(status1)}")

if status0:
    print("\nSamples of Status 0:")
    for item in status0[:10]:
        print(f" - {item.get('timestamp')} {item.get('original')} ({item.get('reading')})")
