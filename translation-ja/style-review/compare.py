"""手本の OSS の日本語訳と、ArchivesSpace の訳（上流 + ja-fixes-all + additions）を突き合わせる。

使い方: python3 -I compare.py <ref のフォルダ> <translation-ja のフォルダ> <出力フォルダ>
訳ファイルには書き込まない。出力は TSV のみ。
"""
import sys, re, csv, json, unicodedata, subprocess
from collections import Counter, defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET

REF, TJ, OUT = map(Path, sys.argv[1:4])
OUT.mkdir(parents=True, exist_ok=True)

# ---------- 手本の読み込み ----------
def unq(s):
    s = s.strip()
    if s.startswith('"') and s.endswith('"'):
        s = s[1:-1]
    return s.replace('\\"', '"').replace('\\n', '\n').replace('\\t', '\t').replace('\\\\', '\\')

def read_po(path):
    out = []
    cur, field, fuzzy = {}, None, False
    def flush():
        nonlocal cur, fuzzy
        if 'msgid' in cur and cur['msgid'] and not fuzzy:
            strs = [v for k, v in cur.items() if k.startswith('msgstr') and v]
            if strs:
                out.append((cur['msgid'], strs[0]))
                if cur.get('msgid_plural'):
                    out.append((cur['msgid_plural'], strs[-1]))
        cur, fuzzy = {}, False
    for line in open(path, encoding='utf-8'):
        line = line.rstrip('\n')
        if line.startswith('#,') and 'fuzzy' in line:
            if cur.get('msgstr') is not None or any(k.startswith('msgstr') for k in cur):
                flush()
            fuzzy = True; continue
        if line.startswith('#') or not line.strip():
            if any(k.startswith('msgstr') for k in cur):
                flush()
            continue
        m = re.match(r'(msgctxt|msgid_plural|msgid|msgstr(?:\[\d+\])?)\s+(".*")$', line)
        if m:
            if m.group(1) in ('msgctxt', 'msgid') and any(k.startswith('msgstr') for k in cur):
                f = fuzzy; flush(); fuzzy = f
            field = m.group(1); cur[field] = unq(m.group(2))
        elif line.startswith('"') and field:
            cur[field] += unq(line)
    flush()
    return out

def read_xliff(path):
    out = []
    for tu in ET.parse(path).getroot().iter():
        if tu.tag.endswith('trans-unit'):
            src = tgt = None
            for c in tu:
                if c.tag.endswith('source'): src = ''.join(c.itertext())
                if c.tag.endswith('target'): tgt = ''.join(c.itertext())
            if src and tgt:
                out.append((src, tgt))
    return out

SOURCES = {
    'Omeka S': [read_po(REF / 'omeka/ja.po')],
    'WordPress': [read_po(REF / 'wp/core.po'), read_po(REF / 'wp/admin.po')],
    'Drupal': [read_po(REF / 'drupal/drupal.ja.po')],
    'AtoM': [read_xliff(REF / 'atom/messages.xml')],
    'Archivematica': [read_po(REF / 'am/django.po'), read_po(REF / 'am/djangojs.po')],
}
NAMES = list(SOURCES)

def norm_en(s):
    s = re.sub(r'<[^>]+>', '', s)
    s = re.sub(r'%\{[^}]*\}|%\d*\$?[sd]|\{[^}]*\}|[@%!:]\w+', '{}', s)
    s = s.replace('&amp;', '&').strip()
    s = re.sub(r'(\.\.\.|…|:|：)\s*$', '', s).strip()
    return re.sub(r'\s+', ' ', s).lower()

def norm_ja(s):
    s = unicodedata.normalize('NFKC', str(s))
    s = re.sub(r'<[^>]+>', '', s)
    s = re.sub(r'\s+', '', s)
    return re.sub(r'(\.\.\.|…|:)$', '', s)

ref = {n: defaultdict(Counter) for n in NAMES}
ref_total = {}
for n, lists in SOURCES.items():
    k = 0
    for lst in lists:
        for en, ja in lst:
            ref[n][norm_en(en)][ja.strip()] += 1; k += 1
    ref_total[n] = k

def ref_cell(n, key):
    c = ref[n].get(key)
    if not c: return ''
    return ' / '.join(f'{t}' + (f'({k})' if k > 1 else '') for t, k in c.most_common(3))

# ---------- こちらの訳 ----------
DIRMAP = {'common/locales/ja.yml': 'common', 'common/locales/enums/ja.yml': 'enums',
          'frontend/config/locales/ja.yml': 'frontend', 'public/config/locales/ja.yml': 'public'}
FLAT = r'''require "yaml";require "json"
def flat(d,p="",o={}) ; if d.is_a?(Hash) then d.each{|k,v| flat(v, p.empty? ? k.to_s : "#{p}.#{k}", o)} else o[p]=d.to_s end; o end
puts JSON.dump(flat(YAML.load_file(ARGV[0])))'''
eff = {}  # (file, key) -> dict(en, ja, src)
for f, d in DIRMAP.items():
    en = json.loads(subprocess.check_output(['ruby', '-e', FLAT, str(TJ / 'upstream-4.2.1' / d / 'en.yml')]))
    ja = json.loads(subprocess.check_output(['ruby', '-e', FLAT, str(TJ / 'upstream-4.2.1' / d / 'ja.yml')]))
    for k, v in en.items():
        k2 = re.sub(r'^en\.', '', k)
        jv = ja.get('ja.' + k2)
        eff[(f, k2)] = {'en': v, 'ja': jv or '', 'src': '上流' if jv else '上流に無し'}

def read_tsv(p):
    with open(p, encoding='utf-8') as fh:
        return list(csv.DictReader(fh, delimiter='\t', quoting=csv.QUOTE_NONE))

for r in read_tsv(TJ / 'ja-fixes-all.tsv'):
    if r['修正案']:
        eff[(r['ファイル'], r['キー'])] = {'en': r['英語'], 'ja': r['修正案'], 'src': 'ja-fixes-all', 'cur': r['現在の訳'], 'kind': r['区分']}
for r in read_tsv(TJ / 'additions.tsv'):
    if r['訳']:
        eff[(r['ファイル'], r['キー'])] = {'en': r['英語'], 'ja': r['訳'], 'src': 'additions', 'cur': r['現在の訳'], 'kind': r['出典']}

# ---------- 1. 英語が同じ文字列の突き合わせ ----------
HEAD = ['判定', '手本の数', '出所', 'ファイル', 'キー', '英語', 'こちらの訳', '上流の訳'] + NAMES
rows = []
stat = Counter()
for (f, k), v in eff.items():
    if not v['ja'] or not isinstance(v['en'], str) or not v['en'].strip():
        continue
    key = norm_en(v['en'])
    if len(key) < 2: continue
    hits = [n for n in NAMES if key in ref[n]]
    if not hits: continue
    ours = norm_ja(v['ja'])
    refset = {norm_ja(t) for n in hits for t in ref[n][key]}
    top = {n: norm_ja(ref[n][key].most_common(1)[0][0]) for n in hits}
    if ours in set(top.values()):
        verdict = '一致'
    elif ours in refset:
        verdict = '一部一致'
    else:
        verdict = '食い違い'
    if verdict != '一致' and len(set(top.values())) > 1:
        verdict += '（手本も割れる）'
    stat[(v['src'], verdict.split('（')[0])] += 1
    rows.append([verdict, len(hits), v['src'], f, k, v['en'], v['ja'], v.get('cur', v['ja'] if v['src'] == '上流' else '')]
                + [ref_cell(n, key) for n in NAMES])

order = {'ja-fixes-all': 0, 'additions': 1, '上流': 2}
rows.sort(key=lambda r: (order.get(r[2], 3), not r[0].startswith('食い違い'), -r[1], r[5].lower()))
with open(OUT / 'match-by-string.tsv', 'w', encoding='utf-8') as fh:
    w = csv.writer(fh, delimiter='\t', lineterminator='\n'); w.writerow(HEAD); w.writerows(rows)

# ---------- 2. 用語の対照表 ----------
TERMS = [l.strip() for l in open(Path(__file__).with_name('terms.txt'), encoding='utf-8') if l.strip() and not l.startswith('#')]
def variants(t):
    t = t.lower(); vs = {t}
    vs.add(t[:-1] + 'ies' if t.endswith('y') and not t.endswith('ey') else (t + 'es' if t.endswith(('s', 'x', 'ch')) else t + 's'))
    return vs
ours_by_en = defaultdict(Counter)
ours_by_en_tsv = defaultdict(Counter)
for v in eff.values():
    if v['ja'] and isinstance(v['en'], str):
        ours_by_en[norm_en(v['en'])][v['ja']] += 1
        if v['src'] in ('ja-fixes-all', 'additions'):
            ours_by_en_tsv[norm_en(v['en'])][v['ja']] += 1
with open(OUT / 'terms.tsv', 'w', encoding='utf-8') as fh:
    w = csv.writer(fh, delimiter='\t', lineterminator='\n')
    w.writerow(['用語', 'こちら（上流＋TSV 反映後）', 'うち TSV の行'] + NAMES)
    for t in TERMS:
        vs = variants(t)
        def cell(cnt_by):
            c = Counter()
            for x in vs: c.update(cnt_by.get(x, {}))
            return ' / '.join(f'{a}' + (f'({b})' if b > 1 else '') for a, b in c.most_common(4))
        w.writerow([t, cell(ours_by_en), cell(ours_by_en_tsv)] + [cell(ref[n]) for n in NAMES])

print('手本の件数:', ref_total)
for (s, vd), c in sorted(stat.items()):
    print(s, vd, c)

with open(OUT / 'effective.tsv', 'w', encoding='utf-8') as fh:
    w = csv.writer(fh, delimiter='\t', lineterminator='\n'); w.writerow(['出所', 'ファイル', 'キー', '英語', '訳'])
    for (f, k), v in sorted(eff.items()):
        w.writerow([v['src'], f, k, str(v['en']).replace('\n', ' '), str(v['ja']).replace('\n', ' ')])
