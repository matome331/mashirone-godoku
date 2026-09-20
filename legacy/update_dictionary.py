import os
import re
import json
import subprocess
from datetime import datetime

# 設定
TARGET_AUTHOR = "@ageha1st"
CHANNEL_URL = "https://www.youtube.com/@mashi_rone/streams"
DATE_THRESHOLD = "2026/02/18" # 2/19の配信を含めるため1日早める
SKIP_KEYWORDS = ["メン限", "メンバー限定", "メン限配信"]

EXTRACT_SCRIPT = os.path.expandvars(r'%USERPROFILE%\yt-comments\extract_comments.py')
REFINED_TXT = os.path.expandvars(r'%USERPROFILE%\yt-comments\mimy_misreadings_refined.txt')
WEBAPP_JS = os.path.expandvars(r'%USERPROFILE%\yt-comments\webapp\data.js')
TEMP_DIR = os.path.expandvars(r'%USERPROFILE%\yt-comments\_temp_update')
EXCLUDE_FILE = os.path.expandvars(r'%USERPROFILE%\yt-comments\exclude_keywords.txt')

def load_exclude_keywords():
    if os.path.exists(EXCLUDE_FILE):
        with open(EXCLUDE_FILE, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    return []

def run_extraction(url, is_channel=False):
    print(f"\n>>> コメント抽出中: {url}")
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)
        
    temp_json = os.path.join(TEMP_DIR, "_all_comments.json")
    # 既存のテンポラリがあれば削除
    if os.path.exists(temp_json):
        os.remove(temp_json)
        
    cmd = [
        "python", EXTRACT_SCRIPT,
        "--url", url,
        "--author", TARGET_AUTHOR
    ]
    if is_channel:
        cmd.extend(["--output-dir", TEMP_DIR, "--channel", "--no-resume"])
    else:
        cmd.extend(["--output", temp_json])
        
    subprocess.run(cmd, check=True)
    
    if os.path.exists(temp_json):
        with open(temp_json, 'r', encoding='utf-8') as f:
            # extract_comments.py の出力には先頭に # ヘッダーがある場合があるので読み飛ばす
            content = "".join([line for line in f if not line.startswith("#")])
            return json.loads(content)
    return []

def get_new_video_list():
    """チャンネルから条件に合う動画IDをリストアップする"""
    print(f"\n>>> チャンネルから新着配信を確認中...")
    import yt_dlp

    # まず一覧を取得
    ydl_opts = {'extract_flat': True, 'quiet': True, 'no_warnings': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(CHANNEL_URL, download=False)
        entries = info.get('entries', [])

    eligible = []
    for e in entries:
        v_title = e.get('title', '')
        v_id = e.get('id', '')
        v_date_raw = e.get('upload_date', None)

        # extract_flat では upload_date が取れないことがあるので個別取得
        if not v_date_raw:
            try:
                ydl_single = {'quiet': True, 'no_warnings': True, 'skip_download': True}
                with yt_dlp.YoutubeDL(ydl_single) as ydl2:
                    vinfo = ydl2.extract_info(f"https://www.youtube.com/watch?v={v_id}", download=False)
                    v_date_raw = vinfo.get('upload_date', '00000000')
            except Exception:
                v_date_raw = '00000000'

        # 整形 YYYYMMDD -> YYYY/MM/DD
        v_date = f"{v_date_raw[:4]}/{v_date_raw[4:6]}/{v_date_raw[6:]}"

        # 条件チェック
        if any(kw in v_title for kw in SKIP_KEYWORDS):
            print(f"  スキップ(メン限): {v_title}")
            continue

        if v_date == "0000/00/00":
            # 日付が取れない(待機所など)場合は単に飛ばして次を探す
            continue

        if v_date <= DATE_THRESHOLD:
            # 2/19以前の動画に到達したらスキャン終了
            print(f"  閾値到達: {v_date} - {v_title} (これ以降は古いので終了)")
            break
        
        print(f"  対象発見: {v_date} - {v_title}")
        eligible.append(f"https://www.youtube.com/watch?v={v_id}")
        
    return eligible

def parse_misreadings(comment_data):
    # ひらがな（正解）の形をコメント内からすべて探し出す
    # タイムスタンプが含まれているコメントを対象とする
    time_pattern = re.compile(r'(\d{1,2}:\d{2}(?::\d{2})?)')
    misread_pattern = re.compile(r'([^()（）\s]+)\s*[(（]([^()（）\s]+)[)）]')
    
    exclude_keywords = load_exclude_keywords()
    
    extracted = []
    for item in comment_data:
        text = item.get('text', '')
        
        # タイムスタンプが含まれているかチェック
        time_matches = list(time_pattern.finditer(text))
        if not time_matches: continue
        
        # コメント内の「カッコ形式」をすべて抽出
        for match in misread_pattern.finditer(text):
            reading = match.group(1).strip()
            original = match.group(2).strip()
            
            # 除外チェック
            if any(kw in original for kw in exclude_keywords): continue
            if reading == original: continue 

            # 最も近い（直前の）タイムスタンプを探す
            timestamp_str = time_matches[0].group(1)
            for tm in time_matches:
                if tm.start() < match.start():
                    timestamp_str = tm.group(1)
                else:
                    break
            
            # タイムスタンプを秒に変換
            parts = timestamp_str.split(':')
            seconds = 0
            try:
                if len(parts) == 3:
                    seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                elif len(parts) == 2:
                    seconds = int(parts[0]) * 60 + int(parts[1])
            except: continue
            
            base_url = item['video_url'].split('?t=')[0].split('&t=')[0]
            final_url = f"{base_url}&t={seconds}s" if '?' in base_url else f"{base_url}?t={seconds}s"
            
            extracted.append({
                'video': item['video_title'],
                'date': item['video_date'],
                'timestamp_str': timestamp_str,
                'timestamp': seconds,
                'reading': reading,
                'original': original,
                'url': final_url
            })
    return extracted

def update_refined_txt(new_items):
    if not new_items: return
    
    print(f"\n>>> テキストファイルに追記中: {REFINED_TXT}")
    
    # 既存の内容を読み込み（重複チェック用）
    existing_content = ""
    if os.path.exists(REFINED_TXT):
        with open(REFINED_TXT, 'r', encoding='utf-8', errors='ignore') as f:
            existing_content = f.read()
            
    with open(REFINED_TXT, 'a', encoding='utf-8') as f:
        current_video = ""
        for item in new_items:
            # 動画タイトルが新しければヘッダーを書き込む
            video_header = f"【動画】{item['video']} ({item['date']})"
            if video_header not in existing_content and video_header != current_video:
                f.write(f"\n{video_header}\n" + "-" * 40 + "\n")
                current_video = video_header
            
            # コメント行が既にあればスキップ
            entry = f"{item['timestamp_str']} - {item['reading']}（{item['original']}）"
            if entry not in existing_content:
                f.write(f"{entry}\n")

def regenerate_webapp_js(new_items_to_add):
    print(f"\n>>> Webアプリ用データを更新中: {WEBAPP_JS}")
    
    # refined.txt から全データを再構築
    # (既存の全データを読み込んで JSON 化する)
    misreadings = []
    current_video = ""
    current_date = ""
    
    video_pattern = re.compile(r'^【動画】(.*)\s+\((.*?)\)$')
    line_pattern = re.compile(r'^(\d{1,2}:\d{2}(?::\d{2})?)\s*-\s*(.*?)（(.*?)）$')

    with open(REFINED_TXT, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
        
    for line in lines:
        line = line.strip()
        if not line: continue
        
        v_match = video_pattern.match(line)
        if v_match:
            current_video = v_match.group(1).strip()
            current_date = v_match.group(2).strip()
            continue
            
        l_match = line_pattern.match(line)
        if l_match:
            ts_str = l_match.group(1)
            reading = l_match.group(2)
            original = l_match.group(3)
            
            # 近似的なURL復元（動画タイトルからURLを引くのは難しいため、
            # もし完璧を期すならJSONマージが必要ですが、
            # とりあえず既存の generate_js.py のロジックを流用するか、
            # ここではシンプルに refined.txt を正とします）
            # ※実際には refined.txt に URL が書いてないので、
            # 今回のフローでは new_items から直接 JS 用のデータも作ります。
            pass

    # --- 実装の簡略化: 全データを一括管理 ---
    # 実際には、既存の JS データを読み込んで、新しいデータを append/merge するのが一番安全
    
    current_data = []
    if os.path.exists(WEBAPP_JS):
        try:
            with open(WEBAPP_JS, 'r', encoding='utf-8') as f:
                content = f.read()
                # 'const dictionaryData = [...];' から [...] を抽出
                json_str = content[content.find('['):content.rfind(']')+1]
                current_data = json.loads(json_str)
        except:
            print("既存の data.js の読み込みに失敗しました。新規作成します。")

    # 重複チェック用キー
    def get_key(item): return f"{item['video']}_{item['timestamp_str']}_{item['original']}"
    existing_keys = {get_key(i) for i in current_data}

    added_count = 0
    # global new_items_global (本当は関数の引数で渡すべき)
    for item in new_items_to_add:
        if get_key(item) not in existing_keys:
            current_data.append(item)
            added_count += 1
            
    # 日付とタイムスタンプでソート
    current_data.sort(key=lambda x: (x.get('date', '0000/00/00'), x.get('timestamp', 0)), reverse=True)

    with open(WEBAPP_JS, 'w', encoding='utf-8') as f:
        f.write('const dictionaryData = ' + json.dumps(current_data, ensure_ascii=False, indent=2) + ';\n')
    
    print(f"Webアプリデータを更新しました（追加: {added_count}件, 合計: {len(current_data)}件）")

if __name__ == "__main__":
    import sys
    
    urls_to_process = []
    
    if len(sys.argv) > 1:
        # URLが指定された場合はそのURLのみ
        urls_to_process = [sys.argv[1]]
    else:
        # 引数がない場合はチャンネルから最新を自動スキャン
        urls_to_process = get_new_video_list()
    
    if not urls_to_process:
        print(f"\n新着配信（{DATE_THRESHOLD} 以降）は見つかりませんでした。")
        sys.exit(0)

    print(f"\n--- 合計 {len(urls_to_process)} 件の処理を開始します ---")
    
    for url in urls_to_process:
        # 1. 抽出
        raw_comments = run_extraction(url)
        
        # 2. 解析
        new_items = parse_misreadings(raw_comments)
        
        if new_items:
            # 3. テキスト更新（ここに追記されるのを確認してください）
            update_refined_txt(new_items)
            
            # 4. Webアプリ更新（一旦停止して確認モードへ）
            # regenerate_webapp_js(new_items)
            print(f"✅ テキストを更新しました: {url}")
            print(f"   {REFINED_TXT} を確認してください。")
        else:
            print(f"⚠️ 誤読なし: {url}")
            
    print("\n🎉 スキャンとテキスト更新が完了しました！")
    print("mimy_misreadings_refined.txt を確認し、問題なければ「Webアプリの更新」を依頼してください。")
