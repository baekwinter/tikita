"""Keyframe video upscaler.

Frames are mostly stills with slow camera moves. Instead of running the AI model on every
frame we upscale a keyframe, keep its *detail layer* D = AI(K) - K, and for following frames
add D warped by the tracked affine motion (ECC) to the original frame. When the residual
between the warped keyframe and the current frame gets structured (new image, subtitle,
misalignment), the current frame becomes the next keyframe.
"""
import sys, time, subprocess, os
import numpy as np, cv2, torch
from spandrel import ModelLoader
import imageio_ffmpeg

FF = imageio_ffmpeg.get_ffmpeg_exe()
W, H = 1920, 1080
LW, LH = 480, 270
torch.set_num_threads(4)
MODEL = ModelLoader().load_from_file("/home/user/models/animevideov3.pth").eval()


def ai(frame):
    x = cv2.resize(frame, (960, 540), interpolation=cv2.INTER_AREA)
    t = torch.from_numpy(x.astype(np.float32) / 255).permute(2, 0, 1)[None]
    with torch.inference_mode():
        y = MODEL(t).clamp(0, 1)[0].permute(1, 2, 0).numpy() * 255
    return cv2.resize(y, (W, H), interpolation=cv2.INTER_AREA)


def gray_small(f):
    return cv2.cvtColor(cv2.resize(f, (LW, LH), interpolation=cv2.INTER_AREA), cv2.COLOR_RGB2GRAY).astype(np.float32)


def detail_mask(g):
    h = np.abs(g - cv2.GaussianBlur(g, (0, 0), 2))
    m = (cv2.GaussianBlur(h, (0, 0), 3) > 2.0).astype(np.uint8)
    m = cv2.dilate(m, np.ones((9, 9), np.uint8))
    return m if m.mean() > 0.05 else np.ones_like(m)


def hf_err(a, b, m=None):
    r = a - b
    r = r - cv2.GaussianBlur(r, (0, 0), 3)  # ignore brightness / fade changes
    r = np.abs(cv2.GaussianBlur(r, (0, 0), 1.0))
    if m is not None:
        r = r[m > 0]
    return float(np.percentile(r, 99.5))


def probe(path):
    out = subprocess.run([FF, "-i", path], capture_output=True, text=True).stderr
    import re
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", out)
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])


def run(src, dst, limit_s=None, max_mb=9.5, thr=4.0, strength=1.0):
    dur = probe(src) if limit_s is None else limit_s
    dec = [FF, "-loglevel", "error", "-i", src]
    if limit_s:
        dec += ["-t", str(limit_s)]
    dec += ["-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    dp = subprocess.Popen(dec, stdout=subprocess.PIPE, bufsize=W * H * 3 * 4)
    abr = 160_000
    vbr = min(int(max_mb * 8 * 1024 * 1024 / dur - abr), 6_000_000)
    tmp = dst + ".tmp.mp4"
    enc = [FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", "24", "-i", "-",
           "-i", src, "-map", "0:v", "-map", "1:a?", "-c:v", "libx264", "-preset", "slow", "-tune", "animation",
           "-b:v", str(vbr), "-maxrate", str(int(vbr * 1.5)), "-bufsize", str(vbr * 2),
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", "-shortest", tmp]
    if limit_s:
        enc[-1:-1] = ["-t", str(limit_s)]
    ep = subprocess.Popen(enc, stdin=subprocess.PIPE)
    n = keys = 0
    K = D = Ks = Km = None
    A = np.eye(2, 3, dtype=np.float32)
    crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 40, 1e-4)
    t0 = time.time()
    while True:
        buf = dp.stdout.read(W * H * 3)
        if len(buf) < W * H * 3:
            break
        F = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
        Fs = gray_small(F)
        use_key = K is None
        if not use_key:
            try:
                _, A2 = cv2.findTransformECC(Ks, Fs, A.copy(), cv2.MOTION_AFFINE, crit, Km, 1)
                Kw = cv2.warpAffine(Ks, A2, (LW, LH), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
                if hf_err(Kw, Fs, Km) > thr:
                    use_key = True
                else:
                    A = A2
            except cv2.error:
                use_key = True
        if use_key:
            K = F
            Ks = Fs
            Km = detail_mask(Fs)
            D = (ai(F) - F.astype(np.float32)) * strength
            A = np.eye(2, 3, dtype=np.float32)
            out = F.astype(np.float32) + D
            keys += 1
        else:
            Ab = A.copy()
            Ab[:, 2] *= W / LW  # translation to full res
            Dw = cv2.warpAffine(D, Ab, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            out = F.astype(np.float32) + Dw
        ep.stdin.write(out.clip(0, 255).astype(np.uint8).tobytes())
        n += 1
        if n % 240 == 0:
            print(f"  {os.path.basename(src)} {n/24:.0f}s  keys={keys} ({keys/n:.0%})  {time.time()-t0:.0f}s", flush=True)
    ep.stdin.close(); ep.wait(); dp.wait()
    os.replace(tmp, dst)
    print(f"{dst}: frames={n} keys={keys} ({keys/max(n,1):.0%}) {os.path.getsize(dst)/1e6:.1f}MB {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    lim = float(sys.argv[3]) if len(sys.argv) > 3 else None
    run(src, dst, lim)
