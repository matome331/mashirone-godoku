#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube コメント抽出スクリプト v2.1
改善点:
  - 投稿日（upload_date）の取得・記録に対応
  - 進捗の途中保存（中断しても続きから再開可能）
  - 動画間にスリープ追加（レート制限回避）
  - 処理済み動画のスキップ
  - コメント数0の動画を早期スキップ
"""

import json
import sys
import os
import re
import time
import argparse
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

try:
    import yt_dlp
except ImportError:
    print("yt-dlp がインストールされていません。pip install yt-dlp を実行してください。")
    sys.exit(1)


# ========================================
# 進捗管理クラス
# ========================================
class ProgressTracker:
    """処理済み動画を記録し、再開時にスキップできるようにする"""

    def __init__(self, progress_file):
        self.progress_file = progress_file
        self.processed = {}  # video_id -> { status, comment_count, timestamp }
        self._load()

    def _load(self):
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    self.processed = json.load(f)
                print(f"[進捗] 前回の記録を読み込みました（処理済み: {len(self.processed)}件）")
            except (json.JSONDecodeError, IOError):
                print("[進捗] 前回の記録が破損していたため、新しく開始します")
                self.processed = {}

    def save(self):
        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(self.processed, f, ensure_ascii=False, indent=2)

    def is_done(self, video_id):
        return video_id in self.processed

    def mark_done(self, video_id, status, comment_count=0):
        self.processed[video_id] = {
            'status': status,
            'comment_count': comment_count,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        self.save()  # 毎回保存（中断に備える）

    def get_stats(self):
        total = len(self.processed)
        success = sum(1 for v in self.processed.values() if v['status'] == 'success')
        skipped = sum(1 for v in self.processed.values() if v['status'] == 'no_comments')
        errors = sum(1 for v in self.processed.values() if v['status'] == 'error')
        total_comments = sum(v.get('comment_count', 0) for v in self.processed.values())
        return {
            'total': total,
            'success': success,
            'skipped': skipped,
            'errors': errors,
            'total_comments': total_comments
        }


# ========================================
# コメント抽出（単一動画）
# ========================================
def extract_comments(video_url, target_author=None, output_file=None, quiet=False):
    """
    指定した動画URLからコメントを取得し、
    target_author が指定されている場合はそのユーザーのコメントのみ抽出する。
    """
    ydl_opts = {
        'getcomments': True,
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
    }

    if not quiet:
        print(f"  動画を取得中: {video_url}")
        print(f"  コメントをダウンロード中...")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)

    video_title = info.get('title', '不明')
    video_id = info.get('id', '不明')
    upload_date_raw = info.get('upload_date', '不明')
    
    # 投稿日を YYYY/MM/DD に整形
    upload_date = "日付不明"
    if upload_date_raw and len(upload_date_raw) == 8:
        upload_date = f"{upload_date_raw[:4]}/{upload_date_raw[4:6]}/{upload_date_raw[6:]}"
    elif upload_date_raw:
        upload_date = upload_date_raw

    comments = info.get('comments', [])

    if not quiet:
        print(f"  タイトル: {video_title}")
        print(f"  投稿日: {upload_date}")
        print(f"  コメント総数: {len(comments)}")

    # コメント0件なら早期リターン
    if not comments:
        if not quiet:
            print(f"  → コメント0件のためスキップ")
        return [], video_title, video_id, 0

    if target_author:
        target_clean = target_author.lstrip('@')
        filtered = []
        for c in comments:
            author = c.get('author', '')
            author_id = c.get('author_id', '')
            author_clean = author.lstrip('@')
            if target_clean.lower() in author_clean.lower() or target_clean.lower() in author_id.lower():
                filtered.append(c)

        if not quiet:
            print(f"  「{target_author}」のコメント: {len(filtered)}件")
        comments = filtered

    # 結果の整形
    results = []
    for c in comments:
        result = {
            'author': c.get('author', '不明'),
            'author_id': c.get('author_id', '不明'),
            'text': c.get('text', ''),
            'timestamp': c.get('timestamp', 0),
            'like_count': c.get('like_count', 0),
            'is_pinned': c.get('is_pinned', False),
            'video_title': video_title,
            'video_date': upload_date,
            'video_id': video_id,
            'video_url': f"https://www.youtube.com/watch?v={video_id}",
        }
        results.append(result)

    # 表示（quiet でない場合）
    if not quiet and results:
        print(f"\n  --- 抽出結果 ---")
        for i, r in enumerate(results, 1):
            text_preview = r['text'][:80].replace('\n', ' ').replace('\r', '')
            if len(r['text']) > 80:
                text_preview += "..."
            print(f"    [{i}] {text_preview}")

    # ファイルに保存
    if output_file and results:
        out_dir = os.path.dirname(output_file)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# 動画: {video_title}\n")
            f.write(f"# URL: https://www.youtube.com/watch?v={video_id}\n")
            f.write(f"# 投稿日: {upload_date}\n")
            f.write(f"# 抽出日: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            if target_author:
                f.write(f"# 対象ユーザー: {target_author}\n")
            f.write(f"# コメント数: {len(results)}\n\n")
            for i, r in enumerate(results, 1):
                f.write(f"--- コメント {i} ---\n")
                f.write(f"投稿者: {r['author']}\n")
                f.write(f"本文:\n{r['text']}\n\n")

        if not quiet:
            print(f"  → 保存: {output_file}")

    return results, video_title, video_id, len(info.get('comments', []))


# ========================================
# チャンネル全体からの抽出（改善版）
# ========================================
def extract_from_channel(channel_url, target_author=None, output_dir=None,
                         max_videos=None, sleep_sec=3, resume=True):
    """
    チャンネル全体の動画からコメントを抽出する（改善版）。
    - 途中保存・再開対応
    - 動画間にスリープ
    - 処理済みスキップ
    """
    ydl_opts = {
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
    }

    print("=" * 60)
    print("  YouTube コメント抽出ツール v2.1")
    print("=" * 60)
    print(f"  チャンネル: {channel_url}")
    if target_author:
        print(f"  対象ユーザー: {target_author}")
    print(f"  スリープ間隔: {sleep_sec}秒")
    print()

    print("チャンネルの動画一覧を取得中...")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(channel_url, download=False)

    entries = info.get('entries', [])
    total = len(entries)

    if max_videos:
        entries = entries[:max_videos]

    print(f"動画数: {total} (処理対象: {len(entries)})")

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # 進捗管理の初期化
    progress_file = os.path.join(output_dir, '_progress.json') if output_dir else '_progress.json'
    tracker = ProgressTracker(progress_file) if resume else ProgressTracker(':memory:')

    # 処理済みの数を確認
    already_done = sum(1 for e in entries if tracker.is_done(e.get('id', '')))
    if already_done > 0:
        print(f"[進捗] {already_done}件は処理済み → スキップします")
    remaining = len(entries) - already_done
    print(f"[進捗] 残り {remaining}件 を処理します")

    if remaining == 0:
        print("\nすべて処理済みです！")
        stats = tracker.get_stats()
        _print_final_stats(stats)
        return []

    # 時間の見積もり
    est_seconds = remaining * (15 + sleep_sec)
    est_time = str(timedelta(seconds=est_seconds))
    print(f"[見積もり] 約 {est_time} かかる可能性があります")
    print()

    all_results = []
    start_time = time.time()
    processed_count = 0

    for i, entry in enumerate(entries, 1):
        video_id = entry.get('id', '')
        video_title = entry.get('title', '不明')
        video_url = entry.get('url', '')
        if not video_url.startswith('http'):
            video_url = f"https://www.youtube.com/watch?v={video_id}"

        # 処理済みスキップ
        if tracker.is_done(video_id):
            continue

        processed_count += 1
        elapsed = time.time() - start_time
        if processed_count > 1:
            avg_per_video = elapsed / (processed_count - 1)
            eta = avg_per_video * (remaining - processed_count + 1)
            eta_str = str(timedelta(seconds=int(eta)))
        else:
            eta_str = "計算中..."

        print(f"\n[{i}/{len(entries)}] (残り約{eta_str}) {video_title}")

        try:
            output_file = None
            if output_dir:
                safe_title = re.sub(r'[\\/*?:"<>|]', '_', video_title)[:50]
                output_file = os.path.join(output_dir, f"{safe_title}_{video_id}.txt")

            results, _, _, total_comment_count = extract_comments(
                video_url, target_author, output_file, quiet=False
            )

            if total_comment_count == 0:
                tracker.mark_done(video_id, 'no_comments', 0)
            elif len(results) == 0:
                tracker.mark_done(video_id, 'no_match', total_comment_count)
            else:
                tracker.mark_done(video_id, 'success', len(results))
                all_results.extend(results)

        except KeyboardInterrupt:
            print("\n\n[中断] Ctrl+C が押されました。進捗は保存済みです。")
            print("       同じコマンドで再実行すれば、続きから処理できます。")
            break
        except Exception as e:
            print(f"  ✗ エラー: {e}")
            tracker.mark_done(video_id, 'error', 0)
            continue

        # レート制限回避のスリープ
        if i < len(entries):
            time.sleep(sleep_sec)

    # 全結果のサマリー
    total_elapsed = time.time() - start_time
    elapsed_str = str(timedelta(seconds=int(total_elapsed)))
    print(f"\n処理時間: {elapsed_str}")

    stats = tracker.get_stats()
    _print_final_stats(stats)

    # 全結果を保存
    if output_dir and all_results:
        # 既存の結果ファイルがあればマージ
        summary_file = os.path.join(output_dir, '_all_comments.json')
        existing_results = []
        if os.path.exists(summary_file):
            try:
                with open(summary_file, 'r', encoding='utf-8') as f:
                    existing_results = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

        # 重複排除してマージ
        existing_ids = set()
        for r in existing_results:
            key = f"{r.get('video_id', '')}_{r.get('author', '')}_{r.get('text', '')[:50]}"
            existing_ids.add(key)

        for r in all_results:
            key = f"{r.get('video_id', '')}_{r.get('author', '')}_{r.get('text', '')[:50]}"
            if key not in existing_ids:
                existing_results.append(r)

        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(existing_results, f, ensure_ascii=False, indent=2)
        print(f"\n全結果を「{summary_file}」に保存しました（{len(existing_results)}件）")

        # テキスト版のサマリー
        summary_txt = os.path.join(output_dir, '_all_comments.txt')
        with open(summary_txt, 'w', encoding='utf-8') as f:
            f.write(f"# YouTube コメント抽出結果\n")
            f.write(f"# 抽出日: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            if target_author:
                f.write(f"# 対象ユーザー: {target_author}\n")
            f.write(f"# 合計コメント数: {len(existing_results)}\n")
            f.write(f"# 処理動画数: {stats['total']}\n\n")

            # 動画ごとにグループ化
            by_video = {}
            for r in existing_results:
                vid = r.get('video_id', '不明')
                if vid not in by_video:
                    by_video[vid] = {
                        'title': r.get('video_title', '不明'),
                        'date': r.get('video_date', '不明'),
                        'comments': []
                    }
                by_video[vid]['comments'].append(r)

            for vid, data in by_video.items():
                f.write(f"{'=' * 60}\n")
                f.write(f"動画: {data['title']}\n")
                f.write(f"投稿日: {data['date']}\n")
                f.write(f"URL: https://www.youtube.com/watch?v={vid}\n")
                f.write(f"コメント数: {len(data['comments'])}\n")
                f.write(f"{'=' * 60}\n\n")
                for r in data['comments']:
                    f.write(f"{r['text']}\n\n")

        print(f"テキスト版を「{summary_txt}」に保存しました")

    return all_results


def _print_final_stats(stats):
    print("\n" + "=" * 60)
    print("  処理結果サマリー")
    print("=" * 60)
    print(f"  処理済み動画数  : {stats['total']}")
    print(f"    成功（該当あり）: {stats['success']}")
    print(f"    該当なし       : {stats.get('skipped', 0)}")
    print(f"    エラー         : {stats['errors']}")
    print(f"  抽出コメント合計: {stats['total_comments']}")
    print("=" * 60)


# ========================================
# メイン
# ========================================
if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='YouTube コメント抽出ツール v2.1',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 特定の動画から特定ユーザーのコメントを抽出
  python extract_comments.py --url "動画URL" --author "@ageha1st"

  # 結果をファイルに保存
  python extract_comments.py --url "動画URL" --author "@ageha1st" -o result.txt

  # チャンネル全体から抽出（途中で止めても再開可能）
  python extract_comments.py --url "https://www.youtube.com/@Channel/videos" --author "@ageha1st" --channel --output-dir results

  # チャンネルから最大10動画だけ処理
  python extract_comments.py --url "https://www.youtube.com/@Channel/videos" --author "@ageha1st" --channel --max-videos 10 --output-dir results

  # スリープ間隔を変更（デフォルト3秒）
  python extract_comments.py --url "..." --channel --sleep 5 --output-dir results

  # 進捗をリセットして最初からやり直す
  python extract_comments.py --url "..." --channel --no-resume --output-dir results
        """
    )

    parser.add_argument('--url', required=True, help='動画URL またはチャンネルURL')
    parser.add_argument('--author', help='抽出対象의 ユーザー名（例: @ageha1st）')
    parser.add_argument('--output', '-o', help='出力ファイル名（単一動画の場合）')
    parser.add_argument('--channel', action='store_true', help='チャンネルモード（複数動画を処理）')
    parser.add_argument('--max-videos', type=int, help='処理する最大動画数（チャンネルモード時）')
    parser.add_argument('--output-dir', help='出力ディレクトリ（チャンネルモード時）')
    parser.add_argument('--sleep', type=int, default=3, help='動画間のスリープ秒数（デフォルト: 3秒）')
    parser.add_argument('--no-resume', action='store_true', help='進捗をリセットして最初から処理する')

    args = parser.parse_args()

    if args.channel:
        extract_from_channel(
            args.url,
            target_author=args.author,
            output_dir=args.output_dir or 'comments_output',
            max_videos=args.max_videos,
            sleep_sec=args.sleep,
            resume=not args.no_resume
        )
    else:
        results, _, _, _ = extract_comments(
            args.url,
            target_author=args.author,
            output_file=args.output
        )
