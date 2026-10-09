# 내 남자친구는 구미호 — 티키타 판타지 × 인외 공모전 출품작

| 파일 | 내용 |
|---|---|
| `manuscript.md` | 최종 원고 전체(검수 반영판, 약 5.5만 자). 작가용 비밀 포함 |
| `tikita/dist/copy_helper.html` | **칸별 복사 버튼 페이지.** 브라우저로 열고 하나씩 복사해 붙여 넣기 |
| `tikita/dist/tikita_register.md` | 칸별 붙여넣기 안내, 글자 수 점검, 제출 순서 |
| `tikita/dist/story_intro.html` | 스토리 소개 HTML 모드용 (p·h2·img·br 태그만 사용) |
| `tikita/dist/story_intro.md` | 스토리 소개 MD 모드용 |
| `tikita/dist/episode_1~5.txt` | 에피소드 내용 (공통 설정 + 해당 화) |
| `tikita/dist/episode_all.txt` | 에피소드를 하나만 등록할 때 쓰는 통합본 |
| `characters.md` | **캐릭터 외관 설정** — 도겸(사람·본모습·의상 4종), 윤서, 면객, 사용자 표현 규칙, 소품, 색 팔레트, 기준 시트 프롬프트 |
| `tikita/image_prompts.md` | 대표 포함 이미지 5장의 생성 프롬프트 (기준 시트를 먼저 만든 뒤 사용) |

## 고치는 법

`tikita/fields/`의 원본을 고친 뒤 아래를 실행하면 `dist/`가 다시 만들어집니다. 글자 수가 한도(작품 30,000 / 스토리 소개 50,000 / 제작자 노트 20,000)를 넘거나 허용되지 않은 HTML 태그가 들어가면 생성이 멈춥니다.

```bash
python3 gumiho-boyfriend/tikita/build.py
```

이미지 주소가 생기면 `tikita/fields/images.json`에 넣고 다시 생성하세요. 그러면 스토리 소개 HTML의 정해진 자리에 `<img>`가 들어갑니다. 붙여 넣은 뒤 티키타의 **외부 이미지 가져오기**를 누르면 Tikita Storage 주소로 바뀝니다.

## 등록 칸 대응

| 티키타 칸 | 넣을 것 |
|---|---|
| 태그라인 | `fields/tagline.txt` |
| 주인공 소개 | `fields/protagonist.txt` (공개용, 비밀 없음) |
| 에피소드 내용 | `dist/episode_N.txt`, 또는 하나만 등록할 때 `dist/episode_all.txt` (비밀 포함 — 독자에게 보이지 않는 칸으로 가정) |
| 도입부 | `fields/epN_opening.txt` |
| 스토리 소개 | `dist/story_intro.html` (HTML 모드) |
| 제작자 노트 / 번역 메모 | `fields/creator_note.txt`, `fields/translation_*.txt` |
| 카테고리 / 태그 / 연령 | 로맨스 판타지 · 현대 판타지 · 시대극/동양풍 / 15개(`판타지공모전`, `인외` 포함) / 전체 이용가 |
