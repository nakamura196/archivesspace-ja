"""論文 5.3 節: 全件の索引を文字バイグラムの設定で作り直すと、Solr の側でどれだけ時間がかかるかを測る。

本番のコア（archivesspace）は他の作業でも使っているので作り直さない。読み出すだけにする。
本番のコアに保存されている全件を書き出し、評価用のコアを 2 つ作って入れ直し、時間を比べる。
  - eval_full_default: 既定の設定（同義語を入れる前の schema.xml.bak-itaiji）
  - eval_full_bigram : 5.3 節の設定（eval_bigram_core.py と同じ text_general）
保存されていない欄（fullrecord など）は、保存されている記録（json 欄）の中の文字列をつないで作る（eval_bigram_core.py と同じ）。
ArchivesSpace の索引作成処理（データベースから記録を組み立てる部分）の時間は含まない。測るのは Solr の解析と書き込みだけ。

使い方（このリポジトリの直下で）:
  python3 eval/eval_reindex_time.py export <出力.jsonl>   # 本番のコアから全件を書き出す（読み出しのみ）
  python3 eval/eval_reindex_time.py run <出力.jsonl>      # 2 つのコアを作って入れ直し、時間を測る → eval/results/reindex-time.tsv
  python3 eval/eval_reindex_time.py drop                  # 2 つのコアを消す
"""

import csv
import json
import sys
import time
import urllib.parse

import eval_bigram_core as core
import eval_search as ev

CORES = {"default": "eval_full_default", "bigram": "eval_full_bigram"}
BATCH = 2000


def export(path):
    n, cursor = 0, "*"
    with open(path, "w", encoding="utf-8") as f:
        while True:
            q = urllib.parse.urlencode({"q": "*:*", "rows": BATCH, "sort": "id asc", "cursorMark": cursor,
                                        "wt": "json", "fl": "*"})
            r = core.http(f"{core.SOLR}/archivesspace/select?{q}")
            for d in r["response"]["docs"]:
                d.pop("_version_", None)
                if "json" in d:
                    d["fullrecord"] = " ".join(core.strings(json.loads(d["json"])))
                f.write(json.dumps(d, ensure_ascii=False) + "\n")
                n += 1
            if r["nextCursorMark"] == cursor:
                break
            cursor = r["nextCursorMark"]
    print(f"{n} 件 → {path}")


def schemas():
    original = core.sh("docker", "exec", core.CONTAINER, "cat", f"{core.CONF}/schema.xml.bak-itaiji")
    start = original.index('    <fieldType name="text_general"')
    end = original.index("</fieldType>", start) + len("</fieldType>\n")
    mapping = core.MAPPING.read_text(encoding="utf-8")
    return {"default": (original, {}),
            "bigram": (original[:start] + core.BIGRAM_TYPE + original[end:], {"itaiji-mapping.txt": mapping})}


def run(path):
    names = [c["name"] for c in core.http(f"{core.SOLR}/admin/cores?action=STATUS&wt=json")["status"].values()]
    rows = []
    for setting, (schema, extra) in schemas().items():
        c = CORES[setting]
        if c not in names:
            core.make_core(c, schema, extra)
        core.http(f"{core.SOLR}/{c}/update?commit=true", json.dumps({"delete": {"query": "*:*"}}).encode())
        n, batch = 0, []
        t0 = time.perf_counter()
        with open(path, encoding="utf-8") as f:
            for line in f:
                batch.append(json.loads(line))
                if len(batch) == BATCH:
                    core.http(f"{core.SOLR}/{c}/update", json.dumps(batch).encode())
                    n += len(batch)
                    batch = []
        if batch:
            core.http(f"{core.SOLR}/{c}/update", json.dumps(batch).encode())
            n += len(batch)
        core.http(f"{core.SOLR}/{c}/update?commit=true", b"[]")
        sec = time.perf_counter() - t0
        st = core.http(f"{core.SOLR}/admin/cores?action=STATUS&core={c}&wt=json")["status"][c]["index"]
        rows.append({"setting": setting, "core": c, "docs": st["numDocs"], "sent": n, "seconds": round(sec, 1),
                     "index_bytes": st["sizeInBytes"]})
        print(rows[-1])
    with open(ev.OUT / "reindex-time.tsv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def drop():
    for c in CORES.values():
        q = urllib.parse.urlencode({"action": "UNLOAD", "core": c, "deleteInstanceDir": "true", "wt": "json"})
        core.http(f"{core.SOLR}/admin/cores?{q}")
    print("dropped")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd in ("export", "run") and len(sys.argv) > 2:
        {"export": export, "run": run}[cmd](sys.argv[2])
    elif cmd == "drop":
        drop()
    else:
        print(__doc__)
