# 使い方: python3 style-review/qa-2026-10-28/oldterms.py [--apply]（translation-ja/ で実行）
# 画面に出る訳（上流 4.2.1 の ja.yml に ja-fixes-all.tsv / additions.tsv を重ねたもの）から、Weblate で直した古い語を探す。
# 別名参照のキーや、4.2.1 と master で英語が少し違うキーは、Weblate の直しが届かないため。--apply で ja-fixes-all.tsv に足す。
import csv, json, re, subprocess, sys
FILE = {"common": "common/locales/ja.yml", "enums": "common/locales/enums/ja.yml", "frontend": "frontend/config/locales/ja.yml",
        "help": "frontend/config/locales/help/ja.yml", "public": "public/config/locales/ja.yml"}
SUB = [(r"<li>死んだ</li>", "<li>日付なし</li>"),
       (r"管理された値リスト|制御された値リスト|コントロール対象値リスト|制御値リスト|管理値リスト", "統制値リスト"),
       (r"制御された値|制御値(?=\d)", "統制値"), (r"分類用語", "分類項目"), (r"トップ・?コンテナ", "最上位コンテナ"),
       (r"コーポレートエンティティ", "団体")]
load = lambda f: json.loads(subprocess.run(["ruby", "-e", "require 'yaml'; require 'json'; puts JSON.dump(YAML.load_file(ARGV[0]))", str(f)],
                                           check=True, capture_output=True, text=True).stdout)
R = lambda f: list(csv.reader(open(f), delimiter="\t", quoting=csv.QUOTE_NONE))
esc = lambda x: str(x).replace("\t", " ").replace("\n", "\\n")
def flat(d, p=()):
    for k, v in d.items():
        if isinstance(v, dict): yield from flat(v, p + (k,))
        else: yield ".".join(p + (k,)), v
fx, ad = R("ja-fixes-all.tsv"), R("additions.tsv"); H, HA = fx[0], ad[0]
ifx = {(r[0], r[1]): r for r in fx[1:]}; iad = {(r[0], r[1]): r for r in ad[1:]}
hits = []
for s, f in FILE.items():
    en = {k: esc(v) for k, v in flat(load(f"upstream-4.2.1/{s}/en.yml")["en"])}
    ja = {k: esc(v) for k, v in flat(load(f"upstream-4.2.1/{s}/ja.yml")["ja"])}
    for k in en:
        key = (f, k)
        if key in iad: v, where = iad[key][HA.index("訳")], "additions"
        elif key in ifx: v, where = ifx[key][H.index("修正案")], "fixes"
        elif k in ja: v, where = ja[k], "upstream"
        else: continue
        w = v
        for p, t in SUB: w = re.sub(p, t, w)
        if w != v: hits.append((key, en[k], v, w, where))
for key, e, v, w, where in hits: print(where, key[0].split("/")[0], key[1], "|", re.sub(r".*?((?:死んだ|管理された値リスト|制御.{0,4}値|分類用語|トップ.?コンテナ|コーポレートエンティティ).{0,10}).*", r"\1", v)[:30])
print("件数", len(hits), file=sys.stderr)
if "--apply" in sys.argv:
    why = "古い語の残り（別名参照・英語の版違いで Weblate の直しが届かないキー）"
    for key, e, v, w, where in hits:
        if where == "additions": iad[key][HA.index("訳")] = w
        elif where == "fixes":
            r = ifx[key]; r[H.index("修正案")] = w; r[H.index("理由")] = (r[H.index("理由")] + " / " if r[H.index("理由")] else "") + why
        else: fx.append([key[0], key[1], e, v, w, "用語統一", "中", why, ""])
    for f, rows in [("ja-fixes-all.tsv", fx), ("additions.tsv", ad)]:
        with open(f, "w", newline="") as o: csv.writer(o, delimiter="\t", quoting=csv.QUOTE_NONE, quotechar=None, escapechar=None, lineterminator="\n").writerows(rows)
