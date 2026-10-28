"""修正一覧から、ArchivesSpace のプラグインに置く上書き用の ja-fixes.yml を作る。

使い方: python3 tools/build_overrides.py <plugins/local のパス>
- ja-fixes-all.tsv（重さ 高・中・低すべて）と additions.tsv（訳の無かったキー・画面調査で見つけたキー）を使う
- help（スタッフ画面のヘルプの文言。上流は frontend/config/locales/help/ja.yml）はスタッフ画面だけに入れる
- common と enums の分は、スタッフ画面（frontend）と閲覧者向け画面（public）の両方に入れる
- プラグインの ja.yml（手で書いた分）にあるキーは、そちらを優先して入れない
- %{…} が英語と食い違う行は入れずに報告する
"""

import csv
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent.parent
UP = HERE / "upstream-4.2.1"
SLUG = {"common/locales/ja.yml": "common", "common/locales/enums/ja.yml": "enums",
        "frontend/config/locales/ja.yml": "frontend", "frontend/config/locales/help/ja.yml": "help",
        "public/config/locales/ja.yml": "public"}
TARGET = {"common": ["frontend", "public"], "enums": ["frontend", "public"],
          "frontend": ["frontend"], "help": ["frontend"], "public": ["public"]}
PH = re.compile(r"%\{[^}]+\}")


def load(path):
    """ArchivesSpace と同じ Ruby の読み方で読む（PyYAML は上流の yml の重複アンカーで止まる）。"""
    rb = "require 'yaml'; require 'json'; puts JSON.dump(YAML.load_file(ARGV[0]))"
    return json.loads(subprocess.run(["ruby", "-e", rb, str(path)], check=True,
                                     capture_output=True, text=True).stdout)


def paths(d, p=(), out=None):
    """入れ子の yml を「ドット区切りのキー → 実際の経路」にする（キーにドットを含むものがあるため）。"""
    out = {} if out is None else out
    if isinstance(d, dict):
        for k, v in d.items():
            paths(v, p + (k,), out)
    else:
        out[".".join(map(str, p[1:]))] = (list(p[1:]), d)
    return out


def unquote(v):
    """値全体が " で囲まれ、中の " がすべて "" に二重化されている場合だけ、CSV の引用符を外す（それ以外は文字通りに残す）。"""
    if len(v) >= 2 and v[0] == '"' and v[-1] == '"' and '"' not in v[1:-1].replace('""', ""):
        return v[1:-1].replace('""', '"')
    return v


def rows():
    """(ファイル, キー, 英語, 訳) を、後のものが勝つ順に返す。"""
    for name, col in (("ja-fixes-all.tsv", "修正案"), ("additions.tsv", "訳")):
        f = HERE / name
        if not f.exists():
            print("なし:", name)
            continue
        for r in csv.DictReader(open(f, encoding="utf-8"), delimiter="\t", quoting=csv.QUOTE_NONE):
            # TSV では改行を \n の 2 文字で書いている。上流の yml に文字どおりの \n は無いので、改行に戻す
            val = unquote((r.get(col) or "").strip()).replace("\\n", "\n")
            if val:
                yield r["ファイル"], r["キー"], r.get("英語", ""), val


def main(plugins):
    pmap, enval = {}, {}
    for slug in set(SLUG.values()):
        m = paths(load(UP / slug / "ja.yml"))
        en_m = paths(load(UP / slug / "en.yml"))
        m.update(en_m)
        pmap[slug] = {k: v[0] for k, v in m.items()}
        # %{…} の照合は上流の英語で（TSV の英語は途中で切れていることがある）。英語に無いキーは今の日本語で
        enval[slug] = {k: str(v[1]) for k, v in m.items()}
    hand = {t: paths(load(Path(plugins) / t / "locales" / "ja.yml"))
            for t in ("frontend", "public")}
    trees = {"frontend": {}, "public": {}}
    count = {"frontend": 0, "public": 0}
    bad = []
    for file, key, en, ja in rows():
        slug = SLUG.get(file)
        if not slug:
            bad.append(f"ファイル不明 {file} {key}")
            continue
        # 上流 4.2.1 の英語で照合する。上流に無いキー（4.2.1 では使われない）は TSV の英語が途中で切れていることがあるので照合しない
        en = enval[slug].get(key, "")
        if en and set(PH.findall(en)) != set(PH.findall(ja)):
            bad.append(f"%{{}}の食い違い {key}: {ja}")
            continue
        path = pmap[slug].get(key) or key.split(".")  # en.yml に無いキー（データベース側の選択肢など）
        for t in TARGET[slug]:
            if key in hand[t]:
                continue
            node = trees[t]
            for k in path[:-1]:
                node = node.setdefault(k, {})
                if not isinstance(node, dict):
                    bad.append(f"経路の衝突 {key}")
                    break
            else:
                if path[-1] not in node:
                    count[t] += 1
                node[path[-1]] = ja
    for t, tree in trees.items():
        out = Path(plugins) / t / "locales" / "ja-fixes.yml"
        head = ("# 同梱の日本語訳の誤りと訳の無い項目を上書きする。\n"
                "# translation-ja/tools/build_overrides.py が ja-fixes-all.tsv と additions.tsv から作る。手で直さない。\n")
        out.write_text(head + yaml.safe_dump({"ja": tree}, allow_unicode=True, width=10**6, sort_keys=True),
                       encoding="utf-8")
        print(t, count[t], "keys ->", out)
    for b in bad:
        print("入れなかった:", b)


if __name__ == "__main__":
    main(sys.argv[1])
