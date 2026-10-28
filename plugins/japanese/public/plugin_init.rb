# 閲覧者向け画面の PDF（目録）を日本語で出す。
# PDF を作る部品（Flying Saucer）は font-family の先頭のフォントだけで字を探し、
# 2 番目以降へ切り替えない。既定の先頭 Kurinto Text には漢字が無く、漢字だけが消える。
# 漢字・仮名・ラテン文字を持つ Kurinto Text JP を先頭に置く（フォントは本体に同梱済み）。
AppConfig[:pui_pdf_font_name] = "Kurinto Text JP,Kurinto Text,Noto Serif"

# アラート（flash）の閉じるボタンの読み上げ用「Close」は helper に直書きされていて、ひな形では直せない。
# helper の同じメソッドを、「Close」だけ訳が効く形にして上書きする（本体 4.2.1 の flash_messages と同じ中身）。
Rails.application.config.to_prepare do
  module JapaneseFlashPatch
    def flash_messages(opts = {})
      flash.each do |msg_type, message|
        concat(content_tag(:div, message, class: "alert #{bootstrap_class_for(msg_type)} alert-dismissible", role: 'alert') do
          concat(content_tag(:button, class: 'close', data: { dismiss: 'alert' }) do
            concat content_tag(:span, '&times;'.html_safe, 'aria-hidden' => true)
            concat content_tag(:span, I18n.t('japanese.alert_close', default: 'Close'), class: 'sr-only')
          end)
          concat (message.is_a?(Array) ? message.join('<br/>').html_safe : message.html_safe)
        end)
      end
      nil
    end
  end
  ApplicationHelper.prepend(JapaneseFlashPatch) unless ApplicationHelper.ancestors.include?(JapaneseFlashPatch)
end
