# iiif_manifest — IIIF for the ArchivesSpace public interface

An ArchivesSpace plugin that publishes IIIF Presentation API 3.0 resources
from digital objects and shows them in Mirador on the public interface.
Tested with ArchivesSpace 4.2.1.

日本語の説明は下にあります。

## What it does

- **Manifest** — `/repositories/:rid/{digital_objects|archival_objects|resources}/:id/manifest.json`
  One canvas per image file in the digital object's file versions.
  For archival objects and resources, the linked digital objects are combined.
- **Collection** — `/repositories/:rid/{resources|archival_objects}/:id/collection.json`
  Follows the public tree. Children with images below them become Collections,
  children with their own images become Manifests. Branches with no images are left out.
- **Change Discovery** — `/iiif/discovery/activity/all-changes` and `/iiif/discovery/activity/page/:n`
  (100 items per page, oldest first, all as `Update`).
- **Viewer** — Mirador 3.3.0 (from jsDelivr, with SRI) on record pages that have images.

The Image API is not used. Canvases point at the image URL (`file_uri`) directly.
Image width and height are read from the file header (JPEG / PNG), so the image files
must be readable from the public app.

## Install

```
git clone https://github.com/nakamura196/archivesspace-ja.git
cp -r archivesspace-ja/plugins/iiif_manifest <ArchivesSpace>/plugins/
```

The folder name must be `iiif_manifest`. Then in `config.rb`:

```ruby
AppConfig[:plugins] << 'iiif_manifest'
# Only file_uri values starting with this URL are included (default: <public_proxy_url>/dip/)
AppConfig[:iiif_image_base_url] = 'https://example.org/dip/'
# Where the same files are visible from the public app (default: /srv/dip)
AppConfig[:iiif_image_dir] = '/srv/dip'
```

With the official Docker setup, mount the image folder into the app container
(e.g. `./dip:/srv/dip:ro`) and restart.

## Limitations

- Change Discovery cannot report deletions (`Delete`).
- Editing only a digital object does not change the modification time of the linked archival object.
- Digital objects whose images are missing from the image folder still appear in Change Discovery.

---

## 日本語

ArchivesSpace の公開画面で、デジタルオブジェクトの画像を IIIF（Presentation API 3.0）で出し、
Mirador で見られるようにするプラグインです。ArchivesSpace 4.2.1 で動作を確かめています。

- マニフェスト・コレクション・Change Discovery の 3 つを出します（URL は上記）
- Image API は使わず、画像の URL をそのまま指します
- 画像の縦横はファイルの先頭を読んで取るので、公開画面のアプリから画像の置き場が見えている必要があります

## License

Educational Community License 2.0 (the same license as ArchivesSpace). See `LICENSE` at the root of this repository.

Satoru Nakamura (The University of Tokyo)
