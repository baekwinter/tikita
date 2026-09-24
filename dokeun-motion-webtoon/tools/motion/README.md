# 모션 웹툰 영상 파이프라인

회차 스토리보드 시트(상단 배너 + 8컷) → 컷 분리 → AI 업스케일(4배) → 1920×1080 모션 영상.

```
source/storyboards/EPxx.webp        원본 시트 (1672×941)
        │  panels.py   : 시트별 컷 좌표 (배너=00, 컷=01~08)
        ▼
crops/EPxx_NN.png                   잘라낸 컷
        │  upscale.py  : Real-ESRGAN x4plus 4배 (원본 15% 블렌드로 선 왜곡 억제)
        ▼
up/EPxx_NN.png                      → assets/scenes/EPxx/NN.jpg 로 보관
        │  build.py    : 타이틀 → 배너 패닝 → 컷 8개(줌·드리프트) → 엔딩 카드
        │  render.py   : 벚꽃 파티클, 크로스페이드, 비네팅, 자체 합성 BGM, x264
        ▼
episodes/EPxx.mp4, EPxx_thumb.jpg   (디스코드 업로드 한도 10MB 이하로 비트레이트 자동 조정)
episodes/TRAILER.mp4                trailer.py
```

## 준비

```bash
pip install pillow numpy opencv-python-headless imageio-ffmpeg torch spandrel
# 모델: https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth → /home/user/models/x4plus.pth
# 폰트: Google Fonts NanumMyeongjo-Bold, NanumPenScript-Regular → /home/user/fonts/
```

## 새 회차 추가

1. 시트를 `source/storyboards/EPxx.webp` 로 저장하고 작업 폴더에 복사.
2. `panels.py` 의 `SHEETS` 에 배너 하단 y 와 컷 좌표를 추가 (흰 구분선 기준).
3. 컷 분리 후 `python upscale.py` → `python build.py <회차번호>` → `python trailer.py`.
