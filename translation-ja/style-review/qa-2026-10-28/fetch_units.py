import json, sys, urllib.request, time
out = sys.argv[1]
for c in ["common","enums","frontend","frontend_help","public"]:
    url = f"https://hosted.weblate.org/api/translations/archivesspace-interfaces/{c}/ja/units/?page_size=1000"
    rows = []
    while url:
        d = json.load(urllib.request.urlopen(url)); rows += d["results"]; url = d["next"]; time.sleep(0.5)
    json.dump([{k:u[k] for k in ["context","source","target","state"]} for u in rows], open(f"{out}/{c}.json","w"), ensure_ascii=False)
    print(c, len(rows))
