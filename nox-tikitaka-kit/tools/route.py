"""B 모드 v4 — '공략 루트' 레이아웃 (아이돌과 연애하는 연애 시뮬레이션 느낌).

게임 문법으로 구성:
  타이틀 화면(엔딩 요정 컷 + 로고 + 메뉴) → 공략 대상 정보(프로필 + 호감도 HUD = 티키타 변수)
  → 프롤로그(나레이션 박스 + 지난 10년 회상 + 대사창) → OFF STAGE(무대 위/아래 + 대사창)
  → CHAPTER 01~04(CG · 장면 · 대사창 · 선택지 2개와 수치 변화) → 엔딩 분기(잠긴 엔딩 ???)
  → 공략 TIP(COORDI NOTE) → CG 갤러리 → 다른 공략 캐릭터(ROUTE 01~07) → OST.
'낙화하는 신들'은 그룹 NOX의 세계관 컨셉으로만 표기한다 (멤버는 현실의 아이돌).
티키타 제약: 인라인 style만, position·애니메이션·가상요소·미디어쿼리 없음.
"""
import html
import re

from inline import EN, MONO, SANS, SERIF, TRACK_STATUS, esc, palette, rgb, sq, yt_id
from stage import BASE, INK, PANEL, PANEL_2, label, mix, phase_icon

# 글자 수 예산 때문에 반투명 rgba 대신 BASE 위에서 같은 색으로 보이는 hex를 쓴다
MUTED, FAINT, HAIR = "#a19d9c", "#67646a", "#232126"
MONO = "monospace"


def page(m, members, faces, src, gal=lambda mid, k: None):
    A, R, L = palette(m)
    DIM = mix(rgb(m["accent"]), (11, 10, 13), .78)
    g, c, d = members["group"], m["copy"], m.get("display", {})
    strong = d.get("strong", [])
    en, ps, t = m["concept_en"], m["profile_suggest"], m.get("tikitaka", {})
    film = m["concept_film"].split()[-1]
    LINE = f"rgba({R},.4)"
    name = m["name"]
    face = src(m["id"])
    hero = gal(m["id"], "hero") or face

    def rich(s):
        s = sq(esc(s))
        for p in strong:
            if p in s:
                s = s.replace(p, f'<strong style="font-weight:600;color:rgb({L})">{p}</strong>', 1)
        return s

    def img(u, h, pos="50% 20%", radius=0, extra=""):
        if not u:
            return f'<div style="height:{h}px;background-color:{DIM};border-radius:{radius}px"></div>'
        return (f'<img src="{html.escape(u)}" alt="" style="display:block;width:100%;height:{h}px;object-fit:cover;'
                f'object-position:{pos};border-radius:{radius}px;{extra}">')

    def talk(line, who=name, mood=""):
        """비주얼노벨 대사창: 이름표 탭 + 대사 + ▼."""
        tag = f'<span style="font-size:10.5px;font-weight:600;color:rgba(11,10,13,.6);margin-left:6px">{mood}</span>' if mood else ""
        return (f'<div style="margin:18px 0">'
                f'<div style="display:inline-block;padding:4px 14px 3px;border-radius:8px 8px 0 0;background-color:{A};color:{BASE};font-size:12.5px;font-weight:800;letter-spacing:.04em">{who}{tag}</div>'
                f'<div style="padding:14px 16px 10px;border-radius:0 10px 10px 10px;background-color:rgba(20,18,24,.92);border:1px solid {LINE};'
                f'box-shadow:0 8px 24px rgba(0,0,0,.45)">'
                f'<p style="margin:0;font-size:15px;line-height:1.8;color:{INK}">{sq(esc(line))}</p>'
                f'<p style="margin:2px 0 0;text-align:right;font-size:11px;color:{A}">▼</p></div></div>')

    def narration(html_text):
        return (f'<div style="margin:0 0 10px;padding:14px 16px;border-radius:8px;background-color:{PANEL};border-left:2px solid {HAIR}">'
                f'<p style="margin:0;font-size:14.5px;line-height:1.9;color:{MUTED}">{html_text}</p></div>')

    def choice(i, ch):
        return (f'<div style="display:flex;align-items:center;justify-content:space-between;gap:10px;margin:8px 0 0;padding:12px 14px;'
                f'border-radius:999px;background-color:{PANEL_2};border:1px solid {LINE};box-shadow:inset 0 0 18px rgba({R},.12)">'
                f'<span style="font-size:14px;color:{INK}"><b style="color:{A};margin-right:8px">{"AB"[i]}</b>{esc(ch["text"])}</span>'
                f'<span style="flex:0 0 auto;font-family:{MONO};font-size:10.5px;color:rgb({L});white-space:nowrap">{esc(ch["effect"])}</span></div>')

    SEC = f"padding:40px 18px;border-top:1px solid {HAIR}"
    o = []
    a = o.append
    a(f'<div style="max-width:680px;margin:0 auto;background-color:{BASE};color:{INK};font-family:{SANS};line-height:1.8;border-radius:14px;overflow:hidden;word-break:keep-all">')

    # ---------------------------------------------------------------- TITLE SCREEN
    pos = m["position"].replace(" · ", " / ")
    menu = [("▶", "START", d.get("start_label", "이야기를 시작한다")), ("◆", "공략", "호감도를 올리는 법"),
            ("■", "CG", f'{1 + sum(1 for k in range(1, 5) if gal(m["id"], f"ep{k}"))}장 수록'), ("◎", "OST", f'{g["album"]["label"]} [{g["album"]["title"]}]')]
    menu_html = "".join(
        f'<div style="display:flex;align-items:center;gap:12px;padding:11px 16px;margin-top:8px;border-radius:10px;'
        + (f'background-color:{A};color:{BASE}' if i == 0 else f'background-color:rgba(255,255,255,.04);border:1px solid {HAIR};color:{INK}') + '">'
        f'<span style="flex:0 0 14px;font-size:12px">{ic}</span><span style="flex:0 0 52px;font-size:12.5px;font-weight:800;letter-spacing:.12em">{k}</span>'
        f'<span style="font-size:13px;{"" if i == 0 else f"color:{MUTED}"}">{esc(v)}</span></div>'
        for i, (ic, k, v) in enumerate(menu))
    a(f'<div data-face="{m["id"]}" style="background-color:{DIM}">'
      f'<div style="display:flex;justify-content:space-between;padding:10px 14px;font-family:{MONO};font-size:10.5px;letter-spacing:.08em;color:{MUTED};background-color:{BASE}">'
      f'<span><span style="color:{A}">●</span> LOVE ROUTE {film} / 07</span><span>SAVE 01 · NEW GAME</span></div>'
      f'<div style="line-height:0">{img(hero, 440, "50% 18%")}</div>'
      f'<div style="display:flex;align-items:stretch">'
      f'<div style="flex:0 0 auto;padding:9px 12px;background-color:{A};color:{BASE};font-size:10.5px;font-weight:800;letter-spacing:.08em;line-height:1.3;display:flex;align-items:center">ENDING<br>FAIRY</div>'
      f'<div style="flex:1 1 auto;padding:8px 14px;background-color:{INK};color:{BASE}">'
      f'<span style="display:block;font-size:18px;font-weight:800;line-height:1.25">NOX {name}</span>'
      f'<span style="display:block;font-size:10.5px;font-weight:600;letter-spacing:.1em;color:#5b555b">{esc(pos)} · {m["concept_ko"]} {m["concept_hanja"]}</span></div></div></div>')
    a(f'<div style="padding:30px 18px 34px;background-color:{BASE};background-image:radial-gradient(ellipse 90% 70% at 50% 0,rgba({R},.22),transparent)">'
      f'<p style="margin:0;text-align:center;font-family:{EN};font-size:13px;letter-spacing:.5em;color:rgb({L})">NOX</p>'
      f'<p style="margin:2px 0 0;text-align:center;font-family:{EN};font-size:40px;font-weight:600;letter-spacing:.14em;line-height:1.15;color:{INK};'
      f'text-shadow:0 0 22px rgba({R},.6)">{g["album"]["title"]}</p>'
      f'<p style="margin:8px 0 0;text-align:center;font-size:13.5px;letter-spacing:.06em;color:{INK}">'
      f'<b style="color:{A}">{name} 루트</b> · {esc(d.get("route_title", m["concept_ko"]))}</p>'
      f'<p style="margin:16px 0 4px;text-align:center;font-family:{SERIF};font-size:20px;line-height:1.55;color:#fff;text-shadow:0 2px 0 #000">'
      f'“{sq(esc(c["signature_line"])).replace(", ", ",<br>", 1)}”</p>'
      f'<div style="max-width:360px;margin:22px auto 0">{menu_html}</div>'
      f'<p style="margin:18px 0 0;text-align:center;font-family:{MONO};font-size:10.5px;letter-spacing:.3em;color:{FAINT}">PRESS START</p></div>')

    # ---------------------------------------------------------------- 공략 대상 + 호감도 HUD
    rows = [("관계", esc(ps.get("relation", "")).replace("{{user}}", "당신")), ("호칭", esc(ps.get("address", "")).replace("{{user}}", "당신")),
            ("성향", esc(m["archetype_suggest"])), ("나이 · 키", f'{ps.get("age", "")}세 · {esc(ps["height"])}'), ("포지션", esc(m["position"]))]
    info = "".join(f'<div style="display:flex;gap:10px;padding:6px 0;border-bottom:1px solid {HAIR}">'
                   f'<span style="flex:0 0 58px;font-size:11.5px;color:{A}">{k}</span><span style="flex:1 1 auto;font-size:13px;color:{INK}">{v}</span></div>'
                   for k, v in rows)
    hud = ""
    for v in t.get("variables", []):
        th = re.search(r"(\d+)\s*이상", v["desc"])
        th = int(th[1]) if th else None
        start = int(v.get("start", 0))
        fill = f"linear-gradient(90deg,rgba({R},.55),{A})"
        hud += (f'<div style="padding:8px 0">'
                f'<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:5px">'
                f'<span style="font-size:13.5px;font-weight:800;color:{INK}">{esc(v["name"])}'
                f'<span style="font-size:11px;font-weight:400;color:{FAINT};margin-left:6px">{sq(esc(v["desc"].replace("{{user}}", "당신")))}</span></span>'
                f'<span style="flex:0 0 auto;font-family:{MONO};font-size:12px;color:rgb({L})">{start}<span style="color:{FAINT}">/100</span></span></div>'
                f'<div style="height:8px;border-radius:4px;background-color:rgba(255,255,255,.07);box-shadow:inset 0 0 0 1px {HAIR}">'
                f'<div style="width:{max(start, 2)}%;height:8px;border-radius:4px;background-image:{fill};box-shadow:0 0 8px {A}"></div></div>'
                + (f'<p style="margin:4px 0 0;font-size:10.5px;color:{FAINT}">{th} 이상이면 이벤트 발생</p>' if th else "") + "</div>")
    pc = (f'<div style="flex:0 0 112px;border-radius:10px;overflow:hidden;background-color:{INK};box-shadow:0 0 0 1px {LINE}">'
          f'<div style="line-height:0">{img(face, 150)}</div>'
          f'<p style="margin:0;padding:5px 8px;font-size:11px;font-weight:800;color:{BASE}">{name}<span style="float:right;font-family:{MONO};font-weight:400;color:{A}">{film}</span></p></div>')
    a(f'<div style="{SEC}">' + label("공략 대상", A, f"TARGET {film}") +
      f'<div style="display:flex;flex-wrap:wrap;gap:16px;align-items:flex-start">{pc}<div style="flex:1 1 200px;min-width:0">'
      f'<p style="margin:0 0 6px;font-size:22px;font-weight:800;color:{INK}">{name} <span style="font-family:{EN};font-style:italic;font-weight:400;font-size:15px;color:{FAINT}">{en}</span></p>'
      f'{info}</div></div>'
      f'<div style="margin-top:18px;padding:12px 14px 6px;border-radius:12px;background-color:{PANEL};box-shadow:0 0 0 1px {HAIR}">'
      f'<p style="margin:0 0 2px;font-family:{MONO};font-size:10.5px;letter-spacing:.14em;color:{A}">STATUS · 호감도</p>{hud}</div>'
      f'<p style="margin:14px 0 0;font-size:12px;line-height:1.7;color:{FAINT}">NOX CONCEPT · 세계관 속 그는 ‘{m["concept_ko"]}’의 신 — '
      f'<b style="color:{MUTED}">{esc(m["power"]["name"])}</b> {sq(esc(m["power"]["desc"]))}</p></div>')

    # ---------------------------------------------------------------- PROLOGUE (나레이션 + 회상 + 대사창)
    tl = d.get("timeline", [])
    memo = "".join(f'<div style="display:flex;gap:12px;padding:8px 0;{"" if i == 0 else f"border-top:1px dashed {HAIR};"}">'
                   f'<span style="flex:0 0 58px;font-family:{MONO};font-size:10.5px;color:{A if i == len(tl) - 1 else FAINT};padding-top:2px">{esc(x["when"])}</span>'
                   f'<p style="margin:0;font-size:13px;line-height:1.75;color:{MUTED}"><b style="color:{INK}">{esc(x["title"])}</b> — {sq(esc(x["body"]))}</p></div>'
                   for i, x in enumerate(tl))
    memo = (f'<div style="margin:16px 0;padding:12px 14px;border-radius:10px;background-color:{DIM};box-shadow:0 0 0 1px {LINE}">'
            f'<p style="margin:0 0 4px;font-family:{MONO};font-size:10.5px;letter-spacing:.14em;color:rgb({L})">MEMORY · {esc(d.get("timeline_caption", ""))}</p>{memo}</div>') if memo else ""
    pro = c["prologue"]
    a(f'<div style="{SEC}">' + label("Prologue", A, "CHAPTER 00") + narration(rich(pro[0])) + narration(rich(pro[1])) + memo
      + narration(rich(pro[2])) + narration(rich(pro[3])) + talk(c["signature_line"]) + "</div>")

    # ---------------------------------------------------------------- OFF STAGE
    md, ct = c["mode"], c["mode"]["contrast"]
    li = lambda xs, col: "".join(f'<p style="margin:0;font-size:13px;line-height:1.85;color:{col}">{sq(esc(x))}</p>' for x in xs)  # noqa: E731
    split = (f'<div style="display:flex;flex-wrap:wrap;border-radius:10px;overflow:hidden;margin:4px 0 18px">'
             f'<div style="flex:1 1 200px;padding:16px;background-color:{INK};color:{BASE}">'
             f'<p style="margin:0 0 6px;font-size:10.5px;font-weight:800;letter-spacing:.2em;color:#6b6469">○ {esc(ct["public_label"]).upper()} · 모두의 그</p>{li(ct["public"], "#2b262a")}</div>'
             f'<div style="flex:1 1 200px;padding:16px;background-color:{DIM};background-image:linear-gradient(135deg,rgba({R},.35),transparent 70%)">'
             f'<p style="margin:0 0 6px;font-size:10.5px;font-weight:800;letter-spacing:.2em;color:{A}">● {esc(ct["hidden_label"]).upper()} · 당신만 아는 그</p>{li(ct["hidden"], INK)}</div></div>')
    a(f'<div style="{SEC};background-image:linear-gradient(180deg,rgba({R},.07),transparent 40%)">' + label(f'Off Stage · {esc(md["name_en"])}', A) +
      f'<p style="margin:0 0 16px;font-size:22px;font-weight:800;line-height:1.4;color:{INK}">{esc(md["title"])}</p>'
      + split + narration(rich(md["body_1"])) + talk(md["line"], mood=esc(md["line_cite"].lstrip("— ").replace(name + ", ", ""))) + narration(rich(md["body_2"])) + "</div>")

    # ---------------------------------------------------------------- CHAPTERS
    marks, chs = d.get("episode_marks", []), d.get("choices", [])
    for i, e in enumerate(c["episodes"]):
        shot = gal(m["id"], f"ep{i + 1}")
        cg = (f'<div style="margin:0 0 14px;border-radius:10px;overflow:hidden;line-height:0;box-shadow:0 0 0 1px {LINE}">'
              f'{img(shot, 230, "50% 22%")}</div>') if shot else ""
        mk = marks[i] if i < len(marks) else ""
        head = (f'<div style="display:flex;align-items:center;gap:12px;margin:0 0 14px">{phase_icon(i, A, L)}<div>'
                f'<p style="margin:0;font-family:{MONO};font-size:10.5px;letter-spacing:.12em;color:{A}">CHAPTER {e["no"]}{" · " + esc(mk) if mk else ""}</p>'
                f'<p style="margin:0;font-size:18px;font-weight:800;line-height:1.4;color:{INK}">{sq(esc(e["title"]))}</p></div></div>')
        body = cg + narration(sq(esc(e["scene"])))
        if e.get("line"):
            body += talk(e["line"])
        if i < len(chs):
            body += (f'<p style="margin:16px 0 0;font-family:{MONO};font-size:10.5px;letter-spacing:.14em;color:{FAINT}">CHOICE</p>'
                     + "".join(choice(k, ch) for k, ch in enumerate(chs[i])))
        a(f'<div style="{SEC}">' + head + body + "</div>")

    # ---------------------------------------------------------------- ENDINGS
    ends = d.get("endings", [])
    if ends:
        cards = "".join(
            f'<div style="flex:1 1 150px;padding:14px;border-radius:10px;background-color:{PANEL};box-shadow:0 0 0 1px {HAIR}">'
            f'<p style="margin:0 0 4px;font-family:{MONO};font-size:10.5px;color:{A}">ENDING {k + 1:02d} · {esc(x["cond"])}</p>'
            f'<p style="margin:0 0 6px;font-size:15px;font-weight:800;color:{INK}">{esc(x["name"])}</p>'
            f'<div style="height:64px;border-radius:6px;background-color:{BASE};background-image:repeating-linear-gradient(45deg,rgba(255,255,255,.04) 0 6px,transparent 6px 12px);'
            f'display:flex;align-items:center;justify-content:center;font-family:{MONO};font-size:13px;letter-spacing:.3em;color:{FAINT}">???</div>'
            f'<p style="margin:8px 0 0;font-size:12px;line-height:1.6;color:{MUTED}">{sq(esc(x["hint"]))}</p></div>'
            for k, x in enumerate(ends))
        a(f'<div style="{SEC}">' + label("Ending", A, f"0 / {len(ends)} UNLOCKED") + f'<div style="display:flex;flex-wrap:wrap;gap:10px">{cards}</div></div>')

    # ---------------------------------------------------------------- 공략 TIP (COORDI NOTE)
    tips = m.get("play_tips", [])
    tip_html = "".join(
        f'<div style="display:flex;gap:12px;padding:12px 0;{"" if i == 0 else f"border-top:1px dashed {HAIR};"}">'
        f'<span style="flex:0 0 22px;height:22px;border-radius:50%;background-color:{A};color:{BASE};font-size:11.5px;font-weight:800;line-height:22px;text-align:center">{i + 1}</span>'
        f'<div style="flex:1 1 auto"><p style="margin:0 0 3px;font-size:14.5px;font-weight:700;color:{INK}">{esc(x["title"])}</p>'
        f'<p style="margin:0;font-size:13px;line-height:1.8;color:{MUTED}">{sq(esc(x["body"]))}</p></div></div>'
        for i, x in enumerate(tips))
    guide = g["play_guide"].replace(g["ooc_example"] + " 등 ", "")
    a(f'<div style="{SEC}">' + label("공략 TIP", A, "COORDI NOTE") +
      f'<div style="border-radius:12px;background-color:{PANEL};padding:6px"><div style="border:1px dashed {LINE};border-radius:9px;padding:14px 16px">'
      f'<p style="margin:0 0 4px;display:flex;justify-content:space-between;font-size:12px;font-weight:800;letter-spacing:.16em;color:{INK}">'
      f'<span>COORDI NOTE</span><span style="font-family:{MONO};font-weight:400;letter-spacing:.04em;color:{FAINT}">NOX {film} / {name}</span></p>{tip_html}'
      f'<div style="margin-top:10px;padding:12px 14px;background-color:{BASE};border-radius:8px;font-size:13px;line-height:1.8;color:{MUTED}">{esc(guide)} '
      f'<span style="display:inline-block;margin-top:6px;font-family:{MONO};font-size:12px;color:{A}">{esc(g["ooc_example"])}</span></div></div></div></div>')

    # ---------------------------------------------------------------- CG GALLERY
    cgs = [u for u in [hero] + [gal(m["id"], f"ep{k}") for k in range(1, 5)] if u]
    if len(cgs) > 1:
        tiles = "".join(f'<div style="flex:1 1 90px;max-width:160px;border-radius:8px;overflow:hidden;line-height:0;box-shadow:0 0 0 1px {LINE}">{img(u, 130, "50% 20%")}'
                        f'<p style="margin:0;padding:5px 8px;line-height:1.4;font-family:{MONO};font-size:10px;color:{MUTED};background-color:{PANEL}">CG {k + 1:02d}</p></div>'
                        for k, u in enumerate(cgs))
        locked = "".join(f'<div style="flex:1 1 90px;max-width:160px;height:150px;border-radius:8px;background-color:{PANEL};border:1px dashed {HAIR};'
                         f'display:flex;align-items:center;justify-content:center;font-family:{MONO};font-size:11px;color:{FAINT}">ENDING ???</div>'
                         for _ in ends)
        a(f'<div style="{SEC}">' + label("CG Gallery", A, f"{len(cgs)} / {len(cgs) + len(ends)}") +
          f'<div style="display:flex;flex-wrap:wrap;gap:8px;justify-content:center">{tiles}{locked}</div></div>')

    # ---------------------------------------------------------------- ROUTE SELECT (7인)
    routes = ""
    for x in members["members"]:
        me = x["id"] == m["id"]
        s_ = src(x["id"])
        routes += (f'<div data-face="{x["id"]}" style="flex:1 1 64px;max-width:120px;border-radius:8px;overflow:hidden;background-color:{PANEL};'
                   f'box-shadow:0 0 0 {"2px " + A if me else "1px " + HAIR}">'
                   f'<div style="line-height:0">{img(s_, 104)}</div><div style="padding:6px 8px 8px">'
                   f'<span style="display:block;font-family:{MONO};font-size:9.5px;color:{A if me else FAINT}">ROUTE {x["concept_film"].split()[-1]}</span>'
                   f'<span style="display:block;font-size:12.5px;font-weight:700;color:{INK}">{x["name"]}</span>'
                   f'<span style="display:block;font-size:10px;color:{A if me else FAINT}">{"플레이 중" if me else x["concept_ko"]}</span></div></div>')
    a(f'<div style="{SEC};background-image:radial-gradient(ellipse 80% 50% at 50% 0,rgba({R},.12),transparent)">' + label("공략 캐릭터 선택", A, "NOX 01—07") +
      f'<p style="margin:0 0 4px;font-family:{SERIF};font-size:19px;font-weight:600;color:{INK}">{esc(g["worldview_title"])}</p>'
      f'<p style="margin:0 0 16px;font-size:13px;line-height:1.85;color:{MUTED}">{sq(esc(g["worldview"]))} '
      f'<span style="color:{FAINT}">— NOX의 세계관 컨셉</span></p>'
      f'<div style="display:flex;flex-wrap:wrap;gap:8px;justify-content:center">{routes}</div></div>')

    # ---------------------------------------------------------------- OST
    al = g["album"]
    tr = ""
    for i, t_ in enumerate(al["tracks"]):
        live = t_["status"] == "live"
        url, vid = t_.get("url"), yt_id(t_.get("url"))
        top = "" if i == 0 else f"border-top:1px solid {HAIR};"
        title = f'{t_["ko"]}<span style="font-family:{EN};font-style:italic;color:{FAINT};margin-left:6px">{t_["en"]}</span>'
        if live and url:
            thumb = (f'<a href="{html.escape(url)}" style="flex:0 0 84px;display:block;border-radius:4px;overflow:hidden;line-height:0;box-shadow:0 0 0 1px {LINE}">'
                     f'<img src="https://img.youtube.com/vi/{vid}/mqdefault.jpg" alt="{t_["ko"]}" width="84" height="48" style="display:block;width:84px;height:48px;object-fit:cover"></a>') if vid else ""
            tr += (f'<div style="display:flex;align-items:center;gap:12px;padding:10px 0;{top}">'
                   f'<span style="flex:0 0 20px;font-family:{MONO};font-size:12px;color:{A}">{t_["no"]}</span>{thumb}'
                   f'<a href="{html.escape(url)}" style="flex:1 1 auto;color:{INK};text-decoration:none;font-size:14px">{title}'
                   f'<span style="display:block;margin-top:2px;font-size:11px;letter-spacing:.06em;color:{A}">▶ PLAY</span></a></div>')
        else:
            tr += (f'<div style="display:flex;align-items:center;gap:12px;padding:10px 0;{top}opacity:{1 if live else .45}">'
                   f'<span style="flex:0 0 20px;font-family:{MONO};font-size:12px;color:{A}">{t_["no"]}</span>'
                   f'<span style="flex:1 1 auto;font-size:14px;color:{INK}">{title}</span>'
                   f'<span style="font-size:11px;color:{FAINT}">{TRACK_STATUS.get(t_["status"], t_["status"])}</span></div>')
    a(f'<div style="{SEC}">' + label("OST", A, al["label"]) +
      f'<p style="margin:0 0 10px;font-family:{EN};font-size:30px;font-weight:600;letter-spacing:.16em;color:{INK}">{al["title"]}</p>{tr}</div>')

    # ---------------------------------------------------------------- END
    a(f'<div style="padding:30px 18px 34px;text-align:center;background-color:{DIM};background-image:linear-gradient(180deg,{BASE},transparent)">'
      f'<p style="margin:0 0 6px;font-family:{MONO};font-size:10.5px;letter-spacing:.3em;color:rgb({L})">TO BE CONTINUED</p>'
      f'<p style="margin:0 0 12px;font-family:{EN};font-style:italic;font-size:19px;letter-spacing:.06em;color:{INK}">{esc(g["idol_concept"]["slogan_suggest"])}</p>'
      f'<p style="margin:0;font-size:11.5px;letter-spacing:.2em;color:{MUTED}"><b style="color:{A}">{en.upper()}</b> : {g["name"]} × {g["credit"]}<br>Tikitaka AI System</p></div>')
    a("</div>")
    return "".join(o)
