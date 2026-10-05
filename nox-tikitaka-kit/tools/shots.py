#!/usr/bin/env python3
"""검증 스크린샷: output/_screens/<name>_<width>.png (390px·1280px 전체 페이지, 모션 정지 상태)."""
import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output" / "_screens"


def shoot(pages, widths=(390, 1280)):
    OUT.mkdir(parents=True, exist_ok=True)
    res = []
    with sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception:  # 설치된 playwright 버전과 브라우저 버전이 다를 때: 미리 깔린 Chromium 사용
            exe = os.environ.get("NOX_CHROMIUM") or next(
                (str(c) for c in Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome")), None)
            b = p.chromium.launch(executable_path=exe)
        for name, path in pages:
            for w in widths:
                ctx = b.new_context(viewport={"width": w, "height": 844}, reduced_motion="reduce")
                pg = ctx.new_page()
                pg.goto(path.resolve().as_uri())
                pg.wait_for_timeout(1500)
                sw = pg.evaluate("document.documentElement.scrollWidth")
                f = OUT / f"{name}_{w}.png"
                pg.screenshot(path=str(f), full_page=True)
                res.append((name, w, sw, f))
                ctx.close()
        b.close()
    return res


if __name__ == "__main__":
    ids = sys.argv[1:] or ["abyss", "eclipse", "comet", "mist", "moon", "aurora", "star"]
    pages = [(i, ROOT / "output" / i / "preview.html") for i in ids] + [("hub", ROOT / "output" / "index.html")]
    for name, w, sw, f in shoot(pages):
        print(f"{name:8s} {w:5d}px  scrollWidth={sw}  {'OK' if sw <= w else '가로 스크롤 발생!'}  {f.relative_to(ROOT)}")
