#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Chat確認用の review_comments だけを安全にGitHubへ送る。

コード、refined.txt、review_state.json などはstage/commitしない。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REVIEW_DIR = "review_comments"
HEALTH_SCRIPT = os.path.join(
    REPO_ROOT,
    "scripts",
    "review_health_check.py",
)

MEMBER_TITLE_MARKERS = (
    "メン限",
    "メンバー限定",
    "メンバーシップ限定",
)
VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def creation_flags():
    if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW"):
        return subprocess.CREATE_NO_WINDOW
    return 0


def run_git(*args, capture=True, check=True):
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=capture,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        creationflags=creation_flags(),
    )
    if check and result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(
            f"git {' '.join(args)} に失敗しました"
            + (f"\n{detail}" if detail else "")
        )
    return result


def split_lines(text):
    return [line.strip() for line in text.splitlines() if line.strip()]


def is_allowed_path(path):
    normalized = path.replace("\\", "/").lstrip("./")
    return (
        normalized.startswith("review_comments/")
        and normalized.endswith(".json")
    )


def ensure_git_available():
    result = subprocess.run(
        ["git", "--version"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        creationflags=creation_flags(),
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Gitが見つかりません。Git for Windowsを確認してください。"
        )


def ensure_master_sync_state():
    branch = run_git("branch", "--show-current").stdout.strip()
    if branch != "master":
        raise RuntimeError(
            f"現在のブランチは {branch or '(detached HEAD)'} です。"
            "reviewログの送信はmasterでだけ実行します。"
        )

    run_git("fetch", "origin", "master", capture=False)

    counts = run_git(
        "rev-list",
        "--left-right",
        "--count",
        "HEAD...origin/master",
    ).stdout.strip().split()

    if len(counts) != 2:
        raise RuntimeError("origin/masterとの同期状態を判定できません")

    ahead, behind = (int(counts[0]), int(counts[1]))

    if behind > 0:
        raise RuntimeError(
            f"ローカルmasterがorigin/masterより {behind} commit古いです。"
            "先に git pull してから collect_mimy.bat を再実行してください。"
        )

    if ahead > 0:
        ahead_paths = split_lines(
            run_git("diff", "--name-only", "origin/master..HEAD").stdout
        )
        unsafe = [
            path for path in ahead_paths
            if not is_allowed_path(path)
        ]
        if unsafe:
            joined = "\n  - ".join(unsafe)
            raise RuntimeError(
                "GitHubへ未送信のコード/正本変更があります。"
                "reviewログと一緒にはpushしません。\n"
                f"  - {joined}"
            )
        print(
            f"前回のreviewログcommitが {ahead} commit未pushです。"
            "今回まとめてpushします。"
        )


def ensure_no_unrelated_staged_files():
    staged = split_lines(
        run_git("diff", "--cached", "--name-only").stdout
    )
    unsafe = [path for path in staged if not is_allowed_path(path)]
    if unsafe:
        joined = "\n  - ".join(unsafe)
        raise RuntimeError(
            "reviewログ以外のファイルがstageされています。"
            "誤commit防止のため中止します。\n"
            f"  - {joined}"
        )


def changed_review_files():
    paths = set()

    modified = split_lines(
        run_git(
            "diff",
            "--name-only",
            "--",
            ":(glob)review_comments/*.json",
        ).stdout
    )
    paths.update(path for path in modified if is_allowed_path(path))

    untracked = split_lines(
        run_git(
            "ls-files",
            "--others",
            "--exclude-standard",
            "--",
            ":(glob)review_comments/*.json",
        ).stdout
    )
    paths.update(path for path in untracked if is_allowed_path(path))

    return sorted(paths)


def is_members_only_metadata(info):
    title = str(info.get("title", "") or "")
    if any(marker in title for marker in MEMBER_TITLE_MARKERS):
        return True

    availability = str(info.get("availability", "") or "").casefold()
    return availability == "subscriber_only"


def sanitize_changed_review_files():
    paths = changed_review_files()
    if not paths:
        print("privacy確認対象のreviewログはありません。")
        return

    if yt_dlp is None:
        raise RuntimeError(
            "メン限確認に必要なyt-dlpが見つかりません。"
            "python -m pip install -U yt-dlp を実行してください。"
        )

    print(f"privacy確認: {len(paths)}件のreviewログ")

    ydl_opts = {
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
    }

    removed = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for rel_path in paths:
            abs_path = os.path.join(REPO_ROOT, rel_path)
            if not os.path.exists(abs_path):
                continue

            try:
                with open(abs_path, "r", encoding="utf-8") as f:
                    payload = json.load(f)
            except (OSError, json.JSONDecodeError) as exc:
                raise RuntimeError(
                    f"{rel_path} をprivacy確認できません: {exc}"
                ) from exc

            title = str(payload.get("title", "") or "")
            video_id = str(payload.get("video_id", "") or "")

            if any(marker in title for marker in MEMBER_TITLE_MARKERS):
                os.remove(abs_path)
                removed.append(rel_path)
                print(f"  削除 (メン限タイトル): {rel_path}")
                continue

            if not VIDEO_ID_RE.fullmatch(video_id):
                raise RuntimeError(
                    f"{rel_path}: video_id が不正なためprivacy確認できません"
                )

            video_url = f"https://www.youtube.com/watch?v={video_id}"
            try:
                info = ydl.extract_info(video_url, download=False)
            except Exception as exc:
                raise RuntimeError(
                    f"{rel_path}: YouTube公開範囲を確認できません。"
                    "安全のためGitHub送信を中止します。"
                ) from exc

            if is_members_only_metadata(info):
                os.remove(abs_path)
                removed.append(rel_path)
                print(f"  削除 (メンバー限定): {rel_path}")

    if removed:
        print(f"privacy保護: メン限reviewログを {len(removed)}件 削除しました。")
    else:
        print("privacy確認: メン限reviewログはありません。")


def run_review_health_check():
    result = subprocess.run(
        [sys.executable, HEALTH_SCRIPT],
        cwd=REPO_ROOT,
        check=False,
        creationflags=creation_flags(),
    )
    if result.returncode != 0:
        raise RuntimeError(
            "reviewキュー健康診断がNGのためGitHub送信を中止しました。"
        )


def stage_review_files():
    run_git(
        "add",
        "-A",
        "--",
        ":(glob)review_comments/*.json",
        capture=False,
    )


def staged_review_files():
    staged = split_lines(
        run_git("diff", "--cached", "--name-only").stdout
    )
    return [path for path in staged if is_allowed_path(path)]


def commit_if_needed():
    staged = staged_review_files()
    if not staged:
        print("新しく送るreviewログはありません。")
        return False

    print("GitHubへ送るreviewログ:")
    for path in staged:
        print(f"  - {path}")

    message = (
        "Update ageha1st review logs "
        + datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    )
    run_git("commit", "-m", message, capture=False)
    print(f"commit: {message}")
    return True


def push_master():
    counts = run_git(
        "rev-list",
        "--left-right",
        "--count",
        "HEAD...origin/master",
    ).stdout.strip().split()
    ahead = int(counts[0]) if len(counts) == 2 else 0

    if ahead <= 0:
        print("GitHubへ送る新しいcommitはありません。")
        return

    print(f"GitHubへ {ahead} commit push中...")
    run_git("push", "origin", "master", capture=False)
    print("✅ Chat確認用ログをGitHubへ送信しました。")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="収集前にGit状態だけ確認する",
    )
    args = parser.parse_args()

    try:
        ensure_git_available()
        ensure_master_sync_state()
        ensure_no_unrelated_staged_files()

        if args.preflight:
            print("Git状態: OK")
            return 0

        sanitize_changed_review_files()
        run_review_health_check()
        stage_review_files()
        commit_if_needed()
        push_master()
        return 0
    except Exception as exc:
        print(f"\n❌ reviewログ送信中止: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
