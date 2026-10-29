#!/usr/bin/env python3
"""Сборка демо-сайта салона.

    python3 build.py

Читает content.json, кадрирует фото из src/originals (оригиналы не меняются),
рендерит template.html.j2, компилирует Tailwind и пишет:
  dist/index.html        — один самодостаточный файл (фото встроены), открывается двойным кликом;
  dist/site/index.html   — версия для хостинга: фото отдельными файлами в dist/site/assets/.
"""
import base64, io, json, re, subprocess, sys, urllib.parse
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from PIL import Image

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
NBSP = " "


def fmt_rub(n):
    return f"{n:,}".replace(",", NBSP) if n >= 1000 else str(n)


def fmt_price(offer):
    if not offer or offer.get("min") is None:
        return None
    lo, hi = offer["min"], offer["max"]
    if hi is None or hi == lo:
        return f"{fmt_rub(lo)}{NBSP}₽"
    return f"{fmt_rub(lo)}–{fmt_rub(hi)}{NBSP}₽"


def build_images(content):
    """Кадрирует фото и возвращает {name: {...}} для обеих сборок."""
    out = {}
    assets = DIST / "site" / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    for old in assets.glob("*.webp"):
        old.unlink()
    specs = {k: v for k, v in content["images"].items() if not k.startswith("_")}
    for i, item in enumerate(content.get("gallery", {}).get("photos", [])):
        specs[f"gallery-{i + 1}"] = {**item, "_dir": "gallery"}
    for name, spec in specs.items():
        im = Image.open(ROOT / "src" / spec.get("_dir", "originals") / spec["source"]).convert("RGB")
        if spec.get("crop"):
            im = im.crop(tuple(spec["crop"]))
        variants = {}
        widths = sorted({w for w in (640, spec["width"]) if w <= im.width})
        for w in widths:
            h = round(im.height * w / im.width)
            buf = io.BytesIO()
            im.resize((w, h), Image.LANCZOS).save(buf, "WEBP", quality=80, method=6)
            data = buf.getvalue()
            fname = f"{name}-{w}.webp"
            (assets / fname).write_bytes(data)
            variants[w] = (fname, data, h)
        big = max(variants)
        fname, data, h = variants[big]
        out[name] = {
            "w": big, "h": h, "alt": spec["alt"], "caption": spec.get("caption", ""),
            "inline": "data:image/webp;base64," + base64.b64encode(data).decode(),
            "path": f"assets/{fname}",
            "srcset": ", ".join(f"assets/{variants[w][0]} {w}w" for w in sorted(variants)) if len(variants) > 1 else "",
            "bytes": len(data),
        }
    return out


def price_model(p):
    """Одна структура для всех режимов: группы → строки → цены по категориям (None = нет в прайсе)."""
    cats = [c["id"] for c in p["categories"]]
    groups = []
    for g in p["groups"]:
        rows = []
        for s in p["services"]:
            if s["group"] != g["id"]:
                continue
            prices = {cid: fmt_price(next((o for o in s["offers"] if o["category"] == cid), None)) for cid in cats}
            rows.append({"name": s["publicName"], "note": s.get("note"), "prices": prices})
        if not rows:
            continue
        # группа доступна только в тех категориях, где есть хотя бы одна цена
        avail = [cid for cid in cats if any(r["prices"][cid] for r in rows)]
        groups.append({"id": g["id"], "label": g["label"], "rows": rows,
                       "only": avail[0] if len(avail) == 1 else None})
    has_top_only = any(g["only"] == "top" for g in groups)
    return groups, has_top_only


def jsonld(c):
    s = c["salon"]
    data = {
        "@context": "https://schema.org",
        "@type": "BeautySalon",
        "name": s["fullName"]["value"],
        "telephone": s["phone"]["e164"],
        "address": {
            "@type": "PostalAddress",
            "streetAddress": s["address"]["street"],
            "addressLocality": s["address"]["locality"],
            "addressRegion": s["address"]["region"],
            "postalCode": s["address"]["postalCode"],
            "addressCountry": "RU",
        },
        "openingHoursSpecification": [{
            "@type": "OpeningHoursSpecification",
            "dayOfWeek": s["hours"]["schema"]["days"],
            "opens": s["hours"]["schema"]["opens"],
            "closes": s["hours"]["schema"]["closes"],
        }],
    }
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def tailwind(html_for_scan):
    scan = re.sub(r"data:image/[^\"' )]+", "", html_for_scan)
    cands = sorted(set(t for t in re.split(r"[\s\"'`<>=]+", scan) if t and len(t) < 160))
    tmp = DIST / ".candidates.txt"
    tmp.write_text("\n".join(cands), encoding="utf-8")
    css = subprocess.run(["node", str(ROOT / "tools" / "tw.mjs"), str(ROOT / "styles.css"), str(tmp)],
                         check=True, capture_output=True, text=True).stdout
    tmp.unlink()
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"\n\s*", "\n", css).strip()
    return css


def main():
    c = json.loads((ROOT / "content.json").read_text(encoding="utf-8"))
    s = c["salon"]
    tel = "tel:" + s["phone"]["e164"]
    m = c["links"]["map"]
    map_url = m["url"] or "https://yandex.ru/maps/?text=" + urllib.parse.quote(m["searchQuery"], safe="")

    price_groups, has_top_only = price_model(c["prices"])
    imgs = build_images(c)

    env = Environment(loader=FileSystemLoader(str(ROOT)), autoescape=True, undefined=StrictUndefined)
    tpl = env.get_template("template.html.j2")
    js = (ROOT / "site.js").read_text(encoding="utf-8")
    site_cfg = json.dumps({"smoothScroll": bool(c["motion"].get("smoothScroll")), "tel": tel,
                           "bookingUrl": c["booking"].get("url")}, ensure_ascii=False)
    js = f"window.__SITE__={site_cfg};\n" + js

    ctx = dict(
        meta=c["meta"], demo=c["demo"], salon=s, gallery=c["gallery"], prices=c["prices"], review=c["review"], texts=c["texts"],
        tel=tel, map_url=map_url, price_groups=price_groups, has_top_only=has_top_only,
        nav=[{"id": "about", "label": "О салоне"}, {"id": "prices", "label": "Услуги и цены"},
             {"id": "contacts", "label": "Контакты"}],
        jsonld=jsonld(c), js=js,
    )

    def render(inline, css, prefix=""):
        def pre(srcset):
            return ", ".join(prefix + part.strip() for part in srcset.split(",")) if srcset else ""
        img = {k: {**v, "src": v["inline"] if inline else prefix + v["path"], "srcset": "" if inline else pre(v["srcset"])}
               for k, v in imgs.items()}
        gallery_imgs = [img[k] for k in sorted((k for k in img if k.startswith("gallery-")), key=lambda k: int(k.split("-")[1]))]
        return tpl.render(**ctx, img=img, gallery_imgs=gallery_imgs, inline_images=inline, css=css)

    css = tailwind(render(False, ""))
    (DIST / "site").mkdir(parents=True, exist_ok=True)
    (DIST / "index.html").write_text(render(True, css), encoding="utf-8")
    (DIST / "site" / "index.html").write_text(render(False, css), encoding="utf-8")
    # корень репозитория — для GitHub Pages: страница открывается по ссылке репозитория, фото берутся из dist/site/assets
    (ROOT / "index.html").write_text(render(False, css, prefix="dist/site/"), encoding="utf-8")
    (ROOT / ".nojekyll").write_text("", encoding="utf-8")
    print("dist/index.html", (DIST / "index.html").stat().st_size // 1024, "KB")
    print("dist/site/index.html", (DIST / "site" / "index.html").stat().st_size // 1024, "KB")
    for k, v in imgs.items():
        print(f"  {k}: {v['w']}×{v['h']} webp {v['bytes'] // 1024} KB")
    print("CSS", len(css) // 1024, "KB")


if __name__ == "__main__":
    sys.exit(main())
