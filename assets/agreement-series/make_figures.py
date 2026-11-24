"""Draws the consistency-model figures for the isolation/consistency post.

Run: python3 assets/agreement-series/make_figures.py
Writes consistency-grid.svg and consistency-hasse.svg next to this file.
"""

from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(__file__).parent
FONT = "Inter, 'Helvetica Neue', Arial, sans-serif"
INK = "#1f1e1d"
MUTED = "#6b6a66"
FAINT = "#b8b5ae"
BAND = "#f7f6f3"
BAND_EDGE = "#e6e4df"

# fill, stroke, text
OP = ("#ece9f8", "#7b4fc9", "#4a2f8a")
TXN = ("#e3eef9", "#2f6fd6", "#1d4f86")
UNAVAILABLE = ("#f8e4e2", "#b23b33", "#7f231d")
STICKY = ("#fdebd8", "#c25e00", "#8a4300")
TOTAL = ("#e3eef9", "#2f6fd6", "#1d4f86")


def text(x, y, s, size=12, weight=400, fill=INK, anchor="middle", italic=False):
    style = ' font-style="italic"' if italic else ""
    return (
        f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
        f'fill="{fill}" text-anchor="{anchor}"{style}>{escape(s)}</text>'
    )


def box(x, y, w, h, label, colors, sub=None, dashed=False):
    fill, stroke, ink = colors
    dash = ' stroke-dasharray="5 3"' if dashed else ""
    out = [
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="1.2"{dash}/>'
    ]
    cx = x + w / 2
    if sub:
        out.append(text(cx, y + h / 2 - 2, label, 12.5, 600, ink))
        out.append(text(cx, y + h / 2 + 12, sub, 10.5, 400, ink))
    else:
        out.append(text(cx, y + h / 2 + 4.5, label, 12.5, 600, ink))
    return "\n".join(out)


def svg(width, height, label, body):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="{FONT}" role="img" '
        f'aria-label="{escape(label, {chr(34): "&quot;"})}">\n'
        f'<rect width="100%" height="100%" fill="#ffffff"/>\n{body}\n</svg>\n'
    )


def legend(x, y, items):
    out, cx = [], x
    for label, colors, dashed in items:
        fill, stroke, _ = colors
        dash = ' stroke-dasharray="5 3"' if dashed else ""
        out.append(
            f'<rect x="{cx}" y="{y}" width="22" height="14" rx="3" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="1.2"{dash}/>'
        )
        out.append(text(cx + 30, y + 11.5, label, 12, 400, MUTED, "start"))
        cx += 30 + 7 * len(label) + 34
    return "\n".join(out)


# ---------------------------------------------------------------- grid

def grid():
    left, top = 20, 92
    label_w, col_w, gap = 140, 196, 10
    box_h, box_gap, pad = 36, 8, 14
    header_h = 46

    columns = [
        ("One total order", "every operation at one point"),
        ("Writes ordered, reads float", "reads placed apart from writes"),
        ("One order per object", "objects need not agree"),
        ("One order per observer", "tied by causality or program order"),
        ("No agreed order", "at most atomic visibility"),
    ]
    rows = [
        ("Real time", "real-time order"),
        ("Session order", "each client's order"),
        ("No constraint", "any prefix"),
    ]
    # Each cell: list of (label, kind, sub, dashed), or a string note, or None.
    cells = [
        [
            [("Linearizable", OP, None, False), ("Strict serializable", TXN, None, False)],
            [("Regular register", OP, None, True), ("Strong SI", TXN, None, True)],
            "collapses into one total order:|linearizability is local",
            [("Real-time causal", OP, None, True)],
            None,
        ],
        [
            [("Sequential", OP, None, False), ("Strong session serializable", TXN, None, False)],
            [("x86-TSO", OP, "loose analogy", True), ("Strong session SI", TXN, None, True)],
            [("Coherence", OP, None, True)],
            [("Causal", OP, None, False), ("PRAM", OP, None, False),
             ("PSI, transactional causal", TXN, None, True)],
            [("MR · MW", OP, None, False), ("RYW · WFR", OP, None, False)],
        ],
        [
            [("Serializable", TXN, None, False),
             ("Repeatable read", TXN, "items, not predicates", False)],
            [("Snapshot isolation", TXN, None, False)],
            [("Cursor stability", TXN, "roughly", False)],
            None,
            [("Eventual", OP, "convergence only", True),
             ("Monotonic atomic view", TXN, None, False),
             ("Read committed", TXN, None, False), ("Read uncommitted", TXN, None, False)],
        ],
    ]

    width = left * 2 + label_w + 5 * col_w + 4 * gap
    body = [
        text(left, 32, "Consistency models on two axes", 17, 600, INK, "start"),
        text(left, 54, "Rows: which ordering constraint the order respects. Columns: how much of "
             "one total order you get.", 12, 400, MUTED, "start"),
        text(left, 71, "Up and left is stronger, with exceptions: repeatable read and snapshot "
             "isolation are incomparable.", 12, 400, MUTED, "start"),
    ]

    col_x = [left + label_w + i * (col_w + gap) for i in range(5)]
    for (title, sub), x in zip(columns, col_x):
        body.append(text(x + col_w / 2, top + 16, title, 13, 600))
        body.append(text(x + col_w / 2, top + 33, sub, 11, 400, MUTED))

    y = top + header_h
    for (title, sub), row in zip(rows, cells):
        n = max(len(c) if isinstance(c, list) else 2 for c in row)
        row_h = 2 * pad + n * box_h + (n - 1) * box_gap
        body.append(
            f'<rect x="{left}" y="{y}" width="{width - 2 * left}" height="{row_h}" rx="8" '
            f'fill="{BAND}" stroke="{BAND_EDGE}"/>'
        )
        body.append(text(left + 14, y + pad + 16, title, 13, 600, INK, "start"))
        body.append(text(left + 14, y + pad + 33, sub, 11, 400, MUTED, "start"))
        for cell, x in zip(row, col_x):
            if cell is None:
                body.append(text(x + col_w / 2, y + row_h / 2 + 4, "—", 14, 400, FAINT))
            elif isinstance(cell, str):
                lines = cell.split("|")
                for i, line in enumerate(lines):
                    body.append(text(x + col_w / 2, y + pad + 20 + 15 * i, line, 11, 400,
                                     MUTED, italic=True))
            else:
                for i, (label, kind, bsub, dashed) in enumerate(cell):
                    by = y + pad + i * (box_h + box_gap)
                    body.append(box(x, by, col_w, box_h, label, kind, bsub, dashed))
        y += row_h + 10

    body.append(legend(left, y + 10, [
        ("Single operation", OP, False),
        ("Transaction", TXN, False),
        ("Not in the Hasse diagram", ("#ffffff", MUTED, MUTED), True),
    ]))
    height = y + 44
    label = ("A grid of consistency models. Rows: real time, session order, no constraint. "
             "Columns: one total order, writes ordered with reads floating, one order per object, "
             "one order per observer, no agreed order.")
    return svg(width, height, label, "\n".join(body))


# ---------------------------------------------------------------- hasse

def hasse():
    """Implication diagram, banded by which ordering constraint a total order respects."""
    h = 38
    left, right = 40, 1100
    bands = [
        ("Total order + real time", 96, 100),
        ("Total order + session order", 206, 100),
        ("Total order only", 316, 100),
        ("No single agreed total order", 426, 316),
    ]
    band_y = {b[0]: b[1] for b in bands}

    def row(band, i=0):
        return band_y[band] + 32 + i * 70

    # Name -> (x0, x1, top y, colors, sub, dashed)
    rt, ss, to, na = (b[0] for b in bands)
    nodes = {
        "Linearizable": (left, 380, row(rt), UNAVAILABLE, None, False),
        "Sequential": (left, 380, row(ss), UNAVAILABLE, None, False),
        "Causal": (left, 380, row(na, 0), STICKY, None, False),
        "PRAM": (left, 270, row(na, 1), STICKY, None, False),
        "MR · MW": (left, 150, row(na, 2), TOTAL, None, False),
        "RYW": (160, 270, row(na, 2), STICKY, None, False),
        "WFR": (290, 380, row(na, 2), TOTAL, None, False),
        "Strict serializable": (500, 780, row(rt), UNAVAILABLE, None, False),
        "Strong session serializable": (500, 780, row(ss), UNAVAILABLE, None, False),
        "Serializable": (500, 780, row(to), UNAVAILABLE, None, False),
        "Repeatable read": (840, right, row(to), UNAVAILABLE, "items, not predicates", False),
        "Snapshot isolation": (500, 780, row(na, 0), UNAVAILABLE, None, False),
        "Monotonic atomic view": (500, 780, row(na, 1), TOTAL, None, False),
        "Cursor stability": (840, right, row(na, 1), UNAVAILABLE, None, False),
        "Read committed": (500, 780, row(na, 2), TOTAL, None, False),
        "Read uncommitted": (500, 780, row(na, 3), TOTAL, None, False),
    }
    # (weaker, stronger): the arrow points to the model that implies the other.
    edges = [
        ("Linearizable", "Strict serializable"),
        ("Sequential", "Strong session serializable"),
        ("Sequential", "Linearizable"),
        ("Causal", "Sequential"),
        ("PRAM", "Causal"),
        ("WFR", "Causal"),
        ("MR · MW", "PRAM"),
        ("RYW", "PRAM"),
        ("Strong session serializable", "Strict serializable"),
        ("Serializable", "Strong session serializable"),
        ("Repeatable read", "Serializable"),
        ("Snapshot isolation", "Serializable"),
        ("Monotonic atomic view", "Snapshot isolation"),
        ("Monotonic atomic view", "Repeatable read"),
        ("Cursor stability", "Repeatable read"),
        ("Read committed", "Monotonic atomic view"),
        ("Read committed", "Cursor stability"),
        ("Read uncommitted", "Read committed"),
    ]

    def clamp(v, lo, hi):
        return max(lo, min(hi, v))

    width = right + 40
    body = [
        '<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
        f'markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" '
        f'fill="{MUTED}"/></marker></defs>',
        text(20, 32, "Consistency models as implications", 17, 600, INK, "start"),
        text(20, 54, "An arrow points to the stronger model. Bands give the ordering constraint "
             "on a total order. Colors show availability under partition.", 12, 400, MUTED,
             "start"),
        text(210, 84, "Single operation", 14, 600),
        text(800, 84, "Transactions", 14, 600),
    ]
    for label, y, bh in bands:
        body.append(
            f'<rect x="20" y="{y}" width="{width - 40}" height="{bh}" rx="8" fill="none" '
            f'stroke="{FAINT}" stroke-dasharray="4 4"/>'
        )
        body.append(text(32, y + 18, label, 12, 400, MUTED, "start"))
    body.append(text(270, row(to) + 24, "(rarely named)", 12, 400, MUTED))

    for weak, strong in edges:
        wx0, wx1, wy, *_ = nodes[weak]
        sx0, sx1, sy, *_ = nodes[strong]
        if wy == sy:
            if wx1 < sx0:
                x1, x2 = wx1 + 2, sx0 - 4
            else:
                x1, x2 = wx0 - 2, sx1 + 4
            y1 = y2 = wy + h / 2
        elif sx0 > wx1:
            # Leave from the side so the line clears boxes stacked above the source.
            x1, y1 = wx1 + 2, wy + h / 2
            x2, y2 = sx0 + 40, sy + h + 4
        else:
            x1 = clamp((sx0 + sx1) / 2, wx0 + 40, wx1 - 40)
            x2 = clamp(x1, sx0 + 40, sx1 - 40)
            y1, y2 = wy - 2, sy + h + 4
        body.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{MUTED}" '
            f'stroke-width="1.3" marker-end="url(#arr)"/>'
        )
    for name, (x0, x1, y, colors, sub, dashed) in nodes.items():
        body.append(box(x0, y, x1 - x0, h, name, colors, sub, dashed))

    ly = bands[-1][1] + bands[-1][2] + 22
    body.append(legend(20, ly, [
        ("Unavailable under partition", UNAVAILABLE, False),
        ("Sticky available", STICKY, False),
        ("Totally available", TOTAL, False),
    ]))
    height = ly + 34
    label = ("Implication diagram of consistency models in four bands. Linearizable implies "
             "strict serializable's single-operation case; sequential pairs with strong session "
             "serializable. Serializable and repeatable read sit in the total-order-only band. "
             "Causal, PRAM, session guarantees, snapshot isolation, monotonic atomic view, "
             "cursor stability, read committed and read uncommitted sit in the band with no "
             "single agreed total order.")
    return svg(width, height, label, "\n".join(body))


if __name__ == "__main__":
    (OUT / "consistency-grid.svg").write_text(grid())
    (OUT / "consistency-hasse.svg").write_text(hasse())
