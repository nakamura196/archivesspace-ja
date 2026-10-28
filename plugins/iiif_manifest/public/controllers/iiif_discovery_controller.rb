# IIIF Change Discovery API 1.0。マニフェストの更新の一覧を、古い順にページに分けて返す。
#
# 対象は、公開されているデジタルオブジェクトと、デジタルオブジェクトがつながった資料・資料群。
# 更新日時はレコードの system_mtime を使う。
# 限界: 削除は記録が残らないので Delete は出せない。つながったデジタルオブジェクトだけを
# 直したとき、資料の側の更新日時は変わらない。
class IiifDiscoveryController < ApplicationController

  DISCOVERY_CONTEXT = 'http://iiif.io/api/discovery/1/context.json'
  CONTENT_TYPE = 'application/ld+json;profile="https://www.w3.org/ns/activitystreams"'
  PAGE_SIZE = 100
  QUERY = 'primary_type:digital_object OR ' \
          '(primary_type:(archival_object OR resource) AND digital_object_uris:[* TO *])'

  def index
    results = search(1, 1)
    total = results['total_hits'].to_i
    last = [(total + PAGE_SIZE - 1) / PAGE_SIZE - 1, 0].max

    respond({
      '@context' => DISCOVERY_CONTEXT,
      'id' => collection_id,
      'type' => 'OrderedCollection',
      'totalItems' => total,
      'first' => { 'id' => page_id(0), 'type' => 'OrderedCollectionPage' },
      'last' => { 'id' => page_id(last), 'type' => 'OrderedCollectionPage' },
    })
  end

  def page
    n = params[:page].to_i
    results = search(n + 1, PAGE_SIZE)
    total = results['total_hits'].to_i
    last = [(total + PAGE_SIZE - 1) / PAGE_SIZE - 1, 0].max
    return head :not_found if n > last

    body = {
      '@context' => DISCOVERY_CONTEXT,
      'id' => page_id(n),
      'type' => 'OrderedCollectionPage',
      'startIndex' => n * PAGE_SIZE,
      'partOf' => { 'id' => collection_id, 'type' => 'OrderedCollection' },
    }
    body['prev'] = { 'id' => page_id(n - 1), 'type' => 'OrderedCollectionPage' } if n > 0
    body['next'] = { 'id' => page_id(n + 1), 'type' => 'OrderedCollectionPage' } if n < last
    body['orderedItems'] = Array(results['results']).map { |r|
      {
        'type' => 'Update',
        'object' => { 'id' => "#{public_base}#{r['uri']}/manifest.json", 'type' => 'Manifest' },
        'endTime' => r['system_mtime'],
      }
    }
    respond(body)
  end

  private

  def public_base
    AppConfig[:public_proxy_url].sub(%r{/+\z}, '')
  end

  def collection_id
    "#{public_base}/iiif/discovery/activity/all-changes"
  end

  def page_id(n)
    "#{public_base}/iiif/discovery/activity/page/#{n}"
  end

  # 同じ時刻の更新が並んでもページの切れ目がずれないよう、uri でも並べる
  def search(page, page_size)
    archivesspace.advanced_search('/search', page,
                                  'q' => QUERY,
                                  'filter_query[]' => ['types:pui'],
                                  'sort' => 'system_mtime asc, uri asc',
                                  'page_size' => page_size,
                                  'hl' => false).raw
  end

  def respond(body)
    response.headers['Access-Control-Allow-Origin'] = '*'
    render :json => JSON.pretty_generate(body), :content_type => CONTENT_TYPE
  end
end
