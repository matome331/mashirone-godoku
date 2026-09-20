# データ管理・メンテナンス

## データの流れ

```text
YouTube / コメント
        ↓
scripts/collect_comments.py
        ↓
review_comments/<video_id>.json ← @ageha1st の生コメントだけ
        ↓
Chatで誤読候補を抽出・人間が精査
        ↓
mimy_misreadings_refined.txt   ← 公開データの正本
        │
        ├── excluded_videos.txt ← 公開除外フィルタ
        │
        ↓
scripts/sync_txt_to_db.py
        ├── data/misreadings.db ← ローカルミラー
        └── webapp/data.js      ← 公開サイト用生成物
```

この流れは一方向です。

`DB → refined.txt` や `data.js → refined.txt` の逆同期は行いません。

## よくある作業

### 誤読を1件修正・削除

`mimy_misreadings_refined.txt` だけ編集して同期します。

### 配信が非公開になった

元データは残し、動画IDを `excluded_videos.txt` に追加します。

```bat
python scripts\exclude_video.py "https://www.youtube.com/watch?v=XXXXXXXXXXX"
python scripts\sync_txt_to_db.py
```

### 再公開された

`excluded_videos.txt` から動画IDを削除して同期します。

### 同期前に壊れていないか確認

```bat
python scripts\sync_txt_to_db.py --check
```

タイトル・日付・URL・誤読行・重複を検証します。
エラー時はDBとWebデータを変更しません。

### refined.txt の読み表記

コメント収集時には誤読判定をしません。
Chatで採用した項目を `mimy_misreadings_refined.txt` に反映した後、
同期処理では「読み」として以下も許容します。

- カタカナ / 半角カナ
- 英字 / 全角英字
- 数字 / 全角数字
- 読みの途中の空白
- `・ . / + # & -` など、単語内で使われやすい一部記号

自由な文章全体を拾わないよう、括弧直前の読み部分は許可文字種を限定しています。

### チャンネル走査範囲

`scripts/collect_comments.py` は「最新50配信」のような固定件数では打ち切りません。

- `/streams` を新しい順に確認
- `THRESHOLD_DATE` より古い配信に到達した時点で終了
- 一覧情報だけで日付が分かる場合は、個別動画を開く前に終了判定
- 一覧で日付が取れない動画だけ個別メタデータで日付確認

これにより、更新間隔が空いて50本を超えても、基準日以降の未確認配信を取りこぼしにくくします。

### 既存配信の再チェック

`scripts/collect_comments.py` は、一度誤読が見つかった動画も永久スキップしません。

- YouTube上のコメント総数が変わった動画は再スキャン
- コメント総数が同じでも、最終コメント確認から7日以上経過した動画は再スキャン
- それ以外はコメント本文の再取得を省略
- 再チェックで @ageha1st さんのコメント内容が変わった場合は、対応する `review_comments/<video_id>.json` を更新

コメント確認専用の日時はDBの `last_comment_scan` で管理し、
Web公開同期の `last_processed` とは分離しています。

## GitHub Actions の扱い

YouTubeコメント収集（yt-dlp）はローカル実行を正規ルートとします。

- GitHub Actions上でのyt-dlp自動収集は、YouTube側のbot判定・PO Token・共有データセンターIP制限の影響を受けやすいため、現状は採用しません。
- `.github/workflows/` に収集用ワークフローは置きません。
- GitHub ActionsはGitHub Pagesの公開処理やリポジトリ健康診断など、YouTube取得を伴わない用途だけに使います。
- `.github/workflows/health-check.yml` は、正本の書式・Python構文・Web JavaScript構文だけを検証し、yt-dlpは実行しません。
- 将来再検討する場合は、現行の正本・除外・同期フローを壊さない独立実験として行います。

## 旧スクリプト

過去の更新・DB・Web生成ルートは `legacy/` に隔離しています。
通常運用では実行せず、過去処理の調査・復旧が必要な場合だけ参照します。

## なぜこの構造にするか

以前は同じ情報が refined.txt / DB / data.js / raw archive にあり、
どのファイルを直すべきか毎回判断する必要がありました。

今後は:

- Chat確認前の材料 = `review_comments/*.json`
- Chat確認状態 = `review_state.json`
- 人間が確定した公開データ = `mimy_misreadings_refined.txt`
- 公開しない動画 = `excluded_videos.txt`
- その他 = 生成物または参照用

と役割を固定します。

## チャット検索と共通の非公開動画除外

運用上の正本は `mashirone-chat/excluded_videos.txt` です。

公開サイトの `webapp/app.js` は起動時に次の2つを読み、動画IDを合算して検索対象から外します。

1. 正本: `https://matome331.github.io/mashirone-chat/excluded_videos.txt`
2. ローカル予備: `../excluded_videos.txt`

そのため、Chatで非公開/削除を確認してチャット検索側の正本へ追加した動画は、
誤読まとめ側でも検索対象から外れます。

ローカルの `excluded_videos.txt` は次の用途で残します。

- `scripts/sync_txt_to_db.py` の生成時フィルター
- 正本取得に失敗した場合のフォールバック
- GitHub上でのミラー確認

元の `mimy_misreadings_refined.txt` は削除しません。
除外解除時は正本の動画IDを外せば、ランタイム検索フィルターは復帰します。
必要に応じてローカルミラーも揃えたうえで再同期します。

## Chatレビューキュー

通常はリポジトリ直下の `collect_mimy.bat` を実行します。

バッチは次の順で動きます。

1. GitHubの `master` とローカルの同期状態を安全確認
2. yt-dlpで対象配信のコメントを取得
3. `@ageha1st` さんのコメントだけを動画単位で `review_comments/<video_id>.json` に保存
4. reviewキュー健康診断
5. `review_comments/` だけをcommit/push

収集側では次を行いません。

- 誤読かどうかの判定
- 正規表現による候補の絞り込み
- `exclude_keywords.txt` による候補除外
- `mimy_misreadings_refined.txt` の編集
- DB/Web公開データへの反映

各review JSONには `source_hash` を保存します。
コメント内容が前回と同じ場合はファイルを書き換えないため、
定期再スキャンだけでGit履歴が増え続けるのを避けます。

`review_state.json` はChatで確認済みの `source_hash` を記録するためのファイルです。
現在のreview JSONの `source_hash` と一致しない動画だけが
「未確認 / コメント更新あり」と判断できます。

Chatでの標準運用:

1. `collect_mimy.bat` を実行
2. GitHub送信成功を確認
3. Chatで「新しい誤読見て」と依頼
4. Chatが未確認reviewだけ読み、誤読候補を提示
5. Chat上で採用 / 修正 / 不採用を精査
6. 採用分だけ `mimy_misreadings_refined.txt` へ反映
7. `review_state.json` に確認済みhashを記録
8. 同期・健康診断・PR・merge

reviewログ送信用スクリプトは `review_comments/` 以外を自動stageしません。
ローカル `master` がGitHubより古い場合もpushせず停止します。

reviewキューだけ健康診断する場合:

```bat
python scripts\review_health_check.py
```
