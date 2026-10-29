(function () {
  'use strict';
  var CFG = window.__SITE__ || {};
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function ready(fn) {
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }

  ready(function () {
    /* ── Мобильное меню ─────────────────────────── */
    var btn = document.querySelector('[data-menu-btn]');
    var menu = document.querySelector('[data-menu]');
    var label = document.querySelector('[data-menu-label]');
    var iOpen = document.querySelector('[data-menu-icon-open]');
    var iClose = document.querySelector('[data-menu-icon-close]');
    var sticky = document.querySelector('[data-sticky-cta]');

    function setMenu(open, returnFocus) {
      if (!btn || !menu) return;
      btn.setAttribute('aria-expanded', String(open));
      menu.classList.toggle('hidden', !open);
      iOpen.classList.toggle('hidden', open);
      iClose.classList.toggle('hidden', !open);
      label.textContent = open ? 'Закрыть меню' : 'Открыть меню';
      if (sticky) sticky.classList.toggle('invisible', open);
      if (open) {
        var first = menu.querySelector('a');
        if (first) first.focus();
      } else if (returnFocus) {
        btn.focus();
      }
    }
    if (btn) {
      btn.addEventListener('click', function () {
        setMenu(btn.getAttribute('aria-expanded') !== 'true', false);
      });
      menu.querySelectorAll('[data-menu-link]').forEach(function (a) {
        a.addEventListener('click', function () { setMenu(false, false); });
      });
      document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && btn.getAttribute('aria-expanded') === 'true') setMenu(false, true);
      });
      document.addEventListener('click', function (e) {
        if (btn.getAttribute('aria-expanded') === 'true' && !menu.contains(e.target) && !btn.contains(e.target)) setMenu(false, false);
      });
      window.matchMedia('(min-width: 1024px)').addEventListener('change', function (m) {
        if (m.matches) setMenu(false, false);
      });
    }

    /* ── Переключатель категорий прайса (ARIA tabs) ── */
    var tablist = document.querySelector('[data-tabs]');
    if (tablist) {
      var tabs = Array.prototype.slice.call(tablist.querySelectorAll('[role="tab"]'));
      var panels = document.querySelectorAll('[data-panel]');
      var mqDesk = window.matchMedia('(min-width: 768px)');

      function visibleTabs() {
        return tabs.filter(function (t) { return !t.hasAttribute('data-desktop-only') || mqDesk.matches; });
      }
      function select(id, focus) {
        tabs.forEach(function (t) {
          var on = t.getAttribute('data-tab') === id;
          t.setAttribute('aria-selected', String(on));
          t.tabIndex = on ? 0 : -1;
          if (on && focus) t.focus();
        });
        panels.forEach(function (p) { p.hidden = p.getAttribute('data-panel') !== id; });
      }
      tabs.forEach(function (t) {
        t.addEventListener('click', function () { select(t.getAttribute('data-tab'), false); });
        t.addEventListener('keydown', function (e) {
          var list = visibleTabs();
          var i = list.indexOf(t);
          var next = null;
          if (e.key === 'ArrowRight') next = list[(i + 1) % list.length];
          else if (e.key === 'ArrowLeft') next = list[(i - 1 + list.length) % list.length];
          else if (e.key === 'Home') next = list[0];
          else if (e.key === 'End') next = list[list.length - 1];
          if (next) { e.preventDefault(); select(next.getAttribute('data-tab'), true); }
        });
      });
      document.querySelectorAll('[data-switch-tab]').forEach(function (a) {
        a.addEventListener('click', function (e) {
          e.preventDefault();
          select(a.getAttribute('data-switch-tab'), true);
          tablist.scrollIntoView({ block: 'center', behavior: reduce ? 'auto' : 'smooth' });
        });
      });
      mqDesk.addEventListener('change', function (m) {
        if (!m.matches && tablist.querySelector('[data-tab="compare"][aria-selected="true"]')) select('master', false);
      });
      select('master', false);
    }

    /* ── Нижняя кнопка звонка: прячем, пока видны кнопки первого экрана ── */
    if (sticky && 'IntersectionObserver' in window) {
      var heroCta = document.querySelector('#top [data-cta]');
      if (heroCta) {
        new IntersectionObserver(function (entries) {
          var visible = entries[0].isIntersecting;
          sticky.classList.toggle('translate-y-full', visible);
          sticky.setAttribute('aria-hidden', String(visible));
          sticky.querySelectorAll('a').forEach(function (a) { a.tabIndex = visible ? -1 : 0; });
        }, { rootMargin: '0px 0px -40px 0px' }).observe(heroCta);
      }
    }

    /* ── Галерея: просмотр фото крупнее ───────────── */
    var dlg = document.querySelector('[data-lightbox-dialog]');
    if (dlg && typeof dlg.showModal === 'function') {
      var dImg = dlg.querySelector('[data-lightbox-img]');
      var dCap = dlg.querySelector('[data-lightbox-caption]');
      var opener = null;
      document.querySelectorAll('[data-lightbox]').forEach(function (b) {
        b.addEventListener('click', function () {
          var img = b.querySelector('img');
          opener = b;
          dImg.src = img.currentSrc || img.src;
          dImg.alt = img.alt;
          dCap.textContent = img.getAttribute('data-caption') || '';
          dlg.showModal();
          dlg.querySelector('[data-lightbox-close]').focus();
        });
      });
      dlg.querySelector('[data-lightbox-close]').addEventListener('click', function () { dlg.close(); });
      dlg.addEventListener('click', function (e) { if (e.target === dlg) dlg.close(); });
      dlg.addEventListener('close', function () { if (opener) opener.focus(); });
    } else {
      document.querySelectorAll('[data-lightbox]').forEach(function (b) {
        b.removeAttribute('aria-label'); b.setAttribute('tabindex', '-1'); b.style.cursor = 'default';
      });
    }

    /* ── Появление секций: один раз, смещение 16px ── */
    if (!reduce && 'IntersectionObserver' in window) {
      var els = Array.prototype.slice.call(document.querySelectorAll('[data-reveal]')).filter(function (el) {
        return el.getBoundingClientRect().top > window.innerHeight * 0.92;
      });
      els.forEach(function (el) { el.style.opacity = '0'; el.style.transform = 'translateY(16px)'; });
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) {
          if (!en.isIntersecting) return;
          var el = en.target;
          io.unobserve(el);
          if (window.gsap) {
            window.gsap.to(el, { opacity: 1, y: 0, duration: 0.45, ease: 'power2.out', clearProps: 'transform,opacity' });
          } else {
            el.style.transition = 'opacity .45s ease-out, transform .45s ease-out';
            requestAnimationFrame(function () { el.style.opacity = ''; el.style.transform = ''; });
          }
        });
      }, { rootMargin: '0px 0px -8% 0px' });
      els.forEach(function (el) { io.observe(el); });
      // страховка: если что-то пошло не так, не оставляем контент скрытым
      setTimeout(function () {
        els.forEach(function (el) {
          if (el.style.opacity === '0' && el.getBoundingClientRect().top < window.innerHeight) {
            el.style.opacity = ''; el.style.transform = '';
          }
        });
      }, 4000);
    }

    /* ── Плавная прокрутка Lenis (выключена по умолчанию) ── */
    if (CFG.smoothScroll && !reduce) {
      var s = document.createElement('script');
      s.src = 'https://cdn.jsdelivr.net/npm/lenis@1.1.13/dist/lenis.min.js';
      s.onload = function () {
        if (!window.Lenis) return;
        var lenis = new window.Lenis({ lerp: 0.12, smoothWheel: true });
        document.documentElement.style.scrollBehavior = 'auto';
        (function raf(t) { lenis.raf(t); requestAnimationFrame(raf); })(0);
        document.querySelectorAll('a[href^="#"]').forEach(function (a) {
          a.addEventListener('click', function (e) {
            var id = a.getAttribute('href');
            if (id.length < 2 || a.hasAttribute('data-switch-tab')) return;
            var t = document.querySelector(id);
            if (t) { e.preventDefault(); lenis.scrollTo(t, { offset: -88 }); }
          });
        });
      };
      document.head.appendChild(s);
    }
  });
})();
