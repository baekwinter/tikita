import sys, time, torch, numpy as np, glob, os
from PIL import Image
from spandrel import ModelLoader
torch.set_num_threads(4)
m = ModelLoader().load_from_file("/home/user/models/x4plus.pth").eval()
os.makedirs("up", exist_ok=True)
files = sys.argv[1:] or sorted(glob.glob("crops/*.png"))
TILE=256; PAD=16
for f in files:
    out=f"up/{os.path.basename(f)}"
    if os.path.exists(out): continue
    t=time.time()
    a=np.asarray(Image.open(f).convert("RGB")).astype(np.float32)/255
    x=torch.from_numpy(a).permute(2,0,1)[None]
    _,_,H,W=x.shape; S=4
    y=torch.zeros(1,3,H*S,W*S)
    with torch.inference_mode():
        for ty in range(0,H,TILE):
            for tx in range(0,W,TILE):
                y0,x0=max(ty-PAD,0),max(tx-PAD,0); y1,x1=min(ty+TILE+PAD,H),min(tx+TILE+PAD,W)
                o=m(x[:,:,y0:y1,x0:x1]).clamp(0,1)
                ey,ex=min(ty+TILE,H),min(tx+TILE,W)
                y[:,:,ty*S:ey*S,tx*S:ex*S]=o[:,:,(ty-y0)*S:(ey-y0)*S,(tx-x0)*S:(ex-x0)*S]
    ai=Image.fromarray((y[0].permute(1,2,0).numpy()*255+0.5).astype(np.uint8)); lz=Image.open(f).convert("RGB").resize(ai.size,Image.LANCZOS); Image.blend(lz,ai,0.85).save(out)
    print(out, W,H,"->",W*S,H*S, f"{time.time()-t:.1f}s", flush=True)
