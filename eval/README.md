# 論文の評価の道具とデータ

論文（中村・金「ArchivesSpaceを日本語の目録公開に使うための拡張」）の 7 章の評価を再現するための道具と、その結果です。
評価用の目録と検索語は、乱数の種を固定して道具が作ります（実在の目録ではありません）。

| 道具 | 評価 | 結果 |
|---|---|---|
| `eval_l10n.py` | E1 画面の日本語化 | `results/l10n.tsv` |
| `eval_search.py` | E2 検索（ArchivesSpace 経由。設定 (a)(b)） | `results/docs.tsv`、`queries.tsv`、`results-*.tsv` |
| `eval_bigram_core.py` | E2 検索（評価用の Solr コア。設定 (c)） | `results/results-bigram.tsv` ほか |
| `eval_bigram_weak.py` | E2 文字バイグラムが苦手とする検索語 | `results/weak-*.tsv` |
| `eval_reindex_time.py` | 5.3 節 全件を入れ直す Solr の処理時間 | `results/reindex-time.tsv` |
| `eval_iiif.py` | E3 IIIF の出力の検証 | `results/iiif.tsv` |

ArchivesSpace 4.2.1 の公式の Docker 一式を手元で動かし、このリポジトリの直下で実行します。
API の接続先と利用者は環境変数 `ASPACE_API`・`ASPACE_USER`・`ASPACE_PASSWORD` で指定します（`aspace_api.py`）。
`eval_search.py` と `eval_bigram_*.py` は Python の標準ライブラリだけ、`eval_iiif.py` は Pillow と jsonschema を使います。
