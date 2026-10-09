"""B 모드 v3 — 'ON AIR' 무대 레이아웃 (NOX 세계관 전용 디자인).

모티프는 전부 NOX 세계에서 가져온다:
  음악방송 생방송 화면(LIVE 바·엔딩 요정 캠·방송 자막 띠) → NOX 컨셉 띠 → IDOL PROFILE × NOX CONCEPT
  ('낙화하는 신들'은 그룹 NOX의 세계관 컨셉. 멤버는 실제 신이 아니라 무대 위에서 그 역할을 맡은 현실의 아이돌)
  → 10년 타임라인(display.timeline) → ON STAGE / OFF STAGE 분할 + 새벽 메신저 말풍선
  → 에피소드 = 상징의 4단계(display.episode_marks, 일식이면 제1접촉→부분식→개기식→다이아몬드 링)
  → COORDI NOTE(의상 태그) 공략 가이드 + 변수 게이지 → 낙화하는 7신 → 포토카드 라인업 → 앨범 트랙리스트 + 바코드.
티키타 제약: 인라인 style만, position·애니메이션·가상요소·미디어쿼리 없음 (inline.py 헬퍼 재사용).
"""
import html
import re

from inline import EN, MONO, SANS, SERIF, TRACK_STATUS, esc, palette, rgb, sq, yt_id

BASE, PANEL, PANEL_2 = "#0b0a0d", "#141218", "#1b1820"
INK = "#f1ece8"
MUTED, FAINT, HAIR = "rgba(241,236,232,.64)", "rgba(241,236,232,.4)", "rgba(241,236,232,.1)"
COND = "'Pretendard','Noto Sans KR','Apple SD Gothic Neo',sans-serif"


def mix(c1, c2, t):
    return "#%02x%02x%02x" % tuple(round(a + (b - a) * t) for a, b in zip(c1, c2))


def label(text, A, right=""):
    r = f'<span style="font-family:{MONO};font-size:10.5px;letter-spacing:.08em;color:{FAINT}">{right}</span>' if right else ""
    return (f'<div style="display:flex;justify-content:space-between;align-items:center;gap:10px;margin:0 0 16px">'
            f'<span style="display:flex;align-items:center;gap:8px;font-size:11px;font-weight:700;letter-spacing:.22em;color:{A};text-transform:uppercase">'
            f'<span style="display:inline-block;width:14px;height:2px;background-color:{A}"></span>{text}</span>{r}</div>')


def phase_icon(k, A, L):
    """상징의 4단계 아이콘 — 밝은 원판을 검은 원이 덮어 가는 모양 (일식 접촉 단계)."""
    cx = [44, 30, 18, 20][k]
    extra = ", radial-gradient(circle 3px at 30px 7px,#fff 99%,transparent 100%)" if k == 3 else ""
    glow = f"box-shadow:0 0 12px 2px rgba({L},.55);" if k >= 2 else ""
    return (f'<span style="flex:0 0 36px;display:block;width:36px;height:36px;border-radius:50%;background-color:{A};{glow}'
            f'background-image:radial-gradient(circle 17px at {cx}px 18px,{BASE} 99%,transparent 100%){extra}"></span>')


def page(m, members, faces, src):
    A, R, L = palette(m)
    DIM = mix(rgb(m["accent"]), (11, 10, 13), .78)   # 포인트 컬러가 스민 어두운 면
    g, c, d = members["group"], m["copy"], m.get("display", {})
    strong = d.get("strong", [])
    en, ps, t = m["concept_en"], m["profile_suggest"], m.get("tikitaka", {})
    film = m["concept_film"].split()[-1]
    LINE = f"rgba({R},.35)"

    def rich(s):
        s = sq(esc(s))
        for p in strong:
            if p in s:
                s = s.replace(p, f'<strong style="font-weight:600;color:rgb({L})">{p}</strong>', 1)
        return s

    P = f"margin:0 0 14px;font-size:15px;line-height:1.95;color:{INK};word-break:keep-all"
    SEC = f"padding:40px 20px;border-top:1px solid {HAIR}"
    o = []
    a = o.append
    a(f'<div style="max-width:680px;margin:0 auto;background-color:{BASE};color:{INK};font-family:{SANS};line-height:1.8;border-radius:14px;overflow:hidden">')

    # ---------------------------------------------------------------- ON AIR
    a(f'<div style="display:flex;justify-content:space-between;align-items:center;gap:10px;padding:12px 16px;font-size:10.5px;letter-spacing:.14em;color:{MUTED}">'
      f'<span style="display:flex;align-items:center;gap:8px"><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background-color:{A};box-shadow:0 0 8px {A}"></span>'
      f'<b style="color:{INK};letter-spacing:.2em">LIVE</b>NOX COMEBACK</span>'
      f'<span style="font-family:{MONO};letter-spacing:.04em">CF.{film} 02:57:14</span></div>')
    cover = src(m["id"])
    img = (f'<img src="{html.escape(cover)}" alt="{m["name"]}" style="display:block;width:100%;height:380px;object-fit:cover;object-position:50% 22%">' if cover else
           f'<div style="height:300px;background-color:{DIM}"></div>')
    pos = m["position"].replace(" · ", " / ")
    a(f'<div style="padding:0 12px">'
      f'<div data-face="{m["id"]}" style="border:1px solid {LINE};border-radius:6px;overflow:hidden;background-color:{PANEL}">'
      f'<div style="display:flex;justify-content:space-between;padding:7px 12px;font-family:{MONO};font-size:10.5px;letter-spacing:.06em;color:{MUTED};background-color:{PANEL}">'
      f'<span><span style="color:{A}">●</span> REC  ENDING FAIRY CAM</span><span>4K · 59.94</span></div>'
      f'<div style="line-height:0;background-color:{DIM}">{img}</div>'
      f'<div style="display:flex;align-items:stretch">'
      f'<div style="flex:0 0 auto;padding:10px 12px;background-color:{A};color:{BASE};font-size:11px;font-weight:800;letter-spacing:.08em;line-height:1.3;display:flex;align-items:center">ENDING<br>FAIRY</div>'
      f'<div style="flex:1 1 auto;padding:9px 14px;background-color:{INK};color:{BASE}">'
      f'<span style="display:block;font-size:19px;font-weight:800;line-height:1.25;letter-spacing:-.01em">NOX {m["name"]}</span>'
      f'<span style="display:block;font-size:11px;font-weight:600;letter-spacing:.1em;color:#5b555b">{esc(pos)} · {m["concept_ko"]} {m["concept_hanja"]}</span></div></div></div></div>')
    # 자막
    a(f'<div style="padding:30px 22px 34px;text-align:center">'
      f'<p style="margin:0;font-family:{SERIF};font-size:27px;font-weight:600;line-height:1.5;color:#fff;text-shadow:0 2px 0 #000,0 0 18px rgba({R},.55);word-break:keep-all">“{sq(esc(c["signature_line"])).replace(", ", ",<br>", 1)}”</p>'
      f'<p style="margin:10px 0 0;font-family:{MONO};font-size:11px;letter-spacing:.08em;color:{FAINT}">— {m["name"]}, {esc(c["title_label"])}</p>'
      f'<p style="margin:18px 0 0;font-size:14.5px;line-height:1.85;color:{MUTED};word-break:keep-all">{sq(esc(c["lead"]))}</p></div>')

    # ---------------------------------------------------------------- CONCEPT 띠 (그룹 세계관 속 역할)
    big = phase_icon(2, A, L).replace("flex:0 0 36px;", "flex:0 0 64px;").replace("width:36px;height:36px", "width:64px;height:64px").replace("circle 17px at 18px 18px", "circle 30px at 32px 32px")
    a(f'<div style="margin:0 12px;padding:20px 18px;border-radius:10px;background-color:{DIM};'
      f'background-image:radial-gradient(circle at 15% 50%,rgba({R},.45),transparent 45%),repeating-linear-gradient(0deg,rgba(255,255,255,.025) 0 1px,transparent 1px 4px);'
      f'display:flex;gap:18px;align-items:center;box-shadow:0 0 0 1px {LINE}">{big}'
      f'<div style="flex:1 1 auto"><p style="margin:0 0 4px;font-family:{MONO};font-size:10.5px;letter-spacing:.14em;color:rgb({L})">NOX CONCEPT · 落花記錄 No.{film}</p>'
      f'<p style="margin:0 0 4px;font-family:{SERIF};font-size:17px;font-weight:600;line-height:1.5;color:{INK};word-break:keep-all">NOX 세계관 속, 그의 이름은 ‘{m["concept_ko"]}’의 신.</p>'
      f'<p style="margin:0;font-size:12.5px;line-height:1.7;color:{MUTED};word-break:keep-all"><b style="color:{A}">{esc(m["power"]["name"])}</b> — {sq(esc(m["power"]["desc"]))}</p></div></div>')

    # ---------------------------------------------------------------- PROFILE (포토카드 + 데이터 시트)
    def sheet(rows, key_col):
        return "".join(f'<div style="display:flex;gap:12px;padding:7px 0;border-bottom:1px solid {HAIR}">'
                       f'<span style="flex:0 0 62px;font-family:{MONO};font-size:10.5px;letter-spacing:.06em;color:{key_col};padding-top:3px">{k}</span>'
                       f'<span style="flex:1 1 auto;font-size:13.5px;color:{INK};word-break:keep-all">{v}</span></div>' for k, v in rows)
    idol = sheet([("POSITION", esc(m["position"])), ("HEIGHT", esc(ps["height"])), ("AGE", f'{ps.get("age", "")}세'),
                  ("TYPE", esc(m["archetype_suggest"])), ("TO YOU", esc(ps.get("relation", "")).replace("{{user}}", "당신"))], FAINT)
    divine = sheet([("SYMBOL", f'{m["concept_ko"]} {m["concept_hanja"]} · {en}'), ("POWER", esc(m["power"]["name"])),
                    ("FILM", f'Concept Film {film} / 07'),
                    ("COLOR", f'<span style="display:inline-block;width:10px;height:10px;border-radius:2px;background-color:{A};margin-right:6px"></span>{esc(ps["color_name"])}')], A)
    pc_img = (f'<img src="{html.escape(cover)}" alt="" style="display:block;width:100%;height:170px;object-fit:cover;object-position:50% 20%">' if cover
              else f'<div style="height:170px;background-color:{DIM}"></div>')
    photocard = (f'<div style="flex:0 0 120px;border-radius:10px;overflow:hidden;background-color:{INK};box-shadow:0 0 0 1px {LINE},0 10px 30px rgba(0,0,0,.5)">'
                 f'<div style="line-height:0">{pc_img}</div>'
                 f'<div style="display:flex;justify-content:space-between;align-items:center;padding:6px 9px;color:{BASE}">'
                 f'<span style="font-size:11.5px;font-weight:800">{m["name"]}</span><span style="font-family:{MONO};font-size:9.5px;color:{A}">NOX {film}</span></div></div>')
    head = lambda t1, t2, col: (f'<p style="margin:0 0 6px;display:flex;justify-content:space-between;font-size:10.5px;font-weight:800;letter-spacing:.2em;color:{col}">'  # noqa: E731
                                f'<span>{t1}</span><span style="font-family:{SERIF};letter-spacing:.1em">{t2}</span></p>')
    a(f'<div style="{SEC}">' + label("Profile", A, "IDOL × CONCEPT") +
      f'<div style="display:flex;flex-wrap:wrap;gap:12px">'
      f'<div style="flex:1 1 260px;padding:16px;border-radius:10px;background-color:{PANEL}">' + head("IDOL PROFILE", "NOX " + film, MUTED) +
      f'<div style="display:flex;flex-wrap:wrap;gap:14px;align-items:flex-start">{photocard}<div style="flex:1 1 170px;min-width:0">{idol}</div></div></div>'
      f'<div style="flex:1 1 220px;padding:16px;border-radius:10px;background-color:{DIM};'
      f'background-image:radial-gradient(circle at 85% 15%,rgba({R},.35),transparent 55%);box-shadow:0 0 0 1px {LINE}">' + head("NOX CONCEPT", m["concept_hanja"], A) + divine +
      f'<p style="margin:10px 0 0;font-size:12.5px;line-height:1.75;color:{MUTED};word-break:keep-all">{sq(esc(m["power"]["desc"]))}</p></div></div></div>')

    # ---------------------------------------------------------------- PROLOGUE (+ 타임라인)
    tl = d.get("timeline", [])
    tl_html = ""
    for i, x in enumerate(tl):
        last = i == len(tl) - 1
        dot = (f'<span style="display:block;width:11px;height:11px;border-radius:50%;margin-left:-6px;'
               + (f'background-color:{A};box-shadow:0 0 10px {A}' if last else f'background-color:{BASE};border:1px solid {A}') + '"></span>')
        tl_html += (f'<div style="display:flex;gap:14px">'
                    f'<span style="flex:0 0 62px;font-family:{MONO};font-size:11px;color:{A if last else FAINT};padding-top:1px;text-align:right">{esc(x["when"])}</span>'
                    f'<div style="flex:1 1 auto;border-left:1px solid {LINE if not last else "transparent"};padding:0 0 {0 if last else 18}px 16px">'
                    f'<div style="display:flex;align-items:center;gap:0;margin:2px 0 4px -16px">{dot}'
                    f'<span style="margin-left:10px;font-size:14px;font-weight:700;color:{INK}">{esc(x["title"])}</span></div>'
                    f'<p style="margin:0;font-size:13.5px;line-height:1.8;color:{MUTED};word-break:keep-all">{sq(esc(x["body"]))}</p></div></div>')
    if tl_html:
        tl_html = f'<div style="margin:6px 0 28px;padding:20px 16px;background-color:{PANEL};border-radius:10px">{tl_html}</div>'
    a(f'<div style="{SEC}">' + label("Prologue", A, d.get("timeline_caption", "")) + tl_html
      + "".join(f'<p style="{P}">{rich(p)}</p>' for p in c["prologue"]) + "</div>")

    # ---------------------------------------------------------------- OFF STAGE (분할 화면 + 메신저)
    md, ct = c["mode"], c["mode"]["contrast"]
    li = lambda xs, col: "".join(f'<p style="margin:0;font-size:13px;line-height:1.85;color:{col};word-break:keep-all">{sq(esc(x))}</p>' for x in xs)  # noqa: E731
    split = (f'<div style="display:flex;flex-wrap:wrap;border-radius:10px;overflow:hidden;margin:4px 0 24px">'
             f'<div style="flex:1 1 200px;padding:18px;background-color:{INK};color:{BASE}">'
             f'<p style="margin:0 0 8px;font-size:10.5px;font-weight:800;letter-spacing:.2em;color:#6b6469">○ {esc(ct["public_label"]).upper()}</p>{li(ct["public"], "#2b262a")}</div>'
             f'<div style="flex:1 1 200px;padding:18px;background-color:{DIM};background-image:linear-gradient(135deg,rgba({R},.35),transparent 70%)">'
             f'<p style="margin:0 0 8px;font-size:10.5px;font-weight:800;letter-spacing:.2em;color:{A}">● {esc(ct["hidden_label"]).upper()}</p>{li(ct["hidden"], INK)}</div></div>')
    av = (f'<img src="{html.escape(cover)}" alt="" style="width:34px;height:34px;border-radius:50%;object-fit:cover;object-position:50% 20%;display:block">' if cover
          else f'<span style="display:block;width:34px;height:34px;border-radius:50%;background-color:{DIM}"></span>')
    chat = (f'<div style="margin:22px 0;padding:16px;background-color:{PANEL};border-radius:12px">'
            f'<p style="margin:0 0 12px;text-align:center;font-size:11px;color:{FAINT}">{esc(md["line_cite"].lstrip("— "))}</p>'
            f'<div style="display:flex;gap:10px;align-items:flex-start"><div style="flex:0 0 34px">{av}</div><div style="flex:1 1 auto">'
            f'<p style="margin:0 0 4px;font-size:12px;color:{MUTED}">{m["name"][1:]}</p>'
            f'<div style="display:flex;align-items:flex-end;gap:6px"><span style="display:inline-block;max-width:86%;padding:10px 13px;border-radius:4px 14px 14px 14px;'
            f'background-color:{PANEL_2};border:1px solid {LINE};font-size:14.5px;line-height:1.7;color:{INK};word-break:keep-all">{sq(esc(md["line"]))}</span>'
            f'<span style="font-size:10px;line-height:1.3;color:{FAINT};white-space:nowrap"><span style="color:{A}">1</span><br>오전 1:12</span></div></div></div></div>')
    a(f'<div style="{SEC};background-color:{BASE};background-image:linear-gradient(180deg,rgba({R},.07),transparent 40%)">'
      + label(f'Off Stage · {esc(md["name_en"])}', A) +
      f'<p style="margin:0 0 18px;font-size:23px;font-weight:800;line-height:1.4;color:{INK};word-break:keep-all">{esc(md["title"])}</p>'
      + split + f'<p style="{P}">{rich(md["body_1"])}</p>' + chat + f'<p style="{P}">{rich(md["body_2"])}</p></div>')

    # ---------------------------------------------------------------- EPISODES (상징의 4단계)
    marks = d.get("episode_marks", [])
    eps = ""
    for i, e in enumerate(c["episodes"]):
        mk = f'<span style="font-family:{MONO};font-size:10.5px;letter-spacing:.06em;color:{A}">EP {e["no"]}' + (f' · {esc(marks[i])}' if i < len(marks) else "") + "</span>"
        q = (f'<p style="margin:8px 0 0;padding-left:10px;border-left:2px solid {A};font-family:{SERIF};font-size:14px;line-height:1.75;color:{INK};word-break:keep-all">{sq(esc(e["line"]))}</p>'
             if e.get("line") else "")
        eps += (f'<div style="display:flex;gap:14px;padding:18px 0;{"" if i == 0 else f"border-top:1px solid {HAIR};"}">{phase_icon(i, A, L)}'
                f'<div style="flex:1 1 auto">{mk}<p style="margin:2px 0 6px;font-size:16px;font-weight:700;line-height:1.5;color:{INK};word-break:keep-all">{sq(esc(e["title"]))}</p>'
                f'<p style="margin:0;font-size:13.5px;line-height:1.8;color:{MUTED};word-break:keep-all">{sq(esc(e["scene"]))}</p>{q}</div></div>')
    a(f'<div style="{SEC}">' + label("Episodes", A, d.get("episode_caption", "4 NIGHTS")) + eps + "</div>")

    # ---------------------------------------------------------------- COORDI NOTE (공략 + 변수 게이지)
    tips = m.get("play_tips", [])
    tip_html = "".join(
        f'<div style="display:flex;gap:12px;padding:12px 0;{"" if i == 0 else f"border-top:1px dashed {HAIR};"}">'
        f'<span style="flex:0 0 18px;height:18px;margin-top:3px;border:1.5px solid {A};border-radius:3px;font-size:11px;line-height:15px;text-align:center;color:{A}">{i + 1}</span>'
        f'<div style="flex:1 1 auto"><p style="margin:0 0 3px;font-size:14.5px;font-weight:700;color:{INK};word-break:keep-all">{esc(x["title"])}</p>'
        f'<p style="margin:0;font-size:13px;line-height:1.8;color:{MUTED};word-break:keep-all">{sq(esc(x["body"]))}</p></div></div>'
        for i, x in enumerate(tips))
    gauges = ""
    for v in t.get("variables", []):
        th = re.search(r"(\d+)\s*이상", v["desc"])
        th = int(th[1]) if th else None
        bar = (f'background-color:{HAIR};background-image:linear-gradient(90deg,rgba({R},.25),{A})' if th is None else
               f'background-color:{HAIR};background-image:linear-gradient(90deg,rgba({R},.25) 0,rgba({R},.6) {th}%,{A} {th}%,{A} 100%)')
        mark = (f'<span style="display:block;margin-left:{th}%;width:2px;height:6px;background-color:{INK}"></span>' if th else "")
        gauges += (f'<div style="padding:10px 0">'
                   f'<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:6px">'
                   f'<span style="font-size:14px;font-weight:700;color:{INK}">{esc(v["name"])} <span style="font-family:{MONO};font-size:10.5px;font-weight:400;color:{FAINT}">{esc(v["key"])}</span></span>'
                   f'<span style="font-family:{MONO};font-size:10.5px;color:{FAINT}">{esc(v["range"])}</span></div>'
                   f'<div style="height:6px;border-radius:3px;{bar}"></div>{mark}'
                   f'<p style="margin:6px 0 0;font-size:12.5px;line-height:1.7;color:{MUTED};word-break:keep-all">{sq(esc(v["desc"].replace("{{user}}", "당신")))}</p></div>')
    guide = g["play_guide"].replace(g["ooc_example"] + " 등 ", "")
    tag = (f'<div style="border-radius:12px;background-color:{PANEL};padding:6px">'
           f'<div style="border:1px dashed {LINE};border-radius:9px;padding:16px 16px 14px">'
           f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">'
           f'<span style="font-size:13px;font-weight:800;letter-spacing:.16em;color:{INK}">COORDI NOTE</span>'
           f'<span style="display:flex;align-items:center;gap:8px;font-family:{MONO};font-size:10.5px;color:{FAINT}">NOX {film} / {m["name"]}'
           f'<span style="display:inline-block;width:12px;height:12px;border-radius:50%;border:1.5px solid {FAINT}"></span></span></div>'
           + tip_html
           + (f'<div style="margin-top:8px;padding-top:6px;border-top:1px solid {HAIR}">{gauges}</div>' if gauges else "")
           + f'<div style="margin-top:10px;padding:12px 14px;background-color:{BASE};border-radius:8px;font-size:13px;line-height:1.8;color:{MUTED};word-break:keep-all">{esc(guide)} '
             f'<span style="display:inline-block;margin-top:6px;font-family:{MONO};font-size:12px;color:{A}">{esc(g["ooc_example"])}</span></div></div></div>')
    a(f'<div style="{SEC}">' + label("How to Play", A) + tag + "</div>")

    # ---------------------------------------------------------------- WORLD
    bodies = ""
    for x in members["members"]:
        me = x["id"] == m["id"]
        dot = (f'<span style="display:block;width:26px;height:26px;border-radius:50%;background-color:{BASE};box-shadow:0 0 0 1px rgb({L}),0 0 14px 3px rgba({R},.7)"></span>' if me
               else f'<span style="display:block;width:10px;height:10px;border-radius:50%;border:1px solid {FAINT}"></span>')
        bodies += f'<div style="display:flex;flex-direction:column;align-items:center;gap:8px;font-size:11px;color:{A if me else FAINT}">{dot}{x["concept_ko"]}</div>'
    a(f'<div style="{SEC};background-image:radial-gradient(ellipse 80% 60% at 50% 100%,rgba({R},.14),transparent)">' + label("NOX Concept", A, "七神落花") +
      f'<p style="margin:0 0 14px;font-family:{SERIF};font-size:22px;font-weight:600;color:{INK}">{esc(g["worldview_title"])}</p>'
      f'<p style="{P};color:{MUTED}">{sq(esc(g["worldview"]))}</p>'
      f'<div style="display:flex;justify-content:space-between;align-items:flex-end;margin:26px 2px">{bodies}</div>'
      f'<p style="{P}">{rich(c["world_closing"])}</p></div>')

    # ---------------------------------------------------------------- LINE-UP (포토카드)
    cards = ""
    for x in members["members"]:
        me = x["id"] == m["id"]
        s_ = src(x["id"])
        im = (f'<img src="{html.escape(s_)}" alt="{x["name"]}" style="display:block;width:100%;height:104px;object-fit:cover;object-position:50% 20%">' if s_
              else f'<div style="height:104px;background-color:{PANEL_2}"></div>')
        cards += (f'<div data-face="{x["id"]}" style="flex:1 1 64px;max-width:120px;border-radius:8px;overflow:hidden;background-color:{PANEL};'
                  f'box-shadow:0 0 0 1px {A if me else HAIR}">'
                  f'<div style="line-height:0">{im}</div><div style="padding:7px 8px 8px">'
                  f'<span style="display:block;font-size:12.5px;font-weight:700;color:{INK}">{x["name"]}</span>'
                  f'<span style="display:block;font-size:10px;letter-spacing:.06em;color:{A if me else FAINT}">{"THIS STORY" if me else x["concept_ko"] + " · " + x["concept_en"].upper()}</span></div></div>')
    lines = "".join(f'<p style="margin:0;padding:6px 0;border-top:1px solid {HAIR};font-size:12.5px;line-height:1.7;color:{MUTED};word-break:keep-all">'
                    f'<b style="color:{A if x["id"] == m["id"] else INK};font-weight:700;margin-right:6px">{x["name"]}</b>{sq(esc(x["one_liner"]))}</p>' for x in members["members"])
    a(f'<div style="{SEC}">' + label("Line-up", A, "NOX 01—07") +
      f'<div style="display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin-bottom:18px">{cards}</div>{lines}</div>')

    # ---------------------------------------------------------------- ALBUM
    al = g["album"]
    tr = ""
    for i, t_ in enumerate(al["tracks"]):
        live = t_["status"] == "live"
        url, vid = t_.get("url"), yt_id(t_.get("url"))
        top = "" if i == 0 else f"border-top:1px solid {HAIR};"
        title = f'{t_["ko"]}<span style="font-family:{EN};font-style:italic;color:{FAINT};margin-left:6px">{t_["en"]}</span>'
        if live and url:
            thumb = (f'<a href="{html.escape(url)}" style="flex:0 0 88px;display:block;border-radius:4px;overflow:hidden;line-height:0;box-shadow:0 0 0 1px {LINE}">'
                     f'<img src="https://img.youtube.com/vi/{vid}/mqdefault.jpg" alt="{t_["ko"]}" width="88" height="50" style="display:block;width:88px;height:50px;object-fit:cover"></a>') if vid else ""
            tr += (f'<div style="display:flex;align-items:center;gap:12px;padding:11px 0;{top}">'
                   f'<span style="flex:0 0 20px;font-family:{MONO};font-size:12px;color:{A}">{t_["no"]}</span>{thumb}'
                   f'<a href="{html.escape(url)}" style="flex:1 1 auto;color:{INK};text-decoration:none;font-size:14.5px;word-break:keep-all">{title}'
                   f'<span style="display:block;margin-top:2px;font-size:11px;letter-spacing:.06em;color:{A}">▶ PLAY ON YOUTUBE</span></a></div>')
        else:
            tr += (f'<div style="display:flex;align-items:center;gap:12px;padding:11px 0;{top}opacity:{1 if live else .45}">'
                   f'<span style="flex:0 0 20px;font-family:{MONO};font-size:12px;color:{A}">{t_["no"]}</span>'
                   f'<span style="flex:1 1 auto;font-size:14.5px;color:{INK}">{title}</span>'
                   f'<span style="font-size:11px;color:{FAINT}">{TRACK_STATUS.get(t_["status"], t_["status"])}</span></div>')
    barcode = (f'<div style="display:flex;align-items:flex-end;justify-content:space-between;gap:12px;margin-top:20px">'
               f'<div><span style="display:block;width:150px;height:30px;background-image:repeating-linear-gradient(90deg,{INK} 0 2px,transparent 2px 4px,{INK} 4px 5px,transparent 5px 8px,{INK} 8px 11px,transparent 11px 13px)"></span>'
               f'<span style="display:block;margin-top:4px;font-family:{MONO};font-size:10px;letter-spacing:.2em;color:{FAINT}">8 809 2026 1009 0{film}</span></div>'
               f'<span style="font-family:{MONO};font-size:10px;color:{FAINT};text-align:right">{al["label"].upper()}<br>VER. {en.upper()}</span></div>')
    a(f'<div style="{SEC}">' + label("Now Playing", A, al["label"]) +
      f'<p style="margin:0 0 14px;font-family:{EN};font-size:34px;font-weight:600;letter-spacing:.16em;line-height:1.1;color:{INK}">{al["title"]}</p>' + tr + barcode + "</div>")

    # ---------------------------------------------------------------- END CARD
    a(f'<div style="padding:34px 20px 36px;text-align:center;background-color:{DIM};background-image:linear-gradient(180deg,{BASE},transparent)">'
      f'<p style="margin:0 0 12px;font-family:{EN};font-style:italic;font-size:20px;letter-spacing:.06em;color:{INK}">{esc(g["idol_concept"]["slogan_suggest"])}</p>'
      f'<p style="margin:0;font-size:11.5px;letter-spacing:.2em;color:{MUTED}"><b style="color:{A}">{en.upper()}</b> : {g["name"]} × {g["credit"]}<br>Tikitaka AI System</p></div>')
    a("</div>")
    return "".join(o)
