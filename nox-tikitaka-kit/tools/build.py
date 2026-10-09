#!/usr/bin/env python3
"""NOX × Tikitaka 빌더.

data/members.json + data/faces.json + data/platform.json → output/ 전체 생성.
  python tools/build.py          # 전체
  python tools/build.py eclipse  # 한 명 (허브·테스트 스니펫은 항상 함께 갱신)
"""
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from heroes import HERO_FX, emblem  # noqa: E402

DATA, OUT = ROOT / "data", ROOT / "output"
BUDGET = 19500  # platform.json "budget"이 있으면 그 값 우선


def budget(platform):
    return int(platform.get("budget", BUDGET))
FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
         '<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;1,500'
         '&family=Noto+Sans+KR:wght@300;400;500;700&family=Noto+Serif+KR:wght@400;600;700&display=swap" rel="stylesheet">')
FONTS_PASTE = ('<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;1,500'
               '&family=Noto+Sans+KR:wght@300;400;500;700&family=Noto+Serif+KR:wght@400;600;700&display=swap" rel="stylesheet">')
SILHOUETTE = ('<svg viewBox="0 0 100 100" aria-hidden="true"><circle cx="50" cy="38" r="17"/>'
              '<path d="M16 100c3-22 18-34 34-34s31 12 34 34z"/></svg>')
# 붙여넣기 버전 실루엣: SVG 대신 CSS (8개 슬롯 × SVG ≈ 1,100자 절약)
SILHOUETTE_CSS = ('.nx-face:empty::before,.nx-face:empty::after{content:"";position:absolute;background:currentColor}'
                  '.nx-face:empty::before{left:36.4%;top:36.8%;width:27.2%;height:27.2%;border-radius:50%}'
                  '.nx-face:empty::after{left:22.8%;right:22.8%;top:72.8%;bottom:0;border-radius:50% 50% 0 0/60% 60% 0 0}')
TRACK_STATUS = {"live": "재생 가능", "soon": "업데이트 예정"}


# ---------------------------------------------------------------- data
def load():
    members = json.loads((DATA / "members.json").read_text(encoding="utf-8"))
    faces = json.loads((DATA / "faces.json").read_text(encoding="utf-8"))
    pf = DATA / "platform.json"
    platform = json.loads(pf.read_text(encoding="utf-8")) if pf.exists() else {}
    platform.setdefault("mode", "A")
    platform.setdefault("cdn_ref", "main")
    return members, faces, platform


def rgb(hexcol):
    h = hexcol.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def tokens(m):
    r, g, b = rgb(m["accent"])
    if m.get("accent_light"):
        lr, lg, lb = rgb(m["accent_light"])
    elif m["id"] == "eclipse":  # reference 값 그대로
        lr, lg, lb = 255, 236, 205
    else:
        lr, lg, lb = (round(c + (255 - c) * .7) for c in (r, g, b))
    return {"__A__": m["accent"], "__RGB__": f"{r},{g},{b}", "__LRGB__": f"{lr},{lg},{lb}"}


def fill(s, tok):
    for k, v in tok.items():
        s = s.replace(k, v)
    return s


def css_for(m):
    base = (ROOT / "tools" / "templates" / "base.css").read_text(encoding="utf-8")
    fx = HERO_FX[m["id"]]["css"].strip("\n")
    base = base.replace("  /* __HERO_FX__ */", f"  /* ---------- HERO FX : {m['concept_en'].upper()} ---------- */\n{fx}")
    return fill(base, tokens(m))


# ---------------------------------------------------------------- text
def esc(s):
    return html.escape(s, quote=False)


def sq(s):
    """곧은 따옴표 → 둥근 따옴표 (“ ” ‘ ’)."""
    s = re.sub(r'"([^"]*)"', "“\\1”", s)
    return re.sub(r"'([^']*)'", "‘\\1’", s)


def rich(s, strong=()):
    s = sq(esc(s))
    for p in strong:
        s = s.replace(p, f"<strong>{p}</strong>", 1) if p in s else s
    return s


def br_after_comma(s):
    return sq(esc(s)).replace(", ", ",<br>", 1)


def spec_chip(s):
    mm = re.fullmatch(r"(\d+)(cm)", s)
    return f'<span class="nx-chip"><b>{mm[1]}</b>{mm[2]}</span>' if mm else f'<span class="nx-chip">{esc(s)}</span>'


# ---------------------------------------------------------------- faces
def face_src(mid, faces, target):
    f = faces.get(mid, {})
    if target == "paste":
        return f.get("url") or None
    if f.get("url"):
        return f["url"]
    local = f.get("local")
    if local:
        p = ROOT / local
        for cand in [p] + [p.with_suffix(e) for e in (".png", ".jpg", ".jpeg", ".webp")]:
            if cand.exists():
                return "../../" + cand.relative_to(ROOT).as_posix()
    return None


def face(mid, name, faces, target, cls=""):
    src = face_src(mid, faces, target)
    inner = f'<img src="{html.escape(src)}" alt="{name}">' if src else ("" if target == "paste" else SILHOUETTE)
    return f'<div class="nx-face{cls}" data-face="{mid}">{inner}</div>'


# ---------------------------------------------------------------- page
def body(m, members, faces, target):
    g, c, d = members["group"], m["copy"], m.get("display", {})
    strong = d.get("strong", [])
    en = m["concept_en"]
    fx = HERO_FX[m["id"]]
    film_no = m["concept_film"].split()[-1]
    emb = emblem(m["id"])
    o = []
    a = o.append
    # HERO
    a('<main class="nx">')
    a('<header class="nx-hero">')
    a(f'<p class="nx-kicker">Concept Film {film_no} · {en}</p>')
    a(f'<div class="nx-orb">{fx["before"]}<div class="nx-disc">{face(m["id"], m["name"], faces, target)}</div>{fx["after"]}</div>')
    a(f'<p class="nx-label">{esc(c["title_label"])}</p>')
    a(f'<h1 class="nx-title">{m["name"]}<small>— {m["concept_ko"]} ({en})</small></h1>')
    a(f'<p class="nx-power">{emb}<b>POWER</b>{esc(m["power"]["name"])}</p>')
    a(f'<p class="nx-lead">{d.get("lead_html") or br_after_comma(c["lead"])}</p>')
    a('<div class="nx-specs">' + "".join(spec_chip(s) for s in c["specs"]) + "</div>")
    a('<p class="nx-scroll">SCROLL</p>')
    a("</header>")
    # OFFICIAL PROFILE
    ps = m["profile_suggest"]
    a('<section class="nx-sec"><p class="nx-eyebrow">Official Profile</p><div class="nx-prof">' + emb + "<dl>"
      f'<dt>포지션</dt><dd>{esc(m["position"])}</dd>'
      f'<dt>신장</dt><dd>{esc(ps["height"])}</dd>'
      f'<dt>상징</dt><dd>{m["concept_ko"]} {m["concept_hanja"]} · {en}</dd>'
      f'<dt>능력</dt><dd>{esc(m["power"]["name"])}<small>{rich(m["power"]["desc"])}</small></dd>'
      f'<dt>컬러</dt><dd><i class="nx-sw"></i>{esc(ps["color_name"])}</dd>'
      "</dl></div></section>")
    # PROLOGUE
    a('<section class="nx-sec"><p class="nx-eyebrow">Prologue</p>')
    a(f'<blockquote class="nx-quote">“{d.get("signature_html") or br_after_comma(c["signature_line"])}”</blockquote>')
    for p in c["prologue"]:
        a(f'<p class="nx-p">{rich(p, strong)}</p>')
    a("</section>")
    # MODE
    md = c["mode"]
    a(f'<section class="nx-sec nx-modesec"><p class="nx-eyebrow">{esc(md["name_en"])}</p><h2 class="nx-h2">{esc(md["title"])}</h2>')
    a(f'<p class="nx-p">{rich(md["body_1"], strong)}</p>')
    a(f'<div class="nx-line">“{sq(esc(md["line"]))}”<cite>{esc(md["line_cite"])}</cite></div>')
    a(f'<p class="nx-p">{rich(md["body_2"], strong)}</p>')
    ct = md["contrast"]
    li = lambda xs: "".join(f"<li>{sq(esc(x))}</li>" for x in xs)  # noqa: E731
    a(f'<div class="nx-modes"><div class="nx-mode"><h4>{esc(ct["public_label"])}</h4><ul>{li(ct["public"])}</ul></div>'
      f'<div class="nx-mode is-hidden"><h4>{esc(ct["hidden_label"])}</h4><ul>{li(ct["hidden"])}</ul></div></div>')
    a("</section>")
    # EPISODES
    a('<section class="nx-sec"><p class="nx-eyebrow">Episodes</p><h2 class="nx-h2">4개의 밤</h2><div class="nx-eps">')
    for e in c["episodes"]:
        q = f'<q>{sq(esc(e["line"]))}</q>' if e.get("line") else ""
        a(f'<article class="nx-ep"><div class="nx-ep-no"><small>EP</small>{e["no"]}</div>'
          f'<h3>{sq(esc(e["title"]))}</h3><p>{sq(esc(e["scene"]))}</p>{q}</article>')
    a("</div></section>")
    # WORLD
    a(f'<section class="nx-sec"><p class="nx-eyebrow">World</p><h2 class="nx-h2">{esc(g["worldview_title"])}</h2>')
    a(f'<p class="nx-p">{sq(esc(g["worldview"]))}</p>')
    a('<div class="nx-orbit" aria-hidden="true">' + "".join(
        f'<div class="nx-body{" is-me" if x["id"] == m["id"] else ""}"><i class="nx-dot"></i>{x["concept_ko"]}</div>'
        for x in members["members"]) + "</div>")
    a(f'<p class="nx-p">{rich(c["world_closing"], strong)}</p>')
    a("</section>")
    # MEMBERS
    a('<section class="nx-sec"><p class="nx-eyebrow">The Members</p><h2 class="nx-h2">7인</h2><ul class="nx-members">')
    for x in members["members"]:
        me = x["id"] == m["id"]
        tag = '<span class="nx-tag">이 스토리</span>' if me else ""
        a(f'<li class="nx-mem{" is-me" if me else ""}">{face(x["id"], x["name"], faces, target, " nx-face--sm")}'
          f'<div><p class="nx-mem-head"><span class="nx-mem-name">{x["name"]}</span>'
          f'<span class="nx-mem-con">{x["concept_ko"]} · {x["concept_en"].upper()}</span>{tag}</p>'
          f'<p class="nx-mem-desc">{sq(esc(x["one_liner"]))}</p></div></li>')
    a("</ul></section>")
    # BGM
    al = g["album"]
    a(f'<section class="nx-sec"><p class="nx-eyebrow">BGM</p><div class="nx-album"><b>{al["title"]}</b><span>{al["label"]}</span></div><ol class="nx-tracks">')
    for t in al["tracks"]:
        soon = t["status"] != "live"
        a(f'<li class="nx-track{" is-soon" if soon else ""}"><span class="nx-track-no">{t["no"]}</span>'
          f'<span class="nx-track-t">{t["ko"]}<i>{t["en"]}</i></span><span class="nx-track-s">{TRACK_STATUS.get(t["status"], t["status"])}</span></li>')
    a("</ol></section>")
    # PLAY GUIDE
    guide = g["play_guide"].replace(g["ooc_example"] + " 등 ", "")
    a(f'<section class="nx-sec"><p class="nx-eyebrow">Play Guide</p><div class="nx-guide"><p>{esc(guide)}</p>'
      f'<span class="nx-cmd">{esc(g["ooc_example"])}</span></div></section>')
    # FOOTER
    a(f'<footer class="nx-foot"><p class="nx-slogan">{esc(g["idol_concept"]["slogan_suggest"])}</p>'
      f'<b>{en.upper()}</b> : {g["name"]} × {g["credit"]}<br>Tikitaka AI System</footer>')
    a("</main>")
    return "\n".join(o)


def doc(title, css, inner, fonts=FONTS):
    return ('<!DOCTYPE html>\n<html lang="ko">\n<head>\n<meta charset="UTF-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f"<title>{title}</title>\n{fonts}\n<style>\n{css}</style>\n</head>\n<body>\n{inner}\n</body>\n</html>\n")


# ---------------------------------------------------------------- paste (티키타 공개 소개)
def scope_css(css):
    """호스트 페이지(티키타)를 건드리지 않도록 전역 선택자를 .nx 안으로 가둔다."""
    css = css.replace(":root{", ".nx{", 1)
    css = css.replace("  *{box-sizing:border-box;margin:0;padding:0}", "  .nx,.nx *{box-sizing:border-box;margin:0;padding:0}")
    css = css.replace("  html,body{background:var(--nx-bg)}\n", "")
    css = css.replace("  body{color:", "  .nx{background:var(--nx-bg);color:")
    css = css.replace("content:\"\";position:fixed;inset:0;", "content:\"\";position:absolute;inset:0;")
    css = css.replace("{*,*::before,*::after{animation:none", "{.nx *,.nx *::before,.nx *::after{animation:none")
    return css + SILHOUETTE_CSS + "\n"


def min_css(css):
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"\s+", " ", css)
    css = re.sub(r"\s*([{};:,>])\s*", r"\1", css)
    return css.replace(";}", "}").strip()


def min_html(h):
    h = re.sub(r"<!--.*?-->", "", h, flags=re.S)
    h = re.sub(r">\s+<", "><", h)
    return re.sub(r"\s+", " ", h).strip()


VAR_SHORT = [("--nx-gold-soft", "--as"), ("--nx-surface", "--s"), ("--nx-muted", "--m"), ("--nx-faint", "--f"),
             ("--nx-serif", "--sf"), ("--nx-sans", "--ss"), ("--nx-gold", "--a"), ("--nx-line", "--l"),
             ("--nx-ink", "--i"), ("--nx-bg", "--b"), ("--nx-en", "--e")]


def reduce_steps():
    """CLAUDE.md §8 순서: 폰트 link → 변수명 단축 → 중복 규칙 병합 → WORLD 천체 점 → MODE 대비 카드."""
    def fonts(s):
        s["fonts"] = ""

    def short_vars(s):
        for a, b in VAR_SHORT:
            s["css"] = s["css"].replace(a, b)

    def merge(s):
        css = s["css"].replace("-webkit-font-smoothing:antialiased;", "")
        lit = "rgba(236,230,218,.07)"
        if css.count(lit) > 2:
            css = css.replace(lit, "var(--d)").replace(".nx{", ".nx{--d:" + lit + ";", 1)
        s["css"] = css

    def orbit(s):
        s["html"] = re.sub(r'<div class="nx-orbit".*?</div></div>', "", s["html"], count=1)
        s["html"] = re.sub(r'<div class="nx-orbit"[^>]*>(<div class="nx-body[^"]*"><i class="nx-dot"></i>[^<]*</div>)*</div>', "", s["html"])
        s["css"] = re.sub(r"\.nx-(orbit|body|dot)[^{]*\{[^}]*\}", "", s["css"])

    def modes(s):
        s["html"] = re.sub(r'<div class="nx-modes">.*?</ul></div></div>', "", s["html"])
        s["css"] = re.sub(r"\.nx-modes?[^{]*\{[^}]*\}", "", s["css"])

    return [("Google Fonts link 제거", fonts), ("CSS 변수명 단축", short_vars), ("중복 규칙 병합", merge),
            ("WORLD 천체 점 열 제거", orbit), ("MODE 대비 카드 제거", modes)]


def assemble(s, mode):
    if mode == "A+":
        return f'<link rel="stylesheet" href="{s["css_url"]}">\n{s["html"]}\n'
    head = (s["fonts"] + "\n") if s["fonts"] else ""
    return f"{head}<style>{s['css']}</style>\n{s['html']}\n"


def paste_version(m, members, faces, platform):
    mode = platform["mode"]
    raw_html = body(m, members, faces, "paste")
    s = {"css": min_css(scope_css(css_for(m))), "html": min_html(raw_html), "fonts": FONTS_PASTE,
         "css_url": platform.get("css_url_pattern",
                                 "https://cdn.jsdelivr.net/gh/baekwinter/tikita@{ref}/nox-tikitaka-kit/output/{id}/nox.css")
                    .format(ref=platform["cdn_ref"], id=m["id"])}
    if mode == "C":
        return markdown_version(m, members, faces), []
    if mode == "B":
        return inline_version(m, members, faces), []
    applied = []
    for label, fn in reduce_steps():
        if len(assemble(s, mode)) <= budget(platform):
            break
        fn(s)
        applied.append(label)
    return assemble(s, mode), applied


def inline_version(m, members, faces):
    """B 모드: 인라인 style만 쓰는 정적 버전 (tools/inline.py)."""
    import inline
    return inline.page(m, members, faces) + "\n"


def markdown_version(m, members, faces):
    """C 모드 (HTML이 지워지는 경우): 마크다운 + 이미지로 같은 위계를 재구성."""
    g, c = members["group"], m["copy"]
    url = faces.get(m["id"], {}).get("url")
    L = []
    if url:
        L += [f"![{m['name']}]({url})", ""]
    L += [f"**CONCEPT FILM {m['concept_film'].split()[-1]} · {m['concept_en'].upper()}**", "",
          f"# {c['title_full']}", "", f"**POWER** {m['power']['name']}", "", f"*{sq(c['lead'])}*", "",
          " · ".join(c["specs"]), "", "---", "", "## OFFICIAL PROFILE", "",
          f"- 포지션 : {m['position']}", f"- 신장 : {m['profile_suggest']['height']}",
          f"- 상징 : {m['concept_ko']} {m['concept_hanja']} · {m['concept_en']}",
          f"- 능력 : {m['power']['name']} — {m['power']['desc']}", f"- 컬러 : {m['profile_suggest']['color_name']}", "",
          "## PROLOGUE", "", f"> “{c['signature_line']}”", ""]
    L += [sq(p) + "\n" for p in c["prologue"]]
    md = c["mode"]
    L += [f"## {md['name_en'].upper()} — {md['title']}", "", sq(md["body_1"]), "", f"> “{md['line']}”  ", f"> {md['line_cite']}", "",
          sq(md["body_2"]), "", "## EPISODES : 4개의 밤", ""]
    for e in c["episodes"]:
        L += [f"**▶ EP {e['no']}. {e['title']}**  ", sq(e["scene"]) + ("  " if e.get("line") else "")]
        if e.get("line"):
            L.append(f"“{e['line']}”")
        L.append("")
    L += [f"## {g['worldview_title']}", "", sq(g["worldview"]), "", sq(c["world_closing"]), "", "## THE MEMBERS", ""]
    for x in members["members"]:
        mark = " ← 이 스토리" if x["id"] == m["id"] else ""
        L.append(f"- **{x['name']}** ({x['concept_ko']} · {x['concept_en'].upper()}) — {sq(x['one_liner'])}{mark}")
    al = g["album"]
    L += ["", f"## BGM : {al['label']} [{al['title']}]", ""]
    L += [f"- 트랙 {t['no']}. {t['ko']} ({t['en']}){'' if t['status'] == 'live' else ' — 업데이트 예정'}" for t in al["tracks"]]
    L += ["", "## PLAY GUIDE", "", g["play_guide"], "", "---", "",
          f"*{g['idol_concept']['slogan_suggest']}*  ", f"{m['concept_en'].upper()} : {g['name']} × {g['credit']} | Tikitaka AI System", ""]
    return "\n".join(L)


# ---------------------------------------------------------------- hub
HUB_CSS = """
  .nx-hub-emb{width:120px;height:120px;color:var(--nx-gold);margin-bottom:40px;animation:nx-spin 60s linear infinite}
  .nx-hero .nx-lead{word-break:keep-all}
  .nx-hub-slogan{font-family:var(--nx-en);font-style:italic;font-size:clamp(20px,5vw,26px);letter-spacing:.06em;color:var(--nx-gold);margin-top:12px}
  .nx-grid{display:flex;flex-wrap:wrap;justify-content:center;gap:12px}
  .nx-grid > .nx-card{flex:0 1 calc((100% - 24px)/3)}
  .nx-card{--nx-gold:var(--c);display:flex;flex-direction:column;gap:10px;padding:22px 20px;border:1px solid rgba(236,230,218,.08);border-radius:14px;background:var(--nx-surface);color:var(--nx-ink);text-decoration:none;transition:border-color .3s,transform .3s}
  .nx-card:hover{border-color:var(--c);transform:translateY(-2px)}
  .nx-card-top{display:flex;align-items:center;justify-content:space-between}
  .nx-card .nx-face{width:72px;height:72px;box-shadow:0 0 0 1px var(--c),0 0 18px color-mix(in srgb,var(--c) 45%,transparent)}
  .nx-card .nx-emb{width:30px;height:30px;color:var(--c)}
  .nx-card-film{font-family:var(--nx-en);font-size:11.5px;letter-spacing:.3em;color:var(--c);text-transform:uppercase}
  .nx-card-name{font-family:var(--nx-serif);font-size:19px;font-weight:600}
  .nx-card-name small{display:block;font-family:var(--nx-en);font-size:12px;letter-spacing:.16em;color:var(--nx-faint);margin-top:2px;font-weight:500}
  .nx-card-desc{font-size:13.5px;line-height:1.7;color:var(--nx-muted);word-break:keep-all}
  .nx-card-pow{font-size:12px;color:var(--c);letter-spacing:.04em}
  .nx-sugg{display:grid;grid-template-columns:72px 1fr;gap:8px 14px;font-size:14px}
  .nx-sugg dt{color:var(--nx-faint);font-size:12.5px}
  .nx-sugg dd{word-break:keep-all}
  @keyframes nx-spin{to{transform:rotate(360deg)}}
  @media (max-width:600px){.nx-grid > .nx-card{flex-basis:calc((100% - 12px)/2);padding:18px 16px}.nx-card .nx-card-film{letter-spacing:.16em;font-size:11px}.nx-card .nx-face{width:60px;height:60px}}
"""


def hub(members, faces):
    g = members["group"]
    ic = g["idol_concept"]
    hubm = {"id": "hub", "accent": "#e3d6bd", "accent_light": "#fff6e4"}
    base = (ROOT / "tools" / "templates" / "base.css").read_text(encoding="utf-8").replace("  /* __HERO_FX__ */", "")
    css = fill(base, tokens(hubm)) + HUB_CSS
    cards = []
    for x in members["members"]:
        cards.append(f'<a class="nx-card" href="{x["id"]}/preview.html" style="--c:{x["accent"]}">'
                     f'<div class="nx-card-top">{face(x["id"], x["name"], faces, "preview")}{emblem(x["id"])}</div>'
                     f'<p class="nx-card-film">{x["concept_film"].title()}</p>'
                     f'<p class="nx-card-name">{x["name"]}<small>{x["concept_ko"]} · {x["concept_en"].upper()}</small></p>'
                     f'<p class="nx-card-desc">{sq(esc(x["one_liner"]))}</p>'
                     f'<p class="nx-card-pow">POWER · {esc(x["power"]["name"])}</p></a>')
    al = g["album"]
    tracks = "".join(f'<li class="nx-track{"" if t["status"] == "live" else " is-soon"}"><span class="nx-track-no">{t["no"]}</span>'
                     f'<span class="nx-track-t">{t["ko"]}<i>{t["en"]}</i></span><span class="nx-track-s">{TRACK_STATUS.get(t["status"], t["status"])}</span></li>'
                     for t in al["tracks"])
    inner = f"""<main class="nx">
<header class="nx-hero">
<p class="nx-kicker">{al['label']} · {al['title']}</p>
{emblem('group', 'nx-emb nx-hub-emb')}
<p class="nx-label">{esc(g['worldview_title'])}</p>
<h1 class="nx-title">{g['name']}<small>{g['name_ko']}</small></h1>
<p class="nx-hub-slogan">{esc(ic['slogan_suggest'])}</p>
<p class="nx-lead">{sq(esc(g['worldview']))}</p>
<p class="nx-scroll">SCROLL</p>
</header>
<section class="nx-sec"><p class="nx-eyebrow">Concept Films 01 — 07</p><h2 class="nx-h2">일곱 개의 낙화</h2>
<div class="nx-grid">{''.join(cards)}</div></section>
<section class="nx-sec"><p class="nx-eyebrow">BGM</p><div class="nx-album"><b>{al['title']}</b><span>{al['label']}</span></div><ol class="nx-tracks">{tracks}</ol></section>
<section class="nx-sec"><p class="nx-eyebrow">Group Profile</p><dl class="nx-sugg">
<dt>데뷔</dt><dd>{esc(ic['debut_frame'])}</dd>
<dt>문양</dt><dd>{esc(ic['group_emblem'])}</dd>
<dt>인사</dt><dd>{esc(ic['greeting_suggest'])} <span class="nx-tag">제안</span></dd>
<dt>팬덤</dt><dd>{esc(ic['fandom_suggest']['name'])} — {esc(ic['fandom_suggest']['meaning'])} <span class="nx-tag">제안</span></dd>
<dt>컬러</dt><dd>{esc(ic['official_color_suggest'])}</dd>
</dl></section>
<footer class="nx-foot"><p class="nx-slogan">{esc(ic['slogan_suggest'])}</p><b>NOX</b> × {g['credit']}<br>Tikitaka AI System</footer>
</main>"""
    return doc("NOX · FANTASIA", css, inner)


# ---------------------------------------------------------------- fields / prompts
def story_setting(m, members):
    t = m["tikitaka"]
    return t["story_setting"].rstrip() + "\n\n" + members["group"]["tikitaka_common_rules"].strip()


def fields_md(m, members):
    """티키타 입력칸 전체. 각 칸은 ``` 블록이라 그대로 복사해 붙여넣을 수 있다."""
    t = m["tikitaka"]
    L = [f"# {m['name']} ({m['concept_ko']} · {m['concept_en']}) — 티키타 입력칸",
         "", f"> 상태: 카피 `{m['status']}` / 입력칸 `{t.get('status', 'draft')}` · 글자 수는 `python tools/check.py`로 재확인",
         "> 공개 소개(마크다운) 칸에는 `tikitaka_intro.html` 내용을 통째로 붙여넣는다.", ""]

    def block(label, val, limit=None):
        n = len(val)
        lim = f" / {limit:,}" if limit else ""
        L.extend([f"### {label}  `{n:,}{lim}자`", "```", val, "```", ""])

    L.append("## 1. 프로필")
    block("스토리 제목", t["story_title"])
    block("한 줄 소개", t["one_liner"], 100)
    block("캐릭터 이름", m["name"], 15)
    block("캐릭터 소개", t["char_intro"], 1000)
    block("비밀", t["secret"], 2000)
    L.extend([f"### 성별 / 나이", f"남성 / {m['profile_suggest']['age']}세", ""])
    block("스토리 설정 (비공개, AI 참고용)", story_setting(m, members), 2000)
    block("첫 메시지", t["first_message"])
    block("대화 예시", t["example_dialogue"])
    L.append("## 2. 에피소드")
    for i, e in enumerate(t["episodes"], 1):
        L.append(f"### EP {i:02d}")
        block(f"EP {i:02d} 제목", e["title"], 20)
        block(f"EP {i:02d} 다음 에피소드로 넘어가는 조건", e["condition"], 50)
        block(f"EP {i:02d} 서사", e["narrative"], 2000)
        block(f"EP {i:02d} 비공개 설정", e["private"], 2000)
    L.append("## 3. 변수 (최대 3개)")
    L += ["| 변수명 | 키 | 범위 · 시작값 | 설명 |", "|---|---|---|---|"]
    L += [f"| {v['name']} | `{v['key']}` | {v['range']} · {v['start']} | {v['desc']} |" for v in t["variables"]]
    L += ["", "## 4. 공개여부"]
    L += [f"### 카테고리  `{len(t['categories'])} / 3개`", "```", ", ".join(t["categories"]), "```", ""]
    L += [f"### 태그  `{len(t['tags'])} / 15개`", "```", " ".join("#" + x for x in t["tags"]), "```", ""]
    block("제작자 코멘트", t["creator_comment"], 1000)
    L += ["### 공개 소개 (마크다운)", "`tikitaka_intro.html` 파일 내용 전체를 붙여넣기 (HTML이 지워지면 `tikitaka_intro.md`).", ""]
    return "\n".join(L)


def image_prompts(m, members):
    im, ip = m["image"], members["group"]["image_prompt_base"]

    def P(model, kws):
        s = ", ".join(kws)
        return f"[{model}] 프롬프트: {s}", len(s)

    face_kw = [ip["quality"], ip["subject"], ip["portrait"], im["appearance"], im["outfit"], im["symbol"], ip["light"], ip["style"]]
    thumb_kw = [ip["quality"], ip["subject"], "cover art, cinematic composition, three-quarter view, looking at viewer",
                im["appearance"], im["outfit"], im["symbol"], "empty space at bottom for title", ip["light"], ip["style"]]
    L = [f"# {m['name']} ({m['concept_en']}) — 이미지 프롬프트", "",
         "티키타 이미지 생성 → 모델 **Romance** (7인 톤 통일) · 512×768 (2:3) · 실사 스타일 금지(illustration 키워드 유지).",
         "생성한 얼굴 이미지를 업로드한 뒤 이미지 주소를 `data/faces.json` → `url`에 붙여넣고 `얼굴 반영해줘`.", ""]
    for title, kws, desc in [("얼굴 (프로필 · 소개 페이지 얼굴 슬롯용)", face_kw, f"{m['name']}, 프로필, 정면, 상반신"),
                             ("썸네일 (스토리 대표 이미지)", thumb_kw, f"{m['name']}, 썸네일, {m['concept_ko']}")]:
        p, n = P("Romance", kws)
        L += [f"## {title}  `{n:,} / 1,200자`", "```", p, "```", f"에셋 설명(매칭 키워드): `{desc}`", ""]
    for i, (e, kw) in enumerate(zip(m["copy"]["episodes"], im["episodes"]), 1):
        kws = [ip["quality"], ip["subject"], im["appearance"], kw, ip["light"], ip["style"]]
        p, n = P("Romance", kws)
        L += [f"## EP {i:02d} — {e['title']}  `{n:,} / 1,200자`", "```", p, "```",
              f"에셋 설명(매칭 키워드): `{', '.join(im['episode_assets'][i - 1])}`", ""]
    return "\n".join(L)


# ---------------------------------------------------------------- compat test (Step 0)
def tikitaka_test(platform):
    ref = platform.get("test_ref") or platform["cdn_ref"]
    url = f"https://cdn.jsdelivr.net/gh/baekwinter/tikita@{ref}/nox-tikitaka-kit/output/_test.css"
    img = f"https://cdn.jsdelivr.net/gh/baekwinter/tikita@{ref}/nox-tikitaka-kit/output/_test.png"
    return f"""<style>.nxt-a{{padding:14px 18px;border:2px solid #d9b26f;border-radius:12px;background:#0e0e13;color:#d9b26f;font-weight:700}}@keyframes nxt-b{{0%,100%{{opacity:.2}}50%{{opacity:1}}}}.nxt-d{{padding:14px 18px;border-radius:12px;background:#d9b26f;color:#07070a;font-weight:700;animation:nxt-b 1.2s ease-in-out infinite}}</style>
<div class="nxt-a">A — 이 박스가 금색 테두리로 보이면 &lt;style&gt; 블록 OK</div>

<link rel="stylesheet" href="{url}">
<div class="nxt-aplus">A+ — 이 박스가 보라색 배경으로 보이면 외부 CSS OK</div>

<div style="padding:14px 18px;border:2px dashed #7fd9bf;border-radius:12px;color:#7fd9bf;font-weight:700">B — 이 박스가 민트색 점선 테두리로 보이면 인라인 style OK</div>

<img src="{img}" alt="C-html" width="120"> ← C1 (img 태그)

![C-markdown]({img}) ← C2 (마크다운 이미지)

<div class="nxt-d">D — 이 박스가 깜빡이면 @keyframes 애니메이션 OK</div>
"""


TEST_CSS = ".nxt-aplus{padding:14px 18px;border-radius:12px;background:#6b4fd8;color:#fff;font-weight:700}\n"


# ---------------------------------------------------------------- review (Step 2 확인표)
def review(members):
    g = members["group"]["idol_concept"]
    L = ["# NOX 7인 확인표", "",
         "`data/members.json`에서 자동 생성. 수정은 members.json에서 하고 `python tools/build.py`.",
         "확정하려면 Claude Code에 `<이름> 확정`이라고 말하면 status가 complete로 바뀐다.", "",
         "| # | 멤버 | 상태 | 나이 · 신장 | 포지션 | 유저와의 관계 | 호칭 | 아키타입 | MODE | 능력 | 컬러 |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for m in members["members"]:
        ps = m["profile_suggest"]
        L.append(f"| {m['order']} | **{m['name']}** {m['concept_ko']} | {m['status']} | {ps['age']}세 · {ps['height']} | {m['position']} | "
                 f"{ps['relation']} | {ps['address']} | {m['archetype_suggest']} | {m['copy']['mode']['name_en']} — {m['copy']['mode']['title']} | "
                 f"{m['power']['name']} | {ps['color_name']} `{m['accent']}` |")
    L += ["", "## 한 줄 훅 (시그니처 대사)", ""]
    L += [f"- **{m['name']}** — “{m['copy']['signature_line']}”" for m in members["members"]]
    L += ["", "## 그룹 제안값 (확인 필요)", "",
          f"- 슬로건: {g['slogan_suggest']}", f"- 인사: {g['greeting_suggest']}",
          f"- 팬덤명: {g['fandom_suggest']['name']} — {g['fandom_suggest']['meaning']}", f"- 공식 컬러: {g['official_color_suggest']}", ""]
    return "\n".join(L)


# ---------------------------------------------------------------- main
def build(only=None):
    members, faces, platform = load()
    OUT.mkdir(exist_ok=True)
    report = []
    for m in members["members"]:
        if only and m["id"] != only:
            continue
        if "copy" not in m:
            report.append((m["id"], "copy 없음 — 건너뜀", 0, []))
            continue
        od = OUT / m["id"]
        od.mkdir(exist_ok=True)
        css = css_for(m)
        title = f"{m['concept_en'].upper()} · {m['name']}"
        (od / "preview.html").write_text(doc(title, css, body(m, members, faces, "preview")), encoding="utf-8")
        (od / "nox.css").write_text(min_css(scope_css(css)) + "\n", encoding="utf-8")
        paste, applied = paste_version(m, members, faces, platform)
        (od / "tikitaka_intro.html").write_text(paste, encoding="utf-8")
        (od / "tikitaka_intro.md").write_text(markdown_version(m, members, faces), encoding="utf-8")
        if "tikitaka" in m:
            (od / "tikitaka_fields.md").write_text(fields_md(m, members), encoding="utf-8")
        if "image" in m:
            (od / "image_prompts.md").write_text(image_prompts(m, members), encoding="utf-8")
        report.append((m["id"], f"mode {platform['mode']}", len(paste), applied))
    (OUT / "index.html").write_text(hub(members, faces), encoding="utf-8")
    (OUT / "_review.md").write_text(review(members), encoding="utf-8")
    (OUT / "_tikitaka_test.md").write_text(tikitaka_test(platform), encoding="utf-8")
    (OUT / "_test.css").write_text(TEST_CSS, encoding="utf-8")
    for mid, mode, n, applied in report:
        print(f"{mid:8s} {mode:8s} 붙여넣기 {n:6,}자  {'축소: ' + ' → '.join(applied) if applied else ''}")
    print("hub    output/index.html")


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    build(None if arg == "all" else arg)
