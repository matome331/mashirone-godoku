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

## なぜこの構造にするか

以前は同じ情報が refined.txt / DB / data.js / raw archive にあり、
どのファイルを直すべきか毎回判断する必要がありました。

今後は:

- 人間が編集するデータ = `mimy_misreadings_refined.txt`
- 公開しない動画 = `excluded_videos.txt`
- その他 = 生成物または参照用

と役割を固定します。
