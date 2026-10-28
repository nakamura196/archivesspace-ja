#!/usr/bin/env zsh
# ArchivesSpace の Solr の text_general を、文字バイグラムの設定（solr/bigram-text_general.xml）に替える。
# 旧字は MappingCharFilter（plugins/japanese/solr/itaiji-mapping.txt）で、索引と検索の両方で今の字に置き換える。
# 索引の解析が変わるので、替えたあとに全件の索引の作り直しが要る（README の「段階 3」）。
# 使い方（docker compose のあるフォルダで）:
#   zsh <このリポジトリ>/scripts/solr-bigram.zsh setup [SOLR]   # schema.xml を書き換えてコアを読み直す（控え schema.xml.bak-bigram）
#   zsh <このリポジトリ>/scripts/solr-bigram.zsh undo  [SOLR]   # 控えに戻す
# SOLR の既定は http://localhost:8983/solr/archivesspace。
# 前提: config.rb に AppConfig[:solr_verify_checksums] = false（schema.xml を書き換えると本体の照合に引っかかるため）。
set -euo pipefail

cmd=${1:-}; SOLR=${2:-http://localhost:8983/solr/archivesspace}
core=${SOLR##*/}; base=${SOLR%/*}
here=${0:A:h}; conf=/var/solr/data/$core/conf
reload() { curl -sf "$base/admin/cores?action=RELOAD&core=$core&wt=json" >/dev/null && echo "reloaded $core"; }

case $cmd in
  setup)
    if docker compose exec -T solr grep -q CJKBigramFilterFactory $conf/schema.xml; then echo "already set up"; exit 0; fi
    tmp=$(mktemp -d)
    docker compose exec -T solr cat $conf/schema.xml > $tmp/schema.xml
    python3 - $tmp/schema.xml $here/../solr/bigram-text_general.xml <<'PY'
import sys
path, part = sys.argv[1], open(sys.argv[2], encoding="utf-8").read()
s = open(path, encoding="utf-8").read()
start = s.index('    <fieldType name="text_general"')
end = s.index("</fieldType>", start) + len("</fieldType>\n")
open(path, "w", encoding="utf-8").write(s[:start] + part + s[end:])
PY
    docker compose exec -T solr cp $conf/schema.xml $conf/schema.xml.bak-bigram
    docker compose cp $tmp/schema.xml solr:$conf/schema.xml
    docker compose cp $here/../plugins/japanese/solr/itaiji-mapping.txt solr:$conf/itaiji-mapping.txt
    rm -r $tmp
    reload
    echo "次に全件の索引を作り直す（README の段階 3）" ;;
  undo)
    docker compose exec -T solr cp $conf/schema.xml.bak-bigram $conf/schema.xml
    reload ;;
  *) sed -n 2,9p $0; exit 1 ;;
esac
