#!/usr/bin/env python3
"""Generate the AES-CTR roofline SVG for the single-core-aes post."""
import math

# ---------------- data ----------------
CLOCK = 4.4e9
GIB = 2**30
def bcyc_to_gibs(b): return b * CLOCK / GIB
def gbs_to_gibs(g): return g * 1e9 / GIB

# diagonals: (name, effective per-core bandwidth GiB/s, color, label_x)
BLUES = ["#86b6ef", "#3987e5", "#256abf", "#184f95", "#0d366b"]
diagonals = [
    ("L1D ≈ 524 GiB/s",             bcyc_to_gibs(128), BLUES[0], 0.062),
    ("L2 ≈ 262 GiB/s",              bcyc_to_gibs(64),  BLUES[1], 0.090),
    ("L3 ≈ 131 GiB/s",              bcyc_to_gibs(32),  BLUES[2], 0.130),
    ("DRAM · 1 core ≈ 47 GiB/s",   gbs_to_gibs(50),   BLUES[3], 0.10),
    ("", gbs_to_gibs(100/8), BLUES[4], None),  # named by its dot annotation
]
# compute roofs: (label, GiB/s, main?)
roofs = [
    ("VAES-512 roof · 52.4 GiB/s", bcyc_to_gibs(64/5.0),  True),
    ("VAES-256 · 26.2 GiB/s",      bcyc_to_gibs(32/5.0),  False),
    ("AES-NI 128-bit · 13.1 GiB/s", bcyc_to_gibs(16/5.0), False),
]
X_KERNEL = 0.5     # 1 read + 1 write per encrypted byte
X_RFO = 1/3        # with write-allocate stores
MEASURED = 49.08
PRED_1CORE = gbs_to_gibs(50) * X_KERNEL
PRED_8SHARE = gbs_to_gibs(100/8) * X_KERNEL

# ---------------- geometry ----------------
W_SVG, H_SVG = 960, 660
L, R, T, B = 64, 930, 96, 572
XMIN, XMAX = 0.04, 8.0
YMIN, YMAX = 3.0, 800.0
LXMIN, LXMAX = math.log10(XMIN), math.log10(XMAX)
LYMIN, LYMAX = math.log10(YMIN), math.log10(YMAX)

def px(x): return L + (math.log10(x) - LXMIN) / (LXMAX - LXMIN) * (R - L)
def py(y): return B - (math.log10(y) - LYMIN) / (LYMAX - LYMIN) * (B - T)

# screen angle of a slope-1 line in log-log space
per_dec_x = (R - L) / (LXMAX - LXMIN)
per_dec_y = (B - T) / (LYMAX - LYMIN)
ANGLE = -math.degrees(math.atan2(per_dec_y, per_dec_x))

INK, INK2, MUTED, GRID, AXIS = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
ACCENT = "#eb6834"
FONT = "system-ui, -apple-system, 'Segoe UI', 'Helvetica Neue', sans-serif"

s = []
s.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W_SVG}" height="{H_SVG}" '
         f'viewBox="0 0 {W_SVG} {H_SVG}" font-family="{FONT}">')
s.append(f'<rect width="{W_SVG}" height="{H_SVG}" fill="#fcfcfb"/>')

# title + subtitle
s.append(f'<text paint-order="stroke" stroke="#fcfcfb" stroke-width="4" stroke-linejoin="round" x="{L}" y="34" font-size="19" font-weight="700" fill="{INK}">'
         f'Roofline — AES-128-CTR on one Zen 5 core (~4.4 GHz)</text>')
s.append(f'<text paint-order="stroke" stroke="#fcfcfb" stroke-width="4" stroke-linejoin="round" x="{L}" y="56" font-size="13" fill="{INK2}">Diagonals: per-core bandwidth of each memory level (1:1 read:write stream). '
         f'Horizontals: AES compute roofs.</text>')
s.append(f'<text paint-order="stroke" stroke="#fcfcfb" stroke-width="4" stroke-linejoin="round" x="{L}" y="74" font-size="13" fill="{INK2}">Zero reuse pins the cipher to one intensity — it can only ever move vertically.</text>')

# clip for plot area
s.append(f'<clipPath id="plot"><rect x="{L}" y="{T}" width="{R-L}" height="{B-T}"/></clipPath>')

# gridlines + ticks
xticks = [0.05, 0.1, 0.2, 0.5, 1, 2, 5]
yticks = [5, 10, 20, 50, 100, 200, 500]
for xt in xticks:
    s.append(f'<line x1="{px(xt):.1f}" y1="{T}" x2="{px(xt):.1f}" y2="{B}" stroke="{GRID}" stroke-width="1"/>')
    lab = f"{xt:g}"
    s.append(f'<text paint-order="stroke" stroke="#fcfcfb" stroke-width="4" stroke-linejoin="round" x="{px(xt):.1f}" y="{B+18}" font-size="11.5" fill="{MUTED}" text-anchor="middle">{lab}</text>')
for yt in yticks:
    s.append(f'<line x1="{L}" y1="{py(yt):.1f}" x2="{R}" y2="{py(yt):.1f}" stroke="{GRID}" stroke-width="1"/>')
    s.append(f'<text paint-order="stroke" stroke="#fcfcfb" stroke-width="4" stroke-linejoin="round" x="{L-8}" y="{py(yt)+4:.1f}" font-size="11.5" fill="{MUTED}" text-anchor="end">{yt:g}</text>')

# axes
s.append(f'<line x1="{L}" y1="{B}" x2="{R}" y2="{B}" stroke="{AXIS}" stroke-width="1.5"/>')
s.append(f'<line x1="{L}" y1="{T}" x2="{L}" y2="{B}" stroke="{AXIS}" stroke-width="1.5"/>')
s.append(f'<text paint-order="stroke" stroke="#fcfcfb" stroke-width="4" stroke-linejoin="round" x="{(L+R)/2:.0f}" y="{B+42}" font-size="13" fill="{INK2}" text-anchor="middle">'
         f'bytes encrypted per byte of memory traffic (arithmetic intensity)</text>')
s.append(f'<text paint-order="stroke" stroke="#fcfcfb" stroke-width="4" stroke-linejoin="round" x="20" y="{(T+B)/2:.0f}" font-size="13" fill="{INK2}" text-anchor="middle" '
         f'transform="rotate(-90 20 {(T+B)/2:.0f})">ciphertext GiB/s</text>')

# ---------------- bandwidth diagonals ----------------
s.append(f'<g clip-path="url(#plot)">')
for name, bw, color, xl in diagonals:
    # draw from XMIN..XMAX clipped
    s.append(f'<line x1="{px(XMIN):.1f}" y1="{py(bw*XMIN):.1f}" x2="{px(XMAX):.1f}" y2="{py(bw*XMAX):.1f}" '
             f'stroke="{color}" stroke-width="2"/>')
s.append('</g>')
# diagonal labels (drawn outside clip so they never get cut)
for name, bw, color, xl in diagonals:
    if not name:
        continue
    lx, ly = px(xl), py(bw * xl) - 7
    s.append(f'<text paint-order="stroke" stroke="#fcfcfb" stroke-width="4" stroke-linejoin="round" x="{lx:.1f}" y="{ly:.1f}" font-size="12" fill="{INK2}" '
             f'transform="rotate({ANGLE:.2f} {lx:.1f} {ly:.1f})">{name}</text>')

# ---------------- compute roofs ----------------
for label, y, main in roofs:
    if main:
        s.append(f'<line x1="{L}" y1="{py(y):.1f}" x2="{R}" y2="{py(y):.1f}" stroke="{INK}" stroke-width="2"/>')
        s.append(f'<text paint-order="stroke" stroke="#fcfcfb" stroke-width="4" stroke-linejoin="round" x="{R-6}" y="{py(y)-7:.1f}" font-size="12.5" font-weight="600" fill="{INK}" text-anchor="end">{label}</text>')
    else:
        s.append(f'<line x1="{L}" y1="{py(y):.1f}" x2="{R}" y2="{py(y):.1f}" stroke="{MUTED}" '
                 f'stroke-width="1.5" stroke-dasharray="7 5"/>')
        s.append(f'<text paint-order="stroke" stroke="#fcfcfb" stroke-width="4" stroke-linejoin="round" x="{R-6}" y="{py(y)-7:.1f}" font-size="12" fill="{MUTED}" text-anchor="end">{label}</text>')

# ---------------- pinned-intensity verticals ----------------
xk = px(X_KERNEL)
s.append(f'<line x1="{xk:.1f}" y1="{T}" x2="{xk:.1f}" y2="{B}" stroke="{INK}" stroke-width="1.5" stroke-dasharray="5 4"/>')
s.append(f'<text paint-order="stroke" stroke="#fcfcfb" stroke-width="4" stroke-linejoin="round" x="{xk-8:.1f}" y="{T+16}" font-size="12.5" font-weight="600" fill="{INK}" text-anchor="end">AES-CTR lives here: ½</text>')
s.append(f'<text paint-order="stroke" stroke="#fcfcfb" stroke-width="4" stroke-linejoin="round" x="{xk-8:.1f}" y="{T+32}" font-size="11.5" fill="{INK2}" text-anchor="end">(1 read + 1 write per byte)</text>')

xr = px(X_RFO)
s.append(f'<line x1="{xr:.1f}" y1="{T}" x2="{xr:.1f}" y2="{B}" stroke="{MUTED}" stroke-width="1" stroke-dasharray="2 4"/>')
s.append(f'<text paint-order="stroke" stroke="#fcfcfb" stroke-width="4" stroke-linejoin="round" x="{xr-6:.1f}" y="{B-10}" font-size="11" fill="{MUTED}" text-anchor="end">⅓ with write-allocate stores</text>')

# ---------------- points ----------------
def dot(x, y, filled, r=6):
    if filled:
        return (f'<circle cx="{px(x):.1f}" cy="{py(y):.1f}" r="{r}" fill="{ACCENT}" '
                f'stroke="#fcfcfb" stroke-width="2"/>')
    return (f'<circle cx="{px(x):.1f}" cy="{py(y):.1f}" r="{r}" fill="#fcfcfb" '
            f'stroke="{ACCENT}" stroke-width="2.5"/>')

# measured
s.append(dot(X_KERNEL, MEASURED, True))
s.append(f'<text paint-order="stroke" stroke="#fcfcfb" stroke-width="4" stroke-linejoin="round" x="{px(X_KERNEL)+12:.1f}" y="{py(MEASURED)+16:.1f}" font-size="12.5" font-weight="600" fill="{INK}">'
         f'measured: 49.1 — 93% of roof (1 MiB, L3-resident)</text>')
# predictions
s.append(dot(X_KERNEL, PRED_1CORE, False))
s.append(f'<text paint-order="stroke" stroke="#fcfcfb" stroke-width="4" stroke-linejoin="round" x="{px(X_KERNEL)+12:.1f}" y="{py(PRED_1CORE)+18:.1f}" font-size="12.5" fill="{INK2}">'
         f'predicted: ~23 — 1 core, cold data</text>')
s.append(dot(X_KERNEL, PRED_8SHARE, False))
s.append(f'<text paint-order="stroke" stroke="#fcfcfb" stroke-width="4" stroke-linejoin="round" x="{px(X_KERNEL)+12:.1f}" y="{py(PRED_8SHARE)+16:.1f}" font-size="12.5" fill="{INK2}">'
         f'predicted: ~5.9 — per core, 8 cores sharing the ~100 GB/s CCD link</text>')

s.append('</svg>')

out = "/Users/samlaf/websites/samlaf.github.io/assets/single-core-aes/roofline.svg"
with open(out, "w") as f:
    f.write("\n".join(s))
print(f"wrote {out}")
print(f"roofs: {[round(y,1) for _,y,_ in roofs]}")
print(f"diagonals GiB/s: {[round(bw,1) for _,bw,_,_ in diagonals]}")
print(f"predictions: {PRED_1CORE:.1f}, {PRED_8SHARE:.1f}; angle {ANGLE:.1f}")
