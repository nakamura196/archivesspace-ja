# ArchivesSpace 日本語訳の誤り一覧

上流 archivesspace/archivesspace の日本語訳を読み、誤訳・未訳・不自然な訳を拾った一覧。
Weblate（https://hosted.weblate.org/projects/archivesspace-interfaces/ ）で直すために使う。

- 基準: 上流 master `98efd1dc9f`（2026-10-28）。この時点で Weblate の日本語は GitHub と同じ（Weblate 側だけの未反映の変更は無かった）
- 作成: 2026-10-27。修正案は AI の下訳。珍しい文字名・法律上の役割名・長いメッセージ（`slug_generation`、`too_many_rows_warning`）は裏付けが弱い
- 画面での確認: 手元の v4.2.1（localhost:8090）で、資料群の表示・編集画面と受入の一覧を見た。確認した行は「確認」列に「画面で確認」とある

## Weblate に入れた訳の前後一覧（2026-10-28）

`style-review/qa-2026-10-28/changes-after.tsv` は、2026-10-28 に Weblate へアップロードした訳の、変える前と変えた後の一覧（2,770 行）。
列は 部品・キー・英語・今の訳（アップロード前の Weblate）・新しい訳。改行は `\n` の 2 文字で書いてある。

- 書き換え 2,448・未訳の穴埋め 320・訳は同じで「要修正」の印だけ外したもの 2
- 部品ごと: common 937・enums 714・frontend 868・frontend_help 51・public 200
- Weblate 上で実際に更新されたのは 2,746 件。アップロード後に Weblate から取り直した訳は `weblate-upload/full/` と全件一致した
- 基準は上流 master `2b29a1c660`（`style-review/qa-2026-10-28/master-sha.txt`）
- 訳は AI の下訳を、3 系統（Sonnet・Opus・Gemini）の点検と人の確認で直したもの。点検の記録は同じフォルダの `review*.tsv`・`merged.tsv`・`dec*.tsv`

English: `style-review/qa-2026-10-28/changes-after.tsv` lists every Japanese string changed on Hosted Weblate on 2026-10-28
(component, key, English source, previous Japanese, new Japanese; 2,770 rows: 2,448 rewrites, 320 previously untranslated, 2 flag-only).

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

2026-10-28 に追加で決めた語: Location = 所在、Note = 注記（連絡先の「メモ」は除く）、Type = 種類（MIME タイプは除く）、
Default = 既定、Resource = リソース、Classification Term = 分類項目。表記は長音を付ける（サーバー）、文末のコロンは全角。
上流の訳だけにある語も、ja-fixes-all.tsv に区分「用語統一」で足して置き換えている。

## Weblate に入れるファイル

`weblate-upload/full/<部品>-ja.yml` は、上流 master（2b29a1c660）の ja.yml に ja-fixes-all.tsv と additions.tsv を重ねた完全な訳。
英語にあるキーはすべて訳がある。作り直し:

```
ruby tools/build_weblate.rb <master の en/ja を置いたフォルダ> . weblate-upload/full
```

master のファイル名は `common_locales_en.yml` のように、パスの `/` を `_` にしたもの（common・enums・frontend・frontend/help・public）。

2026-10-28 に作り直した（master はまだ 2b29a1c660）。Weblate の今の訳と突き合わせると、
アップロードで変わるのは 2,457 件（書き換え 2,085・未訳の穴埋め 372）。

注意:

- 日本語の複数形は `other` だけ。`one` は入れない（Weblate の日本語も 1 形）
- 上流の en.yml は別名参照（`<<: *名前`）で項目を使い回している。受け継いだだけのキーは Weblate に項目が無く、
  アップロードしても読み飛ばされる。画面には受け継ぎ元の訳が出る。手元で受け継ぎ元と違う訳を付けたキーが 283 件あるが、
  Weblate では表せない
- 2026-10-28 夕方、3 系統（Sonnet・Opus・Gemini）の点検で出た 349 件を Opus で英語と照らして確かめ、338 件を直した
  （判定は `style-review/qa-2026-10-28/dec*.tsv`、書き戻しは同じフォルダの `apply.py`）。統制値リスト・分類項目・最上位コンテナの揺れも機械で揃えた。
  続けて、同じ英語なのに訳が割れていた 146 組を仕分け、116 件を揃えた（団体・典拠ID・整理・レコード・記録群・主 など。判定は `dec4.tsv`）。
  2 回目以降の書き戻しは `BASE=all-after.tsv python3 apply.py <判定 TSV>`。直したあとの差分は `changes-after.tsv`（2,770 件）
- 2026-10-28 夜に 5 部品ともアップロード済み（更新 frontend_help 51・public 200・common 925・enums 714・frontend 856）。取り直した Weblate の訳は full/ と全件一致
- 2026-10-28 夜、手元の画面で確かめたところ、Weblate の直しが届いていないキーが見つかった（日付の説明文の「死んだ」など）。
  上流の en.yml が別名参照で使い回しているキーと、4.2.1 と master で英語が少し違うキーは、Weblate では 1 か所を直せば済むが、
  手元の上書きはキーごとに訳を持つため。`style-review/qa-2026-10-28/propagate.py`（英語と末尾のキーが同じものに直しを広げる、192 件）と
  `oldterms.py`（画面に出る訳から古い語を探して直す、53 件）で埋めた。Weblate の項目で変わったのは
  `help.topics.agent_corporate_entity`（コーポレートエンティティ→団体）の 1 件だけで、これは Weblate にまだ入れていない
- 入れ方: 各部品の日本語のページ → ファイル → 翻訳をアップロード。
  「Add as translation」＋「Change translated strings」（承認済みは使っていない）。「Translate」の役割で足りる

## 作り直し方

`tools/` のスクリプトで作った。元の YAML は上流から取り直す。

```
ruby tools/flat.rb <上流の yml を置いたフォルダ>                # 英語と日本語を突き合わせた TSV
python3 tools/merge.py <review/ の親フォルダ>                    # A〜D をまとめる（パスは中で out/ を見る）
ruby tools/upload_yaml.rb <上流フォルダ> ja-fixes-all.tsv weblate-upload
ruby tools/ph.rb <en.yml> <ja.yml> ...                            # %{…} の食い違いを出す
```
