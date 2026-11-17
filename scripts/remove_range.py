#!/usr/bin/env python3
"""jhatpat-reel · remove_range

Video se ek ya zyada hisse kaat do - jaise koi galat line, retake ya "umm".
Times preview_timer.py wali video se lo.

  python remove_range.py take_cut.mp4 27.6-28.9
  python remove_range.py take_cut.mp4 12.0-13.4 27.6-28.9
  python remove_range.py take_cut.mp4 27.6-28.9 --no-snap

--snap (default on): tumhare diye time ko paas ke pause ke beech me khiska deta hai,
taaki koi shabd aadha na kate aur jod par chhota natural pause bacha rahe.
Original file kabhi nahi badalti - nayi file <name>_trimmed.mp4 banti hai.
"""
import argparse, re, shutil, subprocess, sys
from pathlib import Path


def silences(src, db=-32, d=0.06):
    p = subprocess.run(["ffmpeg", "-v", "info", "-i", str(src), "-af", f"silencedetect=noise={db}dB:d={d}",
                        "-f", "null", "-"], capture_output=True, text=True)
    st, out = [], []
    for line in p.stderr.splitlines():
        m = re.search(r"silence_start: (-?[\d.]+)", line)
        if m:
            st.append(max(0.0, float(m.group(1))))
        m = re.search(r"silence_end: ([\d.]+)", line)
        if m and st:
            out.append((st.pop(), float(m.group(1))))
    return out


def snap(t, gaps, reach=0.45, side="start"):
    """Move an edge into the nearest pause. Leave ~0.1s of that pause on the kept side."""
    best = None
    for a, b in gaps:
        if a - reach <= t <= b + reach:
            mid = (a + b) / 2
            cand = min(b, a + 0.10) if side == "start" else max(a, b - 0.10)
            if b - a < 0.22:
                cand = mid
            if best is None or abs(cand - t) < abs(best - t):
                best = cand
    return best if best is not None else t


def probe_dur(src):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(src)],
                       capture_output=True, text=True)
    return float(r.stdout.strip())


def main():
    ap = argparse.ArgumentParser(description="jhatpat-reel remove range")
    ap.add_argument("video")
    ap.add_argument("ranges", nargs="+", help="start-end seconds, jaise 27.6-28.9")
    ap.add_argument("--no-snap", action="store_true")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    if shutil.which("ffmpeg") is None:
        sys.exit("ffmpeg nahi mila.")
    src = Path(a.video).expanduser().resolve()
    if not src.exists():
        sys.exit(f"Video nahi mili: {src}")
    dur = probe_dur(src)
    rm = []
    for r in a.ranges:
        try:
            s, e = [float(x) for x in r.split("-")]
        except ValueError:
            sys.exit(f"Range aise do: 27.6-28.9  (mila: {r})")
        if not 0 <= s < e <= dur + 0.01:
            sys.exit(f"Range video ke bahar hai: {r} (video {dur:.2f}s ki hai)")
        rm.append([s, e])
    if not a.no_snap:
        gaps = silences(src)
        for r in rm:
            r[0], r[1] = snap(r[0], gaps, side="start"), snap(r[1], gaps, side="end")
    rm.sort()
    keep, t = [], 0.0
    for s, e in rm:
        if s > t:
            keep.append((t, s))
        t = max(t, e)
    if t < dur:
        keep.append((t, dur))
    fc, labels = [], ""
    for i, (s, e) in enumerate(keep):
        fc.append(f"[0:v]trim={s:.3f}:{e:.3f},setpts=PTS-STARTPTS[v{i}];"
                  f"[0:a]atrim={s:.3f}:{e:.3f},asetpts=PTS-STARTPTS[a{i}]")
        labels += f"[v{i}][a{i}]"
    fc.append(f"{labels}concat=n={len(keep)}:v=1:a=1[v][a]")
    out = Path(a.out) if a.out else src.parent / f"{src.stem}_trimmed.mp4"
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-filter_complex", ";".join(fc),
                        "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("Kaatne me dikkat:\n" + r.stderr[-600:])
    gone = sum(e - s for s, e in rm)
    for s, e in rm:
        print(f"hataya: {s:.2f} - {e:.2f}  ({e - s:.2f}s)")
    print(f"{dur:.2f}s -> {dur - gone:.2f}s\nbana  : {out}")


if __name__ == "__main__":
    main()
