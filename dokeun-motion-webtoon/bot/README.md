# bot/ — 달빛 방송부 디스코드 봇 & 게임 엔진

전체 설치·운영 안내는 상위 폴더의 [README.md](../README.md) 와 [docs/OPERATIONS.md](../docs/OPERATIONS.md) 를 보세요.

| 파일 | 역할 |
|---|---|
| `main.py` | 봇 실행, 공식 게시(DiscordPublisher), 명령어 등록 |
| `commands.py` | 슬래시 명령어 (참가자 9종 + `/운영` 8종) |
| `ui.py` | 임베드·버튼·모달, 재시작 후에도 동작하는 영구 버튼 |
| `scheduler.py` | 한국 시간 예약 공개, 중복 게시 방지, 재시작 복구 |
| `game.py` | 게임 규칙 (봇·웹 공용) |
| `questions.py` | YES/NO 질문 해석기 |
| `evidence.py` | 회차·증거 카탈로그와 공개 판정 |
| `rewards.py` | 달빛 수사 포인트, CSV 내보내기 |
| `database.py` | SQLite 저장소 (봇·웹 공유) |
| `ai.py` | 선택: AI 질문 해석 보조 |
| `cli.py` | 오프라인 점검 도구 |
| `data/` | 게임 데이터 (정답은 `answers.json` 에 분리) |

```bash
cd dokeun-motion-webtoon
python -m bot.cli check        # 데이터 점검
python -m pytest bot -q        # 테스트
python -m bot.main             # 봇 실행
```
