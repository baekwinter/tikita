"""B 모드 (티키타 공개 소개 = 인라인 style만 살아남음) 전용 페이지 생성기.

티키타 테스트 결과 (2026-10-09): <style>·외부 CSS·@keyframes 제거, 인라인 style="" 유지, <img>는 '외부 이미지 가져오기'로 반입.
그래서 이 버전은
- class 대신 모든 요소에 style=""을 직접 쓴다 (반복되는 스타일은 아래 상수로 재사용)
- position·애니메이션·::before/::after·미디어쿼리를 쓰지 않는다 → 히어로 효과는 중첩 원(테두리·배경 그라디언트·그림자)으로 정적 재현
- 좁은 화면은 flex-wrap과 max-width로 대응
reference 디자인(구조·간격·타이포·색)을 최대한 그대로 옮긴다.
"""
import html
import re

from heroes import EMBLEM_BODY

INK, BG, SURF = "#ece6da", "#07070a", "#0e0e13"
MUTED, FAINT, HAIR = "rgba(236,230,218,.62)", "rgba(236,230,218,.36)", "rgba(236,230,218,.08)"
SERIF = "'Noto Serif KR','Nanum Myeongjo','Apple SD Gothic Neo',serif"
SANS = "'Noto Sans KR','Apple SD Gothic Neo','Malgun Gothic',sans-serif"
EN = "'Cormorant Garamond',Georgia,'Times New Roman',serif"
MONO = "ui-monospace,Consolas,monospace"
TRACK_STATUS = {"live": "재생 가능", "soon": "업데이트 예정"}


def esc(s):
    return html.escape(s, quote=False)


def sq(s):
    s = re.sub(r'"([^"]*)"', "“\\1”", s)
    return re.sub(r"'([^']*)'", "‘\\1’", s)


def rgb(hexcol):
    h = hexcol.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def palette(m):
    r, g, b = rgb(m["accent"])
    if m["id"] == "eclipse":
        lr, lg, lb = 255, 236, 205
    else:
        lr, lg, lb = (round(c + (255 - c) * .7) for c in (r, g, b))
    return m["accent"], f"{r},{g},{b}", f"{lr},{lg},{lb}"


def rich(s, strong, A):
    s = sq(esc(s))
    for p in strong:
        if p in s:
            s = s.replace(p, f'<strong style="font-weight:500;color:{A}">{p}</strong>', 1)
    return s


# ------------------------------------------------------------------ hero (정적)
def ring(inner, style):
    return f'<div style="border-radius:50%;{style}">{inner}</div>'


def hero_orb(m, disc):
    A, R, L = palette(m)
    mid = m["id"]
    glow = f"box-shadow:0 0 0 1px rgba({L},.55),0 0 28px 3px rgba({R},.55),0 0 80px 18px rgba({R},.16)"
    d = ring(disc, glow)
    if mid == "eclipse":  # 금빛 코로나 + 우상단 다이아몬드 링 플레어
        bg = (f"background-color:rgba({R},.18);background-image:radial-gradient(circle at 84% 15%,#fff6e4 0 6px,rgba(255,240,215,.7) 8px,transparent 18px),"
              f"conic-gradient(from 20deg,rgba({R},.05),rgba({R},.85) 8%,rgba({R},.08) 22%,rgba({L},.6) 38%,rgba({R},.06) 52%,rgba({R},.75) 70%,rgba({R},.06) 84%,rgba({L},.5) 94%,rgba({R},.05))")
        o = ring(d, f"padding:16px;{bg};box-shadow:0 0 46px 10px rgba({R},.28)")
    elif mid == "abyss":  # 안으로 가라앉는 동심원
        o = ring(d, f"padding:12px;border:1px solid rgba({L},.42)")
        o = ring(o, f"padding:12px;border:1px solid rgba({L},.24)")
        o = ring(o, f"padding:12px;border:1px solid rgba({L},.12);background-image:radial-gradient(circle,rgba({R},.26),transparent 70%)")
    elif mid == "comet":  # 원을 사선으로 스치는 꼬리별
        bg = (f"background-image:radial-gradient(circle at 87% 14%,#fff 0 3px,rgba({L},.9) 5px,transparent 13px),"
              f"linear-gradient(142deg,transparent 30%,rgba({R},.0) 31%,rgba({R},.45) 44%,rgba({L},.95) 49.5%,transparent 50.5%),"
              f"radial-gradient(circle,rgba({R},.3),transparent 70%)")
        o = ring(d, f"padding:22px;{bg};border:1px solid rgba({R},.22)")
    elif mid == "mist":  # 원 둘레를 흐르는 안개 띠
        bg = (f"background-color:rgba({R},.08);background-image:radial-gradient(ellipse 70% 18% at 30% 22%,rgba({L},.42),transparent),"
              f"radial-gradient(ellipse 80% 16% at 70% 52%,rgba({L},.34),transparent),radial-gradient(ellipse 70% 18% at 35% 82%,rgba({L},.4),transparent)")
        o = ring(d, f"padding:22px;{bg};box-shadow:0 0 50px 14px rgba({R},.18)")
    elif mid == "moon":  # 일정 간격의 얇은 달무리 링
        o = ring(d, f"padding:14px;border:1px solid rgba({L},.55)")
        o = ring(o, f"padding:14px;border:1px solid rgba({L},.32)")
        o = ring(o, f"padding:14px;border:1px solid rgba({L},.16);box-shadow:0 0 60px 12px rgba({L},.12)")
    elif mid == "aurora":  # 뒤에서 일렁이는 빛의 커튼
        bg = (f"background-color:rgba({R},.1);background-image:repeating-linear-gradient(98deg,transparent 0 9%,rgba({R},.55) 15%,transparent 22%,rgba({L},.38) 28%,transparent 35%)")
        o = ring(d, f"padding:24px;{bg};box-shadow:0 0 60px 16px rgba({R},.2)")
    else:  # star — 시차를 둔 별빛
        dots = ",".join(f"radial-gradient(circle at {x}% {y}%,#fff 0 {s}px,rgba({L},.75) {s + 1.5}px,transparent {s * 4}px)"
                        for x, y, s in [(18, 6, 1.6), (93, 22, 2.2), (4, 48, 1.4), (96, 66, 1.6), (78, 95, 2.2), (14, 88, 1.4), (62, 2, 1.2)])
        o = ring(d, f"padding:24px;background-image:{dots},radial-gradient(circle,rgba({R},.24),transparent 68%)")
    return f'<div style="display:flex;justify-content:center;margin:0 0 44px">{o}</div>'


def disc(mid, name, faces, size):
    url = faces.get(mid, {}).get("url")
    base = f"width:{size}px;height:{size}px;border-radius:50%;overflow:hidden;background-color:#111116"
    if url:
        inner = (f'<img src="{html.escape(url)}" alt="{name}" '
                 f'style="width:{size}px;height:{size}px;object-fit:cover;object-position:50% 18%;display:block;border-radius:50%">')
        return f'<div data-face="{mid}" style="{base}">{inner}</div>'
    # 실루엣 (position 없이 flex로)
    head, sh = round(size * .27), round(size * .54)
    inner = (f'<div style="width:{head}px;height:{head}px;border-radius:50%;background-color:rgba(236,230,218,.13);margin-bottom:{round(size * .05)}px"></div>'
             f'<div style="width:{sh}px;height:{round(size * .27)}px;border-radius:{sh}px {sh}px 0 0;background-color:rgba(236,230,218,.13)"></div>')
    return f'<div data-face="{mid}" style="{base};display:flex;flex-direction:column;align-items:center;justify-content:flex-end">{inner}</div>'


def emblem(mid, size, color):
    body = EMBLEM_BODY[mid]
    return f'<svg viewBox="0 0 40 40" width="{size}" height="{size}" style="color:{color};flex:0 0 auto;display:block" aria-hidden="true">{body}</svg>'


# ------------------------------------------------------------------ page
def page(m, members, faces):
    A, R, L = palette(m)
    g, c, d = members["group"], m["copy"], m.get("display", {})
    strong = d.get("strong", [])
    en, ps = m["concept_en"], m["profile_suggest"]
    LINE = f"rgba({R},.24)"
    SEC = f"padding:52px 0;border-top:1px solid {HAIR}"
    P = f"margin:0 0 16px;font-size:15px;line-height:1.9;color:{INK};word-break:keep-all"
    H2 = f"margin:0 0 20px;font-family:{SERIF};font-weight:600;font-size:24px;line-height:1.45;color:{INK};word-break:keep-all"
    CARD = f"background-color:{SURF};border:1px solid {LINE};border-radius:14px"

    def eyebrow(t):
        return (f'<div style="display:flex;align-items:center;gap:12px;margin:0 0 20px">'
                f'<span style="font-family:{EN};font-size:13px;letter-spacing:.32em;color:{A};text-transform:uppercase;white-space:nowrap">{t}</span>'
                f'<span style="flex:1 1 auto;height:1px;background-color:{LINE}"></span></div>')

    o = []
    a = o.append
    a(f'<div style="background-color:{BG};background-image:radial-gradient(ellipse 90% 340px at 50% 0,rgba({R},.12),transparent);'
      f'color:{INK};font-family:{SANS};font-weight:300;line-height:1.85;border-radius:18px;padding:8px 20px 44px;max-width:720px;margin:0 auto">')
    # HERO
    film = m["concept_film"].split()[-1]
    lead = d.get("lead_html") or sq(esc(c["lead"]))
    lead = lead.replace("<em>", f'<span style="color:{MUTED}">').replace("</em>", "</span>")
    chips = "".join(
        (f'<span style="font-size:12.5px;padding:5px 14px;border:1px solid {LINE};border-radius:999px;color:{MUTED}">'
         + (re.sub(r"^(\d+)(cm)$", f'<b style="color:{A};font-weight:500">\\1</b>\\2', esc(s))) + "</span>") for s in c["specs"])
    a(f'<div style="text-align:center;padding:56px 0 52px">'
      f'<p style="margin:0 0 40px;font-family:{EN};font-size:12px;letter-spacing:.28em;color:{A};text-transform:uppercase">Concept Film {film} · {en}</p>'
      + hero_orb(m, disc(m["id"], m["name"], faces, 186)) +
      f'<p style="margin:0 0 8px;font-size:13px;letter-spacing:.08em;color:{MUTED}">{esc(c["title_label"])}</p>'
      f'<p style="margin:0;font-family:{SERIF};font-weight:700;font-size:40px;line-height:1.2;color:{INK}">{m["name"]}</p>'
      f'<p style="margin:6px 0 0;font-family:{EN};font-style:italic;font-size:21px;letter-spacing:.06em;color:{A}">— {m["concept_ko"]} ({en})</p>'
      f'<div style="display:flex;justify-content:center;margin-top:18px"><span style="display:inline-flex;align-items:center;gap:10px;padding:6px 16px 6px 10px;border:1px solid {LINE};border-radius:999px;font-size:13px;color:{INK}">'
      f'{emblem(m["id"], 22, A)}<b style="font-family:{EN};font-weight:600;letter-spacing:.2em;font-size:11px;color:{A}">POWER</b>{esc(m["power"]["name"])}</span></div>'
      f'<p style="margin:24px 0 0;font-size:15.5px;line-height:1.9;color:{INK};word-break:keep-all">{lead}</p>'
      f'<div style="display:flex;flex-wrap:wrap;justify-content:center;gap:8px;margin-top:24px">{chips}</div></div>')
    # OFFICIAL PROFILE
    row = lambda k, v: (f'<div style="display:flex;gap:12px;padding:4px 0"><span style="flex:0 0 56px;font-size:12px;letter-spacing:.06em;color:{FAINT};padding-top:2px">{k}</span>'  # noqa: E731
                        f'<span style="flex:1 1 auto;font-size:13.5px;color:{INK};word-break:keep-all">{v}</span></div>')
    a(f'<div style="{SEC}">' + eyebrow("Official Profile") +
      f'<div style="{CARD};padding:22px 20px;display:flex;flex-wrap:wrap;gap:18px;align-items:flex-start">{emblem(m["id"], 60, A)}<div style="flex:1 1 220px">'
      + row("포지션", esc(m["position"])) + row("신장", esc(ps["height"])) + row("상징", f'{m["concept_ko"]} {m["concept_hanja"]} · {en}')
      + row("능력", f'{esc(m["power"]["name"])}<span style="display:block;color:{MUTED};font-size:12.5px;line-height:1.7;margin-top:2px">{sq(esc(m["power"]["desc"]))}</span>')
      + row("컬러", f'<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background-color:{A};margin-right:6px"></span>{esc(ps["color_name"])}')
      + "</div></div></div>")
    # PROLOGUE
    sig = sq(esc(c["signature_line"])).replace(", ", ",<br>", 1)
    rule = f'<div style="width:36px;height:1px;background-color:{A};margin:0 auto"></div>'
    a(f'<div style="{SEC}">' + eyebrow("Prologue") +
      f'<div style="padding:28px 4px 32px;text-align:center">{rule}<p style="margin:26px 0;font-family:{SERIF};font-size:23px;line-height:1.6;color:{INK};word-break:keep-all">“{sig}”</p>{rule}</div>'
      + "".join(f'<p style="{P}">{rich(p, strong, A)}</p>' for p in c["prologue"]) + "</div>")
    # MODE
    md = c["mode"]
    ct = md["contrast"]
    li = lambda xs: "".join(f'<p style="margin:0;padding-left:12px;font-size:13.5px;line-height:1.75;color:{INK};word-break:keep-all">· {sq(esc(x))}</p>' for x in xs)  # noqa: E731
    a(f'<div style="{SEC}">' + eyebrow(esc(md["name_en"])) + f'<p style="{H2}">{esc(md["title"])}</p>'
      f'<p style="{P}">{rich(md["body_1"], strong, A)}</p>'
      f'<div style="margin:24px 0;padding:18px 20px;background-color:{SURF};border-left:2px solid {A};border-radius:0 10px 10px 0;font-family:{SERIF};font-size:16px;line-height:1.75;color:{INK};word-break:keep-all">'
      f'“{sq(esc(md["line"]))}”<span style="display:block;margin-top:8px;font-family:{SANS};font-size:12px;color:{FAINT};letter-spacing:.06em">{esc(md["line_cite"])}</span></div>'
      f'<p style="{P}">{rich(md["body_2"], strong, A)}</p>'
      f'<div style="display:flex;flex-wrap:wrap;gap:10px;margin-top:24px">'
      f'<div style="flex:1 1 220px;padding:18px;border:1px solid {HAIR};border-radius:12px;background-color:{SURF}"><p style="margin:0 0 8px;font-family:{EN};font-weight:600;font-size:13px;letter-spacing:.22em;text-transform:uppercase;color:{MUTED}">{esc(ct["public_label"])}</p>{li(ct["public"])}</div>'
      f'<div style="flex:1 1 220px;padding:18px;border:1px solid {LINE};border-radius:12px;background-color:{SURF};background-image:linear-gradient(160deg,rgba({R},.16),transparent 70%)"><p style="margin:0 0 8px;font-family:{EN};font-weight:600;font-size:13px;letter-spacing:.22em;text-transform:uppercase;color:{A}">{esc(ct["hidden_label"])}</p>{li(ct["hidden"])}</div>'
      "</div></div>")
    # EPISODES
    eps = []
    for e in c["episodes"]:
        q = (f'<p style="margin:6px 0 0;font-family:{SERIF};font-size:14.5px;line-height:1.7;color:{INK};word-break:keep-all">“{sq(esc(e["line"]))}”</p>'
             if e.get("line") else "")
        eps.append(f'<div style="{CARD};border-color:{HAIR};padding:20px;display:flex;gap:16px">'
                   f'<div style="flex:0 0 46px;font-family:{EN};line-height:1;color:{A}"><span style="display:block;font-size:11px;letter-spacing:.3em;color:{FAINT};margin-bottom:6px">EP</span><span style="font-size:34px;font-weight:500">{e["no"]}</span></div>'
                   f'<div style="flex:1 1 auto"><p style="margin:0 0 4px;font-family:{SERIF};font-size:16.5px;font-weight:600;line-height:1.5;color:{INK};word-break:keep-all">{sq(esc(e["title"]))}</p>'
                   f'<p style="margin:0;font-size:14px;line-height:1.75;color:{MUTED};word-break:keep-all">{sq(esc(e["scene"]))}</p>{q}</div></div>')
    a(f'<div style="{SEC}">' + eyebrow("Episodes") + f'<p style="{H2}">4개의 밤</p><div style="display:flex;flex-direction:column;gap:12px">' + "".join(eps) + "</div></div>")
    # WORLD
    bodies = ""
    for x in members["members"]:
        me = x["id"] == m["id"]
        dot = (f'<span style="display:block;width:30px;height:30px;border-radius:50%;background-color:#040406;box-shadow:0 0 0 1px rgba({L},.6),0 0 14px 3px rgba({R},.6)"></span>' if me
               else f'<span style="display:block;width:13px;height:13px;border-radius:50%;border:1px solid rgba(236,230,218,.35)"></span>')
        bodies += (f'<div style="display:flex;flex-direction:column;align-items:center;gap:8px;font-size:11.5px;color:{A if me else FAINT}">{dot}{x["concept_ko"]}</div>')
    a(f'<div style="{SEC}">' + eyebrow("World") + f'<p style="{H2}">{esc(g["worldview_title"])}</p><p style="{P}">{sq(esc(g["worldview"]))}</p>'
      f'<div style="display:flex;justify-content:space-between;align-items:flex-end;margin:30px 0 28px;padding:0 2px">{bodies}</div>'
      f'<p style="{P}">{rich(c["world_closing"], strong, A)}</p></div>')
    # MEMBERS
    rows = ""
    for x in members["members"]:
        me = x["id"] == m["id"]
        fc = disc(x["id"], x["name"], faces, 46)
        if me:
            fc = f'<div style="border-radius:50%;box-shadow:0 0 0 1px {A},0 0 14px rgba({R},.55)">{fc}</div>'
        tag = (f'<span style="font-size:10.5px;letter-spacing:.06em;color:{A};border:1px solid {LINE};border-radius:4px;padding:0 6px">이 스토리</span>' if me else "")
        rows += (f'<div style="display:flex;align-items:center;gap:16px;padding:12px {"12px" if me else "4px"};border-bottom:1px solid {"transparent" if me else HAIR};'
                 + (f'background-image:linear-gradient(90deg,rgba({R},.16),transparent);border-radius:10px;margin:4px 0' if me else "") + '">'
                 f'<div style="flex:0 0 46px">{fc}</div><div style="flex:1 1 auto">'
                 f'<div style="display:flex;flex-wrap:wrap;align-items:baseline;gap:4px 10px"><span style="font-family:{SERIF};font-size:16px;font-weight:600;color:{INK}">{x["name"]}</span>'
                 f'<span style="font-family:{EN};font-size:12px;letter-spacing:.16em;color:{A if me else FAINT}">{x["concept_ko"]} · {x["concept_en"].upper()}</span>{tag}</div>'
                 f'<p style="margin:2px 0 0;font-size:13.5px;line-height:1.7;color:{INK if me else MUTED};word-break:keep-all">{sq(esc(x["one_liner"]))}</p></div></div>')
    a(f'<div style="{SEC}">' + eyebrow("The Members") + f'<p style="{H2}">7인</p><div style="border-top:1px solid {HAIR}">{rows}</div></div>')
    # BGM
    al = g["album"]
    tr = ""
    for t in al["tracks"]:
        live = t["status"] == "live"
        tr += (f'<div style="display:flex;align-items:center;gap:12px;padding:13px 4px;border-bottom:1px solid {HAIR};font-size:14.5px;opacity:{1 if live else .45}">'
               f'<span style="flex:0 0 28px;font-family:{EN};font-size:15px;color:{A}">{t["no"]}</span>'
               f'<span style="flex:1 1 auto;color:{INK}">{t["ko"]}<span style="font-family:{EN};color:{FAINT};margin-left:6px">{t["en"]}</span></span>'
               f'<span style="font-size:11.5px;letter-spacing:.04em;color:{A if live else MUTED}">{TRACK_STATUS.get(t["status"], t["status"])}</span></div>')
    a(f'<div style="{SEC}">' + eyebrow("BGM") +
      f'<div style="display:flex;align-items:baseline;justify-content:space-between;margin-bottom:12px"><span style="font-family:{EN};font-size:24px;font-weight:600;letter-spacing:.14em;color:{INK}">{al["title"]}</span>'
      f'<span style="font-size:12px;color:{FAINT}">{al["label"]}</span></div>{tr}</div>')
    # PLAY GUIDE
    guide = g["play_guide"].replace(g["ooc_example"] + " 등 ", "")
    a(f'<div style="{SEC}">' + eyebrow("Play Guide") +
      f'<div style="{CARD};padding:22px 20px"><p style="margin:0;font-size:14.5px;line-height:1.85;color:{INK};word-break:keep-all">{esc(guide)}</p>'
      f'<span style="display:inline-block;margin-top:14px;font-family:{MONO};font-size:13px;color:{A};background-color:rgba({R},.08);border:1px dashed {LINE};border-radius:6px;padding:6px 12px">{esc(g["ooc_example"])}</span></div></div>')
    # FOOTER
    a(f'<div style="text-align:center;padding-top:44px;font-family:{EN};font-size:12px;letter-spacing:.24em;color:{FAINT}">'
      f'<p style="margin:0 0 12px;font-style:italic;font-size:18px;letter-spacing:.08em;color:{INK}">{esc(g["idol_concept"]["slogan_suggest"])}</p>'
      f'<b style="color:{A};font-weight:600">{en.upper()}</b> : {g["name"]} × {g["credit"]}<br>Tikitaka AI System</div>')
    a("</div>")
    return "".join(o)
