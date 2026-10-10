# 내 남자친구는 구미호 — 티키타 판타지 × 인외 공모전 출품작

티키타 크리에이터 가이드와 티키타 HTML 작성 규칙에 맞춰 만든 등록 패키지입니다.

| 파일 | 내용 |
|---|---|
| `tikita/dist/guidebook.html` | **등록 가이드북.** 만들기 화면 단계별 복사 버튼과 체크리스트 (Artifact로 발행) |
| `tikita/dist/copy_helper.html` | **칸별 복사 버튼 페이지.** 만들기 화면 단계 순서대로 정리되어 있다 |
| `tikita/dist/tikita_register.md` | 단계별 붙여넣기 안내, 작품 글자 수 내역, 갤러리 계획, 공개 전 체크리스트 |
| `tikita/dist/story_intro.html` | 스토리 소개 HTML (공개여부 단계) |
| `tikita/dist/status_window.html` | 변수 디자인 HTML (상태창, 높이 88px) |
| `characters.md` | 캐릭터 외관 설정과 기준 시트 프롬프트 |
| `tikita/image_prompts.md` | 갤러리·썸네일·비밀 이미지·프로필 이미지 프롬프트 |
| `manuscript.md` | 전체 원고(작가용, 약 5.5만 자). 티키타에는 직접 넣지 않는다 |

## 티키타 칸 구성

| 단계 | 칸 | 원본 (`tikita/src/`) |
|---|---|---|
| 시작하기 | 형식: 스토리 | — |
| 01 프로필 | 제목 · 태그라인 · 스토리 설정 | `profile/` |
| 01 프로필 | 캐릭터 3명 (백도겸 · 윤서 · 면객), 공개 / 비공개 정보 | `characters/char1~3/` |
| 02 대화 | 첫 메시지 · 대화 시작 문구 3 · 추천 페르소나 3 · 예시 대화 5 | `dialogue/` |
| 03 에피소드 | 순차 진행 5화 — 제목 · 본문 · 비공개 설정 · 전환 조건 | `episodes/ep1~5/` |
| 03 에피소드 | 변수 7개 · 변수 디자인 HTML | `variables.json`, `status_window.html` |
| 03 에피소드 | 로어북 12개 | `lorebook.json` |
| 04 갤러리 | 이미지 그룹 5 · 이미지 6장(비밀 1) · 채팅 이미지 모드: 배경 | `gallery.json` |
| 05 공개여부 | 스토리 소개 HTML · 카테고리 · 태그 · 제작자 코멘트 · 번역 메모 | `publish/`, `translation/` |

## 고치는 법

`tikita/src/`를 고친 뒤 아래를 실행하면 `tikita/dist/`가 다시 만들어집니다.

```bash
python3 gumiho-boyfriend/tikita/build.py
```

규격을 어기면 무엇이 틀렸는지 출력하고 멈춥니다. 점검하는 항목은 다음과 같습니다.
- 칸별 한도와 작품 글자 수 30,000자
- 대사·지문 형식(`이름: 대사`, `*지문*`)과 마크다운 사용 여부
- 전환 조건의 `{{user}}` / `{{char1}}` 포함 여부
- `[[var:…]]` 갱신 지시의 변수 이름
- 스토리 소개의 허용 태그·속성과 금지 CSS(`url()` 등)
- 상태창 10,240바이트와 변수 토큰

이미지 주소가 생기면 `tikita/src/images.json`에 넣고 다시 생성하세요. 스토리 소개의 정해진 자리에 `<img class="intro-html-img">`가 들어갑니다. 붙여 넣은 뒤 티키타의 **외부 이미지 가져오기**를 누르면 Tikita Storage 주소로 바뀝니다.
