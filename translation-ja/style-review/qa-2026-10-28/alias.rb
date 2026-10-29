require "yaml"; require "json"
s = ARGV[0]
def paths(d, p=[], o={}) ; d.is_a?(Hash) ? d.each{|k,v| paths(v, p+[k], o)} : o[p[1..].map(&:to_s).join(".")] = d; o end
# 展開後のキー → 受け継ぎ元のキー（英語ファイルの構造から）
def walk(node, path, anchors, origin, from=nil)
  case node
  when Psych::Nodes::Document then walk(node.children[0], path, anchors, origin)
  when Psych::Nodes::Mapping
    anchors[node.anchor] = path if node.anchor
    node.children.each_slice(2) do |k,v|
      if k.value == "<<"
        src = anchors[v.anchor] # Alias
        sub = $leaf[src] || []
        sub.each{|rel| origin[(path+rel).join(".")] ||= (src+rel).join(".")}
      else walk(v, path+[k.value], anchors, origin) end
    end
    $leaf[path] = collect(node)
  when Psych::Nodes::Alias
    src = anchors[node.anchor]; (( $leaf[src]||[[]] )).each{|rel| origin[(path+rel).join(".")] ||= (src+rel).join(".")}
  else anchors[node.anchor] = path if node.respond_to?(:anchor) && node.anchor
  end
end
def collect(node, rel=[])
  return [rel] unless node.is_a?(Psych::Nodes::Mapping)
  node.children.each_slice(2).flat_map{|k,v| k.value=="<<" ? ($leaf[$anch[v.anchor]]||[]).map{|r| rel+r} : collect(v, rel+[k.value])}
end
{"common"=>"common_locales","enums"=>"common_locales_enums","frontend"=>"frontend_config_locales","public"=>"public_config_locales"}.each do |c,b|
  $leaf = {}; anchors = {}; $anch = anchors; origin = {}
  walk(Psych.parse_file("#{s}/master/#{b}_en.yml"), [], anchors, origin)
  ours = paths(YAML.load_file("#{s}/full-new/#{c}-ja.yml"))
  origin = origin.transform_keys{|k| k.sub(/^en\./,"")}.transform_values{|v| v.sub(/^en\./,"")}
  units = JSON.parse(File.read("#{s}/wlu/#{c}.json")).map{|u| [u["context"].gsub("->","."),1]}.to_h; origin.reject!{|k,_| units[k]}; same = diff = 0; ex = []
  origin.each{|k,o| next unless ours.key?(k); if ours[k]==ours[o] then same+=1 else diff+=1; ex << [k, ours[k], o, ours[o]] if ex.size<40 end}
  puts "#{c}: 受け継ぎキー #{origin.size} / 元と同じ訳 #{same} / 元と違う訳 #{diff}"; ex.each{|e| puts "   #{e.inspect}"}
end
