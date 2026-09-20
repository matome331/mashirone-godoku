# Legacy scripts

このディレクトリには、過去の更新・DB・Web生成フローで使っていた旧スクリプトを保管しています。

## 重要

- 現行の公開更新フローでは使用しません。
- AIエージェントは、明示的に「過去処理の調査・復旧」を依頼された場合を除き、ここを実行対象にしません。
- 公開データの正本は `mimy_misreadings_refined.txt` です。
- 非公開・削除動画の除外は `excluded_videos.txt` で管理します。
- 現行の同期は `scripts/sync_txt_to_db.py` を使用します。

## 退避した旧ルート

- `update_dictionary.py`
- `update_all_new_streams.bat`
- `add_new_stream.bat`
- `scripts/final_web_update.py`
- `scripts/generate_webapp_data.py`
- `scripts/sync_channel.py`
- `scripts/add_stream.py`

これらは削除せず、過去の実装確認や復旧用の資料として残しています。
