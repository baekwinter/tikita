# 도근고등학교 달빛 방송부 — 디스코드 봇 컨테이너
# Railway / Fly.io / 개인 서버 공용. 비밀 값은 이미지에 넣지 않고 플랫폼 환경 변수로 주입한다.
ARG BASE_IMAGE=python:3.11-slim
FROM ${BASE_IMAGE}

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    # 게시 이력·진행도 DB 는 반드시 영구 볼륨(/data)에 둔다. 재배포해도 중복 게시가 생기지 않는다.
    DG_DB_PATH=/data/dalbit.db

WORKDIR /app
COPY bot/requirements.txt bot/requirements.txt
RUN pip install -r bot/requirements.txt

COPY bot/ bot/
# 포스터·증거 이미지·회차 영상/썸네일 (없으면 봇이 누락으로 표시하고 공개를 보류)
COPY assets/ assets/
COPY episodes/ episodes/

# 플랫폼 볼륨은 root 소유로 마운트되는 경우가 많아 root 로 실행한다 (컨테이너 격리 안에서만 동작).
RUN mkdir -p /data
CMD ["python", "-m", "bot.main"]
