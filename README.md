# archivesspace-ja

ArchivesSpace 4.2.1 を日本語で使うためのプラグインと設定です。
本体のプログラムは書き換えず、プラグインと Solr の設定だけで、次の 3 つを行います。

- 画面の日本語化（同梱の日本語訳の誤りと訳の無い項目を上書きする）
- 旧字体と新字体を同一視する検索（常用漢字表の旧字体の対応表を Solr の同義語として登録する）
- 文字バイグラムによる検索（字の並びとカタカナ語の部分一致。導入には全件の索引の作り直しが要る）

あわせて、目録の階層から IIIF Presentation API 3.0 の Manifest と Collection を出力するプラグインを、参考実装として含みます。

English summary: plugins and Solr settings for using ArchivesSpace 4.2.1 in Japanese — corrected Japanese UI strings,
old/new kanji form folding at search time, an optional character-bigram analyzer, and a reference IIIF plugin.
No changes to the ArchivesSpace core code are needed.

## 中身

| 場所 | 中身 |
|---|---|
| `plugins/local` | 訳の上書き（`ja-fixes.yml` は `translation-ja/tools/build_overrides.py` が作る。手で直さない） |
| `plugins/japanese` | ひな形の上書き、出力の後置換、帳票のフォント、旧字体の対応表（`solr/`） |
| `plugins/ja_theme` | 公開画面の見た目（MIT License。https://github.com/nakamura196/aspace-theme-ja と同じもの） |
| `plugins/iiif_manifest` | IIIF の出力（参考実装。使い方は同じフォルダの README） |
| `solr/bigram-text_general.xml` | 文字バイグラムの設定（Solr の `text_general` を置き換える） |
| `scripts/solr-itaiji.zsh` | 旧字体の同義語を Solr に入れる |
| `scripts/solr-bigram.zsh` | Solr を文字バイグラムの設定に替える |
| `scripts/make_itaiji_mapping.py` | 対応表から文字バイグラム用の置き換え表を作る |
| `translation-ja/` | 同梱の日本語訳の点検結果と、それを作る道具（修正案は AI の下訳を人が確かめたもの） |
| `config/config.rb.example` | `config.rb` に足す行の例 |

## 導入

公式の Docker 一式（ArchivesSpace 4.2.1）を前提にします。段階 1 だけでも使えます。

### 段階 1: 画面の日本語化

1. `plugins/` の下のフォルダを、ArchivesSpace の `plugins/` に置く
2. `config.rb` に表示言語とプラグインの名前を足す（`config/config.rb.example`）
3. ArchivesSpace を再起動する

### 段階 2: 旧字体と新字体を同一視する検索（索引の作り直しは要らない）

`config.rb` に `AppConfig[:solr_verify_checksums] = false` を足してから、docker compose のあるフォルダで:

```
zsh <このリポジトリ>/scripts/solr-itaiji.zsh setup
zsh <このリポジトリ>/scripts/solr-itaiji.zsh load
```

### 段階 3: 文字バイグラム（全件の索引の作り直しが要る）

段階 2 の代わりに使う（旧字体は置き換え表で扱うので、段階 2 の同義語は要らない）。

```
zsh <このリポジトリ>/scripts/solr-bigram.zsh setup
```

そのあと、公式の手順（https://docs.archivesspace.org/administration/indexes/ ）で全件の索引を作り直す。
ArchivesSpace を止め、`data/indexer_state/` と `data/indexer_pui_state/` を消し、Solr の文書をすべて消してから、再起動する。
1 字だけの検索語は見つかりにくくなる。

## ライセンス

Educational Community License 2.0（ArchivesSpace と同じ。`LICENSE`）。
訳ファイルとひな形は ArchivesSpace 本体のファイルを元にしている。
`plugins/ja_theme` だけは MIT License（`plugins/ja_theme/LICENSE`）。

## 作成

中村 覚（東京大学）、金 甫榮（人間文化研究機構）
