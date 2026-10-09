"""티키타 등록 패키지를 src/ 원본에서 만들고, 크리에이터 가이드 규격을 점검한다.

    python3 build.py

dist/ 에 쓰는 것
  tikita_register.md   만들기 화면 단계 순서(프로필 → 대화 → 에피소드 → 갤러리 → 공개여부)의 붙여넣기 안내
  copy_helper.html     칸마다 복사 버튼이 있는 페이지
  story_intro.html     스토리 소개 (HTML 모드)
  status_window.html   변수 디자인 (HTML 모드)

규격을 하나라도 어기면 무엇이 틀렸는지 출력하고 멈춘다.
"""
import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / "src"
DIST = ROOT / "dist"

TOTAL_LIMIT = 30_000
INTRO_LIMIT = 40_000          # 칸 표시는 50,000이지만 HTML 규칙 문서 기준 40,000으로 잡는다
STATUS_BYTES = 10_240

INTRO_TAGS = set("""h1 h2 h3 h4 h5 h6 p br hr strong em b i u s del mark small sub sup ul ol li dl dt dd
a img figure figcaption blockquote pre code table thead tbody tfoot tr th td div span section article
details summary""".split())
INTRO_ATTRS = set("href target rel src alt width height class id style colspan rowspan scope open loading".split())
BAD_CSS = re.compile(r"url\(|@import|expression\(|image-set\(|behavior\s*:", re.I)
IMG_SLOT = re.compile(r"^\s*\[\[IMG:(\w+)\]\]\s*$", re.M)
VAR_DIRECTIVE = re.compile(r"\[\[var:([^=\]]+)=")

errors, warnings = [], []


def read(rel):
    return (SRC / rel).read_text(encoding="utf-8").strip()


def lines(rel):
    return [l.strip() for l in read(rel).split("\n") if l.strip()]


def limit(label, text, n, minimum=0):
    if len(text) > n:
        errors.append(f"{label}: {len(text):,}자 > {n:,}자")
    if len(text) < minimum:
        errors.append(f"{label}: {len(text):,}자 < 최소 {minimum:,}자")


class TagCheck(HTMLParser):
    def __init__(self, label, tags, attrs):
        super().__init__()
        self.label, self.tags, self.attrs = label, tags, attrs

    def handle_starttag(self, tag, attrs):
        if self.tags is not None and tag not in self.tags:
            errors.append(f"{self.label}: 허용되지 않은 태그 <{tag}>")
        for name, value in attrs:
            if self.attrs is not None and name not in self.attrs:
                errors.append(f"{self.label}: <{tag}>의 허용되지 않은 속성 {name}")
            if name.startswith("on"):
                errors.append(f"{self.label}: 이벤트 속성 {name}")
            if name == "style" and value and BAD_CSS.search(value):
                errors.append(f"{self.label}: <{tag}> style에 url()·@import 등 — style 전체가 지워짐")
            if name == "style" and value and re.search(r"position\s*:\s*fixed|z-index", value):
                warnings.append(f"{self.label}: position:fixed / z-index는 쓰지 않는 것이 좋음")

    handle_startendtag = handle_starttag


def check_html(label, markup, tags=None, attrs=None):
    if re.search(r"<\s*(style|script|iframe|svg|link|meta)\b", markup, re.I):
        errors.append(f"{label}: <style>/<script> 등 금지 태그")
    TagCheck(label, tags, attrs).feed(markup)


def check_dialogue(label, text, names, literal_names):
    """'이름: 대사' / *지문* 형식 점검 (가이드 02 · 대사와 지문 형식)."""
    speakers = set(names) | {"{{user}}"} | {f"{{{{char{i}}}}}" for i in range(1, 11)}
    if literal_names:
        speakers = set(names)
    for raw in text.split("\n"):
        line = raw.strip()
        if not line:
            continue
        if re.match(r"^(#|\*\*|```|- |\d+\. )", line):
            errors.append(f"{label}: 채팅은 마크다운을 지원하지 않음 → {line[:20]}")
        if line.startswith("*"):
            if not (line.endswith("*") and len(line) > 2):
                errors.append(f"{label}: 지문은 별표로 감싸 한 줄로 → {line[:20]}")
            if ":" in line:
                errors.append(f"{label}: 지문 안의 콜론은 이름으로 오인됨 → {line[:20]}")
            continue
        m = re.match(r"^([^:：]{1,20}): \S", line)
        if not m or m.group(1) not in speakers:
            errors.append(f"{label}: 이름 없는 줄은 지문 처리됨. '이름: 대사' 또는 *지문*으로 → {line[:24]}")


def main():
    DIST.mkdir(exist_ok=True)

    # ── 01 프로필
    title, tagline, setting = read("profile/title.txt"), read("profile/tagline.txt"), read("profile/story_setting.txt")
    limit("제목", title, 20)
    limit("태그라인", tagline, 100, 1)
    limit("스토리 설정", setting, 20_000, 1)
    chars = []
    for d in sorted((SRC / "characters").iterdir()):
        c = {k: read(f"characters/{d.name}/{k}.txt") for k in ("name", "public", "private")}
        limit(f"캐릭터 이름({c['name']})", c["name"], 15, 1)
        limit(f"{c['name']} 공개 정보", c["public"], 20_000, 1)
        limit(f"{c['name']} 비공개 정보", c["private"], 20_000)
        chars.append(c)
    if not 1 <= len(chars) <= 10:
        errors.append("캐릭터는 1~10명")
    names = [c["name"] for c in chars]

    # ── 02 대화
    first = read("dialogue/first_message.txt")
    limit("첫 메시지", first, 20_000, 1)
    if not 700 <= len(first) <= 1200:
        warnings.append(f"첫 메시지 {len(first):,}자 — 권장 700~1,200자")
    check_dialogue("첫 메시지", first, names, literal_names=True)
    starters = lines("dialogue/starters.txt")
    if len(starters) > 3:
        errors.append("대화 시작 문구는 3개까지")
    for i, s in enumerate(starters, 1):
        limit(f"대화 시작 문구 {i}", s, 200, 1)
    personas = lines("dialogue/personas.txt")
    if len(personas) > 3:
        errors.append("추천 페르소나는 3개까지")
    examples = [read(f"dialogue/examples/{p.name}") for p in sorted((SRC / "dialogue/examples").glob("*.txt"))]
    if len(examples) > 5:
        errors.append("예시 대화는 5개까지")
    for i, e in enumerate(examples, 1):
        limit(f"예시 대화 {i}", e, 5_000, 1)
        check_dialogue(f"예시 대화 {i}", e, names, literal_names=False)

    # ── 03 에피소드
    variables = json.loads(read("variables.json"))
    if len(variables) > 10:
        errors.append("변수는 10개까지")
    var_names = [v["name"] for v in variables]
    for v in variables:
        if len(v["name"]) > 10 or " " in v["name"]:
            errors.append(f"변수 이름 '{v['name']}': 10자 이내, 띄어쓰기 없이")
        limit(f"변수 {v['name']} 설명", v["description"], 5_000)
        limit(f"변수 {v['name']} 범위 설명", v["range"], 5_000)
        limit(f"변수 {v['name']} 시작값", v["start"], 200, 1)

    episodes = []
    for d in sorted((SRC / "episodes").iterdir()):
        e = {k: read(f"episodes/{d.name}/{k}.txt") for k in ("title", "body", "private", "condition")}
        n = len(episodes) + 1
        limit(f"{n}화 제목", e["title"], 20, 1)
        limit(f"{n}화 본문", e["body"], 2_000, 1)
        limit(f"{n}화 비공개 설정", e["private"], 2_000)
        limit(f"{n}화 전환 조건", e["condition"], 200)
        if n > 1:
            if not e["condition"]:
                errors.append(f"{n}화 전환 조건이 비어 있음")
            elif "{{user}}" not in e["condition"] and "{{char1}}" not in e["condition"]:
                errors.append(f"{n}화 전환 조건에 {{{{user}}}} 또는 {{{{char1}}}} 필요")
            if e["condition"].startswith("조건"):
                errors.append(f"{n}화 전환 조건에 '조건:' 접두사를 붙이지 않음")
        episodes.append(e)
    if not 1 <= len(episodes) <= 20:
        errors.append("에피소드는 1~20개")

    for label, text in [("스토리 설정", setting)] + [(f"{i}화 비공개 설정", e["private"]) for i, e in enumerate(episodes, 1)]:
        for name in VAR_DIRECTIVE.findall(text):
            if name not in var_names:
                errors.append(f"{label}: [[var:{name}=…]] — 정의되지 않은 변수")

    status = read("status_window.html")
    status_bytes = len(status.encode("utf-8"))
    if status_bytes > STATUS_BYTES:
        errors.append(f"상태창 {status_bytes:,}바이트 > {STATUS_BYTES:,}")
    if re.search(r"\{\{\s*(user|char\d+)\s*\}\}", status):
        errors.append("상태창에서는 {{user}}·{{charN}}이 치환되지 않음")
    for tok in re.findall(r"\{\{([^}]+)\}\}", status):
        tok = tok.strip()
        if tok.startswith(("#", "/")):
            parts = tok[1:].split()
            if tok.startswith("#") and len(parts) > 1 and parts[0] not in ("each",) and parts[1] not in var_names:
                errors.append(f"상태창 조건의 변수 '{parts[1]}' 없음")
            continue
        head = tok.split()[0].split(":")[0]
        if head not in var_names and head not in ("name", "value", "numericValue", "math", "repeat", "gauge", "icon"):
            errors.append(f"상태창 토큰 {{{{{tok}}}}} — 변수 이름과 다르면 글자 그대로 보임")
    check_html("상태창", status)

    lore = json.loads(read("lorebook.json"))
    if len(lore) > 200:
        errors.append("로어북은 작품당 200개까지")
    for item in lore:
        limit(f"로어북 '{item['title']}' 제목", item["title"], 50, 1)
        limit(f"로어북 '{item['title']}' 내용", item["content"], 500, 1)
        if not 1 <= len(item["keywords"]) <= 20:
            errors.append(f"로어북 '{item['title']}': 키워드 1~20개")
        for k in item["keywords"]:
            if not 2 <= len(k) <= 60:
                errors.append(f"로어북 '{item['title']}': 키워드 '{k}'는 2~60자")

    # ── 04 갤러리
    gallery = json.loads(read("gallery.json"))
    for g in gallery["groups"]:
        limit(f"이미지 그룹명 {g}", g, 50, 1)
    for im in gallery["images"]:
        limit(f"이미지 설명 {im['file']}", im["description"], 100, 1)
        if im["group"] not in gallery["groups"]:
            errors.append(f"{im['file']}: 없는 그룹 {im['group']}")

    # ── 05 공개여부
    images = json.loads(read("images.json"))
    alts = {im["key"]: im["description"] for im in gallery["images"]}

    def slot(m):
        url = images.get(m.group(1), "").strip()
        if not url:
            return ""
        return (f'<img class="intro-html-img" src="{html.escape(url, quote=True)}" '
                f'alt="{html.escape(alts.get(m.group(1), ""), quote=True)}" loading="lazy" '
                f'style="width:100%;height:auto;border-radius:12px;display:block;margin:12px 0">')

    intro = IMG_SLOT.sub(slot, read("publish/intro.html"))
    intro = re.sub(r"\n{3,}", "\n\n", intro).strip() + "\n"
    limit("스토리 소개 HTML", intro, INTRO_LIMIT, 100)
    check_html("스토리 소개", intro, INTRO_TAGS, INTRO_ATTRS)
    comment = read("publish/creator_comment.txt")
    limit("제작자 코멘트", comment, 20_000)
    cats, tags = lines("publish/categories.txt"), lines("publish/tags.txt")
    if not 1 <= len(cats) <= 3:
        errors.append("카테고리 1~3개")
    if not 1 <= len(tags) <= 15:
        errors.append("태그 1~15개")
    for t in ("판타지공모전", "인외"):
        if t not in tags:
            errors.append(f"공모전 필수 태그 '{t}' 없음")

    # ── 작품 글자 수 (부록 · 합산에 ○인 칸)
    parts = {
        "스토리 설정": len(setting),
        "캐릭터": sum(len(c["name"]) + len(c["public"]) + len(c["private"]) for c in chars),
        "첫 메시지·대화 시작 문구": len(first) + sum(map(len, starters)),
        "예시 대화": sum(map(len, examples)),
        "변수": sum(len(v["name"]) + len(v["description"]) + len(v["range"]) + len(v["start"]) for v in variables),
        "에피소드 제목·전환 조건": sum(len(e["title"]) + len(e["condition"]) for e in episodes),
        "이미지 그룹명·설명": sum(map(len, gallery["groups"])) + sum(len(i["description"]) for i in gallery["images"]),
    }
    total = sum(parts.values())
    if total > TOTAL_LIMIT:
        errors.append(f"작품 글자 수 {total:,} > {TOTAL_LIMIT:,}")

    if errors:
        print("규격 오류:")
        for e in errors:
            print("  ✕", e)
        raise SystemExit(1)

    (DIST / "story_intro.html").write_text(intro, encoding="utf-8")
    (DIST / "status_window.html").write_text(status + "\n", encoding="utf-8")
    write_register(title, tagline, setting, chars, first, starters, personas, examples, variables, episodes,
                   status, status_bytes, lore, gallery, intro, comment, cats, tags, parts, total)
    write_helper(title, tagline, setting, chars, first, starters, personas, examples, variables, episodes,
                 status, lore, gallery, intro, comment, cats, tags, total)

    print(f"작품 글자 수 {total:,} / {TOTAL_LIMIT:,}")
    for k, v in parts.items():
        print(f"  {k}: {v:,}")
    print(f"스토리 소개 {len(intro):,}자 · 상태창 {status_bytes:,}바이트 · 로어북 {len(lore)}개 · 에피소드 {len(episodes)}개")
    for w in warnings:
        print("  ! " + w)


def fence(text, lang=""):
    ticks = "````" if "```" in text else "```"
    return f"{ticks}{lang}\n{text}\n{ticks}"


def write_register(title, tagline, setting, chars, first, starters, personas, examples, variables, episodes,
                   status, status_bytes, lore, gallery, intro, comment, cats, tags, parts, total):
    L = []
    a = L.append
    a("# 티키타 등록 안내 — 내 남자친구는 구미호")
    a("")
    a("`build.py`가 `src/`에서 만든 파일입니다. 고칠 때는 `src/`를 고치고 다시 생성하세요. 순서는 티키타 만들기 화면의 단계와 같습니다.")
    a("")
    a("## 시작하기")
    a("- 형식: **스토리** (시네마는 모든 캐릭터의 표정 스프라이트가 있어야 해서, 이미지가 준비되기 전에는 스토리가 빠릅니다)")
    a("")
    a(f"## 작품 글자 수 — {total:,} / 30,000")
    a("")
    a("| 항목 | 글자 수 |")
    a("|---|---|")
    for k, v in parts.items():
        a(f"| {k} | {v:,} |")
    a("")
    a("에피소드 본문·비공개 설정, 로어북, 스토리 소개, 제작자 코멘트, 추천 페르소나는 합산에 들어가지 않습니다.")
    a("")
    a("## 01 프로필")
    a(f"### 제목 ({len(title)}자 / 20)")
    a(fence(title))
    a(f"### 태그라인 ({len(tagline)}자 / 100)")
    a(fence(tagline))
    a(f"### 스토리 설정 ({len(setting):,}자)")
    a(fence(setting))
    for i, c in enumerate(chars, 1):
        a(f"### 캐릭터 {i} — {c['name']}" + (" (주인공, 1번 카드)" if i == 1 else ""))
        a(f"이름: `{c['name']}`")
        a(f"공개 정보 ({len(c['public']):,}자) — 독자에게 보이고 AI도 읽습니다")
        a(fence(c["public"]))
        a(f"비공개 정보 ({len(c['private']):,}자) — AI만 읽습니다")
        a(fence(c["private"]))
    a("카드 순서를 바꾸면 `{{char1}}`~`{{char3}}` 번호도 바뀌므로 이 순서(백도겸 → 윤서 → 면객)를 유지하세요. 캐릭터마다 프로필 이미지가 필요합니다.")
    a("")
    a("## 02 대화")
    a(f"### 첫 메시지 ({len(first):,}자, 권장 700~1,200)")
    a("지문은 `*별표*`로 감싸고 대사는 `이름: 대사` 형식입니다. 첫 메시지에는 자동 별표가 적용되지 않으므로 그대로 붙여 넣으세요.")
    a(fence(first))
    a("### 대화 시작 문구 (받아들이기 · 파고들기 · 피하기)")
    for s in starters:
        a(fence(s))
    a("### 추천 페르소나 (선택)")
    for p in personas:
        a(fence(p))
    a("### 예시 대화")
    pats = ["처음 만났을 때", "부탁받을 때", "거절당할 때", "다퉜을 때", "다른 사람과 있을 때"]
    for i, e in enumerate(examples, 1):
        a(f"#### 예시 {i} — {pats[i-1] if i <= len(pats) else ''}")
        a(fence(e))
    a("")
    a("## 03 에피소드")
    a("- 진행 모드: **순차 진행** (기승전결이 있는 5화 구성. 한 화에서 100회를 넘기면 다음 화가 자동으로 열립니다)")
    a("- 에피소드 시작 배경: 시네마 전용이라 스토리 형식에서는 없습니다")
    a("")
    for i, e in enumerate(episodes, 1):
        a(f"### {i}화 — {e['title']}")
        a(f"제목 ({len(e['title'])}자 / 20)")
        a(fence(e["title"]))
        a(f"본문 ({len(e['body']):,}자 / 2,000)")
        a(fence(e["body"]))
        a(f"비공개 설정 ({len(e['private']):,}자 / 2,000)")
        a(fence(e["private"]))
        if e["condition"]:
            a(f"전환 조건 ({len(e['condition'])}자 / 200)")
            a(fence(e["condition"]))
        else:
            a("전환 조건: 비워 둠 (순차 진행의 첫 화)")
    a("### 변수")
    a("만들기 화면에서는 텍스트와 숫자만 고를 수 있습니다. 숫자 변수에는 최소·최대값을 함께 넣으세요.")
    for v in variables:
        a(f"#### {v['name']} — {v['type']}")
        a("설명")
        a(fence(v["description"]))
        if v["range"]:
            a("범위 설명")
            a(fence(v["range"]))
        a(f"시작값: `{v['start']}`")
    a(f"### 변수 디자인 — HTML ({status_bytes:,}바이트 / 10,240)")
    a("변수 디자인에서 **HTML**을 누르고 입력칸을 비운 뒤 붙여 넣으세요. 카드가 가로로 2줄이라 높이 300px 안에 들어갑니다. `정체`와 `초대양도`는 기록용이라 표시하지 않고, `여우불`은 1 이상일 때만 나타납니다.")
    a(fence(status, "html"))
    a(f"### 로어북 ({len(lore)}개)")
    a("에피소드 단계 맨 아래 **로어북 관리**에서 항목마다 만든 뒤 **이 작품에 적용**을 누르고, 작품을 저장하세요.")
    for item in lore:
        a(f"#### {item['title']}")
        a(f"발동 키워드: `{', '.join(item['keywords'])}`")
        a(fence(item["content"]))
    a("")
    a("## 04 갤러리")
    a("- 채팅 이미지 모드: **배경** (장소와 분위기가 중요한 작품)")
    a(f"- 이미지 그룹: {', '.join(gallery['groups'])}")
    a("")
    a("| 파일명 | 그룹 | 설명 | 비고 |")
    a("|---|---|---|---|")
    for im in gallery["images"]:
        note = "썸네일" if im.get("thumbnail") else ""
        if im.get("secret"):
            note = f"비밀 이미지 · 해금 비용 {im['unlock_cost']}틱 · 최소 해금 조건 {im['min_unlock']}회"
        a(f"| {im['file']} | {im['group']} | {im['description']} | {note} |")
    a("")
    a("본모습 이미지는 4화의 반전이므로 비밀 이미지로 두고 최소 해금 조건을 켜 두세요. 첫 메시지와 썸네일에는 넣지 않습니다.")
    a("")
    a("## 05 공개여부")
    a(f"### 스토리 소개 — HTML ({len(intro):,}자)")
    a("AI는 이 글을 읽지 않습니다. 이미지 주소를 넣었다면 붙여 넣은 뒤 **외부 이미지 가져오기**를 누르세요.")
    a(fence(intro.strip(), "html"))
    a(f"- 카테고리: {' · '.join(cats)}")
    a(f"- 태그 ({len(tags)}/15): {', '.join(tags)}")
    a("- 연령: **전체 이용가** · 2차 창작: 체크하지 않음")
    a(f"### 제작자 코멘트 ({len(comment):,}자)")
    a(fence(comment))
    a("### 번역 메모")
    a("영어")
    a(fence(read("translation/en.txt")))
    a("일본어")
    a(fence(read("translation/ja.txt")))
    a("")
    a("## 공개 전 체크리스트")
    for t in ["제목 · 태그라인", "캐릭터 3명 — 이름 · 소개 · 프로필 이미지", "첫 메시지", "본문이 있는 에피소드 5개",
              "갤러리 이미지 1장 이상(설명 포함) · 썸네일", "카테고리 · 태그(판타지공모전, 인외 포함)",
              "스토리 소개 100자 이상", "테스트 대화 10회 (화면 아래 '생성'을 먼저 눌러야 대화 버튼이 생김)",
              "작품 글자 수 30,000자 이내", "준비가 끝난 시점에 처음 공개 (신작·급상승에 첫 공개 시점이 반영됨)",
              "공모전 페이지에서 '공모전 참여하기'로 제출 (마감 10월 31일)"]:
        a(f"- [ ] {t}")
    a("")
    (DIST / "tikita_register.md").write_text("\n".join(L), encoding="utf-8")


def write_helper(title, tagline, setting, chars, first, starters, personas, examples, variables, episodes,
                 status, lore, gallery, intro, comment, cats, tags, total):
    S = []
    add = lambda g, l, t: S.append({"group": g, "label": l, "text": t})
    add("01 프로필", "제목", title)
    add("01 프로필", "태그라인", tagline)
    add("01 프로필", "스토리 설정", setting)
    for i, c in enumerate(chars, 1):
        g = f"01 프로필 · 캐릭터 {i} {c['name']}"
        add(g, "이름", c["name"])
        add(g, "공개 정보", c["public"])
        add(g, "비공개 정보", c["private"])
    add("02 대화", "첫 메시지", first)
    for i, s in enumerate(starters, 1):
        add("02 대화", f"대화 시작 문구 {i}", s)
    for i, p in enumerate(personas, 1):
        add("02 대화", f"추천 페르소나 {i}", p)
    for i, e in enumerate(examples, 1):
        add("02 대화", f"예시 대화 {i}", e)
    for i, e in enumerate(episodes, 1):
        g = f"03 에피소드 · {i}화"
        add(g, "제목", e["title"])
        add(g, "본문", e["body"])
        add(g, "비공개 설정", e["private"])
        if e["condition"]:
            add(g, "전환 조건", e["condition"])
    for v in variables:
        g = f"03 변수 · {v['name']} ({v['type']})"
        add(g, "이름", v["name"])
        add(g, "설명", v["description"])
        if v["range"]:
            add(g, "범위 설명", v["range"])
        add(g, "시작값", v["start"])
    add("03 변수 디자인", "HTML", status)
    for item in lore:
        g = f"03 로어북 · {item['title']}"
        add(g, "제목", item["title"])
        add(g, "발동 키워드", ", ".join(item["keywords"]))
        add(g, "내용", item["content"])
    for im in gallery["images"]:
        add("04 갤러리 · 이미지 설명", im["file"], im["description"])
    add("05 공개여부", "스토리 소개 (HTML)", intro.strip())
    add("05 공개여부", "제작자 코멘트", comment)
    add("05 공개여부", "태그 (하나씩)", "\n".join(tags))
    add("05 공개여부", "번역 메모 — 영어", read("translation/en.txt"))
    add("05 공개여부", "번역 메모 — 일본어", read("translation/ja.txt"))
    data = json.dumps(S, ensure_ascii=False).replace("</", "<\\/")
    page = (ROOT / "copy_helper.template.html").read_text(encoding="utf-8")
    page = page.replace("__DATA__", data).replace("__TOTAL__", f"{total:,}")
    (DIST / "copy_helper.html").write_text(page, encoding="utf-8")


if __name__ == "__main__":
    main()
