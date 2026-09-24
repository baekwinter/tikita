import os
from build import *

def P(ep, n, dur=3.2, move=0):
    return PanelShot(f"up/EP{ep:02d}_{n:02d}.png", dur, move=move)

def T(*lines, dur=2.6):
    return text_card([(t, s, FONT_HAND if s >= 80 else FONT_TITLE, c) for t, s, c in lines], dur)

def available(ep, n):
    return os.path.exists(f"up/EP{ep:02d}_{n:02d}.png")

plan = [
    T(("그날 밤, 방송실에서", 96, WHITE)),
    ("P", 7, 1), ("P", 7, 3), ("P", 7, 5),
    T(("누군가의 고백이", 96, WHITE), ("잘못 송출되었다", 110, PINK)),
    ("P", 7, 8), ("P", 8, 2), ("P", 4, 2), ("P", 4, 4),
    T(("편집한 사람과, 올린 사람은", 88, WHITE), ("달랐다", 110, PINK)),
    ("P", 5, 1), ("P", 5, 2), ("P", 6, 3), ("P", 5, 7), ("P", 8, 5),
    T(("네 사람의 추억,", 96, WHITE), ("네 사람의 청춘", 110, PINK)),
    ("P", 4, 5), ("P", 6, 4), ("P", 8, 7), ("P", 4, 8),
]
shots = []
for i, x in enumerate(plan):
    if isinstance(x, tuple):
        _, ep, n = x
        if available(ep, n):
            shots.append(P(ep, n, move=i))
    else:
        shots.append(x)
shots.append(PanShot("up/EP06_00.png", 5.0, x0=0.30, x1=0.75))
shots.append(text_card([
    ("도근고등학교 달빛 방송부", 52, FONT_TITLE, LAV),
    ("고백이 잘못 송출되었습니다", 130, FONT_HAND, PINK),
    ("YES/NO 추리 이벤트  ·  도근도근 디스코드", 44, FONT_TITLE, WHITE),
], 6.0))
d = render(shots, f"{OUT}/TRAILER.mp4", seed=99, bpm=74)
thumb_img = shots[-1].frame(3.0) * vignette()
Image.fromarray(thumb_img.clip(0, 255).astype(np.uint8)).resize((1280, 720), Image.LANCZOS).save(f"{OUT}/TRAILER_thumb.jpg", quality=90)
print(f"TRAILER {d:.1f}s {os.path.getsize(f'{OUT}/TRAILER.mp4')/1e6:.1f}MB")
