"""論文の評価（E1 画面の日本語化）。訳ファイルを、プラグインなし（上流 4.2.1 のまま）とプラグインありで比べる。

画面ごとに、英語の訳ファイルにあるキーを母数として数える:
  - 日本語のキーが無いもの（画面には英語がそのまま出る）
  - 差し込み部分 %{…} の名前が英語と食い違うもの（Rails が例外を出し、画面が表示できなくなる）
  - 点検で見つけた誤り（ja-fixes-all.tsv）のうち、修正案どおりの訳になったもの
プラグインありは、上流の日本語にプラグインの ja*.yml を後から重ねたもの（ArchivesSpace が読み込む順と同じく、後のものが勝つ）。

使い方: python3 eval/eval_l10n.py   → 表を出し、eval/results/l10n.tsv に書く
"""

import csv
import json
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
UP = HERE / "translation-ja" / "upstream-4.2.1"
PLUG = HERE / "plugins"
FIXES = HERE / "translation-ja" / "ja-fixes-all.tsv"
OUT = HERE / "eval" / "results" / "l10n.tsv"
PH = re.compile(r"%\{[^}]+\}")
# 画面ごとに読み込まれる上流の訳（common と enums は両方の画面に入る）
SCREENS = {"frontend": ["common", "enums", "frontend"], "public": ["common", "enums", "public"]}
SLUG = {"common/locales/ja.yml": "common", "common/locales/enums/ja.yml": "enums",
        "frontend/config/locales/ja.yml": "frontend", "public/config/locales/ja.yml": "public"}


def load(path):
    """ArchivesSpace と同じ Ruby の読み方で読む（PyYAML は上流の yml の重複アンカーで止まる）。"""
    rb = "require 'yaml'; require 'json'; puts JSON.dump(YAML.load_file(ARGV[0]))"
    return json.loads(subprocess.run(["ruby", "-e", rb, str(path)], check=True,
                                     capture_output=True, text=True).stdout)


def flat(d, p="", out=None):
    out = {} if out is None else out
    if isinstance(d, dict):
        for k, v in d.items():
            flat(v, f"{p}.{k}" if p else str(k), out)
    elif d is not None:
        out[p] = d
    return out


def strings(lang, slugs):
    m = {}
    for s in slugs:
        m.update(flat(load(UP / s / f"{lang}.yml").get(lang, {})))
    return m


def plugin_strings(screen):
    m = {}
    for f in sorted(PLUG.glob(f"*/{screen}/locales/*.yml")):
        if f.parent.parent.parent.name not in ("local", "japanese", "ja_theme", "iiif_manifest"):
            continue
        d = load(f) or {}
        if "ja" in d:
            m.update(flat(d["ja"]))
    return m


def unquote(v):
    """値全体が " で囲まれ、中の " がすべて "" に二重化されている場合だけ、CSV の引用符を外す（build_overrides.py と同じ）。"""
    v = v.strip()
    if len(v) >= 2 and v[0] == '"' and v[-1] == '"' and '"' not in v[1:-1].replace('""', ""):
        return v[1:-1].replace('""', '"')
    return v


def is_text(v):
    return isinstance(v, str)


def measure(screen, en, ja, fixes):
    keys = [k for k, v in en.items() if is_text(v)]
    missing = [k for k in keys if not is_text(ja.get(k))]
    ph = [k for k in keys if is_text(ja.get(k)) and sorted(PH.findall(en[k])) != sorted(PH.findall(ja[k]))]
    fx = [r for r in fixes if r["key"] in en]
    applied = [r for r in fx if ja.get(r["key"]) == r["fix"]]
    high = [r for r in fx if r["weight"] == "高"]
    return {"screen": screen, "keys": len(keys), "missing": len(missing), "placeholder": len(ph),
            "fixes": len(fx), "fixes_applied": len(applied), "high": len(high),
            "high_applied": sum(1 for r in high if ja.get(r["key"]) == r["fix"])}


def main():
    with open(FIXES, encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE))
    out = []
    for screen, slugs in SCREENS.items():
        en = strings("en", slugs)
        ja = strings("ja", slugs)
        # 同じキーに common と画面固有の両方の修正があれば、画面固有のほう（後に読まれるほう）を数える
        by_key = {}
        for slug in slugs:
            for r in rows:
                if SLUG.get(r["ファイル"]) == slug and r["修正案"]:
                    by_key[r["キー"]] = {"key": r["キー"], "fix": unquote(r["修正案"]), "weight": r["重さ"]}
        fixes = list(by_key.values())
        after = dict(ja, **plugin_strings(screen))
        out.append(dict(measure(screen, en, ja, fixes), state="before"))
        out.append(dict(measure(screen, en, after, fixes), state="after"))
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["state"] + [k for k in out[0] if k != "state"], delimiter="\t",
                           lineterminator="\n")
        w.writeheader()
        w.writerows(out)
    for r in out:
        print("\t".join(str(r[k]) for k in ["state", "screen", "keys", "missing", "placeholder",
                                             "fixes", "fixes_applied", "high", "high_applied"]))


if __name__ == "__main__":
    main()
