# 使い方: ruby upload_yaml.rb <上流の en/ja を置いたフォルダ> <ja-fixes-all.tsv> <出力フォルダ>
# 重さ「高」と区分「プレースホルダ」の行だけを、Weblate に読み込ませる ja.yml の断片にする
require "yaml"; require "csv"
up, tsv, out = ARGV
def paths(d, p=[], o={}) ; d.is_a?(Hash) ? d.each{|k,v| paths(v, p+[k], o)} : o[p[1..].map(&:to_s).join(".")] = p; o end
comp = {"common/locales/ja.yml"=>["common","common_locales"], "common/locales/enums/ja.yml"=>["enums","common_locales_enums"],
        "frontend/config/locales/ja.yml"=>["frontend","frontend_config_locales"], "public/config/locales/ja.yml"=>["public","public_config_locales"]}
rows = CSV.read(tsv, col_sep: "\t", headers: true, quote_char: "\x00")
comp.each do |file,(slug,base)|
  pmap = paths(YAML.load_file("#{up}/#{base}_ja.yml")).merge(paths(YAML.load_file("#{up}/#{base}_en.yml")).transform_values{|p| ["ja"]+p[1..]})
  tree = {}; n = 0; miss = []
  rows.each do |r|
    next unless r["ファイル"] == file && (r["重さ"] == "高" || r["区分"] == "プレースホルダ")
    p = pmap[r["キー"]] or (miss << r["キー"]; next)
    p = ["ja"] + p[1..]
    p[0..-2].inject(tree){|h,k| h[k] ||= {}}[p[-1]] = r["修正案"]; n += 1
  end
  File.write("#{out}/#{slug}-ja.yml", tree.to_yaml(line_width: -1))
  puts "#{slug}: #{n} keys#{miss.empty? ? "" : " / キーが見つからない: #{miss.join(', ')}"}"
end
