import yt_dlp
import os
import time
import re
from datetime import datetime, timedelta

from core.database import DatabaseManager

# 設定
CHANNEL_URL = "https://www.youtube.com/@mashi_rone/streams"
TARGET_AUTHOR = "@ageha1st"
THRESHOLD_DATE = "2026/03/01"
RECHECK_DAYS = 7


def safe_print(msg):
    """CP932でエンコードできない文字を安全に処理して表示"""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('cp932', errors='replace').decode('cp932'))


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


def merge_findings_into_refined(refined_path, findings):
    """
    新規動画は先頭へ追加し、既存動画の再チェックで見つかった項目は
    同じ動画セクションへ追記する。重複動画セクションは作らない。
    """
    if os.path.exists(refined_path):
        with open(refined_path, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = ""

    new_blocks = []

    for finding in findings:
        video_url = finding["video_url"]
        entry_lines = finding["entries"]
        url_marker = f"URL: {video_url}"
        url_pos = content.find(url_marker)

        if url_pos >= 0:
            section_start = content.rfind("【動画】", 0, url_pos)
            next_section = content.find("\n【動画】", url_pos)
            section_end = next_section if next_section >= 0 else len(content)

            if section_start < 0:
                # 形式が想定外なら既存データを壊さず、新規ブロック扱いにする。
                url_pos = -1
            else:
                section = content[section_start:section_end]
                existing_lines = {line.strip() for line in section.splitlines()}
                additions = [line for line in entry_lines if line not in existing_lines]

                if additions:
                    separator = re.search(r"^-{5,}\s*$", section, re.MULTILINE)
                    if separator:
                        insert_at = separator.end()
                        section = (
                            section[:insert_at]
                            + "\n"
                            + "\n".join(additions)
                            + section[insert_at:]
                        )
                    else:
                        section = section.rstrip() + "\n" + "\n".join(additions) + "\n"

                    content = content[:section_start] + section + content[section_end:]
                continue

        if url_pos < 0:
            block = (
                f"\n【動画】{finding['title']} ({finding['upload_date']})\n"
                f"URL: {video_url}\n"
                + "-" * 40
                + "\n"
                + "\n".join(entry_lines)
                + "\n\n"
            )
            new_blocks.append(block)

    if new_blocks:
        new_text = "".join(new_blocks)
        header_match = re.match(
            r"(^真白猫ミミィ.*?\n=+\n\n)",
            content,
            re.DOTALL,
        )
        if header_match:
            header = header_match.group(1)
            body = content[len(header):]
            content = header + new_text + body
        else:
            content = new_text + "\n" + content

    with open(refined_path, "w", encoding="utf-8") as f:
        f.write(content)


def collect_and_analyze():
    db = DatabaseManager()

    # 除外キーワードのロード
    exclude_keywords = []
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    exclude_path = os.path.join(base_dir, "exclude_keywords.txt")
    if os.path.exists(exclude_path):
        with open(exclude_path, "r", encoding="utf-8") as f:
            exclude_keywords = [line.strip() for line in f if line.strip()]

    # 非公開・削除済みなど、今後の収集対象から外す動画ID
    excluded_video_ids = set()
    excluded_videos_path = os.path.join(base_dir, "excluded_videos.txt")
    if os.path.exists(excluded_videos_path):
        with open(excluded_videos_path, "r", encoding="utf-8") as f:
            for line in f:
                clean = line.split("#", 1)[0].strip()
                if clean:
                    excluded_video_ids.add(clean)

    # 追加のゴミキーワード（自動除外）
    auto_exclude = [
        "潔癖症", "接続確認", "答え", "└", "えっ？", "忘れない",
        "不具合", "設定忘れ", "録画ミス", "ひゃー", "いやー", "あー", "ふっふっふ"
    ]

    refined_path = os.path.join(base_dir, "mimy_misreadings_refined.txt")

    # 判定ルール
    # 読みは従来のひらがなに加えて、カタカナ・半角カナ・英数字と
    # 読みの中で使われやすい区切り記号を許容する。
    # 何でも拾うのではなく、括弧の直前をこの文字種に限定して誤検出を抑える。
    reading_chunk = r"[ぁ-んァ-ヶーｦ-ﾟA-Za-zＡ-Ｚａ-ｚ0-9０-９・･._．/／+＋#＃&＆'’\-‐‑]+"
    pattern = re.compile(
        r'(?P<timestamp>\d{1,2}:\d{2}(?::\d{2})?)'
        r'\s+'
        rf'(?P<reading>{reading_chunk}(?:[ \u3000]+{reading_chunk})*)'
        r'\s*[\(（]'
        r'(?P<original>[^）\)\s]+)'
        r'[\)）]'
    )

    # 一覧・コメント数確認用（コメント本文は取らない）
    metadata_opts = {
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
    }

    # 実際の再スキャン時だけコメント本文を取得
    comment_opts = {
        'getcomments': True,
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
    }

    print(f"--- チャンネルの最新動画を確認中: {CHANNEL_URL} ---")

    try:
        with yt_dlp.YoutubeDL(metadata_opts) as metadata_ydl, yt_dlp.YoutubeDL(comment_opts) as comment_ydl:
            channel_info = metadata_ydl.extract_info(
                CHANNEL_URL, download=False, process=False
            )
            entries = list(channel_info.get('entries', []))[:50]

            new_findings = []
            total_found = 0
            scanned_count = 0
            unchanged_count = 0

            for entry in entries:
                live_status = entry.get('live_status')
                entry_title = entry.get('title', '')
                if (
                    live_status in ['is_upcoming', 'is_live']
                    or "予定" in entry_title
                    or "メン限" in entry_title
                ):
                    safe_print(f"Skipped (Live/Upcoming/Member): {entry_title}")
                    continue

                raw_video_id = entry.get('id')
                video_id = re.split(r'[&?]', raw_video_id)[0] if raw_video_id else None
                if not video_id:
                    continue

                if video_id in excluded_video_ids:
                    safe_print(f"Skipped (Excluded video): {entry_title}")
                    continue

                video_url = f"https://www.youtube.com/watch?v={video_id}"

                # まず軽量な動画情報だけ取得して、再スキャンが必要か判定する。
                try:
                    metadata = metadata_ydl.extract_info(video_url, download=False)
                except Exception:
                    continue

                title = metadata.get('title', entry_title)
                if "メン限" in title or metadata.get('live_status') == 'is_live':
                    continue

                upload_date_raw = metadata.get('upload_date', '00000000')
                upload_date = (
                    f"{upload_date_raw[:4]}/{upload_date_raw[4:6]}/{upload_date_raw[6:]}"
                )
                if upload_date < THRESHOLD_DATE:
                    continue

                current_comment_count = metadata.get('comment_count')
                scan_state = db.get_video_scan_state(video_id)
                should_scan, reason = should_rescan_video(
                    scan_state, current_comment_count
                )

                if not should_scan:
                    unchanged_count += 1
                    safe_print(f"Skipped (Unchanged): {title}")
                    continue

                safe_print(f"Scanning: {title} ({upload_date}) [{reason}]")

                try:
                    info = comment_ydl.extract_info(video_url, download=False)
                except Exception:
                    continue

                comments = info.get('comments', [])
                recorded_comment_count = info.get('comment_count')
                if recorded_comment_count is None:
                    recorded_comment_count = current_comment_count
                if recorded_comment_count is None:
                    recorded_comment_count = len(comments)

                target_clean = TARGET_AUTHOR.lower().lstrip('@')
                entry_lines = []

                for c in comments:
                    text = c.get('text', '')
                    author = c.get('author', '').lower().lstrip('@')
                    author_id = c.get('author_id', '').lower().lstrip('@')

                    if target_clean not in author and target_clean not in author_id:
                        continue

                    for line in text.split('\n'):
                        line = line.strip()
                        if not line:
                            continue

                        if any(kw in line for kw in exclude_keywords + auto_exclude):
                            continue

                        match = pattern.search(line)
                        if not match:
                            continue

                        ts = match.group('timestamp')
                        rd = match.group('reading')
                        og = match.group('original')

                        if (
                            re.match(r'^[\d:\./ \-]+$', rd)
                            or re.match(r'^[\d:\./ \-]+$', og)
                        ):
                            continue
                        if len(rd) < 1 or len(og) < 1:
                            continue

                        # 既に公開済みの項目は再追加しない。
                        with db._get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute(
                                """
                                SELECT 1
                                FROM misreadings
                                WHERE video_id = ?
                                  AND timestamp = ?
                                  AND original = ?
                                  AND reading = ?
                                  AND status = 1
                                """,
                                (video_id, ts, og, rd),
                            )
                            if cursor.fetchone():
                                continue

                        output_line = f"{ts} - {rd}（{og}）"
                        if output_line not in entry_lines:
                            entry_lines.append(output_line)

                if entry_lines:
                    new_findings.append(
                        {
                            "title": title,
                            "upload_date": upload_date,
                            "video_url": video_url,
                            "entries": entry_lines,
                        }
                    )
                    total_found += len(entry_lines)

                # コメント本文の確認が完了した時だけスキャン日時を更新する。
                db.record_video_scan(
                    video_id,
                    title,
                    video_url,
                    upload_date,
                    recorded_comment_count,
                )
                scanned_count += 1
                time.sleep(1)

            if total_found > 0:
                merge_findings_into_refined(refined_path, new_findings)
                safe_print(
                    f"\n✅ 解析完了: {total_found}件の新規候補を"
                    "「mimy_misreadings_refined.txt」に反映しました。"
                )
                safe_print(" ファイルを確認・編集してください。")
            else:
                print("\n新しい誤読候補は見つかりませんでした。")

            safe_print(
                f"確認結果: 再スキャン {scanned_count}本 / "
                f"変更なしスキップ {unchanged_count}本"
            )

    except Exception as e:
        import traceback
        traceback.print_exc()
        safe_print(f"エラーが発生しました: {e}")


if __name__ == "__main__":
    collect_and_analyze()
