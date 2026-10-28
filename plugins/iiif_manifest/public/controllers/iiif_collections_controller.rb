# 資料群・シリーズなど、下に資料を持つものを IIIF Collection（Presentation API 3.0）で返す。
#
# 中身は公開の階層（ツリー）をそのまま使う。
#   - 下に資料を持つ子 → その子の collection.json
#   - 画像を持つ子（下に資料を持たない） → その子の manifest.json
#   - 自分自身に画像があれば、先頭に自分の manifest.json を置く
# 画像を持つ資料が配下に 1 件も無い子は載せない。
class IiifCollectionsController < ApplicationController

  PRESENTATION_CONTEXT = 'http://iiif.io/api/presentation/3/context.json'
  SEARCH_PAGE_SIZE = 250

  def show
    uri = "/repositories/#{params[:rid]}/#{params[:obj_type]}/#{params[:id]}"
    record = archivesspace.get_record(params[:obj_type] == 'archival_objects' ? "#{uri}#pui" : uri)

    if params[:obj_type] == 'resources'
      root_uri = uri
      node = archivesspace.get_raw_record("#{root_uri}/tree/root")
      parent_key = ''
    else
      root_uri = record['json'].dig('resource', 'ref')
      node = archivesspace.get_raw_record("#{root_uri}/tree/node_#{uri}")
      parent_key = uri
    end

    with_images = uris_with_images_below(uri)
    label = strip_tags(record.display_string)

    items = []
    items << reference(uri, 'Manifest', label) if node['has_digital_instance']
    children_of(root_uri, node, parent_key).each do |child|
      next if child['suppressed'] == true || child['suppressed'].to_i == 1
      child_label = strip_tags(child['title'])
      if child['child_count'].to_i > 0 && with_images.include?(child['uri'])
        items << reference(child['uri'], 'Collection', child_label)
      elsif child['has_digital_instance']
        items << reference(child['uri'], 'Manifest', child_label)
      end
    end

    collection = {
      '@context' => PRESENTATION_CONTEXT,
      'id' => "#{public_base}#{uri}/collection.json",
      'type' => 'Collection',
      'label' => { 'none' => [label] },
      'homepage' => [{
        'id' => "#{public_base}#{uri}",
        'type' => 'Text',
        'label' => { 'none' => [label] },
        'format' => 'text/html',
      }],
      'items' => items,
    }

    response.headers['Access-Control-Allow-Origin'] = '*'
    render :json => JSON.pretty_generate(collection),
           :content_type => %Q{application/ld+json;profile="#{PRESENTATION_CONTEXT}"}
  rescue RecordNotFound
    head :not_found
  end

  private

  def public_base
    AppConfig[:public_proxy_url].sub(%r{/+\z}, '')
  end

  def reference(uri, type, label)
    file = type == 'Collection' ? 'collection.json' : 'manifest.json'
    { 'id' => "#{public_base}#{uri}/#{file}", 'type' => type, 'label' => { 'none' => [label] } }
  end

  # 子は 200 件ずつの塊（waypoint）に分かれている。1 つ目は node に入っていて、残りは別に取る
  def children_of(root_uri, node, parent_key)
    children = Array(node.dig('precomputed_waypoints', parent_key, '0'))
    (1...node['waypoints'].to_i).each do |n|
      children.concat(Array(archivesspace.get_raw_record("#{root_uri}/tree/waypoint_#{parent_key}_#{n}")))
    end
    children
  end

  # uri の配下で、画像（デジタルオブジェクト）を持つ資料の祖先をすべて集める。
  # 子を載せるかどうかを、1 回の検索で決めるため
  def uris_with_images_below(uri)
    found = Set.new
    page = 1
    loop do
      results = archivesspace.advanced_search('/search', page,
                                              'q' => %Q{ancestors:"#{uri}" AND digital_object_uris:[* TO *]},
                                              'filter_query[]' => ['types:pui'],
                                              'page_size' => SEARCH_PAGE_SIZE,
                                              'hl' => false).raw
      Array(results['results']).each { |r| found.merge(Array(r['ancestors'])) }
      break if page >= results['last_page'].to_i
      page += 1
    end
    found
  end

  def strip_tags(s)
    ActionController::Base.helpers.strip_tags(s.to_s).strip
  end
end
