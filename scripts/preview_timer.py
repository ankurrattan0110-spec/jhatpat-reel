#!/usr/bin/env python3
"""jhatpat-reel · preview_timer

Video par bada timer (aur rough_cut ke piece number) chipka deta hai, taaki dekh kar
bata sako "ye line 27.6 se 28.9 tak hai". graphics.json ki timing bharne ke liye bhi yahi.

  python preview_timer.py take_cut.mp4
  python preview_timer.py take_cut.mp4 --cuts jhatpat/cuts.json
"""
import argparse, json, shutil, subprocess, sys, tempfile
from pathlib import Path


def find_font():
    for p in [r"C:\Windows\Fonts\consolab.ttf", r"C:\Windows\Fonts\arialbd.ttf",
              "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"]:
        if Path(p).exists():
            return p
    return None


def esc(p):
    # ffmpeg filter paths: forward slashes, escape the drive colon
    return str(p).replace("\\", "/").replace(":", "\\:")


def main():
    ap = argparse.ArgumentParser(description="jhatpat-reel preview timer")
    ap.add_argument("video")
    ap.add_argument("--cuts", default=None, help="cuts.json - piece number bhi dikhega")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    if shutil.which("ffmpeg") is None:
        sys.exit("ffmpeg nahi mila.")
    src = Path(a.video).expanduser().resolve()
    if not src.exists():
        sys.exit(f"Video nahi mili: {src}")
    font = find_font()
    ff = f"fontfile='{esc(font)}':" if font else ""
    parts = []
    cuts = Path(a.cuts) if a.cuts else src.parent / "cuts.json"
    if cuts.exists():
        t = 0.0
        for i, p in enumerate(json.loads(cuts.read_text())["pieces"], 1):
            a0, b0 = t, t + p["dur"]; t = b0
            parts.append(f"drawtext={ff}text='PIECE {i}':fontcolor=yellow:fontsize=h/28:x=(w-text_w)/2:"
                         f"y=h*0.17:box=1:boxcolor=black@0.6:boxborderw=14:enable='between(t,{a0:.3f},{b0:.3f})'")
    parts.append(f"drawtext={ff}text='%{{pts\\:hms}}':fontcolor=white:fontsize=h/20:x=(w-text_w)/2:"
                 f"y=h*0.08:box=1:boxcolor=black@0.7:boxborderw=16")
    parts.append("scale=720:-2")
    out = Path(a.out) if a.out else src.parent / f"{src.stem}_timer.mp4"
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as fh:
        fh.write(",".join(parts)); script = fh.name
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-filter_script:v", script,
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
                        "-c:a", "aac", "-b:a", "96k", str(out)], capture_output=True, text=True)
    Path(script).unlink(missing_ok=True)
    if r.returncode != 0:
        sys.exit("Timer banane me dikkat:\n" + r.stderr[-600:])
    print(f"bana: {out}\nIse chala kar dekho - jis line ko hatana ho uska start/end timer se note karo.")


if __name__ == "__main__":
    main()
