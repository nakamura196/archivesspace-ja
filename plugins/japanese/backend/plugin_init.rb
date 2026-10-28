# スタッフ画面のレポート（PDF など）を日本語で出す。
# (1) 本体のレポートには、項目名の共通の訳（reports.translation_defaults）の日本語版が無い。
#     訳が無いと、項目名「repository」などが同名の別の訳（リポジトリの入力項目一式）に
#     落ちて、見出しに中身がそのまま流れ込む。日本語版をここで足す。
# (2) レポートの PDF は既定で DejaVu Sans を使い、漢字・仮名が消える。
#     本体に同梱の Kurinto Text JP（漢字・仮名・ラテン文字あり）に替える。
I18n.load_path += Dir[File.join(File.dirname(__FILE__), 'locales', '*.yml')]

AppConfig[:report_pdf_font_paths] = proc {
  %w[Rg Bd].map { |w| "file:///archivesspace/stylesheets/fonts/KurintoTextJP-#{w}.ttf" }
}
AppConfig[:report_pdf_font_family] = "\"Kurinto Text JP\", sans-serif"
