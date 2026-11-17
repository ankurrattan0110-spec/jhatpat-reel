# Changelog

## v2: motion graphics (Nov 2026)

**New**
- `motion_graphics.py`: tech-style graphics driven by one `graphics.json`. 14 beat types: terminal, clock, countdown, before/after, device frames, word captions, file import, this-reel timeline, repo card, big CTA word and more. Big text passes behind the speaker's head using a wall-colour mask (no AI model, no download). Synthesised sound effects, -14 LUFS output, Premiere marker EDL.
- `preview_timer.py`: big timer and piece numbers on your video, for finding exact times.
- `remove_range.py`: cut out a line or retake by time, snapped to the nearest pause.
- `examples/graphics.example.json`: the full config from a real 65-second reel.
- `requirements.txt` (numpy, opencv-python, pillow), needed only for graphics.
- Fonts are found automatically on Windows, macOS and Linux.
- Any input size works: 16:9 is cover-cropped to 9:16 for graphics.

**Docs**
- Step-by-step Windows quick start: installing ffmpeg/Python, folders, hidden `.mp4` extensions, drag-to-paste paths.
- Install folders for Claude Code, Codex and Gemini CLI.
- `SKILL.md`: new stages for removing lines and adding graphics, plus new rules (on-screen numbers must match what was said, never cover the face).

**Fixed**
- `SKILL.md` mentioned `--pre-pad` / `--post-pad` flags that don't exist. It now points to `config.json`.

## v1: first version (Nov 2026)
- `rough_cut.py`, `reframe.py`, `burn_captions.py`.
