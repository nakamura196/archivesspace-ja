# IIIF Presentation API 3.0 のマニフェストを返す。
#
# デジタルオブジェクトの file_versions のうち、画像ファイルが
# AppConfig[:iiif_image_dir] にあるものを 1 枚 1 ページ（Canvas）にする。
# Image API は使わず、画像の URL（file_uri）をそのまま指す。
# 資料・資料群のページでは、つながっているデジタルオブジェクトをまとめる。
class IiifManifestsController < ApplicationController

  PRESENTATION_CONTEXT = 'http://iiif.io/api/presentation/3/context.json'
  MEDIA_TYPES = { 'jpeg' => 'image/jpeg', 'png' => 'image/png' }

  def show
    uri = "/repositories/#{params[:rid]}/#{params[:obj_type]}/#{params[:id]}"
    record = archivesspace.get_record(params[:obj_type] == 'archival_objects' ? "#{uri}#pui" : uri,
                                      { 'resolve[]' => ['repository:id', 'resource:id@compact_resource'] })
    json = record['json']

    digital_objects = params[:obj_type] == 'digital_objects' ? [json] : linked_digital_objects(json)
    id = "#{public_base}#{uri}/manifest.json"

    canvases = []
    digital_objects.each do |dobj|
      canvases.concat(canvases_for(dobj, id, canvases.length))
    end

    manifest = {
      '@context' => PRESENTATION_CONTEXT,
      'id' => id,
      'type' => 'Manifest',
      'label' => { 'none' => [strip_tags(record.display_string)] },
      'metadata' => metadata_for(json, record),
      'homepage' => [{
        'id' => "#{public_base}#{uri}",
        'type' => 'Text',
        'label' => { 'none' => [strip_tags(record.display_string)] },
        'format' => 'text/html',
      }],
      'items' => canvases,
    }

    response.headers['Access-Control-Allow-Origin'] = '*'
    render :json => JSON.pretty_generate(manifest),
           :content_type => %Q{application/ld+json;profile="#{PRESENTATION_CONTEXT}"}
  rescue RecordNotFound
    head :not_found
  end

  private

  def public_base
    AppConfig[:public_proxy_url].sub(%r{/+\z}, '')
  end

  # 索引のデータでは、つながったデジタルオブジェクトが instance の中に _resolved として入っている
  def linked_digital_objects(json)
    Array(json['instances']).map { |instance|
      dobj = instance.dig('digital_object', '_resolved')
      dobj if dobj && dobj['publish']
    }.compact
  end

  def canvases_for(dobj, manifest_id, offset)
    file_versions = Array(dobj['file_versions']).select { |fv| fv['publish'] != false }

    file_versions.map { |fv|
      path = local_path(fv['file_uri'])
      next unless path
      size = image_size(path)
      next unless size
      width, height, kind = size

      offset += 1
      canvas_id = "#{manifest_id.sub(/\.json\z/, '')}/canvas/#{offset}"
      label = fv['caption'].to_s.strip
      label = "#{strip_tags(dobj['title'].to_s)} #{offset}" if label.empty?

      {
        'id' => canvas_id,
        'type' => 'Canvas',
        'label' => { 'none' => [label] },
        'width' => width,
        'height' => height,
        'items' => [{
          'id' => "#{canvas_id}/page",
          'type' => 'AnnotationPage',
          'items' => [{
            'id' => "#{canvas_id}/page/image",
            'type' => 'Annotation',
            'motivation' => 'painting',
            'body' => {
              'id' => fv['file_uri'],
              'type' => 'Image',
              'format' => MEDIA_TYPES[kind],
              'width' => width,
              'height' => height,
            },
            'target' => canvas_id,
          }],
        }],
      }
    }.compact
  end

  # file_uri が AppConfig[:iiif_image_base_url] の下を指していれば、
  # 対応する手元のファイルの場所を返す。外を指すもの・置き場の外に出るものは nil。
  def local_path(file_uri)
    base = AppConfig[:iiif_image_base_url]
    return nil if file_uri.nil? || !file_uri.start_with?(base)

    rest = URI::DEFAULT_PARSER.unescape(file_uri[base.length..-1].split(/[?#]/, 2).first.to_s)
    root = File.expand_path(AppConfig[:iiif_image_dir])
    path = File.expand_path(rest, root)
    return nil unless path.start_with?(root + File::SEPARATOR) && File.file?(path)

    path
  end

  # 画像の先頭だけを読んで [幅, 高さ, 種類] を返す。JPEG と PNG のみ。
  def image_size(path)
    File.open(path, 'rb') do |f|
      head = f.read(24)
      return nil if head.nil? || head.bytesize < 24

      if head.start_with?("\x89PNG\r\n\x1A\n".b)
        width, height = head[16, 8].unpack('NN')
        return [width, height, 'png']
      end

      return nil unless head.start_with?("\xFF\xD8".b)

      f.seek(2)
      loop do
        marker = f.read(2)
        return nil if marker.nil? || marker.bytesize < 2 || marker.getbyte(0) != 0xFF
        code = marker.getbyte(1)
        length = f.read(2)&.unpack1('n')
        return nil unless length
        # SOF0〜SOF15（DHT・JPG・DAC を除く）に寸法が入っている
        if (0xC0..0xCF).cover?(code) && ![0xC4, 0xC8, 0xCC].include?(code)
          height, width = f.read(5)[1, 4].unpack('nn')
          return [width, height, 'jpeg']
        end
        f.seek(length - 2, IO::SEEK_CUR)
      end
    end
  rescue SystemCallError
    nil
  end

  def metadata_for(json, record)
    rows = []
    add = lambda do |key, value|
      value = Array(value).map { |v| strip_tags(v.to_s) }.reject(&:empty?)
      rows << { 'label' => { 'none' => [I18n.t(key)] }, 'value' => { 'none' => value } } unless value.empty?
    end

    add.call('iiif_manifest.identifier', json['digital_object_id'] || json['component_id'] || record.identifier)
    add.call('iiif_manifest.dates', Array(json['dates']).map { |d| d['expression'].presence || [d['begin'], d['end']].compact.uniq.join(' - ') })
    add.call('iiif_manifest.collection', record.resolved_resource['title']) if params[:obj_type] != 'resources' && record.resolved_resource
    add.call('iiif_manifest.repository', record.resolved_repository && record.resolved_repository['name'])
    rows
  rescue NoMethodError
    rows
  end

  def strip_tags(s)
    ActionController::Base.helpers.strip_tags(s.to_s).strip
  end
end
