# 論文の評価の道具とデータ

論文（中村・金「ArchivesSpaceを日本語の目録公開に使うための拡張」）の 7 章の評価を再現するための道具と、その結果です。
評価には 2 種類の目録を使います。
1 つは評価用に設計した目録で、題名と検索語は乱数の種を固定して道具が作ります（実在の目録ではありません）。
もう 1 つは国立公文書館の公開目録（公文録・明治９年）です。下の「国立公文書館の目録での評価」を見てください。

| 道具 | 評価 | 結果 |
|---|---|---|
| `eval_l10n.py` | E1 画面の日本語化 | `results/l10n.tsv` |
| `eval_placeholders.rb` | 3.2・8.1 節 同梱の訳の差し込み部分の食い違いを、本体と同じ JRuby・i18n で展開する | `results/placeholders-interp.tsv` |
| `eval_search.py` | E2 検索（ArchivesSpace 経由。設定 (a)(b)） | `results/docs.tsv`、`queries.tsv`、`results-*.tsv` |
| `eval_bigram_core.py` | E2 検索（評価用の Solr コア。設定 (c)(d)） | `results/results-bigram.tsv`、`results-bigram-uni.tsv` ほか |
| `eval_bigram_weak.py` | E2 文字バイグラムが苦手とする検索語 | `results/weak-*.tsv` |
| `eval_reindex_time.py` | 5.3 節 全件を入れ直す Solr の処理時間と索引の大きさ（設定 (a)(c)(d)） | `results/reindex-time.tsv`、`reindex-time-runs.tsv`（3 回流した各回を並べたもの。論文の値はその中央値） |
| `eval_index_size_merge.py` | 5.3 節 索引の大きさが回ごとにばらつく理由（登録直後と統合後） | `results/reindex-size-merge.tsv` |
| `eval_iiif.py` | E3 IIIF の出力の検証 | `results/iiif.tsv` |
| `naj_fetch.py` | 7.1・7.4 国立公文書館「公文録・明治９年」の目録を取る（目録情報は CC0） | `data/naj/raw`（git には入れない） |
| `eval_naj_search.py` | 7.4 E2 実際の目録での検索（設定 (a)〜(d)） | `results/naj/search.tsv`、`search-summary.md` |
| `import_naj.py` | 7.1 国立公文書館の目録を ArchivesSpace に入れる | `results/naj/import-log.md` |
| `eval_core_unchanged.zsh` | E4 本体を改変しないこと | `results/core-diff.txt`、`core-diff-d.txt`（設定 (d) のスキーマ） |

ArchivesSpace 4.2.1 の公式の Docker 一式を手元で動かし、このリポジトリの直下で実行します。
API の接続先と利用者は環境変数 `ASPACE_API`・`ASPACE_USER`・`ASPACE_PASSWORD` で指定します（`aspace_api.py`）。
`eval_search.py` と `eval_bigram_*.py` は Python の標準ライブラリだけ、`eval_iiif.py` は Pillow と jsonschema を使います。

## 国立公文書館の目録での評価

7.4 節では、設計した目録で確かめた結果が実際の目録でも成り立つかを見ました。
使ったのは、国立公文書館デジタルアーカイブの「公文録・明治９年」の件名 6,162 件の題名です（目録情報は CC0）。
目録は配布物に含めていません。`naj_fetch.py` で SPARQL エンドポイントから取ってください。

```
python3 eval/naj_fetch.py
python3 eval/eval_naj_search.py setup
python3 eval/eval_naj_search.py run
python3 eval/eval_naj_search.py drop
```

`setup` は、Solr に 4 つの設定 (a)〜(d) のコアを作り、題名を入れます（Solr のコンテナ名は `solr` とします。`eval_bigram_core.py` と同じです）。
`run` は、題名から検索語を乱数で切り出し（乱数の種 20261028）、4 つのコアで検索して `results/naj/` に書きます。
検索の条件は、ArchivesSpace が Solr に送る条件と同じです。
正解は Solr を使わずに決めます。旧字体を新字体に寄せたうえで、検索語を部分文字列として含む題名を正解とします。
検索語は語の切れ目を考えずに切り出すので、語をまたぐ文字列も含みます。

2026-10-28 の結果は `results/naj/search-summary.md` にあります。
173 語のうち、題名の部分文字列の検索と結果が一致したのは、(a) 43 語、(b) 70 語、(c) 149 語、(d) 171 語でした。
(c) で 1 件も返らなかった 22 語は、すべて 1 字の検索語です。
このリポジトリの直下で取り直すと、`search.tsv` は 10-28 のものと同じになります（11-01 に確認）。
なお `setup` を走らせると、`plugins/japanese/solr/itaiji-mapping.txt` の 1 行目のコメントが書き換わります（対応表そのものは変わりません）。

`import_naj.py` は、同じ目録を ArchivesSpace 本体に入れる道具です（7.1 節）。
資料群 1 件の下に簿冊 283 件、その下に件名 6,162 件を置きます。
`--mode naive` は目録をそのまま写し、`--mode fixed` は並び順と日付に手当てをします。
起きたことと手当ての中身は `results/naj/import-log.md` に書きました。
