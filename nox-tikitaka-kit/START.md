# NOX × 티키타 킷

## 지금 상태 (2026-10-09)
7인 소개 페이지 · 허브 · 티키타 입력칸 · 이미지 프롬프트까지 **전부 만들어져 있습니다.** 아래 4가지만 확인해 주면 끝납니다.

| 할 일 | 어디서 | 끝나면 Claude Code에 |
|---|---|---|
| ① 공개 소개 붙여넣기 | 테스트 결과 B 모드(인라인 style)로 확정됨. `output/<id>/tikitaka_intro.html` 전체를 공개 소개 칸에 | 미리보기 스크린샷을 보여주면 깨진 부분 수정 |
| ② 6인 카피 확인 | `output/_review.md` 표 + `output/<id>/preview.html` | `윤하겸 확정` / `백도하 EP02 대사 더 아프게` |
| ③ 얼굴 이미지 | `output/<id>/image_prompts.md` 얼굴 프롬프트 → 티키타 생성 → 주소를 `data/faces.json`에 | `얼굴 반영해줘` |
| ④ 그룹 제안값 | `_review.md` 하단 (슬로건 · 팬덤명 LUMEN · 인사) | `슬로건 확정` / `팬덤명 바꿔줘` |

- 붙여넣기: `output/<id>/tikitaka_intro.html` → 공개 소개 칸 / `output/<id>/tikitaka_fields.md` → 나머지 입력칸 (칸마다 복사 블록 + 글자 수)
- 미리보기: `output/index.html` (허브, 7인 링크)
- 직접 고친 뒤: `python tools/build.py` → `python tools/check.py`

---

## 처음부터 다시 시킬 때 — Claude Code 실행 프롬프트

이 폴더(`nox-tikitaka-kit`)를 Claude Code로 연 뒤, 아래 박스 안의 내용을 그대로 붙여넣으세요.
(Claude Code는 같은 폴더의 `CLAUDE.md`를 자동으로 읽습니다.)

---

```
CLAUDE.md를 끝까지 읽고 그 규칙대로 NOX 7인 티키타 스토리를 제작해줘.

목표
- 7명 멤버 각각의 티키타 공개 소개용 HTML 소개 페이지 + 티키타 입력칸 전체 텍스트
- NOX는 2010년대 세계관형 보이그룹 컨셉(EXO식 구조: 멤버별 초능력·상징 문양·티저 필름·공식 프로필). 단 실존 그룹 요소는 하나도 차용하지 말 것
- 모든 페이지에 캐릭터 얼굴: 히어로에 주인공 얼굴, 멤버 리스트에 7인 얼굴

기준
- 디자인 기준: reference/eclipse_chaeungyeol.html (구조·간격·모션 그대로, 멤버별로는 포인트 컬러·히어로 효과·문양만 변경)
- 데이터 원본: data/members.json (차은결은 complete — 카피 수정 금지)
- 얼굴: data/faces.json + assets/faces/

진행 순서
1. Step 0: output/_tikitaka_test.md 호환성 테스트 스니펫을 먼저 만들고, 내가 티키타 공개 소개 미리보기에 붙여넣을 방법을 3줄로 알려줘
2. 결과를 기다리는 동안 tools/build.py, tools/check.py를 만들고 차은결 페이지를 데이터로 재생성해서 reference와 같은지 스크린샷으로 확인
3. 나머지 6명 카피를 members.json에 draft로 작성하고, 멤버별 관계 설정·호칭·mode 이름·능력 요약을 표 하나로 보여준 뒤 내 확인을 받아
4. 확인 후 7인 페이지 + 허브(index.html) + image_prompts.md + tikitaka_fields.md 생성
5. check.py와 390px/1280px 스크린샷으로 검증하고 결과(파일 경로, 글자 수 표, 얼굴 누락, 확인 필요 사항)를 보고

모르는 건 추측하지 말고 확인 지점에서 물어봐.
```

---

## 이후 자주 쓰는 한 줄 명령

| 상황 | 이렇게 말하기 |
|---|---|
| 티키타에서 얼굴 생성 후 URL을 faces.json에 넣었을 때 | `얼굴 반영해줘` |
| 테스트 결과 알려줄 때 | `티키타 테스트 결과: A, C 보임` |
| 특정 멤버 수정 | `윤하겸 EP02 대사 더 집착적으로` |
| 카피 확정 | `백도하 확정` |
| 음원 업데이트 | `트랙 03 열렸어` |
| 글자 수 점검 | `글자 수 표 보여줘` |

## 얼굴 이미지 준비 흐름
1. `output/<id>/image_prompts.md`의 **얼굴 프롬프트** 복사 → 티키타 이미지 생성(Romance 모델) → 512×768
2. 마음에 드는 이미지를 캐릭터 프로필/갤러리에 업로드
3. 업로드된 이미지 우클릭 → 이미지 주소 복사 → `data/faces.json`의 `url`에 붙여넣기
4. (선택) 같은 이미지를 `assets/faces/<id>.png`로 저장하면 로컬 미리보기에도 표시
5. Claude Code에 `얼굴 반영해줘`
