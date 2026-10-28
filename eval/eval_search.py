"""論文の評価（E2 検索）用。ダミーの目録を作り、手元の ArchivesSpace に入れ、検索の再現率と適合率を測る。

正解は設計から決まる: 旧字を今の字に直したうえで、題名が検索語を部分文字列として含む資料を正解とする。
目録は資料群 1 つの直下に資料を平らに並べ、題名以外の記述を持たせない（他の欄で当たらないように）。

使い方（順に）:
  python3 eval/eval_search.py make              # eval/results/docs.tsv と queries.tsv を作る（乱数の種は固定）
  python3 eval/eval_search.py load              # 手元（localhost:8090）に EVAL-JA リポジトリを作って入れる
  python3 eval/eval_search.py run <設定の名前>  # 検索して eval/results/results-<名前>.tsv と集計を出す
  python3 eval/eval_search.py summary           # 全設定の集計を並べる

既定の admin/admin は試験環境の初期値。本番では使わない。
"""

import csv
import json
import os
import random
import sys
import time
import urllib.parse
from pathlib import Path

from aspace_api import call, login

HERE = Path(__file__).resolve().parent
OUT = HERE / "results"
ITAIJI = HERE.parent / "plugins" / "japanese" / "solr" / "itaiji-ja.tsv"
REPO_CODE = "EVAL-JA"
SEED = 20261028

# 旧字の対を含む語（今の字で書く）。旧字は itaiji-ja.tsv から引く
ITAIJI_WORDS = ["写真", "学会", "旧蔵", "会議", "図書", "台湾", "鉄道", "横浜", "広島", "沢田",
                "国語", "戦争", "来訪", "号外", "区役所", "県庁", "気象", "発電所", "芸術", "体育",
                "医学", "薬品", "桜井", "竜宮", "亀山", "恵比寿", "絵画", "楽団", "書状", "神社"]
# カタカナの複合語と、その一部の語（一部の語で検索して複合語も拾えるか）
KATAKANA = [("ガラスプレート", "ガラス"), ("ポストカード", "カード"), ("ネガフィルム", "フィルム"),
            ("スクラップブック", "スクラップ"), ("レコードジャケット", "レコード"), ("カメラマン", "カメラ"),
            ("ラジオドラマ", "ドラマ"), ("テレビニュース", "ニュース"), ("パンフレット", "パンフ"),
            ("ポスターデザイン", "ポスター")]
# 字の並びを入れ替えると別の語になる組（語順を見ないと取り違える）
ORDER = [("田中", "中田"), ("山下", "下山"), ("山本", "本山"), ("上野", "野上"), ("会社", "社会"),
         ("日本", "本日"), ("中山", "山中"), ("川上", "上川"), ("科学", "学科"), ("市長", "長市")]
# 字が離れて現れるだけの紛らわしい題名（検索語, 題名）
SCATTER = [("東京", "京橋の東側"), ("東京", "東山の京菓子"), ("京都", "都心の京菓子"), ("京都", "都の京人形"),
           ("大阪", "阪神の大会"), ("大阪", "阪急の大型店"), ("北海道", "道北の海"), ("北海道", "海道の北側")]
# 対照（どの設定でも問題が起きないはずの語）
CONTROL = ["書簡", "日記", "名簿", "地図", "新聞", "手紙", "葉書", "大学"]

FRAMES = ["{w}", "{w}一括", "{w}関係綴", "昭和期の{w}", "{w}ほか", "{w}（控）", "明治期{w}"]


def old_map():
    """今の字 → 旧字（複数あれば先頭）。"""
    m = {}
    for line in ITAIJI.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        old, new = line.split("\t")
        m.setdefault(new, old)
    return m


def fold_map():
    """旧字 → 今の字（正解を決めるための畳み込み）。"""
    m = {}
    for line in ITAIJI.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        old, new = line.split("\t")
        m[old] = new
    return m


def fold(s, fm):
    return "".join(fm.get(c, c) for c in s)


def make():
    rnd = random.Random(SEED)
    om = old_map()
    docs, queries = [], []

    def add(title, kind):
        docs.append((f"E{len(docs) + 1:04d}", title, kind))

    def framed(w, n):
        return [rnd.choice(FRAMES).format(w=w) for _ in range(n)]

    for w in ITAIJI_WORDS:
        full = "".join(om.get(c, c) for c in w)
        assert full != w, f"旧字が無い: {w}"
        # 一部だけ旧字の書き方（寫真 など）。旧字のある最初の字だけを旧字にする
        i = next(i for i, c in enumerate(w) if c in om)
        part = w[:i] + om[w[i]] + w[i + 1:]
        for t in framed(w, 3):
            add(t, "itaiji:new")
        for t in framed(full, 3):
            add(t, "itaiji:old")
        if part != full:
            for t in framed(part, 1):
                add(t, "itaiji:mixed")
        queries += [(w, "itaiji-new"), (full, "itaiji-old")]
    for whole, piece in KATAKANA:
        for t in framed(whole, 3):
            add(t, "katakana:compound")
        for t in framed(piece, 2):
            add(t, "katakana:piece")
        queries.append((piece, "katakana"))
    for a, b in ORDER:
        for t in framed(a, 3):
            add(t, "order")
        for t in framed(b, 3):
            add(t, "order")
        queries += [(a, "order"), (b, "order")]
    for q in dict.fromkeys(q for q, _ in SCATTER):
        for t in framed(q, 2):
            add(t, "scatter:true")
        queries.append((q, "scatter"))
    for q, title in SCATTER:
        add(title, "scatter:decoy")
    for w in CONTROL:
        for t in framed(w, 3):
            add(t, "control")
        queries.append((w, "control"))

    fm = fold_map()
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "docs.tsv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(["id", "title", "kind"])
        w.writerows(docs)
    with open(OUT / "queries.tsv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(["query", "category", "n_relevant"])
        for q, cat in queries:
            n = sum(1 for _, t, _ in docs if fold(q, fm) in fold(t, fm))
            w.writerow([q, cat, n])
    print(f"docs {len(docs)}, queries {len(queries)} → {OUT}")


def read_tsv(name):
    with open(OUT / name, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def find_repo(token):
    for r in call("GET", "/repositories", token=token):
        if r["repo_code"] == REPO_CODE:
            return r["uri"]
    return None


def load():
    token = login()
    repo = find_repo(token)
    if repo and call("GET", f"{repo}/resources?all_ids=true", token=token):
        sys.exit(f"{REPO_CODE} に資料群が既にある。入れ直すなら管理画面でリポジトリを消してから")
    if not repo:
        repo = call("POST", "/repositories", {"repo_code": REPO_CODE, "name": "Evaluation"}, token)["uri"]
    res = call("POST", f"{repo}/resources", {
        "finding_aid_language": "jpn", "finding_aid_script": "Jpan",
        "title": "Evaluation set", "id_0": "EVAL-001", "level": "collection", "publish": True,
        "lang_materials": [{"language_and_script": {"language": "jpn", "script": "Jpan"}}],
        "dates": [{"label": "creation", "date_type": "single", "expression": "2026", "begin": "2026"}],
        "extents": [{"portion": "whole", "number": "1", "extent_type": "volumes"}],
    }, token)["uri"]
    ids = {}
    for d in read_tsv("docs.tsv"):
        ao = call("POST", f"{repo}/archival_objects", {
            "title": d["title"], "level": "item", "publish": True,
            "component_id": d["id"], "resource": {"ref": res},
        }, token)
        ids[ao["uri"]] = d["id"]
    (OUT / "uri-map.json").write_text(json.dumps(ids, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{repo}: {len(ids)} 件を入れた")


def search(token, repo, q):
    hits, page = set(), 1
    while True:
        qs = urllib.parse.urlencode({"q": q, "type[]": "archival_object", "page": page, "page_size": 250})
        r = call("GET", f"{repo}/search?{qs}", token=token)
        hits |= {x["uri"] for x in r["results"]}
        if page >= r["last_page"]:
            return hits
        page += 1


def run(setting):
    token = login()
    repo = find_repo(token)
    uri2id = json.loads((OUT / "uri-map.json").read_text(encoding="utf-8"))
    docs = read_tsv("docs.tsv")
    # 索引が追いついているか（全件が「*」で見つかるか）
    n = len(search(token, repo, "*"))
    if n != len(docs):
        sys.exit(f"索引に {n}/{len(docs)} 件しか無い。索引の作成を待ってからやり直す")
    fm = fold_map()
    rows = []
    for qd in read_tsv("queries.tsv"):
        q = qd["query"]
        rel = {d["id"] for d in docs if fold(q, fm) in fold(d["title"], fm)}
        t0 = time.perf_counter()
        got = {uri2id[u] for u in search(token, repo, q)}
        ms = (time.perf_counter() - t0) * 1000
        tp = len(rel & got)
        rows.append({"query": q, "category": qd["category"], "relevant": len(rel), "retrieved": len(got),
                     "tp": tp, "recall": tp / len(rel) if rel else 1.0,
                     "precision": tp / len(got) if got else (1.0 if not rel else 0.0), "ms": round(ms, 1),
                     "false_hits": " ".join(sorted(got - rel)), "missed": " ".join(sorted(rel - got))})
    with open(OUT / f"results-{setting}.tsv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print_summary({setting: rows})


def print_summary(by_setting):
    cats = ["itaiji-new", "itaiji-old", "katakana", "order", "scatter", "control"]
    print("設定\t区分\t語数\t再現率\t適合率\t全部正しい語")
    for s, rows in by_setting.items():
        for c in cats + ["(全体)"]:
            rs = [r for r in rows if c == "(全体)" or r["category"] == c]
            if not rs:
                continue
            rec = sum(float(r["recall"]) for r in rs) / len(rs)
            pre = sum(float(r["precision"]) for r in rs) / len(rs)
            ok = sum(1 for r in rs if float(r["recall"]) == 1 and float(r["precision"]) == 1)
            print(f"{s}\t{c}\t{len(rs)}\t{rec:.3f}\t{pre:.3f}\t{ok}/{len(rs)}")


def summary():
    by = {}
    for p in sorted(OUT.glob("results-*.tsv")):
        with open(p, encoding="utf-8") as f:
            by[p.stem[len("results-"):]] = list(csv.DictReader(f, delimiter="\t"))
    print_summary(by)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "make":
        make()
    elif cmd == "load":
        load()
    elif cmd == "run" and len(sys.argv) > 2:
        run(sys.argv[2])
    elif cmd == "summary":
        summary()
    else:
        print(__doc__)
