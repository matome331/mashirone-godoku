import os
import re
import sys


def extract_video_id(value):
    value = value.strip()
    if not value:
        return None

    patterns = [
        r"[?&]v=([A-Za-z0-9_-]{11})",
        r"youtu\.be/([A-Za-z0-9_-]{11})",
        r"youtube\.com/(?:shorts|live|embed)/([A-Za-z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, value)
        if match:
            return match.group(1)

    if re.fullmatch(r"[A-Za-z0-9_-]{11}", value):
        return value

    return None


def load_excluded_ids(path):
    if not os.path.exists(path):
        return set()

    excluded = set()
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            clean = line.split("#", 1)[0].strip()
            if clean:
                excluded.add(clean)
    return excluded


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    excluded_path = os.path.join(base_dir, "excluded_videos.txt")

    value = sys.argv[1] if len(sys.argv) > 1 else input("除外するYouTube URLまたは動画ID: ").strip()
    video_id = extract_video_id(value)

    if not video_id:
        print("[ERROR] YouTube動画IDを判別できませんでした。")
        sys.exit(1)

    excluded_ids = load_excluded_ids(excluded_path)
    if video_id in excluded_ids:
        print(f"[INFO] {video_id} はすでに除外リストにあります。")
        return

    with open(excluded_path, "a", encoding="utf-8") as f:
        if os.path.getsize(excluded_path) > 0:
            f.write("\n")
        f.write(video_id + "\n")

    print(f"[SUCCESS] {video_id} を公開除外リストに追加しました。")
    print("続けて Webサイト・DB 同期を実行すると検索結果から外れます。")


if __name__ == "__main__":
    main()
