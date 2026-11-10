// Three small jobs: popovers (open, Escape closes, focus returns) and the first-visit hint (the one-screen switch comes with the Case view).
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
  });
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    document.querySelectorAll('.popover:not([hidden])').forEach(close);
  });
  // Case view: show plain 403 and 409 messages, and focus the next thing to do after a swap.
  document.addEventListener('htmx:beforeSwap', function (e) {
    var st = e.detail.xhr.status;
    if (st === 403 || st === 404 || st === 409) { e.detail.shouldSwap = true; e.detail.isError = false; }
  });
  document.addEventListener('htmx:afterSettle', function (e) {
    var c = e.target;
    if (!c || c.id !== 'case') return;
    var live = document.getElementById('live'), bar = document.getElementById('bar-text');
    if (live && bar) live.textContent = bar.textContent;
    (c.querySelector('[data-focus]') || c.querySelector('button.primary:not([disabled]), a.primary') || c).focus();
  });
  var hint = document.getElementById('hint');
  try {
    if (hint && !sessionStorage.getItem('hint-seen')) { hint.hidden = false; sessionStorage.setItem('hint-seen', '1'); }
  } catch (err) { /* storage blocked: no hint */ }
  function hideHint() { if (hint) hint.hidden = true; }
  var dismiss = document.getElementById('hint-dismiss');
  if (dismiss) dismiss.addEventListener('click', hideHint);
  document.addEventListener('keydown', hideHint, { once: true });
})();
