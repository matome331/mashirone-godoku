# Chat review queue

`collect_mimy.bat` がローカルPCで yt-dlp を使って収集した
`@ageha1st` さんのコメントを、動画ごとのJSONとして保存する場所です。

- 誤読判定はここでは行いません
- `mimy_misreadings_refined.txt` へ自動追記しません
- Chatで内容を確認し、採用分だけ正本へ反映します
- ファイル名は `<video_id>.json`
- `source_hash` が `review_state.json` の記録と違う動画が未確認扱いです
