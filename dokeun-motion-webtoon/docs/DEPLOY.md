# 봇 배포 안내 (Railway 권장 · Fly.io 대안)

봇은 **24시간 켜져 있어야** 회차를 자동 공개합니다. 아래 순서대로 하면 약 15분이면 끝납니다.
웹 조사실은 선택입니다. 디스코드 명령어·버튼만으로도 게임 전체가 진행됩니다.

## 0. 준비물 (Developer Portal, 5분)

1. <https://discord.com/developers/applications> → **New Application** → 이름 `도근고등학교 달빛 방송부`
2. **Bot** 탭 → Username 확인 → **Reset Token** → 토큰 복사 (채팅·깃에 붙여 넣지 말 것)
   - Privileged Gateway Intents 3개는 **모두 끈 채로** 둡니다.
3. **General Information** → **Application ID** 복사
4. 초대: 아래 주소의 `<APPLICATION_ID>` 를 바꿔 브라우저에서 열고, 도근도근 서버를 선택해 승인합니다 (서버 관리 권한 필요).
   ```
   https://discord.com/oauth2/authorize?client_id=<APPLICATION_ID>&scope=bot+applications.commands&permissions=117760
   ```
   권한 117760 = 채널 보기·메시지 보내기·링크 임베드·파일 첨부·메시지 기록 보기 (관리자 권한 없음)
5. 운영진 2명의 **사용자 ID** 준비 (디스코드 설정 → 고급 → 개발자 모드 켜기 → 프로필 우클릭 → ID 복사)

## 1. Railway 배포 (권장)

1. <https://railway.com> 에 GitHub 로 로그인 → **New Project → Deploy from GitHub repo** → 이 저장소 선택
2. 서비스 **Settings**
   - **Source → Root Directory**: `dokeun-motion-webtoon`
   - **Source → Branch**: 봇 코드가 있는 브랜치 (병합 전이면 `claude/festive-cannon-8ihj63`)
   - 빌드는 `Dockerfile` / `railway.json` 을 자동 인식합니다. 공개 도메인(Networking)은 만들 필요 없습니다.
3. **Volumes → Add Volume** → Mount path `/data` (게시 이력·진행도 DB 보관. **반드시 필요** — 없으면 재배포 때 기록이 사라져 공지가 다시 올라갈 수 있습니다)
4. **Variables** 에 추가
   | 이름 | 값 |
   |---|---|
   | `DISCORD_TOKEN` | 봇 토큰 |
   | `DISCORD_APPLICATION_ID` | Application ID |
   | `DG_ADMIN_USER_IDS` | 운영진 ID 2개, 쉼표 구분 |
   | `DG_ADMIN_ALERT_CHANNEL_ID` | (선택) 운영진 전용 채널 ID. 비우면 운영진에게 DM |
   | `TZ` | `Asia/Seoul` (로그 시각 표시용, 선택) |
5. **Deploy** → **Deployments → View Logs** 에서 아래 줄이 보이면 성공
   ```
   길드 명령어 10개 등록 (서버 1539519514956398692)
   로그인: 도근고등학교 달빛 방송부 ...
   ```
   `봇이 지정된 서버에 초대되어 있지 않습니다` 가 보이면 0-4 초대를 다시 확인하세요.

## 2. 켠 직후 할 일 (개막 시각이 이미 지났다면 필수)

개막(9/24 00:00)이 12시간 넘게 지난 뒤에 켜면, 봇은 대량 게시를 막기 위해 **개막 공지를 자동으로 올리지 않고 운영진에게 알림만** 보냅니다.

1. 이벤트 채널에서 `/운영 상태` → 상태·알림 확인
2. `/운영 예약` → 2화~12화 공개 시각이 비어 있으면 입력
   예) `/운영 예약 회차:2 일시:2026-09-25 12:00` (DB 에 저장되어 재배포해도 유지)
3. `/운영 시작` → 개막 공지 + 1화 게시
   - 영상 파일이 없으면 1화는 영상 없이 게시되며 안내 문구가 붙습니다. 영상 링크가 있다면 먼저 `bot/data/episodes.json` 의 `video_url` 에 넣고 푸시(자동 재배포)하세요.
4. 이미 시각이 지난 회차는 `/운영 공개 대상:회차 번호:2` 처럼 순서대로 수동 공개

## 3. 콘텐츠 수정 → 재배포

`bot/data/*.json`, `assets/`, `episodes/` 를 수정해 GitHub 에 푸시하면 Railway 가 자동으로 다시 빌드·배포합니다.
DB 는 볼륨(`/data`)에 있으므로 게시 이력과 참가자 진행도는 그대로 유지되고, 이미 올린 공지는 다시 올라가지 않습니다.
큰 영상 파일은 깃에 올리기보다 `video_url` 링크 사용을 권장합니다.

## 4. Fly.io 로 배포할 때 (대안)

```bash
cd dokeun-motion-webtoon
fly launch --no-deploy --copy-config        # 앱 이름이 바뀌면 fly.toml 의 app 값 확인
fly volumes create dalbit_data --region nrt --size 1
fly secrets set DISCORD_TOKEN=... DISCORD_APPLICATION_ID=... DG_ADMIN_USER_IDS=111,222
fly deploy
fly logs
```

## 5. 개인 서버(VPS)에 올릴 때

`README.md` 7절의 systemd 방식, 또는:

```bash
cd dokeun-motion-webtoon
docker build -t dalbit-bot .
docker run -d --name dalbit-bot --restart always -v dalbit-data:/data \
  -e DISCORD_TOKEN=... -e DISCORD_APPLICATION_ID=... -e DG_ADMIN_USER_IDS=111,222 dalbit-bot
docker logs -f dalbit-bot
```

## 문제 해결

| 증상 | 확인 |
|---|---|
| 로그에 `DISCORD_TOKEN 이 설정되지 않았습니다` | Variables 에 토큰 입력 후 재배포 |
| `Improper token` / 401 | 토큰을 다시 Reset 해서 교체 |
| 명령어가 안 보임 | 봇이 서버에 초대됐는지, 디스코드 앱을 재시작(Ctrl+R) |
| `/운영` 이 안 보임 | '서버 관리' 권한이 없으면 서버 설정 → 연동 → 달빛 방송부 → `/운영` 에서 운영진 허용 |
| 게시 실패 알림 (Forbidden) | 이벤트 채널에서 봇 역할 권한 확인 |
| 재배포 후 공지가 또 올라옴 | 볼륨이 `/data` 에 연결됐는지 확인 |
