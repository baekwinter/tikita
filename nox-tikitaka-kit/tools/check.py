#!/usr/bin/env python3
"""NOX × Tikitaka 검증. 실패 항목이 있으면 exit 1.

  python tools/check.py           # 전체 표
  python tools/check.py --short   # 글자 수 요약 표만
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import build  # noqa: E402

OUT = ROOT / "output"
EMOJI = re.compile("[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F900-\U0001F9FF⭐⭕⌚-⌛⏩-⏺️]")
fails, warns = [], []


def fail(msg):
    fails.append(msg)


def warn(msg):
    warns.append(msg)


def norm(s):
    return re.sub(r"\s+", " ", s.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")).strip()


def strip_tags(s):
    return norm(re.sub(r"<br\s*/?>", " ", re.sub(r"</?(em|strong|b|i)>", "", s)))


def copy_len(c):
    s = [c["title_label"], c["lead"], c["signature_line"], *c["specs"], *c["prologue"], c["mode"]["title"],
         c["mode"]["body_1"], c["mode"]["line"], c["mode"]["body_2"], c["world_closing"]]
    for e in c["episodes"]:
        s += [e["title"], e["scene"], e["line"]]
    return sum(map(len, s))


def field_rows(m, members):
    """(칸 이름, 글자 수, 제한) 목록 — 티키타 크리에이터 가이드 한도."""
    t, L = m["tikitaka"], build.LIMITS
    rows = [("제목", len(t["story_title"]), L["title"]), ("태그라인", len(t["one_liner"]), L["tagline"]),
            ("캐릭터 이름", len(m["name"]), L["name"]),
            ("공개 정보", len(t["char_intro"]), L["public"]), ("비공개 정보", len(t["secret"]), L["private"]),
            ("스토리 설정", len(build.story_setting(m, members)), L["setting"]),
            ("첫 메시지", len(t["first_message"]), L["first"])]
    rows += [(f"시작 문구{i}", len(x["text"]), L["starter"]) for i, x in enumerate(t.get("starters", []), 1)]
    ex = build.examples(t)
    rows += [(f"예시 대화{i}", len(x["text"]), L["example"]) for i, x in enumerate(ex, 1)]
    rows += [("예시 대화 수", len(ex), L["examples"]), ("추천 페르소나 수", len(t.get("personas", [])), L["personas"])]
    rows += [(f"페르소나{i} 소개", len(x["intro"]), L["persona"]) for i, x in enumerate(t.get("personas", []), 1)]
    for i, e in enumerate(t["episodes"], 1):
        rows += [(f"EP{i} 제목", len(e["title"]), L["ep_title"]), (f"EP{i} 조건", len(e["condition"]), L["ep_cond"]),
                 (f"EP{i} 본문", len(e["narrative"]), L["ep_body"]), (f"EP{i} 비공개", len(e["private"]), L["ep_private"])]
    rows += [("에피소드 수", len(t["episodes"]), L["episodes"]), ("변수 수", len(t["variables"]), L["variables"])]
    for v in t["variables"]:
        rows += [(f"변수 {v['name']} 이름", len(v["name"]), L["var_name"]), (f"변수 {v['name']} 설명", len(v["desc"]), L["var_desc"]),
                 (f"변수 {v['name']} 범위", len(v.get("range_desc", "")), L["var_range"]), (f"변수 {v['name']} 시작값", len(str(v["start"])), L["var_start"])]
    if t.get("status_html"):
        rows.append(("변수 디자인(바이트)", len(t["status_html"].encode("utf-8")), L["status_bytes"]))
    for x in t.get("lorebook", []):
        rows += [(f"로어북 {x['title']} 제목", len(x["title"]), L["lore_title"]), (f"로어북 {x['title']} 내용", len(x["content"]), L["lore_content"]),
                 (f"로어북 {x['title']} 키워드 수", len(x["keywords"]), 20)]
    for g in t.get("gallery", []):
        rows.append((f"이미지 그룹 {g['group']}", len(g["group"]), L["gallery_group"]))
        rows += [(f"이미지 설명 {x['file']}", len(x["desc"]), L["gallery_desc"]) for x in g["images"]]
    rows += [("카테고리 수", len(t["categories"]), L["categories"]), ("태그 수", len(t["tags"]), L["tags"]),
             ("제작자 코멘트", len(t["creator_comment"]), L["comment"]), ("작품 글자 수", build.work_count(m, members)[1], L["work"])]
    if "image" in m:
        md = build.image_prompts(m, members)
        for label, n in re.findall(r"^## (.+?)  `([\d,]+) / 1,200자`", md, flags=re.M):
            rows.append((f"이미지:{label.split(' (')[0].split(' —')[0]}", int(n.replace(",", "")), 1200))
    return rows


def guide_format(m):
    """가이드 형식 검사: 대사·지문 줄, 전환 조건, 변수 이름, 로어북 키워드. 문제 목록을 돌려준다."""
    t, out = m["tikitaka"], []
    names = {m["name"], "{{user}}", "{{char1}}"}
    texts = [("첫 메시지", t["first_message"])] + [(f"예시 대화{i}", x["text"]) for i, x in enumerate(build.examples(t), 1)]
    for label, txt in texts:
        for ln in filter(None, (x.strip() for x in txt.splitlines())):
            if ln.startswith("*"):
                if not ln.endswith("*") or ln.count("*") != 2:
                    out.append(f"{label}: 지문은 *한 쌍*으로 한 줄 전체를 감싸야 함 — {ln[:24]}…")
                elif ":" in ln:
                    out.append(f"{label}: 지문 안에 콜론 — 이름으로 오인됨 — {ln[:24]}…")
                continue
            who, sep, rest = ln.partition(": ")
            if not sep or who not in names:
                out.append(f"{label}: 이름 없는 줄 (자동 지문 처리됨) — {ln[:24]}…")
            elif "*" in rest:
                out.append(f"{label}: 대사 줄 안의 *지문* — 윗줄로 분리 — {ln[:24]}…")
    for i, e in enumerate(t["episodes"], 1):
        c = e["condition"]
        if i == 1:
            continue
        if not c:
            out.append(f"EP{i}: 전환 조건 없음")
        elif c.startswith("조건") or ("{{user}}" not in c and "{{char1}}" not in c):
            out.append(f"EP{i}: 전환 조건은 접두사 없이 {{{{user}}}}/{{{{char1}}}}를 넣은 한 문장으로")
    for v in t["variables"]:
        if " " in v["name"]:
            out.append(f"변수 {v['name']}: 이름에 띄어쓰기")
    for x in t.get("lorebook", []):
        bad = [k for k in x["keywords"] if not 2 <= len(k) <= 60]
        if bad:
            out.append(f"로어북 {x['title']}: 키워드 길이 2~60자 위반 {bad}")
    if t.get("status_html") and "<style" in t["status_html"]:
        out.append("변수 디자인: <style> 태그는 안 먹음")
    return out


def main(short=False):
    members, faces, platform = build.load()
    ms = members["members"]
    ids = [m["id"] for m in ms]
    base_len = copy_len(next(m for m in ms if m["id"] == "eclipse")["copy"])
    locked = json.loads((ROOT / "data" / "locked" / "complete_copy.json").read_text(encoding="utf-8"))
    source = (ROOT / "data" / "locked" / "eclipse_source.txt").read_text(encoding="utf-8")
    amend = ROOT / "data" / "locked" / "eclipse_amendments.json"  # 사용자가 승인한 원문 수정 (원문 파일은 그대로 둔다)
    for a in (json.loads(amend.read_text(encoding="utf-8")) if amend.exists() else []):
        source = source.replace(a["from"], a["to"])
    source = norm(source)

    # ---- 1. 글자 수 (입력칸)
    print("\n[1] 티키타 입력칸 글자 수 (최대값 / 제한)")
    print(f"{'멤버':8s} {'상태':9s} {'카피':>6s} {'작품 글자 수':>14s} {'첫 메시지':>8s} {'예시':>4s} {'문구':>4s} {'페르소나':>4s} {'EP':>3s} {'변수':>4s} {'붙여넣기':>14s}")
    for m in ms:
        if "tikitaka" not in m:
            fail(f"{m['id']}: tikitaka 입력칸 데이터 없음")
            continue
        rows = field_rows(m, members)
        for label, n, lim in rows:
            if n > lim:
                fail(f"{m['id']}: {label} {n:,}자 > 제한 {lim:,}")
        mx = lambda key: max((n for l, n, _ in rows if key in l), default=0)  # noqa: E731
        paste = OUT / m["id"] / "tikitaka_intro.html"
        pn = len(paste.read_text(encoding="utf-8")) if paste.exists() else -1
        if pn < 0:
            fail(f"{m['id']}: tikitaka_intro.html 없음 (build.py 실행 필요)")
        elif pn > build.budget(platform):
            fail(f"{m['id']}: tikitaka_intro.html {pn:,}자 > 예산 {build.budget(platform):,}")
        ratio = copy_len(m["copy"]) / base_len * 100
        if abs(ratio - 100) > 15:
            warn(f"{m['id']}: 카피 분량 {ratio:.0f}% (차은결 대비 ±15% 초과)")
        t = m["tikitaka"]
        total = build.work_count(m, members)[1]
        print(f"{m['id']:8s} {m['status']:9s} {ratio:5.0f}% {total:>7,}/30,000 {len(t['first_message']):>8,} {len(build.examples(t)):>4} "
              f"{len(t.get('starters', [])):>4} {len(t.get('personas', [])):>6} {len(t['episodes']):>3} {len(t['variables']):>4} {pn:>6,}/{build.budget(platform):,}")
        probs = guide_format(m)
        lo, hi = build.FIRST_RECOMMENDED
        if t.get("guide_version"):  # 가이드 반영을 마친 멤버는 형식 위반 = 실패
            for x in probs:
                fail(f"{m['id']}: {x}")
            if not lo <= len(t["first_message"]) <= hi:
                warn(f"{m['id']}: 첫 메시지 {len(t['first_message']):,}자 (가이드 권장 {lo:,}~{hi:,}자)")
        elif probs:
            warn(f"{m['id']}: 가이드 형식 미반영 {len(probs)}건 (입력칸 재작성 전) — 예: {probs[0]}")
    if short:
        return report()

    # ---- 2. 얼굴 슬롯
    print("\n[2] 얼굴 슬롯 (히어로 1 + 멤버 7 = 8)")
    for m in ms:
        for f in ("preview.html", "tikitaka_intro.html"):
            p = OUT / m["id"] / f
            if not p.exists():
                continue
            s = p.read_text(encoding="utf-8")
            slots = re.findall(r'data-face="(\w+)"', s)
            hero = slots[0] if slots else None  # 첫 슬롯 = 히어로
            ok = len(slots) == 8 and hero == m["id"] and sorted(slots[1:]) == sorted(ids)
            if not ok:
                fail(f"{m['id']}/{f}: 얼굴 슬롯 {len(slots)}개 (히어로={hero or '없음'})")
        print(f"  {m['id']:8s} preview·intro 슬롯 OK" if not any(m['id'] + '/' in x for x in fails) else f"  {m['id']:8s} 슬롯 오류")
    missing_url = [f"{faces[i]['name']}({i})" for i in ids if not faces.get(i, {}).get("url")]
    if missing_url:
        warn(f"얼굴 이미지 URL 없음 {len(missing_url)}/7 — 붙여넣기 버전은 실루엣으로 빌드됨: {', '.join(missing_url)}")
    print(f"  URL 등록 {7 - len(missing_url)}/7")

    # ---- 3. script / 이모지
    print("\n[3] <script> · 이모지")
    targets = [p for p in OUT.rglob("*") if p.suffix in (".html", ".md", ".css")]
    for p in targets:
        s = p.read_text(encoding="utf-8")
        if re.search(r"<script", s, re.I):
            fail(f"{p.relative_to(ROOT)}: <script> 포함")
        e = EMOJI.findall(s)
        if e:
            fail(f"{p.relative_to(ROOT)}: 이모지 {''.join(sorted(set(e)))}")
    print(f"  검사 파일 {len(targets)}개")

    # ---- 4. complete 카피 잠금
    print("\n[4] complete 카피 잠금")
    for m in ms:
        if m["status"] != "complete":
            continue
        snap = locked.get(m["id"])
        if snap is None:
            fail(f"{m['id']}: complete인데 data/locked/complete_copy.json 스냅샷 없음")
        elif snap != m["copy"]:
            fail(f"{m['id']}: complete 카피가 잠금 스냅샷과 다름 (수정 금지)")
        if m["id"] == "eclipse":
            c = m["copy"]
            prose = [c["title_full"], c["lead"], c["signature_line"], *c["prologue"], c["mode"]["body_1"],
                     c["mode"]["line"], c["mode"]["body_2"], c["world_closing"]]
            prose += [x for e in c["episodes"] for x in (e["title"], e["scene"], e["line"]) if x]
            bad = [x for x in prose if norm(x) not in source]
            for x in bad:
                fail(f"eclipse: 원문(eclipse_source.txt)에 없는 문장: {x[:30]}…")
        d = m.get("display", {})
        if d.get("lead_html") and strip_tags(d["lead_html"]) != norm(m["copy"]["lead"]):
            fail(f"{m['id']}: display.lead_html 텍스트가 copy.lead와 다름")
        print(f"  {m['id']:8s} {'OK' if not any(x.startswith(m['id'] + ':') for x in fails) else '변경 감지'}")

    # ---- 5. 성인 확인
    print("\n[5] 나이 (전원 20세 이상, 막내 21세 이상)")
    for m in ms:
        age = m["profile_suggest"].get("age")
        if not isinstance(age, int) or age < 20 or (m["id"] == "star" and age < 21):
            fail(f"{m['id']}: 나이 {age}")
    print("  " + " · ".join(f"{m['name']} {m['profile_suggest'].get('age')}" for m in ms))

    # ---- 6. 관계 중복
    rel = [m["profile_suggest"].get("relation", "") for m in ms]
    if len(set(rel)) != len(rel):
        fail("유저와의 관계 설정이 겹치는 멤버가 있음")
    return report()


def report():
    print()
    for w in warns:
        print(f"경고  {w}")
    for f in fails:
        print(f"실패  {f}")
    print(f"\n결과: 실패 {len(fails)} · 경고 {len(warns)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(short="--short" in sys.argv))
