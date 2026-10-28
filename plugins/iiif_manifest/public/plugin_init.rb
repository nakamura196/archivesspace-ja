# 画像の URL の先頭（file_uri がこれで始まるものだけをマニフェストに入れる）と、
# それに対応するアプリ側から見た置き場。config.rb で上書きできる。
unless AppConfig.has_key?(:iiif_image_base_url)
  AppConfig[:iiif_image_base_url] = "#{AppConfig[:public_proxy_url].sub(%r{/+\z}, '')}/dip/"
end
AppConfig[:iiif_image_dir] = '/srv/dip' unless AppConfig.has_key?(:iiif_image_dir)

Plugins::extend_aspace_routes(File.join(File.dirname(__FILE__), 'routes.rb'))
