"""論文の評価（E3 IIIF）。画像付きの評価用の目録を手元に入れ、プラグインが出す IIIF の資源を検証する。

目録（リポジトリ EVAL-IIIF、資料群 1 件）:
  - 系列 S1・S2: 各 4 件のファイル。うち 3 件にデジタルオブジェクト（画像 4 枚）を付ける
  - 系列 S3: 画像を持たない枝（Collection から除かれるかを見る）
  - 系列 S4: 画像の枚数を変えたファイル 5 件。画像 1・10・50・100・200 枚のデジタルオブジェクトを付ける
画像は仮のもの（Pillow で作る。縦横を 4 通りに変える）。archivesspace/dip/eval/ に書く。

検証は、IIIF 公式の検証ツール（IIIF/presentation-validator）が Presentation 3.0 の検証に使う JSON Schema
（schema/iiif_3_0.json）で行う。ツール本体は動かさず、スキーマを Draft 7 で当てる（ツールより厳しい側になる）。
あわせて、Canvas の縦横が画像ファイルの実際の縦横と一致するか、Collection に画像の無い枝が入らないかを確かめる。

使い方:
  python3 eval/eval_iiif.py load                    # 画像を作り、手元（localhost:8090）に入れる
  python3 eval/eval_iiif.py check <iiif_3_0.json>   # 検証 → eval/results/iiif.tsv

公開画面に出すため、リポジトリ EVAL-IIIF は公開（publish）にしておく。
"""

import csv
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

from aspace_api import call, login

HERE = Path(__file__).resolve().parent.parent
DIP = HERE / "eval" / "images"
OUT = HERE / "eval" / "results"
PUB = "http://localhost:8090"
IMAGE_BASE = os.environ.get("IIIF_IMAGE_BASE", "https://example.org/dip/eval/")
REPO_CODE = "EVAL-IIIF"
SIZES = [(800, 1100), (1100, 800), (1000, 1000), (1600, 1200)]
TIMING = [1, 10, 50, 100, 200]
N_IMAGES = max(TIMING)


def image_name(i):
    return f"img-{i:03d}.jpg"


def make_images():
    from PIL import Image, ImageDraw

    DIP.mkdir(parents=True, exist_ok=True)
    for i in range(N_IMAGES):
        w, h = SIZES[i % len(SIZES)]
        im = Image.new("RGB", (w, h), (230 - i % 40, 220, 200 + i % 50))
        ImageDraw.Draw(im).rectangle([20, 20, w - 20, h - 20], outline=(80, 60, 40), width=6)
        im.save(DIP / image_name(i), quality=70)
    print(f"images {N_IMAGES} → {DIP}")


def find_repo(token):
    for r in call("GET", "/repositories", token=token):
        if r["repo_code"] == REPO_CODE:
            return r["uri"]
    return None


def digital_object(token, repo, ident, n):
    return call("POST", f"{repo}/digital_objects", {
        "title": f"画像 {n} 枚（{ident}）", "digital_object_id": ident, "publish": True,
        "file_versions": [{"file_uri": IMAGE_BASE + image_name(i), "use_statement": "image-service",
                           "publish": True, "file_format_name": "jpeg", "is_representative": i == 0}
                          for i in range(n)],
    }, token)["uri"]


def ao(token, repo, res, parent, title, cid, level, dobj=None):
    body = {"title": title, "component_id": cid, "level": level, "publish": True, "resource": {"ref": res}}
    if parent:
        body["parent"] = {"ref": parent}
    if dobj:
        body["instances"] = [{"instance_type": "digital_object", "digital_object": {"ref": dobj}}]
    return call("POST", f"{repo}/archival_objects", body, token)["uri"]


def load():
    make_images()
    token = login()
    if find_repo(token):
        sys.exit(f"{REPO_CODE} は既にある。入れ直すなら管理画面でリポジトリを消してから")
    repo = call("POST", "/repositories", {"repo_code": REPO_CODE, "name": "Evaluation IIIF"}, token)["uri"]
    res = call("POST", f"{repo}/resources", {
        "finding_aid_language": "jpn", "finding_aid_script": "Jpan",
        "title": "IIIF評価用資料群", "id_0": "EVAL-IIIF-001", "level": "collection", "publish": True,
        "lang_materials": [{"language_and_script": {"language": "jpn", "script": "Jpan"}}],
        "dates": [{"label": "creation", "date_type": "single", "expression": "2026", "begin": "2026"}],
        "extents": [{"portion": "whole", "number": "1", "extent_type": "volumes"}],
    }, token)["uri"]
    made = {"repo": repo, "resource": res, "series": {}, "files": [], "timing": {}}
    for s in ["S1", "S2", "S3", "S4"]:
        made["series"][s] = ao(token, repo, res, None, f"系列{s}", s, "series")
    for s in ["S1", "S2"]:
        for k in range(1, 5):
            cid = f"{s}-{k}"
            d = digital_object(token, repo, f"DO-{cid}", 4) if k <= 3 else None
            made["files"].append({"ao": ao(token, repo, res, made["series"][s], f"ファイル{cid}", cid, "file", d),
                                  "do": d, "images": 4 if d else 0})
    for k in range(1, 4):
        made["files"].append({"ao": ao(token, repo, res, made["series"]["S3"], f"ファイルS3-{k}", f"S3-{k}", "file"),
                              "do": None, "images": 0})
    for n in TIMING:
        d = digital_object(token, repo, f"DO-T{n}", n)
        a = ao(token, repo, res, made["series"]["S4"], f"生成時間{n}枚", f"T{n}", "file", d)
        made["timing"][n] = {"ao": a, "do": d}
    (OUT / "iiif-map.json").write_text(json.dumps(made, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{repo}: resource {res}")


def get(path):
    t0 = time.perf_counter()
    with urllib.request.urlopen(PUB + path) as r:
        body = json.loads(r.read())
    return body, (time.perf_counter() - t0) * 1000


def actual_sizes():
    from PIL import Image
    return {IMAGE_BASE + p.name: Image.open(p).size for p in DIP.glob("*.jpg")}


def check(schema_path):
    from jsonschema import Draft7Validator

    validator = Draft7Validator(json.loads(Path(schema_path).read_text(encoding="utf-8")))
    made = json.loads((OUT / "iiif-map.json").read_text(encoding="utf-8"))
    sizes = actual_sizes()
    targets = [("manifest", made["resource"] + "/manifest.json"), ("collection", made["resource"] + "/collection.json")]
    for s, uri in made["series"].items():
        targets.append(("collection", uri + "/collection.json"))
    for f in made["files"]:
        if f["do"]:
            targets += [("manifest", f["ao"] + "/manifest.json"), ("manifest", f["do"] + "/manifest.json")]
    for n, t in made["timing"].items():
        targets += [("manifest", t["do"] + "/manifest.json")]
    rows = []
    for kind, path in targets:
        try:
            body, _ = get(path)
        except urllib.error.HTTPError as e:
            rows.append({"kind": kind, "path": path, "status": e.code, "schema_errors": "", "canvases": "",
                         "size_mismatch": "", "items": ""})
            continue
        errors = list(validator.iter_errors(body))
        canv = [c for c in body.get("items", []) if c.get("type") == "Canvas"]
        mismatch = 0
        for c in canv:
            img = c["items"][0]["items"][0]["body"]
            if sizes.get(img["id"]) != (c["width"], c["height"]):
                mismatch += 1
        rows.append({"kind": kind, "path": path, "status": 200, "schema_errors": len(errors), "canvases": len(canv),
                     "size_mismatch": mismatch,
                     "items": " ".join(i["type"] + ":" + i["id"].replace(PUB, "") for i in body.get("items", [])
                                       if i.get("type") in ("Collection", "Manifest"))})
    # Change Discovery（スキーマは無いので、形だけを確かめる）
    top, _ = get("/iiif/discovery/activity/all-changes")
    n_items, bad = 0, 0
    page = top["first"]["id"].replace(PUB, "")
    while True:
        p, _ = get(page)
        for it in p["orderedItems"]:
            n_items += 1
            ok = it.get("type") == "Update" and it.get("endTime") and it["object"].get("type") == "Manifest"
            bad += 0 if ok else 1
        if "next" not in p:
            break
        page = p["next"]["id"].replace(PUB, "")
    rows.append({"kind": "discovery", "path": "/iiif/discovery/activity/all-changes", "status": 200,
                 "schema_errors": bad, "canvases": n_items, "size_mismatch": "", "items": f"totalItems={top.get('totalItems')}"})
    with open(OUT / "iiif.tsv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print(r["kind"], r["path"], r["status"], "errors", r["schema_errors"], "canvases", r["canvases"],
              "mismatch", r["size_mismatch"], r["items"][:160])


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "load":
        load()
    elif cmd == "check" and len(sys.argv) > 2:
        check(sys.argv[2])
    else:
        print(__doc__)
