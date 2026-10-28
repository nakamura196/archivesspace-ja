"""論文の評価（E2 検索）の 3 つ目の設定: 文字バイグラム。

本番の索引を作り直さずに測るため、同じ Solr に評価用のコアを別に作り、評価用の資料（EVAL-JA）だけを入れる。
資料は本体のコアに保存されている記録（json 欄）から作り直し、fullrecord はその中の文字列をすべてつなげて作る
（ArchivesSpace の索引作成とほぼ同じ。完全には一致しないので、まず今の設定のコアで本体経由の結果と一致するかを確かめる）。
検索の条件は ArchivesSpace が Solr に送るもの（2026-10-28 に Solr の記録から写した）と同じにする。

使い方（このリポジトリの直下で。Solr のコンテナ名は solr とする）:
  python3 eval/eval_bigram_core.py setup         # コア eval_itaiji（今の設定の写し）と eval_bigram を作り、資料を入れる
  python3 eval/eval_bigram_core.py run itaiji-core eval_itaiji   # 本体経由の results-itaiji.tsv と一致するか確かめる用
  python3 eval/eval_bigram_core.py run bigram eval_bigram
  python3 eval/eval_bigram_core.py drop          # 評価用のコアを消す
"""

import json
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path

import eval_search as ev

SOLR = "http://localhost:8983/solr"
CONTAINER = "solr"
CONF = "/var/solr/data/archivesspace/conf"
HERE = Path(__file__).resolve().parent
MAPPING = HERE.parent / "plugins" / "japanese" / "solr" / "itaiji-mapping.txt"

# ArchivesSpace が送る条件（q と fq の repository 以外）
PARAMS = {"q.op": "AND", "defType": "edismax", "qf": "identifier_ws^3 title_ws^2 finding_aid_filing_title^2 fullrecord",
          "pf": "four_part_id^4", "fq": ['types:("archival_object")', "-exclude_by_default:true", "-types:pui_only"]}

BIGRAM_TYPE = """    <fieldType name="text_general" class="solr.TextField" positionIncrementGap="100">
      <!-- 評価用: 旧字を今の字に置き換え（索引・検索の両方），全角半角をそろえ，漢字・かなを 2 字ずつに切る -->
      <analyzer type="index">
        <charFilter class="solr.HTMLStripCharFilterFactory" />
        <charFilter class="solr.MappingCharFilterFactory" mapping="itaiji-mapping.txt" />
        <tokenizer class="solr.StandardTokenizerFactory" />
        <filter class="solr.CJKWidthFilterFactory" />
        <filter class="solr.StopFilterFactory" ignoreCase="true" words="stopwords.txt" />
        <filter class="solr.LowerCaseFilterFactory" />
        <filter class="solr.ASCIIFoldingFilterFactory" />
        <filter class="solr.CJKBigramFilterFactory" />
      </analyzer>
      <analyzer type="query">
        <charFilter class="solr.MappingCharFilterFactory" mapping="itaiji-mapping.txt" />
        <tokenizer class="solr.StandardTokenizerFactory" />
        <filter class="solr.CJKWidthFilterFactory" />
        <filter class="solr.StopFilterFactory" ignoreCase="true" words="stopwords.txt" />
        <filter class="solr.LowerCaseFilterFactory" />
        <filter class="solr.ASCIIFoldingFilterFactory" />
        <filter class="solr.CJKBigramFilterFactory" />
      </analyzer>
    </fieldType>
"""


def sh(*args, **kw):
    return subprocess.run(args, check=True, capture_output=True, text=True, **kw).stdout


def http(url, body=None):
    req = urllib.request.Request(url, data=body, method="POST" if body is not None else "GET")
    if body is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def write_mapping():
    lines = ["# 旧字・異体字 → 今の字（itaiji-ja.tsv から eval_bigram_core.py が作る。MappingCharFilter 用）"]
    for line in ev.ITAIJI.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        old, new = line.split("\t")
        lines.append(f'"{old}" => "{new}"')
    MAPPING.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(lines) - 1


def make_core(name, schema_text, extra_files):
    d = f"/var/solr/data/{name}"
    sh("docker", "exec", "-u", "solr", CONTAINER, "sh", "-c",
       f"mkdir -p {d}/conf && cp {CONF}/solrconfig.xml {CONF}/stopwords.txt {CONF}/synonyms.txt {d}/conf/")
    with tempfile.TemporaryDirectory() as tmp:
        files = dict(extra_files, **{"schema.xml": schema_text})
        for fn, text in files.items():
            Path(tmp, fn).write_text(text, encoding="utf-8")
            sh("docker", "cp", str(Path(tmp, fn)), f"{CONTAINER}:/tmp/{name}-{fn}")
            sh("docker", "exec", "-u", "0", CONTAINER, "sh", "-c",
               f"cp /tmp/{name}-{fn} {d}/conf/{fn} && chown solr {d}/conf/{fn} && rm /tmp/{name}-{fn}")
    q = urllib.parse.urlencode({"action": "CREATE", "name": name, "instanceDir": name, "wt": "json"})
    http(f"{SOLR}/admin/cores?{q}")


def strings(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for v in x.values():
            yield from strings(v)
    elif isinstance(x, list):
        for v in x:
            yield from strings(v)


def source_docs():
    q = urllib.parse.urlencode({"q": 'repository:"/repositories/4" AND types:archival_object', "rows": 1000,
                                "wt": "json", "fl": "id,uri,title,primary_type,types,repository,identifier,"
                                "component_id,level,resource,ancestors,publish,suppressed,json"})
    docs = http(f"{SOLR}/archivesspace/select?{q}")["response"]["docs"]
    for d in docs:
        rec = json.loads(d.pop("json"))
        d["fullrecord"] = " ".join(strings(rec))
    return docs


def setup():
    n = write_mapping()
    print(f"mapping {n} 組 → {MAPPING}")
    current = sh("docker", "exec", CONTAINER, "cat", f"{CONF}/schema.xml")
    original = sh("docker", "exec", CONTAINER, "cat", f"{CONF}/schema.xml.bak-itaiji")
    managed = sh("docker", "exec", CONTAINER, "cat", f"{CONF}/_schema_analysis_synonyms_ja_itaiji.json")
    start = original.index('    <fieldType name="text_general"')
    end = original.index("</fieldType>", start) + len("</fieldType>\n")
    bigram = original[:start] + BIGRAM_TYPE + original[end:]
    make_core("eval_itaiji", current, {"_schema_analysis_synonyms_ja_itaiji.json": managed})
    make_core("eval_bigram", bigram, {"itaiji-mapping.txt": MAPPING.read_text(encoding="utf-8")})
    docs = source_docs()
    for core in ("eval_itaiji", "eval_bigram"):
        t0 = time.perf_counter()
        http(f"{SOLR}/{core}/update?commit=true", json.dumps(docs).encode())
        print(f"{core}: {len(docs)} 件を入れた（{time.perf_counter() - t0:.1f} 秒）")


def search(core, q):
    params = dict(PARAMS, q=q, rows=1000, wt="json", fl="uri")
    params["fq"] = params["fq"] + ['repository:"/repositories/4" OR repository:global']
    qs = urllib.parse.urlencode(params, doseq=True)
    return {d["uri"] for d in http(f"{SOLR}/{core}/select?{qs}")["response"]["docs"]}


def run(setting, core):
    # 本体経由と同じ集計にするため、eval_search の run の検索だけを差し替える
    ev.login = lambda: None
    ev.find_repo = lambda token: "/repositories/4"
    ev.search = lambda token, repo, q: search(core, "*:*" if q == "*" else q)
    ev.run(setting)


def drop():
    for core in ("eval_itaiji", "eval_bigram"):
        q = urllib.parse.urlencode({"action": "UNLOAD", "core": core, "deleteInstanceDir": "true", "wt": "json"})
        http(f"{SOLR}/admin/cores?{q}")
        print("dropped", core)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "setup":
        setup()
    elif cmd == "run" and len(sys.argv) > 3:
        run(sys.argv[2], sys.argv[3])
    elif cmd == "drop":
        drop()
    else:
        print(__doc__)
