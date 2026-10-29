require "yaml"; require "json"; require "csv"
s, t = ARGV
def paths(d, p=[], o={}) ; d.is_a?(Hash) ? d.each{|k,v| paths(v, p+[k], o)} : o[p[1..].map(&:to_s).join(".")] = d; o end
file = {"common"=>"common/locales/ja.yml","enums"=>"common/locales/enums/ja.yml","frontend"=>"frontend/config/locales/ja.yml","frontend_help"=>"frontend/config/locales/help/ja.yml","public"=>"public/config/locales/ja.yml"}
mine = Hash.new{|h,k| h[k]={}}
[["ja-fixes-all.tsv","修正案"],["additions.tsv","訳"]].each{|f,col| CSV.read("#{t}/#{f}", col_sep: "\t", headers: true, quote_char: "\x00").each{|r| v=r[col].to_s.strip; mine[r["ファイル"]][r["キー"]]=v unless v.empty?}}
file.each do |c,f|
  ours = paths(YAML.load_file("#{s}/full-new/#{c}-ja.yml"))
  units = JSON.parse(File.read("#{s}/wlu/#{c}.json"))
  st = Hash.new(0); keys = {}
  units.each do |u|
    k = u["context"].gsub("->","."); keys[k]=1
    v = ours[k]; cur = u["target"].join
    if v.nil? then st["手元に無い"]+=1
    elsif !v.is_a?(String) then st["文字列でない"]+=1
    elsif cur.empty? || u["state"]<20 then st["未訳/要修正→埋まる"]+=1
    elsif v == cur then st["同じ"]+=1
    else st["変わる"]+=1 end
  end
  lost = mine[f].keys.reject{|k| keys[k]}
  puts "#{c}: Weblate #{units.size} #{st.inspect} / 手元の訳のうち Weblate に項目が無いキー #{lost.size}#{lost.first(5).inspect}"
end
