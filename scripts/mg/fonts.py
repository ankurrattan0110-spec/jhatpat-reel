"""Find usable fonts on Windows, macOS or Linux without asking the user to install anything.

Config can name a font file directly. Anything left as "auto" (or a path that does not
exist) falls back through this list. Inter / Montserrat look best - install them if you like."""
import os
from pathlib import Path

WIN = os.environ.get("WINDIR", r"C:\Windows")
CANDIDATES = {
    "black": [
        "Inter-Black.otf", "Inter-ExtraBold.otf", "Montserrat-ExtraBold.ttf", "Montserrat-Black.ttf",
        rf"{WIN}\Fonts\seguibl.ttf",          # Segoe UI Black
        rf"{WIN}\Fonts\ariblk.ttf",           # Arial Black
        "/System/Library/Fonts/Supplemental/Arial Black.ttf",
        "/Library/Fonts/Arial Black.ttf",
        "/usr/share/fonts/opentype/inter/Inter-Black.otf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ],
    "bold": [
        "Inter-Bold.otf", "Montserrat-Bold.ttf",
        rf"{WIN}\Fonts\seguisb.ttf", rf"{WIN}\Fonts\arialbd.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/usr/share/fonts/opentype/inter/Inter-Bold.otf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ],
    "mono": [
        "JetBrainsMono-Bold.ttf",
        rf"{WIN}\Fonts\consolab.ttf", rf"{WIN}\Fonts\courbd.ttf",
        "/System/Library/Fonts/Menlo.ttc", "/System/Library/Fonts/Supplemental/Courier New Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    ],
    "mono_regular": [
        "JetBrainsMono-Regular.ttf",
        rf"{WIN}\Fonts\consola.ttf", rf"{WIN}\Fonts\cour.ttf",
        "/System/Library/Fonts/Menlo.ttc", "/System/Library/Fonts/Supplemental/Courier New.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    ],
}

USER_DIRS = [
    Path.home() / "AppData/Local/Microsoft/Windows/Fonts",
    Path.home() / "Library/Fonts",
    Path.home() / ".local/share/fonts",
    Path.home() / ".fonts",
    Path(WIN) / "Fonts",
    Path("/usr/share/fonts/opentype/inter"),
    Path("/usr/share/fonts/truetype"),
]


def _find(name):
    p = Path(name).expanduser()
    if p.is_absolute():
        return str(p) if p.exists() else None
    for d in USER_DIRS:
        q = d / name
        if q.exists():
            return str(q)
    return None


def resolve(fonts_cfg):
    out = {}
    for role, cands in CANDIDATES.items():
        want = (fonts_cfg or {}).get(role, "auto")
        hit = None if want in (None, "", "auto") else _find(want)
        if not hit:
            for c in cands:
                hit = _find(c)
                if hit:
                    break
        if not hit:
            raise SystemExit(f"Koi '{role}' font nahi mila. config me 'fonts.{role}' me kisi .ttf/.otf ka poora path do.")
        out[role] = hit
    out["semibold"] = out["bold"]
    return out
