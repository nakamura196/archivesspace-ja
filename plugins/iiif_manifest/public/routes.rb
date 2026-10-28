Rails.application.routes.draw do
  scope AppConfig[:public_proxy_prefix] do
    get 'repositories/:rid/:obj_type/:id/manifest.json' => 'iiif_manifests#show',
        :constraints => { :rid => /\d+/, :id => /\d+/, :obj_type => /digital_objects|archival_objects|resources/ },
        :format => false
    get 'repositories/:rid/:obj_type/:id/collection.json' => 'iiif_collections#show',
        :constraints => { :rid => /\d+/, :id => /\d+/, :obj_type => /archival_objects|resources/ },
        :format => false
    get 'iiif/discovery/activity/all-changes' => 'iiif_discovery#index', :format => false
    get 'iiif/discovery/activity/page/:page' => 'iiif_discovery#page',
        :constraints => { :page => /\d+/ }, :format => false
  end
end
