import csv, re, sys, collections
rows = list(csv.reader(open(sys.argv[1]), delimiter="\t", quoting=csv.QUOTE_NONE))
chg = {(r[0],r[1]) for r in csv.reader(open(sys.argv[2]), delimiter="\t", quoting=csv.QUOTE_NONE)}
iss = collections.defaultdict(list)
tag = lambda s: sorted(re.findall(r"</?\s*([a-zA-Z0-9]+)", s))
old = {"ロケーション":r"ロケーション","ノート":r"ノート","タイプ":r"タイプ","デフォルト":r"デフォルト","サーバ(ー無し)":r"サーバ(?!ー)","分類用語":r"分類用語","ディジタル":r"ディジタル","ファインディングエイド":r"ファインディング・?エイド","アクセッション":r"アクセッション","リポジトリ":r"リポジトリ","アセスメント":r"アセスメント"}
for c,k,en,ja in rows:
    tagc = "変わる" if (c,k) in chg else "そのまま"
    if sorted(re.findall(r"%\{[^}]+\}", en)) != sorted(re.findall(r"%\{[^}]+\}", ja)): iss["差し込み記号 %{}"].append((tagc,c,k,ja))
    if tag(en) != tag(ja): iss["HTMLタグ"].append((tagc,c,k,ja))
    if re.search(r"[A-Za-z]{3}", en) and ja == en and not re.fullmatch(r"[A-Z0-9 ./_-]+|https?://\S+", en): iss["英語のまま"].append((tagc,c,k,ja))
    if re.search(r"[ぁ-んァ-ン一-龥]", ja) is None and re.search(r"[A-Za-z]{4}", ja) and ja != en: iss["日本語が無い"].append((tagc,c,k,ja))
    for n,p in old.items():
        if re.search(p, ja): iss["旧語/要検討:"+n].append((tagc,c,k,ja))
    if "  " in ja.replace("\\n","") and "  " not in en: iss["空白が2つ"].append((tagc,c,k,ja))
    if re.search(r"[ぁ-んァ-ン一-龥][:;](?!//)", ja): iss["半角コロン"].append((tagc,c,k,ja))
    if re.search(r"[!?](?=[ぁ-んァ-ン一-龥])|[ぁ-んァ-ン一-龥][!?]", ja): iss["半角!?"].append((tagc,c,k,ja))
    if re.search(r"。。|、、|\?\?", ja): iss["重複記号"].append((tagc,c,k,ja))
for n,v in sorted(iss.items()):
    cnt = collections.Counter(x[0] for x in v)
    print(f"## {n}: 計 {len(v)}（変わる {cnt['変わる']} / そのまま {cnt['そのまま']}）")
    for x in [y for y in v if y[0]=="変わる"][:6]: print("   ", x[1], x[2], "|", x[3][:90])
