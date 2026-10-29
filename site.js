(function () {
  'use strict';
  var CFG = window.__SITE__ || {};
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var HEADER_OFFSET = 84;

  function ready(fn) {
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }
  function scrollToEl(el) {
    var y = el.getBoundingClientRect().top + window.scrollY - HEADER_OFFSET;
    window.scrollTo({ top: y, behavior: reduce ? 'auto' : 'smooth' });
  }

  ready(function () {
    /* ── «Записаться»: на телефоне сразу звонок, на компьютере — к блоку с телефоном ── */
    if (CFG.tel && window.matchMedia('(pointer: coarse)').matches) {
      document.querySelectorAll('[data-book]').forEach(function (a) { a.setAttribute('href', CFG.tel); });
    }
    if (CFG.bookingUrl) {
      document.querySelectorAll('[data-book]').forEach(function (a) {
        a.setAttribute('href', CFG.bookingUrl); a.target = '_blank'; a.rel = 'noopener';
      });
    }

    /* ── Мобильное меню ── */
    var btn = document.querySelector('[data-menu-btn]');
    var menu = document.querySelector('[data-menu]');
    if (btn && menu) {
      var label = document.querySelector('[data-menu-label]');
      var iOpen = document.querySelector('[data-menu-icon-open]');
      var iClose = document.querySelector('[data-menu-icon-close]');
      var setMenu = function (open, returnFocus) {
        btn.setAttribute('aria-expanded', String(open));
        menu.classList.toggle('hidden', !open);
        iOpen.classList.toggle('hidden', open);
        iClose.classList.toggle('hidden', !open);
        label.textContent = open ? 'Закрыть меню' : 'Открыть меню';
        if (open) { var a = menu.querySelector('a'); if (a) a.focus(); }
        else if (returnFocus) btn.focus();
      };
      btn.addEventListener('click', function () { setMenu(btn.getAttribute('aria-expanded') !== 'true', false); });
      menu.querySelectorAll('[data-menu-link]').forEach(function (a) {
        a.addEventListener('click', function () { setMenu(false, false); });
      });
      document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && btn.getAttribute('aria-expanded') === 'true') setMenu(false, true);
      });
      document.addEventListener('click', function (e) {
        if (btn.getAttribute('aria-expanded') === 'true' && !menu.contains(e.target) && !btn.contains(e.target)) setMenu(false, false);
      });
      window.matchMedia('(min-width: 1024px)').addEventListener('change', function (m) { if (m.matches) setMenu(false, false); });
    }

    /* ── Прайс: категория и аккордеоны ── */
    var list = document.querySelector('[data-price-list]');
    var status = document.querySelector('[data-cat-status]');
    var groups = list ? Array.prototype.slice.call(list.querySelectorAll('details[data-group]')) : [];
    var catButtons = document.querySelectorAll('[data-cat-switch] [data-set-cat]');
    var catLabels = { master: 'Мастер', top: 'Топ-мастер' };

    function available(g, cat) { var only = g.getAttribute('data-only'); return !only || only === cat; }
    function setCategory(cat, announce) {
      if (!list) return;
      list.setAttribute('data-view', cat);
      catButtons.forEach(function (b) { b.setAttribute('aria-pressed', String(b.getAttribute('data-set-cat') === cat)); });
      // открытая группа сохраняется, если доступна; иначе раскрываем первую
      var anyOpen = groups.some(function (g) { return g.open && available(g, cat); });
      if (!anyOpen && groups[0]) groups[0].open = true;
      if (announce && status) status.textContent = 'Показаны цены: ' + catLabels[cat];
    }
    function openOnly(id) {
      groups.forEach(function (g) { g.open = g.getAttribute('data-group') === id; });
    }
    document.querySelectorAll('[data-set-cat]').forEach(function (b) {
      b.addEventListener('click', function () {
        setCategory(b.getAttribute('data-set-cat'), true);
        var open = b.getAttribute('data-open');
        if (open) {
          openOnly(open);
          var target = document.getElementById('group-' + open);
          if (target) { target.querySelector('summary').focus({ preventScroll: true }); scrollToEl(target); }
        }
      });
    });
    setCategory('master', false);

    /* ── Карточки направлений ведут к своей группе прайса ── */
    document.querySelectorAll('[data-open-group]').forEach(function (a) {
      a.addEventListener('click', function (e) {
        var id = a.getAttribute('data-open-group');
        var target = document.getElementById('group-' + id);
        if (!target) return;
        e.preventDefault();
        var cat = a.getAttribute('data-cat');
        if (cat) setCategory(cat, true);
        else if (!available(target, list.getAttribute('data-view'))) setCategory(target.getAttribute('data-only'), true);
        openOnly(id);
        scrollToEl(target);
        target.querySelector('summary').focus({ preventScroll: true });
        if (history.replaceState) history.replaceState(null, '', '#group-' + id);
      });
    });

    /* ── Галерея работ: просмотр крупнее ── */
    var dlg = document.querySelector('[data-lightbox-dialog]');
    if (dlg && typeof dlg.showModal === 'function') {
      var dImg = dlg.querySelector('[data-lightbox-img]');
      var opener = null;
      document.querySelectorAll('[data-lightbox]').forEach(function (b) {
        b.addEventListener('click', function () {
          var im = b.querySelector('img');
          opener = b; dImg.src = im.currentSrc || im.src; dImg.alt = im.alt;
          dlg.showModal(); dlg.querySelector('[data-lightbox-close]').focus();
        });
      });
      dlg.querySelector('[data-lightbox-close]').addEventListener('click', function () { dlg.close(); });
      dlg.addEventListener('click', function (e) { if (e.target === dlg) dlg.close(); });
      dlg.addEventListener('close', function () { if (opener) opener.focus(); });
    }

    /* ── Мягкое появление секций (один раз, 14px, ~350 мс) ── */
    if (!reduce && 'IntersectionObserver' in window && Element.prototype.animate) {
      var els = Array.prototype.slice.call(document.querySelectorAll('[data-reveal]')).filter(function (el) {
        return el.getBoundingClientRect().top > window.innerHeight;
      });
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) {
          if (!en.isIntersecting) return;
          io.unobserve(en.target);
          en.target.animate(
            [{ opacity: 0, transform: 'translateY(14px)' }, { opacity: 1, transform: 'none' }],
            { duration: 350, easing: 'cubic-bezier(.2,.7,.3,1)', fill: 'backwards' }
          );
        });
      }, { rootMargin: '0px 0px -6% 0px' });
      els.forEach(function (el) { io.observe(el); });
    }

    /* ── Lenis (выключен по умолчанию) ── */
    if (CFG.smoothScroll && !reduce) {
      var s = document.createElement('script');
      s.src = 'https://cdn.jsdelivr.net/npm/lenis@1.1.13/dist/lenis.min.js';
      s.onload = function () {
        if (!window.Lenis) return;
        var lenis = new window.Lenis({ lerp: 0.12 });
        document.documentElement.style.scrollBehavior = 'auto';
        (function raf(t) { lenis.raf(t); requestAnimationFrame(raf); })(0);
      };
      document.head.appendChild(s);
    }
  });
})();
