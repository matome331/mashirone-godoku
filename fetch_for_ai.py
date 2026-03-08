from core.extractor import YouTubeExtractor
import json

def fetch():
    extractor = YouTubeExtractor()
    channel_url = "https://www.youtube.com/@mashi_rone/streams"
    target_author = "@ageha1st"
    threshold_date = "20260220"

    video_ids = extractor.get_recent_video_ids(channel_url, max_results=15)
    
    for vid in video_ids:
        url = f"https://www.youtube.com/watch?v={vid}"
        info = extractor.get_video_info(url, silent_error=True)
        if not info: continue
        
        date = info.get('upload_date', '0')
        if date < threshold_date: continue
        
        title = info.get('title', '')
        if "メン限" in title: continue

        comments, _ = extractor.extract_comments(url, target_author=target_author)
        if comments:
            formatted_date = f"{date[:4]}/{date[4:6]}/{date[6:]}"
            print(f"---VIDEO_START---")
            print(f"TITLE: {title}")
            print(f"DATE: {formatted_date}")
            for c in comments:
                print(f"RAW_COMMENT: {c['text']}")
            print(f"---VIDEO_END---")

if __name__ == "__main__":
    fetch()
