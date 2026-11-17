#!/usr/bin/env python3
"""jhatpat-reel · motion_graphics

Talking-head reel ke upar tech-style motion graphics: terminal, clock, badi text
jo sir ke PEECHE se guzarti hai, device frames, captions, sound effects.
Sab kuch ek JSON file (graphics.json) se chalta hai - kaunsa beat, kab se kab tak.

  python motion_graphics.py take_cut.mp4 graphics.json
  python motion_graphics.py take_cut.mp4 graphics.json --stills 5,12,30   # pehle layout check karo
  python motion_graphics.py take_cut.mp4 graphics.json --range 20-30      # sirf ek hissa render

Output: <video>_graphics.mp4 (1080x1920, -14 LUFS) + <video>_markers.edl (Premiere markers).

Best results: phone on a tripod, plain wall behind you, you sitting still-ish.
The "behind the head" effect reads the wall colour; a busy background won't separate cleanly."""
import argparse, json, shutil, subprocess, sys
from pathlib import Path

try:
    import cv2
    import numpy as np
    from PIL import Image
except ImportError:
    sys.exit("Pehle install karo:  pip install -r requirements.txt   (numpy, opencv-python, pillow)")

sys.path.insert(0, str(Path(__file__).parent))
from mg.beats import Beats, W, H
from mg.fonts import resolve
from mg.mask import WallMask
from mg.sfx import build_audio


def need(tool):
    if shutil.which(tool) is None:
        sys.exit(f"'{tool}' nahi mila. ffmpeg install karo (Windows: winget install Gyan.FFmpeg).")


def fit_916(img):
    """Cover-crop any input to 1080x1920 so the graphics land where they were designed."""
    h, w = img.shape[:2]
    if (w, h) == (W, H):
        return img
    s = max(W / w, H / h)
    r = cv2.resize(img, (int(round(w * s)), int(round(h * s))), interpolation=cv2.INTER_AREA)
    y = (r.shape[0] - H) // 2; x = (r.shape[1] - W) // 2
    return r[y:y + H, x:x + W]


def zoom_frame(img, z, anchor):
    if abs(z - 1) < 1e-3:
        return img
    ax, ay = anchor
    M = np.array([[z, 0, ax * (1 - z)], [0, z, ay * (1 - z)]], np.float32)
    return cv2.warpAffine(img, M, (img.shape[1], img.shape[0]), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def composite(rgb, mask, back, front):
    out = rgb.astype(np.float32)
    b = np.asarray(back, np.float32); f = np.asarray(front, np.float32)
    ab = (b[..., 3:4] / 255) * (1 - mask[..., None])
    out = out * (1 - ab) + b[..., :3] * ab
    af = f[..., 3:4] / 255
    return (out * (1 - af) + f[..., :3] * af).clip(0, 255).astype(np.uint8)


def render(t, bgr, wm, bt):
    bgr = fit_916(bgr)
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    m = wm(bgr, (W, H)) if wm else np.zeros((H, W), np.float32)
    z = bt.zoom(t)
    rgb = zoom_frame(rgb, z, bt.anchor); m = zoom_frame(m, z, bt.anchor)
    back = Image.new("RGBA", (W, H), (0, 0, 0, 0)); front = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bt.draw(t, back, front, rgb)
    return composite(rgb, m, back, front)


def tc(sec, fps):
    f = int(round(sec * fps)); s, f = divmod(f, fps); m, s = divmod(s, 60); h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}:{f:02d}"


def write_edl(bt, dur, fps, name, path):
    L = ["TITLE: jhatpat-reel graphics markers", "FCM: NON-DROP FRAME", "",
         f"001  AX       V     C        {tc(0, fps)} {tc(dur, fps)} {tc(0, fps)} {tc(dur, fps)}",
         f"* FROM CLIP NAME: {name}"]
    for b in bt.beats:
        L.append(f"* LOC: {tc(b['start'], fps)} YELLOW  {b['type'].upper()}")
    for t, k in bt.cues:
        if k in ("whoosh", "bass", "glitch", "enter"):
            L.append(f"* LOC: {tc(t, fps)} CYAN    SFX {k}")
    Path(path).write_text("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser(description="jhatpat-reel motion graphics")
    ap.add_argument("video")
    ap.add_argument("graphics", help="graphics.json (examples/graphics.example.json se shuru karo)")
    ap.add_argument("--cuts", default=None, help="rough_cut ka cuts.json (THIS REEL timeline ke liye)")
    ap.add_argument("--stills", default=None, help="in seconds par JPG banao, jaise 5,12.5,30")
    ap.add_argument("--range", default=None, help="sirf itna render karo, jaise 20-30")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    need("ffmpeg")

    src = Path(a.video).expanduser().resolve()
    if not src.exists():
        sys.exit(f"Video nahi mili: {src}")
    cfg = json.loads(Path(a.graphics).expanduser().read_text(encoding="utf-8"))
    fonts = resolve(cfg.get("fonts"))

    cap = cv2.VideoCapture(str(src))
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = int(round(cap.get(cv2.CAP_PROP_FPS) or 30))
    dur = n / fps

    cuts_path = a.cuts or (src.parent / "cuts.json")
    cuts = []
    if Path(cuts_path).exists():
        cuts = [p["dur"] for p in json.loads(Path(cuts_path).read_text())["pieces"]]
        k = dur / max(1e-6, sum(cuts)); cuts = [c * k for c in cuts]
    bt = Beats(cfg, fonts, cuts); bt.total = dur

    m = cfg.get("mask", {})
    wm = None
    if m.get("enabled", True):
        samples = []
        for i in np.linspace(0, n - 1, 40).astype(int):
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(i)); ok, f = cap.read()
            if ok:
                samples.append(fit_916(f))
        wm = WallMask(samples, m.get("wall_top", 0.26), m.get("side", 0.07), m.get("threshold", 11.0))

    if a.stills:
        od = src.parent / f"{src.stem}_stills"; od.mkdir(exist_ok=True)
        for sec in [float(x) for x in a.stills.split(",")]:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(sec * fps)); ok, f = cap.read()
            if ok:
                Image.fromarray(render(sec, f, wm, bt)).save(od / f"t{sec:06.2f}.jpg", quality=88)
        print("stills ->", od); return

    t0, t1 = 0.0, dur
    if a.range:
        t0, t1 = [float(x) for x in a.range.split("-")]
    f0, f1 = int(t0 * fps), min(n, int(t1 * fps))

    out = Path(a.out).expanduser() if a.out else src.parent / f"{src.stem}_graphics.mp4"
    wav = out.with_suffix(".mix.wav"); tmp = out.with_suffix(".tmp.mp4")
    cues = [(t - t0, k) for t, k in bt.cues if t0 <= t < t1]
    seg = src
    if a.range:
        seg = out.with_suffix(".seg.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t0), "-to", str(t1), "-i", str(src),
                        "-vn", "-ac", "1", str(seg)], check=False)
    build_audio(seg, cues, t1 - t0, cfg.get("sfx_gain_db", -15), wav)

    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{W}x{H}", "-r", str(fps), "-i", "-", "-i", str(wav),
                            "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium",
                            "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                            "-shortest", str(tmp)], stdin=subprocess.PIPE)
    cap.set(cv2.CAP_PROP_POS_FRAMES, f0)
    for i in range(f0, f1):
        ok, f = cap.read()
        if not ok:
            break
        enc.stdin.write(render(i / fps, f, wm, bt).tobytes())
        if (i - f0) % 150 == 0:
            print(f"  frame {i - f0}/{f1 - f0}", flush=True)
    enc.stdin.close(); enc.wait()
    lu = cfg.get("loudness_lufs", -14)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp), "-c:v", "copy",
                    "-af", f"loudnorm=I={lu}:TP=-1.5:LRA=11", "-ar", "48000", "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart", str(out)], check=True)
    for p in (tmp, wav, out.with_suffix(".seg.wav")):
        p.unlink(missing_ok=True)
    edl = src.parent / f"{src.stem}_markers.edl"
    write_edl(bt, dur, fps, out.name, edl)
    print(f"bana  : {out}\nEDL   : {edl}")


if __name__ == "__main__":
    main()
