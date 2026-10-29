# 使い方: python3 apply.py <判定 TSV ...>
# 判定（番号 部品 キー 判定 最終訳 理由）の「直す」を ja-fixes-all.tsv / additions.tsv に書き戻す。
# そのあと用語の機械置換（統制値リスト・分類項目・最上位コンテナ）を全訳にかける。置き場は translation-ja/ から見たパス。
import csv, re, sys
FILE = {"common":"common/locales/ja.yml","enums":"common/locales/enums/ja.yml","frontend":"frontend/config/locales/ja.yml",
        "frontend_help":"frontend/config/locales/help/ja.yml","public":"public/config/locales/ja.yml"}
T = "../../"
R = lambda f: list(csv.reader(open(f), delimiter="\t", quoting=csv.QUOTE_NONE))
fx, ad = R(T+"ja-fixes-all.tsv"), R(T+"additions.tsv")
H, HA = fx[0], ad[0]
ifx = {(r[0],r[1]):r for r in fx[1:]}; iad = {(r[0],r[1]):r for r in ad[1:]}
import os; allv = {(r[0],r[1]):r for r in R(os.environ.get("BASE", "all.tsv"))}  # 2 回目以降は BASE=all-after.tsv（直した後の訳を土台にする）
n = {"追加":0,"修正案を更新":0,"additions を更新":0}
def put(c, k, v, why, kind):
    f = FILE[c]; key = (f,k)
    if key in iad: iad[key][HA.index("訳")] = v; n["additions を更新"] += 1
    elif key in ifx:
        r = ifx[key]; r[H.index("修正案")] = v
        r[H.index("理由")] = (r[H.index("理由")] + " / " if r[H.index("理由")] else "") + why; n["修正案を更新"] += 1
    else:
        a = allv[(c,k)]; r = [f,k,a[2],a[3],v,kind,"中",why,""]
        fx.append(r); ifx[key] = r; n["追加"] += 1
    allv[(c,k)] = allv[(c,k)][:3] + [v]
for d in sys.argv[1:]:
    for r in R(d)[1:]:
        if len(r) >= 6 and r[3] == "直す" and r[4].strip(): put(r[1], r[2], r[4].strip(), "3系統点検: "+r[5], "3系統点検")
SUB = [(r"管理された値リスト|制御された値リスト|コントロール対象値リスト|制御値リスト|管理値リスト", "統制値リスト"),
       (r"制御された値|制御値(?=\d)", "統制値"), (r"分類用語", "分類項目"), (r"トップ・?コンテナ", "最上位コンテナ")]
m = 0
for (c,k),a in list(allv.items()):
    v = a[3]; w = v
    for p,s in SUB: w = re.sub(p, s, w)
    if w != v: put(c, k, w, "用語統一（統制値リスト・分類項目・最上位コンテナ）", "用語統一"); m += 1
for f,rows in [(T+"ja-fixes-all.tsv",fx),(T+"additions.tsv",ad)]:
    with open(f,"w",newline="") as o: csv.writer(o, delimiter="\t", quoting=csv.QUOTE_NONE, quotechar=None, escapechar=None, lineterminator="\n").writerows(rows)
print(n, "用語置換", m)
