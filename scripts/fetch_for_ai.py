from core.extractor import YouTubeExtractor
import json

def fetch():
    extractor = YouTubeExtractor()
    channel_url = "https://www.youtube.com/@mashi_rone/streams"
    target_author = "@ageha1st"
    threshold_date = "20260220"

    print(f"--- 2/20以降の配信から {target_author} さんのコメントを抽出中 ---")
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
            print(f"\n🎥 VIDEO: {title} ({date})")
            for c in comments:
                print(f"  COMMENT: {c['text']}")

if __name__ == "__main__":
    fetch()
