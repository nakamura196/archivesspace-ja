#!/usr/bin/env python3
"""国立公文書館デジタルアーカイブ(NAJ)の目録を SPARQL で取得する。

既定では「公文録・明治９年」(fonds/568359) の簿冊と件名・細目を取る。
出典: 国立公文書館所蔵 / 目録情報は CC0
(https://www.digital.archives.go.jp/secondary-use)
エンドポイント: https://www.digital.archives.go.jp/sparql (1 回 30,000 トリプルまで)

使い方（このリポジトリの直下で）:  python3 eval/naj_fetch.py [--fonds 568359] [--out data/naj/raw]
リクエストの間に 1.5 秒以上あける。取得済みのページはスキップする(再実行可)。
"""
import argparse, json, os, sys, time, urllib.parse, urllib.request

EP = "https://www.digital.archives.go.jp/sparql"
UA = "Mozilla/5.0 (Macintosh) AppleWebKit/537.36 Chrome/120 Safari/537.36"
BASE = "http://www.digital.archives.go.jp"
DCT = "http://purl.org/dc/terms/"
PROV = "http://www.w3.org/ns/prov#"
FOAF = "http://xmlns.com/foaf/0.1/"
WAIT = 1.5
PAGE = 1000


def sparql(q):
    url = EP + "?" + urllib.parse.urlencode({"query": q})
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/sparql-results+json"})
    for n in range(4):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read()
            time.sleep(WAIT)
            return json.loads(data)
        except Exception as e:
            print("retry", n, e, file=sys.stderr)
            time.sleep(5 * (n + 1))
    raise SystemExit("failed")


def paged(out, name, member, fonds_clause):
    """member: 'file' or 'item'. 親からたどる句は fonds_clause (?i の親が対象)。"""
    p = 0
    while True:
        path = os.path.join(out, f"{name}_{p:03d}.json")
        if os.path.exists(path):
            d = json.load(open(path))
        else:
            q = f"""
SELECT ?i ?parent ?title ?id ?from ?to ?name ?see WHERE {{
  {{ SELECT DISTINCT ?i WHERE {{ {fonds_clause} }} ORDER BY ?i LIMIT {PAGE} OFFSET {p*PAGE} }}
  ?i <{DCT}isPartOf> ?parent .
  OPTIONAL {{ ?i <{DCT}title> ?title }}
  OPTIONAL {{ ?i <{DCT}identifier> ?id }}
  OPTIONAL {{ ?i <{PROV}startedAtTime> ?from }}
  OPTIONAL {{ ?i <{PROV}endedAtTime> ?to }}
  OPTIONAL {{ ?i <{FOAF}name> ?name }}
  OPTIONAL {{ ?i <http://www.w3.org/2000/01/rdf-schema#seeAlso> ?see }}
}}"""
            d = sparql(q)
            json.dump(d, open(path, "w"), ensure_ascii=False)
        n = len({b["i"]["value"] for b in d["results"]["bindings"]})
        print(name, p, n)
        if n < PAGE:
            break
        p += 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fonds", default="568359")
    ap.add_argument("--out", default="data/naj/raw")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    F = f"<{BASE}/fonds/{a.fonds}>"
    # 上位階層(資料群)のタイトル
    path = os.path.join(a.out, "fonds_chain.json")
    if not os.path.exists(path):
        q = f"""SELECT ?f ?title ?parent WHERE {{
  VALUES ?f {{ {F} <{BASE}/fonds/2999753> <{BASE}/fonds/567818> }}
  ?f <{DCT}title> ?title . OPTIONAL {{ ?f <{DCT}isPartOf> ?parent }} }}"""
        json.dump(sparql(q), open(path, "w"), ensure_ascii=False)
    paged(a.out, "files", "file", f"?i <{DCT}isPartOf> {F} .")
    paged(a.out, "items", "item", f"?f <{DCT}isPartOf> {F} . ?i <{DCT}isPartOf> ?f .")


if __name__ == "__main__":
    main()
