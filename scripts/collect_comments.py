#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""@ageha1st さんのコメントをChat確認用キューへ収集する。

このスクリプトは誤読判定を行わない。
mimy_misreadings_refined.txt も変更しない。

流れ:
YouTube -> @ageha1st コメントだけ抽出 -> review_comments/<video_id>.json
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta

try:
    import yt_dlp
except ImportError:
    print(
        "yt-dlp が見つかりません。"
        "python -m pip install -U yt-dlp を実行してください。",
        file=sys.stderr,
    )
    raise SystemExit(1)

from core.database import DatabaseManager


CHANNEL_URL = "https://www.youtube.com/@mashi_rone/streams"
TARGET_AUTHOR = "@ageha1st"
THRESHOLD_DATE = "2026/03/01"
RECHECK_DAYS = 7

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REVIEW_DIR = os.path.join(BASE_DIR, "review_comments")
EXCLUDED_VIDEOS_PATH = os.path.join(BASE_DIR, "excluded_videos.txt")


def format_upload_date(info):
    """Return YYYY/MM/DD when yt-dlp metadata includes a usable date."""
    upload_date_raw = info.get("upload_date")
    if upload_date_raw and re.fullmatch(r"\d{8}", str(upload_date_raw)):
        raw = str(upload_date_raw)
        return f"{raw[:4]}/{raw[4:6]}/{raw[6:]}"

    timestamp = info.get("timestamp") or info.get("release_timestamp")
    if timestamp:
        try:
            return datetime.fromtimestamp(timestamp).strftime("%Y/%m/%d")
        except (TypeError, ValueError, OSError):
            pass

    return None


def safe_print(message):
    """Windows consoleでも表示で停止しないようにする。"""
    try:
        print(message, flush=True)
    except UnicodeEncodeError:
        print(
            str(message).encode("cp932", errors="replace").decode("cp932"),
            flush=True,
        )


def load_excluded_video_ids():
    excluded = set()
    if not os.path.exists(EXCLUDED_VIDEOS_PATH):
        return excluded

    with open(EXCLUDED_VIDEOS_PATH, "r", encoding="utf-8") as f:
        for raw_line in f:
            video_id = raw_line.split("#", 1)[0].strip()
            if video_id:
                excluded.add(video_id)
    return excluded


def should_rescan_video(scan_state, current_comment_count):
    """Return (should_scan, reason) for a video."""
    if scan_state is None:
        return True, "初回スキャン"

    previous_count = scan_state.get("comment_count")
    if (
        current_comment_count is not None
        and previous_count is not None
        and current_comment_count != previous_count
    ):
        return True, f"コメント数変化 {previous_count} -> {current_comment_count}"

    last_scan_raw = scan_state.get("last_comment_scan")
    if not last_scan_raw:
        return True, "再チェック管理導入後の初回スキャン"

    try:
        last_scan = datetime.fromisoformat(last_scan_raw)
    except (TypeError, ValueError):
        return True, "最終スキャン日時を判定できないため再確認"

    if datetime.now() - last_scan >= timedelta(days=RECHECK_DAYS):
        return True, f"{RECHECK_DAYS}日ごとの定期再チェック"

    return False, "コメント数変化なし・最近確認済み"


def is_target_comment(comment):
    target = TARGET_AUTHOR.casefold().lstrip("@")
    author = str(comment.get("author", "")).casefold().lstrip("@")
    author_id = str(comment.get("author_id", "")).casefold().lstrip("@")
    return target in author or target in author_id


def normalize_target_comments(comments):
    """Chatで判断できるよう、対象ユーザーのコメント本文をほぼそのまま保存する。"""
    normalized = []
    seen = set()

    for comment in comments:
        if not is_target_comment(comment):
            continue

        text = str(comment.get("text", "") or "")
        text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
        if not text:
            continue

        comment_id = str(
            comment.get("id")
            or comment.get("comment_id")
            or ""
        )
        author = str(comment.get("author", "") or TARGET_AUTHOR)
        author_id = str(comment.get("author_id", "") or "")
        posted_at = comment.get("timestamp")

        dedupe_key = comment_id or (
            author_id,
            text,
            str(posted_at),
        )
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        item = {
            "comment_id": comment_id,
            "author": author,
            "author_id": author_id,
            "text": text,
        }
        if isinstance(posted_at, (int, float)):
            item["posted_at"] = posted_at

        normalized.append(item)

    normalized.sort(
        key=lambda item: (
            item.get("posted_at", 0),
            item.get("comment_id", ""),
            item.get("text", ""),
        )
    )
    return normalized


def calculate_source_hash(comments):
    canonical = json.dumps(
        comments,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def review_file_path(video_id):
    return os.path.join(REVIEW_DIR, f"{video_id}.json")


def write_review_file(video_id, title, upload_date, video_url, comments):
    """必要なときだけreview JSONを書き換える。

    対象コメントが0件かつ既存ファイルもない場合はファイルを作らない。
    以前コメントがあった動画で0件になった場合は空配列へ更新し、
    Chat側で変化を確認できるようにする。
    """
    os.makedirs(REVIEW_DIR, exist_ok=True)
    path = review_file_path(video_id)

    if not comments and not os.path.exists(path):
        return "no_target"

    payload = {
        "version": 1,
        "video_id": video_id,
        "title": title,
        "date": upload_date,
        "url": video_url,
        "target_author": TARGET_AUTHOR,
        "source_hash": calculate_source_hash(comments),
        "target_comment_count": len(comments),
        "comments": comments,
    }

    existing = None
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except (OSError, json.JSONDecodeError):
            existing = None

    if existing == payload:
        return "unchanged"

    temp_path = path + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(temp_path, path)

    return "updated" if existing is not None else "new"


def collect_comments_for_review():
    db = DatabaseManager()
    excluded_video_ids = load_excluded_video_ids()

    metadata_opts = {
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
    }
    comment_opts = {
        "getcomments": True,
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
    }

    safe_print(f"--- チャンネル確認中: {CHANNEL_URL} ---")
    safe_print(
        f"対象: {TARGET_AUTHOR} のコメントのみ / "
        "誤読判定・refined.txt更新は行いません"
    )

    counters = {
        "checked": 0,
        "rescanned": 0,
        "unchanged_scan": 0,
        "new_files": 0,
        "updated_files": 0,
        "same_files": 0,
        "no_target": 0,
        "errors": 0,
    }

    try:
        with (
            yt_dlp.YoutubeDL(metadata_opts) as metadata_ydl,
            yt_dlp.YoutubeDL(comment_opts) as comment_ydl,
        ):
            channel_info = metadata_ydl.extract_info(
                CHANNEL_URL,
                download=False,
                process=False,
            )
            entries = list(channel_info.get("entries", []))

            for entry in entries:
                counters["checked"] += 1

                live_status = entry.get("live_status")
                entry_title = entry.get("title", "")
                if (
                    live_status in {"is_upcoming", "is_live"}
                    or "予定" in entry_title
                    or "メン限" in entry_title
                ):
                    safe_print(f"Skipped (Live/Upcoming/Member): {entry_title}")
                    continue

                entry_date = format_upload_date(entry)
                if entry_date and entry_date < THRESHOLD_DATE:
                    safe_print(
                        f"Reached threshold: {entry_date} < {THRESHOLD_DATE}. "
                        "Stopping channel scan."
                    )
                    break

                raw_video_id = entry.get("id")
                video_id = (
                    re.split(r"[&?]", str(raw_video_id))[0]
                    if raw_video_id
                    else None
                )
                if not video_id:
                    continue

                if video_id in excluded_video_ids:
                    safe_print(f"Skipped (Excluded video): {entry_title}")
                    continue

                video_url = f"https://www.youtube.com/watch?v={video_id}"

                try:
                    metadata = metadata_ydl.extract_info(
                        video_url,
                        download=False,
                    )
                except Exception as exc:
                    counters["errors"] += 1
                    safe_print(
                        f"Metadata error: {video_id} "
                        f"({type(exc).__name__})"
                    )
                    continue

                title = metadata.get("title", entry_title)
                if (
                    "メン限" in title
                    or metadata.get("live_status") in {"is_live", "is_upcoming"}
                ):
                    continue

                upload_date = format_upload_date(metadata)
                if not upload_date:
                    safe_print(f"Skipped (Unknown upload date): {title}")
                    continue

                if upload_date < THRESHOLD_DATE:
                    safe_print(
                        f"Reached threshold: {upload_date} < {THRESHOLD_DATE}. "
                        "Stopping channel scan."
                    )
                    break

                current_comment_count = metadata.get("comment_count")
                scan_state = db.get_video_scan_state(video_id)
                should_scan, reason = should_rescan_video(
                    scan_state,
                    current_comment_count,
                )

                if not should_scan:
                    counters["unchanged_scan"] += 1
                    safe_print(f"Skipped (Unchanged): {title}")
                    continue

                safe_print(
                    f"Scanning: {title} ({upload_date}) [{reason}]"
                )

                try:
                    info = comment_ydl.extract_info(
                        video_url,
                        download=False,
                    )
                except Exception as exc:
                    counters["errors"] += 1
                    safe_print(
                        f"Comment error: {video_id} "
                        f"({type(exc).__name__})"
                    )
                    continue

                all_comments = info.get("comments", [])
                target_comments = normalize_target_comments(all_comments)

                result = write_review_file(
                    video_id,
                    title,
                    upload_date,
                    video_url,
                    target_comments,
                )

                if result == "new":
                    counters["new_files"] += 1
                    safe_print(
                        f"  -> review新規: {len(target_comments)}コメント"
                    )
                elif result == "updated":
                    counters["updated_files"] += 1
                    safe_print(
                        f"  -> review更新: {len(target_comments)}コメント"
                    )
                elif result == "unchanged":
                    counters["same_files"] += 1
                    safe_print(
                        f"  -> ageha1stコメント変化なし: "
                        f"{len(target_comments)}コメント"
                    )
                else:
                    counters["no_target"] += 1
                    safe_print("  -> ageha1stコメントなし")

                recorded_comment_count = info.get("comment_count")
                if recorded_comment_count is None:
                    recorded_comment_count = current_comment_count
                if recorded_comment_count is None:
                    recorded_comment_count = len(all_comments)

                db.record_video_scan(
                    video_id,
                    title,
                    video_url,
                    upload_date,
                    recorded_comment_count,
                )
                counters["rescanned"] += 1
                time.sleep(1)

    except KeyboardInterrupt:
        safe_print("\n中断しました。完了済みの動画は記録されています。")
        return 130
    except Exception as exc:
        import traceback

        traceback.print_exc()
        safe_print(f"収集処理を継続できません: {exc}")
        return 1

    safe_print("\n" + "=" * 60)
    safe_print("  収集結果")
    safe_print("=" * 60)
    safe_print(f"  一覧確認: {counters['checked']}本")
    safe_print(f"  コメント再スキャン: {counters['rescanned']}本")
    safe_print(f"  最近確認済みスキップ: {counters['unchanged_scan']}本")
    safe_print(f"  review新規: {counters['new_files']}本")
    safe_print(f"  review更新: {counters['updated_files']}本")
    safe_print(f"  review内容変化なし: {counters['same_files']}本")
    safe_print(f"  ageha1stコメントなし: {counters['no_target']}本")
    safe_print(f"  取得エラー: {counters['errors']}本")
    safe_print("=" * 60)
    safe_print(
        "誤読候補の判断はしていません。"
        "review_comments をChatで確認してください。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(collect_comments_for_review())
