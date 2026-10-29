"""Проверки собранной страницы в Chromium (Playwright). Запуск: python3 tools/check.py"""
import json, sys, urllib.parse
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
URL = (ROOT / "dist" / "index.html").as_uri()
NB = " "
TEL = "tel:+79897605460"

EXPECTED = {
    "master": {
        "Женская стрижка": "800–1 500 ₽", "Мужская стрижка": "500–800 ₽", "Укладка": "700–1 000 ₽",
        "Причёска": "1 000–1 500 ₽", "Окрашивание": "1 500–4 000 ₽", "Творческие техники": "3 000–7 000 ₽",
        "Буст-ап": "2 500 ₽", "Химическая завивка · женская": "2 500–4 000 ₽",
        "Химическая завивка · мужская": "2 500 ₽", "SPA-процедура": "1 000 ₽",
    },
    "top": {
        "Женская стрижка": "1 500–2 000 ₽", "Мужская стрижка": "800–1 000 ₽", "Укладка": "1 000–1 500 ₽",
        "Причёска": "1 500–2 500 ₽", "Окрашивание": "1 500–5 000 ₽", "Творческие техники": "4 000–15 000 ₽",
        "Буст-ап": "3 000 ₽", "Химическая завивка · женская": "4 000–6 000 ₽",
        "Химическая завивка · мужская": "3 000 ₽", "SPA-процедура": "1 500 ₽", "Макияж": "1 500 ₽", "Брови": "700 ₽",
    },
}
FORBIDDEN = ["Демо", "демо", "индексац", "ждёт материал", "Линии света", "Светлый камень", "AURELIA", "Aurelia",
             "хирург", "врач", "операци", "консультац", "маникюр", "педикюр", "ресниц", "рейтинг", "WhatsApp",
             "Telegram", "max.ru", "официальн", "франшиз", "Санкт-Петербург", "лет опыта", "скидк"]
results, problems = [], []


def ok(cond, msg):
    (results if cond else problems).append(("OK  " if cond else "FAIL") + " " + msg)


def norm(s):
    return " ".join(s.replace(NB, " ").split())


def cclick(page, sel):
    page.eval_on_selector(sel, "e => e.scrollIntoView({block: 'center', behavior: 'instant'})")
    page.wait_for_timeout(150)
    page.click(sel)


def visible_prices(page):
    page.evaluate("document.querySelectorAll('details[data-group]').forEach(d => d.open = true)")
    return page.evaluate("""() => {
        const out = {};
        document.querySelectorAll('[data-price-list] li').forEach(li => {
          if (!li.offsetParent) return;
          const name = li.querySelector('div p').innerText;
          const price = [...li.querySelectorAll('[data-p]')].filter(p => p.offsetParent).map(p => p.innerText).join(' | ');
          out[name] = price;
        });
        return out; }""")


def new_page(browser, width, height, **kw):
    mob = width < 800
    ctx = browser.new_context(viewport={"width": width, "height": height}, device_scale_factor=2 if mob else 1,
                              is_mobile=mob, has_touch=mob, **kw)
    page = ctx.new_page()
    errors = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" and "net::ERR" not in m.text else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.route("**/*", lambda r: r.abort() if r.request.url.startswith("http") else r.continue_())
    page.goto(URL, wait_until="load")
    page.add_style_tag(content="html{scroll-behavior:auto!important}")
    page.wait_for_timeout(200)
    return ctx, page, errors


with sync_playwright() as p:
    browser = p.chromium.launch()
    for width, height in [(360, 740), (390, 844), (768, 1024), (1440, 900)]:
        name = str(width)
        ctx, page, errors = new_page(browser, width, height)

        ov = page.evaluate("[document.documentElement.scrollWidth, document.documentElement.clientWidth]")
        ok(ov[0] <= ov[1], f"{name}: нет горизонтальной прокрутки ({ov[0]} ≤ {ov[1]})")
        ok(page.locator("h1").count() == 1, f"{name}: ровно один H1")
        h1 = page.eval_on_selector("h1", """e => { const r = e.getBoundingClientRect(); const lh = parseFloat(getComputedStyle(e).lineHeight);
            return [Math.round(r.height / lh), parseFloat(getComputedStyle(e).fontSize), r.right <= innerWidth] }""")
        ok(h1[0] <= 4 and h1[2], f"{name}: H1 {h1[1]:.0f}px, {h1[0]} строки, не обрезан")
        cta = page.eval_on_selector("[data-hero-cta]", "e => e.getBoundingClientRect().bottom")
        ok(cta <= height, f"{name}: кнопка «Записаться» в первом экране без прокрутки ({cta:.0f} ≤ {height})")
        fixed = page.evaluate("[...document.querySelectorAll('body *')].filter(e => getComputedStyle(e).position === 'fixed' && e.offsetParent !== null || (getComputedStyle(e).position==='fixed' && getComputedStyle(e).display!=='none')).map(e=>e.className.slice(0,40))")
        ok(not fixed, f"{name}: нет фиксированных плашек и нижней полосы звонка {fixed}")
        hh = page.eval_on_selector("header", "e => e.getBoundingClientRect().height")
        ok(hh <= 80, f"{name}: высота шапки {hh:.0f}px")

        small = page.evaluate("""() => { const out=[]; const w=document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
            while(w.nextNode()){ const n=w.currentNode; if(!n.textContent.trim()) continue; const el=n.parentElement;
              if(el.closest('.sr-only,[hidden],[aria-hidden=true]') || !el.offsetParent) continue;
              const fs=parseFloat(getComputedStyle(el).fontSize); if(fs<13) out.push([fs, n.textContent.trim().slice(0,30)]); } return out; }""")
        ok(not small, f"{name}: нет текста мельче 13px {small[:3]}")
        tiny = page.evaluate("""() => [...document.querySelectorAll('a[class*=min-h], button, summary, [data-open-group]')].filter(e=>{const r=e.getBoundingClientRect(); return r.width>0 && r.height<44}).map(e=>e.innerText.slice(0,30)||e.getAttribute('aria-label'))""")
        ok(not tiny, f"{name}: интерактивные элементы ≥ 44px {tiny}")

        # прайс: обе категории полностью совпадают с источником
        for cat in ("top", "master"):
            cclick(page, f'[data-cat-switch] [data-set-cat="{cat}"]')
            got = {norm(k): norm(v) for k, v in visible_prices(page).items()}
            ok(got == EXPECTED[cat], f"{name}: прайс «{cat}» = источник ({len(got)} строк)" + ("" if got == EXPECTED[cat] else f" got={got}"))
            pressed = page.eval_on_selector(f'[data-cat-switch] [data-set-cat="{cat}"]', "e => e.getAttribute('aria-pressed')")
            ok(pressed == "true", f"{name}: aria-pressed отражает выбор «{cat}»")
        ok(not page.is_visible("#group-makeup"), f"{name}: у «Мастера» группа «Макияж и брови» не показана")
        ok(page.evaluate("document.querySelector('[data-price-list]').innerText.indexOf(' 0 ₽') === -1"), f"{name}: нет цен «0 ₽»")
        overlap = page.evaluate("""() => [...document.querySelectorAll('[data-price-list] li')].filter(li=>li.offsetParent).filter(li=>{
            const a=li.children[0].getBoundingClientRect(), b=li.children[1].getBoundingClientRect();
            return a.right > b.left + 0.5 || b.height > 30; }).map(li=>li.innerText)""")
        ok(not overlap, f"{name}: цены не переносятся и не налезают на названия {overlap[:2]}")

        # аккордеон: одна группа раскрыта изначально; клавиатура; сохранение группы
        page.reload(); page.add_style_tag(content="html{scroll-behavior:auto!important}")
        opened = page.evaluate("[...document.querySelectorAll('details[data-group]')].filter(d=>d.open).map(d=>d.dataset.group)")
        ok(opened == ["cuts"], f"{name}: изначально раскрыта одна группа {opened}")
        page.focus("#group-color summary"); page.keyboard.press("Enter")
        ok(page.evaluate("document.getElementById('group-color').open"), f"{name}: группа раскрывается с клавиатуры (Enter)")
        page.evaluate("document.getElementById('group-cuts').open=false")
        cclick(page, '[data-cat-switch] [data-set-cat="top"]')
        ok(page.evaluate("document.getElementById('group-color').open && document.getElementById('group-color').offsetParent!==null"),
           f"{name}: при смене категории открытая группа сохраняется")
        page.evaluate("document.querySelectorAll('details').forEach(d=>d.open=d.id==='group-makeup')")
        cclick(page, '[data-cat-switch] [data-set-cat="master"]')
        vis_open = page.evaluate("[...document.querySelectorAll('details[data-group]')].filter(d=>d.open && d.offsetParent).map(d=>d.dataset.group)")
        ok(vis_open == ["cuts"], f"{name}: если группа недоступна в категории — раскрывается первая {vis_open}")

        # карточки направлений
        for gid, cat in (("makeup", "top"), ("color", None), ("cuts", None)):
            cclick(page, f'[data-open-group="{gid}"]')
            page.wait_for_timeout(1200)
            st = page.evaluate(f"""() => {{ const d=document.getElementById('group-{gid}'); return [d.open, !!d.offsetParent,
                Math.round(d.getBoundingClientRect().top), document.querySelector('[data-price-list]').dataset.view] }}""")
            ok(st[0] and st[1] and 40 <= st[2] <= 140 and (cat is None or st[3] == cat),
               f"{name}: карточка «{gid}» раскрывает свою группу и прокручивает к ней {st}")

        # меню
        if width < 1024:
            page.evaluate("window.scrollTo(0,0)")
            page.click("[data-menu-btn]")
            ok(page.get_attribute("[data-menu-btn]", "aria-expanded") == "true" and page.is_visible("#mobile-menu")
               and page.evaluate("document.activeElement.closest('#mobile-menu') !== null"), f"{name}: меню открывается, фокус в меню")
            ok(page.locator("#mobile-menu a[href^='tel:']").count() == 1, f"{name}: в меню одна кнопка звонка")
            page.keyboard.press("Escape")
            ok(not page.is_visible("#mobile-menu") and page.evaluate("document.activeElement.hasAttribute('data-menu-btn')"),
               f"{name}: Escape закрывает меню и возвращает фокус")
            page.click("[data-menu-btn]"); page.click('#mobile-menu a[href="#contacts"]'); page.wait_for_timeout(300)
            top = page.eval_on_selector("#contacts", "e => e.getBoundingClientRect().top")
            at_end = page.evaluate("Math.ceil(scrollY + innerHeight) >= document.documentElement.scrollHeight - 1")
            ok(not page.is_visible("#mobile-menu") and (40 <= top <= 110 or (at_end and top > 40)), f"{name}: якорь «Контакты» с учётом шапки (top={top:.0f}, конец страницы={at_end})")
            book = set(page.eval_on_selector_all("[data-book]", "e => e.map(a => a.getAttribute('href'))"))
            ok(book <= {TEL}, f"{name}: на телефоне «Записаться» сразу звонит {book}")
        else:
            page.evaluate("window.scrollTo(0,0)")
            page.click('nav a[href="#prices"]'); page.wait_for_timeout(300)
            top = page.eval_on_selector("#prices", "e => e.getBoundingClientRect().top")
            ok(40 <= top <= 110, f"{name}: якорь «Услуги и цены» с учётом шапки (top={top:.0f})")
            book = set(page.eval_on_selector_all("[data-book]", "e => e.map(a => a.getAttribute('href'))"))
            ok(book == {"#contacts"}, f"{name}: на компьютере «Записаться» ведёт к блоку с телефоном {book}")

        # прокрутка, изображения, появление
        page.evaluate("window.scrollTo(0,0)")
        for y in range(0, page.evaluate("document.body.scrollHeight"), 350):
            page.evaluate(f"window.scrollTo(0,{y})"); page.wait_for_timeout(40)
        page.wait_for_timeout(600)
        imgs = page.evaluate("[...document.images].map(i=>[i.naturalWidth, i.alt.slice(0,25)])")
        ok(len(imgs) == 3 and all(w > 0 for w, _ in imgs), f"{name}: 3 фото загружены {[(w) for w,_ in imgs]}")
        hidden = page.evaluate("[...document.querySelectorAll('[data-reveal]')].filter(e=>getComputedStyle(e).opacity<0.99).length")
        ok(hidden == 0, f"{name}: после прокрутки все блоки видимы")
        about_h = page.eval_on_selector("#about img", "e => e.getBoundingClientRect().height")
        if width < 768:
            ok(240 <= about_h <= 300, f"{name}: фото «О салоне» ограничено по высоте ({about_h:.0f}px)")
        ok(not errors, f"{name}: ошибок в консоли нет {errors[:3]}")
        ctx.close()

    # содержание и ссылки
    ctx, page, _ = new_page(browser, 1440, 900)
    html = page.content(); body = page.inner_text("body")
    tels = set(page.eval_on_selector_all('a[href^="tel:"]', "e => e.map(a => a.getAttribute('href'))"))
    ok(tels == {TEL}, f"все ссылки звонка = {TEL}")
    maps = page.eval_on_selector_all('a[href*="yandex.ru/maps"]', "e => e.map(a => a.href)")
    ok(len(maps) == 1 and urllib.parse.unquote(maps[0].split("text=")[1]) == "Краснодарский край, Крымск, Коммунистическая улица, 48",
       "ссылка «Открыть на карте» кодирует полный адрес")
    for bad in FORBIDDEN:
        ok(bad not in body, f"в интерфейсе нет «{bad}»")
    for must in ["Красота начинается", "Салон красоты · Крымск", "Женские и мужские стрижки", "Окрашивание и уход", "Косметика ESTEL",
                 "Счастливые люди. Время для себя", "Уход продолжается дома", "Наши работы", "Выберите время для себя", "+7 (989) 760-54-60", "Ежедневно 09:00–19:00",
                 "Коммунистическая улица, 48", "ESTEL Счастливые люди Яны Белинской", "Итоговую стоимость уточняйте при записи"]:
        ok(must in norm(body), f"есть текст «{must}»")
    ok("Анжела" not in body and "отзыв" not in body.lower(), "блок отзыва убран")
    ok(page.locator("#works li").count() == 4 and page.locator("#works img").count() == 0,
       "раздел «Наши работы»: 4 места под фото, чужих или стоковых снимков нет")
    ok(norm(body).count("Итоговую стоимость уточняйте при записи") == 1, "подпись о стоимости — одна")
    ok(page.get_attribute('meta[name="robots"]', "content") == "noindex, nofollow", "технический noindex сохранён")
    ld = json.loads(page.eval_on_selector('script[type="application/ld+json"]', 'e=>e.textContent'))
    ok(not {"aggregateRating", "review", "priceRange"} & set(ld), "JSON-LD без рейтинга, отзывов и цен")
    calls = page.evaluate("[...document.querySelectorAll('main a[href^=\"tel:\"]')].filter(a=>a.className.includes('bg-olive')).length")
    ok(calls == 1, f"в основном содержании одна кнопка «Позвонить» (финальный блок): {calls}")
    ctx.close()

    # без JavaScript
    ctx = browser.new_context(java_script_enabled=False, viewport={"width": 390, "height": 844}); page = ctx.new_page()
    page.route("**/*", lambda r: r.abort() if r.request.url.startswith("http") else r.continue_())
    page.goto(URL)
    page.evaluate("1") if False else None
    txt = norm(page.inner_text("#group-cuts"))
    ok(page.is_visible("h1") and "800–1 500 ₽" in txt and "1 500–2 000 ₽" in txt, "без JS: видны цены обеих категорий")
    ok(not page.is_visible("[data-cat-switch]"), "без JS: неработающий переключатель скрыт")
    ctx.close()

    # reduced motion
    ctx = browser.new_context(reduced_motion="reduce", viewport={"width": 390, "height": 844}); page = ctx.new_page()
    page.route("**/*", lambda r: r.abort() if r.request.url.startswith("http") else r.continue_())
    page.goto(URL); page.evaluate("window.scrollTo(0, 2500)"); page.wait_for_timeout(100)
    ok(page.evaluate("document.getAnimations().length") == 0, "prefers-reduced-motion: анимации появления отключены")
    ctx.close()
    browser.close()

print("\n".join(results + problems))
print(f"\n{len(results)} OK, {len(problems)} FAIL")
sys.exit(1 if problems else 0)
