# AGENTS.md

このリポジトリをAIエージェントが編集するときの最優先ルールです。

## Source of Truth（正本）

公開する誤読データの唯一の正本は:

- `mimy_misreadings_refined.txt`

公開除外する動画の唯一の正本は:

- `excluded_videos.txt`

それ以外は正本ではありません。

## 生成物・ミラー

以下は正本から生成・同期されるデータです。内容の修正目的で直接編集しないでください。

- `data/misreadings.db` — ローカルDBミラー。Git管理対象外。
- `webapp/data.js` — 公開サイト用の生成データ。

公開データを変更するときは `mimy_misreadings_refined.txt` または
`excluded_videos.txt` を編集し、その後:

```bat
python scripts\sync_txt_to_db.py
```

を実行してください。

書式確認だけなら:

```bat
python scripts\sync_txt_to_db.py --check
```

## Raw archive

`mimy_archive_all/` は収集元の生アーカイブです。

- 公開データの削除・修正のために編集しない。
- 非公開動画をサイトから外すために削除しない。
- 過去データの再調査が必要なときだけ参照する。

## 非公開・削除動画

YouTube配信が非公開・削除された場合、過去データを物理削除しません。

```bat
python scripts\exclude_video.py <YouTube URL または動画ID>
python scripts\sync_txt_to_db.py
```

これで検索結果・公開データ・今後の新規収集から除外されます。

再公開された場合は `excluded_videos.txt` から動画IDを削除して再同期します。

## 現行ワークフロー

1. `update_mimy.bat`
2. `scripts/collect_comments.py` で新規候補を収集し、既存配信もコメント数変化または7日経過時に再確認
3. 人間が `mimy_misreadings_refined.txt` を確認・編集
4. `scripts/sync_txt_to_db.py` でDBミラーと `webapp/data.js` を生成
5. Gitへ反映

## Legacy / 調査用スクリプト

旧更新ルートは `legacy/` に隔離されています。
通常の更新・修正では参照・実行しません。

過去処理の調査や復旧が明示的に必要な場合だけ `legacy/README.md` を確認してください。

`mimy_misreadings.txt` も現行の正本ではなく、過去データ・調査用として扱います。

## 変更時の原則

- `webapp/data.js` を手作業で修正しない。
- DBだけ直して公開データを変更しない。
- raw archiveを公開状態の調整に使わない。
- `legacy/` のコードを現行フローへ混ぜない。
- YouTube収集用のGitHub Actionsワークフローを追加しない。yt-dlp収集はローカル実行を正規ルートとする。
- 既存動画を「誤読が1件ある」という理由だけで永久スキップしない。
- 同じ情報を複数箇所へ手作業で同期しない。
- 同期スクリプトの検証が失敗した場合は、生成物を更新せず原因を修正する。
- 大規模整理や旧ファイル削除は、現行フローと分けて行う。
