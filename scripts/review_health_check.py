#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""review_comments と review_state.json の整合性を検証する。"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REVIEW_DIR = os.path.join(REPO_ROOT, "review_comments")
STATE_FILE = os.path.join(REPO_ROOT, "review_state.json")

VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
DATE_RE = re.compile(r"^\d{4}/\d{2}/\d{2}$")


def source_hash(comments):
    canonical = json.dumps(
        comments,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def load_json(path, errors, label):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        errors.append(f"{label} が見つかりません: {path}")
    except json.JSONDecodeError as exc:
        errors.append(
            f"{label} のJSONが壊れています "
            f"(line {exc.lineno}, column {exc.colno})"
        )
    except OSError as exc:
        errors.append(f"{label} を読めません: {exc}")
    return None


def validate_review_file(path, errors):
    name = os.path.basename(path)
    file_id = name[:-5]
    data = load_json(path, errors, name)
    if not isinstance(data, dict):
        return None

    if data.get("version") != 1:
        errors.append(f"{name}: version が1ではありません")

    video_id = data.get("video_id")
    if video_id != file_id or not VIDEO_ID_RE.fullmatch(str(video_id)):
        errors.append(
            f"{name}: video_id がファイル名と一致しない/不正です: "
            f"{video_id!r}"
        )

    title = data.get("title")
    if not isinstance(title, str) or not title.strip():
        errors.append(f"{name}: title が空です")

    date = data.get("date")
    if not isinstance(date, str) or not DATE_RE.fullmatch(date):
        errors.append(f"{name}: date 形式が不正です: {date!r}")

    url = data.get("url")
    if not isinstance(url, str) or video_id not in url:
        errors.append(f"{name}: url が不正です")

    if data.get("target_author") != "@ageha1st":
        errors.append(
            f"{name}: target_author が @ageha1st ではありません"
        )

    comments = data.get("comments")
    if not isinstance(comments, list):
        errors.append(f"{name}: comments が配列ではありません")
        return None

    expected_count = data.get("target_comment_count")
    if expected_count != len(comments):
        errors.append(
            f"{name}: target_comment_count 不整合 "
            f"({expected_count!r} != {len(comments)})"
        )

    for index, comment in enumerate(comments):
        if not isinstance(comment, dict):
            errors.append(f"{name}: comments[{index}] がobjectではありません")
            continue

        text = comment.get("text")
        if not isinstance(text, str) or not text.strip():
            errors.append(f"{name}: comments[{index}].text が空です")

        for field in ("comment_id", "author", "author_id"):
            if not isinstance(comment.get(field), str):
                errors.append(
                    f"{name}: comments[{index}].{field} が文字列ではありません"
                )

        posted_at = comment.get("posted_at")
        if posted_at is not None and (
            not isinstance(posted_at, (int, float))
            or isinstance(posted_at, bool)
        ):
            errors.append(
                f"{name}: comments[{index}].posted_at が数値ではありません"
            )

    expected_hash = source_hash(comments)
    actual_hash = data.get("source_hash")
    if actual_hash != expected_hash:
        errors.append(
            f"{name}: source_hash 不整合 "
            f"(expected {expected_hash}, actual {actual_hash!r})"
        )

    return {
        "video_id": video_id,
        "source_hash": expected_hash,
        "comment_count": len(comments),
    }


def validate_state(review_files, errors, warnings):
    state = load_json(STATE_FILE, errors, "review_state.json")
    if not isinstance(state, dict):
        return {}, 0

    if state.get("version") != 1:
        errors.append("review_state.json: version が1ではありません")

    reviewed = state.get("reviewed")
    if not isinstance(reviewed, dict):
        errors.append("review_state.json: reviewed がobjectではありません")
        return {}, 0

    for video_id, item in reviewed.items():
        if not VIDEO_ID_RE.fullmatch(str(video_id)):
            errors.append(
                f"review_state.json: 不正な動画ID {video_id!r}"
            )
            continue

        if not isinstance(item, dict):
            errors.append(
                f"review_state.json: {video_id} の値がobjectではありません"
            )
            continue

        hash_value = item.get("source_hash")
        if not isinstance(hash_value, str) or not HASH_RE.fullmatch(hash_value):
            errors.append(
                f"review_state.json: {video_id}.source_hash が不正です"
            )

        reviewed_at = item.get("reviewed_at")
        if reviewed_at:
            try:
                datetime.fromisoformat(reviewed_at)
            except (TypeError, ValueError):
                errors.append(
                    f"review_state.json: {video_id}.reviewed_at がISO日時ではありません"
                )

        if video_id not in review_files:
            warnings.append(
                f"review_stateにはあるがreviewファイルがない: {video_id}"
            )

    pending = sum(
        1
        for video_id, info in review_files.items()
        if reviewed.get(video_id, {}).get("source_hash")
        != info["source_hash"]
    )

    return reviewed, pending


def main():
    errors = []
    warnings = []
    review_files = {}

    if not os.path.isdir(REVIEW_DIR):
        errors.append(f"review_comments が見つかりません: {REVIEW_DIR}")
    else:
        for name in sorted(os.listdir(REVIEW_DIR)):
            if not name.endswith(".json"):
                continue
            path = os.path.join(REVIEW_DIR, name)
            if not os.path.isfile(path):
                continue
            info = validate_review_file(path, errors)
            if info and info.get("video_id"):
                review_files[info["video_id"]] = info

    _, pending = validate_state(review_files, errors, warnings)

    print("=" * 60)
    print("  Chat review queue 健康診断")
    print("=" * 60)
    print(f"  review動画数: {len(review_files)}")
    print(
        "  review内コメント数: "
        f"{sum(item['comment_count'] for item in review_files.values())}"
    )
    print(f"  Chat未確認/更新あり: {pending}本")
    print(f"  warning: {len(warnings)}")
    print(f"  error: {len(errors)}")

    if warnings:
        print("\n[WARNINGS]")
        for warning in warnings:
            print(f"  - {warning}")

    if errors:
        print("\n[ERRORS]")
        for error in errors:
            print(f"  - {error}")
        print("\n  ❌ reviewキュー健康診断: NG")
        return 1

    print("\n  ✅ reviewキュー健康診断: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
