"""티키타 등록용 결과물을 fields/ 원본에서 만든다.

    python3 build.py

dist/ 에 다음을 쓴다.
  story_intro.html      스토리 소개 (HTML 모드, p·h2·img·br 태그만)
  story_intro.md        스토리 소개 (MD 모드)
  episode_1..5.txt      에피소드 내용 (공통 설정 + 해당 화)
  episode_all.txt       에피소드를 하나만 등록할 때 쓰는 통합본
  tikita_register.md    칸별 붙여넣기 안내 + 글자 수 점검
  copy_helper.html      칸별 복사 버튼 페이지
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
FIELDS = ROOT / "fields"
DIST = ROOT / "dist"

LIMIT_WORK = 30_000   # 작품 글자 수
LIMIT_INTRO = 50_000  # 스토리 소개
LIMIT_NOTE = 20_000   # 제작자 노트
MIN_SETTING = 1_000   # 공모전: 스토리 설정 최소
ALLOWED_TAGS = {"p", "h2", "img", "br"}
IMG_RE = re.compile(r"^\[\[IMG:(\w+)\|(.+)\]\]$")


def read(name):
    return (FIELDS / name).read_text(encoding="utf-8").strip()


def intro_blocks():
    return [b.strip() for b in read("intro.src").split("\n\n") if b.strip()]


def intro_html(images):
    out = []
    for block in intro_blocks():
        m = IMG_RE.match(block)
        if m:
            url = images.get(m.group(1), "").strip()
            if url:
                out.append(f'<img src="{html.escape(url, quote=True)}" alt="{html.escape(m.group(2), quote=True)}">')
        elif block.startswith("## "):
            out.append(f"<h2>{html.escape(block[3:], quote=False)}</h2>")
        else:
            lines = [html.escape(line, quote=False) for line in block.split("\n")]
            out.append("<p>" + "<br>".join(lines) + "</p>")
    return "\n".join(out) + "\n"


def intro_md(images):
    out = []
    for block in intro_blocks():
        m = IMG_RE.match(block)
        if m:
            url = images.get(m.group(1), "").strip()
            if url:
                out.append(f"![{m.group(2)}]({url})")
        else:
            out.append(block.replace("\n", "  \n"))
    return "\n\n".join(out) + "\n"


def check_tags(markup):
    bad = {t.lower() for t in re.findall(r"</?\s*([a-zA-Z0-9]+)", markup)} - ALLOWED_TAGS
    if bad:
        raise SystemExit(f"허용되지 않은 태그: {sorted(bad)}")


def fence(text, lang=""):
    ticks = "````" if "```" in text else "```"
    return f"{ticks}{lang}\n{text}\n{ticks}"


def main():
    DIST.mkdir(exist_ok=True)
    images = json.loads(read("images.json"))

    story_html = intro_html(images)
    check_tags(story_html)
    story_md = intro_md(images)

    common = read("common.txt")
    episodes = [f"{common}\n\n{read(f'ep{i}.txt')}" for i in range(1, 6)]
    openings = [read(f"ep{i}_opening.txt") for i in range(1, 6)]
    allinone = "\n\n".join([read("integrated_header.txt"), common] + [read(f"ep{i}.txt") for i in range(1, 6)])

    (DIST / "story_intro.html").write_text(story_html, encoding="utf-8")
    (DIST / "story_intro.md").write_text(story_md, encoding="utf-8")
    for i, ep in enumerate(episodes, 1):
        (DIST / f"episode_{i}.txt").write_text(ep + "\n", encoding="utf-8")
    (DIST / "episode_all.txt").write_text(allinone + "\n", encoding="utf-8")

    f = {
        "title": read("title.txt"),
        "tagline": read("tagline.txt"),
        "categories": read("categories.txt"),
        "tags": read("tags.txt"),
        "age": read("age.txt"),
        "protagonist": read("protagonist.txt"),
        "note": read("creator_note.txt"),
        "tr_en": read("translation_en.txt"),
        "tr_ja": read("translation_ja.txt"),
    }

    # 무엇이 '작품 글자 수'에 들어가는지 화면에서 확인되지 않아, 대화에 쓰이는 칸을 모두 더해 보수적으로 잰다.
    base = len(f["title"]) + len(f["tagline"]) + len(f["protagonist"])
    total_a = base + sum(map(len, episodes)) + sum(map(len, openings))
    total_b = base + len(allinone) + len(openings[0])
    images_used = [k for k, v in images.items() if not k.startswith("_") and v.strip()]

    for name, n, limit in [("작품 글자 수(5화 등록)", total_a, LIMIT_WORK),
                           ("작품 글자 수(통합 1화 등록)", total_b, LIMIT_WORK),
                           ("스토리 소개 HTML", len(story_html), LIMIT_INTRO),
                           ("제작자 노트", len(f["note"]), LIMIT_NOTE)]:
        if n > limit:
            raise SystemExit(f"{name} {n:,}자 — 한도 {limit:,}자 초과")
    for i, ep in enumerate(episodes, 1):
        if len(ep) < MIN_SETTING:
            raise SystemExit(f"에피소드 {i} 내용이 {MIN_SETTING:,}자 미만")

    tags = f["tags"].split("\n")
    if len(tags) > 15:
        raise SystemExit("태그는 15개까지")
    cats = f["categories"].split("\n")
    if len(cats) > 3:
        raise SystemExit("카테고리는 3개까지")

    def n(s):
        return f"{len(s):,}자"

    doc = [
        "# 티키타 등록 안내 — 내 남자친구는 구미호",
        "",
        "`build.py`로 `fields/`에서 자동 생성한 파일입니다. 이 파일을 직접 고치지 말고 `fields/`를 고친 뒤 다시 생성하세요.",
        "",
        "## 글자 수 점검",
        "",
        "| 항목 | 글자 수 | 한도 |",
        "|---|---|---|",
        f"| 작품 글자 수 — 에피소드 5개로 등록 | {total_a:,} | {LIMIT_WORK:,} |",
        f"| 작품 글자 수 — 통합 에피소드 1개로 등록 | {total_b:,} | {LIMIT_WORK:,} |",
        f"| 스토리 소개 HTML | {len(story_html):,} | {LIMIT_INTRO:,} |",
        f"| 제작자 노트 | {len(f['note']):,} | {LIMIT_NOTE:,} |",
        f"| 에피소드 내용 최소(공모전 설정 1,000자) | {min(map(len, episodes)):,} | ≥ {MIN_SETTING:,} |",
        "",
        "작품 글자 수는 제목·태그라인·주인공 소개·에피소드 내용·도입부를 모두 더한 값입니다. 티키타가 어떤 칸을 세는지 화면에서 확인되지 않아 넉넉하게 계산했습니다.",
        "",
        f"스토리 소개에 들어간 이미지: {', '.join(images_used) if images_used else '없음 — fields/images.json에 주소를 넣고 다시 생성하세요'}",
        "",
        "## 기본 정보",
        "",
        "- 공개 여부: 점검을 마칠 때까지 **비공개**로 두고, 제출 직전에 **공개**로 바꾸세요. 공모전에 참여하려면 공개된 작품이어야 합니다.",
        "- 2차 창작: 체크하지 않음 (창작물)",
        f"- 연령 등급: **{f['age']}**",
        f"- 카테고리 ({len(cats)}/3): {' · '.join(cats)}",
        f"- 태그 ({len(tags)}/15) — 앞의 두 개는 공모전 필수 태그입니다: {', '.join(tags)}",
        "",
        "### 작품 제목",
        fence(f["title"]),
        f"### 태그라인 ({n(f['tagline'])})",
        fence(f["tagline"]),
        f"### 주인공 소개 ({n(f['protagonist'])})",
        fence(f["protagonist"]),
        "",
        f"## 스토리 소개 — HTML 모드 ({n(story_html)})",
        "",
        "스토리 소개 칸에서 **HTML**을 선택한 뒤 붙여 넣으세요. 이미지 주소가 있다면 '외부 이미지 가져오기'를 누르세요. MD 모드를 쓰려면 `dist/story_intro.md`를 붙여 넣으면 됩니다.",
        "",
        fence(story_html.strip(), "html"),
        "",
        "## 에피소드",
        "",
        "에피소드를 다섯 개 만들 수 있으면 **방식 A**, 하나만 만들 수 있으면 **방식 B**를 쓰세요. 에피소드 내용은 독자에게 보이지 않는 칸으로 보고 비밀을 넣었습니다. 독자에게 보인다면 알려 주세요. 공개용으로 다시 나누겠습니다.",
        "",
        "### 방식 A — 에피소드 5개",
    ]
    titles = ["1화 〈달〉 소개팅 상대는 궁의 점술사", "2화 〈연인〉 월하당의 두 번째 문",
              "3화 〈악마〉 황궁 제복을 입은 남자친구", "4화 〈심판〉 탈의 밤, 아홉 개의 꼬리",
              "5화 〈별〉 점괘에 없는 내일"]
    for i, (t, ep, op) in enumerate(zip(titles, episodes, openings), 1):
        doc += [f"#### {t}", f"에피소드 내용 ({n(ep)})", fence(ep), f"도입부 ({n(op)})", fence(op), ""]
    doc += [
        "### 방식 B — 통합 에피소드 1개",
        f"에피소드 내용 ({n(allinone)})", fence(allinone), f"도입부 = 1화 도입부 ({n(openings[0])})", fence(openings[0]), "",
        f"## 제작자 노트 ({n(f['note'])})", fence(f["note"]), "",
        "## 번역 메모", "### 영어", fence(f["tr_en"]), "### 일본어", fence(f["tr_ja"]), "",
        "## 제출",
        "1. 이미지 5장 이상(대표 포함)을 등록합니다. 프롬프트는 `image_prompts.md`에 있습니다.",
        "2. 태그에 `판타지공모전`, `인외`가 있는지 확인합니다.",
        "3. 작품을 **공개**로 바꿉니다.",
        "4. 공모전 페이지에서 **‘공모전 참여하기’**로 작품을 제출합니다. 공개만 해서는 접수되지 않습니다. 마감은 10월 31일입니다.",
        "",
    ]
    (DIST / "tikita_register.md").write_text("\n".join(doc), encoding="utf-8")

    sections = [
        ("기본", "작품 제목", f["title"]), ("기본", "태그라인", f["tagline"]),
        ("기본", "카테고리 (하나씩 선택)", f["categories"]), ("기본", "태그 (하나씩 추가)", f["tags"]),
        ("기본", "주인공 소개", f["protagonist"]),
        ("스토리 소개", "스토리 소개 — HTML 모드", story_html.strip()),
        ("스토리 소개", "스토리 소개 — MD 모드", story_md.strip()),
    ]
    for t, ep, op in zip(titles, episodes, openings):
        sections += [(f"방식 A · {t}", "에피소드 내용", ep), (f"방식 A · {t}", "도입부", op)]
    sections += [("방식 B · 통합 1개", "에피소드 내용", allinone), ("방식 B · 통합 1개", "도입부", openings[0]),
                 ("기타", "제작자 노트", f["note"]), ("기타", "번역 메모 — 영어", f["tr_en"]),
                 ("기타", "번역 메모 — 일본어", f["tr_ja"])]
    data = json.dumps([{"group": g, "label": l, "text": t} for g, l, t in sections], ensure_ascii=False)
    data = data.replace("</", "<\\/")
    page = (ROOT / "copy_helper.template.html").read_text(encoding="utf-8")
    page = page.replace("__DATA__", data).replace("__TOTAL_A__", f"{total_a:,}").replace("__TOTAL_B__", f"{total_b:,}")
    (DIST / "copy_helper.html").write_text(page, encoding="utf-8")

    print(f"작품 글자 수  A(5화) {total_a:,} / B(통합) {total_b:,}  (한도 {LIMIT_WORK:,})")
    print(f"스토리 소개 HTML {len(story_html):,}자 (한도 {LIMIT_INTRO:,}), 이미지 {len(images_used)}장")
    print("에피소드 내용", [len(e) for e in episodes], "통합", len(allinone))


if __name__ == "__main__":
    main()
