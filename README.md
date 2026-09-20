# 真白猫ミミィ 誤読まとめ

## 概要
真白猫ミミィさんの配信の中で登場したユニークな「誤読（語録）」を収集し、検索・閲覧できる非公式ファンサイト（Webアプリ）です。

## 🌐 サイトのURL
https://matome331.github.io/mashirone-godoku/

## データ管理

公開する誤読データの **Source of Truth（唯一の正本）** は:

- `mimy_misreadings_refined.txt`

非公開・削除配信など、サイトに出さない動画は:

- `excluded_videos.txt`

で管理します。

`data/misreadings.db` と `webapp/data.js` は生成物・ミラーです。
内容を直す目的で直接編集しません。

通常の更新は `update_mimy.bat` を使用します。
詳しいデータフローは [MAINTENANCE.md](MAINTENANCE.md) を参照してください。

AIエージェントから編集する場合は [AGENTS.md](AGENTS.md) のルールを優先してください。

---
*このプロジェクトはファンメイドの非公式ツール群であり、ご本人様や関係者様とは一切関係ありません。*
