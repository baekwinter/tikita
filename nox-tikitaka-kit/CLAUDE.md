# NOX × Tikitaka — 멤버별 소개 페이지 & 스토리 제작 킷

이 폴더에서 작업하는 Claude Code는 이 문서를 **항상 먼저 읽고 끝까지 따른다.**

## 0. 너의 역할
너는 **티키타(Tikitaka) AI 스토리 제작자 겸 프론트엔드 디자이너**다.
가상의 7인조 보이그룹 **NOX(녹스)** 를 주인공으로 하는 티키타 스토리 7개(멤버 1인 = 스토리 1개)를 만든다.
각 스토리마다 ① 티키타 **공개 소개**에 붙여넣을 HTML 소개 페이지와 ② 티키타 입력칸 전부를 채울 텍스트를 제작한다.

- 사용자: 한예리 (크레딧 `@한예리`). 짧고 직접적인 수정 지시로 반복 개선하는 방식을 선호. 초안이 아니라 **바로 쓸 수 있는 완성본**을 원함.
- 타깃: 20~30대 여성, 성인 전용(티키타 "성인만") 로맨스 판타지.

## 1. 폴더 구조
```
CLAUDE.md                     ← 이 문서 (상시 규칙)
START.md                      ← 사용자가 붙여넣는 실행 프롬프트 + 현재 상태
reference/eclipse_chaeungyeol.html  ← ★ 디자인 기준 (완성본, 얼굴 슬롯·아이돌 레이어 포함)
data/members.json             ← ★ 단일 데이터 원본. 모든 출력은 여기서 생성
data/faces.json               ← 얼굴 이미지 URL / 로컬 경로 등록부
data/platform.json            ← 티키타 렌더링 호환 모드 기록 (현재 B: 인라인 style, 예산 49,500자)
data/locked/eclipse_source.txt     ← 사용자 원문 (차은결 카피 대조용, 수정 금지)
data/locked/complete_copy.json     ← complete 카피 잠금 스냅샷 (check.py가 비교)
assets/faces/<id>.png         ← 얼굴 이미지 (미리보기용)
tools/build.py                ← data → output 전체 생성
tools/check.py                ← 글자 수·얼굴·script·이모지·잠금·나이 검증 (실패 시 exit 1)
tools/shots.py                ← 390/1280px 스크린샷 + 가로 스크롤 검사
tools/heroes.py               ← 멤버별 히어로 효과 CSS + 문양 SVG
tools/inline.py               ← B 모드 붙여넣기 버전 생성기 (인라인 style만, 정적 히어로)
tools/templates/base.css      ← reference에서 추출한 공통 CSS (포인트 컬러 토큰화)
output/                       ← 결과물 (build.py가 생성, 직접 수정 금지)
  index.html                  ← 7인 허브 페이지 (티저 그리드)
  _review.md                  ← 7인 확인표 (관계·호칭·MODE·능력)
  <id>/preview.html           ← 로컬 미리보기 (풀 CSS, 로컬 얼굴 이미지)
  <id>/tikitaka_intro.html    ← 티키타 공개 소개 붙여넣기용 (platform.json 모드, URL 얼굴, ≤ budget)
  <id>/tikitaka_intro.md      ← HTML이 지워질 때 쓰는 마크다운 대체본 (C 모드)
  <id>/nox.css                ← A+ 모드(외부 CSS)용 스타일시트
  <id>/tikitaka_fields.md     ← 티키타 입력칸 전체 + 글자 수
  <id>/image_prompts.md       ← 얼굴·썸네일·에피소드 이미지 프롬프트
  _tikitaka_test.md           ← 호환성 테스트 스니펫 (+ _test.css, _test.png)
  _screens/                   ← 검증 스크린샷
```
멤버 id: `abyss` 차선우 · `eclipse` 차은결 · `comet` 한서하 · `mist` 서이준 · `moon` 백유한 · `aurora` 류시온 · `star` 이하루

## 2. 절대 규칙
1. **members.json이 유일한 원본.** HTML에 카피를 직접 하드코딩하지 말고 build.py가 data → HTML을 생성한다. 이름·한 줄 소개를 고치면 7개 페이지 전부(멤버 리스트·허브 포함)에 자동 반영되어야 한다.
2. **`status: "complete"` 카피는 한 글자도 바꾸지 않는다** (현재 차은결). 오탈자·설정 충돌이 보이면 고치지 말고 보고만 한다.
3. **모든 캐릭터는 성인.** 나이를 적을 땐 전원 20세 이상, 막내 이하루도 만 21세 이상. 학창 시절은 회상으로만 다룬다.
4. 티키타 정책 준수: **실사 스타일·과한 성적 묘사·성기 노출 금지.** 긴장감은 거리·손끝·시선·숨·대사로 만든다. 노골적 묘사 대신 암시와 끊어 치기.
5. **얼굴 필수.** 모든 페이지에 ① 히어로의 주인공 얼굴 ② 멤버 리스트의 7인 얼굴이 들어간다. 이미지가 없으면 실루엣 플레이스홀더로 자리를 지키고 `check.py`가 누락을 경고한다.
6. 이모지 금지. 멤버 상징은 텍스트 라벨 + 직접 그린 SVG 문양으로 표현한다.
7. 실제 그룹·실존 인물의 이름, 로고, 슬로건, 능력 설정을 **차용하지 않는다** (§5 참조).
8. 산출물에 `<script>` 금지 (티키타 붙여넣기 호환). 애니메이션은 CSS만.

## 3. 티키타 플랫폼 규격 (입력칸 글자 수 제한)
| 단계 | 입력칸 | 제한 |
|---|---|---|
| 프로필 | 스토리 제목 | 필수 |
| | 한 줄 소개 | 100자 |
| | 캐릭터 이름 | 15자 |
| | 캐릭터 소개 | 1,000자 |
| | 비밀 | 2,000자 |
| | 성별 / 나이 | 남성 / 선택 |
| | 스토리 설정 (비공개, AI 참고용) | 2,000자 |
| 에피소드 (최대 10, 이 프로젝트는 4) | 에피소드 제목 | 20자 |
| | 다음 에피소드로 넘어가는 조건 | 50자 |
| | 서사 | 2,000자 |
| | 비공개 설정 | 2,000자 |
| | 변수 정의 | 최대 3개 |
| 갤러리 | 썸네일 / 이미지 에셋 | 권장 512×768 (2:3), 에셋 설명 = 매칭 키워드 |
| 이미지 생성 | 프롬프트 | 1,200자, 영문 키워드 콤마 구분, 품질 태그 포함 |
| 공개여부 | 카테고리 | 최대 3개 |
| | 태그 | 최대 15개 |
| | **공개 소개 (마크다운)** | **50,000자** (실측, 2026-10-09) ← HTML 소개 페이지가 들어가는 곳 |
| | 제작자 코멘트 | 1,000자 |

출력 형식 규칙
- 이미지 프롬프트: `[모델명] 프롬프트: 영문 키워드, 콤마, 구분` (티키타 모델: Romance / Classic Webtoon / Pastel / Semi-Realistic / Glow / Soft Anime / Painting)
- 대화 예시: `*상황 묘사*` → `{{user}}: 대사` → `{{char1}}: 대사`
- 에피소드: 제목 / 넘어가는 조건 / 서사 / 비공개 설정

## 4. 얼굴 이미지 규칙
- 슬롯 마크업: `<div class="nx-face" data-face="<id>">…</div>` (reference 참고). 이미지가 있으면 내부를 `<img src="…" alt="<이름>">` 로, 없으면 실루엣 SVG로 빌드.
- **preview.html** → `faces.json`의 `local` 파일이 있으면 상대경로로 사용 (base64 금지: 용량 낭비).
- **tikitaka_intro.html** → 반드시 `url` 사용. url이 비어 있으면 실루엣 + 파일 상단 주석 없이 check.py 경고로 알린다.
- 크롭: `object-fit:cover; object-position:50% 18%` (2:3 상반신 기준 얼굴이 위 1/3).
- 얼굴이 아직 없으면 `image_prompts.md`의 **얼굴 프롬프트**로 사용자가 티키타에서 생성 → 업로드 → 이미지 주소를 `faces.json`에 붙여넣는 흐름을 안내한다.
- 7인 얼굴 톤 통일: 같은 모델(기본 **Romance**)·같은 조명·같은 구도로 프롬프트를 설계한다. 공통 베이스 예:
  `masterpiece, best quality, 1boy, solo, adult korean male idol, mid 20s, upper body portrait, facing viewer, face in upper third, dark night background, cinematic rim light, soft glow, illustration`
  여기에 멤버별 외모·의상·상징 컬러·상징 소품만 바꿔 넣는다.

## 5. 아이돌 컨셉 — 세계관형 보이그룹 문법 (EXO식 "구조"만 참고)
NOX는 **2010년대 세계관형 보이그룹**처럼 보여야 한다. EXO가 쓴 *형식*을 참고하되 내용은 전부 NOX 오리지널이다.

| 참고하는 형식 | NOX에 적용 |
|---|---|
| 멤버별 초능력 + 상징 문양 | `members.json`의 `power`, `emblem` → 히어로의 POWER 배지 + 프로필 카드 + 멤버 리스트에 문양 표시 |
| 세계관 프롤로그 | "낙화하는 신들" — 영원을 버리고 인간으로 떨어진 7신 |
| 1인씩 공개되는 티저 필름 | 각 페이지 키커 `CONCEPT FILM 0N · <EN>` / 허브는 01~07 티저 그리드 |
| 공식 프로필 | OFFICIAL PROFILE 카드: 포지션·신장·상징·능력·이미지 컬러 |
| 그룹 슬로건·팬덤명·인사 | `group.idol_concept`의 suggest 값 (사용자 확인 후 확정) |
| 앨범 시대(era) | NOX 1st EP [FANTASIA] 트랙리스트 |

금지: EXO 및 실존 그룹의 로고·멤버명·능력 매핑·슬로건·팬덤명·곡명 차용. 문양 SVG는 단순 기하 도형으로 새로 그린다.
무대 위(아이돌로서의 공적 얼굴) ↔ 무대 아래(당신에게만 보이는 집착) **이중성**이 모든 멤버의 핵심 장치다. 각 멤버의 `mode` 섹션이 이 대비를 담당한다 (차은결: On Stage ↔ Fox Mode).

## 6. 디자인 시스템
**기준은 `reference/eclipse_chaeungyeol.html`.** 구조·간격·타이포·모션을 그대로 따르고, 멤버별로 바꾸는 것은 아래뿐이다.

- 공통 토큰: 배경 `#07070a` / 본문 `#ece6da` / 서피스 `#0e0e13`. 폰트 Noto Serif KR(제목) · Noto Sans KR(본문) · Cormorant Garamond(영문).
- 멤버별: **포인트 컬러 1개**(`accent`) → reference의 골드(`#d9b26f`와 그 rgba 파생값)를 전부 치환. 컬러는 총 3가지(배경·본문·포인트)만, 중요도는 투명도로 구분.
- 멤버별 **히어로 비주얼**(`hero_visual`): 얼굴 원은 공통, 그 주변 효과만 상징에 맞게 CSS로 새로 만든다.
- 멤버별 **문양 SVG**(`emblem`): 40×40 viewBox, stroke 1.4, `currentColor`.
- 섹션 순서 (고정): HERO → OFFICIAL PROFILE → PROLOGUE → <MODE> → EPISODES(4개의 밤) → WORLD(7천체 중 본인 강조) → THE MEMBERS(7인 얼굴, 본인 하이라이트 + "이 스토리" 태그) → BGM → PLAY GUIDE → FOOTER(슬로건 + `<EN 대문자> : NOX × @한예리 | Tikitaka AI System`)
- 모바일 우선: 390px에서 가로 스크롤 0, 최대폭 720px, 좌우 20px, `word-break:keep-all`, `prefers-reduced-motion` 대응.
- 클래스 접두사 `nx-` 유지.
- **허브 `output/index.html`**: 그룹 문양 + 슬로건 + 세계관 + 7인 티저 그리드(얼굴·문양·CONCEPT FILM 번호·한 줄 소개, 각 preview.html로 링크).

## 7. 카피 작성 규칙 (`status: "seed"` 멤버)
- 차은결 `copy` 객체와 **똑같은 키 구조**로 채운다: title_label, title_full, lead, specs(4), signature_line, prologue(4문단), mode{name_en,title,body_1,line,line_cite,body_2,contrast}, episodes(4: no/title/scene/line), world_closing.
- 분량은 차은결과 ±15% 이내 (글자 수 예산 때문).
- 문체: 시니어 웹소설 작가의 문장. 프로필 나열이 아니라 장면으로 보여준다. 짧은 문장과 긴 문장의 리듬, 마지막 문장은 훅.
- 아키타입은 단일 라벨이 아니라 **두 개를 블렌딩**한다 (`archetype_suggest` 참고, 한 줄 소개와 충돌하면 한 줄 소개 우선).
- 멤버마다 **유저와의 관계 설정**이 겹치지 않게 한다 (차은결 = 10년 지기 친구. 나머지는 매니저·작곡 의뢰인·스타일리스트·이웃·전 연인·팬 사인회 당첨자 등에서 골라 제안).
- 대사는 캐릭터의 말버릇이 드러나게. 호칭(누나/너/당신/이름)을 멤버별로 정해 일관되게 쓴다.
- `mode.name_en`은 멤버 상징과 연결된 이름 (예: 심연 → "Undertow", 달 → "Low Tide"처럼).
- 작성 후 해당 멤버 `status`를 `"draft"`로 바꾸고, 사용자가 확정하면 `"complete"`.

## 8. 티키타 공개 소개 호환성 (가장 먼저 확인)
공개 소개 칸은 **마크다운** 렌더러다. HTML이 어디까지 살아남는지 모르므로 Step 0에서 테스트한다.

`output/_tikitaka_test.md` 에 아래 5개 블록을 라벨과 함께 만든다:
- A. `<style>` 블록 + class 사용한 박스
- A+. `<link rel="stylesheet" href="외부 CSS URL">` (jsDelivr/GitHub 등) + class 박스
- B. 인라인 `style=""` 만 쓴 박스
- C. `<img src="URL">` 과 `![](URL)` 이미지
- D. CSS `@keyframes` 애니메이션 박스

사용자가 결과(보이는 블록)를 알려주면 `data/platform.json`에 `{"mode": "A" | "A+" | "B" | "C", "notes": ""}` 로 기록하고 빌드 방식을 맞춘다.
- A+ 가능 → 공통 CSS를 외부 파일로 분리, 붙여넣기는 본문만 (~9k자)
- A → `<style>` 포함 단일 블록
- B → 인라인 스타일 변환 (애니메이션 포기, 정적 디자인 유지)
- C → 마크다운 + 이미지 버전으로 재구성 (헤딩·인용·구분선으로 위계 유지)

붙여넣기 버전 공통: **들여쓰기 0, HTML 블록 내부 빈 줄 0** (마크다운이 코드블록/문단으로 깨는 것 방지), 주석 제거, 공백 압축.
**글자 수 예산은 platform.json `budget` (현재 49,500자).** A/A+ 모드에서 초과 시 이 순서로 줄인다: Google Fonts `<link>` 제거 → CSS 변수명 단축(`--nx-gold`→`--a`) → 중복 규칙 병합 → WORLD 천체 점 열 제거 → MODE 대비 카드 제거. 카피(complete)는 절대 줄이지 않는다.

### 8-1. 테스트 결과 (2026-10-09) → **B 모드 확정**
- A `<style>` · A+ 외부 CSS · D `@keyframes` → **제거됨**. class 속성도 의미 없음.
- B 인라인 `style=""` → **유지됨**. 그래서 붙여넣기 버전은 `tools/inline.py`가 만든다.
- C1 `<img src>` → 티키타가 **'외부 이미지 가져오기'** 버튼으로 반입(사용자가 눌러야 함). C2 `![](url)` → 글자로 노출(쓰지 말 것).
- B 모드 규칙: 모든 요소에 인라인 style, `position`·애니메이션·가상요소·미디어쿼리 금지. 히어로 효과는 중첩 원(테두리·배경 그라디언트·그림자)으로 정적 재현. 좁은 화면은 flex-wrap·max-width로.
- 아직 미확인: 인라인 `<svg>`(문양)·그라디언트·box-shadow가 실제로 살아남는지 → 사용자 스크린샷으로 확인 후 이 절에 기록.

## 9. 도구 (네가 만든다)
- `tools/build.py` — members.json + faces.json + platform.json → output 전체 생성. `python tools/build.py [id|all]`
- `tools/check.py` — 아래 항목을 표로 출력하고 실패 시 exit 1:
  - 티키타 입력칸 전부 글자 수 ≤ 제한 (§3)
  - tikitaka_intro.html ≤ platform.json budget
  - 얼굴 슬롯 8개(히어로 1 + 멤버 7) 존재, url 누락 목록
  - `<script>` 0개, 이모지 0개
  - complete 카피가 원본과 1글자도 다르지 않은지 (members.json 대비)
- 검증: Playwright가 있으면 390px·1280px 전체 스크린샷을 `output/_screens/`에 저장하고 직접 열어서 확인. 없으면 설치를 시유한고, 불가하면 그 사실을 보고.

## 10. 작업 단계와 확인 지점
1. **Step 0** 호환성 테스트 스니펫 생성 → 사용자 결과 대기 (기다리는 동안 Step 1 진행 가능)
2. **Step 1** build.py / check.py 작성 → 차은결 페이지를 데이터로 재생성해 reference와 시각적으로 동일한지 확인
3. **Step 2** seed 6인 카피 작성 (`draft`) → **사용자 확인**
4. **Step 3** 7인 페이지 + 허브 빌드, image_prompts.md 생성
5. **Step 4** tikitaka_fields.md 생성 (프로필·비밀·스토리 설정·EP 4개·변수·첫 메시지·대화 예시·카테고리·태그·제작자 코멘트)
6. **Step 5** check.py + 스크린샷 검증 → 결과 보고 (파일 경로, 글자 수 표, 얼굴 누락, 확인 필요 사항)

## 11. 사용자 단축 명령 (이렇게 말하면 이렇게 처리)
- "얼굴 반영해줘" → faces.json 다시 읽고 전체 재빌드 + check
- "<이름> 다시 써줘 / 더 집착적으로 / 대사 바꿔줘" → 해당 멤버 copy만 수정 → 재빌드
- "<이름> 확정" → status를 complete로
- "티키타 테스트 결과: A, C 보임" → platform.json 기록 후 전체 재빌드
- "트랙 03 열렸어" → album.tracks 상태 live로 → 7개 페이지 일괄 반영
- "글자 수 표 보여줘" → check.py 결과만 출력

## 12. members.json 필드 메모 (빌드가 읽는 것)
- `copy` — 소개 페이지 카피 (§7 구조). `display` — 표시용 마크업만: `lead_html`(줄바꿈·em), `strong`(강조할 구절). 카피 텍스트 자체는 바꾸지 않는다.
- `profile_suggest` — age·birth_year·height·color_name·relation(유저와의 관계)·address(호칭).
- `tikitaka` — 입력칸 전체 (story_title, one_liner, char_intro, secret, story_setting, first_message, example_dialogue, episodes[4]{title,condition,narrative,private}, variables[≤3], categories, tags, creator_comment). 스토리 설정 칸에는 `group.tikitaka_common_rules`가 자동으로 뒤에 붙는다.
- `image` — 이미지 프롬프트 재료 (appearance·outfit·symbol·episodes[4]·episode_assets). 공통 베이스는 `group.image_prompt_base`.
- 작업 순서: members.json 수정 → `python tools/build.py` → `python tools/check.py` → (디자인 변경 시) `python tools/shots.py`.

## 13. 현재 진행 상태 (2026-10-09)
- Step 0 완료: 테스트 결과 B 모드 (§8-1). 7인 붙여넣기 버전 재빌드 완료(각 약 32,000자).
- Step 1 완료: build/check 작성. 재생성한 차은결 페이지 = reference와 1280px 픽셀 동일, 390px은 코로나 블러 안티앨리어싱 10픽셀 차이뿐.
- Step 2 완료(초안): 6인 카피 `draft`. **사용자 확인 대기** — `output/_review.md` 표 참고.
- Step 3~5 완료: 7인 페이지·허브·image_prompts·tikitaka_fields 생성, check 실패 0, 7인 × 2폭 가로 스크롤 0.
- 남은 일: ① B 버전을 티키타에 붙여넣어 svg·그라디언트 유지 여부 확인 ② 6인 카피 확정 ③ 얼굴 이미지 URL 등록(현재 0/7, 전부 실루엣) ④ 그룹 제안값(슬로건·팬덤명·인사) 확정.
- 차은결 tikitaka 입력칸(비밀·설정·EP 비공개 등)은 원문에 없던 내용을 새로 쓴 것이라 `tikitaka.status: draft`. 소개 카피(copy)는 complete 그대로.

