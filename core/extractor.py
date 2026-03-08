import yt_dlp
import json
import re
import os
from datetime import datetime

class YouTubeExtractor:
    def __init__(self, quiet=True):
        self.quiet = quiet

    def get_video_info(self, url, silent_error=False):
        """Fetch metadata for a single video using yt-dlp Python API."""
        ydl_opts = {
            'skip_download': True,
            'quiet': True,
            'no_warnings': True,
            'no_check_certificate': True,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info
        except Exception as e:
            if not silent_error:
                print(f"Error fetching video info: {e}")
            return None

    def get_recent_video_ids(self, channel_url, max_results=10):
        """Get a list of recent video IDs from a channel."""
        ydl_opts = {
            'extract_flat': True,
            'quiet': True,
            'no_warnings': True,
            'playlist_items': f'1-{max_results}',
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(channel_url, download=False)
                entries = info.get('entries', [])
                return [e.get('id') for e in entries if e.get('id')]
        except Exception as e:
            print(f"Error listing channel videos: {e}")
            return []

    def extract_comments(self, url, target_author=None):
        """Extract traditional comments using yt-dlp Python API."""
        # Using the logic from user's extract_comments.py which is proven to work
        ydl_opts = {
            'getcomments': True,
            'skip_download': True,
            'quiet': True,
            'no_warnings': True,
            'no_check_certificate': True,
        }
        
        filtered_comments = []
        total_count = 0
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                comments = info.get('comments', [])
                total_count = len(comments)
                
                if target_author:
                    target_clean = target_author.lower().lstrip('@')
                    for c in comments:
                        author = c.get('author', '').lower().lstrip('@')
                        author_id = c.get('author_id', '').lower().lstrip('@')
                        
                        # Match handle or name
                        if target_clean in author or target_clean in author_id:
                            filtered_comments.append({
                                'author': c.get('author'),
                                'text': c.get('text')
                            })
                else:
                    for c in comments:
                        filtered_comments.append({
                            'author': c.get('author'),
                            'text': c.get('text')
                        })
                        
            return filtered_comments, total_count
        except Exception as e:
            print(f"Error during comment extraction: {e}")
            return [], 0

if __name__ == "__main__":
    extractor = YouTubeExtractor()
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    info = extractor.get_video_info(test_url)
    if info:
        print(f"Video Title: {info.get('title')}")
