# memorywire graph — the trust graph

See an agent's memory as a picture: which memories are clean, which came from untrusted sources,
and the **blast radius** of any one source — every memory it planted.

```bash
memorywire graph --agent my-agent --store sqlite-vec://./mem.db --report out.html
```

Open `out.html` in any browser. It's a **single self-contained file** — inline SVG, no server, no
CDN, no external calls — and it's hardened against attacker-controlled memory content.

## What you see

- **Circles = memories**, colored by the recovery classifier's verdict:
  - green = clean · amber (dashed ring) = quarantined for review · red (X) = purged, untrusted origin
- **Squares = sources**, gray with a **green ring (trusted origin)** or **red ring (untrusted)**.
- **Edges = provenance** — a source links to the memories it wrote. *(Provenance, not causal
  influence: it shows which source wrote which memory, not that one memory influenced another.)*

## The interaction

Click an **untrusted source** (red-ringed square) → its blast radius lights up: every memory it
planted. Then hit **Purge by provenance** → those memories collapse and the counts tick down. This
is origin-based purge (what `recover` does), *not* content detection.

Directives hidden inside *trusted* memories (the entangled case) are **not** auto-removed — they're
quarantined for a human. The graph shows them amber.

## Flags

`--report <path>` (output HTML) · `--trusted user,system` · `--title "..."` · `--agent` / `--store`.

Colors are colorblind-safe and trust is encoded by shape as well as hue, so the graph survives
grayscale, color-vision deficiency, and GIF compression.
