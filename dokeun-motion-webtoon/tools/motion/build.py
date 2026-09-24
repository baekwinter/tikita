import sys, os, glob, time
from PIL import Image
import numpy as np
from render import *

TITLES = {
    4: "네가 울던 날, 나는 거기 있었어", 5: "가장 수상한 사람", 6: "내가 좋아하는 애는 너니까",
    7: "내가 먼저 좋아했어", 8: "전송되지 않은 마음", 9: "두 번째 남자주인공",
    10: "가장 오래된 친구", 11: "누군가 써 내려간 결말",
}
OUT = "/home/user/tikita/dokeun-motion-webtoon/episodes"
PINK, WHITE, LAV = (255, 150, 200), (255, 255, 255), (200, 185, 240)


def end_card(ep):
    last = ep == 12
    return text_card([
        (f"EP.{ep:02d}  {TITLES.get(ep, '')}", 60, FONT_TITLE, LAV),
        ("당신은 이 사건의 진실을 찾았나요?" if last else "다음 화에서 계속", 120, FONT_HAND, PINK),
        ("도근고등학교 달빛 방송부", 44, FONT_TITLE, WHITE),
    ], 4.5)


def episode_shots(ep, per=6.5):
    banner = f"up/EP{ep:02d}_00.png"
    panels = sorted(glob.glob(f"up/EP{ep:02d}_0[1-9].png")) + sorted(glob.glob(f"up/EP{ep:02d}_1[0-9].png"))
    shots = [TitleShot(banner, 6.0, ep, TITLES.get(ep, "")), PanShot(banner, 6.5, x0=0.40, x1=0.80)]
    for i, p in enumerate(panels):
        shots.append(PanelShot(p, per, move=i))
    shots.append(end_card(ep))
    return shots


def thumb(ep, shot):
    f = shot.frame(4.0) * vignette()
    Image.fromarray(f.clip(0, 255).astype(np.uint8)).resize((1280, 720), Image.LANCZOS).save(f"{OUT}/EP{ep:02d}_thumb.jpg", quality=90)


if __name__ == "__main__":
    for ep in map(int, sys.argv[1:]):
        t = time.time()
        shots = episode_shots(ep)
        thumb(ep, shots[0])
        d = render(shots, f"{OUT}/EP{ep:02d}.mp4", seed=ep)
        print(f"EP{ep:02d} {d:.1f}s video, {os.path.getsize(f'{OUT}/EP{ep:02d}.mp4')/1e6:.1f}MB, took {time.time()-t:.0f}s", flush=True)
