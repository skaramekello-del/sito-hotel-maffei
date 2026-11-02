#!/usr/bin/env python3
"""Genera il sito statico dell'Hotel Garnì Maffei (IT, EN, PL).

Uso:  python3 _sorgenti/genera.py            (dalla cartella del repo)
Legge _sorgenti/config.json, _sorgenti/testi.json, _sorgenti/foto.json
e scrive le pagine nella radice del repo (pubblicata da GitHub Pages).
Le foto web (img/foto/) si rifanno solo se mancano o se il master e' piu' nuovo.
"""
import hashlib, html, json, os, re, sys
from datetime import date

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = os.path.join(R, '_sorgenti')
C = json.load(open(os.path.join(S, 'config.json'), encoding='utf-8'))
T = json.load(open(os.path.join(S, 'testi.json'), encoding='utf-8'))
F = {int(k): v for k, v in json.load(open(os.path.join(S, 'foto.json'), encoding='utf-8')).items()}
DOM = C['dominio']
LANGS = C['lingue']
OGGI = date.today().isoformat()

def e(s):
    return html.escape(s or '', quote=True)

def url(page, lang):
    return '/' + C['slug'][page][lang]

def lurl(page, lang):
    return url(page, lang) if lang in C['slug'][page] else url('home', lang)

def absu(page, lang):
    return DOM + url(page, lang)

def page_t(page, lang):
    return T['pagine'][page][lang]

def ui(lang, key):
    return T['ui'][lang].get(key, '') or ''

def conta(lang, n, key='reviews_count'):
    """Numero + parola con il plurale giusto (il polacco ha tre forme)."""
    if lang == 'pl' and key == 'reviews_count':
        if n == 1:
            w = 'opinia'
        elif n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
            w = 'opinie'
        else:
            w = 'opinii'
        return f'{n} {w}'
    return f'{n} {ui(lang, key)}'

def sec(t, sid):
    for s in t.get('sections', []):
        if s.get('id') == sid:
            return s
    return {'id': sid, 'kicker': '', 'title': '', 'paragraphs': [], 'items': [], 'cta': ''}

def linkify(h):
    """Rende cliccabili email, telefoni (il cellulare scritto dopo "WhatsApp" apre WhatsApp) e i due siti citati nel testo (gia' passato da e())."""
    c = C['contatti']
    cell = re.escape(e(c['cellulare']))
    h = re.sub(r'(WhatsApp[^<]{0,40}?)(' + cell + ')', lambda m: f'{m.group(1)}<a class="nowrap" href="https://wa.me/{c["whatsapp"]}" rel="noopener">{m.group(2)}</a>', h)
    h = re.sub(r'(?<!>)' + cell, f'<a href="tel:{c["cellulare_tel"]}">{e(c["cellulare"])}</a>', h)
    for a, b in ((e(c['email']), f'<a href="mailto:{c["email"]}">{e(c["email"])}</a>'),
                 (e(c['fisso']), f'<a href="tel:{c["fisso_tel"]}">{e(c["fisso"])}</a>'),
                 ('www.ski.it', '<a href="https://www.ski.it/" rel="noopener">www.ski.it</a>'),
                 ('www.garanteprivacy.it', '<a href="https://www.garanteprivacy.it/" rel="noopener">www.garanteprivacy.it</a>'),
                 ('www.facebook.com/privacy/policy', '<a href="https://www.facebook.com/privacy/policy" rel="noopener">www.facebook.com/privacy/policy</a>')):
        h = h.replace(a, b)
    return h

def paras(s, cls=''):
    c = f' class="{cls}"' if cls else ''
    return ''.join(f'<p{c}>{linkify(e(p))}</p>' for p in s.get('paragraphs', []) if p.strip())

def kicker(s):
    return f'<span class="kicker">{e(s)}</span>' if s else ''

ANCORE = {('cena', 'pl'): 'kolacja'}

def int_link(lang, it):
    """Collegamento a un'altra pagina del sito ("colazione#cena"), con il testo preso da ui -> link_<ancora>."""
    spec = it.get('link_interno', '')
    if not spec:
        return ''
    page, _, frag = spec.partition('#')
    return f' <a class="nowrap" href="{url(page, lang)}{"#" + ANCORE.get((frag, lang), frag) if frag else ""}">{e(ui(lang, "link_" + (frag or page)))}</a>'

# ---------------------------------------------------------------- immagini
WIDTHS = [480, 800, 1200, 1600]
HERO = 2000
_done = {}

def _hash(path):
    return hashlib.md5(open(path, 'rb').read()).hexdigest()[:8]

def foto(n, hero=False):
    """Rende disponibili le versioni web della foto n e ne restituisce i dati."""
    key = (n, hero)
    if key in _done:
        return _done[key]
    from PIL import Image
    meta = F[n]
    src = os.path.join(os.path.expanduser(C['cartella_master']), meta['file'])
    slug = meta['slug']
    outdir = os.path.join(R, 'img', 'foto')
    os.makedirs(outdir, exist_ok=True)
    im = None
    with Image.open(src) as probe:
        W, H = probe.size
    ws = [w for w in WIDTHS + ([HERO] if hero else []) if w <= W] or [W]
    for w in ws:
        for ext in ('webp', 'jpg'):
            if ext == 'jpg' and w not in (800, 1600, ws[-1]):
                continue
            p = os.path.join(outdir, f'{slug}-{w}.{ext}')
            if os.path.exists(p) and os.path.getmtime(p) >= os.path.getmtime(src):
                continue
            if im is None:
                im = Image.open(src).convert('RGB')
            r = im.resize((w, round(H * w / W)), Image.LANCZOS) if w != W else im
            if ext == 'webp':
                r.save(p, 'WEBP', quality=76, method=6)
            else:
                r.save(p, 'JPEG', quality=80, optimize=True, progressive=True)
    d = {'slug': slug, 'w': W, 'h': H, 'widths': ws, 'alt': meta['alt']}
    _done[key] = d
    return d

def picture(n, lang, sizes='100vw', cls='', eager=False, hero=False, style='', alt=None):
    d = foto(n, hero=hero)
    base = f"/img/foto/{d['slug']}"
    webp = ', '.join(f'{base}-{w}.webp {w}w' for w in d['widths'])
    jpgs = [w for w in d['widths'] if w in (800, 1600) or w == d['widths'][-1]]
    jsrc = ', '.join(f'{base}-{w}.jpg {w}w' for w in sorted(set(jpgs)))
    fallback = f'{base}-{800 if 800 in d["widths"] else d["widths"][-1]}.jpg'
    w0 = 800 if 800 in d['widths'] else d['widths'][-1]
    h0 = round(d['h'] * w0 / d['w'])
    alt = d['alt'].get(lang, '') if alt is None else alt
    load = 'eager" fetchpriority="high' if eager else 'lazy'
    c = f' class="{cls}"' if cls else ''
    st = f' style="{style}"' if style else ''
    return (f'<picture><source type="image/webp" srcset="{webp}" sizes="{sizes}">'
            f'<img{c}{st} src="{fallback}" srcset="{jsrc}" sizes="{sizes}" width="{w0}" height="{h0}" alt="{e(alt)}" loading="{load}" decoding="async"></picture>')

def og_image(n):
    """Immagine 1200x630 per la condivisione (WhatsApp, Facebook)."""
    from PIL import Image
    meta = F[n]
    out = os.path.join(R, 'img', 'og', f"{meta['slug']}.jpg")
    src = os.path.join(os.path.expanduser(C['cartella_master']), meta['file'])
    if not (os.path.exists(out) and os.path.getmtime(out) >= os.path.getmtime(src)):
        os.makedirs(os.path.dirname(out), exist_ok=True)
        im = Image.open(src).convert('RGB')
        W, H = im.size
        tw = W; th = round(W * 630 / 1200)
        if th > H:
            th = H; tw = round(H * 1200 / 630)
        x = (W - tw) // 2; y = max(0, (H - th) // 3)
        im.crop((x, y, x + tw, y + th)).resize((1200, 630), Image.LANCZOS).save(out, 'JPEG', quality=82, optimize=True, progressive=True)
    return f"{DOM}/img/og/{meta['slug']}.jpg"

def asset(p):
    full = os.path.join(R, p.lstrip('/'))
    return f'{p}?v={_hash(full)}'

# ---------------------------------------------------------------- icone
ICON = {
 'neve': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 2v20M4.9 7l14.2 10M4.9 17L19.1 7M9 4l3 2 3-2M9 20l3-2 3 2"/></svg>',
 'sole': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>',
 'wa': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 20l1.3-3.9A8 8 0 1 1 8 19z"/><path d="M9.5 9.5c.3 1.6 1.4 3.2 3 4 .5.2 1 .2 1.4-.2l.6-.6"/></svg>',
 'menu': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg>',
 'prev': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 5l-7 7 7 7"/></svg>',
 'next': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 5l7 7-7 7"/></svg>',
 'cal': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18"/></svg>',
}

def wa_link(lang):
    from urllib.parse import quote
    return f"https://wa.me/{C['contatti']['whatsapp']}?text={quote(ui(lang, 'whatsapp_msg'))}"

def book_href(lang):
    return f"{C['prenotazione']['engine']}?lang={C['prenotazione']['lingua_engine'][lang]}"

def book_btn(lang, label=None, adults=2, cls='btn', sr='', con_date=True):
    lab = label or ui(lang, 'book_long')
    extra = f'<span class="sr-only"> – {e(sr)}</span>' if sr else ''
    dati = f' data-book data-adults="{adults}"' if con_date else ''
    return f'<a class="{cls}" href="{book_href(lang)}"{dati}>{ICON["cal"]}{e(lab)}{extra}</a>'

# ---------------------------------------------------------------- testata e piede
def srcset_webp(n):
    d = foto(n, hero=True)
    return ', '.join(f"/img/foto/{d['slug']}-{w}.webp {w}w" for w in d['widths'])

# Stagione del sito: quella scelta durante la visita (sessionStorage), altrimenti estate da maggio a ottobre
SCRIPT_STAGIONE = ("var D=document.documentElement,M=window.MAFFEI,st;try{st=sessionStorage.getItem('maffei-stagione')}catch(e){}"
                   "if(st!=='estate'&&st!=='inverno'){var m=new Date().getMonth();st=(m>=4&&m<=9)?'estate':'inverno'}"
                   "D.classList.add('st-'+st);if(M.heroPre){var l=document.createElement('link');l.rel='preload';l.as='image';l.type='image/webp';"
                   "l.setAttribute('imagesrcset',M.heroPre[st]);l.setAttribute('imagesizes','100vw');l.setAttribute('fetchpriority','high');document.head.appendChild(l)}")

# Scelta sul banner: {s: 'si'|'no', t: data in ms, v: versione della pagina Cookie}; si richiede dopo 180 giorni
SCRIPT_CONSENSO = ("try{var c=JSON.parse(localStorage.getItem('maffei-consenso')||'null');"
                   "if(c&&c.v===M.consensoVer&&Date.now()-c.t<15552e6){D.classList.add('ck-ok');M.consenso=c.s}}catch(e){}")

def head(page, lang, t, hero_n=None, extra_ld=None, hero_estate=None, noindex=False, evento=None):
    title = t['meta_title']; desc = t['meta_description']
    if noindex:
        alts = '<meta name="robots" content="noindex">'
    else:
        alts = ''.join(f'<link rel="alternate" hreflang="{l}" href="{absu(page, l)}">' for l in LANGS)
        alts += f'<link rel="alternate" hreflang="x-default" href="{absu(page, "it")}">'
    og_n = C['foto_pagine']['og'].get(page, C['foto_pagine']['og']['home'])
    og = og_image(og_n)
    og_alt = ''.join(f'<meta property="og:locale:alternate" content="{C["locale"][l]}">' for l in LANGS if l != lang)
    pre = ''
    if hero_n and not hero_estate:
        pre = f'<link rel="preload" as="image" type="image/webp" imagesrcset="{srcset_webp(hero_n)}" imagesizes="100vw" fetchpriority="high">'
    ld = [jsonld_breadcrumb(page, lang, t)] if page != 'home' else []
    if extra_ld:
        ld.extend(extra_ld)
    lds = ''.join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in ld if x)
    cfg = {'widget': C['prenotazione']['widget'], 'engine': C['prenotazione']['engine'], 'bookLang': C['prenotazione']['lingua_engine'][lang],
           'beddyScript': C['prenotazione']['script'], 'stagioni': C['prenotazione']['stagioni'],
           'pixel': C['pixel']['id'], 'consensoVer': C['pixel']['versione_consenso']}
    if evento:
        cfg['evento'] = evento
    if hero_n and hero_estate:
        cfg['heroPre'] = {'inverno': srcset_webp(hero_n), 'estate': srcset_webp(hero_estate)}
    return f'''<!DOCTYPE html>
<html lang="{lang}" class="no-js{' cta-vista' if page == 'home' and hero_n else ''}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="format-detection" content="telephone=no">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
{'' if noindex else f'<link rel="canonical" href="{absu(page, lang)}">'}
{alts}
<meta name="theme-color" content="#F3F1EB" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#131916" media="(prefers-color-scheme: dark)">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{e(C['nome'])}">
<meta property="og:locale" content="{C['locale'][lang]}">{og_alt}
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{absu(page, lang)}">
<meta property="og:image" content="{og}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{e(F[og_n]['alt'].get(lang, ''))}">
<meta name="twitter:image:alt" content="{e(F[og_n]['alt'].get(lang, ''))}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="icon" type="image/png" href="/img/logo/icona-192.png" sizes="192x192">
<link rel="apple-touch-icon" href="/img/logo/apple-touch-icon.png">
<link rel="preload" href="/assets/fonts/gloock-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/assets/fonts/hanken-grotesk-latin.woff2" as="font" type="font/woff2" crossorigin>
{pre}
<link rel="stylesheet" href="{asset('/assets/sito.css')}">
<style id="beddy-default-font"></style>
<script>document.documentElement.className=document.documentElement.className.replace('no-js','js');window.MAFFEI={json.dumps(cfg)};{SCRIPT_STAGIONE}{SCRIPT_CONSENSO}</script>
<script src="{asset('/assets/sito.js')}" defer></script>
{lds}
</head>
'''

def header(page, lang):
    items = []
    for p in C['menu']:
        cur = ' aria-current="page"' if p == page else ''
        label = {'camere': 'nav_rooms', 'colazione': 'nav_breakfast', 'pinzolo': 'nav_pinzolo', 'contatti': 'nav_contact'}[p]
        items.append(f'<li><a href="{url(p, lang)}"{cur}>{e(ui(lang, label))}</a></li>')
    CUR = ' aria-current="true"'
    langs = ''.join(
        f'<a href="{lurl(page, l)}" hreflang="{l}" lang="{l}"{CUR if l == lang else ""}>{l.upper()}</a>' for l in LANGS)
    return f'''<body>
<a class="skip" href="#main">{e(ui(lang, 'skip'))}</a>
<div class="cookie" role="region" aria-label="{e(ui(lang, 'cookie_label'))}"><div class="wrap"><p>{e(ui(lang, 'cookie_text'))} <a href="{url('cookie', lang)}">{e(ui(lang, 'cookie_more'))}</a></p><div class="cookie-btns"><button class="btn btn-line" type="button" data-consenso="no">{e(ui(lang, 'cookie_no'))}</button><button class="btn btn-line" type="button" data-consenso="si">{e(ui(lang, 'cookie_si'))}</button></div></div></div>
<header class="top">
<div class="wrap">
<a class="logo" href="{url('home', lang)}"><picture><source type="image/webp" srcset="/img/logo/logo-maffei-128.webp 1x, /img/logo/logo-maffei-256.webp 2x"><img src="/img/logo/logo-maffei-128.png" width="{LOGO_W128}" height="128" alt="" style="height:64px;width:auto"></picture><span class="logo-name">Hotel Garnì Maffei<small>Pinzolo · <span aria-hidden="true">★★★</span><span class="sr-only">{e(ui(lang, 'stars'))}</span></small></span></a>
<nav class="nav" id="nav" aria-label="{e(ui(lang, 'menu'))}"><ul>{''.join(items)}</ul></nav>
<div class="langs" role="group" aria-label="{e(ui(lang, 'lang_label'))}">{langs}</div>
<a class="btn btn-small btn-book" href="{book_href(lang)}" data-book data-adults="2">{e(ui(lang, 'book'))}</a>
<button class="menu-btn" type="button" aria-expanded="false" aria-controls="nav">{ICON['menu']}{e(ui(lang, 'menu'))}</button>
</div>
</header>
'''

def footer(page, lang):
    c = C['contatti']; so = C['societa']
    langs = ' · '.join(f'<a href="{lurl(page, l)}" hreflang="{l}" lang="{l}">{l.upper()}</a>' for l in LANGS)
    menu = ''.join(f'<li><a href="{url(p, lang)}">{e(ui(lang, {"camere": "nav_rooms", "colazione": "nav_breakfast", "pinzolo": "nav_pinzolo", "contatti": "nav_contact"}[p]))}</a></li>' for p in C['menu'])
    beddy_note = ui(lang, 'beddy_note')
    note = f'<p class="muted" style="font-size:14px;margin-top:14px">{e(beddy_note)}</p>' if beddy_note else ''
    return f'''<footer class="foot">
<div class="wrap">
<div class="cols">
<div><picture><source type="image/webp" srcset="/img/logo/logo-maffei-256.webp"><img class="flogo" src="/img/logo/logo-maffei-256.png" width="{LOGO_W256}" height="256" alt="Hotel Garnì Maffei" style="height:84px;width:auto" loading="lazy" decoding="async"></picture><p>{e(c['via'])}<br>{e(c['cap'])} {e(c['citta'])} ({e(c['provincia'])})</p></div>
<div><h2>{e(ui(lang, 'footer_contacts'))}</h2><ul>
<li>{e(ui(lang, 'cell_label'))}: <a href="tel:{c['cellulare_tel']}">{e(c['cellulare'])}</a></li>
<li>{e(ui(lang, 'phone_label'))}: <a href="tel:{c['fisso_tel']}">{e(c['fisso'])}</a></li>
<li><a href="mailto:{c['email']}">{e(c['email'])}</a></li>
<li><a href="{c['instagram']}" rel="noopener">{e(ui(lang, 'instagram'))}</a></li></ul></div>
<div><h2>{e(ui(lang, 'footer_info'))}</h2><ul>{menu}<li><a href="{url('privacy', lang)}">{e(ui(lang, 'privacy'))}</a></li><li><a href="{url('cookie', lang)}">{e(ui(lang, 'cookie_page'))}</a></li><li><button class="link-btn" type="button" data-cookie-pref>{e(ui(lang, 'cookie_pref'))}</button></li></ul>{note}</div>
<div><h2>{e(ui(lang, 'footer_company'))}</h2><p>{e(so['ragione'])}<br>{e(ui(lang, 'company_vat'))} {e(so['piva'])} · {e(ui(lang, 'company_rea'))} {e(so['rea'])}<br>{e(ui(lang, 'company_cin'))} {e(so['cin'])}</p></div>
</div>
<p class="legal">© {date.today().year} {e(C['nome'])} · {langs}</p>
</div>
</footer>
<div class="bookbar" role="region" aria-label="{e(ui(lang, 'book_bar_label'))}"><div class="wrap"><p>{e(ui(lang, 'book_note'))}</p>{book_btn(lang)}</div></div>
<beddy-bar lang="{C['prenotazione']['lingua_engine'][lang]}" widgetcode="{C['prenotazione']['widget']}"></beddy-bar>
<a class="wa-fab" href="{wa_link(lang)}" rel="noopener" aria-label="{e(ui(lang, 'whatsapp'))}">{ICON['wa']}</a>
</body>
</html>
'''

# ---------------------------------------------------------------- dati strutturati
def jsonld_breadcrumb(page, lang, t):
    return {'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': 1, 'name': ui(lang, 'breadcrumb_home') or C['nome'], 'item': absu('home', lang)},
        {'@type': 'ListItem', 'position': 2, 'name': page_label(page, lang, t), 'item': absu(page, lang)}]}

def jsonld_hotel(lang, t):
    c = C['contatti']
    return {
        '@context': 'https://schema.org', '@type': 'Hotel', '@id': DOM + '/#hotel',
        'name': C['nome'], 'alternateName': 'Hotel Maffei', 'url': absu('home', lang),
        'description': t['meta_description'],
        'image': [og_image(C['foto_pagine']['og']['home']), og_image(C['foto_pagine']['og']['camere'])],
        'logo': DOM + '/img/logo/logo-maffei-256.png',
        'telephone': c['cellulare_tel'], 'email': c['email'],
        'address': {'@type': 'PostalAddress', 'streetAddress': c['via'], 'postalCode': c['cap'], 'addressLocality': c['citta'], 'addressRegion': c['provincia'], 'addressCountry': c['paese']},
        'geo': {'@type': 'GeoCoordinates', 'latitude': c['lat'], 'longitude': c['lon']},
        'hasMap': c['maps'],
        'starRating': {'@type': 'Rating', 'ratingValue': '3'},
        'numberOfRooms': 13, 'checkinTime': '14:00', 'checkoutTime': '10:00',
        'amenityFeature': [{'@type': 'LocationFeatureSpecification', 'name': n, 'value': True} for n in ('Breakfast included', 'Free WiFi', 'Ski storage', 'Parking')],
        'sameAs': [c['instagram']],
        'potentialAction': {'@type': 'ReserveAction', 'target': book_href(lang)},
    }

def jsonld_faq(t):
    if not t.get('faq'):
        return None
    return {'@context': 'https://schema.org', '@type': 'FAQPage', 'mainEntity': [
        {'@type': 'Question', 'name': q['q'], 'acceptedAnswer': {'@type': 'Answer', 'text': q['a']}} for q in t['faq']]}

def jsonld_rooms(lang, t):
    items = []
    for k, r in enumerate(C['camere']):
        s = sec(t, r['id'])
        maxv = int(re.sub(r'\D', '', r['ospiti']['en']) or r['adulti'])
        items.append({'@type': 'ListItem', 'position': k + 1, 'item': {
            '@type': 'HotelRoom', 'name': s['title'], 'description': ' '.join(s.get('paragraphs', [])),
            'occupancy': {'@type': 'QuantitativeValue', 'maxValue': maxv, 'unitCode': 'C62'},
            'image': f"{DOM}/img/foto/{foto(r['foto'][0])['slug']}-1200.webp"}})
    return {'@context': 'https://schema.org', '@type': 'ItemList', 'itemListElement': items}

# ---------------------------------------------------------------- pagine
def stagione_switch(lang):
    b = lambda k, ic: f'<button type="button" data-stagione="{k}" aria-pressed="false">{ICON[ic]}{e(ui(lang, "season_" + ("winter" if k == "inverno" else "summer")))}</button>'
    return f'<div class="stagione-switch" role="group" aria-label="{e(ui(lang, "season_label"))}">{b("inverno", "neve")}{b("estate", "sole")}</div>'

def hero(n, lang, t, sub=False, pos='50% 50%', n_estate=None, pos_estate='50% 50%', cta_html=None):
    cls = 'hero hero-sub' if sub else 'hero'
    k = kicker(t.get('kicker', ''))
    lead = f'<p class="lead">{e(t.get("lead", ""))}</p>' if t.get('lead') else ''
    cta = ''
    if cta_html:
        cta = f'<div class="cta">{cta_html}</div>'
    elif not sub:
        cta = f'<div class="cta">{book_btn(lang)}<a class="btn btn-line" href="{wa_link(lang)}" rel="noopener">{ICON["wa"]}{e(ui(lang, "whatsapp"))}</a></div>'
    if n_estate:
        cls += ' hero-stagioni'
        pics = (picture(n, lang, sizes="100vw", hero=True, cls='solo-inverno')
                + picture(n_estate, lang, sizes="100vw", hero=True, cls='solo-estate', style=f'object-position:{pos_estate}') + stagione_switch(lang))
    else:
        pics = picture(n, lang, sizes="100vw", eager=True, hero=True)
    return f'''<section class="{cls}" style="--pos:{pos}">
{pics}
<div class="wrap">{k}<h1>{e(t['h1'])}</h1>{lead}{cta}</div>
</section>
'''

# punti della foto dall'alto (9900), in percentuale: la punta della freccia
ETICHETTE_DOVE = (('label_gondola', 19, 40), ('label_hotel', 79, 30))

def foto_dove(n, lang, sizes):
    tag = ''.join(f'<span class="etichetta" style="left:{x}%;top:{y}%">{e(ui(lang, k))}</span>' for k, x, y in ETICHETTE_DOVE)
    return f'<figure class="figure figure-etichette" style="--ratio:16/9">{picture(n, lang, sizes=sizes)}{tag}</figure>'

NAV_KEY = {'camere': 'nav_rooms', 'colazione': 'nav_breakfast', 'pinzolo': 'nav_pinzolo', 'contatti': 'nav_contact', 'privacy': 'privacy', 'cookie': 'cookie_page'}

def page_label(page, lang, t):
    k = NAV_KEY.get(page)
    return (ui(lang, k) if k else '') or t['h1']

def crumbs(page, lang, t):
    return f'<nav class="wrap breadcrumb" aria-label="{e(ui(lang, "breadcrumb_label"))}"><a href="{url("home", lang)}">{e(ui(lang, "breadcrumb_home"))}</a> › <span aria-current="page">{e(page_label(page, lang, t))}</span></nav>'

def room_names(lang):
    tc = page_t('camere', lang)
    return {r['id']: sec(tc, r['id'])['title'] for r in C['camere']}

def solo(i):
    return f' class="solo-{i["stagione"]}"' if i.get('stagione') else ''

def render_home(lang):
    t = page_t('home', lang); fp = C['foto_pagine']
    names = room_names(lang)
    out = [head('home', lang, t, hero_n=fp['home_hero'], extra_ld=[jsonld_hotel(lang, t)], hero_estate=fp['home_hero_estate']), header('home', lang), '<main id="main">']
    out.append(hero(fp['home_hero'], lang, t, pos='35% 50%', n_estate=fp['home_hero_estate'], pos_estate='40% 55%'))
    s = sec(t, 'in-breve')
    lis = ''.join(f'<li{solo(i)}><h3>{e(i["t"])}</h3><p>{e(i["d"])}{int_link(lang, i)}</p></li>' for i in s['items'])
    out.append(f'<section class="section" aria-labelledby="s-breve"><div class="wrap"><div class="section-head center">{kicker(s["kicker"])}<h2 id="s-breve">{e(s["title"])}</h2></div><ul class="facts">{lis}</ul></div></section>')
    s = sec(t, 'camere')
    lines = {}
    for i, it in enumerate(s['items']):
        lines[i] = it
    cards = []
    for k, r in enumerate(C['camere']):
        nm = names[r['id']]
        line = next((it['d'] for it in s['items'] if it['t'].strip().lower() == nm.strip().lower()), lines.get(k, {}).get('d', ''))
        cards.append(f'<a class="card" href="{url("camere", lang)}#{r["id"]}">{picture(r["foto"][0], lang, sizes="(min-width: 1180px) 360px, (min-width: 700px) 45vw, 100vw", alt="")}<div class="card-body"><h3>{e(nm)}</h3><p>{e(line)}</p><span class="more" aria-hidden="true">→</span></div></a>')
    out.append(f'<section class="section" aria-labelledby="s-camere"><div class="wrap"><div class="section-head">{kicker(s["kicker"])}<h2 id="s-camere">{e(s["title"])}</h2>{paras(s, "lead")}</div><div class="cards">{"".join(cards)}</div><p style="margin-top:26px"><a class="btn btn-line" href="{url("camere", lang)}">{e(s["cta"] or ui(lang, "rooms_all"))}</a></p></div></section>')
    s = sec(t, 'colazione')
    out.append(f'<section class="feature" aria-labelledby="s-colazione">{picture(fp["home_colazione"], lang, sizes="100vw")}<div class="panel">{kicker(s["kicker"])}<h2 id="s-colazione">{e(s["title"])}</h2>{paras(s)}<p style="margin-top:16px"><a href="{url("colazione", lang)}">{e(s["cta"])}</a></p></div></section>')
    s = sec(t, 'luca-manuela')
    out.append(f'<section class="section" style="padding-top:clamp(56px,8vw,104px)" aria-labelledby="s-noi"><div class="wrap grid-2"><div class="hosts-photo">{picture(fp["home_luca_manuela"], lang, sizes="(min-width: 860px) 520px, 100vw")}</div><div>{kicker(s["kicker"])}<h2 id="s-noi" style="margin-bottom:16px">{e(s["title"])}</h2>{paras(s)}<p class="sign">{e(ui(lang, "signature"))}</p></div></div></section>')
    s = sec(t, 'pinzolo')
    figs = ''.join(f'<figure class="figure solo-{k}" style="--ratio:3/2">{picture(fp[f], lang, sizes="(min-width: 860px) 560px, 100vw")}</figure>' for k, f in (('inverno', 'home_pinzolo'), ('estate', 'home_pinzolo_estate')))
    p_inv, p_est = (f'<p>{linkify(e(x))}</p>' for x in s['paragraphs'])
    tit = f'<span class="solo-inverno">{e(s["title"])}</span><span class="solo-estate">{e(s["title_estate"])}</span>'
    kic = f'<span class="kicker"><span class="solo-inverno">{e(s["kicker"])}</span><span class="solo-estate">{e(s["kicker_estate"])}</span></span>'
    out.append(f'<section class="section" aria-labelledby="s-pinzolo"><div class="wrap grid-2">{figs}<div>{kic}<h2 id="s-pinzolo" style="margin-bottom:16px">{tit}</h2><div class="solo-inverno">{p_inv}{p_est}</div><div class="solo-estate">{p_est}{p_inv}</div><p style="margin-top:18px"><a class="btn btn-line" href="{url("pinzolo", lang)}">{e(s["cta"])}</a></p></div></div></section>')
    s = sec(t, 'dove')
    out.append(f'<section class="section" aria-labelledby="s-dove"><div class="wrap grid-2"><div>{kicker(s["kicker"])}<h2 id="s-dove" style="margin-bottom:16px">{e(s["title"])}</h2>{paras(s)}<p style="margin-top:18px"><a class="btn btn-line" href="{url("contatti", lang)}">{e(s["cta"])}</a></p></div>{foto_dove(fp["home_dove"], lang, "(min-width: 860px) 560px, 100vw")}</div></section>')
    s = sec(t, 'recensioni'); rv = C['recensioni']
    v_b = rv['booking']['voto'] if lang in ('it', 'pl') else rv['booking']['voto_en']
    v_g = rv['google']['voto'] if lang in ('it', 'pl') else rv['google']['voto_en']
    ordine = sorted(rv['citazioni'], key=lambda q: (q['lingua'] != lang, q['lingua'] != 'en'))
    qa, qc = {'it': ('«', '»'), 'en': ('“', '”'), 'pl': ('„', '”')}[lang]
    quotes = ''.join(f'<figure class="quote"><blockquote lang="{q["lingua"]}">{qa}{e(q["testo"])}{qc}</blockquote><figcaption>{e(q["autore"])} · {e(q["fonte"])}</figcaption></figure>' for q in ordine)
    out.append(f'<section class="section" aria-labelledby="s-recensioni"><div class="wrap"><div class="section-head">{kicker(s["kicker"])}<h2 id="s-recensioni">{e(s["title"])}</h2>{paras(s, "lead")}</div><div class="grid-2" style="align-items:start"><div class="scores"><a class="score" href="{rv["booking"]["url"]}" rel="noopener"><strong>{v_b}<small>/{rv["booking"]["su"]}</small></strong><span>{e(ui(lang, "reviews_booking"))} · {e(conta(lang, rv["booking"]["numero"]))}</span></a><div class="score"><strong>{v_g}<small>/{rv["google"]["su"]}</small></strong><span>{e(ui(lang, "reviews_google"))} · {e(conta(lang, rv["google"]["numero"]))}</span></div><p class="muted" style="flex-basis:100%;font-size:14px;margin:0">{e(ui(lang, "reviews_date"))}</p></div><div class="quotes">{quotes}</div></div></div></section>')
    out.append('</main>'); out.append(footer('home', lang))
    return ''.join(out)

def gallery(ns, lang, label):
    figs = ''.join(f'<figure>{picture(n, lang, sizes="(min-width: 860px) 620px, 100vw")}</figure>' for n in ns)
    nav = f'<div class="gallery-nav"><button type="button" data-prev aria-label="{e(ui(lang, "gallery_prev"))}">{ICON["prev"]}</button><span class="gallery-count" aria-live="polite">1 / {len(ns)}</span><button type="button" data-next aria-label="{e(ui(lang, "gallery_next"))}">{ICON["next"]}</button></div>'
    return f'<div class="gallery" role="group" aria-label="{e(label)}"><div class="gallery-track" tabindex="0">{figs}</div>{nav}</div>'

def render_camere(lang):
    t = page_t('camere', lang); fp = C['foto_pagine']
    out = [head('camere', lang, t, hero_n=fp['camere_hero'], extra_ld=[jsonld_rooms(lang, t)]), header('camere', lang), '<main id="main">']
    out.append(hero(fp['camere_hero'], lang, t, sub=True))
    out.append(crumbs('camere', lang, t))
    s = sec(t, 'da-sapere')
    notes = ''.join(f'<li><strong>{e(i["t"])}</strong><span>{e(i["d"])}{int_link(lang, i)}</span></li>' for i in s['items'])
    out.append(f'<section class="section" style="padding-top:40px" aria-labelledby="s-sapere"><div class="wrap"><h2 id="s-sapere" style="margin-bottom:18px">{e(s["title"])}</h2><ul class="notes">{notes}</ul></div></section>')
    out.append('<div class="wrap">')
    for r in C['camere']:
        s = sec(t, r['id'])
        specs = (f'<dt>{e(ui(lang, "room_guests"))}</dt><dd>{e(r["ospiti"][lang])}</dd>'
                 f'<dt>{e(ui(lang, "room_beds"))}</dt><dd>{e(r["letti"][lang])}</dd>'
                 f'<dt>{e(ui(lang, "room_bath"))}</dt><dd>{e(ui(lang, "room_bath_value"))}</dd>'
                 f'<dt>{e(ui(lang, "room_count"))}</dt><dd>{r["quante"]}</dd>')
        out.append(f'<section class="room" id="{r["id"]}" aria-labelledby="h-{r["id"]}">{gallery(r["foto"], lang, ui(lang, "gallery_label") + ": " + s["title"])}<div>{kicker(s["kicker"])}<h2 id="h-{r["id"]}">{e(s["title"])}</h2>{paras(s)}<dl class="specs">{specs}</dl>{book_btn(lang, s["cta"] or None, adults=r["adulti"], sr=s["title"])}</div></section>')
    out.append('</div>')
    s = sec(t, 'in-tutte-le-camere')
    am = ''.join(f'<li><strong>{e(i["t"])}</strong>{f"<span>{e(i[chr(100)])}</span>" if i.get("d") else ""}</li>' for i in s['items'])
    strip = ''.join(picture(n, lang, sizes='(min-width: 1180px) 380px, 50vw') for n in fp['camere_bagni'] + fp['camere_balconi'])
    out.append(f'<section class="section" style="padding-top:clamp(40px,6vw,72px)" aria-labelledby="s-tutte"><div class="wrap"><h2 id="s-tutte" style="margin-bottom:18px">{e(s["title"])}</h2><ul class="amenities">{am}</ul>{paras(s, "strip-note")}<div class="strip">{strip}</div></div></section>')
    s = sec(t, 'prenota')
    out.append(f'<section class="section" aria-labelledby="s-prenota"><div class="wrap center" style="max-width:720px"><h2 id="s-prenota" style="margin-bottom:12px">{e(s["title"])}</h2>{paras(s, "lead")}<p style="margin-top:22px;display:flex;gap:12px;justify-content:center;flex-wrap:wrap">{book_btn(lang, s["cta"] or None)}<a class="btn btn-line" href="{wa_link(lang)}" rel="noopener">{ICON["wa"]}{e(ui(lang, "whatsapp"))}</a></p></div></section>')
    out.append('</main>'); out.append(footer('camere', lang))
    return ''.join(out)

def cta_book(lang, s, con_date=True):
    return f'<p style="margin-top:20px">{book_btn(lang, s["cta"], con_date=con_date)}</p>' if s.get('cta') else ''

def cta_wa(lang, s):
    return f'<p style="margin-top:22px"><a class="btn btn-line" href="{wa_link(lang)}" rel="noopener">{ICON["wa"]}{e(s["cta"] or ui(lang, "whatsapp"))}</a></p>'

def items_list(s):
    return '<ul class="items">' + ''.join(f'<li><strong>{e(i["t"])}</strong><span>{linkify(e(i["d"]))}</span></li>' for i in s['items']) + '</ul>' if s['items'] else ''

def render_colazione(lang):
    t = page_t('colazione', lang); fp = C['foto_pagine']
    out = [head('colazione', lang, t, hero_n=fp['colazione_hero']), header('colazione', lang), '<main id="main">']
    out.append(hero(fp['colazione_hero'], lang, t, sub=True))
    out.append(crumbs('colazione', lang, t))
    s = sec(t, 'buffet')
    strip = ''.join(picture(n, lang, sizes='(min-width: 1180px) 280px, 50vw') for n in fp['colazione_buffet'])
    out.append(f'<section class="section" style="padding-top:40px" aria-labelledby="s-buffet"><div class="wrap"><div class="section-head"><h2 id="s-buffet">{e(s["title"])}</h2>{paras(s, "lead")}</div>{items_list(s)}<div class="strip">{strip}</div></div></section>')
    s = sec(t, 'torte')
    out.append(f'<section class="section" style="padding-top:clamp(56px,8vw,104px)" aria-labelledby="s-torte"><div class="wrap grid-2"><figure class="figure" style="--ratio:4/3">{picture(fp["colazione_torte"], lang, sizes="(min-width: 860px) 560px, 100vw")}</figure><div><h2 id="s-torte" style="margin-bottom:16px">{e(s["title"])}</h2>{paras(s)}</div></div></section>')
    s1 = sec(t, 'orari')
    out.append(f'<section class="section" aria-labelledby="s-orari"><div class="wrap"><div style="max-width:720px"><h2 id="s-orari" style="margin-bottom:8px">{e(s1["title"])}</h2>{paras(s1)}{items_list(s1)}</div></div></section>')
    strip = ''.join(picture(n, lang, sizes='(min-width: 1180px) 380px, 50vw') for n in fp['colazione_sala'])
    out.append(f'<div class="wrap"><div class="strip">{strip}</div></div>')
    out.append(render_ristoranti(lang, sec(t, 'cena')))
    s = sec(t, 'prenota')
    out.append(f'<section class="section" style="padding-top:clamp(56px,8vw,104px)" aria-labelledby="s-prenota"><div class="wrap center" style="max-width:720px"><h2 id="s-prenota" style="margin-bottom:12px">{e(s["title"])}</h2>{paras(s, "lead")}<p style="margin-top:22px;display:flex;gap:12px;justify-content:center;flex-wrap:wrap">{book_btn(lang, s["cta"] or None)}<a class="btn btn-line" href="{wa_link(lang)}" rel="noopener">{ICON["wa"]}{e(ui(lang, "whatsapp"))}</a></p></div></section>')
    out.append('</main>'); out.append(footer('colazione', lang))
    return ''.join(out)

def render_ristoranti(lang, s):
    """I ristoranti che consigliamo (config.json -> ristoranti), a gruppi; titoli e note da testi.json (sezione cena)."""
    R = C.get('ristoranti', {})
    blocchi = ''
    for g in R.get('gruppi', []):
        lis = ''
        for r in (x for x in R.get('elenco', []) if x['gruppo'] == g):
            sito = r.get('sito', '')
            sito = sito.get(lang, '') if isinstance(sito, dict) else sito
            nome = f'<a href="{sito}" rel="noopener">{e(r["nome"])}</a>' if sito else e(r['nome'])
            nb = lambda x: x.replace(' ', '\u00a0')
            det = [ui(lang, 'tipo_' + r['tipo']), r.get('luogo', ''), nb(r['nota'][lang]) if r.get('nota') else '']
            if r.get('minuti_piedi'):
                det.append(nb(ui(lang, 'min_piedi').replace('{n}', str(r['minuti_piedi']))))
            elif r.get('km'):
                km = f'{r["km"]:g}'
                det.append(nb(ui(lang, 'km').replace('{n}', km if lang == 'en' else km.replace('.', ','))))
            lis += f'<li><strong>{nome}</strong><span>{e(" · ".join(x for x in det if x))}</span></li>'
        if lis:
            blocchi += f'<div><h3>{e(s["gruppi"][g])}</h3><ul class="items">{lis}</ul></div>'
    lista = f'<div class="ristoranti">{blocchi}</div>' if blocchi else ''
    nota = f'<p class="muted" style="margin-top:24px">{e(s["nota"])}</p>' if s.get('nota') else ''
    return (f'<section class="section" id="{ANCORE.get(("cena", lang), "cena")}" aria-labelledby="s-cena"><div class="wrap"><div class="section-head">'
            f'<h2 id="s-cena">{e(s["title"])}</h2>{paras(s, "lead")}</div>{lista}{nota}</div></section>')

def render_pinzolo(lang):
    t = page_t('pinzolo', lang); fp = C['foto_pagine']; L = C['link_esterni']
    out = [head('pinzolo', lang, t, hero_n=fp['pinzolo_hero'], hero_estate=fp['pinzolo_hero_estate']), header('pinzolo', lang), '<main id="main">']
    out.append(hero(fp['pinzolo_hero'], lang, t, sub=True, pos='50% 40%', n_estate=fp['pinzolo_hero_estate'], pos_estate='50% 40%'))
    out.append(crumbs('pinzolo', lang, t))
    s = sec(t, 'inverno')
    out.append('<div class="sezioni-stagione">')
    out.append(f'<section class="section sez-inverno" aria-labelledby="s-inverno"><div class="wrap grid-2" style="align-items:start"><div><span class="kicker">{e(ui(lang, "season_winter"))}</span><h2 id="s-inverno" style="margin-bottom:16px">{e(s["title"])}</h2>{paras(s)}{items_list(s)}{cta_book(lang, s)}</div><figure class="figure" style="--ratio:4/3">{picture(fp["pinzolo_inverno"], lang, sizes="(min-width: 860px) 560px, 100vw")}</figure></div></section>')
    s = sec(t, 'estate')
    out.append(f'<section class="section sez-estate" aria-labelledby="s-estate"><div class="wrap grid-2" style="align-items:start"><figure class="figure" style="--ratio:4/3">{picture(fp["pinzolo_estate"], lang, sizes="(min-width: 860px) 560px, 100vw")}</figure><div><span class="kicker">{e(ui(lang, "season_summer"))}</span><h2 id="s-estate" style="margin-bottom:16px">{e(s["title"])}</h2>{paras(s)}{items_list(s)}{cta_book(lang, s, con_date=False)}</div></div></section>')
    out.append('</div>')
    s = sec(t, 'come-arrivare')
    lis = ''
    for i in s['items']:
        v = L.get(i.get('link', ''), '')
        href = (v.get(lang) or v.get('it', '')) if isinstance(v, dict) else v
        tt = f'<a href="{href}" rel="noopener">{e(i["t"])}</a>' if href else e(i['t'])
        lis += f'<li><strong>{tt}</strong><span>{e(i["d"])}</span></li>'
    out.append(f'<section class="section" aria-labelledby="s-arrivare"><div class="wrap"><div class="section-head"><h2 id="s-arrivare">{e(s["title"])}</h2>{paras(s, "lead")}</div><ul class="items">{lis}</ul>{cta_wa(lang, s)}</div></section>')
    s = sec(t, 'skipass')
    out.append(f'<section class="section" aria-labelledby="s-skipass"><div class="wrap"><div style="max-width:820px"><h2 id="s-skipass" style="margin-bottom:12px">{e(s["title"])}</h2>{paras(s)}</div></div></section>')
    out.append('</main>'); out.append(footer('pinzolo', lang))
    return ''.join(out)

def render_contatti(lang):
    t = page_t('contatti', lang); fp = C['foto_pagine']; c = C['contatti']; so = C['societa']
    out = [head('contatti', lang, t, hero_n=fp['contatti_hero'], extra_ld=[jsonld_faq(t)]), header('contatti', lang), '<main id="main">']
    out.append(hero(fp['contatti_hero'], lang, t, sub=True, pos='100% 25%'))
    out.append(crumbs('contatti', lang, t))
    s = sec(t, 'contatti')
    lst = (f'<ul class="contact-list">'
           f'<li><span class="label">{e(ui(lang, "cell_label"))}</span><a href="tel:{c["cellulare_tel"]}">{e(c["cellulare"])}</a></li>'
           f'<li><span class="label">WhatsApp</span><a href="{wa_link(lang)}" rel="noopener">{e(ui(lang, "whatsapp"))}</a></li>'
           f'<li><span class="label">{e(ui(lang, "phone_label"))}</span><a href="tel:{c["fisso_tel"]}">{e(c["fisso"])}</a></li>'
           f'<li><span class="label">{e(ui(lang, "email_label"))}</span><a href="mailto:{c["email"]}">{e(c["email"])}</a></li>'
           f'<li><span class="label">{e(ui(lang, "address_label"))}</span><span class="value">{e(c["via"])}, {e(c["cap"])} {e(c["citta"])} ({e(c["provincia"])})</span></li></ul>')
    s2 = sec(t, 'prenotare')
    out.append(f'<section class="section" style="padding-top:40px" aria-labelledby="s-contatti"><div class="wrap grid-2" style="align-items:start"><div><h2 id="s-contatti" style="margin-bottom:12px">{e(s["title"])}</h2>{paras(s)}<div style="margin-top:22px">{lst}</div></div><div><h2 style="margin-bottom:12px">{e(s2["title"])}</h2>{paras(s2)}{items_list(s2)}<p style="margin-top:22px">{book_btn(lang)}</p></div></div></section>')
    s = sec(t, 'dove-siamo')
    out.append(f'<section class="section" aria-labelledby="s-dove"><div class="wrap grid-2">{foto_dove(fp["contatti_dove"], lang, "(min-width: 860px) 560px, 100vw")}<div><h2 id="s-dove" style="margin-bottom:12px">{e(s["title"])}</h2>{paras(s)}<p style="margin-top:18px"><a class="btn btn-line" href="{c["maps"]}" rel="noopener">{e(s["cta"] or ui(lang, "open_maps"))}</a></p></div></div></section>')
    if t.get('faq'):
        qs = ''.join(f'<details><summary>{e(q["q"])}</summary><p>{linkify(e(q["a"]))}{int_link(lang, q)}</p></details>' for q in t['faq'])
        out.append(f'<section class="section faq" aria-labelledby="s-faq"><div class="wrap"><div style="max-width:860px"><h2 id="s-faq" style="margin-bottom:18px">{e(FAQ_TITLE.get(lang, "FAQ"))}</h2>{qs}</div></div></section>')
    s = sec(t, 'societa')
    out.append(f'<section class="section" aria-labelledby="s-societa"><div class="wrap"><div style="max-width:860px"><h2 id="s-societa" style="margin-bottom:12px;font-size:clamp(24px,2.6vw,32px)">{e(s["title"])}</h2><p>{e(so["ragione"])}<br>{e(c["via"])}, {e(c["cap"])} {e(c["citta"])} ({e(c["provincia"])})<br>{e(ui(lang, "company_vat"))} {e(so["piva"])} · {e(ui(lang, "company_rea"))} {e(so["rea"])} · {e(ui(lang, "company_cin"))} {e(so["cin"])}</p></div></div></section>')
    out.append('</main>'); out.append(footer('contatti', lang))
    return ''.join(out)

FAQ_TITLE = {'it': 'Domande frequenti', 'en': 'Frequently asked questions', 'pl': 'Najczęściej zadawane pytania'}

# dove il testo legale nomina l'altra pagina, il nome diventa un collegamento
RIMANDI = {'privacy': ('cookie', {'it': r'pagina Cookie', 'en': r'Cookies page', 'pl': r'„Pliki cookie”'}),
           'cookie': ('privacy', {'it': r'informativa privacy', 'en': r'privacy policy', 'pl': r'polity(?:ka|ce) prywatności'})}

def render_legale(page, lang):
    t = page_t(page, lang)
    dest, rx = RIMANDI[page][0], RIMANDI[page][1][lang]
    def lk(h):
        return re.sub(rx, lambda m: f'<a href="{url(dest, lang)}">{m.group(0)}</a>', linkify(h))
    out = [head(page, lang, t), header(page, lang), '<main id="main" class="legal-page">' + crumbs(page, lang, t) + '<div class="wrap prose">']
    out.append(f'<h1>{e(t["h1"])}</h1><p class="lead">{lk(e(t["lead"]))}</p>')
    for s in t.get('sections', []):
        if s.get('id') == 'dati':
            ps = ''
            for para in s.get('paragraphs', []):
                m = re.match(r'^([^.]{3,45}\.)\s+(.*)$', para)
                ps += (f'<p><strong>{e(m.group(1))}</strong> {lk(e(m.group(2)))}</p>' if m else f'<p>{lk(e(para))}</p>')
            out.append(f'<h2>{e(s["title"])}</h2>{ps}')
        else:
            out.append(f'<h2>{e(s["title"])}</h2>' + ''.join(f'<p>{lk(e(p))}</p>' for p in s.get('paragraphs', []) if p.strip()))
        if s.get('items'):
            out.append(items_list(s))
        if s.get('tabella'):
            tb = s['tabella']
            testa = ''.join(f'<th scope="col">{e(x)}</th>' for x in tb['testa'])
            righe = ''.join('<tr>' + ''.join(f'<td data-col="{e(tb["testa"][i])}">{lk(e(c))}</td>' for i, c in enumerate(r)) + '</tr>' for r in tb['righe'])
            out.append(f'<div class="tabella"><table><thead><tr>{testa}</tr></thead><tbody>{righe}</tbody></table></div>')
        if s.get('dopo'):
            out.append(''.join(f'<p>{lk(e(x))}</p>' for x in s['dopo']))
    out.append('</div></main>'); out.append(footer(page, lang))
    return ''.join(out)

def link_date(lang, label, dal, al, cls='btn', adulti=2):
    """Bottone che apre il motore su date fisse (lo script aggiunge le date e i parametri della campagna)."""
    return f'<a class="{cls}" href="{book_href(lang)}" data-book data-adults="{adulti}" data-dal="{dal}" data-al="{al}">{ICON["cal"]}{e(label)}</a>'

def render_offerta(page, lang):
    t = page_t(page, lang); o = C['offerte'][page]
    btns = ''.join(link_date(lang, d['etichetta'], d['dal'], d['al'], cls='btn' if i == 0 else 'btn btn-line') for i, d in enumerate(o['date']))
    out = [head(page, lang, t, hero_n=o['foto'], noindex=True, evento={'nome': 'ViewContent', 'dati': {'content_name': o['nome_evento']}}),
           header(page, lang), '<main id="main">']
    out.append(hero(o['foto'], lang, t, pos=o.get('pos', '50% 50%'), cta_html=btns))
    s = sec(t, 'perche')
    lis = ''.join(f'<li><h3>{e(i["t"])}</h3><p>{linkify(e(i["d"]))}</p></li>' for i in s['items'])
    out.append(f'<section class="section" aria-labelledby="s-perche"><div class="wrap"><div class="section-head center">{kicker(s.get("kicker", ""))}<h2 id="s-perche">{e(s["title"])}</h2></div><ul class="facts">{lis}</ul></div></section>')
    strip = ''.join(f'<figure class="figure" style="--ratio:4/3">{picture(n, lang, sizes="(min-width: 860px) 380px, 100vw")}</figure>' for n in o['foto_striscia'])
    out.append(f'<section class="section" style="padding-top:0" aria-label="{e(ui(lang, "gallery_label"))}"><div class="wrap"><div class="strip-3">{strip}</div></div></section>')
    s = sec(t, 'prenota')
    out.append(f'<section class="section" aria-labelledby="s-prenota"><div class="wrap narrow"><h2 id="s-prenota" style="margin-bottom:14px">{e(s["title"])}</h2>{paras(s)}<div class="cta" style="margin-top:22px">{btns}<a class="btn btn-line" href="{wa_link(lang)}" rel="noopener">{ICON["wa"]}{e(ui(lang, "whatsapp"))}</a></div></div></section>')
    out.append('</main>'); out.append(footer(page, lang))
    return ''.join(out)

RENDER = {'home': render_home, 'camere': render_camere, 'colazione': render_colazione, 'pinzolo': render_pinzolo, 'contatti': render_contatti, 'privacy': lambda l: render_legale('privacy', l), 'cookie': lambda l: render_legale('cookie', l),
          'offerta-dicembre': lambda l: render_offerta('offerta-dicembre', l)}

# ---------------------------------------------------------------- logo e icone
def logo_files():
    from PIL import Image
    global LOGO_W128, LOGO_W256
    src = os.path.join(S, 'logo-maffei.png')
    d = os.path.join(R, 'img', 'logo'); os.makedirs(d, exist_ok=True)
    lg = Image.open(src).convert('RGBA')
    for h in (128, 256):
        w = round(lg.width * h / lg.height)
        r = lg.resize((w, h), Image.LANCZOS)
        r.save(os.path.join(d, f'logo-maffei-{h}.png'), optimize=True)
        r.save(os.path.join(d, f'logo-maffei-{h}.webp'), 'WEBP', quality=88, method=6)
        if h == 128: LOGO_W128 = w
        else: LOGO_W256 = w
    def square(size, bg=(243, 241, 235, 255), pad=0.08):
        canvas = Image.new('RGBA', (size, size), bg)
        inner = round(size * (1 - 2 * pad))
        w = round(lg.width * inner / lg.height)
        x = lg.resize((w, inner), Image.LANCZOS)
        canvas.paste(x, ((size - w) // 2, (size - inner) // 2), x)
        return canvas
    square(180).convert('RGB').save(os.path.join(d, 'apple-touch-icon.png'), optimize=True)
    square(192).save(os.path.join(d, 'icona-192.png'), optimize=True)
    square(64, pad=0.02).save(os.path.join(R, 'favicon.ico'), sizes=[(16, 16), (32, 32), (48, 48)])

LOGO_W128 = LOGO_W256 = 0

# ---------------------------------------------------------------- file di servizio
def tipografia_pl(h):
    """Solo nel testo visibile (non in script e stili): spazio fisso dopo le parole di una lettera."""
    parti = re.split(r'(<script.*?</script>|<style.*?</style>)', h, flags=re.S)
    def testo(m):
        t = re.sub(r'(?<=[\s(>\u00a0])([aiouwzAIOUWZ]) ', '\\1\u00a0', m.group(0))
        t = re.sub(r'(?<=[\s(>\u00a0])([aiouwzAIOUWZ]) ', '\\1\u00a0', t)
        t = re.sub(r'(?<=\d) (?=[^\W\d_])', '\u00a0', t)
        t = re.sub(r'\b(art\.|ust\.|lit\.|np\.) ', '\\1\u00a0', t)
        return re.sub(r'\b(e-mail\w*)', r'<span class="nowrap">\1</span>', t)
    return ''.join(x if x.startswith(('<script', '<style')) else re.sub(r'>[^<]+<', testo, x) for x in parti)

def tipografia_pl_body(h):
    i = h.find('<body>')
    return h if i < 0 else h[:i] + tipografia_pl(h[i:])

def write(rel, text):
    p = os.path.join(R, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'w', encoding='utf-8').write(text)

def sitemap():
    rows = []
    for page in C['pagine']:
        for lang in LANGS:
            alts = ''.join(f'<xhtml:link rel="alternate" hreflang="{l}" href="{absu(page, l)}"/>' for l in LANGS)
            alts += f'<xhtml:link rel="alternate" hreflang="x-default" href="{absu(page, "it")}"/>'
            rows.append(f'<url><loc>{absu(page, lang)}</loc><lastmod>{OGGI}</lastmod>{alts}</url>')
    write('sitemap.xml', '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n' + '\n'.join(rows) + '\n</urlset>\n')
    write('robots.txt', f'User-agent: *\nAllow: /\nDisallow: /_sorgenti/\n\nSitemap: {DOM}/sitemap.xml\n')

def redirects():
    for old, new in C['reindirizzi'].items():
        target = '/' + new
        write(old + 'index.html', f'<!DOCTYPE html><html lang="it"><head><meta charset="utf-8"><title>Hotel Garnì Maffei</title><meta name="robots" content="noindex"><link rel="canonical" href="{DOM}{target}"><meta http-equiv="refresh" content="0; url={target}"></head><body><p><a href="{target}">{DOM}{target}</a></p></body></html>\n')

def notfound():
    t = {'meta_title': ui('it', 'notfound_title') + ' – ' + C['nome'], 'meta_description': ui('it', 'notfound_text'), 'h1': ui('it', 'notfound_title')}
    links = ' · '.join(f'<a href="{url("home", l)}" lang="{l}">{e(ui(l, "notfound_back"))}</a>' for l in LANGS)
    altre = ''.join(f'<p lang="{l}"><strong>{e(ui(l, "notfound_title"))}.</strong> {e(ui(l, "notfound_text"))}</p>' for l in LANGS if l != 'it')
    body = (head('home', 'it', t).replace(f'<link rel="canonical" href="{absu("home", "it")}">', '<meta name="robots" content="noindex">')
            + header('home', 'it') + f'<main id="main" class="legal-page"><div class="wrap prose"><h1>{e(ui("it", "notfound_title"))}</h1><p class="lead">{e(ui("it", "notfound_text"))}</p>{altre}<p>{links}</p><p style="margin-top:22px">{book_btn("it")}</p></div></main>' + footer('home', 'it'))
    write('404.html', body)

def main():
    logo_files()
    n = 0
    for page in C['pagine']:
        for lang in LANGS:
            h = RENDER[page](lang)
            write(C['slug'][page][lang] + 'index.html', tipografia_pl_body(h) if lang == 'pl' else h); n += 1
    for page in C.get('pagine_offerte', []):
        for lang in C['slug'][page]:
            h = RENDER[page](lang)
            write(C['slug'][page][lang] + 'index.html', tipografia_pl_body(h) if lang == 'pl' else h); n += 1
    sitemap(); redirects(); notfound()
    print(f'{n} pagine generate')

if __name__ == '__main__':
    main()
