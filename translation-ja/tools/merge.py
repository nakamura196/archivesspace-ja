import csv,sys,collections
S=sys.argv[1]; rows=[]
seen_screen={"navbar.brand","resource._frontend.section.finding_aid","actions.duplicate_resource","actions.export","actions.merge","actions.suppress","note._frontend.preview.raw","navbar.unpublished","subject._plural","date.era","date.begin","date.end","date.expression","actions.save_prefix","resource.finding_aid_title","resource.finding_aid_subtitle","resource.finding_aid_filing_title","resource.finding_aid_date","resource.finding_aid_author","resource.finding_aid_status","resource.finding_aid_note","accession._plural","accession._singular","resource.restrictions_apply","enumerations.archival_record_level.fonds","enumerations.archival_record_level.subfonds","enumerations.date_era.ce","enumerations.date_label.creation","enumerations.date_role.begin","enumerations.resource_resource_type.papers","enumerations.extent_portion.part","note._frontend.action.apply_note_order","boolean.true","boolean.false","enumerations.date_type.single","search_results.result_identifier","actions.more"}
for x in "ABCD":
    with open(f"{S}/out/{x}.tsv") as f:
        r=csv.reader(f,delimiter="\t"); next(r)
        for row in r:
            if len(row)!=8: continue
            row=[c.strip() for c in row]
            if row[0].startswith("public") or row[1].startswith("PUBLIC:"): row[0]="public/config/locales/ja.yml"; row[1]=row[1].replace("PUBLIC:","")
            rows.append(row+["画面で確認" if row[1] in seen_screen else ""])
pri={"高":0,"中":1,"低":2}
rows.sort(key=lambda r:(pri.get(r[6],3),r[0],r[1]))
H=["ファイル","キー","英語","現在の訳","修正案","区分","重さ","理由","確認"]
with open(f"{S}/ja-fixes-all.tsv","w") as f:
    w=csv.writer(f,delimiter="\t"); w.writerow(H); w.writerows(rows)
g=collections.OrderedDict()
for r in rows:
    k=(r[2],r[3]); g.setdefault(k,{"r":r,"keys":[]})["keys"].append(f"{r[0].split('/')[0]}:{r[1]}")
with open(f"{S}/ja-fixes-grouped.tsv","w") as f:
    w=csv.writer(f,delimiter="\t"); w.writerow(["英語","現在の訳","修正案","区分","重さ","理由","確認","キー数","キー"])
    for (en,ja),v in g.items():
        r=v["r"]; w.writerow([en,ja,r[4],r[5],r[6],r[7],r[8],len(v["keys"])," ".join(v["keys"])])
c=collections.Counter((r[6],r[5]) for r in rows)
print(len(rows),"rows;",len(g),"distinct"); print(sorted(c.items()))
print("distinct by sev", collections.Counter(v["r"][6] for v in g.values()))
