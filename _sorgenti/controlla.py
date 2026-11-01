#!/usr/bin/env python3
"""Controlli automatici sul sito generato (da lanciare dopo genera.py).

Verifica per ogni pagina: titolo e descrizione (lunghezze), un solo h1, canonical,
hreflang per tutte le lingue, link interni che portano a file esistenti, immagini
con testo alternativo e dimensioni, dati strutturati leggibili, nessun testo segnaposto
dimenticato (tranne il REA, finche' Luca non lo da').
"""
import json, os, re, sys
from html.parser import HTMLParser

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
C = json.load(open(os.path.join(R, '_sorgenti', 'config.json'), encoding='utf-8'))

class P(HTMLParser):
    def __init__(self):
        super().__init__(); self.tags = []; self.h1 = 0; self.title = ''; self._t = False; self.ld = []; self._ld = False; self.text = []; self.in_a = 0
    def handle_starttag(self, tag, a):
        a = dict(a)
        if tag == 'a': self.in_a += 1
        if tag == 'img': a['_in_a'] = self.in_a > 0
        self.tags.append((tag, a))
        if tag == 'h1': self.h1 += 1
        if tag == 'title': self._t = True
        if tag == 'script' and a.get('type') == 'application/ld+json': self._ld = True; self.ld.append('')
    def handle_endtag(self, tag):
        if tag == 'title': self._t = False
        if tag == 'a': self.in_a = max(0, self.in_a - 1)
        if tag == 'script': self._ld = False
    def handle_data(self, d):
        if self._t: self.title += d
        if self._ld: self.ld[-1] += d
        self.text.append(d)

def exists(href):
    path = href.split('#')[0].split('?')[0]
    if not path.startswith('/'):
        return True
    f = os.path.join(R, path.lstrip('/'))
    if path.endswith('/'):
        f = os.path.join(f, 'index.html')
    return os.path.exists(f)

errs, warns = [], []
pages = []
for page in C['pagine']:
    for lang in C['lingue']:
        pages.append((page, lang, C['slug'][page][lang] + 'index.html'))
pages.append(('404', 'it', '404.html'))
for page, lang, rel in pages:
    f = os.path.join(R, rel)
    if not os.path.exists(f):
        errs.append(f'{rel}: manca'); continue
    src = open(f, encoding='utf-8').read()
    p = P(); p.feed(src)
    tag = f'{rel}'
    if not (10 <= len(p.title) <= 65): warns.append(f'{tag}: titolo di {len(p.title)} caratteri: {p.title!r}')
    desc = [a.get('content', '') for t, a in p.tags if t == 'meta' and a.get('name') == 'description']
    if not desc or not (50 <= len(desc[0]) <= 160): warns.append(f'{tag}: descrizione di {len(desc[0]) if desc else 0} caratteri')
    if p.h1 != 1: errs.append(f'{tag}: {p.h1} titoli h1')
    if page != '404':
        if not any(t == 'link' and a.get('rel') == 'canonical' for t, a in p.tags): errs.append(f'{tag}: manca canonical')
        hl = {a.get('hreflang') for t, a in p.tags if t == 'link' and a.get('rel') == 'alternate'}
        for l in C['lingue'] + ['x-default']:
            if l not in hl: errs.append(f'{tag}: manca hreflang {l}')
    for t, a in p.tags:
        for k in ('href', 'src'):
            v = a.get(k)
            if v and v.startswith('/') and not exists(v):
                errs.append(f'{tag}: link rotto {v}')
        if t == 'img':
            if 'alt' not in a: errs.append(f'{tag}: immagine senza alt {a.get("src")}')
            elif not a['alt'] and 'logo' not in (a.get('src') or '') and not a.get('_in_a'): warns.append(f'{tag}: alt vuoto {a.get("src")}')
            if not a.get('width') or not a.get('height'): warns.append(f'{tag}: immagine senza dimensioni {a.get("src")}')
            for part in (a.get('srcset') or '').split(','):
                u = part.strip().split(' ')[0]
                if u.startswith('/') and not exists(u): errs.append(f'{tag}: srcset rotto {u}')
        if t == 'source':
            for part in (a.get('srcset') or '').split(','):
                u = part.strip().split(' ')[0]
                if u.startswith('/') and not exists(u): errs.append(f'{tag}: srcset rotto {u}')
    for j in p.ld:
        try: json.loads(j)
        except Exception as ex: errs.append(f'{tag}: JSON-LD non valido ({ex})')
    text = ' '.join(p.text)
    for bad in ('[prezzo]', '[m²]', 'lorem', 'TODO', 'undefined', 'None'):
        if bad.lower() in text.lower(): errs.append(f'{tag}: testo segnaposto "{bad}"')
    if '[REA da inserire]' in text: warns.append(f'{tag}: REA ancora da inserire')
    if lang in ('en', 'pl') and re.search(r'\b(camera|colazione|prenota)\b', text, re.I):
        warns.append(f'{tag}: parole italiane in una pagina {lang}?')

print(f'pagine controllate: {len(pages)}')
print(f'ERRORI: {len(errs)}'); [print('  -', x) for x in errs]
print(f'avvisi: {len(warns)}'); [print('  -', x) for x in sorted(set(warns))[:80]]
sys.exit(1 if errs else 0)
