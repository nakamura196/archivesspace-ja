# 使い方: ruby build_weblate.rb <master の yml フォルダ> <translation-ja> <出力フォルダ>
# master の ja.yml に ja-fixes-all.tsv（修正案）と additions.tsv（訳）を重ね、英語に無いキーを除いた完全な ja.yml を作る
require "yaml"; require "csv"
up, tj, out = ARGV
COMP = {"common/locales/ja.yml"=>["common","common_locales"], "common/locales/enums/ja.yml"=>["enums","common_locales_enums"],
        "frontend/config/locales/ja.yml"=>["frontend","frontend_config_locales"],
        "frontend/config/locales/help/ja.yml"=>["frontend_help","frontend_config_locales_help"],
        "public/config/locales/ja.yml"=>["public","public_config_locales"]}
def paths(d, p=[], o={}) ; d.is_a?(Hash) ? d.each{|k,v| paths(v, p+[k], o)} : o[p[1..].map(&:to_s).join(".")] = [p[1..], d]; o end
vals = Hash.new{|h,k| h[k] = {}}
[["ja-fixes-all.tsv","修正案"],["additions.tsv","訳"]].each do |f,col|
  CSV.read("#{tj}/#{f}", col_sep: "\t", headers: true, quote_char: "\x00").each do |r|
    v = r[col].to_s.strip; next if v.empty?
    vals[r["ファイル"]][r["キー"]] = v.gsub('\n', "\n")
  end
end
COMP.each do |file,(slug,base)|
  en = paths(YAML.load_file("#{up}/#{base}_en.yml"), [], {})
  ja = paths(YAML.load_file("#{up}/#{base}_ja.yml"), [], {})
  tree = {}; stat = Hash.new(0); bad = []
  en.each do |k,(path,env)|
    next if path[-1] == "one" && en.key?(k.sub(/one\z/, "other")) # 日本語の複数形は other だけ（Weblate も 1 形）
    v = vals[file][k] || (ja[k] && ja[k][1])
    if v.nil? || (v.is_a?(String) && v.empty?) then stat["訳なし"] += 1; next end
    if env.is_a?(String) && v.is_a?(String) && env.scan(/%\{[^}]+\}/).sort != v.scan(/%\{[^}]+\}/).sort
      bad << k; v = ja[k] && ja[k][1]; next if v.nil?
    end
    stat[vals[file][k] ? "手元の訳" : "上流のまま"] += 1
    node = path[0..-2].inject(tree){|h,x| h[x] ||= {}}
    node[path[-1]] = v
  end
  File.write("#{out}/#{slug}-ja.yml", {"ja"=>tree}.to_yaml(line_width: -1))
  puts "#{slug}: 英語 #{en.size} / #{stat.inspect}#{bad.empty? ? "" : " / %{}食い違いで上流を使用: #{bad.join(', ')}"}"
end
