# Weblate の項目ごとに 英語・今の訳・新しい訳 を並べた TSV（変わるものだけ）と、全項目の機械検査
require "yaml"; require "json"
s = ARGV[0]
def paths(d, p=[], o={}) ; d.is_a?(Hash) ? d.each{|k,v| paths(v, p+[k], o)} : o[p[1..].map(&:to_s).join(".")] = d; o end
out = File.open("#{s}/qa/changes.tsv","w"); out.puts %w[部品 キー 英語 今の訳 新しい訳].join("\t")
all = File.open("#{s}/qa/all.tsv","w")
esc = ->(x){ x.to_s.gsub("\t"," ").gsub("\n","\\n") }
%w[common enums frontend frontend_help public].each do |c|
  ours = paths(YAML.load_file("#{s}/full-new/#{c}-ja.yml"))
  JSON.parse(File.read("#{s}/wlu/#{c}.json")).each do |u|
    k = u["context"].gsub("->","."); en = u["source"][-1]; cur = u["target"].join
    v = ours[k] || ours["#{k}.other"]; next unless v.is_a?(String)
    all.puts [c,k,esc[en],esc[v]].join("\t")
    out.puts [c,k,esc[en],esc[cur],esc[v]].join("\t") if v != cur || u["state"] < 20
  end
end
