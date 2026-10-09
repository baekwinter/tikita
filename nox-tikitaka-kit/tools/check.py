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
    """(칸 이름, 글자 수, 제한) 목록."""
    t = m["tikitaka"]
    rows = [("한 줄 소개", len(t["one_liner"]), 100), ("캐릭터 이름", len(m["name"]), 15),
            ("캐릭터 소개", len(t["char_intro"]), 1000), ("비밀", len(t["secret"]), 2000),
            ("스토리 설정", len(build.story_setting(m, members)), 2000)]
    for i, e in enumerate(t["episodes"], 1):
        rows += [(f"EP{i} 제목", len(e["title"]), 20), (f"EP{i} 조건", len(e["condition"]), 50),
                 (f"EP{i} 서사", len(e["narrative"]), 2000), (f"EP{i} 비공개", len(e["private"]), 2000)]
    rows += [("에피소드 수", len(t["episodes"]), 10), ("변수 수", len(t["variables"]), 3),
             ("카테고리 수", len(t["categories"]), 3), ("태그 수", len(t["tags"]), 15),
             ("제작자 코멘트", len(t["creator_comment"]), 1000)]
    if "image" in m:
        md = build.image_prompts(m, members)
        for label, n in re.findall(r"^## (.+?)  `([\d,]+) / 1,200자`", md, flags=re.M):
            rows.append((f"이미지:{label.split(' (')[0].split(' —')[0]}", int(n.replace(",", "")), 1200))
    return rows


def main(short=False):
    members, faces, platform = build.load()
    ms = members["members"]
    ids = [m["id"] for m in ms]
    base_len = copy_len(next(m for m in ms if m["id"] == "eclipse")["copy"])
    locked = json.loads((ROOT / "data" / "locked" / "complete_copy.json").read_text(encoding="utf-8"))
    source = norm((ROOT / "data" / "locked" / "eclipse_source.txt").read_text(encoding="utf-8"))

    # ---- 1. 글자 수 (입력칸)
    print("\n[1] 티키타 입력칸 글자 수 (최대값 / 제한)")
    print(f"{'멤버':8s} {'상태':9s} {'카피':>6s} {'한줄':>7s} {'소개':>9s} {'비밀':>9s} {'설정':>9s} {'EP제목':>7s} {'EP조건':>7s} {'EP서사':>9s} {'EP비공개':>9s} {'태그':>6s} {'이미지':>9s} {'붙여넣기':>12s}")
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
        print(f"{m['id']:8s} {m['status']:9s} {ratio:5.0f}% {len(t['one_liner']):>3}/100 {len(t['char_intro']):>4}/1000 "
              f"{len(t['secret']):>4}/2000 {len(build.story_setting(m, members)):>4}/2000 {mx('제목'):>4}/20 {mx('조건'):>4}/50 "
              f"{mx('서사'):>4}/2000 {mx('비공개'):>4}/2000 {len(t['tags']):>3}/15 {mx('이미지'):>4}/1200 {pn:>6,}/{build.budget(platform):,}")
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
