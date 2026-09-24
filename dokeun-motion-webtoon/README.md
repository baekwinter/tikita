# 도근고등학교 달빛 방송부 — 〈고백이 잘못 송출되었습니다〉

도근도근 디스코드 서버의 YES/NO 탐정 추리 이벤트입니다.
**이벤트 운영은 디스코드 봇**이, **몰입형 플레이는 웹 조사실**이 맡고, 두 쪽 모두 **하나의 게임 엔진과 하나의 DB**를 씁니다.

- 개막: **2026-09-24 00:00 (Asia/Seoul)** = `2026-09-23T15:00:00Z`
- 서버 `1539519514956398692` · 이벤트 채널 `1548252787002048572`
- 12화 모션 웹툰 + YES/NO 질문 + 증거 조사 + 최종 추리 + 달빛 수사 포인트

```
                ┌──────────────────────┐        ┌───────────────────────────┐
 Discord 채널 ◀─┤  bot/ (discord.py)   │        │  web/ (Next.js 수사실 UI) │◀─ 참가자 브라우저
  개막·회차·증거│  예약 공개·버튼·명령어 │        │  /api/* → FastAPI 로 전달  │
  공지, 버튼    └─────────┬────────────┘        └────────────┬──────────────┘
                          │  bot.game.GameService (공용 엔진)  │
                          │                    ┌──────────────▼──────────────┐
                          │                    │ api/ (FastAPI)               │
                          │                    │ Discord OAuth2 · 서버 멤버 확인 │
                          ▼                    └──────────────┬──────────────┘
                  ┌───────────────────────────────────────────▼──┐
                  │ SQLite (WAL) bot/var/dalbit.db — 진행도·게시 이력 │
                  └───────────────────────────────────────────────┘
                  bot/data/*.json  — 회차·증거·질문 / 정답(answers.json, 서버 전용)
```

## 폴더 구조

```
dokeun-motion-webtoon/
├─ source/ story/ characters/ assets/ episodes/ output/   ← 기존 제작 자료 (봇이 수정하지 않음)
├─ bot/            디스코드 봇 + 게임 엔진 (Python 3.11+)
│  ├─ main.py config.py database.py scheduler.py commands.py ui.py
│  ├─ game.py questions.py evidence.py rewards.py ai.py cli.py
│  ├─ data/        episodes.json evidence.json questions.json answers.json rewards.json settings.json
│  ├─ tests/       pytest 58개
│  ├─ .env.example requirements.txt README.md
├─ api/            웹 조사실 백엔드 (FastAPI) — app.py, requirements.txt
├─ web/            웹 조사실 프론트엔드 (Next.js 16 · React 19 · TypeScript)
│  ├─ src/app/ (첫 화면, /play)  src/components/  src/lib/  src/styles/
│  ├─ public/ next.config.js package.json .env.example
├─ shared/schema/  데이터 파일 JSON Schema
├─ shared/content/ 콘텐츠 편집 안내
├─ Dockerfile railway.json fly.toml   봇 컨테이너 배포 설정
├─ deploy/         systemd 서비스 3개 + Caddyfile
└─ docs/OPERATIONS.md  운영진 매뉴얼 · 테스트 시나리오 · 장애 대응
```

## 1. 로컬 실행 (5분)

```bash
cd dokeun-motion-webtoon
python3 -m venv .venv && source .venv/bin/activate
pip install -r bot/requirements-dev.txt
cp bot/.env.example bot/.env          # 값 채우기 (아래 3절)

python -m bot.cli check               # 데이터·편성·미디어 점검
python -m bot.cli simulate            # 임시 DB 로 전체 일정 모의 실행 (게시 없음)
python -m pytest bot -q               # 테스트

python -m bot.main                    # 봇
uvicorn api.app:app --port 8000       # 웹 API
cd web && npm install && npm run build && npm start   # 웹 (http://localhost:3000)
```

디스코드 없이 웹 화면만 확인하려면 **별도 테스트 값**으로 개발용 로그인을 켭니다 (실서버 ID 로는 동작하지 않음):

```bash
export DG_TEST_MODE=true DG_TEST_GUILD_ID=42 DG_TEST_CHANNEL_ID=43 DG_WEB_DEV_LOGIN=true DG_DB_PATH=/tmp/dalbit-dev.db
uvicorn api.app:app --port 8000
# 브라우저에서 http://localhost:3000/api/auth/dev?uid=1 로 접속
```

## 2. Discord Developer Portal 설정 (운영진이 직접)

1. <https://discord.com/developers/applications> → **New Application** → 이름 `도근고등학교 달빛 방송부`.
2. **General Information**: 앱 아이콘(포스터 등) 등록, **Application ID** 복사 → `.env` 의 `DISCORD_APPLICATION_ID`, `DISCORD_CLIENT_ID`.
3. **Bot** 탭
   - Username 을 `도근고등학교 달빛 방송부` 로 설정 (서버에 표시되는 이름).
   - **Reset Token** → 토큰을 `.env` 의 `DISCORD_TOKEN` 에만 붙여 넣습니다. 채팅·스크린샷·깃에 절대 올리지 마세요.
   - **Privileged Gateway Intents 3개는 모두 끈 상태로 둡니다** (이 봇은 메시지 내용을 읽지 않습니다).
   - Public Bot 은 꺼 두는 것을 권장합니다 (다른 서버 초대 방지).
4. **OAuth2** 탭 (웹 로그인용)
   - **Client Secret** → `.env` 의 `DISCORD_CLIENT_SECRET`.
   - **Redirects** 에 `https://<웹 도메인>/api/auth/callback` 추가 (로컬은 `http://localhost:3000/api/auth/callback`).
   - 웹 로그인은 `identify guilds` 범위만 요청합니다 (사용자 ID·이름, 참여 서버 목록 → 도근도근 멤버인지 확인).

## 3. 봇 초대와 권한

`.env` 에 `DISCORD_APPLICATION_ID` 를 넣은 뒤 **실제 Application ID 로** 초대 링크를 만듭니다:

```bash
python -m bot.cli invite
```

- 범위: `bot`, `applications.commands`
- 권한(117760): 채널 보기 · 메시지 보내기 · 링크 임베드 · 파일 첨부 · 메시지 기록 보기 — **관리자 권한은 요청하지 않습니다.**
- 초대 후, 이벤트 채널 `#…(1548252787002048572)` 에서 봇 역할에 위 권한이 실제로 허용되어 있는지 채널 권한을 확인하세요.
- 봇을 실행하면 로그에도 같은 초대 링크가 출력됩니다.

**명령어 노출 범위**: 명령어는 도근도근 서버에만 등록되고, 게임 기능은 이벤트 채널에서만 동작합니다.
`/운영` 은 기본적으로 '서버 관리' 권한자에게만 보입니다. 운영진 2명이 그 권한이 없다면
서버 설정 → 연동(Integrations) → 달빛 방송부 → `/운영` 에서 운영진 역할/사용자를 허용하고,
`.env` 의 `DG_ADMIN_USER_IDS` 에 두 사람의 사용자 ID 를 넣으세요 (실행 시 한 번 더 확인합니다).

## 4. 환경 변수

`bot/.env.example` 을 복사해 `bot/.env` 로 사용합니다 (봇과 웹 API 가 같은 파일을 읽음). `web/.env.example` 은 `API_ORIGIN` 하나입니다.
`.env` 는 `.gitignore` 에 포함되어 있으며, 토큰·키는 코드와 로그에 출력하지 않습니다.

| 변수 | 설명 |
|---|---|
| `DISCORD_TOKEN` | 봇 토큰 |
| `DISCORD_APPLICATION_ID` / `DISCORD_CLIENT_ID` / `DISCORD_CLIENT_SECRET` | 앱 ID, OAuth2 |
| `DG_ADMIN_USER_IDS` | 운영진 2명의 사용자 ID (쉼표 구분) |
| `DG_ADMIN_ALERT_CHANNEL_ID` | 운영 알림 채널 (없으면 운영진 DM) |
| `DG_WEB_URL` | 디스코드 버튼에 걸 웹 조사실 주소 |
| `DG_PUBLIC_URL` / `DG_SESSION_SECRET` | 웹 공개 주소, 세션 서명 키 |
| `DG_DB_PATH` | 공유 DB 경로 (봇·API 동일해야 함) |
| `DG_AI_ENABLED` / `ANTHROPIC_API_KEY` | 선택: AI 질문 해석 보조 |
| `DG_TEST_*` | 별도 테스트 서버 리허설용 |

## 5. 12화 콘텐츠 등록

1. 영상·썸네일을 `episodes/EP01.mp4`, `episodes/EP01_thumb.jpg` … 로 넣습니다.
   - 파일이 `settings.json` 의 `media.upload_limit_mb`(기본 10MB, 서버 부스트 등급에 맞게 조정) 이하면 **디스코드 첨부**로 올립니다.
   - 더 크면 `episodes.json` 의 `video_url` 에 **접근 가능한 영상 링크**를 넣습니다.
   - 둘 다 없으면 봇은 없는 파일·링크를 만들지 않고 **공개를 보류하고 운영진에게 알립니다** (`missing_video_policy: hold`).
2. `episodes.json` 의 `title`, `description`, `keywords` 를 스토리보드 기준으로 채웁니다.
3. 메인 포스터를 `assets/poster.png` 로 넣습니다 (또는 `settings.json` 의 `poster_url`).
4. 증거 이미지는 `assets/evidence/E-01.png` … (없으면 텍스트만 표시).
5. `python -m bot.cli check` 로 누락이 없는지 확인합니다.

## 6. 공개 일정 (한국 시간)

`bot/data/settings.json` → `schedule`

- `mode`: `4days_3per_day` (기본, 9/24~27 하루 3화) 또는 `3days_4per_day` (9/26 종료 필요 시).
- 1화는 개막 시각(9/24 00:00)에 공개됩니다. **나머지 시각은 임의로 정하지 않았으니 `times` 의 `null` 을 운영진이 직접 채워 주세요**
  (예: `["00:00", "12:00", "20:00"]`). 시각이 `null` 인 회차는 자동 공개되지 않습니다.
- 행사 중 변경은 `/운영 예약 회차:5 일시:2026-09-25 18:00` (DB 에 저장, 파일보다 우선).
- `ending_at` 을 넣으면 12화 공개 후 그 시각에 엔딩(진실 공개 + 정답 보상 정산)이 자동 게시됩니다. 비워 두면 `/운영 공개 대상:엔딩` 으로 수동 게시.

## 7. 배포 (이벤트 기간 내내 켜 두기)

봇이 꺼져 있으면 아무것도 자동 게시되지 않습니다. 9/23~9/28 동안 상시 실행되는 서버가 필요합니다.

**가장 간단한 방법: [docs/DEPLOY.md](docs/DEPLOY.md)** — `Dockerfile` + `railway.json` 으로 Railway 에 봇을 올립니다 (Fly.io 용 `fly.toml` 포함).

웹 조사실까지 함께 운영하려면 소형 리눅스 VM 1대(1 vCPU / 1GB)에 봇·API·웹을 함께 실행합니다.

```bash
sudo useradd -r -m dalbit && sudo mkdir -p /opt && sudo chown dalbit /opt
sudo -u dalbit git clone <repo> /opt/repo && sudo ln -s /opt/repo/dokeun-motion-webtoon /opt/dokeun-motion-webtoon
cd /opt/dokeun-motion-webtoon
python3.11 -m venv .venv && .venv/bin/pip install -r api/requirements.txt
cp bot/.env.example bot/.env && chmod 600 bot/.env    # 값 채우기
(cd web && npm ci && npm run build)
sudo cp deploy/dalbit-*.service /etc/systemd/system/ && sudo systemctl daemon-reload
sudo systemctl enable --now dalbit-bot dalbit-api dalbit-web
# HTTPS: deploy/Caddyfile 의 도메인을 바꾼 뒤 Caddy 로 3000 포트를 프록시
journalctl -u dalbit-bot -f    # 로그 (bot/var/bot.log 에도 기록)
```

- 서버 시계는 NTP 동기화(`timedatectl`)를 확인하세요. 봇은 내부적으로 UTC 로 계산하고 Asia/Seoul 로 표시합니다.
- DB 백업: `sqlite3 bot/var/dalbit.db ".backup backup-$(date +%F).db"` 를 하루 한 번.

## 8. 재시작 · 장애 대응

- **중복 게시 방지**: 모든 공식 게시는 DB 에 먼저 선점(`posting`)하고, 성공 시 메시지 ID 와 함께 `posted` 로 기록합니다. 재시작해도 같은 공지·회차는 다시 올라가지 않습니다.
- **게시 도중 종료**: 재시작 시 채널 최근 50개 메시지에서 `ref:episode:N` 표식을 찾아 복구하고, 없을 때만 다시 게시합니다.
- **늦게 켜진 경우**: 공개 시각이 30분(`catchup_grace_minutes`) 넘게 지난 회차는 몰아서 올리지 않고 운영진에게 알립니다 → `/운영 공개` 로 수동 공개. 개막 공지는 12시간까지 자동 보충.
- **Discord 오류**: 5xx·네트워크 오류는 2/4/8초 간격으로 재시도(재시도 전 이미 올라갔는지 확인). 권한 오류는 재시도하지 않고 운영 알림.
- **버튼**: 공식 게시물 버튼은 영구 버튼이라 재시작 후에도 동작합니다.
- 자세한 절차는 [docs/OPERATIONS.md](docs/OPERATIONS.md).

## 9. 게임 설계 요약

- **YES/NO 판정**: `questions.json`(인식 규칙, 정답 없음) + `answers.json`(정답·공개 회차, 서버 전용).
  인물 조합·필수 개념·주어 방향이 모두 맞을 때만 같은 질문으로 인정합니다. "하늘이는 휘혈이를 좋아해?" 와 "휘혈이는 하늘이를 좋아해?" 는 다른 질문입니다.
  부정형("~하지 않았나요?")·애매한 질문은 답하지 않고 다시 묻게 하여 키워드 오답을 막습니다. 해석 실패 질문은 횟수에서 차감하지 않습니다.
- **미공개 정보**: `minimum_episode` 이전에는 "아직 공개되지 않은 정보입니다." 만 답하고, 메모·관련 증거도 숨깁니다. 잠긴 증거는 번호와 공개 회차만 보입니다.
- **AI 보조(선택)**: 규칙 해석이 실패했을 때, 현재 답할 수 있는 표준 질문 목록 중 같은 뜻을 고르게만 합니다. 정답과 미공개 질문은 AI 에게 전달되지 않습니다. 키가 없어도 게임은 정상 동작합니다.
- **최종 추리**: Q1~Q4 인물 선택 + Q5 '왜·어떻게' 서술(+ 사건 흐름). Q5 는 '오해를 풀기 위해'(필수) + 방법·무단·두 음성 중 2개 이상이 있어야 인정되어, 이름만 맞혀서는 해결되지 않습니다.
  기본 3회 제출, 제출 시 "5문항 중 N개 정답" 만 알려 줍니다(`feedback: count`, 문항별 정오는 비공개). `sealed` 로 바꾸면 엔딩까지 결과를 숨깁니다.
- **포인트**: 이벤트 전용 '달빛 수사 포인트'(`rewards.json`). 보상 키 단위로 1회만 지급. 기존 레벨링 봇 EXP 는 공식 연동 API 가 확인되지 않아 **직접 바꾸지 않습니다** — 종료 후 CSV(`/운영 결과 형식:CSV` 또는 웹 `/api/admin/export.csv`)로 내려받아 수동 지급하세요.
- **개인정보**: Discord 사용자 ID·표시 이름·게임 진행도(질문 문장, 가설, 노트 포함)만 저장합니다. DM·전화번호·실제 연애 관계는 수집하지 않습니다.

## 10. 원작 확인이 필요한 항목

사건의 확정 사실(녹음자·상대·답장·예약 목록 수정·송출자·21:00 송출·남궁호 비공범·2025/2026 별도 사건)은 그대로 반영했습니다.
다만 아래는 원작 자료(PPT·스토리보드)가 저장소에 없어 **임시 값**이니 운영진이 확인해 주세요.

- 회차별 제목·설명, 각 증거가 열리는 회차, 각 질문의 `minimum_episode` (현재는 추리 흐름에 맞춘 임시 배치)
- 증거 E-01~E-08 의 상세 문구 (확정 사실만으로 작성)
- `answers.json` 에서 `confirmed: false` 인 3문항 (2025년 답장 전달을 누군가 고의로 막았는지, 차세리의 2025년 관여, 남궁호에게 편집을 부탁한 사람) — 원작에 근거가 없어 답하지 않도록 두었습니다.
