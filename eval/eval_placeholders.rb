# 論文の評価（3.2 節・8.1 節 (1)）。同梱の訳（4.2.1）でプレースホルダ %{…} の名前が英語と食い違うキーを、
# 本体と同じ JRuby・i18n で、英語の名前で値を渡して展開する（本体の画面は英語の名前で値を渡す）。
# 結果: OK = 展開できた（出力の 5 列目が画面に出る文字列）、RAISE = 例外（画面を表示できない）。
#
# 使い方（ArchivesSpace 4.2.1 のコンテナで動かす。手元の Ruby は版が違うので使わない）:
#   docker cp eval/eval_placeholders.rb <コンテナ>:/tmp/ && docker cp translation-ja/upstream-4.2.1 <コンテナ>:/tmp/up
#   docker exec <コンテナ> sh -c 'L=/archivesspace/gems/gems/jruby-jars-9.4.9.0/lib; java -cp $L/jruby-core-9.4.9.0-complete.jar:$L/jruby-stdlib-9.4.9.0.jar org.jruby.Main /tmp/eval_placeholders.rb /tmp/up' | sort > eval/results/placeholders-interp.tsv
$LOAD_PATH.unshift("/archivesspace/gems/gems/i18n-1.14.8/lib", *Dir["/archivesspace/gems/gems/concurrent-ruby-*/lib/concurrent-ruby"])
require "i18n"
require "yaml"

def flat(h, p = "", o = {})
  if h.is_a?(Hash) then h.each { |k, v| flat(v, p.empty? ? k.to_s : "#{p}.#{k}", o) } else o[p] = h end
  o
end

up = ARGV[0]
ja = {}
en = {}
# help は画面の説明文で、プレースホルダを持たない
%w[common enums frontend public].each do |s|
  ja.merge!(flat(YAML.load_file("#{up}/#{s}/ja.yml", aliases: true)["ja"]))
  en.merge!(flat(YAML.load_file("#{up}/#{s}/en.yml", aliases: true)["en"]))
end
ph = /%\{([^}]+)\}/
en.each do |k, e|
  next unless e.is_a?(String) && ja[k].is_a?(String)
  a = e.scan(ph).flatten.sort
  b = ja[k].scan(ph).flatten.sort
  next if a == b
  args = Hash[a.map { |n| [n.to_sym, "<#{n}>"] }]
  begin
    out = I18n.interpolate(ja[k], args)
    r = "OK"
  rescue => ex
    out = ex.class.name
    r = "RAISE"
  end
  # 列: 結果、キー、訳にだけある名前、訳に無い名前、展開した文字列
  puts [r, k, (b - a).uniq.join(","), (a - b).uniq.join(","), out.to_s.gsub("\n", " ")].join("\t")
end
