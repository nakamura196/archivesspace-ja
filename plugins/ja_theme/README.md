# aspace-theme-ja

ArchivesSpace の公開画面（PUI）のための、日本語向けの見た目のプラグインです。
ほぼ CSS だけで動きます。画面の HTML（ERB）に手を入れるのは、トップの入口のカードと、検索欄の 2 か所だけです。
本体のひな形をまるごと上書きしているのは検索欄（`shared/_search.html.erb`）だけです。

- 淡いグレーの地に白いカード、上端に固定される 1 段のヘッダー
- 大きな検索欄、絞り込みはチップ
- トップとリポジトリの画面では、詳しい検索条件を最初は畳んでおく
- 資料の項目は「項目名｜値」の 2 段組
- 資料の木は広めにとり、深い階層でも名前を折り返して全部見せる
- トップに入口のカード
- 外部のサーバーから文字を読み込みません（端末に入っている日本語の文字を使います）

ArchivesSpace v4.2.1 で確認しています。

## 入れ方

```sh
cd /path/to/archivesspace/plugins
git clone https://github.com/nakamura196/aspace-theme-ja.git ja_theme
```

`config/config.rb` の `AppConfig[:plugins]` に `ja_theme` を足し、ArchivesSpace を再起動します。

```ruby
AppConfig[:plugins] = ['local', 'ja_theme']
```

フォルダ名は `ja_theme` にしてください。設定に書く名前と同じである必要があります。

画面の言葉を日本語にするのは、このプラグインの役目ではありません（`AppConfig[:locale] = :ja` と、訳の上書き用のプラグインで行います）。

## 色や文字を館ごとに変える

このプラグインのファイルは書き換えず、館用のプラグインを 1 つ作って変数だけを上書きします。

ArchivesSpace は、すべてのプラグインの `public/views/layout_head.html.erb` を、`AppConfig[:plugins]` に並べた順に読み込みます。
そのため、後ろに並べたプラグインの値が勝ちます。

```
plugins/my_theme/public/views/layout_head.html.erb
```

```erb
<style>
  :root {
    --c-accent: #2292ca;
    --c-accent-dark: #17709d;
    --c-accent-light: #39a9dd;
    --c-accent-soft: #e7f3fa;
    --c-accent-line: #bfdcee;
    --c-focus-ring: 0 0 0 3px rgba(34, 146, 202, .18);
    --c-hero-top: #eaf4fa;
    --c-hero-glow: rgba(34, 146, 202, .14);
  }
</style>
```

```ruby
AppConfig[:plugins] = ['local', 'ja_theme', 'my_theme']
```

Web フォントを使いたいときも、同じファイルに `<link>` を足します。

### 変数の一覧

| 種類 | 変数 |
|---|---|
| 文字 | `--c-font` |
| 差し色 | `--c-accent` `--c-accent-dark` `--c-accent-light` `--c-accent-soft` `--c-accent-line` `--c-on-accent` `--c-focus-ring` |
| トップの帯 | `--c-hero-top` `--c-hero-glow` |
| 文字の濃淡 | `--c-text` `--c-sub` `--c-muted` `--c-placeholder` `--c-disabled` |
| 面 | `--c-bg` `--c-surface` `--c-soft` `--c-segment-bg` `--c-segment-hover` `--c-header-bg` |
| 罫線・強調 | `--c-line` `--c-line-strong` `--c-mark` |
| 角丸 | `--c-radius` `--c-radius-sm` `--c-radius-lg` `--c-radius-pill` `--c-btn-radius` `--c-action-radius` |
| 影 | `--c-shadow` `--c-shadow-hover` `--c-shadow-pop` `--c-shadow-modal` |
| 幅 | `--c-max` |

## トップの入口のカード

トップの検索欄の下に、メニューと同じ入口（リポジトリ・コレクション・デジタル資料など）をカードで並べます。
本体のトップ画面が用意している差し込み口 `public/views/_welcome_addition.html.erb` を使うので、トップ画面のひな形そのものは上書きしません。
`AppConfig[:pui_hide]` でメニューから隠した入口は、カードにも出ません。

カードの見出しは本体の訳を使います。説明文はこのプラグインの `public/locales/ja.yml`・`en.yml` にあります。
説明文を館ごとに変えるときは、後ろに並べたプラグインの `public/locales/ja.yml` に、変えたいものだけを書きます。

```yaml
ja:
  ja_theme:
    welcome:
      desc:
        subject: 写真の主題や撮影地から探す
```

キーは `heading`（カード群の見出し）と、`desc.` に続く `repository` `resource` `digital_object` `accession` `subject` `pui_agent` `classification` です。
訳の変更は、ArchivesSpace を再起動すると反映されます。

## 検索欄（詳しい条件の折りたたみ）

トップとリポジトリの画面では、最初はキーワードの欄と検索ボタンだけを出します。
「詳しい条件」を押すと、種別・項目・年代などの条件が開きます。
すでに条件が入っているときは、開いた状態で出します。
検索結果の画面の「検索を絞り込む」の中では畳みません。

このために、本体の `public/app/views/shared/_search.html.erb`（v4.2.1）を写して `public/views/shared/_search.html.erb` に置き、書き換えています。
**ArchivesSpace 本体を上げたときは、新しい版のこのファイルを写し直して、同じ変更を当て直してください。**
本体の検索欄の変更が、このプラグインを入れている間は反映されないためです。

ボタンの文言は `ja_theme.search.more`（詳しい条件 / More options）で、ほかと同じく後ろのプラグインの locales で変えられます。
このファイルの変更は、ArchivesSpace を再起動すると反映されます。

## English

A theme for the ArchivesSpace Public User Interface, designed for Japanese-language sites. It is mostly CSS, plus entry cards on the home page and a collapsible search form.
The only core template it overrides is the search form (`shared/_search.html.erb`, copied from v4.2.1). On the home and repository pages the advanced fields start collapsed behind a "More options" button (`ja_theme.search.more`) and open automatically when a search is already filtered. When you upgrade ArchivesSpace, re-copy that file from the new version and re-apply the changes.
Clone it into `plugins/ja_theme` and add `ja_theme` to `AppConfig[:plugins]`.
To customise colours or fonts, create another plugin whose `public/views/layout_head.html.erb` overrides the `--c-*` CSS variables in `:root`, and list it after `ja_theme`.
The home-page entry cards use the `_welcome_addition.html.erb` hook and are built from the main menu; override their descriptions (`ja_theme.welcome.desc.*`) in a later plugin's `public/locales/*.yml`.
The collection tree is wider, uses a 12px indent per level, and wraps long titles instead of truncating them.
Tested with ArchivesSpace v4.2.1.

## ライセンス

MIT License。作成: 中村 覚（東京大学） / Satoru Nakamura (The University of Tokyo)
