"""The beat library. Every beat in graphics.json has a "type" that maps to one method here.

Each beat draws on two layers:
  back  - drawn BEHIND the speaker (the depth mask hides it where the person is)
  front - drawn on top of everything

Coordinates are for a 1080x1920 frame. On a typical talking head the free wall
above the head is roughly y 0-760; big words go around y 700 so the head overlaps them."""
import math
import numpy as np
from PIL import Image, ImageDraw
from .fx import (clamp, lerp, ease_out_expo, ease_out_back, ease_in_out_cubic, envelope,
                 hexrgb, font, text_img, text_size, paste, paste_tl, ghost_paste, card, pill)

W, H = 1080, 1920
TRACK = (26, 31, 38)       # solid colour used for tracks inside cards


class Beats:
    def __init__(self, cfg, fonts, cuts):
        col = cfg.get("colors", {})
        g = lambda k, d: hexrgb(col.get(k, d))
        self.BG, self.CY, self.OR = g("bg", "#0D1117"), g("cyan", "#00F5D4"), g("orange", "#FF6B00")
        self.TX, self.MU, self.RD = g("text", "#F0F6FC"), g("muted", "#8B949E"), g("red", "#FF4D4D")
        self.FB, self.FBo, self.FM, self.FMr = fonts["black"], fonts["bold"], fonts["mono"], fonts["mono_regular"]
        self.beats = sorted(cfg.get("beats", []), key=lambda b: b["start"])
        self.cuts = cuts
        self.total = 1.0
        self.amb = cfg.get("ambient", {"from": 0.0, "grid": True, "particles": True, "pops": True})
        cam = cfg.get("camera", {})
        self.anchor = cam.get("anchor", [540, 860])
        self.punch_z = cam.get("punch_zoom", 1.06)
        self.punch_t = cam.get("punch_time", 0.35)
        self.settle_z = cam.get("settle_zoom", 1.025)
        rng = np.random.default_rng(4)
        self.parts = [(rng.uniform(150, 930), rng.uniform(0, 1), rng.uniform(4, 11),
                       rng.uniform(0.7, 1.6), rng.choice([0, 1, 1])) for _ in range(46)]
        self.cues = []
        for b in self.beats:
            getattr(self, "cue_" + b["type"], lambda b: None)(b)
            if not hasattr(self, "draw_" + b["type"]):
                raise SystemExit(f"Beat type '{b['type']}' nahi pehchana. Dekho examples/graphics.example.json")

    # ---------------------------------------------------------- frame logic
    def active(self, t):
        return [b for b in self.beats if b["start"] <= t < b["end"]]

    def zoom(self, t):
        for b in self.beats:
            if b["type"] == "push_in" and b["start"] <= t < b["end"]:
                z0, z1 = b.get("zoom", [1.0, 1.12])
                return lerp(z0, z1, ease_in_out_cubic((t - b["start"]) / (b["end"] - b["start"])))
        last = None
        for b in self.beats:
            if b.get("punch", b["type"] != "push_in") and b["start"] <= t:
                last = b
        if not last:
            return 1.0
        u = t - last["start"]
        if u < self.punch_t:
            return lerp(1.0, self.punch_z, ease_out_expo(u / self.punch_t))
        span = max(0.5, last["end"] - last["start"] - self.punch_t)
        return lerp(self.punch_z, self.settle_z, ease_in_out_cubic((u - self.punch_t) / span))

    def draw(self, t, back, front, frame_rgb):
        self.ambient(t, back)
        for b in self.active(t):
            fn = getattr(self, "draw_" + b["type"])
            if b["type"] == "devices":
                fn(t, b, back, front, frame_rgb)
            else:
                fn(t, b, back, front)

    # ---------------------------------------------------------- ambient
    def ambient(self, t, back):
        a0 = self.amb.get("from", 0.0)
        if t < a0 or self.amb.get("off"):
            return
        a = clamp((t - a0) / 0.6)
        d = ImageDraw.Draw(back)
        if self.amb.get("grid", True):
            off = (t * 18) % 60
            for x in range(0, W, 60):
                d.line([(x, 0), (x, 780)], fill=self.CY[:3] + (int(16 * a),), width=1)
            for y in range(int(-60 + off), 780, 60):
                d.line([(0, y), (W, y)], fill=self.CY[:3] + (int(16 * a),), width=1)
        if self.amb.get("particles", True):
            for x, ph, r, sp, kind in self.parts:
                p = (ph + t * 0.12 * sp) % 1.0
                y = 1150 - p * 1200
                xx = x + math.sin(t * 1.3 + ph * 9) * 18
                al = int(200 * a * math.sin(math.pi * p) ** 1.2)
                c = self.CY if kind else self.OR
                d.ellipse([xx - r * 2.2, y - r * 2.2, xx + r * 2.2, y + r * 2.2], fill=c[:3] + (al // 6,))
                d.ellipse([xx - r * .55, y - r * .55, xx + r * .55, y + r * .55], fill=c[:3] + (al,))
        if self.amb.get("pops", True):
            for k in range(5):
                ph = (t * 0.7 + k * 0.37) % 1.0
                if ph < 0.18:
                    px = 120 + (k * 211) % 840; py = 120 + (k * 137) % 560
                    rr = 10 + ph * 220; al = int(150 * (1 - ph / 0.18) * a)
                    d.ellipse([px - rr, py - rr, px + rr, py + rr], outline=self.CY[:3] + (al,), width=3)

    # ---------------------------------------------------------- push_in (camera only)
    def draw_push_in(self, t, b, back, front):
        pass

    # ---------------------------------------------------------- fast timeline
    def cue_timeline_fast(self, b):
        self.cues.append((b["start"], "whoosh"))

    def draw_timeline_fast(self, t, b, back, front):
        s, e = b["start"], b["end"]
        vis = envelope(t, s, e, 0.3, 0.3)
        y0 = lerp(-420, 150, ease_out_expo((t - s) / 0.6))
        card(front, 70, y0, 940, 380, vis)
        d = ImageDraw.Draw(front); a = int(255 * vis)
        d.text((105, y0 + 28), b.get("label", "TIMELINE · manual edit"), font=font(self.FBo, 30), fill=self.MU[:3] + (a,))
        sp = float(str(b.get("speed", "2.5x")).rstrip("x") or 2.5)
        for row in range(4):
            yy = y0 + 92 + row * 66
            d.rounded_rectangle([105, yy, 975, yy + 50], 8, fill=TRACK + (a,))
            x = 105 - ((t - s) * 260 * sp * (1 + row * .25)) % 160; k = 0
            c = [self.CY, self.OR, (120, 140, 255, 255), (255, 120, 170, 255)][row]
            while x < 975:
                wseg = 60 + ((row * 37 + k * 53) % 110)
                x1, x2 = max(105, x), min(975, x + wseg)
                if x2 > x1:
                    d.rounded_rectangle([x1, yy + 6, x2, yy + 44], 6, fill=c[:3] + (a,))
                x += wseg + 10; k += 1
        ph = 105 + ((t - s) * 900) % 870
        d.line([(ph, y0 + 80), (ph, y0 + 360)], fill=(255, 77, 77, a), width=4)
        for k in range(6):
            sy = y0 + 95 + k * 45; sx = ph - 40 - k * 9
            d.line([(sx - 120, sy), (sx, sy)], fill=(255, 255, 255, int(60 * vis)), width=2)
        paste(front, pill(str(b.get("speed", "2.5x")), self.FB, 34, self.BG, self.OR), 920, y0 + 46, vis)

    # ---------------------------------------------------------- kinetic list
    def cue_kinetic_list(self, b):
        for t, _ in b["items"]:
            self.cues += [(t, "whoosh_s"), (t + 0.28, "tick")]

    def draw_kinetic_list(self, t, b, back, front):
        items = b["items"]
        vis_all = envelope(t, b["start"], b["end"], 0.05, 0.4)
        shown = [it for it in items if it[0] <= t]
        n = len(shown)
        for i, (t0, label) in enumerate(shown):
            slot = n - 1 - i
            ty = 640 - slot * 118
            prev_ty = 640 - max(0, slot - 1) * 118
            lift = ease_out_expo((t - shown[i + 1][0]) / 0.35) if i + 1 < n else 1
            yy = lerp(prev_ty, ty, lift) if slot > 0 else ty
            num = pill(f"{i + 1:02d}", self.FM, 34, self.BG, self.OR if i % 2 else self.CY, 16, 8)
            im = text_img(label, self.FB, 78, self.TX[:3] + (255,), True, 0)
            def pos(tt, _t0=t0, _yy=yy, _w=im.width):
                return (lerp(-500, 120 + _w / 2, ease_out_back((tt - _t0) / 0.5)),
                        lerp(_yy + 160, _yy, ease_out_expo((tt - _t0) / 0.5)))
            x, y = pos(t)
            d = ImageDraw.Draw(front)
            a = int(225 * vis_all * clamp((t - t0) / 0.15))
            d.rounded_rectangle([x - im.width / 2 - 70, y - 54, x + im.width / 2 - 10, y + 54], 22, fill=self.BG[:3] + (a,))
            ghost_paste(front, im, pos, t, vis_all)
            paste(front, num, x - im.width / 2 - 28, y, vis_all * clamp((t - t0) / 0.2))

    # ---------------------------------------------------------- clock behind the head
    def cue_clock(self, b):
        self.cues.append((b["start"], "bass"))
        for k in range(int((b["end"] - b["start"]) * 4)):
            self.cues.append((b["start"] + 0.3 + k * 0.25, "tick_soft"))

    def draw_clock(self, t, b, back, front):
        c0, c1 = b["start"], b["end"]
        vis = envelope(t, c0, c1, 0.2, 0.4)
        rise = ease_out_expo((t - c0) / 0.7)
        cx, cy, R = 540, lerp(1150, 560, rise), 330
        d = ImageDraw.Draw(back); a = int(255 * vis)
        d.ellipse([cx - R - 20, cy - R - 20, cx + R + 20, cy + R + 20], fill=self.CY[:3] + (int(40 * vis),))
        d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=self.BG[:3] + (int(235 * vis),), outline=self.CY[:3] + (a,), width=10)
        for k in range(60):
            ang = k / 60 * 2 * math.pi; L = 40 if k % 5 == 0 else 16
            d.line([(cx + math.sin(ang) * (R - 18), cy - math.cos(ang) * (R - 18)),
                    (cx + math.sin(ang) * (R - 18 - L), cy - math.cos(ang) * (R - 18 - L))],
                   fill=self.TX[:3] + (int(220 * vis),), width=6 if k % 5 == 0 else 3)
        spin = (t - c0) * 2 * math.pi * 1.6
        d.line([(cx, cy), (cx + math.sin(spin / 12) * R * .5, cy - math.cos(spin / 12) * R * .5)], fill=self.TX[:3] + (a,), width=14)
        d.line([(cx, cy), (cx + math.sin(spin) * R * .78, cy - math.cos(spin) * R * .78)], fill=self.OR[:3] + (a,), width=8)
        d.ellipse([cx - 16, cy - 16, cx + 16, cy + 16], fill=self.OR[:3] + (a,))
        if b.get("label"):
            lab = text_img(b["label"], self.FB, 92, self.OR[:3] + (255,), True, 0)
            paste(front, lab, 540, 120, vis * clamp((t - c0 - 0.4) / 0.3), ease_out_back((t - c0 - 0.4) / 0.4))
        u = clamp((t - c0 - 0.5) / 2.2)
        sx = lerp(cx + 80, 170, ease_in_out_cubic(u))
        sy = lerp(cy - 60, 1240, ease_in_out_cubic(u)) - math.sin(u * math.pi) * 200
        d2 = ImageDraw.Draw(front if u > 0.35 else back)
        al = int(255 * vis * clamp(u / 0.1)); r2 = 64
        d2.ellipse([sx - r2, sy - r2, sx + r2, sy + r2], fill=self.BG[:3] + (al,), outline=self.CY[:3] + (al,), width=6)
        sp2 = (t - c0) * 2 * math.pi * 3
        d2.line([(sx, sy), (sx + math.sin(sp2) * 44, sy - math.cos(sp2) * 44)], fill=self.OR[:3] + (al,), width=6)
        mins = int(clamp((t - c0) / max(.1, c1 - c0)) * b.get("minutes", 120))
        d2.text((sx - 54, sy + r2 + 8), f"{mins // 60}:{mins % 60:02d}:00", font=font(self.FM, 28), fill=self.TX[:3] + (al,))

    # ---------------------------------------------------------- flat graph
    def cue_flat_graph(self, b):
        self.cues.append((b["start"], "glitch"))

    def draw_flat_graph(self, t, b, back, front):
        g0, g1 = b["start"], b["end"]
        vis = envelope(t, g0, g1, 0.15, 0.3)
        glitch = (t - g0) % 1.1 < 0.18
        x0, y0 = 90 + (math.sin(t * 90) * 10 if glitch else 0), 140
        card(front, x0, y0, 900, 470, vis, border=self.RD[:3] + (170,))
        d = ImageDraw.Draw(front); a = int(255 * vis)
        d.text((x0 + 40, y0 + 30), b.get("title", "VIEWS"), font=font(self.FB, 44), fill=self.TX[:3] + (a,))
        d.text((x0 + 640, y0 + 30), b.get("value", "+0%"), font=font(self.FB, 52), fill=self.RD[:3] + (a,))
        pts, prog = [], ease_out_expo((t - g0) / 1.0)
        for k in range(41):
            xx = x0 + 50 + k * 20
            if xx > x0 + 50 + prog * 800:
                break
            pts.append((xx, y0 + 380 - (60 if k < 6 else 0) * (k / 6) - math.sin(k * 1.7) * 4))
        if len(pts) > 1:
            d.line(pts, fill=self.RD[:3] + (a,), width=8, joint="curve")
        if glitch:
            for k in range(5):
                yy = y0 + 60 + k * 80
                d.rectangle([x0, yy, x0 + 900, yy + 10], fill=(self.CY if k % 2 else self.RD)[:3] + (a,))
        if b.get("label"):
            paste(front, text_img(b["label"], self.FB, 70, self.TX[:3] + (255,), True), 540, 690,
                  vis * clamp((t - g0 - 0.5) / 0.3))

    # ---------------------------------------------------------- countdown / big text behind head
    def cue_countdown(self, b):
        self.cues.append((b["start"], "bass"))
        for k in range(int((b["end"] - b["start"]) * 2)):
            self.cues.append((b["start"] + 0.4 + k * 0.5, "tick"))

    def draw_countdown(self, t, b, back, front):
        s, e = b["start"], b["end"]
        vis = envelope(t, s, e, 0.08, 0.3)
        sh = math.sin(t * 70) * 6 * clamp(1 - (t - s) / 0.5)
        d = ImageDraw.Draw(back)
        for k in range(9):
            d.line([(40, 200 + k * 70), (1040, 200 + k * 70)], fill=self.CY[:3] + (int(40 * vis),), width=2)
        im = text_img(b.get("text", "10 SEC"), self.FB, 300, self.CY[:3] + (255,), True, 0, glow=self.CY[:3] + (150,))
        paste(back, im, 540 + sh, b.get("y", 735), vis, ease_out_back((t - s) / 0.5, 1.2))
        start_n = float(b.get("from", 10))
        left = max(0.0, start_n - (t - s) * (start_n / max(1.0, e - s)))
        paste(front, text_img(f"{left:05.2f}", self.FM, 96, self.OR[:3] + (255,), True), 540, 230, vis)
        d2 = ImageDraw.Draw(front); a = int(230 * vis)
        for (x, y, dx, dy) in [(60, 150, 1, 1), (1020, 150, -1, 1), (60, 330, 1, -1), (1020, 330, -1, -1)]:
            d2.line([(x, y), (x + 60 * dx, y)], fill=self.CY[:3] + (a,), width=5)
            d2.line([(x, y), (x, y + 60 * dy)], fill=self.CY[:3] + (a,), width=5)

    # ---------------------------------------------------------- terminal
    def cue_terminal(self, b):
        self.cues.append((b["start"], "whoosh"))
        t0 = b["start"] + 0.9; cmd = b["command"]
        self.cues += [(t0 + k * 0.045, "key") for k in range(0, len(cmd), 2)]
        self.cues.append((t0 + len(cmd) * 0.045 + 0.15, "enter"))

    def draw_terminal(self, t, b, back, front):
        s, e = b["start"], b["end"]
        vis = envelope(t, s, e, 0.1, 0.35)
        x0, w, h = 50, 980, 600
        y0 = lerp(980, 110, ease_out_expo((t - s) / 0.8))
        card(back, x0, y0, w, h, vis, r=22)
        d = ImageDraw.Draw(back); a = int(255 * vis)
        for k, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
            d.ellipse([x0 + 30 + k * 34, y0 + 26, x0 + 52 + k * 34, y0 + 48], fill=c + (a,))
        d.text((x0 + 150, y0 + 22), b.get("title", "Terminal"), font=font(self.FMr, 26), fill=self.MU[:3] + (a,))
        if b.get("badge"):
            bd = pill(b["badge"], self.FB, 34, self.BG, self.CY)
            paste(back, bd, x0 + w - bd.width / 2 - 26, y0 + 37, vis)
        cmd = b["command"]; t0 = s + 0.9
        typed = cmd[:int(clamp((t - t0) / (len(cmd) * 0.045)) * len(cmd))]
        fm = font(self.FM, 34); yy = y0 + 92
        d.text((x0 + 30, yy), b.get("prompt", "$"), font=fm, fill=self.CY[:3] + (a,))
        lines, cur = [], ""
        for word in typed.split(" "):
            cand = (cur + " " + word) if cur else word
            if len(cand) > 40 and cur:
                lines.append(cur); cur = word
            else:
                cur = cand
        lines.append(cur)
        for i, ln in enumerate(lines):
            d.text((x0 + 105, yy + i * 48), ln, font=fm, fill=self.TX[:3] + (a,))
        if len(typed) < len(cmd) and int(t * 3) % 2 == 0:
            cw = fm.getlength(lines[-1]); ly = yy + (len(lines) - 1) * 48
            d.rectangle([x0 + 108 + cw, ly, x0 + 124 + cw, ly + 34], fill=self.CY[:3] + (a,))
        done = t0 + len(cmd) * 0.045 + 0.15
        if t > done:
            py = yy + len(lines) * 48 + 22
            prog = clamp((t - done) / 1.6)
            d.rounded_rectangle([x0 + 30, py, x0 + w - 30, py + 22], 11, fill=(34, 40, 48, a))
            d.rounded_rectangle([x0 + 30, py, x0 + 30 + (w - 60) * prog, py + 22], 11, fill=self.CY[:3] + (a,))
            d.text((x0 + w - 130, py - 40), f"{int(prog * 100):3d}%", font=font(self.FM, 28), fill=self.CY[:3] + (a,))
            hi = b.get("highlight_line", 1)
            for i, ln in enumerate(b.get("output", [])):
                ti = done + 1.0 + i * 0.45
                if t > ti:
                    col = self.OR if i == hi else self.TX
                    d.text((x0 + 30, py + 52 + i * 50), ln, font=font(self.FM if i == hi else self.FMr, 31),
                           fill=col[:3] + (int(a * clamp((t - ti) / 0.2)),))

    # ---------------------------------------------------------- before / after
    def cue_before_after(self, b):
        self.cues += [(b["start"], "whoosh"), (b["start"] + 2.4, "bass")]

    def draw_before_after(self, t, b, back, front):
        s, e = b["start"], b["end"]
        vis = envelope(t, s, e, 0.15, 0.35)
        x0, y0, w = 70, lerp(-400, 110, ease_out_expo((t - s) / 0.6)), 940
        card(front, x0, y0, w, 380, vis)
        d = ImageDraw.Draw(front); a = int(255 * vis); bw = w - 80
        bl, al_ = b.get("before_label", "BEFORE"), b.get("after_label", "AFTER")
        d.text((x0 + 40, y0 + 34), f"{bl}  {b['before']}s", font=font(self.FB, 50), fill=self.MU[:3] + (a,))
        d.rounded_rectangle([x0 + 40, y0 + 92, x0 + 40 + bw, y0 + 152], 12, fill=(110, 118, 129, a))
        collapse = ease_in_out_cubic((t - s - 0.9) / 1.3)
        rng = np.random.default_rng(2)
        for k in range(9):
            bx = x0 + 60 + k * 98 + rng.uniform(0, 30); bwid = rng.uniform(26, 56) * (1 - collapse)
            if bwid > 1:
                d.rectangle([bx, y0 + 96, bx + bwid, y0 + 148], fill=self.RD[:3] + (a,))
        d.text((x0 + 40, y0 + 190), f"{al_}  {b['after']}s", font=font(self.FB, 50), fill=self.CY[:3] + (a,))
        snap = ease_out_back((t - s - 2.2) / 0.5)
        if snap > 0:
            aw = bw * b["after"] / b["before"]
            d.rounded_rectangle([x0 + 40, y0 + 248, x0 + 40 + aw * clamp(snap, 0, 1.08), y0 + 308], 12, fill=self.CY[:3] + (a,))
        if t > s + 2.4:
            pct = b.get("percent", round(100 * (1 - b["after"] / b["before"])))
            shown = int(round(pct * ease_out_expo(clamp((t - s - 2.4) / 0.9))))
            im = text_img(f"-{shown}%", self.FB, 280, self.OR[:3] + (255,), True, glow=self.OR[:3] + (140,))
            ghost_paste(back, im, lambda tt: (lerp(-300, 540, ease_out_back((tt - s - 2.4) / 0.6)), 720), t, vis)

    # ---------------------------------------------------------- device frames
    def cue_devices(self, b):
        self.cues.append((b["start"], "whoosh"))
        self.cues += [(b["start"] + 0.3 + k * 0.22, "pop") for k in range(3)]
        self.cues.append((b["start"] + 2.4, "bass"))

    def draw_devices(self, t, b, back, front, frame_rgb):
        s, e = b["start"], b["end"]
        vis = envelope(t, s, e, 0.15, 0.35)
        d = ImageDraw.Draw(front); src = Image.fromarray(frame_rgb)
        specs = [("9:16", 200, 356), ("1:1", 300, 300), ("16:9", 420, 236)]
        gap = 26; x = (W - sum(w for _, w, _ in specs) - gap * 2) / 2; base = 520
        for i, (lab, w, h) in enumerate(specs):
            u = ease_out_back((t - s - 0.3 - i * 0.22) / 0.5)
            if u <= 0:
                x += w + gap; continue
            yy = base - h + (1 - clamp(u)) * 300
            al = int(255 * vis * clamp(u))
            sw, sh = src.size; ar = w / h
            if sw / sh > ar:
                cw = int(sh * ar); box = ((sw - cw) // 2, 0, (sw - cw) // 2 + cw, sh)
            else:
                ch = int(sw / ar); top = int(sh * 0.22); box = (0, top, sw, min(sh, top + ch))
            thumb = src.crop(box).resize((w - 16, h - 16), Image.BILINEAR).convert("RGBA"); thumb.putalpha(al)
            d.rounded_rectangle([x, yy, x + w, yy + h], 18, fill=self.BG[:3] + (al,), outline=self.CY[:3] + (al,), width=4)
            front.alpha_composite(thumb, (int(x + 8), int(yy + 8)))
            paste(front, pill(lab, self.FB, 28, self.BG, self.OR if i == 1 else self.CY, 16, 6), x + w / 2, yy - 30, vis * clamp(u))
            x += w + gap
        if t > s + 2.3 and b.get("badge", "1 COMMAND"):
            bd = pill(b.get("badge", "1 COMMAND"), self.FB, 64, self.BG, self.CY, 40, 16)
            ghost_paste(front, bd, lambda tt: (lerp(-400, 540, ease_out_back((tt - s - 2.3) / 0.5)), 650), t, vis)

    # ---------------------------------------------------------- word-by-word captions
    def cue_word_captions(self, b):
        self.cues.append((b["start"], "whoosh_s"))

    def draw_word_captions(self, t, b, back, front):
        s, e = b["start"], b["end"]; words = b["words"].split()
        vis = envelope(t, s, e, 0.1, 0.3)
        per = (e - s - 0.3) / len(words)
        idx = min(len(words) - 1, int((t - s) / per)); grp = idx // 3 * 3
        imgs = [text_img(wd, self.FB, 96 if grp + j == idx else 84,
                         (self.CY if grp + j == idx else self.TX)[:3] + (255,), True, 6, (0, 0, 0, 255))
                for j, wd in enumerate(words[grp:grp + 3])]
        x = 540 - (sum(i.width for i in imgs) - 30 * (len(imgs) - 1)) / 2
        for j, im in enumerate(imgs):
            pop = ease_out_back((t - s - (grp + j) * per) / 0.25) if grp + j <= idx else 0
            if pop > 0:
                paste(front, im, x + im.width / 2, b.get("y", 1420), vis, pop)
            x += im.width - 30

    # ---------------------------------------------------------- file dropping into an editor
    def cue_file_import(self, b):
        self.cues += [(b["start"], "whoosh"), (b["start"] + 1.0, "pop")]

    def draw_file_import(self, t, b, back, front):
        s, e = b["start"], b["end"]
        vis = envelope(t, s, e, 0.1, 0.3); u = clamp((t - s) / 0.9)
        x0, y0 = 90, 130
        card(front, x0, y0, 900, 470, vis)
        d = ImageDraw.Draw(front); a = int(255 * vis)
        d.text((x0 + 36, y0 + 26), b.get("title", "Editor  ·  Project"), font=font(self.FBo, 32), fill=self.MU[:3] + (a,))
        d.rounded_rectangle([x0 + 36, y0 + 80, x0 + 300, y0 + 430], 14, outline=(70, 78, 88, a), width=3)
        d.text((x0 + 60, y0 + 96), "BIN", font=font(self.FB, 28), fill=self.MU[:3] + (a,))
        fx_ = lerp(-200, x0 + 168, ease_out_expo(u)); fy_ = lerp(900, y0 + 250, ease_out_expo(u)) - math.sin(u * math.pi) * 180
        d.rounded_rectangle([fx_ - 60, fy_ - 76, fx_ + 60, fy_ + 76], 12, fill=self.TX[:3] + (a,))
        d.polygon([(fx_ + 24, fy_ - 76), (fx_ + 60, fy_ - 40), (fx_ + 24, fy_ - 40)], fill=self.MU[:3] + (a,))
        ext = b.get("ext", ".EDL")
        tw, _ = text_size(ext, self.FB, 36)
        d.text((fx_ - tw / 2, fy_ - 6), ext, font=font(self.FB, 36), fill=self.BG[:3] + (a,))
        fill = clamp((t - s - 1.0) / 1.2)
        for r in range(3):
            yy = y0 + 110 + r * 100
            d.rounded_rectangle([x0 + 330, yy, x0 + 864, yy + 70], 10, fill=TRACK + (a,))
            xx = x0 + 336; k = 0
            c = [self.CY, self.OR, (120, 140, 255, 255)][r]
            while xx < x0 + 336 + 520 * fill:
                ww = 40 + (k * 29 + r * 17) % 70
                d.rounded_rectangle([xx, yy + 8, min(xx + ww, x0 + 858), yy + 62], 6, fill=c[:3] + (a,))
                xx += ww + 6; k += 1
        if fill >= 1 and b.get("done_label", "IMPORTED"):
            ok = pill(b.get("done_label", "IMPORTED"), self.FB, 40, self.BG, self.CY)
            paste(front, ok, 540, 680, vis * clamp((t - s - 2.2) / 0.3), ease_out_back((t - s - 2.2) / 0.3))

    # ---------------------------------------------------------- this video's own timeline
    def cue_this_timeline(self, b):
        self.cues.append((b["start"], "whoosh"))

    def draw_this_timeline(self, t, b, back, front):
        s, e = b["start"], b["end"]; total = self.total
        vis = envelope(t, s, e, 0.15, 0.3)
        x0, y0, w, h = 50, lerp(-420, 130, ease_out_expo((t - s) / 0.6)), 980, 420
        card(front, x0, y0, w, h, vis)
        d = ImageDraw.Draw(front); a = int(255 * vis)
        d.text((x0 + 30, y0 + 22), b.get("title", "timeline"), font=font(self.FBo, 30), fill=self.MU[:3] + (a,))
        tl0, tlw = x0 + 110, w - 140
        for r, (name, kind) in enumerate([("V2", "beats"), ("V1", "cuts"), ("A1", "wave"), ("A2", "sfx")]):
            yy = y0 + 80 + r * 80
            d.text((x0 + 30, yy + 14), name, font=font(self.FM, 28), fill=self.MU[:3] + (a,))
            d.rounded_rectangle([tl0, yy, tl0 + tlw, yy + 62], 8, fill=TRACK + (a,))
            if kind == "cuts" and self.cuts:
                acc = 0
                for i, p in enumerate(self.cuts):
                    x1 = tl0 + acc / total * tlw; x2 = tl0 + (acc + p) / total * tlw
                    d.rectangle([x1 + 1, yy + 6, x2 - 1, yy + 56], fill=(self.CY if i % 2 else (0, 190, 165, 255))[:3] + (a,))
                    acc += p
            elif kind == "beats":
                for bb in self.beats:
                    if bb["type"] == "push_in":
                        continue
                    x1 = tl0 + bb["start"] / total * tlw; x2 = tl0 + bb["end"] / total * tlw
                    d.rounded_rectangle([x1 + 2, yy + 8, max(x1 + 6, x2 - 2), yy + 54], 6, fill=self.OR[:3] + (a,))
            elif kind == "wave":
                for k in range(0, int(tlw), 6):
                    amp = 22 * abs(math.sin(k * 0.21) * math.cos(k * 0.047))
                    d.line([(tl0 + k, yy + 31 - amp), (tl0 + k, yy + 31 + amp)], fill=(120, 200, 255, a), width=3)
            else:
                for ct, _ in self.cues:
                    xx = tl0 + ct / total * tlw
                    d.line([(xx, yy + 10), (xx, yy + 52)], fill=self.OR[:3] + (a,), width=2)
        ph = tl0 + (t / total) * tlw
        d.line([(ph, y0 + 70), (ph, y0 + 400)], fill=(255, 77, 77, a), width=4)
        d.polygon([(ph - 12, y0 + 64), (ph + 12, y0 + 64), (ph, y0 + 80)], fill=(255, 77, 77, a))
        if t > s + 0.6 and b.get("label", "THIS REEL"):
            bob = math.sin(t * 6) * 8
            lab = pill(b.get("label", "THIS REEL"), self.FB, 56, self.BG, self.OR, 34, 14)
            paste(front, lab, 540, 680 + bob, vis * clamp((t - s - 0.6) / 0.25), ease_out_back((t - s - 0.6) / 0.35))
            d.polygon([(ph - 22, y0 + h + 10 + bob), (ph + 22, y0 + h + 10 + bob), (ph, y0 + h - 22 + bob)], fill=self.OR[:3] + (a,))

    # ---------------------------------------------------------- repo card
    def cue_repo_card(self, b):
        self.cues.append((b["start"], "whoosh"))

    def draw_repo_card(self, t, b, back, front):
        s, e = b["start"], b["end"]
        gv = envelope(t, s, e, 0.15, 0.3)
        x0, y0 = 90, lerp(-400, 170, ease_out_expo((t - s) / 0.6))
        card(front, x0, y0, 900, 330, gv)
        d = ImageDraw.Draw(front); a = int(255 * gv)
        d.rounded_rectangle([x0 + 40, y0 + 46, x0 + 96, y0 + 112], 8, outline=self.TX[:3] + (a,), width=5)
        d.line([(x0 + 56, y0 + 46), (x0 + 56, y0 + 112)], fill=self.TX[:3] + (a,), width=5)
        d.text((x0 + 120, y0 + 40), b.get("host", "GitHub"), font=font(self.FB, 40), fill=self.MU[:3] + (a,))
        d.text((x0 + 120, y0 + 96), b["repo"], font=font(self.FBo, 40), fill=self.TX[:3] + (a,))
        bx = x0 + 40
        for i, txt in enumerate(b.get("badges", ["FREE", "OPEN SOURCE"])):
            p = pill(txt, self.FB, 44, self.BG, self.OR if i % 2 else self.CY, 22, 10)
            pop = ease_out_back((t - s - 0.5 - i * 0.18) / 0.35)
            if pop > 0:
                paste(front, p, bx + p.width / 2, y0 + 230, gv * clamp(pop), pop)
            bx += p.width + 18

    # ---------------------------------------------------------- huge word behind the head (CTA)
    def cue_big_word(self, b):
        self.cues.append((b["start"], "bass"))

    def draw_big_word(self, t, b, back, front):
        s, e = b["start"], b["end"]; u = t - s
        vis = envelope(t, s, e, 0.15, 0.3)
        if b.get("top"):
            top = text_img(b["top"], self.FB, 76, self.TX[:3] + (255,), True)
            paste(front, top, 540, 330, vis * clamp(u / 0.3), ease_out_back(u / 0.4))
        col = self.CY if b.get("color") == "cyan" else self.OR
        pulse = 1 + 0.04 * math.sin(max(0, u - 0.6) * 6)
        im = text_img(b["word"], self.FB, b.get("size", 330), col[:3] + (255,), True, 0, glow=col[:3] + (170,))
        ghost_paste(back, im, lambda tt: (lerp(-500, 540, ease_out_back((tt - s) / 0.6)),
                                          lerp(900, b.get("y", 690), ease_out_expo((tt - s) / 0.6))),
                    t, vis, lambda tt: pulse)
