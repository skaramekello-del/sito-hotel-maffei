(function () {
  var src = document.currentScript.src.split('?')[0];
  var base = src.replace(/\.js$/, '/');
  function loadModule(path) {
    var s = document.createElement('script');
    s.type = 'module';
    s.src = base + path;
    document.head.appendChild(s);
  }
  loadModule('polyfills.js');
  loadModule('main.js');
})();
