#!/usr/bin/env python3
"""Copia del sito generato con collegamenti RELATIVI, per un'anteprima privata
(pagina claude.ai o cartella aperta da un altro computer). Non tocca il sito vero.

Uso: python3 _sorgenti/anteprima.py CARTELLA_USCITA [--leggera]
- copia solo le pagine generate e i file che usano (niente resti del vecchio sito);
- i link "/camere/" diventano "../camere/index.html" (secondo la profondita' della pagina);
- asset e foto "/img/..." diventano relativi;
- in testa a ogni pagina una striscia "ANTEPRIMA" e robots noindex;
- --leggera: nelle foto tiene solo le misure 800 e 1600 (meno file da caricare).
"""
import os, re, shutil, sys

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.abspath(sys.argv[1])
LEGGERA = '--leggera' in sys.argv
VECCHIO = {'_sorgenti', '.git', 'wp-content', 'wp-includes', 's'}

def rel(target, depth):
    pre = '../' * depth
    path, _, frag = target.partition('#')
    path, _, query = path.partition('?')
    if path.endswith('/'):
        path += 'index.html'
    path = path.lstrip('/')
    out = pre + (path or 'index.html')
    if query and not path.endswith('.html'):
        out += '?' + query
    return out + ('#' + frag if frag else '')

def locale(u):
    """percorso del file nel repo per un indirizzo /..., o None"""
    if not u.startswith('/') or u.startswith('//'):
        return None
    p = u.split('#')[0].split('?')[0].lstrip('/')
    if p == '' or p.endswith('/'):
        p += 'index.html'
    return p

usati = set()

def fix_html(src, depth):
    def attr(m):
        p = locale(m.group(2))
        if p: usati.add(p)
        return f'{m.group(1)}="{rel(m.group(2), depth)}"'
    src = re.sub(r'\b(href|src)="(/(?!/)[^"]*)"', attr, src)
    def srcset(m):
        parts = []
        for p in m.group(2).split(','):
            p = p.strip(); u, _, w = p.partition(' ')
            if LEGGERA and re.search(r'-(480|1200|2000)\.webp$', u):
                continue
            q = locale(u)
            if q: usati.add(q)
            parts.append((rel(u, depth) if q else u) + (' ' + w if w else ''))
        return f'{m.group(1)}="{", ".join(parts)}"'
    src = re.sub(r'\b(srcset|imagesrcset)="([^"]*)"', srcset, src)
    banner = ('<div style="background:#8C3F1F;color:#fff;text-align:center;font:600 13px system-ui;'
              'padding:6px">ANTEPRIMA del sito nuovo, non ancora pubblicato</div>')
    src = src.replace('<body>', '<body>' + banner, 1)
    src = src.replace('<meta charset="utf-8">', '<meta charset="utf-8"><meta name="robots" content="noindex">', 1)
    return src

pagine = []
for root, dirs, files in os.walk(R):
    dirs[:] = sorted(d for d in dirs if d not in VECCHIO and not d.startswith('.'))
    for f in files:
        if f.endswith('.html'):
            pagine.append(os.path.relpath(os.path.join(root, f), R))
for relp in sorted(pagine):
    dst = os.path.join(OUT, relp)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    depth = relp.count(os.sep)
    open(dst, 'w', encoding='utf-8').write(fix_html(open(os.path.join(R, relp), encoding='utf-8').read(), depth))
# file usati dalle pagine, piu' i caratteri richiamati dal foglio di stile
for css in [p for p in usati if p.endswith('.css')]:
    for u in re.findall(r'url\(([^)]+)\)', open(os.path.join(R, css), encoding='utf-8').read()):
        u = u.strip('\'"')
        if not u.startswith(('data:', 'http', '/')):
            usati.add(os.path.normpath(os.path.join(os.path.dirname(css), u)))
mancano = []
for p in sorted(usati):
    if p.endswith('.html'):
        continue
    s = os.path.join(R, p)
    if not os.path.isfile(s):
        mancano.append(p); continue
    os.makedirs(os.path.dirname(os.path.join(OUT, p)), exist_ok=True)
    shutil.copy2(s, os.path.join(OUT, p))
n_file = sum(len(f) for _, _, f in os.walk(OUT))
print(f'{len(pagine)} pagine, {n_file} file in tutto, in {OUT}')
if mancano:
    print('ATTENZIONE, file richiamati ma assenti:', mancano)
