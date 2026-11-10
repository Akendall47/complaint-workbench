// Three small jobs: popovers (open, Escape closes, focus returns), the one-screen switch, the first-visit hint.
(function () {
  var opener = null;
  function close(el) {
    el.hidden = true;
    var b = document.querySelector('[data-open="' + el.id + '"]');
    if (b) b.setAttribute('aria-expanded', 'false');
    if (opener) opener.focus();
    opener = null;
  }
  document.addEventListener('click', function (e) {
    var open = e.target.closest('[data-open]'), shut = e.target.closest('[data-close]');
    if (open) {
      var el = document.getElementById(open.getAttribute('data-open'));
      if (!el.hidden) return close(el);
      opener = open; el.hidden = false; open.setAttribute('aria-expanded', 'true');
      (el.querySelector('button') || el).focus();
    } else if (shut) {
      close(document.getElementById(shut.getAttribute('data-close')));
    }
    var sw = e.target.closest('[data-one-screen]');
    if (sw) {
      var on = sw.getAttribute('aria-pressed') !== 'true';
      sw.setAttribute('aria-pressed', String(on));
      document.body.classList.toggle('one-screen', on);
    }
  });
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    document.querySelectorAll('.popover:not([hidden])').forEach(close);
  });
  var hint = document.getElementById('hint');
  try {
    if (hint && !sessionStorage.getItem('hint-seen')) { hint.hidden = false; sessionStorage.setItem('hint-seen', '1'); }
  } catch (err) { /* storage blocked: no hint */ }
})();
