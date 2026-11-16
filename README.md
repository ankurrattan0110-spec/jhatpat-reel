# jhatpat-reel

**Ek lamba take do. Tight reel wapas lo.**

A Claude skill that turns one talking-head take into a finished Instagram Reel or YouTube Short — silence cut, reframed, captioned — without opening a timeline.

Built by [Ankur Rattan Shakya](https://instagram.com/ankurrattanshakya) for Hinglish and Hindi creators who film one take and don't want to spend two hours editing a sixty-second video.

```bash
# ek take, teen output
python3 scripts/rough_cut.py take.mp4 --preset reel
python3 scripts/reframe.py jhatpat/take_cut.mp4 --all
python3 scripts/burn_captions.py jhatpat/take_cut_9x16.mp4 take.srt --style pop
```

---

## Why

Most editing tools assume English and assume you edit in their app. This one assumes
you speak Hinglish, film one take, and already have an editor you like.

- **Hinglish pacing.** Hindi bolne me English se lamba pause aata hai. The presets are tuned for that, not copied from an English tool.
- **Your editor, not mine.** Every cut also exports as an EDL you can import into Premiere Pro or DaVinci Resolve. Use the rendered MP4, or take the cut list and finish by hand.
- **One take, three aspect ratios.** 9:16 for Reels and Shorts, 1:1 for the feed, 16:9 for YouTube — from the same cut.
- **Raw footage is never touched.** Everything is written to a new `jhatpat/` folder.

---

## Install

```bash
git clone https://github.com/ankurrattan0110-spec/jhatpat-reel.git
mkdir -p ~/.claude/skills
cp -R jhatpat-reel ~/.claude/skills/
```

Then open Claude Code where your footage is and say **"edit this reel"**.

Or use the scripts on their own — they don't need Claude:

```bash
python3 jhatpat-reel/scripts/rough_cut.py take.mp4
```

### What you need

| Thing | Why | Cost |
|---|---|---|
| `ffmpeg` + `ffprobe` | cutting, reframing, captions | free |
| `python3` 3.9+ | the three scripts | free |
| any speech-to-text | only if you want retakes removed too | free (whisper) |
| Noto Sans Devanagari | only for Hindi-script captions | free |

```bash
brew install ffmpeg          # macOS
choco install ffmpeg         # Windows
sudo apt install ffmpeg      # Linux
```

---

## The three scripts

### `rough_cut.py` — silence out, cut list in

```bash
python3 scripts/rough_cut.py take.mp4 --preset reel
python3 scripts/rough_cut.py take.mp4 --preset calm --no-render
python3 scripts/rough_cut.py take.mp4 --silence-db -34 --max-pause 0.6
```

| Preset | For | Feels like |
|---|---|---|
| `reel` | default | chust, Instagram pacing |
| `calm` | poetry, storytelling, long explainers | saans lene ki jagah |
| `tight` | hook-heavy, fast tutorials | ek bhi khali frame nahi |

Writes `jhatpat/cuts.json`, `jhatpat/<name>_cut.mp4` and `jhatpat/<name>.edl`.

Example output:

```
raw   : 54.00s   1280x720 @ 30.0fps
cut   : 38.27s   (15.73s nikala, 29% chhota)
pieces: 12   silences mile: 13
   1.    0.87 -   4.13  ( 3.27s)  scene start
   2.    5.33 -   6.73  ( 1.40s)  pause 1.20s -> 0.22s
```

### `reframe.py` — one cut, every aspect ratio

```bash
python3 scripts/reframe.py cut.mp4 --all
python3 scripts/reframe.py cut.mp4 --to 9:16 --anchor 0.3
python3 scripts/reframe.py cut.mp4 --to 16:9 --mode pad
```

`--anchor` decides where the crop sits: `0` is hard top (or left), `1` is hard bottom
(or right). Default `0.35` suits a talking head, where the face sits high in frame.
Face getting cut? Lower the anchor.

`--mode pad` keeps the whole frame and fills the sides with a blurred copy — use it for
screen recordings, where cropping would slice the text.

### `burn_captions.py` — Instagram-style captions

```bash
python3 scripts/burn_captions.py reel.mp4 reel.srt --style pop --accent "#C6FF3D"
python3 scripts/burn_captions.py reel.mp4 reel.srt --style box
python3 scripts/burn_captions.py reel.mp4 reel.srt --font ~/Library/Fonts/NotoSansDevanagari-Bold.ttf
```

| Style | Looks like | Good for |
|---|---|---|
| `pop` | 1–3 big words in the middle | reels, hooks |
| `box` | words on a solid box | busy footage, b-roll |
| `bar` | small line at the bottom | long-form |

Long subtitle cues get split automatically so `pop` stays 1–3 words. Font size and
position scale with the video height, so the same command looks right at 9:16, 1:1
and 16:9.

---

## Honest limits

- **It does not find your retakes.** Without a transcript it only hears silence, not meaning. Feed it an SRT and ask Claude to drop the retakes, or trim them yourself.
- **It is a first pass.** Expect to give notes. That is the point — notes become rules in `SKILL.md`, and the next reel starts smarter.
- **It does not post, does not pick music, does not film.**
- Tested on macOS and Linux with ffmpeg 6. Windows should work; tell me if it doesn't.

## Licence

MIT — use it, change it, sell what you make with it. See [LICENSE](LICENSE).

## Credits

Written from scratch by Ankur Rattan Shakya, with Claude as the pair programmer.
No code or text was copied from another skill.

If it saves you an hour, tell me what you made with it.
