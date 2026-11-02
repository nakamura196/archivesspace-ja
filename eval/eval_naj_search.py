"""論文の評価（E2 検索）を実データで行う。国立公文書館「公文録・明治９年」の件名 6,162 件の標題を使う。

作り物の評価用データでは設計どおりの満点になるため、実際の目録の標題で、既定 (a) と拡張 (b)(c)(d) を比べる。
  (a) naj_default   : 既定（同義語を入れる前の schema.xml.bak-itaiji）
  (b) naj_itaiji    : 検索側の ManagedSynonymGraph で旧字 → 新字（365 組）
  (c) naj_bigram    : CJKWidth + CJKBigram と、索引・検索の両側で旧字を新字に寄せる MappingCharFilter
  (d) naj_bigram_uni: (c) に索引側だけ outputUnigrams="true"
コアの作り方・検索の条件は eval_bigram_core.py と同じ（ArchivesSpace が Solr に送る条件）。
既存の eval_* / eval_full_* / archivesspace コアには触らない。

正解（Solr に依存しない）:
  記録の標題を新字体に寄せた文字列が、検索語（空白で区切られていれば各語）を新字体に寄せた文字列を
  部分文字列として含むとき、その記録を正解とする（空白区切りの複数語は、すべて含むこと = AND）。
  新字体に寄せるとは itaiji-ja.tsv の旧字 → 新字（365 組）で 1 字ずつ置き換えること。
  ArchivesSpace の既定の検索が q.op=AND の部分一致に近い振る舞いをする前提と、E2 の既存評価
  （eval_search.py）の定義に合わせた。語の切れ目（形態素）を使わないのは、標題が分かち書きされていないため。
索引する欄: id, uri, title, identifier(component_id), fullrecord(標題 + 識別番号)。親の簿冊の標題は入れない
  （入れると標題以外で当たり、正解の定義と食い違うため）。

使い方（このリポジトリの直下で。先に eval/naj_fetch.py で data/naj/raw に目録を取っておく）:
  python3 eval/eval_naj_search.py setup   # 4 つのコアを作り、標題を入れる
  python3 eval/eval_naj_search.py run     # 検索語の組を作って流し、eval/results/naj/ に書く
  python3 eval/eval_naj_search.py drop    # NAJ 用のコアを消す
"""

import csv
import glob
import json
import random
import re
import sys
import time
import urllib.parse
from collections import Counter
from pathlib import Path

import eval_bigram_core as core

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RAW = ROOT / "data" / "naj" / "raw"
OUT = HERE / "results" / "naj"
ITAIJI = ROOT / "plugins" / "japanese" / "solr" / "itaiji-ja.tsv"
SEED = 20261028
CORES = {"a-default": "naj_default", "b-itaiji": "naj_itaiji", "c-bigram": "naj_bigram", "d-bigram-uni": "naj_bigram_uni"}
KANJI = re.compile(r"[一-鿿々]+")
ROWS = 7000


# ---------- データ ----------
def read_itaiji():
    old2new = {}
    for line in ITAIJI.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        old, new = line.split("\t")
        old2new[old] = new
    new2old = {}
    for old, new in old2new.items():
        new2old.setdefault(new, old)
    return old2new, new2old


OLD2NEW, NEW2OLD = read_itaiji()


def fold(s):
    return "".join(OLD2NEW.get(c, c) for c in s)


def to_old(s):
    return "".join(NEW2OLD.get(c, c) for c in s)


def load_items():
    items = {}
    for f in sorted(glob.glob(str(RAW / "items_*.json"))):
        for b in json.load(open(f, encoding="utf-8"))["results"]["bindings"]:
            iid = b["i"]["value"].rsplit("/", 1)[1]
            items[iid] = {"title": b["title"]["value"], "identifier": b.get("id", {}).get("value", "")}
    return items


# ---------- 検索語の組 ----------
def ngram_df(folded_titles, lens):
    """新字体に寄せた標題について、漢字の連なりの中の n 字連続の出現標題数。"""
    df = Counter()
    for t in folded_titles:
        seen = set()
        for run in KANJI.findall(t):
            for n in lens:
                for i in range(len(run) - n + 1):
                    seen.add(run[i:i + n])
        df.update(seen)
    return df


def make_queries(items):
    rnd = random.Random(SEED)
    ids = sorted(items)
    folded = {i: fold(items[i]["title"]) for i in ids}
    df = ngram_df(folded.values(), (1, 2, 3, 4))
    conv = set(NEW2OLD)  # 旧字のある新字
    qs, notes = [], []

    # A / B: 新字を含む 2〜4 字の語（出現 5 件以上）。2 字 20・3 字 15・4 字 10 を無作為に選ぶ
    pool = {n: sorted(w for w, c in df.items() if len(w) == n and c >= 5 and any(ch in conv for ch in w)) for n in (2, 3, 4)}
    words = []
    for n, k in ((2, 20), (3, 15), (4, 10)):
        words += rnd.sample(pool[n], min(k, len(pool[n])))
        notes.append(f"A/B 候補: {n} 字 {len(pool[n])} 語（出現 5 件以上、365 組の新字を含む）から {min(k, len(pool[n]))} 語を無作為に選択")
    for w in words:
        qs.append(("A-old", to_old(w), f"標題の語「{w}」の新字をすべて旧字に置換"))
    for w in words:
        qs.append(("B-new", w, "同じ語を新字体のまま"))

    # C1: 1 字。新字のある字（旧字で検索）10・それ以外 10（出現 5〜500 件）+ 彌/弥
    one = sorted(w for w, c in df.items() if len(w) == 1 and 5 <= c <= 500)
    one_conv = [w for w in one if w in conv]
    one_plain = [w for w in one if w not in conv and w not in OLD2NEW]
    notes.append(f"C1 候補: 新字のある字 {len(one_conv)}・それ以外 {len(one_plain)}（出現 5〜500 件）から各 10 字")
    for w in rnd.sample(one_conv, 10):
        qs.append(("C1-char-old", to_old(w), f"新字「{w}」を旧字にして 1 字で検索"))
    for w in rnd.sample(one_plain, 10):
        qs.append(("C1-char-plain", w, "新字のない字を 1 字で検索"))
    for w, why in (("弥", "人名に出る字（新字）"), ("彌", "人名に出る字（旧字。標題に旧字で現れるもの）")):
        qs.append(("C1-char-name", w, why))

    # C2: 長い標題（15 字以上）の中の 2 字の語（出現 2〜30 件）20 語 + 賞与
    long_titles = [folded[i] for i in ids if len(folded[i]) >= 15]
    cand = set()
    for t in long_titles:
        for run in KANJI.findall(t):
            for i in range(len(run) - 1):
                if 2 <= df[run[i:i + 2]] <= 30:
                    cand.add(run[i:i + 2])
    cand = sorted(cand)
    notes.append(f"C2 候補: 15 字以上の標題の漢字連続中の 2 字で出現 2〜30 件のもの {len(cand)} 語から 20 語")
    for w in rnd.sample(cand, 20):
        qs.append(("C2-part2", w, "長い標題の一部の 2 字"))
    qs.append(("C2-part2", "賞与", "例: 華族伊達宗徳外四人賞与ノ儀上申"))

    # D: 標題の中で離れて出る 2 語（各 2〜3 字・出現 5 件以上・間に 2 字以上）を空白区切りで。15 組
    longer = [i for i in ids if len(folded[i]) >= 14]
    rnd.shuffle(longer)
    pairs = []
    for i in longer:
        t = folded[i]
        found = []
        for run_m in KANJI.finditer(t):
            run, off = run_m.group(), run_m.start()
            for n in (2, 3):
                for k in range(len(run) - n + 1):
                    if df[run[k:k + n]] >= 5:
                        found.append((off + k, off + k + n, run[k:k + n]))
        ok = [(a, b) for a in found for b in found if b[0] >= a[1] + 2 and a[2] != b[2]]
        if ok:
            a, b = rnd.choice(ok)
            if (a[2], b[2]) not in pairs:
                pairs.append((a[2], b[2]))
        if len(pairs) == 15:
            break
    for a, b in pairs:
        qs.append(("D-order", f"{a} {b}", "標題の中の出現順で空白区切り"))
    for a, b in pairs:
        qs.append(("D-reverse", f"{b} {a}", "出現順を逆にして空白区切り"))
    for a, b in pairs:
        if to_old(a) != a or to_old(b) != b:
            qs.append(("D-old", f"{to_old(a)} {to_old(b)}", "旧字に置換して空白区切り"))
    notes.append("D: 14 字以上の標題を無作為な順に見て、2〜3 字で出現 5 件以上の語を、間に 2 字以上あけて 2 つ取る（15 組）")
    return qs, notes, folded


def relevant(q, folded):
    terms = fold(q).split()
    return {i for i, t in folded.items() if all(w in t for w in terms)}


# ---------- コア ----------
def setup():
    core.write_mapping()
    original = core.sh("docker", "exec", core.CONTAINER, "cat", f"{core.CONF}/schema.xml.bak-itaiji")
    current = core.sh("docker", "exec", core.CONTAINER, "cat", f"{core.CONF}/schema.xml")
    managed = core.sh("docker", "exec", core.CONTAINER, "cat", f"{core.CONF}/_schema_analysis_synonyms_ja_itaiji.json")
    start = original.index('    <fieldType name="text_general"')
    end = original.index("</fieldType>", start) + len("</fieldType>\n")
    mapping = core.MAPPING.read_text(encoding="utf-8")
    core.make_core("naj_default", original, {})
    core.make_core("naj_itaiji", current, {"_schema_analysis_synonyms_ja_itaiji.json": managed})
    core.make_core("naj_bigram", original[:start] + core.BIGRAM_TYPE + original[end:], {"itaiji-mapping.txt": mapping})
    core.make_core("naj_bigram_uni", original[:start] + core.BIGRAM_UNI_TYPE + original[end:], {"itaiji-mapping.txt": mapping})
    items = load_items()
    docs = [{"id": f"naj-{i}", "uri": f"/naj/{i}", "title": v["title"], "identifier": v["identifier"],
             "primary_type": "archival_object", "types": ["archival_object"], "repository": "/repositories/99",
             "fullrecord": f'{v["title"]} {v["identifier"]}'} for i, v in sorted(items.items())]
    for c in CORES.values():
        t0 = time.perf_counter()
        for k in range(0, len(docs), 2000):
            core.http(f"{core.SOLR}/{c}/update", json.dumps(docs[k:k + 2000]).encode())
        core.http(f"{core.SOLR}/{c}/update?commit=true", b"[]")
        n = core.http(f"{core.SOLR}/{c}/select?q=*:*&rows=0&wt=json")["response"]["numFound"]
        print(f"{c}: {n} 件（{time.perf_counter() - t0:.1f} 秒）")


def search(c, q):
    params = dict(core.PARAMS, q=q, rows=ROWS, wt="json", fl="uri")
    d = core.http(f"{core.SOLR}/{c}/select?{urllib.parse.urlencode(params, doseq=True)}")["response"]
    assert d["numFound"] <= ROWS
    return {x["uri"].rsplit("/", 1)[1] for x in d["docs"]}


def run():
    items = load_items()
    qs, notes, folded = make_queries(items)
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for setting, c in CORES.items():
        for group, q, why in qs:
            rel = relevant(q, folded)
            got = search(c, q)
            tp = len(rel & got)
            rows.append({"setting": setting, "group": group, "query": q, "note": why, "relevant": len(rel),
                         "retrieved": len(got), "tp": tp,
                         "recall": f"{tp / len(rel):.4f}" if rel else "",
                         "precision": f"{tp / len(got):.4f}" if got else "",
                         "missed": " ".join(sorted(rel - got)[:5]), "false_hits": " ".join(sorted(got - rel)[:5])})
    with open(OUT / "search.tsv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    write_summary(rows, qs, notes, items, folded)


def mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def write_summary(rows, qs, notes, items, folded):
    groups = []
    for g, _, _ in qs:
        if g not in groups:
            groups.append(g)
    L = ["# NAJ「公文録・明治９年」標題での検索評価（E2 実データ版）", "",
         f"- 実行日: {time.strftime('%Y-%m-%d')}、Solr 9.9.0、記録 {len(items)} 件（件名の標題のみ）、乱数の種 {SEED}",
         "- 出典: 国立公文書館所蔵（目録情報 CC0）", "- 設定: " + " / ".join(f"{k}={v}" for k, v in CORES.items()), "",
         "## 正解の定義（Solr に依存しない）", "",
         "標題・検索語とも itaiji-ja.tsv の旧字 → 新字（365 組）で 1 字ずつ新字体に寄せたうえで、標題が検索語を部分文字列として含む記録を正解とする。",
         "空白区切りの複数語は、すべてを含む記録（AND、順序は問わない）。",
         "理由: 標題は分かち書きされておらず形態素の切れ目を使えないこと、E2 の既存評価（eval_search.py）と定義を揃えること、",
         "検索エンジンの出力を正解に使わないこと。限界: 「語として」の一致ではなく文字列の一致なので、語の途中で当たる記録（例: 「学校」が「医学校」）も正解に数える。",
         "再現率・適合率は検索語ごとに出して平均した（マクロ平均）。適合率は、1 件も返らなかった検索語を除いて平均し、0 件の語数は別に示す。", "",
         "## 検索語の作り方", ""] + [f"- {n}" for n in notes] + [
         "", "検索クエリは ArchivesSpace が Solr に送る条件（edismax, q.op=AND, qf=identifier_ws^3 title_ws^2 finding_aid_filing_title^2 fullrecord）と同じ。", "",
         "## 設定 × 組ごとの平均（検索語数 / 再現率 / 適合率 / 0件の語数 / 再現率1かつ適合率1の語数）", ""]
    L.append("| 組 | 語数 | " + " | ".join(CORES) + " |")
    L.append("|---|---|" + "---|" * len(CORES))
    for g in groups + ["(全体)"]:
        cells = []
        n = 0
        for s in CORES:
            rs = [r for r in rows if r["setting"] == s and (g == "(全体)" or r["group"] == g)]
            n = len(rs)
            rec = mean([float(r["recall"]) for r in rs if r["recall"]])
            pr = [float(r["precision"]) for r in rs if r["precision"]]
            zero = sum(1 for r in rs if r["retrieved"] == 0)
            perfect = sum(1 for r in rs if r["recall"] and r["precision"] and float(r["recall"]) == 1 and float(r["precision"]) == 1)
            cells.append(f"R {rec:.3f} / P {mean(pr):.3f} / 0件 {zero} / 満点 {perfect}")
        L.append(f"| {g} | {n} | " + " | ".join(cells) + " |")
    L += ["", "## 件数の合計（組ごと。正解 / 返った / 当たった）", ""]
    L.append("| 組 | " + " | ".join(CORES) + " |")
    L.append("|---|" + "---|" * len(CORES))
    for g in groups:
        cells = []
        for s in CORES:
            rs = [r for r in rows if r["setting"] == s and r["group"] == g]
            cells.append(f'{sum(int(r["relevant"]) for r in rs)} / {sum(int(r["retrieved"]) for r in rs)} / {sum(int(r["tp"]) for r in rs)}')
        L.append(f"| {g} | " + " | ".join(cells) + " |")

    def ex(r, kind):
        ids = (r["missed"] if kind == "missed" else r["false_hits"]).split()
        t = items[ids[0]]["title"] if ids else ""
        return f'- {r["setting"]} / {r["group"]} / 検索語「{r["query"]}」: 正解 {r["relevant"]}・返却 {r["retrieved"]}・当たり {r["tp"]}。例 {kind == "missed" and "取りこぼし" or "誤検出"}: 「{t}」'

    L += ["", "## 目立った実例（自動抽出: 設定ごとに再現率の最も低い語と適合率の最も低い語）", ""]
    for s in CORES:
        rs = [r for r in rows if r["setting"] == s]
        miss = sorted((r for r in rs if r["missed"]), key=lambda r: (float(r["recall"]), -int(r["relevant"])))
        fals = sorted((r for r in rs if r["false_hits"]), key=lambda r: (float(r["precision"]), -int(r["retrieved"])))
        if miss:
            L.append(ex(miss[0], "missed"))
        if fals:
            L.append(ex(fals[0], "false"))
    L += ["", "## (d) の 1 字索引による誤検出（(c) では当たらず (d) だけで返った件数）", ""]
    byq = {}
    for r in rows:
        byq.setdefault((r["group"], r["query"]), {})[r["setting"]] = r
    extra = []
    for (g, q), d in byq.items():
        dd, cc = d["d-bigram-uni"], d["c-bigram"]
        diff = int(dd["retrieved"]) - int(cc["retrieved"])
        if diff > 0 or float(dd["precision"] or 1) < float(cc["precision"] or 1) - 1e-9:
            extra.append((diff, g, q, dd, cc))
    L.append(f"- (d) が (c) より多く返した検索語: {len(extra)} 語 / {len(byq)} 語")
    for diff, g, q, dd, cc in sorted(extra, key=lambda x: -x[0])[:5]:
        L.append(f'- {g} 「{q}」: (c) 返却 {cc["retrieved"]}（適合率 {cc["precision"]}）→ (d) 返却 {dd["retrieved"]}（適合率 {dd["precision"]}）')
    L.append("")
    (OUT / "search-summary.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))


def drop():
    for c in CORES.values():
        q = urllib.parse.urlencode({"action": "UNLOAD", "core": c, "deleteInstanceDir": "true", "wt": "json"})
        core.http(f"{core.SOLR}/admin/cores?{q}")
        print("dropped", c)
    names = list(core.http(f"{core.SOLR}/admin/cores?action=STATUS&wt=json")["status"])
    print("残っているコア:", names)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"setup": setup, "run": run, "drop": drop}.get(cmd, lambda: print(__doc__))()
