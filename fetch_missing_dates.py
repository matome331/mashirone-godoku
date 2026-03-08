import yt_dlp
import os
import time

needed_path = os.path.expandvars(r'%USERPROFILE%\yt-comments\missing_vids.txt')
dates_path = os.path.expandvars(r'%USERPROFILE%\yt-comments\mimy_archive_all\video_dates.txt')

with open(needed_path, 'r') as f:
    missing_vids = [line.strip() for line in f if line.strip()]

ydl_opts = {
    'quiet': True,
    'skip_download': True,
    'extract_flat': 'in_playlist',
    'no_warnings': True,
}

print(f"Fetching dates for {len(missing_vids)} videos...")

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    with open(dates_path, 'a', encoding='utf-8') as f:
        for i, vid in enumerate(missing_vids):
            url = f"https://www.youtube.com/watch?v={vid}"
            try:
                info = ydl.extract_info(url, download=False)
                upload_date = info.get('upload_date', 'NA')
                if not upload_date:
                    # 'release_date'や'live_status'などを確認
                     upload_date = info.get('release_date', 'NA')
                f.write(f"{vid}#{upload_date}\n")
                f.flush()
                if i % 10 == 0:
                    print(f"Progress: {i}/{len(missing_vids)} videos processed...")
            except Exception as e:
                f.write(f"{vid}#NA\n")
                f.flush()

print("Done fetching missing dates.")
