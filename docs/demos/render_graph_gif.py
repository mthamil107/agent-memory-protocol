"""Render docs/demos/trust-graph.gif — the trust-graph launch hero.

Three acts, matching the `memorywire graph` HTML's visual language (colorblind-safe palette +
shape encoding): settle -> click the untrusted source, blast radius lights up -> purge by
provenance, poison collapses. Deterministic Pillow renderer (no browser needed).

    .venv/Scripts/python.exe docs/demos/render_graph_gif.py
"""
from __future__ import annotations

import math
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BG = (15, 17, 21)
INK = (230, 230, 230)
MUTED = (154, 160, 170)
CLEAN = (0, 158, 115)
QUAR = (194, 132, 0)
PURGE = (204, 51, 17)
SOURCE = (138, 145, 162)
HI = (70, 145, 207)
GREEN_RING = CLEAN
RED_RING = PURGE
W, H = 960, 620
FPS = 13
FRAME_MS = int(round(1000 / FPS))


def _font(paths, size):
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


F_TITLE = _font([r"C:\Windows\Fonts\segoeuib.ttf", r"C:\Windows\Fonts\arialbd.ttf"], 26)
F_CAP = _font([r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf"], 20)
F_SM = _font([r"C:\Windows\Fonts\segoeui.ttf"], 14)
F_MONO = _font([r"C:\Windows\Fonts\CascadiaMono.ttf", r"C:\Windows\Fonts\consola.ttf"], 15)

# --- scenario: one trusted source (user) + one untrusted (web_page) -------------------
# node = dict(x, y, trust, label)
USER = (250, 330)
WEB = (712, 320)


def _arc(cx, cy, r, angles):
    return [(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))) for a in angles]


user_mem = _arc(*USER, 140, [200, 243, 286, 329, 12, 55, 98])
web_mem = _arc(*WEB, 118, [205, 255, 305, 355])

MEMORIES = (
    [{"pos": p, "trust": "clean", "src": "user"} for p in user_mem[:6]]
    + [{"pos": user_mem[6], "trust": "quarantine", "src": "user"}]
    + [{"pos": p, "trust": "purge", "src": "web_page"} for p in web_mem]
)
SOURCES = {"user": {"pos": USER, "trusted": True}, "web_page": {"pos": WEB, "trusted": False}}
EDGES = [(m["src"], i) for i, m in enumerate(MEMORIES)]


def lerp(a, b, t):
    return a + (b - a) * t


def blend(c, t):  # fade a color toward BG by (1-t)
    return tuple(int(lerp(BG[i], c[i], t)) for i in range(3))


def draw_frame(alpha, *, hi=False, purged=0.0, caption="", cap_color=INK, counts=None):
    """alpha: node fade-in 0..1; hi: blast highlight on web_page; purged: 0..1 collapse of red."""
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    # title
    d.text((28, 20), "memorywire — an agent's memory under attack", font=F_TITLE, fill=INK)

    def dim_for(src):
        if hi:
            return 1.0 if src == "web_page" else 0.28
        return 1.0

    # edges
    for src, i in EDGES:
        m = MEMORIES[i]
        sp = SOURCES[src]["pos"]
        mp = m["pos"]
        on = hi and src == "web_page"
        a = alpha * dim_for(src)
        if m["trust"] == "purge":
            a *= (1 - purged)
        col = blend(HI if on else (42, 45, 52), a)
        d.line([sp, mp], fill=col, width=2 if on else 1)

    # memories
    for m in MEMORIES:
        x, y = m["pos"]
        a = alpha * dim_for(m["src"])
        r = 10
        if m["trust"] == "purge":
            a *= (1 - purged)
            r = int(10 * (1 - purged * 0.9))
        if a <= 0.02 or r <= 0:
            continue
        col = blend({"clean": CLEAN, "quarantine": QUAR, "purge": PURGE}[m["trust"]], a)
        if hi and m["src"] == "web_page":
            d.ellipse((x - r - 3, y - r - 3, x + r + 3, y + r + 3), outline=blend(HI, a), width=3)
        d.ellipse((x - r, y - r, x + r, y + r), fill=col, outline=blend(BG, a), width=2)
        if m["trust"] == "purge":
            xb = blend(BG, a)
            d.line((x - r * .5, y - r * .5, x + r * .5, y + r * .5), fill=xb, width=2)
            d.line((x + r * .5, y - r * .5, x - r * .5, y + r * .5), fill=xb, width=2)
        if m["trust"] == "quarantine":  # dashed ring (approx: 8 arc segments)
            for seg in range(0, 360, 30):
                d.arc((x - r - 3, y - r - 3, x + r + 3, y + r + 3), seg, seg + 18, fill=blend(QUAR, a), width=2)

    # sources (squares with trust ring + label)
    for name, s in SOURCES.items():
        x, y = s["pos"]
        a = alpha * dim_for(name)
        if a <= 0.02:
            continue
        ring = blend(HI if (hi and name == "web_page") else (GREEN_RING if s["trusted"] else RED_RING), a)
        d.rounded_rectangle((x - 11, y - 11, x + 11, y + 11), radius=3,
                            fill=blend(SOURCE, a), outline=ring, width=3)
        d.text((x, y + 18), name, font=F_SM, fill=blend(MUTED, a), anchor="ma")
        if not s["trusted"] and a > 0.5:
            d.text((x, y - 34), "untrusted origin", font=F_SM, fill=blend(RED_RING, a), anchor="ma")

    # legend
    lx, ly = 28, H - 92
    items = [(CLEAN, f"clean ({counts['clean']})" if counts else "clean"),
             (QUAR, f"quarantined ({counts['quarantine']})" if counts else "quarantined"),
             (PURGE, f"purged ({counts['purge']})" if counts else "purged")]
    for col, lab in items:
        d.ellipse((lx, ly, lx + 12, ly + 12), fill=col)
        d.text((lx + 18, ly - 2), lab, font=F_SM, fill=MUTED)
        lx += 26 + d.textlength(lab, font=F_SM) + 18

    # caption
    if caption:
        d.text((W / 2, H - 42), caption, font=F_CAP, fill=cap_color, anchor="ma")
    return img


def main():
    frames, durs = [], []

    def hold(img, n):
        for _ in range(n):
            frames.append(img)
            durs.append(FRAME_MS)

    C_ALL = {"clean": 6, "quarantine": 1, "purge": 4}
    C_CLEAN = {"clean": 6, "quarantine": 1, "purge": 0}

    # Act 1 — settle (fade in)
    for f in range(14):
        hold(draw_frame(f / 13, caption="an agent's long-term memory", counts=C_ALL), 1)
    hold(draw_frame(1, caption="an agent's long-term memory", counts=C_ALL), 8)

    # Act 2 — blast radius
    for f in range(10):
        t = f / 9
        hold(draw_frame(1, hi=True, caption="click the untrusted source → its blast radius",
                        counts=C_ALL), 1)
    hold(draw_frame(1, hi=True, caption="every memory the poisoned source planted", counts=C_ALL), 18)

    # Act 3 — purge
    for f in range(14):
        t = f / 13
        cnt = {"clean": 6, "quarantine": 1, "purge": max(0, round(4 * (1 - t)))}
        hold(draw_frame(1, hi=True, purged=t, caption="purge by provenance  (origin-based, not detection)",
                        cap_color=INK, counts=cnt), 1)
    hold(draw_frame(1, hi=False, purged=1, caption="poison purged · benign kept · hidden directive quarantined for a human",
                    cap_color=CLEAN, counts=C_CLEAN), 34)

    pal = frames[0].quantize(colors=64, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    q = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in frames]
    out = Path("docs/demos/trust-graph.gif")
    q[0].save(out, save_all=True, append_images=q[1:], duration=durs, loop=0, optimize=True, disposal=1)
    print(f"wrote {out} ({out.stat().st_size/1024:.1f} KB, {len(frames)} frames, {sum(durs)/1000:.1f}s)")


if __name__ == "__main__":
    os.chdir(Path(__file__).resolve().parents[2])
    main()
