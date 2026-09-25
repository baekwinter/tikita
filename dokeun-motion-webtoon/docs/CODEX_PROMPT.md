# 코덱스(Codex)용 작업 프롬프트 — 달빛 방송부 봇 배포

아래 ``` 안의 내용을 그대로 코덱스에 붙여 넣으세요.
비밀 값(봇 토큰, Railway 토큰)은 프롬프트에 적지 말고 코덱스 실행 환경의 **환경 변수/시크릿**으로 넣으세요.

```
너는 이 저장소의 디스코드 봇을 실제 운영 환경에 배포하고 검증하는 배포 엔지니어다.
가능한 모든 단계는 직접 실행하고, 사람의 로그인·승인이 필요한 단계만 정확히 요청한 뒤 기다려라.

## 프로젝트
- 저장소: baekwinter/tikita, 브랜치: claude/festive-cannon-8ihj63
- 작업 폴더: dokeun-motion-webtoon/
- 봇: bot/ (Python 3.11, discord.py). 실행: `python -m bot.main`
- 배포 설정: dokeun-motion-webtoon/Dockerfile, railway.json, fly.toml
- 안내서: dokeun-motion-webtoon/docs/DEPLOY.md, docs/OPERATIONS.md, README.md — 먼저 읽고 그대로 따른다.
- 봇 이름: 도근고등학교 달빛 방송부
- 디스코드 서버 ID 1539519514956398692, 이벤트 채널 ID 1552877179187232798
- 개막: 2026-09-24 00:00 Asia/Seoul (이미 지났을 수 있음)

## 완료 기준
1. 봇이 Railway(불가하면 Fly.io)에서 24시간 실행 중이고, /data 영구 볼륨에 DB 가 저장된다.
2. 배포 로그에 `길드 명령어 10개 등록 (서버 1539519514956398692)` 와 `로그인:` 줄이 있다.
3. 디스코드 REST API 로 봇이 서버에 들어와 있고 이벤트 채널을 볼 수 있음을 확인했다.
4. 운영진에게 남은 작업(/운영 예약, /운영 시작)을 정확한 명령어로 안내했다.

## 절대 규칙
- 사건 설정, bot/data/answers.json 의 정답, 질문 답변을 바꾸지 않는다.
- 토큰·시크릿을 코드, 커밋, 로그, 출력, 커밋 메시지에 절대 남기지 않는다. echo 로 출력하지 않는다.
  .env 는 커밋하지 않는다.
- 실제 이벤트 채널에 테스트 메시지를 보내지 않는다. 검증은 읽기 전용 API(GET)만 사용한다.
  공식 게시는 운영진이 디스코드에서 `/운영 시작` 으로 한다.
- 서버의 다른 채널, 역할, 설정을 건드리지 않는다. 관리자 권한을 요구하지 않는다(권한 정수 117760 유지).
- Application ID, 초대 링크, 배포 성공 여부를 추측하거나 지어내지 않는다. 확인한 값만 보고한다.
- 사람이 해야 하는 단계에서 막히면 우회하지 말고 "사람 작업 필요" 로 멈추고 무엇이 필요한지 한 번에 요청한다.
- 코드 수정은 배포 실패를 고치는 데 꼭 필요한 최소한만 한다. 수정했다면 먼저
  `cd dokeun-motion-webtoon && python -m pytest bot -q` 를 통과시키고 커밋한다.

## 사람이 해야 하는 일 (너는 할 수 없다 — 없으면 요청하고 기다린다)
- Discord Developer Portal 앱 생성, 봇 토큰 발급 → 환경 변수 DISCORD_TOKEN
- Application ID → 환경 변수 DISCORD_APPLICATION_ID
- 초대 승인: 서버 관리자가 아래 링크를 열어 승인 (<ID> 는 실제 Application ID 로 네가 채워서 제시)
  https://discord.com/oauth2/authorize?client_id=<ID>&scope=bot+applications.commands&permissions=117760
- Railway 인증: 환경 변수 RAILWAY_TOKEN(프로젝트 토큰) 또는 RAILWAY_API_TOKEN(계정 토큰).
  Fly.io 라면 FLY_API_TOKEN.
- 운영진 2명의 디스코드 사용자 ID → DG_ADMIN_USER_IDS (쉼표 구분)
- (선택) 2~12화 공개 시각, 영상 링크(video_url), 운영 알림 채널 ID

## 작업 순서
1. 점검
   - `cd dokeun-motion-webtoon && pip install -r bot/requirements-dev.txt`
   - `python -m pytest bot -q` (58개 통과해야 함)
   - `python -m bot.cli check` 결과를 기록한다. 영상·제목·편성 누락은 배포를 막지 않지만 보고서에 적는다.
   - 필요한 환경 변수가 있는지 이름만 확인한다(값 출력 금지). 없으면 "사람 작업 필요" 로 한 번에 요청.
2. 토큰 검증 (읽기 전용)
   - `GET https://discord.com/api/v10/users/@me` (헤더 `Authorization: Bot $DISCORD_TOKEN`) → 봇 id/이름 확인.
     응답의 id 가 DISCORD_APPLICATION_ID 와 일치하는지 확인.
   - `GET /users/@me/guilds` 에 1539519514956398692 가 있는지 확인. 없으면 초대 링크를 제시하고 승인을 기다린다.
   - `GET /channels/1552877179187232798` 가 200 인지 확인(403 이면 채널 권한 문제로 보고).
   - 네트워크 정책으로 discord.com 이 막혀 있으면 그 사실을 보고하고 배포 단계로 넘어간다.
3. 배포 (Railway 우선)
   - railway CLI 를 설치한다(`npm i -g @railway/cli`). 명령과 플래그는 추측하지 말고 `railway --help`,
     `railway <명령> --help` 로 확인한 뒤 사용한다.
   - 프로젝트/서비스를 만들거나 연결하고, 서비스 루트는 dokeun-motion-webtoon, 빌드는 Dockerfile 을 쓴다.
   - 볼륨을 /data 에 연결한다 (필수).
   - 변수 설정: DISCORD_TOKEN, DISCORD_APPLICATION_ID, DG_ADMIN_USER_IDS, TZ=Asia/Seoul,
     (있으면) DG_ADMIN_ALERT_CHANNEL_ID. 값은 환경 변수에서 읽어 넘기고 화면에 출력하지 않는다.
   - 배포 후 로그를 확인해 완료 기준 2의 두 줄을 찾는다. 오류가 있으면 원인을 고치고 재배포한다
     (최대 3회. 같은 오류가 반복되면 멈추고 보고).
   - Railway 를 쓸 수 없으면 docs/DEPLOY.md 4절대로 Fly.io 에 배포한다 (볼륨 dalbit_data → /data).
4. 콘텐츠 (사람이 값을 준 경우만)
   - 공개 시각: bot/data/settings.json 의 schedule.presets[mode] 의 null 을 받은 "HH:MM" 으로 채운다.
     받은 값이 없으면 임의로 정하지 않는다.
   - 영상 링크: bot/data/episodes.json 의 video_url 에 넣는다. 링크를 지어내지 않는다.
   - 수정 후 `python -m bot.cli check`, pytest 통과 → 커밋·푸시(같은 브랜치) → 자동 재배포 확인.
5. 마무리 보고 (짧게, 한국어)
   - 배포 플랫폼, 서비스 이름, 볼륨 연결 여부, 로그 증거 두 줄, REST 검증 결과
   - `bot.cli check` 의 남은 항목
   - 운영진 다음 행동 (개막 시각이 지났으면 반드시 포함):
     1) 이벤트 채널에서 `/운영 상태`
     2) `/운영 예약 회차:N 일시:YYYY-MM-DD HH:MM` 으로 2~12화 시각 입력
     3) `/운영 시작` → 개막 공지 + 1화 게시
     4) 이미 시각이 지난 회차는 `/운영 공개 대상:회차 번호:N` 으로 순서대로
   - 확인하지 못한 것은 확인하지 못했다고 쓴다.
```

## 참고 — 코덱스도 대신할 수 없는 것

- 디스코드 앱 생성·토큰 발급, 서버 초대 승인, Railway/Fly.io 로그인은 계정 주인이 직접 해야 합니다.
  토큰을 미리 발급해 코덱스 실행 환경의 시크릿에 넣어 두면 나머지는 코덱스가 진행할 수 있습니다.
- 코덱스 실행 환경의 인터넷 접근이 꺼져 있으면 배포 CLI 와 디스코드 확인이 모두 막히니, 코덱스 환경 설정에서 인터넷 접근을 허용하세요.
