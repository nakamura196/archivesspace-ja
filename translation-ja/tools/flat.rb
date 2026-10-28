require "yaml"
def flat(d,p="",o={}) ; if d.is_a?(Hash) then d.each{|k,v| flat(v, p.empty? ? k.to_s : "#{p}.#{k}", o)} else o[p]=d end; o end
def load(f) YAML.load_file(f) end
up=ARGV[0]
%w[common_locales common_locales_enums frontend_config_locales public_config_locales].each do |n|
  en=flat(load("#{up}/#{n}_en.yml")).transform_keys{|k|k.sub(/^en\./,"")}
  ja=flat(load("#{up}/#{n}_ja.yml")).transform_keys{|k|k.sub(/^ja\./,"")}
  File.open("#{up}/../#{n}.tsv","w"){|f| en.each{|k,v| f.puts [k, v.to_s.gsub(/\s+/," ")[0,300], ja.key?(k) ? ja[k].to_s.gsub(/\s+/," ")[0,300] : "<<MISSING>>"].join("\t")}}
  miss=en.keys-ja.keys
  same=en.select{|k,v| v.is_a?(String) && ja[k]==v && v=~/[A-Za-z]{3}/}.keys
  asc=en.select{|k,v| ja[k].is_a?(String) && ja[k]!=v && ja[k]!~/[぀-ヿ一-鿿]/ && ja[k]=~/[A-Za-z]{4}/}.keys
  puts "#{n}: en=#{en.size} ja=#{ja.size} missing=#{miss.size} same=#{same.size} ascii=#{asc.size}"
end
