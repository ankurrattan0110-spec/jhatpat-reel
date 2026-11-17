"""Tiny synthesised sound effects - no sample files, no licences to worry about."""
import subprocess
import wave
import numpy as np

SR = 48000


def synth(kind, rng):
    def env(n, a=0.004, d=8.0):
        t = np.arange(n) / SR
        return np.minimum(1, t / a) * np.exp(-t * d)
    if kind in ("whoosh", "whoosh_s"):
        n = int(SR * (0.55 if kind == "whoosh" else 0.32)); t = np.arange(n) / SR
        noise = rng.normal(0, 1, n)
        k = np.linspace(80, 6, n).astype(int)
        out = np.array([noise[max(0, i - k[i]):i + 1].mean() for i in range(0, n)])
        shape = np.sin(np.pi * t / t[-1]) ** 1.5
        return out * shape * (0.9 if kind == "whoosh" else 0.6)
    if kind == "bass":
        n = int(SR * 0.7); t = np.arange(n) / SR
        f = 80 * np.exp(-t * 6) + 42
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.002, 5) * 1.1
    if kind in ("tick", "tick_soft"):
        n = int(SR * 0.05); t = np.arange(n) / SR
        return np.sin(2 * np.pi * 1900 * t) * env(n, 0.001, 70) * (0.35 if kind == "tick" else 0.15)
    if kind == "key":
        n = int(SR * 0.04)
        x = rng.normal(0, 1, n); x = x - np.convolve(x, np.ones(6) / 6, "same")
        return x * env(n, 0.0005, 90) * 0.5
    if kind == "enter":
        n = int(SR * 0.09)
        x = rng.normal(0, 1, n); x = np.convolve(x, np.ones(4) / 4, "same")
        return x * env(n, 0.001, 40) * 0.8
    if kind == "pop":
        n = int(SR * 0.12); t = np.arange(n) / SR
        return np.sin(2 * np.pi * (500 + 900 * np.exp(-t * 40)) * t) * env(n, 0.001, 30) * 0.5
    if kind == "glitch":
        n = int(SR * 0.25)
        x = np.sign(np.sin(2 * np.pi * 180 * np.arange(n) / SR)) * (rng.random(n) > 0.4)
        return x * env(n, 0.001, 9) * 0.25
    return np.zeros(1)


def build_audio(src, cues, dur, gain_db, out_wav):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(src), "-vn", "-ac", "1", "-ar", str(SR),
                        "-f", "s16le", "-"], capture_output=True)
    raw = r.stdout if r.returncode == 0 else b""   # video without audio still works
    voice = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    n = max(len(voice), int(dur * SR))
    sfx = np.zeros(n, np.float32)
    rng = np.random.default_rng(9)
    cache = {}
    for t, kind in cues:
        if kind not in cache:
            cache[kind] = synth(kind, rng).astype(np.float32)
        s = cache[kind]; a = int(t * SR)
        if 0 <= a < n:
            m = min(len(s), n - a); sfx[a:a + m] += s[:m]
    g = 10 ** (gain_db / 20)
    mix = np.zeros(n, np.float32); mix[:len(voice)] += voice; mix += sfx * g
    mix = np.clip(mix, -1, 1)
    with wave.open(str(out_wav), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())


