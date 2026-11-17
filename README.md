# jhatpat-reel

**Ek lamba take do. Tight reel wapas lo.**

A free, open-source skill that turns one talking-head take into a finished Instagram Reel or YouTube Short: silence cut, bad lines removed, reframed, captioned, and finished with tech-style motion graphics. No timeline needed.

Built by [Ankur Rattan Shakya](https://instagram.com/ankurrattanshakya) for Hinglish and Hindi creators who film one take and don't want to spend two hours editing a sixty-second video. Made with the help of Claude.

**Works with or without AI.** Every script runs on its own with Python and ffmpeg. Add it to Claude Code (or Codex / Gemini CLI) and you can just say *"edit this reel"*.

---

## What it does

| Script | What it does |
|---|---|
| `rough_cut.py` | Cuts silence and dead air. A 3 min 41 s take became 68 s. Exports an EDL for Premiere. |
| `preview_timer.py` | Puts a big timer on your video so you can note exactly when a line starts and ends. |
| `remove_range.py` | Removes a bad line or retake by time, and snaps the cut to the nearest pause. |
| `reframe.py` | One cut, three shapes: 9:16, 1:1, 16:9. |
| `burn_captions.py` | Instagram-style captions from an SRT file. |
| `motion_graphics.py` | Terminal, clock, countdown, before/after bars, device frames, captions, and big words that pass **behind your head**, plus sound effects. |

---

## Quick start: Windows (step by step)

**1. Install once.** Open PowerShell and run:
```
winget install Gyan.FFmpeg
winget install Python.Python.3.12
```
Close PowerShell and open it again. Check both with:
```
ffmpeg -version
python --version
```

**2. Download the skill.**
- On this page, click the green **Code** button → **Download ZIP**
- Right-click the zip → **Extract All** → type `D:\` (or `C:\`) → **Extract**
- You now have `D:\jhatpat-reel-main\`. Inside it you should see `scripts` and `SKILL.md`.
  If you see another `jhatpat-reel-main` folder inside, use that inner one.

**3. Put your video in the same folder**, next to `SKILL.md`, and name it `take.mp4`.

> **Watch out:** Windows hides file extensions. If you type `take.mp4` you may get `take.mp4.mp4`.
> In File Explorer turn on **View → Show → File name extensions** to check.

**4. Open PowerShell inside that folder.** Click File Explorer's address bar, type `powershell`, press Enter.

**5. Cut the silence:**
```
python scripts\rough_cut.py take.mp4 --preset tight
```
Your cut is now at `jhatpat\take_cut.mp4`.

> **Tip:** if your video is somewhere else, type `python scripts\rough_cut.py ` (with a space),
> then **drag the video file into the PowerShell window**. Windows pastes its exact path for you.

**6. (Optional) Remove a bad line:**
```
python scripts\preview_timer.py jhatpat\take_cut.mp4
```
Play `take_cut_timer.mp4` and note when the line starts and ends, then:
```
python scripts\remove_range.py jhatpat\take_cut.mp4 27.6-28.9
```

**7. (Optional) Add motion graphics:**
```
pip install -r requirements.txt
copy examples\graphics.example.json graphics.json
```
If you removed a line in step 6, use `jhatpat\take_cut_trimmed.mp4` instead of `jhatpat\take_cut.mp4` below.
Open `graphics.json` in Notepad and change the times and text to match **your** video (use the timer video for the times). Check the layout first, then render:
```
python scripts\motion_graphics.py jhatpat\take_cut.mp4 graphics.json --stills 5,15,30
python scripts\motion_graphics.py jhatpat\take_cut.mp4 graphics.json
```
Your finished reel is `jhatpat\take_cut_graphics.mp4`: 1080×1920, with loudness set for Instagram and YouTube.

**macOS / Linux:** same steps. Use `python3` instead of `python`, `/` instead of `\`, and install with `brew install ffmpeg` or `sudo apt install ffmpeg`.

---

## Use it with an AI agent

```bash
git clone https://github.com/ankurrattan0110-spec/jhatpat-reel.git
```
Copy the folder into your agent's skills folder:

| Agent | Folder |
|---|---|
| Claude Code | `~/.claude/skills/jhatpat-reel` |
| OpenAI Codex | `.agents/skills/jhatpat-reel` |
| Gemini CLI | `.gemini/skills/jhatpat-reel` |

Open the agent in the folder where your footage is and say **"edit this reel"**. `SKILL.md` tells the agent which script to run when, and what to ask you.

---

## The scripts in detail

### `rough_cut.py`: silence out, cut list in
```
python scripts/rough_cut.py take.mp4 --preset reel
python scripts/rough_cut.py take.mp4 --preset calm --no-render
```
| Preset | For | Feels like |
|---|---|---|
| `reel` | default | tight, Instagram pacing |
| `calm` | poetry, storytelling | room to breathe |
| `tight` | hook-heavy, fast tutorials | no empty frames at all |

Writes `jhatpat/cuts.json`, `jhatpat/<name>_cut.mp4`, `jhatpat/<name>.edl`. Tune the numbers by copying `config.example.json` to `config.json` and passing `--config config.json`.

### `preview_timer.py` + `remove_range.py`: take out one line
`remove_range.py` snaps your times into the nearest pause, so a rough guess like `27.6-28.9` still cuts cleanly without clipping a word. You can remove several ranges at once: `12.0-13.4 27.6-28.9`. Use `--no-snap` to cut exactly where you say.

### `reframe.py`: one cut, every shape
```
python scripts/reframe.py cut.mp4 --all
python scripts/reframe.py cut.mp4 --to 9:16 --anchor 0.3
```
`--anchor` decides where the crop sits (0 = top, 1 = bottom). If your face gets cut off, lower it. `--mode pad` keeps the whole frame for screen recordings.

### `burn_captions.py`: Instagram-style captions
```
python scripts/burn_captions.py reel.mp4 reel.srt --style pop --accent "#C6FF3D"
```
Styles: `pop` (1–3 big words in the middle), `box` (words on a solid box), `bar` (small line at the bottom). For Hindi script, pass a Devanagari font with `--font`.

### `motion_graphics.py`: the beats
Everything is driven by `graphics.json`. Each beat has a `type`, a `start` and an `end`:

`push_in` · `timeline_fast` · `kinetic_list` · `clock` · `flat_graph` · `countdown` · `terminal` · `before_after` · `devices` · `word_captions` · `file_import` · `this_timeline` · `repo_card` · `big_word`

`examples/graphics.example.json` is the full config from a real 65-second reel. Start from it.

- **Behind the head:** the script reads the colour of your wall to separate you from the background, with no AI model and no download. It works best with **a plain wall, a phone on a tripod, and you sitting fairly still**. With a busy background, set `"mask": {"enabled": false}`.
- **Fonts:** leave them on `"auto"` and it picks what your system has (Segoe UI Black / Consolas on Windows, Arial Black / Menlo on Mac). Install Inter for the best look.
- **Speed:** a 60-second reel takes roughly 5–10 minutes on a normal laptop. Use `--range 20-30` to render just one part while you adjust timing.
- **Premiere:** `<name>_markers.edl` has a marker for every beat and sound effect.

---

## Honest limits

- **It doesn't understand what you say.** It finds silence, not meaning. You give the times of retakes (with the timer video) or use a transcript.
- **The graphics are a template, not magic.** You set the times and text in `graphics.json`. The example shows how.
- **It's a first pass.** Notes you give become rules in `SKILL.md`, so the next reel starts smarter.
- It doesn't post, doesn't pick music, and doesn't film.

## Licence

MIT. Use it, change it, and sell what you make with it. See [LICENSE](LICENSE).

## Credits

Written by Ankur Rattan Shakya, with Claude as the pair programmer. No code or text was copied from another skill.

If it saves you an hour, tell me what you made with it → [@ankurrattanshakya](https://instagram.com/ankurrattanshakya)
