// Nearfront — shared progressive-enhancement script.
// Content is fully visible without JS; this only adds motion + the mobile menu.
(function () {
  var root = document.documentElement;

  // Mobile nav toggle
  var toggle = document.querySelector('.nav-toggle');
  var menu = document.getElementById('nav-menu');
  if (toggle && menu) {
    toggle.addEventListener('click', function () {
      var open = menu.classList.toggle('open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }

  // The .fade-up entrance is a pure CSS load animation (see site.css); it needs
  // no JS and always ends in the visible state, so nothing to do here.
})();
