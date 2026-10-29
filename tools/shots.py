"""Скриншоты: python3 tools/shots.py [out_dir]"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "dist" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)
URL = (ROOT / "dist" / "index.html").as_uri()
with sync_playwright() as p:
    b = p.chromium.launch()
    for w, h in ((360, 740), (390, 844), (1440, 900)):
        mob = w < 800
        pg = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=2 if mob else 1, is_mobile=mob, has_touch=mob)
        pg.route("**/*", lambda r: r.abort() if r.request.url.startswith("http") else r.continue_())
        pg.emulate_media(reduced_motion="reduce")
        pg.goto(URL); pg.wait_for_timeout(300)
        pg.screenshot(path=str(OUT / f"{w}-first-screen.png"))
        for y in range(0, pg.evaluate("document.body.scrollHeight"), 400):
            pg.evaluate(f"scrollTo(0,{y})"); pg.wait_for_timeout(30)
        pg.wait_for_timeout(400); pg.evaluate("scrollTo(0,0)"); pg.wait_for_timeout(200)
        pg.screenshot(path=str(OUT / f"{w}-full.png"), full_page=True)
