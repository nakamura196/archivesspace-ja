#!/usr/bin/env zsh
# 論文の評価（E4 本体を改変しないこと）。
#
# 次を調べて eval/results/core-diff.txt に書く:
#   (1) 配布物 archivesspace-docker-v4.2.1.zip を展開したものと、動かしている docker compose のフォルダのファイルごとの違い
#       （本稿で加えたプラグインの中身と、作業用の控え *.bak-* は数えない）
#   (2) 動いているアプリのコンテナが、イメージ archivesspace/archivesspace:4.2.1 から変えたファイル（docker diff）
#       本体のプログラム（Ruby・JavaScript・ひな形）はイメージの中にあるので、ここに出なければ変更 0 件
#   (3) Solr のスキーマの、イメージの元のものと動いているコアのものの違い
#
# 使い方（このリポジトリの直下で）:
#   zsh eval/eval_core_unchanged.zsh <配布物の zip> <compose のフォルダ> [コンテナ名（既定 archivesspace）]
# compose のフォルダは、zip を展開してできる archivesspace/（docker-compose.yml のあるところ）
set -euo pipefail

zip=${1:A}
work=${2:A}
container=${3:-archivesspace}
out=${0:A:h}/results/core-diff.txt
tmp=$(mktemp -d)
trap 'rm -rf $tmp' EXIT

unzip -q $zip -d $tmp

{
  print "# (1) 配布物と作業ツリーの違い（diff -rq。プラグインの中身・控え・backups を除く）"
  diff -rq $tmp/archivesspace $work -x backups -x .DS_Store -x '*.bak-*' -x dip \
    | sed "s|$tmp/||; s|$work|archivesspace|" \
    | grep -v '^Only in archivesspace/plugins' \
    | grep -v '^Only in archivesspace/plugins/local' || true
  print
  print "# (1') 加えたプラグイン（plugins/ の直下で配布物に無いもの）"
  diff -rq $tmp/archivesspace/plugins $work/plugins -x .DS_Store | grep "^Only in $work/plugins:" | sed "s|$work|archivesspace|" || true
  print
  print "# (2) コンテナ $container がイメージから変えたファイル（docker diff。/tmp と実行時のキャッシュを除く）"
  docker inspect $container --format 'image: {{.Config.Image}} {{.Image}}'
  docker diff $container | grep -v ' /tmp' | grep -v '/\.cache' | grep -v '/\.java' | grep -v '/\.fop' || true
  print
  print "# (3) Solr のスキーマ（イメージ archivesspace/solr:4.2.1 の元のものと、動いているコアのもの）"
  docker run --rm --entrypoint sh archivesspace/solr:4.2.1 -c 'cat /opt/solr-*/server/solr/configsets/archivesspace/conf/schema.xml' > $tmp/schema.orig.xml
  docker exec solr cat /var/solr/data/archivesspace/conf/schema.xml > $tmp/schema.now.xml
  diff -u $tmp/schema.orig.xml $tmp/schema.now.xml | sed "s|$tmp/||" || true
  print
  print "# 判定: 本体のプログラム（/archivesspace/ の下で、マウントしていない場所）の変更"
  n=$( { docker diff $container | grep -E ' /archivesspace/' | grep -vE ' /archivesspace/(data|config|plugins|locales|stylesheets)(/|$)' || true; } | wc -l | tr -d ' ')
  print "changed_program_files: $n"
} > $out

cat $out
