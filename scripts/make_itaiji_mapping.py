"""旧字体の対応表（plugins/japanese/solr/itaiji-ja.tsv）から、文字バイグラムの設定で使う
MappingCharFilter 用の itaiji-mapping.txt を作る。

使い方: python3 scripts/make_itaiji_mapping.py
"""

from pathlib import Path

SOLR = Path(__file__).resolve().parent.parent / "plugins" / "japanese" / "solr"

lines = ["# 旧字・異体字 → 今の字（itaiji-ja.tsv から scripts/make_itaiji_mapping.py が作る。MappingCharFilter 用）"]
for line in (SOLR / "itaiji-ja.tsv").read_text(encoding="utf-8").splitlines():
    if line.startswith("#") or not line.strip():
        continue
    old, new = line.split("\t")
    lines.append(f'"{old}" => "{new}"')
(SOLR / "itaiji-mapping.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"{len(lines) - 1} 組 → {SOLR / 'itaiji-mapping.txt'}")
