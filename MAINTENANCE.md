# データ管理・メンテナンス

## データの流れ

```text
YouTube / コメント
        ↓
scripts/collect_comments.py
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

### 誤読コメントの読み表記

収集時の「読み」は、ひらがなだけでなく以下も許容します。

- カタカナ / 半角カナ
- 英字 / 全角英字
- 数字 / 全角数字
- 読みの途中の空白
- `・ . / + # & -` など、単語内で使われやすい一部記号

自由な文章全体を拾わないよう、括弧直前の読み部分は許可文字種を限定しています。

### 既存配信の再チェック

`scripts/collect_comments.py` は、一度誤読が見つかった動画も永久スキップしません。

- YouTube上のコメント総数が変わった動画は再スキャン
- コメント総数が同じでも、最終コメント確認から7日以上経過した動画は再スキャン
- それ以外はコメント本文の再取得を省略
- 再チェックで見つかった新規項目は、既存の同じ動画セクションへ追記

コメント確認専用の日時はDBの `last_comment_scan` で管理し、
Web公開同期の `last_processed` とは分離しています。

## GitHub Actions の扱い

YouTubeコメント収集（yt-dlp）はローカル実行を正規ルートとします。

- GitHub Actions上でのyt-dlp自動収集は、YouTube側のbot判定・PO Token・共有データセンターIP制限の影響を受けやすいため、現状は採用しません。
- `.github/workflows/` に収集用ワークフローは置きません。
- GitHub ActionsはGitHub Pagesの公開処理など、YouTube取得を伴わない用途だけに使います。
- 将来再検討する場合は、現行の正本・除外・同期フローを壊さない独立実験として行います。

## 旧スクリプト

過去の更新・DB・Web生成ルートは `legacy/` に隔離しています。
通常運用では実行せず、過去処理の調査・復旧が必要な場合だけ参照します。

## なぜこの構造にするか

以前は同じ情報が refined.txt / DB / data.js / raw archive にあり、
どのファイルを直すべきか毎回判断する必要がありました。

今後は:

- 人間が編集するデータ = `mimy_misreadings_refined.txt`
- 公開しない動画 = `excluded_videos.txt`
- その他 = 生成物または参照用

と役割を固定します。
