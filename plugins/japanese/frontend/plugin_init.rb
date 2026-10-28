# スタッフ画面の Ruby コード（helpers/application_helper.rb）に直書きされた英語を日本語にする。
# ひな形（erb）と違い、helper はプラグインで丸ごと差し替えられないので、出力の英語部分だけを後から置き換える。
#  - ヘルプ欄の読み上げ用の「Visit the …」
#  - 作成者・最終更新者の行の「URI:」と語順
Rails.application.config.to_prepare do
  module JapaneseHelperPatch
    def link_to_help(opts = {})
      html = super(opts)
      return html if html.nil?
      name = I18n.t("help.help_center")
      visit = I18n.t("japanese.help_visit", name: name, default: "Visit the #{name}")
      html.to_s.sub(" Visit the #{name}", " #{visit}").html_safe
    end

    def display_audit_info(hash, opts = {})
      html = super(hash, opts).to_s
      return html.html_safe unless hash['create_time'] and hash['user_mtime']
      created = I18n.t("search_results.created")
      modified = I18n.t("search_results.modified")
      html = html.sub("#{created} #{hash['created_by']}",
                      I18n.t("japanese.audit_created", user: hash['created_by'], default: "#{created} #{hash['created_by']}"))
      html = html.sub("#{modified} #{hash['last_modified_by']}",
                      I18n.t("japanese.audit_modified", user: hash['last_modified_by'], default: "#{modified} #{hash['last_modified_by']}"))
      html = html.sub("<strong>URI:</strong>", "<strong>#{I18n.t('japanese.audit_uri', default: 'URI')}:</strong>")
      html.html_safe
    end
  end
  ApplicationHelper.prepend(JapaneseHelperPatch) unless ApplicationHelper.ancestors.include?(JapaneseHelperPatch)
end
