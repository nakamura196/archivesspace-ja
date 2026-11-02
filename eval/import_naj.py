"""国立公文書館（NAJ）「公文録・明治９年」の目録を、手元の ArchivesSpace に入れる（論文の実データ評価用）。

使い方:
  python3 eval/import_naj.py --mode naive [--limit N] [--reset]   そのまま写す（直さず、弾かれたものを記録する）
  python3 eval/import_naj.py --mode fixed [--reset]               弾かれた原因に手当てして写す
- 専用のリポジトリ NAJ を作る（あれば使い回す）。--reset はそのリポジトリの資料群を消して作り直す（他のリポジトリには触らない）
- 資料群 = Resource、簿冊 = Archival Object (file)、件名・細目 = その子 (item)
- 簿冊の既存確認は component_id ではなく Resource の id_0/id_1 で行う。同じ資料群が既にあれば飛ばす
- IIIF マニフェストは external_documents（外部リンク）で付ける
- 弾かれた記録は data/naj/import-errors-<mode>.jsonl に、所要時間は標準出力に出す
先に eval/naj_fetch.py で data/naj/raw に目録を取っておく。接続先と資格情報は aspace_api.py と同じ（ASPACE_API / ASPACE_USER / ASPACE_PASSWORD）。
"""
import argparse, glob, json, re, sys, time, urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import aspace_api
from aspace_api import login

RETRIES = {"n": 0}


def call(method, path, body=None, token=None):
    """5xx（サーバ再起動中の 502 など）は待って 6 回まで出し直す。4xx（検証エラー）は出し直さない。"""
    for k in range(7):
        try:
            return aspace_api.call(method, path, body, token)
        except urllib.error.HTTPError as e:
            if e.code < 500 or k == 6:
                raise
        except urllib.error.URLError:
            if k == 6:
                raise
        RETRIES["n"] += 1
        time.sleep(10)

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data/naj/raw"
REPO_CODE = "NAJ"
FONDS_NO = "568359"
FONDS_TITLE = "公文録・明治９年"
ATTR = "国立公文書館所蔵"


def load(pattern):
    rows = []
    for f in sorted(glob.glob(str(RAW / pattern))):
        rows += json.load(open(f))["results"]["bindings"]
    return [{k: v["value"] for k, v in b.items()} for b in rows]


def dates(node, fixed):
    b, e = node.get("from"), node.get("to")
    expr = b + (f"/{e}" if e else "")
    d = {"label": "creation", "date_type": "inclusive" if e else "single", "begin": b}
    if e:
        d["end"] = e
    if fixed:
        d["expression"] = expr
        if e and (e < b[:len(e)] or (e == b[:len(e)] and len(e) < len(b))):
            # 終了が開始より前（または粗くて開始に含まれる）。終了は表記だけに残す
            d.pop("end"); d["date_type"] = "single"
    return [d]


def body_common(node, fixed, repo, resource_uri, agent_uri):
    t = node["title"]
    b = {
        "title": t,
        "component_id": node["id"],
        "level": "file" if node["kind"] == "file" else "item",
        "publish": True,
        "resource": {"ref": resource_uri},
        "dates": dates(node, fixed),
        "linked_agents": [{"role": "creator", "ref": agent_uri}],
    }
    if node.get("see"):
        b["external_documents"] = [{"title": "IIIF マニフェスト（" + ATTR + "）", "location": node["see"]}]
    return b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["naive", "fixed"], required=True)
    ap.add_argument("--limit", type=int, help="簿冊の数を絞る（試し用）")
    ap.add_argument("--reset", action="store_true")
    a = ap.parse_args()
    fixed = a.mode == "fixed"
    errlog = open(ROOT / f"data/naj/import-errors-{a.mode}.jsonl", "w")
    errs = {"n": 0}

    def fail(kind, node, err):
        errs["n"] += 1
        body = getattr(err, "body", str(err))
        errlog.write(json.dumps({"kind": kind, "id": node.get("id"), "title": node.get("title"),
                                 "from": node.get("from"), "to": node.get("to"), "status": getattr(err, "code", None),
                                 "response": body}, ensure_ascii=False) + "\n")

    files, items = load("files_*.json"), load("items_*.json")
    for f in files: f["kind"] = "file"
    for i in items: i["kind"] = "item"
    if a.limit:
        files = files[:a.limit]
    children = {}
    for it in items:
        children.setdefault(it["parent"], []).append(it)
    if fixed:  # 並び順は識別子順にする
        files.sort(key=lambda x: x["id"])
        for v in children.values(): v.sort(key=lambda x: x["id"])

    t = login()
    repo = next((r for r in call("GET", "/repositories", token=t) if r["repo_code"] == REPO_CODE), None)
    if not repo:
        repo = call("POST", "/repositories", {"repo_code": REPO_CODE, "name": "国立公文書館（試験取り込み）", "publish": True}, t)
    uri = repo["uri"]
    exist = call("GET", f"{uri}/resources?all_ids=true", token=t)
    if exist and a.reset:
        t0 = time.time()
        for i in exist:
            call("DELETE", f"{uri}/resources/{i}", token=t)
        print(f"reset: {len(exist)} resources deleted in {time.time()-t0:.1f}s")
    elif exist:
        print("既に資料群があるので飛ばします（--reset で作り直し）"); return

    # 作成者 agent（全件共通の「太政官」）
    t0 = time.time()
    try:
        agent = call("POST", "/agents/corporate_entities", {"names": [
            {"primary_name": "太政官", "sort_name_auto_generate": True, "source": "local"}]}, t)["uri"]
    except urllib.error.HTTPError as e:  # agent は全リポジトリ共通。再実行では既存のものを使う
        agent = json.loads(e.body)["error"]["conflicting_record"][0]
    resource = call("POST", f"{uri}/resources", {
        "title": FONDS_TITLE, "id_0": "NAJ", "id_1": FONDS_NO, "level": "recordgrp", "publish": True,
        "dates": [{"label": "creation", "date_type": "single", "begin": "1876", "expression": "1876"}],
        "extents": [{"portion": "whole", "number": str(len(files)), "extent_type": "volumes"}],
        "lang_materials": [{"language_and_script": {"language": "jpn", "script": "Jpan"}}],
        "finding_aid_language": "jpn", "finding_aid_script": "Jpan",
        "linked_agents": [{"role": "creator", "ref": agent}],
        "notes": [{"jsonmodel_type": "note_multipart", "type": "scopecontent", "publish": True,
                   "subnotes": [{"jsonmodel_type": "note_text", "content": f"出典: {ATTR}。目録情報は CC0。"}]}],
    }, t)["uri"]

    nf = ni = 0
    for f in files:
        try:
            fu = call("POST", f"{uri}/archival_objects", body_common(f, fixed, uri, resource, agent), t)["uri"]
            nf += 1
        except urllib.error.HTTPError as e:
            fail("file", f, e); continue
        for it in children.get(f["i"], []):
            b = body_common(it, fixed, uri, resource, agent)
            b["parent"] = {"ref": fu}
            try:
                call("POST", f"{uri}/archival_objects", b, t); ni += 1
            except urllib.error.HTTPError as e:
                fail("item", it, e)
        if nf % 20 == 0:
            print(f"files {nf} items {ni} errors {errs['n']} {time.time()-t0:.0f}s", flush=True)
    print(f"DONE mode={a.mode} files={nf} items={ni} errors={errs['n']} elapsed={time.time()-t0:.1f}s retries={RETRIES['n']} resource={resource}")


if __name__ == "__main__":
    main()
