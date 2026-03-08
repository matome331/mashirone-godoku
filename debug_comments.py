import subprocess
import json

def test_comments(video_id):
    url = f"https://www.youtube.com/watch?v={video_id}"
    # Fetch first 10 comments with all fields
    cmd = [
        'yt-dlp',
        '--get-comments',
        '--max-comments', '20',
        '--print', '%(author)s ||| %(author_id)s ||| %(author_handle)s ||| %(text)s',
        '--no-check-certificate',
        url
    ]
    print(f"Testing URL: {url}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        print(f"Status Code: {result.returncode}")
        print("Output (all lines):")
        print(result.stdout)
        print("Error Output (if any):")
        if result.stderr:
            print(result.stderr)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Use one of the videos from the screenshot
    test_comments("6L0E5unORQ4")
