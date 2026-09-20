"""
正式な公開同期処理。

Source of Truth:
  mimy_misreadings_refined.txt

Publication filter:
  excluded_videos.txt

Generated / mirror data:
  data/misreadings.db
  webapp/data.js

raw archive や既存DBを公開データの正本として逆輸入しないこと。
"""
import argparse
import json
import os
import re
from datetime import datetime

from core.database import DatabaseManager


TITLE_RE = re.compile(r"(.+?)\s*\((\d{4}/\d{2}/\d{2})\)\s*$")
ENTRY_RE = re.compile(
    r"(\d{1,2}:\d{2}(?::\d{2})?)\s*-\s*([^（(]+)[（(](.+?)[）)]\s*$"
)
VIDEO_ID_RE = re.compile(r"[?&]v=([A-Za-z0-9_-]{11})")


def load_excluded_video_ids(path):
    if not os.path.exists(path):
        return set()

    excluded = set()
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            clean = line.split("#", 1)[0].strip()
            if clean:
                excluded.add(clean)
    return excluded


def strip_timestamp_from_url(url):
    url = re.sub(r"([?&])t=\d+s?(&|$)", lambda m: m.group(1) if m.group(2) else "", url)
    return url.rstrip("?&")


def parse_refined_file(refined_path, excluded_video_ids):
    with open(refined_path, "r", encoding="utf-8") as f:
        content = f.read()

    raw_sections = re.split(r"【動画】", content)[1:]
    if not raw_sections:
        raise ValueError("【動画】セクションが1件も見つかりません。")

    videos = {}
    publish_items = []
    errors = []
    excluded_entries = 0
    seen_keys = set()

    for section_no, section in enumerate(raw_sections, start=1):
        lines = section.strip().splitlines()
        if not lines:
            continue

        title_line = lines[0].strip()
        title_match = TITLE_RE.fullmatch(title_line)
        if not title_match:
            errors.append(f"section {section_no}: タイトル/日付を解析できません: {title_line}")
            continue

        video_title = title_match.group(1).strip()
        video_date = title_match.group(2)

        url_line = next((line.strip() for line in lines[1:] if line.strip().startswith("URL:")), None)
        if not url_line:
            errors.append(f"section {section_no}: URL行がありません: {video_title}")
            continue

        video_url = strip_timestamp_from_url(url_line.split("URL:", 1)[1].strip())
        video_id_match = VIDEO_ID_RE.search(video_url)
        if not video_id_match:
            errors.append(f"section {section_no}: YouTube動画IDを取得できません: {video_url}")
            continue

        video_id = video_id_match.group(1)
        is_excluded = video_id in excluded_video_ids

        videos[video_id] = {
            "video_id": video_id,
            "title": video_title,
            "url": video_url,
            "upload_date": video_date,
        }

        for line in lines[1:]:
            line = line.strip()
            if not line or line.startswith("URL:") or re.fullmatch(r"-{5,}", line):
                continue

            match = ENTRY_RE.fullmatch(line)
            if not match:
                errors.append(
                    f"section {section_no}: 誤読行を解析できません: {video_title} | {line}"
                )
                continue

            timestamp = match.group(1)
            reading = match.group(2).strip()
            original = match.group(3).strip()
            key = (video_id, timestamp, original, reading)

            if key in seen_keys:
                errors.append(
                    f"section {section_no}: 重複データ: {video_id} | {timestamp} | {original} | {reading}"
                )
                continue
            seen_keys.add(key)

            if is_excluded:
                excluded_entries += 1
                continue

            publish_items.append(
                {
                    "video_id": video_id,
                    "video_title": video_title,
                    "video_url": video_url,
                    "upload_date": video_date,
                    "timestamp": timestamp,
                    "original": original,
                    "reading": reading,
                    "context": "",
                }
            )

    if errors:
        preview = "\n".join(f"  - {err}" for err in errors[:20])
        extra = "" if len(errors) <= 20 else f"\n  ...ほか {len(errors) - 20} 件"
        raise ValueError(
            f"refined.txt の検証に失敗しました ({len(errors)}件)。\n{preview}{extra}\n"
            "DB/Webは変更していません。"
        )

    return list(videos.values()), publish_items, excluded_entries, len(raw_sections)


def get_seconds(timestamp):
    parts = timestamp.split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
    except ValueError:
        pass
    raise ValueError(f"不正なタイムスタンプ: {timestamp}")


def build_web_list(publish_items):
    web_list = []
    for item in publish_items:
        sec = get_seconds(item["timestamp"])
        sep = "&" if "?" in item["video_url"] else "?"
        jump_url = f'{item["video_url"]}{sep}t={sec}s'

        web_list.append(
            {
                "timestamp": item["timestamp"],
                "original": item["original"],
                "reading": item["reading"],
                "context": item["context"],
                "videoTitle": item["video_title"],
                "videoUrl": jump_url,
                "date": item["upload_date"],
            }
        )
    return web_list


def sync_database(db, videos, publish_items):
    now = datetime.now().isoformat()

    with db._get_connection() as conn:
        cursor = conn.cursor()

        # refined.txt が唯一の公開正本。
        # 以前の承認済みデータは一旦ミラー状態から外し、正本にある項目だけ再承認する。
        cursor.execute("UPDATE misreadings SET status = 0 WHERE status = 1")

        for video in videos:
            cursor.execute(
                """
                INSERT INTO videos (video_id, title, url, upload_date, last_processed)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(video_id) DO UPDATE SET
                    title = excluded.title,
                    url = excluded.url,
                    upload_date = excluded.upload_date,
                    last_processed = excluded.last_processed
                """,
                (
                    video["video_id"],
                    video["title"],
                    video["url"],
                    video["upload_date"],
                    now,
                ),
            )

        for item in publish_items:
            cursor.execute(
                """
                INSERT INTO misreadings
                    (video_id, timestamp, original, reading, context, status, created_at)
                VALUES (?, ?, ?, ?, ?, 1, ?)
                ON CONFLICT(video_id, timestamp, original, reading)
                DO UPDATE SET
                    context = excluded.context,
                    status = 1
                """,
                (
                    item["video_id"],
                    item["timestamp"],
                    item["original"],
                    item["reading"],
                    item["context"],
                    now,
                ),
            )

        conn.commit()


def write_web_data_atomic(output_path, web_list):
    js_content = (
        "const dictionaryData = "
        + json.dumps(web_list, ensure_ascii=False, indent=2)
        + ";\n"
    )
    temp_path = output_path + ".tmp"

    with open(temp_path, "w", encoding="utf-8") as f:
        f.write(js_content)

    os.replace(temp_path, output_path)


def run(check_only=False):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    refined_path = os.path.join(base_dir, "mimy_misreadings_refined.txt")
    excluded_path = os.path.join(base_dir, "excluded_videos.txt")
    output_path = os.path.join(base_dir, "webapp", "data.js")

    if not os.path.exists(refined_path):
        raise FileNotFoundError(f"正本が見つかりません: {refined_path}")

    excluded_video_ids = load_excluded_video_ids(excluded_path)
    videos, publish_items, excluded_entries, section_count = parse_refined_file(
        refined_path, excluded_video_ids
    )
    web_list = build_web_list(publish_items)

    print(f"[CHECK] 動画セクション: {section_count} 件")
    print(f"[CHECK] 公開する誤読: {len(web_list)} 件")
    print(f"[CHECK] 公開除外動画ID: {len(excluded_video_ids)} 件")
    print(f"[CHECK] 除外された誤読: {excluded_entries} 件")
    print("[CHECK] refined.txt: OK")

    if check_only:
        print("[SUCCESS] 検証のみ完了。DB/Webは変更していません。")
        return

    # 検証がすべて通った後だけ生成物を更新する。
    db = DatabaseManager()
    sync_database(db, videos, publish_items)
    write_web_data_atomic(output_path, web_list)

    print("[SUCCESS] Source of Truth -> DB mirror / Web data の同期が完了しました。")
    print(f"[SUCCESS] Web公開データ: {len(web_list)} 件")


def main():
    parser = argparse.ArgumentParser(
        description="mimy_misreadings_refined.txt を正本としてDBとWebを同期します。"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="書式と件数だけ検証し、DB/data.jsは変更しません。",
    )
    args = parser.parse_args()

    try:
        run(check_only=args.check)
    except Exception as exc:
        print(f"[ERROR] {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
