# 使い方: python3 style-review/qa-2026-10-28/propagate.py（translation-ja/ で実行）
# Weblate で直した訳を、上流の en.yml が別名参照（<<: *）で使い回しているキーにも広げる。
# Weblate ではこれらのキーに項目が無く受け継ぎ元の訳が出るが、手元の上書きはキーごとに訳を持つため、直しが届かない。
# 「末尾のキーと英語が同じで、直した訳が 1 通りに決まる」ものだけを、ja-fixes-all.tsv / additions.tsv に書く。
# SKIP は Weblate に項目がある（別名参照ではない）のに末尾と英語が一致したもの。文脈が違う（数量の「数」と番号など）。
SKIP = {"event_linked_agent.ref_tooltip", "extent.number"}
import csv, json, re, subprocess
from pathlib import Path
QA = Path("style-review/qa-2026-10-28")
FILE = {"common": "common/locales/ja.yml", "enums": "common/locales/enums/ja.yml", "frontend": "frontend/config/locales/ja.yml",
        "help": "frontend/config/locales/help/ja.yml", "public": "public/config/locales/ja.yml"}
load = lambda f: json.loads(subprocess.run(["ruby", "-e", "require 'yaml'; require 'json'; puts JSON.dump(YAML.load_file(ARGV[0]))", str(f)],
                                           check=True, capture_output=True, text=True).stdout)
R = lambda f: list(csv.reader(open(f), delimiter="\t", quoting=csv.QUOTE_NONE))
esc = lambda x: str(x).replace("\t", " ").replace("\n", "\\n")
# 英語は空白・改行の入り方が 4.2.1 と master で違うことがあるので、つぶしてから比べる
norm = lambda x: re.sub(r"(\s|\\n)+", " ", x).strip()
def flat(d, p=()):
    for k, v in d.items():
        if isinstance(v, dict): yield from flat(v, p + (k,))
        else: yield ".".join(p + (k,)), v
new = {}
for r in R(QA / "changes-after.tsv")[1:]:
    new.setdefault((r[1].split(".")[-1], norm(r[2])), set()).add(r[4])
en = {s: {k: esc(v) for k, v in flat(load(f"upstream-4.2.1/{s}/en.yml")["en"])} for s in FILE}
fx, ad = R("ja-fixes-all.tsv"), R("additions.tsv"); H, HA = fx[0], ad[0]
ifx = {(r[0], r[1]): r for r in fx[1:]}; iad = {(r[0], r[1]): r for r in ad[1:]}
n = {"追加": 0, "修正案を更新": 0, "additions を更新": 0}; seen = set()
for side in ["frontend", "public"]:
    for k, v in flat(load(f"../archivesspace/plugins/local/{side}/locales/ja-fixes.yml")["ja"]):
        v = esc(v)
        src = next((s for s in (["frontend", "help"] if side == "frontend" else ["public"]) + ["common", "enums"] if k in en[s]), None)
        if src is None or (src, k) in seen or k in SKIP: continue
        c = new.get((k.split(".")[-1], norm(en[src][k])))
        if not c or len(c) != 1 or v in c: continue
        seen.add((src, k)); w = next(iter(c)); key = (FILE[src], k); why = "別名参照のキーに Weblate の直しを広げた"
        if key in iad: iad[key][HA.index("訳")] = w; n["additions を更新"] += 1
        elif key in ifx:
            r = ifx[key]; r[H.index("修正案")] = w; r[H.index("理由")] = (r[H.index("理由")] + " / " if r[H.index("理由")] else "") + why; n["修正案を更新"] += 1
        else:
            fx.append([FILE[src], k, en[src][k], v, w, "受け継ぎ", "中", why, ""]); n["追加"] += 1
for f, rows in [("ja-fixes-all.tsv", fx), ("additions.tsv", ad)]:
    with open(f, "w", newline="") as o: csv.writer(o, delimiter="\t", quoting=csv.QUOTE_NONE, quotechar=None, escapechar=None, lineterminator="\n").writerows(rows)
print(n)
