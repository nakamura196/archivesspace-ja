"""論文の評価（E2 検索）の追加: 文字バイグラムが苦手とする 2 種を測る。

表1 の評価用データは既定の設定で起きる問題を再現するように作ったので、バイグラムの弱点を含まない。
ここでは、次の 2 種の題名と検索語を別に作り、3 つの設定のコアで測る。
  - 1 字の検索語（写・図・橋 など）。題名の中で他の字と続いている場合と、1 字だけで立っている場合を入れる
  - 3 字以上の検索語で、その 2 字の組がすべて題名の離れた位置に現れる紛らわしい題名（「北海の海道」など）

本体の目録（EVAL-JA）とは混ぜない。評価用のコアに、別のリポジトリの値（/repositories/999）を付けて直接入れる。
設定 (a) 既定の写しのコア eval_default は、ここで作る（同義語を入れる前のスキーマ schema.xml.bak-itaiji から）。
(b) eval_itaiji と (c) eval_bigram は eval_bigram_core.py setup で作ったものを使う。

使い方（このリポジトリの直下で）:
  python3 eval/eval_bigram_weak.py make    # eval/results/weak-docs.tsv と weak-queries.tsv を作る
  python3 eval/eval_bigram_weak.py setup   # eval_default を作り、3 つのコアに資料を入れる
  python3 eval/eval_bigram_weak.py run     # 3 設定で測る → eval/results/weak-results.tsv と集計
  python3 eval/eval_bigram_weak.py drop    # 3 つのコアから追加の資料を消し、eval_default を消す
"""

import csv
import json
import sys
import urllib.parse

import eval_bigram_core as core
import eval_search as ev

OUT = ev.OUT
REPO = "/repositories/999"
CORES = {"default": "eval_default", "itaiji": "eval_itaiji", "bigram": "eval_bigram"}

# 1 字の検索語と、その字を含む題名（続いている字の中にあるもの、1 字で立っているもの、旧字で書いたもの）
SINGLE = {
    "写": ["写真帖", "複写一括", "写本ほか", "写（控）", "寫本目録"],
    "図": ["地図一括", "図面ほか", "絵図関係綴", "図（控）", "圖書目録"],
    "橋": ["日本橋の絵葉書", "橋梁写真", "京橋ほか", "橋（控）"],
    "寺": ["寺院明細帳", "東寺文書", "寺社関係綴", "寺（控）"],
    "駅": ["駅舎写真", "上野駅ほか", "駅前の商店", "駅（控）", "驛前の商店"],
    "港": ["横浜港一括", "港湾関係綴", "築港工事", "港（控）"],
}
# 3 字以上の検索語と、その 2 字の組がすべて題名の離れた位置に現れる紛らわしい題名
SCATTER3 = {
    "北海道": ["北海の海道", "海道と北海"],
    "東京都": ["東京から京都へ", "京都と東京"],
    "日本史": ["日本の本史料", "本史料と日本"],
    "中学校": ["中学・学校行事", "学校と中学"],
    "大学院": ["大学・学院一覧", "学院と大学"],
    "京都大学": ["京都の都大路と大学", "大学と京都の都大路"],
}


def make():
    docs, queries = [], []

    def add(title, kind):
        docs.append((f"W{len(docs) + 1:04d}", title, kind))

    for q, titles in SINGLE.items():
        for t in titles:
            add(t, "single")
        queries.append((q, "single"))
    for q, decoys in SCATTER3.items():
        for t in [f"{q}一括", f"昭和期の{q}"]:
            add(t, "scatter3:true")
        for t in decoys:
            add(t, "scatter3:decoy")
        queries.append((q, "scatter3"))
    fm = ev.fold_map()
    with open(OUT / "weak-docs.tsv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(["id", "title", "kind"])
        w.writerows(docs)
    with open(OUT / "weak-queries.tsv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(["query", "category", "n_relevant"])
        for q, cat in queries:
            w.writerow([q, cat, sum(1 for _, t, _ in docs if ev.fold(q, fm) in ev.fold(t, fm))])
    print(f"docs {len(docs)}, queries {len(queries)} → {OUT}")


def solr_docs():
    out = []
    for d in ev.read_tsv("weak-docs.tsv"):
        uri = f"{REPO}/archival_objects/{d['id']}"
        out.append({"id": uri, "uri": uri, "title": d["title"], "primary_type": "archival_object",
                    "types": ["archival_object"], "suppressed": False, "publish": True, "repository": REPO,
                    "identifier": d["id"], "component_id": d["id"], "level": "item",
                    "fullrecord": f"{d['title']} {d['id']} item"})
    return out


def setup():
    names = [c["name"] for c in core.http(f"{core.SOLR}/admin/cores?action=STATUS&wt=json")["status"].values()]
    if "eval_default" not in names:
        original = core.sh("docker", "exec", core.CONTAINER, "cat", f"{core.CONF}/schema.xml.bak-itaiji")
        core.make_core("eval_default", original, {})
        core.http(f"{core.SOLR}/eval_default/update?commit=true", json.dumps(core.source_docs()).encode())
    docs = solr_docs()
    for c in CORES.values():
        core.http(f"{core.SOLR}/{c}/update?commit=true", json.dumps(docs).encode())
        print(f"{c}: {len(docs)} 件を入れた")


def search(c, q):
    params = dict(core.PARAMS, q=q, rows=1000, wt="json", fl="uri")
    params["fq"] = params["fq"] + [f'repository:"{REPO}"']
    qs = urllib.parse.urlencode(params, doseq=True)
    return {d["uri"].rsplit("/", 1)[1] for d in core.http(f"{core.SOLR}/{c}/select?{qs}")["response"]["docs"]}


def run():
    docs = ev.read_tsv("weak-docs.tsv")
    fm = ev.fold_map()
    rows = []
    for setting, c in CORES.items():
        assert len(search(c, "*:*")) == len(docs), f"{c} に資料が揃っていない"
        for qd in ev.read_tsv("weak-queries.tsv"):
            q = qd["query"]
            rel = {d["id"] for d in docs if ev.fold(q, fm) in ev.fold(d["title"], fm)}
            got = search(c, q)
            tp = len(rel & got)
            rows.append({"setting": setting, "query": q, "category": qd["category"], "relevant": len(rel),
                         "retrieved": len(got), "tp": tp, "recall": round(tp / len(rel), 3),
                         "precision": round(tp / len(got), 3) if got else "",
                         "false_hits": " ".join(sorted(got - rel)), "missed": " ".join(sorted(rel - got))})
    with open(OUT / "weak-results.tsv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print("設定\t区分\t語数\t正解\t検索結果\t正しく見つけた\t再現率\t適合率")
    for setting in CORES:
        for cat in ["single", "scatter3"]:
            rs = [r for r in rows if r["setting"] == setting and r["category"] == cat]
            rel, got, tp = (sum(r[k] for r in rs) for k in ("relevant", "retrieved", "tp"))
            print(f"{setting}\t{cat}\t{len(rs)}\t{rel}\t{got}\t{tp}\t{tp / rel:.3f}\t{tp / got if got else 0:.3f}")
    for r in rows:
        print(r["setting"], r["query"], f"{r['tp']}/{r['relevant']} got {r['retrieved']}",
              "誤:" + r["false_hits"], "漏:" + r["missed"])


def drop():
    for c in CORES.values():
        q = json.dumps({"delete": {"query": f'repository:"{REPO}"'}}).encode()
        core.http(f"{core.SOLR}/{c}/update?commit=true", q)
    q = urllib.parse.urlencode({"action": "UNLOAD", "core": "eval_default", "deleteInstanceDir": "true", "wt": "json"})
    core.http(f"{core.SOLR}/admin/cores?{q}")
    print("dropped")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"make": make, "setup": setup, "run": run, "drop": drop}.get(cmd, lambda: print(__doc__))()
