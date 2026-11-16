---
name: jhatpat-reel
description: Turn one long talking-head take into a tight Instagram Reel or YouTube Short. Cuts silence and dead air, keeps the best take of each line, reframes to 9:16 / 1:1 / 16:9, burns Instagram-style captions, and exports an EDL for Premiere Pro. Built for Hinglish and Hindi creators who film one take on a phone or DSLR. Use for "edit this reel", "cut this take", "make a short out of this", or any first-pass edit of a single-speaker video.
---

# jhatpat-reel

**Seedhi baat:** ek lamba take do, tight reel wapas lo. Pehla draft machine banayegi, taste tum lagaoge.

Ye skill **first-pass editor** hai, final editor nahi. Script silence aur dead air nikalti hai;
retake aur fumble tum (ya Claude transcript padh kar) batate ho. Raw footage kabhi change nahi hoti.

## Kab use karna hai

- Ek speaker, ek take, phone ya DSLR se — talking head.
- Instagram Reel, YouTube Short, ya dono ek hi take se.
- Hinglish, Hindi ya English — teeno chalega.

Kab **nahi**: multi-camera interview, music video, ya aisa edit jahan har cut pe taste
chahiye. Uske liye timeline khud kholo.

## Kya chahiye

| Cheez | Kyun | Check |
|---|---|---|
| `ffmpeg` + `ffprobe` | kaatna, reframe, captions | `ffmpeg -version` |
| `python3` 3.9+ | teeno script | `python3 --version` |
| transcript (optional) | retake pakadne ke liye | whisper / whisperx / koi bhi STT |
| Devanagari font (optional) | Hindi captions | Noto Sans Devanagari |

## Pipeline

Har stage ka output agla stage khata hai. Beech me ruk kar dikhao, phir aage badho.

### Stage 0 — dekho, phir kaato
Footage probe karo. Creator ko ek line me batao: kitni lambi, kaun sa resolution, fps,
audio kis channel pe. Agar **vertical already hai**, reframe skip ho sakta hai.
Agar **awaaz sirf ek channel me hai** (wireless mic ka common issue), pehle wo theek karo —
warna cut ke baad aadhi reel me awaaz nahi aayegi.

Agar transcript mil sakta hai, abhi le lo. Transcript ke bina ye skill sirf **silence**
hata sakti hai; retake aur fumble nahi pakad sakti. Creator ko ye saaf bata do.

### Stage 1 — rough cut
```bash
python3 scripts/rough_cut.py take.mp4 --preset reel
```
Presets: `reel` (default, chust), `calm` (poetry, story, lambi baat), `tight` (hook-heavy, fast).

Ye teen cheezein banata hai: `cuts.json`, `<name>_cut.mp4`, `<name>.edl`.

**Agar transcript hai**, `cuts.json` padho aur retake wale pieces nikaal do:
ek hi line do-teen baar boli gayi ho to **aakhri saaf wala** rakho, baaki hata do.
"sorry", "ek baar phir", "umm" — ye bhi jaate hain. Phir dobara render karo.
`cuts.json` ko haath se mat likho — preset ya config badal kar script dobara chalao.

### Stage 2 — cut sun kar check karo
Har cut ke dono taraf 0.2s sun'na zaroori hai. Agar koi shabd beech se kata hai,
`--pre-pad` / `--post-pad` badhao. Transcript sahi dikh sakta hai jabki audio kata hua ho.

### Stage 3 — reframe
```bash
python3 scripts/reframe.py take_cut.mp4 --all        # 9:16 + 1:1 + 16:9
python3 scripts/reframe.py take_cut.mp4 --to 9:16 --anchor 0.3
```
`--anchor` se tay hota hai frame kahan se kate. Talking head me chehra upar hota hai,
isliye default `0.35` hai. Chehra kat raha ho to anchor **kam** karo.
Screen recording ke liye `--mode pad` — crop se text kat jaata hai.

### Stage 4 — captions
```bash
python3 scripts/burn_captions.py take_cut_9x16.mp4 take.srt --style pop --accent "#C6FF3D"
```
Styles: `pop` (1-3 bade shabd beech me — reel aur hook ke liye),
`box` (solid box, busy footage ke upar bhi padhne layak),
`bar` (neeche patli line, long-form).

Script khud lambe cue ko chhote tukdon me todta hai, taaki `pop` ka matlab bana rahe.
Hindi captions ke liye `--font` se Devanagari font ka path do — warna aadhe
akshar nahi banenge.

### Stage 5 — aakhri nazar
Export se pehle apne hi kaam par ye check chalao:

1. **Pehla second.** Pehle frame me kuch ho — chehra, bada shabd, ya movement. Khali frame = scroll.
2. **Koi shabd kata to nahi.** Teen random cut sun lo.
3. **Captions chehre pe to nahi.** 9:16 me `pop` beech me aata hai; agar chehra beech me hai to `--style box` better hai.
4. **Last 2 second.** CTA dikhe aur ruke, bhaage nahi.
5. **Awaaz.** Instagram aur YouTube dono -14 LUFS pe normalise karte hain. Isse zyada dhimi rakhoge to wo uthayenge aur kharab lagegi:
   ```bash
   ffmpeg -i final.mp4 -af loudnorm=I=-14:TP=-1.5:LRA=11 -c:v copy out.mp4
   ```

## Rules (har rule ke saath wajah)

- **Raw footage kabhi mat chhuo.** Sab kuch naye file me. *Kyunki* ek galat render se shoot wapas nahi aati.
- **Cut par zoom mat karo.** *Kyunki* cut pe zoom cut ko announce kar deta hai.
- **Ek reel, ek baat.** Doosri baat doosri reel hai. *Kyunki* do baatein ek saath = dono yaad nahi rehti.
- **Pause poore mat hatao.** `pause_keep` 0.2s se neeche mat le jao. *Kyunki* bilkul chipke hue shabd robot jaise lagte hain, aur saans lene ki jagah chahiye.
- **Hook ke baad hi baaki kuch.** Pehle 3 second theek na hon to baaki edit bekaar hai. *Kyunki* wahin pe log scroll karte hain.
- **Jo creator ne haath se hata diya, wapas mat lao.** Dobara render se pehle unka version padho.
- **Transcript ke bina retake ka dawa mat karo.** Saaf bolo: "silence hata di, retake tumhe dekhne honge."

## Config

`config.example.json` copy karke `config.json` banao, phir `--config config.json` do.
Har value ka matlab wahin likha hai.

## Jo ye skill nahi karti

- Film nahi karti. Shoot tumhara.
- Instagram pe post nahi karti.
- Kisi aur ka video download ya copy nahi karti.
- Music nahi chunti — licence tumhari zimmedari.
- Transcript nahi banati; STT tum chalao, SRT do.

## Notes wapas skill me daalo

Jab creator kahe "cut bahut choppy hai" ya "caption chehre pe aa raha hai" —
wo theek karo **aur us note ko yahan rule bana kar likh do, wajah ke saath**.
Do-teen reel ke baad ye skill tumhari taste se chalne lagegi.
