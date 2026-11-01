/* Hotel Garnì Maffei — piccoli comportamenti del sito (nessun tracciamento) */
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

  // Date proposte alla prenotazione: il primo sabato utile dentro una stagione aperta, 7 notti
  function iso(d) { return d.toISOString().slice(0, 10); }
  function parse(s) { var p = s.split('-'); return new Date(Date.UTC(+p[0], +p[1] - 1, +p[2])); }
  function proposta() {
    var oggi = new Date(); oggi = new Date(Date.UTC(oggi.getFullYear(), oggi.getMonth(), oggi.getDate()));
    var domani = new Date(oggi.getTime() + 864e5);
    var stagioni = cfg.stagioni || [];
    for (var i = 0; i < stagioni.length; i++) {
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
  var date = proposta();
  if (date && cfg.widget) {
    var links = document.querySelectorAll('a[data-book]');
    for (var j = 0; j < links.length; j++) {
      var a = links[j];
      var adulti = parseInt(a.getAttribute('data-adults') || '2', 10);
      var q = { booking_widget_code: cfg.widget, date_from: date[0], date_to: date[1], currency: 'EUR', lang: cfg.bookLang || 'it', coupon_code: null, rooms: [{ adults: adulti, children: [] }], searchOrigin: 'beddybar', unlock_key: [] };
      var enc = b64(JSON.stringify(q));
      if (enc) a.href = cfg.engine + '?search=' + encodeURIComponent(enc) + '&lang=' + (cfg.bookLang || 'it');
    }
  }

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

  // Avviso cookie (solo cookie tecnici: e' un'informativa, non una richiesta di consenso)
  var ck = document.querySelector('.cookie');
  if (ck) {
    var ok = ck.querySelector('button');
    if (ok) ok.addEventListener('click', function () {
      doc.classList.add('ck-ok');
      try { window.localStorage.setItem('maffei-cookie-ok', '1'); } catch (e) { /* niente */ }
      fabUpd();
    });
  }

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
