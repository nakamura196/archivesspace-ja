require "yaml"
def flat(d,p="",o={}) ; if d.is_a?(Hash) then d.each{|k,v| flat(v, p.empty? ? k.to_s : "#{p}.#{k}", o)} else o[p]=d end; o end
ARGV.each_slice(2) do |enf, jaf|
  en=flat(YAML.load_file(enf)).transform_keys{|k|k.sub(/^en\./,"")}
  ja=flat(YAML.load_file(jaf)).transform_keys{|k|k.sub(/^ja\./,"")}
  en.each{|k,v| next unless v.is_a?(String) && ja[k].is_a?(String)
    a=v.scan(/%\{[^}]+\}/).uniq.sort; b=ja[k].scan(/%\{[^}]+\}/).uniq.sort
    extra=b-a; miss=a-b
    puts [File.basename(jaf),k,"ja-only:#{extra.join(',')}","missing:#{miss.join(',')}"].join("\t") unless extra.empty? && miss.empty? }
end
