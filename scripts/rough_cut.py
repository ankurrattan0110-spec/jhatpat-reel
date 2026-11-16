#!/usr/bin/env python3
"""jhatpat-reel · rough_cut

Raw talking-head take se silence, dead air aur lambe pauses nikaal kar
ek tight cut banata hai. Teen cheezein deta hai:

  1. cuts.json   - har kept piece ka in/out, frame-exact
  2. <name>_cut.mp4 - chala hua cut, dekhne ke liye
  3. <name>.edl  - Premiere Pro / Resolve me import karne ke liye

Kuch bhi original file par nahi likhta. Raw footage read-only.

Usage:
  python3 rough_cut.py take.mp4
  python3 rough_cut.py take.mp4 --preset calm --no-render
  python3 rough_cut.py take.mp4 --config my.json
"""
import argparse, json, re, shutil, subprocess, sys
from pathlib import Path

# Hinglish bolne me English se thoda lamba pause aata hai - defaults usi hisaab se.
PRESETS = {
    "reel":  dict(silence_db=-38, silence_min=0.22, pre_pad=0.10, post_pad=0.14,
                  max_pause=0.42, pause_keep=0.22, scene_lead_in=0.35, scene_tail=0.45,
                  min_piece=0.45),
    "calm":  dict(silence_db=-40, silence_min=0.30, pre_pad=0.12, post_pad=0.20,
                  max_pause=0.80, pause_keep=0.45, scene_lead_in=0.60, scene_tail=0.80,
                  min_piece=0.60),
    "tight": dict(silence_db=-36, silence_min=0.18, pre_pad=0.06, post_pad=0.10,
                  max_pause=0.28, pause_keep=0.14, scene_lead_in=0.25, scene_tail=0.35,
                  min_piece=0.35),
}


def need(tool):
    if shutil.which(tool) is None:
        sys.exit(f"'{tool}' nahi mila. Install karo: brew install ffmpeg (Mac) / "
                 f"choco install ffmpeg (Windows)")


def probe(path):
    need("ffprobe")
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=r_frame_rate,width,height",
         "-show_entries", "format=duration", "-of", "json", str(path)],
        capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"ffprobe fail hua: {path}\n{out.stderr.strip()}")
    d = json.loads(out.stdout)
    st = (d.get("streams") or [{}])[0]
    num, _, den = (st.get("r_frame_rate") or "30/1").partition("/")
    fps = float(num) / float(den or 1)
    return dict(fps=round(fps, 4), w=st.get("width"), h=st.get("height"),
                dur=float(d["format"]["duration"]))


def silences(path, db, mind):
    p = subprocess.run(
        ["ffmpeg", "-v", "info", "-i", str(path),
         "-af", f"silencedetect=noise={db}dB:d={mind}", "-f", "null", "-"],
        capture_output=True, text=True)
    starts, spans = [], []
    for line in p.stderr.splitlines():
        m = re.search(r"silence_start: (-?[\d.]+)", line)
        if m:
            starts.append(max(0.0, float(m.group(1))))
        m = re.search(r"silence_end: ([\d.]+)", line)
        if m and starts:
            spans.append((starts.pop(), float(m.group(1))))
    return spans


def speech_from_silence(spans, dur):
    """Silence ke beech jo bacha, wahi bola hua hissa hai."""
    out, t = [], 0.0
    for a, b in sorted(spans):
        if a - t > 0.01:
            out.append((t, a))
        t = max(t, b)
    if dur - t > 0.01:
        out.append((t, dur))
    return out


def plan(speech, dur, fps, c):
    pieces = []
    for i, (s, e) in enumerate(speech):
        if e - s < c["min_piece"]:
            continue                      # bahut chhota - saans ya khat-pat hai, bolna nahi
        lead = c["scene_lead_in"] if not pieces else c["pre_pad"]
        a = max(0.0, s - lead)
        b = min(dur, e + c["post_pad"])
        if pieces and a - pieces[-1]["out"] <= 0.02:
            pieces[-1]["out"] = b         # chipke hue tukde jod do
        else:
            pieces.append(dict(**{"in": a, "out": b}))
    if not pieces:
        sys.exit("Koi bolne wala hissa nahi mila. --silence-db thoda upar karo (-30 try karo).")
    pieces[-1]["out"] = min(dur, pieces[-1]["out"] + c["scene_tail"] - c["post_pad"])

    for i, p in enumerate(pieces):
        p["in_f"] = round(p["in"] * fps)
        p["out_f"] = round(p["out"] * fps)
        p["in"] = p["in_f"] / fps
        p["out"] = p["out_f"] / fps
        p["dur"] = round(p["out"] - p["in"], 3)
        gap = p["in"] - pieces[i - 1]["out"] if i else 0.0
        p["gap_before"] = round(gap, 3)
        p["note"] = ("scene start" if not i else
                     f"pause {gap:.2f}s -> {c['pause_keep']:.2f}s" if gap > c["max_pause"]
                     else f"pause {gap:.2f}s rakha")
    return pieces


def tc(seconds, fps):
    f = int(round(seconds * fps))
    h, f = divmod(f, int(round(fps)) * 3600)
    m, f = divmod(f, int(round(fps)) * 60)
    s, f = divmod(f, int(round(fps)))
    return f"{h:02d}:{m:02d}:{s:02d}:{f:02d}"


def write_edl(pieces, fps, src_name, out_path, title):
    L = [f"TITLE: {title}", "FCM: NON-DROP FRAME", ""]
    rec = 0.0
    for i, p in enumerate(pieces, 1):
        L.append(f"{i:03d}  AX       AA/V  C        "
                 f"{tc(p['in'], fps)} {tc(p['out'], fps)} "
                 f"{tc(rec, fps)} {tc(rec + p['dur'], fps)}")
        L.append(f"* FROM CLIP NAME: {src_name}")
        L.append("")
        rec += p["dur"]
    out_path.write_text("\n".join(L))


def render(src, pieces, out, fps):
    tmp = out.parent / (out.stem + "_parts")
    tmp.mkdir(exist_ok=True)
    for f in tmp.glob("*.mp4"):
        f.unlink()
    files = []
    for i, p in enumerate(pieces):
        o = tmp / f"p{i:03d}.mp4"
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-ss", f"{p['in']:.3f}", "-to", f"{p['out']:.3f}",
             "-i", str(src), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
             "-pix_fmt", "yuv420p", "-r", str(round(fps)),
             "-c:a", "aac", "-b:a", "160k", "-ar", "48000", str(o)], check=True)
        files.append(o)
    lst = tmp / "list.txt"
    lst.write_text("".join(f"file '{f.name}'\n" for f in files))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0",
                    "-i", str(lst), "-c", "copy", str(out)],
                   check=True, cwd=str(tmp))
    shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description="jhatpat-reel rough cut")
    ap.add_argument("video")
    ap.add_argument("--preset", default="reel", choices=sorted(PRESETS))
    ap.add_argument("--config", help="JSON file jo preset ki values override kare")
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--no-render", action="store_true", help="sirf cuts.json + EDL")
    ap.add_argument("--silence-db", type=float)
    ap.add_argument("--max-pause", type=float)
    a = ap.parse_args()

    need("ffmpeg")
    src = Path(a.video).expanduser().resolve()
    if not src.exists():
        sys.exit(f"File nahi mili: {src}")

    c = dict(PRESETS[a.preset])
    if a.config:
        user = json.loads(Path(a.config).read_text())
        # "_" se shuru hone wali keys sirf samjhane ke liye hain
        c.update({k: v for k, v in user.items() if not k.startswith("_")})
        unknown = [k for k in user if not k.startswith("_") and k not in PRESETS["reel"]]
        if unknown:
            print(f"warning: ye keys pehchani nahi gayi: {', '.join(unknown)}")
    if a.silence_db is not None:
        c["silence_db"] = a.silence_db
    if a.max_pause is not None:
        c["max_pause"] = a.max_pause

    out_dir = Path(a.out_dir).expanduser() if a.out_dir else src.parent / "jhatpat"
    out_dir.mkdir(parents=True, exist_ok=True)

    info = probe(src)
    sp = silences(src, c["silence_db"], c["silence_min"])
    speech = speech_from_silence(sp, info["dur"])
    pieces = plan(speech, info["dur"], info["fps"], c)
    kept = sum(p["dur"] for p in pieces)

    (out_dir / "cuts.json").write_text(json.dumps(
        dict(source=str(src), preset=a.preset, config=c, info=info,
             silences=sp, pieces=pieces, raw=info["dur"], cut=round(kept, 3)), indent=1))
    write_edl(pieces, info["fps"], src.name, out_dir / f"{src.stem}.edl", src.stem)

    print(f"raw   : {info['dur']:.2f}s   {info['w']}x{info['h']} @ {info['fps']}fps")
    print(f"cut   : {kept:.2f}s   ({info['dur']-kept:.2f}s nikala, "
          f"{100*(info['dur']-kept)/info['dur']:.0f}% chhota)")
    print(f"pieces: {len(pieces)}   silences mile: {len(sp)}")
    for i, p in enumerate(pieces, 1):
        print(f"  {i:>2}. {p['in']:7.2f} - {p['out']:6.2f}  ({p['dur']:5.2f}s)  {p['note']}")

    if not a.no_render:
        out = out_dir / f"{src.stem}_cut.mp4"
        render(src, pieces, out, info["fps"])
        print(f"\nbana  : {out}")
    print(f"EDL   : {out_dir / (src.stem + '.edl')}  (Premiere: File > Import)")


if __name__ == "__main__":
    main()
