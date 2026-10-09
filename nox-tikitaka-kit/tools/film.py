"""B 모드 v5 — 통합형 '컨셉 필름' 레이아웃 (사용자 선택: C 티저 필름으로 시작 + A 프라이빗 메시지 + B 인터뷰).

영화 한 편처럼 흐른다:
  OPENING(C) 컨셉 필름 타이틀 · 시네마 비율 메인 컷 · 자막 명대사 · EN 타이틀
  → PRIVATE MESSAGE(A) 폰 화면 속 새벽 대화 (display.chat)
  → INTERVIEW(B) '국민 남친의 가면' 기사: 프롤로그 본문 + 프로필 박스 + ON/OFF STAGE + Q&A (display.interview)
  → SCENES(C) 에피소드 4장면 (display.scene_slugs)
  → 공략 노트(A 톤) 팁 + 티키타 변수
  → CAST · OST · END CREDITS(C)
'낙화하는 신들'은 그룹 NOX의 세계관 컨셉. 티키타 제약: 인라인 style만 (position·애니메이션·가상요소·미디어쿼리 없음).
"""
import html

from inline import EN, SANS, SERIF, TRACK_STATUS, esc, palette, rgb, sq, yt_id

MONO = "monospace"
BLK, INK, MUT, DIM_T, HAIR = "#060507", "#eeeae7", "#8e8a8d", "#5c585c", "#1f1d21"      # 필름(어두운) 토큰
PH_BG, PH_INK, PH_MUT, PH_LINE = "#f3eff1", "#1d1a1c", "#8a8287", "#e4dde1"             # 폰(밝은) 토큰
PAPER, P_INK, P_MUT, P_LINE = "#f7f5f2", "#141214", "#5f5a5d", "#dcd7d2"                 # 매거진(종이) 토큰


def page(m, members, faces, src, gal=lambda mid, k: None):
    A, R, L = palette(m)
    g, c, d = members["group"], m["copy"], m.get("display", {})
    en, ps, t = m["concept_en"], m["profile_suggest"], m.get("tikitaka", {})
    film = m["concept_film"].split()[-1]
    name, mid = m["name"], m["id"]
    face = src(mid)
    hero = gal(mid, "hero") or face
    strong = d.get("strong", [])

    def im(u, h, pos="50% 22%", style=""):
        if not u:
            return f'<div style="height:{h}px;background-color:#1a1719"></div>'
        return f'<img src="{html.escape(u)}" alt="" style="display:block;width:100%;height:{h}px;object-fit:cover;object-position:{pos};{style}">'

    def letterbox(u, h, bar=22):
        return f'<div style="border-top:{bar}px solid #000;border-bottom:{bar}px solid #000;background-color:#000;line-height:0">{im(u, h)}</div>'

    def rich(s, col):
        s = sq(esc(s))
        for p in strong:
            if p in s:
                s = s.replace(p, f'<b style="color:{col}">{p}</b>', 1)
        return s

    def kicker(txt, col, center=True):
        return f'<p style="margin:0 0 6px;{"text-align:center;" if center else ""}font-size:10.5px;letter-spacing:.4em;color:{col}">{txt}</p>'

    o = []
    a = o.append
    a(f'<div style="max-width:680px;margin:0 auto;background-color:{BLK};color:{INK};font-family:{SANS};line-height:1.8;word-break:keep-all;border-radius:14px;overflow:hidden">')

    # ================================================================ OPENING (C)
    al = g["album"]
    a(f'<div data-face="{mid}" style="padding:30px 0 34px">' + kicker(f'NOX {al["label"].replace("NOX ", "").upper()} [{al["title"]}]', MUT) +
      f'<p style="margin:0 0 22px;text-align:center;font-family:{EN};font-size:27px;letter-spacing:.28em;color:{INK}">CONCEPT FILM {film}</p>'
      + letterbox(hero, 240) +
      f'<p style="margin:16px 20px 0;text-align:center;font-size:16.5px;line-height:1.6;color:#fff;text-shadow:0 0 4px #000">“{sq(esc(c["signature_line"]))}”</p>'
      f'<p style="margin:4px 0 0;text-align:center;font-family:{MONO};font-size:10.5px;color:{DIM_T}">00:00:14:{film}</p>'
      f'<p style="margin:30px 0 0;text-align:center;font-family:{EN};font-size:46px;font-weight:600;letter-spacing:.2em;line-height:1.1;color:{A};text-shadow:0 0 24px rgba({R},.45)">{en.upper()}</p>'
      f'<p style="margin:6px 0 0;text-align:center;font-size:12px;letter-spacing:.5em;color:{MUT}">{" ".join(name)}</p>'
      f'<p style="margin:18px 24px 0;text-align:center;font-size:13.5px;line-height:1.85;color:{MUT}">{sq(esc(c["lead"]))}</p></div>')

    # ================================================================ PRIVATE MESSAGE (A)
    chat = d.get("chat") or [{"divider": "무대가 끝난 뒤"}, {"him": c["signature_line"], "time": "1:10"},
                             {"photo": "hero", "time": "1:11"}, {"him": c["mode"]["line"], "time": "1:12"}]
    msgs = ""
    for x in chat:
        tm = f'<span style="font-size:10px;color:{PH_MUT}">{x.get("time", "")}</span>'
        if "divider" in x:
            msgs += f'<p style="margin:6px 0 10px;text-align:center;font-size:11px;color:{PH_MUT}">{esc(x["divider"])}</p>'
        elif "him" in x:
            msgs += (f'<div style="display:flex;gap:6px;align-items:flex-end;margin:6px 0">'
                     f'<span style="max-width:78%;padding:9px 13px;border-radius:4px 16px 16px 16px;background-color:#fff;color:{PH_INK};font-size:14.5px;line-height:1.65">'
                     f'{sq(esc(x["him"])).replace(chr(10), "<br>")}</span>{tm}</div>')
        elif "me" in x:
            msgs += (f'<div style="display:flex;gap:6px;align-items:flex-end;justify-content:flex-end;margin:6px 0">'
                     f'<span style="font-size:10px;color:{PH_MUT};text-align:right"><span style="color:{A}">1</span><br>{x.get("time", "")}</span>'
                     f'<span style="max-width:72%;padding:9px 13px;border-radius:16px 4px 16px 16px;background-color:{A};color:#fff;font-size:14.5px;line-height:1.65">{sq(esc(x["me"]))}</span></div>')
        elif "photo" in x:
            u = gal(mid, x["photo"]) or face
            if u:
                msgs += (f'<div style="display:flex;gap:6px;align-items:flex-end;margin:6px 0"><div style="width:62%;border-radius:14px;overflow:hidden;line-height:0">'
                         f'{im(u, 250, "50% 18%")}</div>{tm}</div>')
        elif "voice" in x:
            msgs += (f'<div style="display:flex;gap:6px;align-items:flex-end;margin:6px 0"><span style="display:flex;align-items:center;gap:10px;padding:9px 13px;border-radius:4px 16px 16px 16px;background-color:#fff">'
                     f'<span style="width:24px;height:24px;border-radius:50%;background-color:{A};color:#fff;font-size:10px;line-height:24px;text-align:center">▶</span>'
                     f'<span style="width:110px;height:15px;background-image:repeating-linear-gradient(90deg,{A} 0 2px,transparent 2px 5px)"></span>'
                     f'<span style="font-size:11px;color:{PH_MUT}">{x["voice"]}</span></span>{tm}</div>')
    av = (f'<img src="{html.escape(face)}" alt="" style="width:38px;height:38px;border-radius:50%;object-fit:cover;object-position:50% 20%">' if face
          else f'<span style="width:38px;height:38px;border-radius:50%;background-color:{PH_LINE}"></span>')
    a(f'<div style="padding:34px 14px;background-color:#0d0b0e">' + kicker("PRIVATE MESSAGE", A) +
      f'<p style="margin:0 0 18px;text-align:center;font-family:{SERIF};font-size:19px;color:{INK}">그날 밤, 그에게서 온 메시지</p>'
      f'<div style="max-width:400px;margin:0 auto;background-color:{PH_BG};color:{PH_INK};border-radius:26px;overflow:hidden;box-shadow:0 0 0 7px #000,0 0 0 8px #2a272b">'
      f'<div style="display:flex;justify-content:space-between;padding:9px 20px 3px;font-size:11.5px;font-weight:700">1:13<span>5G</span></div>'
      f'<div style="display:flex;align-items:center;gap:10px;padding:7px 14px 11px;border-bottom:1px solid {PH_LINE};background-color:#fbf9fa">'
      f'<span style="font-size:20px;color:{PH_MUT}">‹</span>{av}<div style="flex:1 1 auto">'
      f'<p style="margin:0;font-size:14.5px;font-weight:800;line-height:1.4">{name} <span style="font-size:10.5px;color:{A}">● NOX</span></p>'
      f'<p style="margin:0;font-size:11px;line-height:1.4;color:{PH_MUT}">{esc(d.get("chat_status", "당신만 구독 중"))}</p></div></div>'
      f'<div style="padding:12px 12px 16px">{msgs}</div></div></div>')

    # ================================================================ INTERVIEW (B)
    iv = d.get("interview", {})
    ps_rows = [("포지션", esc(m["position"])), ("신장 · 나이", f'{esc(ps["height"])} · {ps.get("age", "")}세'),
               ("당신과의 관계", esc(ps.get("relation", "")).replace("{{user}}", "당신")), ("성향", esc(m["archetype_suggest"])),
               ("NOX 컨셉", f'{m["concept_ko"]} {m["concept_hanja"]} · {esc(m["power"]["name"])}')]
    box = (f'<div style="margin:6px 0 22px;padding:14px 16px;border:1.5px solid {P_INK}">'
           f'<p style="margin:0 0 6px;font-size:10.5px;font-weight:800;letter-spacing:.3em;color:{A}">PROFILE</p>'
           + "".join(f'<p style="margin:0;padding:5px 0;border-top:1px solid {P_LINE};font-size:13px;display:flex;gap:10px">'
                     f'<span style="flex:0 0 84px;color:{P_MUT}">{k}</span><span style="flex:1 1 auto">{v}</span></p>' for k, v in ps_rows) + "</div>")
    pro = c["prologue"]
    rp = rich(pro[0], A)
    cap = (f'<span style="float:left;margin:4px 8px 0 0;font-family:{SERIF};font-size:46px;line-height:.9;font-weight:700;color:{A}">{rp[0]}</span>{rp[1:]}'
           if rp[:1] not in ("<", "&", "") else rp)  # 첫 글자 드롭캡 (태그로 시작하면 생략)
    body = (f'<p style="margin:0 0 14px;font-size:14.5px;line-height:1.95;color:#2a2628">{cap}</p>'
            + "".join(f'<p style="margin:0 0 14px;font-size:14.5px;line-height:1.95;color:#2a2628">{rich(p, A)}</p>' for p in pro[1:]))
    md, ct = c["mode"], c["mode"]["contrast"]
    vs = (f'<div style="display:flex;flex-wrap:wrap;margin:22px 0;border:1.5px solid {P_INK}">'
          f'<div style="flex:1 1 180px;padding:14px 16px"><p style="margin:0 0 6px;font-size:10.5px;font-weight:800;letter-spacing:.24em;color:{P_MUT}">{esc(ct["public_label"]).upper()}</p>'
          + "".join(f'<p style="margin:0;font-size:13px;line-height:1.8">{sq(esc(x))}</p>' for x in ct["public"]) + "</div>"
          f'<div style="flex:1 1 180px;padding:14px 16px;background-color:{P_INK};color:#fff"><p style="margin:0 0 6px;font-size:10.5px;font-weight:800;letter-spacing:.24em;color:{A}">{esc(ct["hidden_label"]).upper()}</p>'
          + "".join(f'<p style="margin:0;font-size:13px;line-height:1.8">{sq(esc(x))}</p>' for x in ct["hidden"]) + "</div></div>"
          f'<p style="margin:0 0 6px;font-family:{SERIF};font-size:18px;font-weight:700;color:{P_INK}">{esc(md["title"])}</p>'
          f'<p style="margin:0 0 14px;font-size:14.5px;line-height:1.95;color:#2a2628">{rich(md["body_1"], A)} {rich(md["body_2"], A)}</p>')
    qa = "".join(f'<p style="margin:0 0 3px;font-size:14px;font-weight:800;color:{P_INK}">Q. {esc(q)}</p>'
                 f'<p style="margin:0 0 16px;font-size:14px;line-height:1.85;color:#333"><b style="color:{A}">A.</b> {sq(esc(an))}</p>' for q, an in iv.get("qa", []))
    title = iv.get("title", ["국민 남친의 가면,", "그 아래의 한 사람"])
    cover_img = gal(mid, "ep4") or face
    a(f'<div style="background-color:{PAPER};color:{P_INK}">'
      f'<div style="display:flex;justify-content:space-between;align-items:flex-end;padding:18px 18px 0">'
      f'<span style="font-family:{EN};font-size:70px;font-weight:600;line-height:.8;letter-spacing:-.02em;color:{P_INK}">NOX</span>'
      f'<span style="font-size:10px;letter-spacing:.14em;text-align:right;line-height:1.6">ISSUE {film} · {en.upper()}<br>{esc(iv.get("kicker", "COVER STORY"))}</span></div>'
      f'<div style="height:3px;background-color:{P_INK};margin:10px 18px 0"></div>'
      f'<div style="margin:12px 18px 0;line-height:0">{im(cover_img, 360, "50% 15%")}</div>'
      f'<div style="margin:0 18px;padding:14px 16px 12px;background-color:{P_INK};color:#fff">'
      f'<p style="margin:0;font-size:10.5px;letter-spacing:.24em;color:{A}">INTERVIEW</p>'
      f'<p style="margin:2px 0 0;font-family:{SERIF};font-size:26px;font-weight:700;line-height:1.3">{esc(title[0])}<br>{esc(title[1])}</p>'
      f'<p style="margin:6px 0 0;font-size:12px;letter-spacing:.04em;color:#b9b4b7">{esc(iv.get("deck", name))}</p></div>'
      f'<div style="padding:24px 18px 28px">{box}{body}{vs}'
      + (f'<div style="height:1.5px;background-color:{P_INK};margin:22px 0 18px"></div>{qa}' if qa else "")
      + f'<p style="margin:8px 0 0;font-size:10.5px;color:#8b8588">EDITOR {g["credit"]} · PHOTOGRAPHY NOX × Tikitaka</p></div></div>')

    # ================================================================ SCENES (C)
    slugs, marks = d.get("scene_slugs", []), d.get("episode_marks", [])
    sc = ""
    for i, e in enumerate(c["episodes"]):
        u = gal(mid, f"ep{i + 1}")
        slug = slugs[i] if i < len(slugs) else (marks[i] if i < len(marks) else "")
        line = (f'<p style="margin:10px 0 0;text-align:center;font-size:14.5px;line-height:1.6;color:#fff;text-shadow:0 0 4px #000">“{sq(esc(e["line"]))}”</p>' if e.get("line") else "")
        sc += (f'<div style="margin:0 0 30px">' + (letterbox(u, 170, 14) if u else "") +
               f'<div style="padding:0 16px"><div style="display:flex;justify-content:space-between;gap:10px;margin-top:9px;font-family:{MONO};font-size:10.5px;color:{DIM_T}">'
               f'<span style="color:{A}">SCENE #{e["no"]}</span><span>{esc(slug)}</span></div>'
               f'<p style="margin:4px 0 0;font-size:16px;font-weight:700;color:{INK}">{sq(esc(e["title"]))}</p>'
               f'<p style="margin:3px 0 0;font-size:13.5px;line-height:1.75;color:{MUT}">{sq(esc(e["scene"]))}</p>{line}</div></div>')
    a(f'<div style="padding:36px 0 6px">' + kicker("SCENES", A) +
      f'<p style="margin:0 0 24px;text-align:center;font-family:{SERIF};font-size:21px;color:{INK}">네 번의 밤</p>{sc}</div>')

    # ================================================================ 공략 노트 (A 톤)
    tips = m.get("play_tips", [])
    tip = "".join(f'<div style="padding:12px 14px;margin:0 0 8px;border-radius:14px;background-color:#fff">'
                  f'<p style="margin:0 0 2px;font-size:14px;font-weight:800;color:{PH_INK}"><span style="color:{A};margin-right:6px">{i + 1}</span>{esc(x["title"])}</p>'
                  f'<p style="margin:0;font-size:13px;line-height:1.75;color:#5d575b">{sq(esc(x["body"]))}</p></div>' for i, x in enumerate(tips))
    var = "".join(f'<div style="flex:1 1 150px;padding:10px 12px;border-radius:12px;background-color:#fff;border:1px solid {PH_LINE}">'
                  f'<p style="margin:0;font-size:13.5px;font-weight:800;color:{A}">{esc(v["name"])}</p>'
                  f'<p style="margin:2px 0 0;font-size:12px;line-height:1.6;color:#5d575b">{sq(esc(v["desc"].replace("{{user}}", "당신")))}</p></div>' for v in t.get("variables", []))
    guide = g["play_guide"].replace(g["ooc_example"] + " 등 ", "")
    a(f'<div style="margin:0 12px;padding:22px 14px 16px;border-radius:20px;background-color:{PH_BG};color:{PH_INK}">'
      f'<p style="margin:0 0 2px;font-size:11px;font-weight:800;letter-spacing:.2em;color:{A}">공략 노트</p>'
      f'<p style="margin:0 0 14px;font-size:18px;font-weight:800">{name}에게 다가가는 법</p>{tip}'
      f'<div style="display:flex;flex-wrap:wrap;gap:8px;margin:10px 0 0">{var}</div>'
      f'<p style="margin:12px 0 0;font-size:12.5px;line-height:1.75;color:{PH_MUT}">{esc(guide)} <b style="color:{A}">{esc(g["ooc_example"])}</b></p></div>')

    # ================================================================ CAST (C)
    cast = ""
    for x in members["members"]:
        me = x["id"] == mid
        s_ = src(x["id"])
        f_ = (f'<img src="{html.escape(s_)}" alt="{x["name"]}" style="width:56px;height:56px;border-radius:50%;object-fit:cover;object-position:50% 20%;display:block;'
              f'{"box-shadow:0 0 0 2px " + A if me else "filter:grayscale(.4)"}">' if s_ else f'<span style="display:block;width:56px;height:56px;border-radius:50%;background-color:{HAIR}"></span>')
        cast += (f'<div data-face="{x["id"]}" style="flex:0 0 74px;text-align:center">'
                 f'<div style="display:flex;justify-content:center">{f_}</div>'
                 f'<p style="margin:6px 0 0;font-size:12px;font-weight:700;line-height:1.3;color:{A if me else INK}">{x["name"]}</p>'
                 f'<p style="margin:0;font-size:9.5px;letter-spacing:.1em;line-height:1.4;color:{DIM_T}">{x["concept_en"].upper()}</p></div>')
    a(f'<div style="padding:40px 16px 10px;text-align:center">' + kicker("CAST", A) +
      f'<p style="margin:0 0 6px;font-family:{SERIF};font-size:19px;color:{INK}">{esc(g["worldview_title"])}</p>'
      f'<p style="margin:0 auto 20px;max-width:480px;font-size:12.5px;line-height:1.85;color:{MUT}">{sq(esc(g["worldview"]))} <span style="color:{DIM_T}">— NOX의 세계관 컨셉</span></p>'
      f'<div style="display:flex;flex-wrap:wrap;justify-content:center;gap:14px 6px">{cast}</div></div>')

    # ================================================================ OST + END CREDITS (C)
    tr = ""
    for i, t_ in enumerate(al["tracks"]):
        live = t_["status"] == "live"
        url, vid = t_.get("url"), yt_id(t_.get("url"))
        ttl = f'{t_["ko"]} <span style="font-family:{EN};font-style:italic;color:{DIM_T}">{t_["en"]}</span>'
        if live and url and vid:
            tr += (f'<a href="{html.escape(url)}" style="display:flex;align-items:center;gap:12px;padding:9px 0;border-top:1px solid {HAIR};color:{INK};text-decoration:none">'
                   f'<span style="flex:0 0 80px;line-height:0;border-radius:3px;overflow:hidden"><img src="https://img.youtube.com/vi/{vid}/mqdefault.jpg" alt="" width="80" height="45" style="display:block;width:80px;height:45px;object-fit:cover"></span>'
                   f'<span style="flex:1 1 auto;font-size:14px">{t_["no"]}. {ttl}<span style="display:block;font-size:10.5px;letter-spacing:.1em;color:{A}">▶ PLAY</span></span></a>')
        else:
            tr += (f'<p style="margin:0;padding:10px 0;border-top:1px solid {HAIR};font-size:14px;color:{DIM_T}">{t_["no"]}. {ttl} '
                   f'<span style="font-size:10.5px">· {TRACK_STATUS.get(t_["status"], t_["status"])}</span></p>')
    a(f'<div style="padding:34px 18px 10px">' + kicker("ORIGINAL SOUNDTRACK", A) +
      f'<p style="margin:0 0 12px;text-align:center;font-family:{EN};font-size:26px;letter-spacing:.2em;color:{INK}">{al["title"]}</p>{tr}</div>')
    a(f'<div style="padding:34px 18px 40px;text-align:center;font-size:10.5px;line-height:2.1;letter-spacing:.3em;color:{MUT}">'
      f'<p style="margin:0 0 14px;font-family:{EN};font-style:italic;font-size:19px;letter-spacing:.06em;color:{INK}">{esc(g["idol_concept"]["slogan_suggest"])}</p>'
      f'DIRECTED BY {g["credit"]}<br>STARRING <b style="color:{A}">{name}</b> · YOU<br><span style="color:{DIM_T}">{en.upper()} : {g["name"]} × Tikitaka AI System</span></div>')
    a("</div>")
    return "".join(o)
