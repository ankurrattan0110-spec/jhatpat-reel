#!/usr/bin/env python3
"""jhatpat-reel · burn_captions

SRT ko video par chipka deta hai - Instagram wale bade, mote, padhne-layak captions.
Hinglish Roman me by default; Devanagari chahiye to --font se Noto Sans Devanagari do.

Styles:
  pop   - 1-3 bade shabd beech me, keyword accent colour me
  box   - solid box par shabd, busy footage ke upar bhi dikhte hain
  bar   - neeche patli line, long-form ke liye

Usage:
  python3 burn_captions.py reel.mp4 reel.srt --style pop
  python3 burn_captions.py reel.mp4 reel.srt --style box --accent "#C6FF3D"
  python3 burn_captions.py reel.mp4 reel.srt --font ~/Library/Fonts/NotoSansDevanagari-Bold.ttf
"""
import argparse, re, shutil, subprocess, sys
from pathlib import Path

# size aur margin dono video ki height ke hisaab se nikalte hain, taaki
# 9:16, 1:1 aur 16:9 teeno me caption ek jaisa dikhe.
#   size_frac   : font size = height * frac
#   margin_frac : neeche se itni height upar (Alignment hamesha 2 = bottom-center,
#                 kyunki libass ke dono numbering schemes me 2 ka matlab wahi hai)
STYLES = {
    "pop": dict(size_frac=0.055, outline=4, shadow=1, margin_frac=0.44, box=0, words=3),
    "box": dict(size_frac=0.044, outline=0, shadow=0, margin_frac=0.13, box=3, words=5),
    "bar": dict(size_frac=0.032, outline=2, shadow=0, margin_frac=0.06, box=0, words=0),
}

TS = re.compile(r"(\d\d):(\d\d):(\d\d)[,.](\d\d\d)\s*-->\s*(\d\d):(\d\d):(\d\d)[,.](\d\d\d)")


def _sec(h, m, s, ms):
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def _stamp(t):
    h, r = divmod(max(0.0, t), 3600)
    m, s = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s % 1) * 1000)):03d}"


def parse_srt(text):
    cues, cur = [], None
    for line in text.splitlines():
        m = TS.search(line)
        if m:
            cur = dict(a=_sec(*m.groups()[:4]), b=_sec(*m.groups()[4:]), lines=[])
            cues.append(cur)
        elif cur is not None and line.strip() and not line.strip().isdigit():
            cur["lines"].append(line.strip())
    return [c for c in cues if c["lines"]]


def resplit(cues, max_words):
    """Lambe cue ko chhote tukdon me baant do, time barabar baant kar.
    pop style ka poora matlab hi yahi hai - 1 se 3 shabd, bade."""
    if not max_words:
        return cues
    out = []
    for c in cues:
        words = " ".join(c["lines"]).split()
        if len(words) <= max_words:
            out.append(c); continue
        groups = [words[i:i + max_words] for i in range(0, len(words), max_words)]
        span = (c["b"] - c["a"]) / len(groups)
        for i, g in enumerate(groups):
            out.append(dict(a=c["a"] + i * span, b=c["a"] + (i + 1) * span, lines=[" ".join(g)]))
    return out


def _ass_time(t):
    h, r = divmod(max(0.0, t), 3600)
    m, s = divmod(r, 60)
    return f"{int(h):d}:{int(m):02d}:{int(s):02d}.{int((s % 1) * 100):02d}"


def write_ass(cues, path, *, w, h, font, size, primary, outline_col,
              border_style, outline, shadow, marginv, side):
    """ASS khud likhte hain taaki PlayRes video ke barabar ho.

    SRT ko seedha ffmpeg ke subtitles filter me dene par wo 384x288 ka
    farzi canvas maan leta hai, aur pixel me diye gaye size/margin bahar
    chale jaate hain. Isliye apni ASS banate hain - sab kuch asli pixel me.
    """
    head = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {w}", f"PlayResY: {h}",
        "WrapStyle: 0", "ScaledBorderAndShadow: yes", "YCbCr Matrix: TV.709", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: J,{font},{size},{primary},{primary},{outline_col},&H90000000,"
        f"1,0,0,0,100,100,0,0,{border_style},{outline},{shadow},2,{side},{side},{marginv},1",
        "", "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for c in cues:
        text = "\\N".join(x.replace("\n", " ").strip() for x in c["lines"])
        head.append(f"Dialogue: 0,{_ass_time(c['a'])},{_ass_time(c['b'])},J,,0,0,0,,{text}")
    path.write_text("\n".join(head) + "\n", encoding="utf-8")


def need(tool):
    if shutil.which(tool) is None:
        sys.exit(f"'{tool}' nahi mila. ffmpeg install karo.")


def video_size(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", str(path)],
                       capture_output=True, text=True)
    try:
        w, h = r.stdout.strip().split("x")[:2]
        return int(w), int(h)
    except ValueError:
        return 1080, 1920


def hex_to_ass(h):
    """#RRGGBB -> &HAABBGGRR& (ASS BGR order)."""
    h = h.lstrip("#")
    if len(h) != 6:
        sys.exit(f"Colour aise do: #RRGGBB (mila: {h})")
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H00{b}{g}{r}".upper()


def load_srt(path):
    cues = parse_srt(path.read_text(encoding="utf-8", errors="replace"))
    if not cues:
        sys.exit(f"{path.name} me koi timing nahi mili - ye SRT nahi lagta.")
    return cues


def main():
    ap = argparse.ArgumentParser(description="jhatpat-reel burn captions")
    ap.add_argument("video")
    ap.add_argument("srt")
    ap.add_argument("--style", default="pop", choices=sorted(STYLES))
    ap.add_argument("--accent", default="#FFFFFF", help="caption text colour, #RRGGBB")
    ap.add_argument("--outline-colour", default="#000000")
    ap.add_argument("--font", default=None, help="font file ka path (Devanagari ke liye zaroori)")
    ap.add_argument("--font-name", default="Inter")
    ap.add_argument("--words", type=int, default=None,
                    help="ek cue me zyada se zyada kitne shabd (style ka default override)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    need("ffmpeg")
    vid, srt = Path(a.video).expanduser().resolve(), Path(a.srt).expanduser().resolve()
    for p in (vid, srt):
        if not p.exists():
            sys.exit(f"File nahi mili: {p}")

    s = STYLES[a.style]
    cues = load_srt(srt)
    before = len(cues)
    cues = resplit(cues, a.words if a.words is not None else s["words"])
    n = len(cues)
    if n != before:
        print(f"{before} cues ko {n} chhote cues me toda ({a.style} style)")
    name = a.font_name
    fontsdir = ""
    if a.font:
        fp = Path(a.font).expanduser().resolve()
        if not fp.exists():
            sys.exit(f"Font nahi mila: {fp}")
        fontsdir = f":fontsdir={fp.parent}"
        name = fp.stem.split("-")[0]

    vw, vh = video_size(vid)
    out = Path(a.out).expanduser() if a.out else vid.parent / f"{vid.stem}_captioned.mp4"
    work = out.parent / f".jhatpat_{vid.stem}_{a.style}.ass"
    write_ass(cues, work, w=vw, h=vh, font=name,
              size=max(12, int(round(vh * s["size_frac"]))),
              primary=hex_to_ass(a.accent), outline_col=hex_to_ass(a.outline_colour),
              border_style=3 if s["box"] else 1,
              outline=int(round(vh * 0.004)) + (4 if s["box"] else s["outline"]),
              shadow=s["shadow"], marginv=int(round(vh * s["margin_frac"])),
              side=int(round(vh * 0.035)))

    # filter me path likhne se bachne ke liye usi folder me chalao
    vf = f"ass={work.name}{fontsdir}"
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(vid), "-vf", vf,
         "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
         "-c:a", "copy", "-movflags", "+faststart", str(out.name)],
        cwd=str(out.parent), capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("Captions chipkane me dikkat:\n" + r.stderr.strip()[-700:])
    work.unlink(missing_ok=True)
    print(f"{n} captions chipkaye ({a.style} style, {vw}x{vh})  ->  {out}")


if __name__ == "__main__":
    main()
