#!/usr/bin/env zsh
# ArchivesSpace の Solr に、旧字・異体字の言い換え辞書（ja_itaiji）を入れる。
# 検索するときだけ言い換えるので、索引の作り直しは要らない。
# 使い方:
#   zsh scripts/solr-itaiji.zsh setup [SOLR]   # schema.xml を書き換えてコアを読み直す（1 回だけ。控え schema.xml.bak-itaiji）
#   zsh scripts/solr-itaiji.zsh load  [SOLR]   # plugins/japanese/solr/itaiji-ja.tsv を API で登録して読み直す
#   zsh scripts/solr-itaiji.zsh list  [SOLR]   # 登録済みの辞書を表示
#   zsh scripts/solr-itaiji.zsh off   [SOLR]   # 評価用: 一時的に元の schema.xml に戻す（言い換えなし。控え schema.xml.itaiji）
#   zsh scripts/solr-itaiji.zsh on    [SOLR]   # 評価用: off の前の schema.xml に戻す
# SOLR の既定は http://localhost:8983/solr/archivesspace。
# 前提: config.rb に AppConfig[:solr_verify_checksums] = false（schema.xml を書き換えると本体の照合に引っかかるため）。
# setup は docker compose の solr コンテナの中のファイルを書き換えるので、compose のあるフォルダで実行する。
set -euo pipefail

cmd=${1:-}; SOLR=${2:-http://localhost:8983/solr/archivesspace}
core=${SOLR##*/}; base=${SOLR%/*}
here=${0:A:h}; tsv=$here/../plugins/japanese/solr/itaiji-ja.tsv
api=$SOLR/schema/analysis/synonyms/ja_itaiji

reload() { curl -sf "$base/admin/cores?action=RELOAD&core=$core&wt=json" >/dev/null && echo "reloaded $core"; }

case $cmd in
  setup)
    conf=/var/solr/data/$core/conf/schema.xml
    if docker compose exec -T solr grep -q ManagedSynonymGraphFilterFactory $conf; then echo "already set up"; exit 0; fi
    docker compose exec -T solr sh -c "cp $conf $conf.bak-itaiji && sed -i 's#<filter class=\"solr.SynonymGraphFilterFactory\" synonyms=\"synonyms.txt\" ignoreCase=\"true\" expand=\"true\" />#<filter class=\"solr.ManagedSynonymGraphFilterFactory\" managed=\"ja_itaiji\" />#' $conf && grep -c ManagedSynonymGraphFilterFactory $conf"
    reload ;;
  load)
    # 今の字ごとにまとめて 1 組で送る（弁＝辨・瓣・辯 のように旧字が複数あると、1 行ずつ送ると後の組が前の組を上書きする）
    python3 -c 'import sys,json,collections
g=collections.OrderedDict()
for l in open(sys.argv[1],encoding="utf-8"):
    if l.startswith("#") or not l.strip(): continue
    a,b=l.rstrip("\n").split("\t"); g.setdefault(b,[b]).append(a)
for v in g.values(): print(json.dumps(v,ensure_ascii=False))' $tsv | while read -r json; do
      curl -sf -X PUT -H 'Content-type: application/json' --data-binary "$json" $api >/dev/null && echo "added $json"
    done
    reload ;;
  off)
    conf=/var/solr/data/$core/conf/schema.xml
    docker compose exec -T solr sh -c "cp $conf $conf.itaiji && cp $conf.bak-itaiji $conf && grep -c ManagedSynonymGraphFilterFactory $conf || true"
    reload ;;
  on)
    conf=/var/solr/data/$core/conf/schema.xml
    docker compose exec -T solr sh -c "cp $conf.itaiji $conf && grep -c ManagedSynonymGraphFilterFactory $conf"
    reload ;;
  list)
    curl -sf "$api?wt=json" | python3 -c 'import sys,json;m=json.load(sys.stdin)["synonymMappings"]["managedMap"];print(len(m),"entries");print(m)' ;;
  *) sed -n 2,10p $0; exit 1 ;;
esac
