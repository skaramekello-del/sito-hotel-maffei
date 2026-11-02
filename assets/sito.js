/* Hotel Garnì Maffei — piccoli comportamenti del sito (il pixel di Meta parte solo dopo "Accetta") */
(function () {
  var doc = document.documentElement;
  doc.classList.remove('no-js');
  doc.classList.add('js');
  var cfg = window.MAFFEI || {};

  // Menu sul telefono
  var btn = document.querySelector('.menu-btn');
  var nav = document.getElementById('nav');
  if (btn && nav) {
    btn.addEventListener('click', function () {
      var open = nav.classList.toggle('open');
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }

  // Stagione del sito (la sceglie lo script in testa alla pagina; i bottoni Inverno/Estate la cambiano per la visita)
  function stagione() { return doc.classList.contains('st-estate') ? 'estate' : 'inverno'; }
  function tipo(s) { var m = +s[0].split('-')[1]; return (m >= 5 && m <= 10) ? 'estate' : 'inverno'; }

  // Date proposte alla prenotazione: il primo sabato utile dentro una stagione aperta del tipo scelto, 7 notti
  function iso(d) { return d.toISOString().slice(0, 10); }
  function parse(s) { var p = s.split('-'); return new Date(Date.UTC(+p[0], +p[1] - 1, +p[2])); }
  function proposta() {
    var oggi = new Date(); oggi = new Date(Date.UTC(oggi.getFullYear(), oggi.getMonth(), oggi.getDate()));
    var domani = new Date(oggi.getTime() + 864e5);
    var stagioni = cfg.stagioni || [];
    for (var i = 0; i < stagioni.length; i++) {
      if (tipo(stagioni[i]) !== stagione()) continue;
      var da = parse(stagioni[i][0]), a = parse(stagioni[i][1]);
      if (a < domani) continue;
      var d = da > domani ? da : domani;
      while (d.getUTCDay() !== 6) d = new Date(d.getTime() + 864e5);
      var fine = new Date(d.getTime() + 7 * 864e5);
      if (fine <= new Date(a.getTime() + 864e5)) return [iso(d), iso(fine)];
    }
    return null;
  }
  function b64(s) { try { return btoa(unescape(encodeURIComponent(s))); } catch (e) { return ''; } }
  // Parametri della campagna (utm_*, fbclid, gclid): dai link Prenota passano al motore Beddy (la barra Beddy lo fa da se').
  // Senza consenso si passano solo quelli dell'indirizzo di questa pagina; con il consenso si ricordano per la visita.
  function campagna() {
    var out = [];
    window.location.search.slice(1).split('&').forEach(function (p) {
      var k = decodeURIComponent(p.split('=')[0] || '');
      if (/^utm_/.test(k) || k === 'fbclid' || k === 'gclid') out.push(p);
    });
    if (cfg.consenso === 'si') {
      try {
        if (out.length) window.sessionStorage.setItem('maffei-utm', out.join('&'));
        else return window.sessionStorage.getItem('maffei-utm') || '';
      } catch (e) { /* niente */ }
    }
    return out.join('&');
  }
  function dateUpd() {
    var date = cfg.widget ? proposta() : null, par = campagna();
    var links = document.querySelectorAll('a[data-book]');
    for (var j = 0; j < links.length; j++) {
      var a = links[j];
      if (!a.hasAttribute('data-href0')) a.setAttribute('data-href0', a.getAttribute('href'));
      // i bottoni delle offerte hanno date fisse
      var d = a.getAttribute('data-dal') ? [a.getAttribute('data-dal'), a.getAttribute('data-al')] : date;
      var h = a.getAttribute('data-href0');
      if (d && cfg.widget) {
        var adulti = parseInt(a.getAttribute('data-adults') || '2', 10);
        var q = { booking_widget_code: cfg.widget, date_from: d[0], date_to: d[1], currency: 'EUR', lang: cfg.bookLang || 'it', coupon_code: null, rooms: [{ adults: adulti, children: [] }], searchOrigin: 'beddybar', unlock_key: [] };
        var enc = b64(JSON.stringify(q));
        if (enc) h = cfg.engine + '?search=' + encodeURIComponent(enc) + '&lang=' + (cfg.bookLang || 'it');
      }
      if (par) h += (h.indexOf('?') < 0 ? '?' : '&') + par;
      a.setAttribute('href', h);
    }
  }
  dateUpd();

  // Bottoni Inverno/Estate
  var stBtns = document.querySelectorAll('[data-stagione]');
  function stUpd() {
    for (var k = 0; k < stBtns.length; k++) stBtns[k].setAttribute('aria-pressed', stBtns[k].getAttribute('data-stagione') === stagione() ? 'true' : 'false');
  }
  for (var k = 0; k < stBtns.length; k++) stBtns[k].addEventListener('click', function () {
    var s = this.getAttribute('data-stagione');
    doc.classList.remove('st-inverno', 'st-estate');
    doc.classList.add('st-' + s);
    try { window.sessionStorage.setItem('maffei-stagione', s); } catch (e) { /* niente */ }
    stUpd(); dateUpd();
  });
  stUpd();

  // Gallerie delle camere
  var gals = document.querySelectorAll('.gallery');
  for (var g = 0; g < gals.length; g++) (function (gal) {
    var track = gal.querySelector('.gallery-track');
    var prev = gal.querySelector('[data-prev]'), next = gal.querySelector('[data-next]');
    var count = gal.querySelector('.gallery-count');
    var n = track ? track.children.length : 0;
    function idx() { return Math.round(track.scrollLeft / track.clientWidth); }
    function upd() { if (count) count.textContent = (idx() + 1) + ' / ' + n; }
    function go(k) { track.scrollTo({ left: k * track.clientWidth, behavior: 'smooth' }); }
    if (prev) prev.addEventListener('click', function () { go(Math.max(0, idx() - 1)); });
    if (next) next.addEventListener('click', function () { go(Math.min(n - 1, idx() + 1)); });
    if (track) track.addEventListener('scroll', function () { window.requestAnimationFrame(upd); }, { passive: true });
    upd();
  })(gals[g]);

  // Consenso: "Accetta" carica il pixel di Meta; "Rifiuta", o nessuna scelta, non manda nulla a Meta.
  // La scelta resta sul dispositivo con data e versione della pagina Cookie (la legge lo script in testa alla pagina).
  function salva(s) {
    cfg.consenso = s;
    try {
      window.localStorage.setItem('maffei-consenso', JSON.stringify({ s: s, t: Date.now(), v: cfg.consensoVer }));
      window.localStorage.removeItem('maffei-cookie-ok');
    } catch (e) { /* niente */ }
  }
  function pixel() {
    if (!cfg.pixel || window.fbq) return;
    /* codice base del pixel di Meta */
    !function (f, b, e, v, n, t, s) {
      if (f.fbq) return; n = f.fbq = function () { n.callMethod ? n.callMethod.apply(n, arguments) : n.queue.push(arguments); };
      if (!f._fbq) f._fbq = n; n.push = n; n.loaded = !0; n.version = '2.0'; n.queue = [];
      t = b.createElement(e); t.async = !0; t.src = v; s = b.getElementsByTagName(e)[0]; s.parentNode.insertBefore(t, s);
    }(window, document, 'script', 'https://connect.facebook.net/en_US/fbevents.js');
    window.fbq('init', cfg.pixel);
    window.fbq('track', 'PageView');
    if (cfg.evento) window.fbq('track', cfg.evento.nome, cfg.evento.dati || {});
  }
  function togliPixel() {
    if (window.fbq) window.fbq('consent', 'revoke');
    var host = window.location.hostname, dom = host.split('.').slice(-2).join('.');
    ['_fbp', '_fbc'].forEach(function (n) {
      document.cookie = n + '=; Max-Age=0; path=/';
      [host, '.' + host, dom, '.' + dom].forEach(function (d) { document.cookie = n + '=; Max-Age=0; path=/; domain=' + d; });
    });
    try { window.sessionStorage.removeItem('maffei-utm'); } catch (e) { /* niente */ }
  }
  if (cfg.consenso === 'si') pixel();
  var ck = document.querySelector('.cookie');
  if (ck) {
    var scelte = ck.querySelectorAll('[data-consenso]');
    for (var c = 0; c < scelte.length; c++) scelte[c].addEventListener('click', function () {
      var s = this.getAttribute('data-consenso');
      salva(s);
      doc.classList.add('ck-ok');
      if (s === 'si') { if (window.fbq) window.fbq('consent', 'grant'); pixel(); } else togliPixel();
      dateUpd(); fabUpd();
    });
  }
  // "Preferenze cookie" in fondo alla pagina: il banner torna visibile
  var pref = document.querySelectorAll('[data-cookie-pref]');
  for (var p = 0; p < pref.length; p++) pref[p].addEventListener('click', function () {
    doc.classList.remove('ck-ok');
    window.scrollTo(0, 0);
    var b = ck && ck.querySelector('[data-consenso]');
    if (b) b.focus({ preventScroll: true });
    fabUpd();
  });
  // Evento per il pixel (solo se caricato): clic sui bottoni Prenota del sito e sulla ricerca della barra Beddy
  document.addEventListener('click', function (ev) {
    if (!window.fbq || cfg.consenso !== 'si') return;
    var path = ev.composedPath ? ev.composedPath() : [ev.target];
    for (var i = 0; i < path.length; i++) {
      var el = path[i];
      if (!el || !el.getAttribute) continue;
      var orig = el.hasAttribute('data-book') ? 'bottone' : (el.classList && el.classList.contains('by-beddy-bar-ui__search-button') ? 'barra' : '');
      if (orig) { window.fbq('trackCustom', 'ClicPrenota', { origine: orig, pagina: window.location.pathname }); return; }
    }
  }, true);

  // Bottone tondo di WhatsApp (Home): nascosto mentre il bottone WhatsApp dell'apertura si vede sopra la barra in basso
  // (nostra 65 px, Beddy fino a 90 px); se ricompare dove coprirebbe i bottoni dell'apertura, sale sopra di loro
  var waH = document.querySelector('.hero .cta .btn-line'), bookH = document.querySelector('.hero .cta [data-book]');
  var fab = document.querySelector('.wa-fab');
  function fabUpd() {
    if (!waH || !fab) return;
    var h = window.innerHeight, w = waH.getBoundingClientRect(), b = bookH ? bookH.getBoundingClientRect() : w;
    var f = fab.getBoundingClientRect(), giu = h - parseFloat(window.getComputedStyle(fab).bottom), su = giu - f.height;
    var barra = doc.classList.contains('beddy-ready') ? 90 : 65;
    var visto = Math.min(w.bottom, h - barra) - Math.max(w.top, 0) >= w.height * 0.75;
    var alto = Math.min(w.top, b.top), basso = Math.max(w.bottom, b.bottom);
    var copre = alto < giu && basso > su && Math.min(w.left, b.left) < f.right && Math.max(w.right, b.right) > f.left;
    var sali = !visto && copre ? Math.ceil(giu - alto + 8) : 0;
    doc.classList.toggle('cta-vista', visto || su - sali < 72);
    fab.style.transform = sali && su - sali >= 72 ? 'translateY(-' + sali + 'px)' : '';
  }
  if (waH && fab) {
    fabUpd();
    ['scroll', 'resize', 'load'].forEach(function (ev) { window.addEventListener(ev, fabUpd, { passive: true }); });
  } else {
    doc.classList.remove('cta-vista');
  }

  // Barra Beddy: caricata quando la pagina e' pronta, per non rallentare l'apertura
  function caricaBeddy() {
    if (!cfg.beddyScript || document.querySelector('script[data-beddy]')) return;
    var s = document.createElement('script');
    s.src = cfg.beddyScript; s.charset = 'UTF-8'; s.defer = true; s.setAttribute('data-beddy', '');
    document.head.appendChild(s);
    if (window.customElements && customElements.whenDefined) {
      customElements.whenDefined('beddy-bar').then(function () {
        // Colori del sito nella barra Beddy: sfondo pieno (Beddy lo mette grigio trasparente) e bottone terracotta.
        // Il bottone resta del colore chiaro anche nel tema scuro: le finestre di Beddy sono sempre bianche.
        var bar = document.querySelector('beddy-bar');
        if (bar && bar.shadowRoot) {
          var st = document.createElement('style');
          st.textContent = '*{--footerMaskBgCustomize:var(--surface)!important;--buttonCustomize:#8C3F1F!important;--buttonLighterCustomize:#6F3118!important;' +
            '--buttonFontColorCustomize:#fff!important;--buttonColorHoverCustomize:#fff!important;--borderCustomize:#8C3F1F!important}' +
            '.by-beddy-bar-ui__container{border-top:1px solid var(--line)}';
          bar.shadowRoot.appendChild(st);
        }
        window.setTimeout(function () { doc.classList.add('beddy-ready'); fabUpd(); }, 600);
      });
    }
  }
  // La barra Beddy (con Stripe) pesa circa 1 MB: si carica al primo gesto del visitatore.
  // Fino ad allora c'e' la nostra barra "Verifica prezzi e prenota", che porta allo stesso booking engine.
  ['pointerdown', 'pointermove', 'keydown', 'scroll', 'touchstart', 'focusin'].forEach(function (ev) {
    window.addEventListener(ev, caricaBeddy, { once: true, passive: true });
  });
})();
