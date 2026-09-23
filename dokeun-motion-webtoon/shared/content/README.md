# shared/content

게임 콘텐츠(텍스트 데이터)의 **원본은 `bot/data/*.json`** 이며, 봇과 웹 API 가 같은 파일을 읽습니다.
이 폴더는 데이터 편집 규칙을 안내하고, 스키마(`../schema`)와 함께 콘텐츠 담당자가 참고하는 곳입니다.

| 파일 | 내용 | 공개 범위 |
|---|---|---|
| `bot/data/episodes.json` | 12화 제목·설명·영상·썸네일·공개 시각·증거 | 공개된 회차만 참가자에게 노출 |
| `bot/data/evidence.json` | 증거 E-01~E-08 | 공개된 증거만 노출, 잠긴 증거는 번호만 |
| `bot/data/questions.json` | YES/NO 질문 인식 데이터 (정답 없음) | 서버 전용 |
| `bot/data/answers.json` | 질문 정답·공개 회차·최종 정답 | **서버 전용, 절대 프론트로 보내지 않음** |
| `bot/data/rewards.json` | 달빛 수사 포인트 지급표 | 서버 전용 |
| `bot/data/settings.json` | 개막 시각·편성표·질문 제한·정답 제출 규칙 | 서버 전용 |

미디어 파일은 `dokeun-motion-webtoon/` 기준 경로로 적습니다.

- 영상: `episodes/EP01.mp4` … (없으면 `video_url` 에 접근 가능한 링크)
- 썸네일/장면: `episodes/EP01_thumb.jpg` …
- 증거 이미지: `assets/evidence/E-01.png` …
- 메인 포스터: `assets/poster.png`

편집 후에는 `python -m bot.cli check` 로 반드시 점검하세요.
