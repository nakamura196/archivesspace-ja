# ArchivesSpace 日本語訳の誤り一覧

上流 archivesspace/archivesspace の日本語訳を読み、誤訳・未訳・不自然な訳を拾った一覧。
Weblate（https://hosted.weblate.org/projects/archivesspace-interfaces/ ）で直すために使う。

- 基準: 上流 master `98efd1dc9f`（2026-10-28）。この時点で Weblate の日本語は GitHub と同じ（Weblate 側だけの未反映の変更は無かった）
- 作成: 2026-10-27。修正案は AI の下訳。珍しい文字名・法律上の役割名・長いメッセージ（`slug_generation`、`too_many_rows_warning`）は裏付けが弱い
- 画面での確認: 手元の v4.2.1（localhost:8090）で、資料群の表示・編集画面と受入の一覧を見た。確認した行は「確認」列に「画面で確認」とある

## ファイル

| ファイル | 中身 |
|---|---|
| `archivesspace-ja-fixes.xlsx` | 下の 3 つの TSV を 1 冊にしたもの |
| `ja-fixes-grouped.tsv` | 同じ英語・同じ訳を 1 行にまとめたもの（1,359 行） |
| `ja-fixes-all.tsv` | キーごとに 1 行（2,289 行） |
| `missing.tsv` | 日本語のキーが無いもの（936 件。うち staff 画面 762） |
| `placeholders.tsv` | `%{…}` の名前が英語と合わないキー。画面がエラーになるおそれがある |
| `review/A〜D.tsv` | 分担して見た元の結果（A・B = common、C = enums、D = frontend と public） |
| `weblate-upload/*-ja.yml` | 重さ「高」とプレースホルダの行だけを、Weblate に読み込ませる形にしたもの（233 キー） |

## 用語の方針

Accession = 受入、Finding Aid = 検索手段、Extent = 数量、Suppress = 非表示、Deaccession = 除籍、
Subject = 件名、fonds = フォンド、True / False = はい / いいえ。
ただし、エージェントに付ける Terms は「細目」とする（見出しの下位区分のため）。

## 作り直し方

`tools/` のスクリプトで作った。元の YAML は上流から取り直す。

```
ruby tools/flat.rb <上流の yml を置いたフォルダ>                # 英語と日本語を突き合わせた TSV
python3 tools/merge.py <review/ の親フォルダ>                    # A〜D をまとめる（パスは中で out/ を見る）
ruby tools/upload_yaml.rb <上流フォルダ> ja-fixes-all.tsv weblate-upload
ruby tools/ph.rb <en.yml> <ja.yml> ...                            # %{…} の食い違いを出す
```
