#!/usr/bin/env python3
"""jhatpat-reel · reframe

Ek hi cut ko Instagram Reel (9:16), YouTube Shorts (9:16) aur
main YouTube (16:9) ke liye alag-alag frame me nikaalta hai.

Do tareeke:
  crop - asli pixels kaat kar bharta hai. Talking head ke liye best.
  pad  - poora frame rakh kar peeche blur bhar deta hai. Screen recording ke liye.

Usage:
  python3 reframe.py cut.mp4 --to 9:16
  python3 reframe.py cut.mp4 --to 9:16 --anchor 0.35      # chehra baayein hai
  python3 reframe.py cut.mp4 --to 16:9 --mode pad
  python3 reframe.py cut.mp4 --all
"""
import argparse, json, shutil, subprocess, sys
from pathlib import Path

RATIOS = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080), "4:5": (1080, 1350)}


def need(tool):
    if shutil.which(tool) is None:
        sys.exit(f"'{tool}' nahi mila. ffmpeg install karo.")


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                          "-show_entries", "stream=width,height", "-of", "json", str(path)],
                         capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"ffprobe fail: {out.stderr.strip()}")
    s = json.loads(out.stdout)["streams"][0]
    return s["width"], s["height"]


def build_filter(sw, sh, tw, th, mode, anchor):
    src_ar, tgt_ar = sw / sh, tw / th
    if mode == "crop":
        if src_ar > tgt_ar:                      # source zyada chaura - side kaato
            nh, nw = sh, int(round(sh * tgt_ar))
            maxx = sw - nw
            x = int(round(maxx * min(max(anchor, 0.0), 1.0)))
            y = 0
        else:                                    # source zyada lamba - upar-neeche kaato
            nw, nh = sw, int(round(sw / tgt_ar))
            maxy = sh - nh
            # talking head me chehra upar hota hai, isliye default 0.35 upar ki taraf
            y = int(round(maxy * min(max(anchor, 0.0), 1.0)))
            x = 0
        nw -= nw % 2; nh -= nh % 2
        return f"crop={nw}:{nh}:{x}:{y},scale={tw}:{th}:flags=lanczos"
    # pad: blurred background + poora frame beech me
    return (f"[0:v]scale={tw}:{th}:force_original_aspect_ratio=increase,"
            f"crop={tw}:{th},boxblur=28:2,eq=brightness=-0.08[bg];"
            f"[0:v]scale={tw}:{th}:force_original_aspect_ratio=decrease[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2")


def run(src, ratio, mode, anchor, out_dir, crf):
    tw, th = RATIOS[ratio]
    sw, sh = probe(src)
    f = build_filter(sw, sh, tw, th, mode, anchor)
    tag = ratio.replace(":", "x")
    out = out_dir / f"{src.stem}_{tag}.mp4"
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(src)]
    cmd += (["-filter_complex", f] if mode == "pad" else ["-vf", f])
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True)
    print(f"  {ratio:>5}  {mode:<4}  ->  {out.name}   ({tw}x{th})")
    return out


def main():
    ap = argparse.ArgumentParser(description="jhatpat-reel reframe")
    ap.add_argument("video")
    ap.add_argument("--to", default="9:16", choices=sorted(RATIOS))
    ap.add_argument("--mode", default="crop", choices=["crop", "pad"])
    ap.add_argument("--anchor", type=float, default=0.35,
                    help="0 = bilkul upar/baayein, 1 = neeche/daayein (default 0.35)")
    ap.add_argument("--all", action="store_true", help="9:16, 1:1 aur 16:9 teeno banao")
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--crf", type=int, default=20)
    a = ap.parse_args()

    need("ffmpeg")
    src = Path(a.video).expanduser().resolve()
    if not src.exists():
        sys.exit(f"File nahi mili: {src}")
    out_dir = Path(a.out_dir).expanduser() if a.out_dir else src.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"source: {src.name}  {probe(src)[0]}x{probe(src)[1]}")
    if a.all:
        for r, m in [("9:16", "crop"), ("1:1", "crop"), ("16:9", a.mode)]:
            run(src, r, m, a.anchor, out_dir, a.crf)
    else:
        run(src, a.to, a.mode, a.anchor, out_dir, a.crf)


if __name__ == "__main__":
    main()
