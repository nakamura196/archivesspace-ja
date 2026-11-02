"""論文 5.3 節: 索引の大きさが回ごとにばらつく理由を調べる（2026-10-30）。

eval_reindex_time.py の run と同じ手順で、書き出した全件を評価用のコアに入れ直し、
commit 直後（(d) は 60 秒後も）と、1 つのセグメントに統合（optimize）した後の大きさ・セグメント数・削除済みの件数を記録する。

使い方（このリポジトリの直下で）:
  python3 eval/eval_index_size_merge.py <書き出した.jsonl> <出力.tsv> <default|bigram|bigram-uni> <回数>
"""
import json, sys, time
sys.path.insert(0, "eval")
import eval_bigram_core as core
import eval_reindex_time as rt

path, out, setting, runs = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
schema, extra = rt.schemas()[setting]
c = rt.CORES[setting]
names = [x["name"] for x in core.http(f"{core.SOLR}/admin/cores?action=STATUS&wt=json")["status"].values()]
if c not in names:
    core.make_core(c, schema, extra)


def st():
    i = core.http(f"{core.SOLR}/admin/cores?action=STATUS&core={c}&wt=json")["status"][c]["index"]
    return i["numDocs"], i["deletedDocs"], i["segmentCount"], i["sizeInBytes"]


steps = ("commit", "after60s", "optimize") if setting == "bigram-uni" else ("commit", "optimize")
rows = []
for run in range(1, runs + 1):
    core.http(f"{core.SOLR}/{c}/update?commit=true", json.dumps({"delete": {"query": "*:*"}}).encode())
    batch = []
    t0 = time.perf_counter()
    with open(path, encoding="utf-8") as f:
        for line in f:
            batch.append(json.loads(line))
            if len(batch) == rt.BATCH:
                core.http(f"{core.SOLR}/{c}/update", json.dumps(batch).encode())
                batch = []
    if batch:
        core.http(f"{core.SOLR}/{c}/update", json.dumps(batch).encode())
    core.http(f"{core.SOLR}/{c}/update?commit=true", b"[]")
    sec = round(time.perf_counter() - t0, 1)
    for label in steps:
        if label == "after60s":
            time.sleep(60)
        if label == "optimize":
            core.http(f"{core.SOLR}/{c}/update?optimize=true&maxSegments=1&waitSearcher=true", b"[]")
        rows.append((setting, run, label, sec, *st()))
        print(*rows[-1], flush=True)
with open(out, "a", encoding="utf-8") as f:
    if f.tell() == 0:
        f.write("setting\trun\twhen\tseconds\tdocs\tdeleted\tsegments\tindex_bytes\n")
    for r in rows:
        f.write("\t".join(map(str, r)) + "\n")
