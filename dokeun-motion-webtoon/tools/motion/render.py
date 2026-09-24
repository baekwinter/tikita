"""Motion-webtoon renderer: upscaled panels -> 1920x1080 mp4 with camera moves, petals, crossfades, music."""
import math, os, subprocess, sys, random, wave
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import imageio_ffmpeg

W, H, FPS = 1920, 1080, 30
FF = imageio_ffmpeg.get_ffmpeg_exe()
FONT_TITLE = "/home/user/fonts/NanumMyeongjo-Bold.ttf"
FONT_HAND = "/home/user/fonts/NanumPenScript-Regular.ttf"
XF = 0.7  # crossfade seconds


def load(path):
    return np.asarray(Image.open(path).convert("RGB"))


def cover(img, w, h):
    ih, iw = img.shape[:2]
    s = max(w / iw, h / ih)
    r = cv2.resize(img, (math.ceil(iw * s), math.ceil(ih * s)), interpolation=cv2.INTER_AREA)
    y, x = (r.shape[0] - h) // 2, (r.shape[1] - w) // 2
    return r[y:y + h, x:x + w]


def blurred_bg(img, dark=0.42):
    small = cover(img, W // 4, H // 4)
    small = cv2.GaussianBlur(small, (0, 0), 9)
    bg = cv2.resize(small, (W, H), interpolation=cv2.INTER_CUBIC).astype(np.float32)
    return bg * dark + np.array([18, 10, 30], np.float32) * (1 - dark) * 0.6


VIGNETTE = None


def vignette():
    global VIGNETTE
    if VIGNETTE is None:
        y, x = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2)
        VIGNETTE = (1 - 0.38 * np.clip(d - 0.55, 0, 1) ** 1.4)[..., None].astype(np.float32)
    return VIGNETTE


class PanelShot:
    """Panel framed over its own blurred backdrop, slow zoom + drift."""

    def __init__(self, path, dur, move=0, fit=0.93):
        img = load(path)
        self.dur = dur
        self.bg = blurred_bg(img)
        ih, iw = img.shape[:2]
        s = min(W * fit / iw, H * fit / ih)
        self.dw, self.dh = iw * s, ih * s
        self.src = cv2.resize(img, (round(self.dw * 1.07), round(self.dh * 1.07)), interpolation=cv2.INTER_AREA).astype(np.float32)
        self.move = move
        # soft shadow baked into bg
        sh = np.zeros((H, W), np.float32)
        x0, y0 = int((W - self.dw) / 2), int((H - self.dh) / 2)
        cv2.rectangle(sh, (x0 + 10, y0 + 18), (int(x0 + self.dw) + 10, int(y0 + self.dh) + 18), 1.0, -1)
        sh = cv2.GaussianBlur(sh, (0, 0), 22)[..., None]
        self.bg = self.bg * (1 - 0.6 * sh)
        self.mask = np.zeros((H, W), np.float32)
        cv2.rectangle(self.mask, (x0, y0), (int(x0 + self.dw) - 1, int(y0 + self.dh) - 1), 1.0, -1)
        self.mask = self.mask[..., None]

    def frame(self, t):
        p = t / self.dur
        e = 0.5 - 0.5 * math.cos(math.pi * p)
        z = 1.0 + 0.055 * e  # zoom inside the frame
        dx = [0, 1, -1, 0][self.move % 4] * 0.018 * (e - 0.5)
        dy = [0, 0, 0, 1][self.move % 4] * 0.018 * (e - 0.5)
        sh, sw = self.src.shape[:2]
        # map dst frame rect (dw x dh at center) to src with zoom z around center + drift
        k = self.dw * z / sw  # src is pre-scaled to 1.07x the framed size
        cx, cy = W / 2 + dx * self.dw, H / 2 + dy * self.dh + getattr(self, 'shift', 0)
        M = np.float32([[k, 0, cx - k * sw / 2], [0, k, cy - k * sh / 2]])
        fg = cv2.warpAffine(self.src, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        return self.bg * (1 - self.mask) + fg * self.mask


class PanShot:
    """Full-bleed pan across a wide image (e.g. the episode banner)."""

    def __init__(self, path, dur, x0=0.0, x1=1.0, zoom=1.0):
        img = load(path)
        ih, iw = img.shape[:2]
        s = H / ih * zoom
        self.src = cv2.resize(img, (round(iw * s), round(ih * s)), interpolation=cv2.INTER_AREA).astype(np.float32)
        self.dur, self.x0, self.x1 = dur, x0, x1

    def frame(self, t):
        e = 0.5 - 0.5 * math.cos(math.pi * t / self.dur)
        sw = self.src.shape[1]
        cx = (self.x0 + (self.x1 - self.x0) * e) * sw
        cx = min(max(cx, W / 2), sw - W / 2)
        top = (self.src.shape[0] - H) / 2
        M = np.float32([[1, 0, -(cx - W / 2)], [0, 1, -top]])
        return cv2.warpAffine(self.src, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def text_card(lines, dur, sub=None):
    """lines: [(text, size, font, color)] centered."""
    img = Image.new("RGB", (W, H), (10, 6, 20))
    g = np.zeros((H, W), np.float32)
    cv2.circle(g, (W // 2, H // 2), 520, 1.0, -1)
    g = cv2.GaussianBlur(g, (0, 0), 260)
    base = (np.array([10, 6, 20], np.float32) + g[..., None] * np.array([70, 30, 70], np.float32))
    img = Image.fromarray(base.clip(0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    fonts = [ImageFont.truetype(f, s) for _, s, f, _ in lines]
    hs = [d.textbbox((0, 0), t, font=fo)[3] - d.textbbox((0, 0), t, font=fo)[1] for (t, *_), fo in zip(lines, fonts)]
    gap = 34
    y = (H - (sum(hs) + gap * (len(lines) - 1))) / 2
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for (t, s, f, c), fo, h in zip(lines, fonts, hs):
        bb = d.textbbox((0, 0), t, font=fo)
        x = (W - (bb[2] - bb[0])) / 2 - bb[0]
        gd.text((x, y - bb[1]), t, font=fo, fill=(255, 90, 170) if c != (255, 255, 255) else (120, 90, 200))
        d.text((x, y - bb[1]), t, font=fo, fill=c)
        y += h + gap
    glow = glow.filter(ImageFilter.GaussianBlur(18))
    arr = np.asarray(img).astype(np.float32) + np.asarray(glow).astype(np.float32) * 0.8
    return StillShot(arr.clip(0, 255), dur)


class TitleShot(PanelShot):
    """Banner strip in the lower half, big episode title above it."""

    def __init__(self, path, dur, ep, title, sub="네 사람의 추억, 네 사람의 청춘"):
        super().__init__(path, dur, move=0, fit=0.96)
        # push the banner down: rebuild mask/bg offsets via a vertical shift
        self.shift = 150
        self.bg = blurred_bg(load(path), 0.38)
        x0, y0 = int((W - self.dw) / 2), int((H - self.dh) / 2) + self.shift
        sh = np.zeros((H, W), np.float32)
        cv2.rectangle(sh, (x0 + 10, y0 + 18), (int(x0 + self.dw) + 10, int(y0 + self.dh) + 18), 1.0, -1)
        self.bg = self.bg * (1 - 0.6 * cv2.GaussianBlur(sh, (0, 0), 22)[..., None])
        self.mask = np.zeros((H, W), np.float32)
        cv2.rectangle(self.mask, (x0, y0), (int(x0 + self.dw) - 1, int(y0 + self.dh) - 1), 1.0, -1)
        self.mask = self.mask[..., None]
        txt = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(txt)
        f1, f2, f3 = ImageFont.truetype(FONT_TITLE, 46), ImageFont.truetype(FONT_HAND, 138), ImageFont.truetype(FONT_HAND, 60)
        def c(t, f, y, fill):
            bb = d.textbbox((0, 0), t, font=f)
            d.text(((W - (bb[2] - bb[0])) / 2 - bb[0], y - bb[1]), t, font=f, fill=fill)
        c(f"도근고등학교 달빛 방송부  ·  EP.{ep:02d}", f1, 150, (215, 200, 245, 255))
        c(title, f2, 225, (255, 170, 215, 255))
        c(sub, f3, 400, (255, 255, 255, 235))
        glow = txt.filter(ImageFilter.GaussianBlur(16))
        ga = np.asarray(glow).astype(np.float32)
        ta = np.asarray(txt).astype(np.float32)
        self.glow = (ga[..., :3] * np.array([1.0, 0.45, 0.8]), ga[..., 3:] / 255 * 0.9)
        self.txt = (ta[..., :3], ta[..., 3:] / 255)

    def frame(self, t):
        out = super().frame(t)
        a = min(1.0, max(0.0, (t - 0.4) / 1.0))
        g, ga = self.glow
        out = out + g * ga * a
        tc, ta = self.txt
        return out * (1 - ta * a) + tc * ta * a


class StillShot:
    def __init__(self, arr, dur):
        self.arr, self.dur = arr.astype(np.float32), dur

    def frame(self, t):
        e = t / self.dur
        z = 1.0 + 0.03 * e
        M = cv2.getRotationMatrix2D((W / 2, H / 2), 0, z)
        return cv2.warpAffine(self.arr, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


class Petals:
    def __init__(self, n=34, seed=7):
        rnd = random.Random(seed)
        self.sprites = []
        for i in range(6):
            s = 64
            a = np.zeros((s, s), np.float32)
            cv2.ellipse(a, (s // 2, s // 2), (s // 2 - 6, s // 4 - 2 + i % 3 * 2), 0, 0, 360, 1.0, -1)
            cv2.circle(a, (s // 2 + s // 3, s // 2), s // 7, 0.0, -1)  # notch
            a = cv2.GaussianBlur(a, (0, 0), 1.2 + (i % 2) * 1.5)
            self.sprites.append(a)
        self.p = [dict(x=rnd.uniform(0, W), y=rnd.uniform(-H, H), vx=rnd.uniform(-60, -15), vy=rnd.uniform(45, 110),
                       sz=rnd.uniform(0.25, 0.8), rot=rnd.uniform(0, 360), vr=rnd.uniform(-90, 90),
                       ph=rnd.uniform(0, 6.28), sp=rnd.randrange(6), a=rnd.uniform(0.35, 0.8)) for _ in range(n)]
        self.color = np.array([255, 190, 222], np.float32)

    def apply(self, frame, t):
        for q in self.p:
            y = (q["y"] + q["vy"] * t) % (H + 200) - 100
            x = (q["x"] + q["vx"] * t + 40 * math.sin(q["ph"] + t * 1.3)) % (W + 200) - 100
            spr = self.sprites[q["sp"]]
            s = max(8, int(64 * q["sz"]))
            M = cv2.getRotationMatrix2D((32, 32), q["rot"] + q["vr"] * t, s / 64)
            M[0, 2] += s / 2 - 32
            M[1, 2] += s / 2 - 32
            flip = abs(math.cos(q["ph"] + t * 2.1))
            a = cv2.warpAffine(spr, M, (s, s)) * q["a"]
            if flip < 0.3:
                a = cv2.resize(a, (s, max(2, int(s * (0.3 + flip)))))
            h_, w_ = a.shape
            x0, y0 = int(x - w_ / 2), int(y - h_ / 2)
            xa, ya, xb, yb = max(x0, 0), max(y0, 0), min(x0 + w_, W), min(y0 + h_, H)
            if xa >= xb or ya >= yb:
                continue
            al = a[ya - y0:yb - y0, xa - x0:xb - x0, None]
            reg = frame[ya:yb, xa:xb]
            frame[ya:yb, xa:xb] = reg * (1 - al) + self.color * al
        return frame


def music(total, path, seed=1, bpm=66):
    """Soft pad + music-box arpeggio, deterministic."""
    sr = 44100
    n = int(total * sr) + sr
    t = np.arange(n) / sr
    out = np.zeros((n, 2), np.float32)
    beat = 60 / bpm
    bar = beat * 4
    # Am  F  C  G  (i - VI - III - VII)  in Hz roots
    prog = [[57, 60, 64, 69], [53, 57, 60, 65], [48, 55, 60, 64], [55, 59, 62, 67]]
    hz = lambda m: 440 * 2 ** ((m - 69) / 12)
    nb = int(total / bar) + 2
    rnd = random.Random(seed)
    for b in range(nb):
        ch = prog[b % 4]
        s0, s1 = int(b * bar * sr), int((b + 1) * bar * sr + 1.5 * sr)
        s1 = min(s1, n)
        tt = np.arange(s1 - s0) / sr
        env = np.minimum(tt / 1.2, 1) * np.exp(-np.maximum(tt - bar, 0) / 0.6)
        for i, m in enumerate(ch):
            f = hz(m - 12)
            v = (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * f * 2.003 * tt) + 0.12 * np.sin(2 * np.pi * f * 3.01 * tt))
            pan = 0.35 + 0.1 * i
            out[s0:s1, 0] += (v * env * 0.045 * (1 - pan)).astype(np.float32)
            out[s0:s1, 1] += (v * env * 0.045 * pan).astype(np.float32)
        # music box: 8 eighth notes arpeggio
        pat = [0, 2, 1, 3, 2, 1, 3, 2]
        for k in range(8):
            if rnd.random() < 0.18:
                continue
            m = ch[pat[k]] + 12 + (12 if k in (3, 6) and rnd.random() < 0.5 else 0)
            st = int((b * bar + k * beat / 2) * sr)
            ln = min(int(2.2 * sr), n - st)
            if ln <= 0:
                continue
            tt = np.arange(ln) / sr
            f = hz(m)
            v = (np.sin(2 * np.pi * f * tt) + 0.25 * np.sin(2 * np.pi * f * 4.02 * tt) * np.exp(-tt * 9)) * np.exp(-tt * 2.6) * np.minimum(tt / 0.004, 1)
            pan = rnd.uniform(0.3, 0.7)
            out[st:st + ln, 0] += (v * 0.07 * (1 - pan)).astype(np.float32)
            out[st:st + ln, 1] += (v * 0.07 * pan).astype(np.float32)
    # simple reverb: multi-tap feedback delays
    for d, g in [(0.113, 0.32), (0.187, 0.26), (0.271, 0.2), (0.419, 0.14)]:
        k = int(d * sr)
        wet = np.zeros_like(out)
        wet[k:] = out[:-k] * g
        out[:, ::-1] += wet * 0.9
    out = out[: int(total * sr)]
    fade = np.ones(len(out), np.float32)
    fi, fo = int(1.5 * sr), int(3.0 * sr)
    fade[:fi] = np.linspace(0, 1, fi)
    fade[-fo:] = np.linspace(1, 0, fo)
    out *= fade[:, None]
    out /= max(1e-6, np.abs(out).max()) / 0.6
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((out * 32767).astype(np.int16).tobytes())


def render(shots, out_path, seed=1, max_mb=9.5, petals=True, bpm=66):
    starts, t = [], 0.0
    for i, s in enumerate(shots):
        starts.append(t)
        t += s.dur - (XF if i < len(shots) - 1 else 0)
    total = t
    wav = out_path + ".wav"
    music(total, wav, seed=seed, bpm=bpm)
    pet = Petals(seed=seed) if petals else None
    vig = vignette()
    tmp = out_path + ".tmp.mp4"
    nfr = int(total * FPS)
    # target bitrate so file stays under max_mb (Discord upload limit)
    abr = 128_000
    vbr = int(max_mb * 8 * 1024 * 1024 / total - abr)
    vbr = min(vbr, 8_000_000)
    cmd = [FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", wav, "-c:v", "libx264", "-preset", "slow", "-tune", "animation", "-crf", "19",
           "-maxrate", str(vbr), "-bufsize", str(vbr * 2), "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
           "-movflags", "+faststart", "-shortest", tmp]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for fi in range(nfr):
        tt = fi / FPS
        act = [i for i, st in enumerate(starts) if st <= tt < st + shots[i].dur]
        frame = None
        for i in act:
            lt = tt - starts[i]
            f = shots[i].frame(lt)
            a = 1.0
            if i > 0 and lt < XF:
                a = lt / XF
            if frame is None:
                frame = f
            else:
                frame = frame * (1 - a) + f * a
        if tt < 0.8:
            frame = frame * (tt / 0.8)
        if tt > total - 1.2:
            frame = frame * max(0, (total - tt) / 1.2)
        if pet is not None:
            frame = pet.apply(frame, tt)
        frame = frame * vig
        p.stdin.write(frame.clip(0, 255).astype(np.uint8).tobytes())
    p.stdin.close()
    p.wait()
    os.replace(tmp, out_path)
    os.remove(wav)
    return total
