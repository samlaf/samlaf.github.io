"""Generate figures 02, 03, 04, and 06 through 13 for the "Carving a database at its joints" post.

Run `python3 assets/db-cuts/gen_figs.py`; it writes the SVGs next to itself.
The other SVGs in this folder are drawn by hand or elsewhere.
"""
import os
import sys
from xml.sax.saxutils import escape, quoteattr

FG, DIM, LINE, STORE = "#1f1e1d", "#6b6a66", "#b8b5ae", "#ecebe7"
BLUE, ORANGE, WHITE = "#2f6fd6", "#c25e00", "#ffffff"
FONT = "Inter, 'Helvetica Neue', Arial, sans-serif"


class Svg:
    def __init__(self, w, h, aria):
        self.w, self.h, self.aria, self.parts = w, h, aria, []

    def add(self, s):
        self.parts.append(s)

    def text(self, x, y, s, size=11, weight=400, fill=FG, anchor="middle"):
        self.add(f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{size}" '
                 f'font-weight="{weight}" fill="{fill}">{escape(s)}</text>')

    def rect(self, x, y, w, h, fill=WHITE, stroke=LINE, rx=4, extra=""):
        s = f' stroke="{stroke}" stroke-width="1.25"' if stroke else ""
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}"{s}{extra}/>')

    def line(self, x1, y, x2, color, dashed):
        d = ' stroke-dasharray="5 3"' if dashed else ""
        self.add(f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="{color}" stroke-width="2.5"{d}/>')

    def header(self, title, subs):
        self.text(20, 28, title, 15, 600, anchor="start")
        for i, s in enumerate(subs):
            self.text(20, 47 + 17 * i, s, 11.5, fill=DIM, anchor="start")

    def render(self):
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
                f'font-family="{FONT}" viewBox="0 0 {self.w} {self.h}" role="img" '
                f'aria-label={quoteattr(self.aria)} font-size="13">'
                f'<rect width="100%" height="100%" fill="{WHITE}"/>' + "".join(self.parts) + "</svg>\n")


def joints_map():
    layers = [("Application", False), ("SQL", False), ("Access methods", False),
              ("Buffer pool + log", False), ("Disk", True)]
    joints = [
        ("Shared nothing", "Vitess/Citus, Calvin", "Command log", "Calvin, NAM-DB"),
        ("Shared key-value store", "CockroachDB/Spanner, DSQL", "Logical log", "Vitess, CockroachDB/Spanner, DSQL"),
        ("Shared buffer pool", "FaRM, NAM-DB", "Object log", "FaRM"),
        ("Shared disk", "Oracle RAC, Aurora", "Physical log or blocks", "Citus, Oracle RAC, Aurora"),
    ]
    x0, x1, top, rh, bh = 255, 505, 44, 66, 32
    mid = (x0 + x1) / 2
    h = top + (len(layers) - 1) * rh + bh + 24
    svg = Svg(760, h, "One engine stack: application, SQL, access methods, buffer pool and log, disk. "
              "Each of the four joints between layers can host either point. On the left, the family "
              "that splits the data at that joint: shared nothing above SQL, shared key-value store below SQL, "
              "shared buffer pool below the access methods, shared disk below the buffer pool and log. On the right, "
              "what a design ships when it replicates at that joint: a command log, a logical log, "
              "an object log, or a physical log or blocks. Each design on the left also appears on the right.")
    svg.text(x0 - 15, top - 14, "Split point", 12, 600, BLUE, "end")
    svg.text(x1 + 15, top - 14, "Replication point", 12, 600, ORANGE, "start")
    for i, (name, store) in enumerate(layers):
        y = top + i * rh
        svg.rect(x0, y, x1 - x0, bh, STORE if store else WHITE)
        svg.text((x0 + x1) / 2, y + 20, name, 11.5)
    for j, (fam, fam_ex, log, log_ex) in enumerate(joints):
        y = top + j * rh + bh + (rh - bh) / 2
        svg.line(x0 - 8, y, mid, BLUE, False)
        svg.line(mid, y, x1 + 8, ORANGE, True)
        svg.text(x0 - 15, y - 3, fam, 12, 600, anchor="end")
        svg.text(x0 - 15, y + 12, fam_ex, 10.5, fill=DIM, anchor="end")
        svg.text(x1 + 15, y - 3, log, 12, 600, anchor="start")
        svg.text(x1 + 15, y + 12, log_ex, 10.5, fill=DIM, anchor="start")
    return svg.render()


# Column heads shared by the figures that sort designs by who checks conflicts.
DECIDERS = [("Owner-decider", "the nodes that hold the data decide"),
            ("Separate-decider", "nodes that don't hold the data decide"),
            ("Single-decider", "the one writer decides")]


def who_orders():
    # Per family: where it splits, then (name, mechanism lines) for each decider, or None.
    rows = [
        ("Shared nothing", "splits above SQL",
         ("Routed shards", ["Vitess, Citus: each shard locks", "its rows; 2PC joins shards"]),
         ("Deterministic", ["Calvin: the input log fixes the", "order before any partition runs"]),
         None),
        ("Shared key-value store", "splits below SQL",
         ("Range owners", ["CockroachDB, Spanner: each", "leaseholder locks its range"]),
         ("Unbundled", ["DSQL: adjudicators check", "write sets at commit"]),
         None),
        ("Shared buffer pool", "splits below access methods",
         ("Object owners", ["FaRM: each primary locks its", "objects at commit"]),
         ("Disaggregated memory", ["NAM-DB: the writer locks", "records by compare-and-swap"]),
         None),
        ("Shared disk", "splits below the buffer pool",
         ("Page owners", ["Aurora Multi-Master (retired):", "storage takes the first write", "to a page; the loser aborts"]),
         ("Coherent caches", ["Oracle RAC: global locks, one", "joint above the split"]),
         ("Log-based storage", ["Aurora, Neon: the one writer", "orders, above the split"])),
    ]
    cols = [(20, 150), (182, 186), (368, 186), (554, 186)]
    line_h, top = 13, 132
    heights = [38 + line_h * max(len(c[1]) for c in r[2:] if c) for r in rows]
    h = top + sum(heights) + 10
    svg = Svg(760, h, "Which nodes decide, in each family. Rows are the four families that span machines, each named "
              "by where it splits; columns are owner-decider, separate-decider, and single-decider. Shared nothing: "
              "routed shards, such as Vitess and Citus, let each shard lock its rows, with 2PC between shards; "
              "Calvin's input log fixes the order before any partition runs. Shared key-value store: CockroachDB and "
              "Spanner let each leaseholder lock its range; DSQL's adjudicators check write sets at commit. Shared "
              "buffer pool: FaRM's primaries lock their objects at commit; NAM-DB's writer locks records by "
              "compare-and-swap. Shared disk: in Aurora Multi-Master, now retired, storage takes the first write to "
              "each page and the loser aborts; Oracle RAC orders with global locks, one joint above its split; and "
              "only this family has a single-decider design: Aurora and Neon have one writer, which orders every "
              "write, above the split.")
    svg.header("Which nodes decide, in each family",
               ["Every family that spans machines has an owner-decider and a separate-decider design.",
                "Only shared disk adds a third: one writer, over storage that spans machines."])
    heads = [("Family", "named by where it splits", BLUE)] + [(t, sub, DIM) for t, sub in DECIDERS]
    for (cx, _), (t, sub, color) in zip(cols, heads):
        svg.text(cx, 102, t, 12, 600, color, "start")
        svg.text(cx, 118, sub, 10.5, fill=DIM, anchor="start")
    y = top
    for (fam, where, *cells), rh in zip(rows, heights):
        svg.add(f'<line x1="20" y1="{y}" x2="740" y2="{y}" stroke="{STORE}" stroke-width="1.5"/>')
        svg.text(cols[0][0], y + 20, fam, 12, 600, anchor="start")
        svg.text(cols[0][0], y + 35, where, 10.5, fill=DIM, anchor="start")
        for (cx, _), cell in zip(cols[1:], cells):
            if not cell:
                continue
            nm, mech = cell
            svg.text(cx, y + 20, nm, 12, 600, anchor="start")
            for k, m in enumerate(mech):
                svg.text(cx, y + 35 + k * line_h, m, 10.5, fill=DIM, anchor="start")
        y += rh
    return svg.render()


def two_sequences():
    pw, gap_g, gap_b = 350, 12, 6
    r0, r1, r2, bh, oh = 68, 180, 258, 40, 24
    svg = Svg(760, r2 + bh + 72,
              "Two panels. Left, split, order, replicate, as in Vitess and most designs: the application and "
              "router sit on top; a blue line splits the data into two shards, keys a to m and n to z; each shard "
              "then orders its own writes in its own SQL engine; an orange line below replicates each shard three "
              "times through its binlog. Right, order, replicate, split, as in Calvin: a sequencer first fixes one "
              "order for every key; an orange line then replicates the input log of transactions to three replicas; "
              "a blue line then splits each replica into two partitions, and each transaction runs on the "
              "partitions that hold its keys. Both end "
              "with six pieces, but Vitess has one order per shard and Calvin one order for all, and in Calvin each "
              "replica repeats far more of the work.")

    def groups(px, n_groups, n_boxes):
        gw = (pw - gap_g * (n_groups - 1)) / n_groups
        bw = (gw - gap_b * (n_boxes - 1)) / n_boxes
        return [(px + g * (gw + gap_g), gw, bw) for g in range(n_groups)]

    def two_line_box(x, y, w, top, sub, fill=WHITE):
        svg.rect(x, y, w, bh, fill)
        svg.text(x + w / 2, y + 17, top, 11.5)
        svg.text(x + w / 2, y + 31, sub, 10, fill=DIM)

    # Drawn like the ordering point in the whole-picture figure.
    def order_box(x, y, w, label):
        svg.rect(x, y, w, oh, STORE, LINE, 4, ' stroke-dasharray="4 3"')
        svg.text(x + w / 2, y + 16, label, 10.5)

    def point(px, y, color, dashed, label):
        svg.line(px, y, px + pw, color, dashed)
        svg.text(px, y - 7, label, 10.5, fill=color, anchor="start")

    def shade(px, y):
        svg.rect(px - 6, y + 4, pw + 12, r2 + bh + 26 - (y + 4), ORANGE, None, 6, ' fill-opacity="0.07"')

    # Left: split, then each shard orders and replicates its own writes.
    px, split_y, repl_y = 20, 132, 246
    shade(px, repl_y)
    svg.text(px, r0 - 40, "Split, order, replicate", 13, 600, anchor="start")
    svg.text(px, r0 - 23, "Vitess, and most designs", 11, fill=DIM, anchor="start")
    two_line_box(px, r0, pw, "Application + router", "every query enters here")
    point(px, split_y, BLUE, False, "split: the router sends each statement to its shard")
    point(px, repl_y, ORANGE, True, "replicate: each shard ships its binlog")
    for (gx, gw, bw), key in zip(groups(px, 2, 3), ["a–m", "n–z"]):
        order_box(gx, split_y + 10, gw, f"order: the shard locks keys {key}")
        two_line_box(gx, r1, gw, "SQL", f"keys {key}, runs each write once")
        for b in range(3):
            two_line_box(gx + b * (bw + gap_b), r2, bw, key, "storage", STORE)
        svg.text(gx + gw / 2, r2 + bh + 17, f"three replicas of {key}", 10.5, fill=DIM)
    svg.text(px, r2 + bh + 44, "Each shard orders its own writes.", 11, anchor="start")
    svg.text(px, r2 + bh + 60, "Each replica only applies the row changes.", 11, fill=DIM, anchor="start")

    # Right: one order for every key, then replicate it, then split.
    px, repl_y, split_y = 390, 166, 246
    shade(px, repl_y)
    svg.text(px, r0 - 40, "Order, replicate, split", 13, 600, anchor="start")
    svg.text(px, r0 - 23, "Calvin", 11, fill=DIM, anchor="start")
    two_line_box(px, r0, pw, "Application", "every transaction enters here")
    order_box(px, r0 + bh + 10, pw, "order: the sequencer fixes one order for every key")
    point(px, repl_y, ORANGE, True, "replicate: the input log of transactions")
    point(px, split_y, BLUE, False, "split: each replica partitions the log by key")
    for n, (gx, gw, bw) in enumerate(groups(px, 3, 2), 1):
        two_line_box(gx, r1, gw, "Input log", "all keys")
        for b, key in enumerate(["a–m", "n–z"]):
            two_line_box(gx + b * (bw + gap_b), r2, bw, key, "execute", STORE)
        svg.text(gx + gw / 2, r2 + bh + 17, f"replica {n}", 10.5, fill=DIM)
    svg.text(px, r2 + bh + 44, "Each replica runs every transaction.", 11, anchor="start")
    svg.text(px, r2 + bh + 60, "That works only because execution is deterministic.", 11, fill=DIM, anchor="start")
    return svg.render()


def state_placement():
    ONE, SPLIT, STEP, STREAM, NONE = range(5)
    # Per answer to "who checks conflicts?": its designs, each with cells for locks, cache, and log.
    groups = [
        ("Single-decider", "the one writer decides", [
            ("Read replicas", "Postgres, MySQL",
             [(ONE, ["the primary"]), (ONE, ["the primary"]), (ONE, ["the primary's WAL"])]),
            ("Log-based storage", "Aurora",
             [(ONE, ["the one writer"]), (ONE, ["the writer's;", "replicas follow redo"]),
              (ONE, ["written by the writer,", "kept by storage"])]),
        ]),
        ("Owner-decider", "the nodes that hold the data decide", [
            ("Routed shards", "Vitess, Citus",
             [(SPLIT, ["per shard"]), (SPLIT, ["per shard"]), (SPLIT, ["per shard"])]),
            ("Range owners", "CockroachDB, Spanner",
             [(SPLIT, ["per range, at", "its leaseholder"]), (SPLIT, ["per node, for", "its own ranges"]),
              (SPLIT, ["Raft log", "per range"])]),
            ("Object owners", "FaRM",
             [(SPLIT, ["per object,", "at its primary"]), (NONE, ["none: reads go", "to the primary"]),
              (SPLIT, ["per primary, copied", "to its backups"])]),
        ]),
        ("Separate-decider", "nodes that don't hold the data decide", [
            ("Deterministic", "Calvin",
             [(SPLIT, ["per partition,", "in log order"]), (SPLIT, ["per partition"]),
              (STREAM, ["one input log,", "merged by epoch"])]),
            ("Unbundled", "DSQL",
             [(SPLIT, ["adjudicators,", "per key range"]), (SPLIT, ["in storage,", "per key range"]),
              (STREAM, ["the journal, one", "shared service"])]),
            ("Disaggregated memory", "NAM-DB",
             [(SPLIT, ["per record, by CAS", "in memory servers"]), (NONE, ["none"]),
              (STEP, ["per compute thread,", "merged at recovery"])]),
            ("Coherent caches", "Oracle RAC",
             [(SPLIT, ["per resource, at", "its master node"]), (STEP, ["one per node, coherent;", "a master per block"]),
              (STEP, ["one per node,", "merged by SCN"])]),
        ]),
    ]
    heads = [("Locks", "who checks conflicts"), ("Cache", "hot pages or rows"),
             ("Log", "the order, made durable")]
    nx, cx0, cw, gap = 20, 192, 176, 8
    right = cx0 + 3 * cw + 2 * gap
    top, rh, rgap, gh, ggap = 124, 40, 5, 26, 12
    n_rows = sum(len(rows) for _, _, rows in groups)
    legend_y = top + len(groups) * (gh + ggap) + n_rows * (rh + rgap) + 20
    h = legend_y + 40
    svg = Svg(760, h, "Where each design keeps the state that orders writes: locks, cache, and log, grouped by "
              "who checks conflicts. In single-decider designs, read replicas and Aurora, all three stay "
              "in one node. In owner-decider designs, routed shards, range owners, and FaRM's object "
              "owners, the locks split with the data, per shard, range, or object, and so do the caches and logs, "
              "except that FaRM keeps no cache. In separate-decider designs, the locks still split, "
              "per partition, key range, record, or resource, but caches and logs vary most: Calvin and DSQL share "
              "one log stream, and NAM-DB and Oracle RAC keep one log per node and merge them; RAC also keeps one "
              "coherent cache per node.")
    svg.header("Where each design keeps the state that orders writes",
               ["With one writer, all three stay in one node. With many, the locks always split, so each slice has",
                "one owner. With separate deciders, caches and logs have the most options."])
    for i, (t, sub) in enumerate(heads):
        x = cx0 + i * (cw + gap)
        svg.text(x + cw / 2, 100, t, 12, 600)
        svg.text(x + cw / 2, 114, sub, 10, fill=DIM)

    def cell(x, y, kind, lines, w=cw):
        if kind == ONE:
            svg.rect(x, y, w, rh, STORE, None)
        elif kind == SPLIT:
            svg.rect(x, y, w, rh, BLUE, None, extra=' fill-opacity="0.12"')
        elif kind == STEP:
            svg.add(f'<rect x="{x + 0.75}" y="{y + 0.75}" width="{w - 1.5}" height="{rh - 1.5}" rx="4" '
                    f'fill="{WHITE}" stroke="{BLUE}" stroke-width="1.5"/>')
        elif kind == STREAM:
            svg.add(f'<rect x="{x + 0.75}" y="{y + 0.75}" width="{w - 1.5}" height="{rh - 1.5}" rx="4" '
                    f'fill="{STORE}" stroke="{DIM}" stroke-width="1.25" stroke-dasharray="4 3"/>')
        color = DIM if kind == NONE else FG
        if len(lines) == 1:
            svg.text(x + w / 2, y + rh / 2 + 4, lines[0], 10, fill=color)
        else:
            svg.text(x + w / 2, y + rh / 2 - 3, lines[0], 10, fill=color)
            svg.text(x + w / 2, y + rh / 2 + 10, lines[1], 10, fill=color)

    y = top
    for title, gloss, rows in groups:
        y += ggap
        svg.text(nx, y + 12, title, 12, 600, anchor="start")
        svg.text(nx + 7 * len(title) + 10, y + 12, gloss, 10.5, fill=DIM, anchor="start")
        svg.add(f'<line x1="{nx}" y1="{y + 19}" x2="{right}" y2="{y + 19}" stroke="{LINE}" stroke-width="1"/>')
        y += gh
        for name, ex, cells in rows:
            svg.text(nx + 10, y + 17, name, 11.5, 600, anchor="start")
            svg.text(nx + 10, y + 31, ex, 10, fill=DIM, anchor="start")
            for i, (kind, lines) in enumerate(cells):
                cell(cx0 + i * (cw + gap), y, kind, lines)
            y += rh + rgap

    legend = [(ONE, "in one node"), (SPLIT, "split: each slice has one owner"),
              (STEP, "one per node, kept coherent or merged"), (STREAM, "one shared stream")]
    lx = nx
    for kind, label in legend:
        svg.add(f'<g transform="translate({lx} {legend_y}) scale(0.5)">')
        cell(0, 0, kind, [""], 40)
        svg.add('</g>')
        svg.text(lx + 26, legend_y + 14, label, 10.5, fill=DIM, anchor="start")
        lx += 60 + len(label) * 5.2
    return svg.render()


def replication_paths():
    rows = ["SQL", "Access methods", "Buffer pool + log", "Disk"]
    row_y = {"Write request": 120, "SQL": 200, "Access methods": 280, "Buffer pool + log": 360, "Disk": 440}
    cw, ch, step = 120, 30, 145
    # (first row the replica repeats, line label, log name, examples), lowest replication point first.
    copies = [
        ("Disk", "page changes", "Physical log", "Postgres WAL, Aurora redo"),
        ("Buffer pool + log", "new object values", "Object log", "FaRM"),
        ("Access methods", "row and key changes", "Logical log", "Vitess, CockroachDB, DSQL"),
        ("SQL", "transactions and their inputs", "Command log", "Calvin, VoltDB"),
    ]
    svg = Svg(760, 536, "A write runs down the primary's stack: SQL, access methods, buffer pool and log, disk. "
              "Orange arrows show where it leaves for the replicas at four heights. A physical log leaves "
              "below the buffer pool and log, so each replica only writes its disk. An object log leaves below the "
              "access methods, so each replica updates its memory and disk. A logical log leaves below SQL, "
              "so each replica runs its access methods, buffer pool and log, and disk. A command log leaves above SQL, "
              "so each replica runs the whole stack.")
    svg.add('<defs>' + "".join(
        f'<marker id="{i}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" '
        f'orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="{c}"/></marker>'
        for i, c in [("ar", LINE), ("ar-ink", FG), ("ar-or", ORANGE)]) + '</defs>')
    svg.header("Where each write leaves for the replicas",
               ["A write runs down the primary's stack. At the replication point, it leaves as a log and continues down each replica.",
                "Shaded: the layers every replica runs for every write. The higher the replication point, the more of the stack each replica repeats.",
                "Replicas may also run the upper layers, but only to serve reads, so the figure leaves them out."])

    def column(x, names, arrow):
        prev = None
        for n in names:
            y = row_y[n]
            svg.rect(x, y, cw, ch, STORE if n == "Disk" else WHITE)
            svg.text(x + cw / 2, y + 19, n)
            if prev is not None:
                svg.add(f'<line x1="{x + cw / 2}" y1="{prev + ch}" x2="{x + cw / 2}" y2="{y - 2}" '
                        f'stroke="{FG if arrow == "ar-ink" else LINE}" stroke-width="1.25" marker-end="url(#{arrow})"/>')
            prev = y

    def footer(x, name, ex):
        svg.text(x + cw / 2, 500, name, 12, 600)
        svg.text(x + cw / 2, 516, ex, 11, fill=DIM)

    column(30, ["Write request"] + rows, "ar-ink")
    footer(30, "Primary", "where the write enters")
    for k, (first, label, name, ex) in enumerate(copies, 1):
        x = 30 + k * step
        top = row_y[first]
        svg.rect(x - 10, top - 10, cw + 20, 480 - (top - 10), ORANGE, None, 6, ' fill-opacity="0.07"')
        column(x, rows[rows.index(first):], "ar")
        ly = top - 25
        svg.line(22, ly, 158, ORANGE, True)
        svg.add(f'<path d="M158 {ly}H{x + cw / 2}V{top - 2}" fill="none" stroke="{ORANGE}" '
                f'stroke-width="1.5" marker-end="url(#ar-or)"/>')
        svg.text(164, ly - 6, label, 11, fill=ORANGE, anchor="start")
        footer(x, name, ex)
    return svg.render()


def decision_tree():
    lw, lh, gap = 232, 140, 12
    lx = [20, 20 + lw + gap, 20 + 2 * (lw + gap)]
    lc = [x + lw / 2 for x in lx]
    q2c = (lc[1] + lc[2]) / 2
    q1c = (lc[0] + q2c) / 2
    y1 = 92
    ly = y1 + 210
    h = ly + lh + 24
    svg = Svg(760, h,
              "A decision tree with two questions and three answers. First: how many nodes may write? With one "
              "writer, the writer decides, inside itself, at no joint (single-decider); its locks, cache, and log stay private, and "
              "shards, if any, stay hidden, as in Aurora, Neon, and read replicas. With many writers, the locks, "
              "cache, and log must be split or kept coherent. Then: which nodes decide? If the data owners decide "
              "(owner-decider), they order at the split, in each slice; the locks split with the data, and shards show to whoever "
              "coordinates commits, the application or the engine, as in Vitess, CockroachDB, and FaRM. If something "
              "else decides (separate-decider), it orders at the split on other nodes, or above it; the locks still split, "
              "and the data shards stay hidden, as in Calvin, DSQL, NAM-DB, and Oracle RAC.")
    svg.header("Who checks conflicts?",
               ["Two questions sort every design into one of three answers. Most of the design follows from",
                "the answer."])

    def wire(d):
        svg.add(f'<path d="{d}" fill="none" stroke="{LINE}" stroke-width="1.5"/>')

    def question(cx, y, label, w=220):
        svg.rect(cx - w / 2, y, w, 32, WHITE, FG)
        svg.text(cx, y + 20.5, label, 12, 600)

    def branch(x, y, label):
        svg.text(x + 6, y, label, 10.5, fill=DIM, anchor="start")

    question(q1c, y1, "How many nodes may write?")
    wire(f"M{q1c} {y1 + 32}V{y1 + 50}H{lc[0]}V{ly}")
    wire(f"M{q1c} {y1 + 50}H{q2c}V{y1 + 74}")
    branch(lc[0], y1 + 70, "one")
    branch(q2c, y1 + 66, "many")
    svg.rect(q2c - 130, y1 + 74, 260, 38, STORE, None)
    svg.text(q2c, y1 + 89, "Split the locks, cache, and log,", 10.5, fill=DIM)
    svg.text(q2c, y1 + 103, "or keep them coherent across nodes", 10.5, fill=DIM)
    wire(f"M{q2c} {y1 + 112}V{y1 + 126}")
    question(q2c, y1 + 126, "Which nodes decide?")
    wire(f"M{q2c} {y1 + 158}V{y1 + 174}H{lc[1]}V{ly}")
    wire(f"M{q2c} {y1 + 174}H{lc[2]}V{ly}")
    branch(lc[1], y1 + 192, "the data owners")
    branch(lc[2], y1 + 192, "something else")

    leaves = [
        ("Single-decider",
         ["Orders inside the writer, at no joint.", "Locks, cache, and log stay private.",
          "Shards, if any, stay hidden."],
         "Aurora, Neon, read replicas"),
        ("Owner-decider",
         ["Orders at the split, in each slice.", "The locks split with the data.",
          "Shards show to whoever coordinates", "commits: the app, or the engine."],
         "Vitess, CockroachDB, FaRM"),
        ("Separate-decider",
         ["Orders at the split on other nodes,", "or above it.", "The locks still split.",
          "Data shards stay hidden."],
         "Calvin, DSQL, NAM-DB, Oracle RAC"),
    ]
    for x, (title, facts, examples) in zip(lx, leaves):
        svg.rect(x, ly, lw, lh, WHITE, LINE, 6)
        svg.text(x + 12, ly + 22, title, 12.5, 600, anchor="start")
        for i, f in enumerate(facts):
            svg.text(x + 12, ly + 42 + 14 * i, f, 10.5, fill=DIM, anchor="start")
        svg.add(f'<line x1="{x + 12}" y1="{ly + 104}" x2="{x + lw - 12}" y2="{ly + 104}" stroke="{STORE}" stroke-width="1.5"/>')
        svg.text(x + 12, ly + 125, examples, 11, 600, anchor="start")
    return svg.render()



# Places a step can happen, top to bottom; a design's markers sit on these tracks.
PLACES = ["in a node", "above SQL", "below SQL", "below access methods", "below the buffer pool"]
N, TOP, SQL, AM, BP = range(5)
EXEC_FILL = "#e6f0e1"


def space_time_grid(rows, n_cols, aria, title):
    """Draw one small grid per design, one row per family and one column per decider.

    Each row is (family, owner-decider, separate-decider, single-decider), with None for an empty cell.
    Each design is (name, steps, execute span). A step is (kind, place, column), plus True when it is
    only an alternative. The execute span, when given, is the (first, last) column the transaction runs in.
    """
    pw, rh, head_h, title_h = 192, 13, 20, 18
    gh = rh * len(PLACES)
    cw = pw / n_cols
    cols = [128, 128 + pw + 18, 128 + 2 * pw + 36]
    row_h = head_h + title_h + gh + 16
    lg = 50  # top of the legend
    hy = lg + 128  # top of the column heads
    y0 = hy + 42
    svg = Svg(760, y0 + row_h * len(rows) + 10, aria)
    svg.header(title, [])
    fills = {"S": BLUE, "R": ORANGE}

    def marker(cx, cy, kind, hollow):
        if kind == "O":
            svg.rect(cx - 8, cy - 6, 16, 12, STORE, DIM, 3, ' stroke-dasharray="3 2"')
            svg.text(cx, cy + 3.5, "O", 9, 600)
        elif hollow:
            svg.rect(cx - 8, cy - 6, 16, 12, WHITE, fills[kind], 6, ' stroke-dasharray="3 2"')
            svg.text(cx, cy + 3.5, kind, 9, 600, fills[kind])
        else:
            svg.rect(cx - 8, cy - 6, 16, 12, fills[kind], None, 6)
            svg.text(cx, cy + 3.5, kind, 9, 600, WHITE)

    def panel(x, y, name, steps, span, faded):
        svg.add(f'<g{" opacity=\"0.45\"" if faded else ""}>')
        svg.text(x + 2, y + 13, name, 11, 600, anchor="start")
        gy = y + title_h
        if steps is None:
            svg.rect(x, gy, pw, gh, STORE, None, 4)
            svg.text(x + pw / 2, gy + gh / 2 - 2, "no replicas: a statement log", 10.5, fill=DIM)
            svg.text(x + pw / 2, gy + gh / 2 + 12, "for recovery only", 10.5, fill=DIM)
            svg.add("</g>")
            return
        svg.rect(x, gy, pw, gh, WHITE, LINE, 4)
        if span:
            first, last = span
            svg.rect(x + first * cw + 3, gy + 2, (last - first + 1) * cw - 6, gh - 4, EXEC_FILL, None, 3)
        for k in range(1, len(PLACES)):
            svg.add(f'<line x1="{x}" y1="{gy + k * rh}" x2="{x + pw}" y2="{gy + k * rh}" stroke="{STORE}" stroke-width="1"/>')
        pos = lambda pl, i: (x + (i + 0.5) * cw, gy + (pl + 0.5) * rh)
        main = sorted([st for st in steps if len(st) == 3], key=lambda st: st[2])
        path = " ".join(f"{'M' if k == 0 else 'L'}{pos(pl, i)[0]} {pos(pl, i)[1]}" for k, (_, pl, i) in enumerate(main))
        svg.add(f'<path d="{path}" fill="none" stroke="{DIM}" stroke-width="1.25"/>')
        for kind, pl, i, *alt in steps:
            if alt:
                prev = [st for st in main if st[2] < i][-1]
                ax, ay = pos(prev[1], prev[2])
                bx, by = pos(pl, i)
                svg.add(f'<path d="M{ax} {ay}L{bx} {by}" fill="none" stroke="{DIM}" stroke-width="1" stroke-dasharray="2 2"/>')
        for kind, pl, i, *alt in steps:
            marker(*pos(pl, i), kind, bool(alt))
        svg.add("</g>")

    def legend_item(x, y, draw, name, desc):
        draw(x + 10, y + 6)
        svg.text(x + 28, y + 10, name, 11, 600, anchor="start")
        svg.text(x + 28, y + 24, desc, 10.5, fill=DIM, anchor="start")

    def swatch(cx, cy):
        svg.rect(cx - 10, cy - 7, 20, 14, EXEC_FILL, None, 3)

    def link(cx, cy):
        svg.add(f'<path d="M{cx - 10} {cy}H{cx + 10}" stroke="{DIM}" stroke-width="1.25"/>')

    svg.rect(20, lg, 720, 100, WHITE, STORE, 6)
    items = [
        [(lambda x, y: marker(x, y, "S", False), "Split point", "requests reach the owner of each slice"),
         (lambda x, y: marker(x, y, "O", False), "Ordering point", "conflicting writes are checked"),
         (lambda x, y: marker(x, y, "R", False), "Replication point", "copies leave for the replicas")],
        [(swatch, "Execution", "the transaction runs: no fixed place"),
         (lambda x, y: marker(x, y, "R", True), "Alternative", "Postgres's WAL instead of MySQL's binlog"),
         (link, "Sequence", "rows: where; columns: in what order")],
    ]
    for r, row in enumerate(items):
        for k, item in enumerate(row):
            legend_item(34 + 240 * k, lg + 14 + 42 * r, *item)

    for x, (t, sub) in zip(cols, DECIDERS):
        svg.text(x, hy, t, 12, 600, DIM, "start")
        svg.text(x, hy + 16, sub, 10.5, fill=DIM, anchor="start")
    for c in cols:
        for k in range(n_cols):
            svg.text(c + (k + 0.5) * cw, hy + 34, ["1st", "2nd", "3rd", "4th"][k], 10, fill=DIM)

    for r, (fam, *designs) in enumerate(rows):
        faded = fam.startswith("Leaderless")
        svg.add(f'<line x1="20" y1="{y0 + r * row_h}" x2="740" y2="{y0 + r * row_h}" stroke="{STORE}" stroke-width="1.5"/>')
        svg.text(20, y0 + r * row_h + 15, fam, 12, 600, DIM if faded else FG, "start")
        y = y0 + r * row_h + head_h
        for k, pl in enumerate(PLACES):
            svg.text(cols[0] - 8, y + title_h + (k + 0.5) * rh + 3, pl, 8.5, fill=DIM, anchor="end")
        for design, x in zip(designs, cols):
            if design:
                panel(x, y, *design, faded)
    return svg.render()


def space_time():
    # The commit path of one write. O is where conflicts are checked (Miller's validate): inside the
    # execute band for lock-based designs, after it for commit-time checks, before it for Calvin.
    rows = [
        ("Shared memory", None, None, ("Read replicas", [("O", N, 1), ("R", SQL, 2), ("R", BP, 2, True)], (0, 1))),
        ("Shared nothing",
         ("Vitess, Citus", [("S", TOP, 0), ("O", TOP, 2), ("R", SQL, 3), ("R", BP, 3, True)], (1, 2)),
         ("Calvin", [("O", TOP, 0), ("R", TOP, 1), ("S", TOP, 2)], (3, 3)), None),
        ("Shared key-value store",
         ("CockroachDB, Spanner", [("S", SQL, 1), ("O", SQL, 2), ("R", SQL, 3)], (0, 3)),
         ("DSQL, FoundationDB", [("O", SQL, 1), ("R", SQL, 2), ("S", SQL, 3)], (0, 0)), None),
        ("Shared buffer pool",
         ("FaRM", [("S", AM, 1), ("O", AM, 2), ("R", AM, 3)], (0, 0)),
         ("NAM-DB", None, None), None),
        ("Shared disk",
         ("Aurora Multi-Master", [("S", BP, 1), ("O", BP, 2), ("R", BP, 3)], (0, 3)),
         ("Oracle RAC", [("O", AM, 1), ("S", BP, 2), ("R", BP, 3)], (0, 1)),
         ("Aurora, Neon", [("O", N, 1), ("S", BP, 2), ("R", BP, 3)], (0, 3))),
        ("Leaderless, out of scope: replicas settle writes later",
         ("Dynamo, Cassandra", [("S", SQL, 0), ("R", SQL, 1), ("O", SQL, 2)], None), None, None),
    ]
    return space_time_grid(
        rows, 4,
        "Every design placed in space and time. Each panel is one design, in three columns by who checks "
        "conflicts: owner-decider, separate-decider, and single-decider. Its rows are places: in a node, above "
        "SQL, below SQL, below the access methods, below the buffer pool. Its columns are four steps in sequence. "
        "S is the split point, O the ordering point, R the replication point, and a green band marks when the "
        "transaction executes, which has no fixed place. Owner-deciders split first, then order and replicate. "
        "Separate-deciders order first: Calvin before it executes, DSQL after, and Oracle RAC while it runs. "
        "Single-deciders order in the one writer while it executes.",
        "Every design in space and time")


def timeline(title, aria, design, cols, lanes, boxes, arrows, split, repl, shade, notes=()):
    """Draw one design's steps: columns are steps in time, lanes are the parts that run them.

    cols: step names; a name starting with "~" is drawn dim, for a step after the commit.
    lanes: (name, description) from top to bottom.
    boxes: {id: (column, lane, text)}.
    arrows: (from id, to id, color, *options). When the boxes share no column or lane, the route bends once:
        across then down by default, or down then across with the option "vh". The option "dashed" dashes it.
    split, repl: (lane boundary, label); boundary k is the top of lane k. split may be None.
    shade: (first column, first lane), shaded to the right and bottom edges: steps every replica repeats.
    notes: (x, y, text, color, anchor).
    """
    x0, cw, top, lh, bw, bh = 200, 160, 112, 70, 140, 28
    right = x0 + cw * len(cols)
    svg = Svg(right + 20, top + lh * len(lanes) + 20, aria)
    svg.add('<defs>' + "".join(
        f'<marker id="tl-{n}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" '
        f'orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="{c}"/></marker>'
        for n, c in [("grey", LINE), ("blue", BLUE)]) + '</defs>')
    svg.header(title, [f"Across: the four steps of a transaction, in {design}'s sequence. Down: the layer that runs each step.",
                       "Orange: the replication point; the shaded steps run again on every replica. "
                       "Blue: the split point, and what crosses there."])
    c0, l0 = shade
    svg.add(f'<rect x="{x0 + cw * c0}" y="{top + lh * l0}" width="{right - x0 - cw * c0}" '
            f'height="{lh * (len(lanes) - l0)}" fill="{ORANGE}" fill-opacity="0.07"/>')
    svg.add(f'<path d="M{x0} 82H{right}" stroke="{LINE}" stroke-width="1" marker-end="url(#tl-grey)"/>')
    svg.text(x0 - 8, 86, "time", 11.5, fill=DIM, anchor="end")
    for k, c in enumerate(cols):
        dim = c.startswith("~")
        svg.text(x0 + cw * (k + 0.5), 101, c.lstrip("~"), 12, 400 if dim else 600, DIM if dim else FG)
    rule = lambda y: svg.add(f'<line x1="24" y1="{y}" x2="{right}" y2="{y}" stroke="#e6e4df" stroke-width="1"/>')
    rule(top)
    for k, (name, desc) in enumerate(lanes):
        svg.text(24, top + lh * k + 33, name, 12.5, 600, anchor="start")
        svg.text(24, top + lh * k + 49, desc, 10.5, fill=DIM, anchor="start")
        rule(top + lh * (k + 1))
    y = top + lh * repl[0]
    svg.add(f'<line x1="24" y1="{y}" x2="{right}" y2="{y}" stroke="{ORANGE}" stroke-width="2" stroke-dasharray="5 3"/>')
    svg.text(right - 4, y - 6, repl[1], 11, fill=ORANGE, anchor="end")
    if split:
        # A split on the replication boundary sits just above it, with its label below, so both stay legible.
        shared = split[0] == repl[0]
        y = top + lh * split[0] - (3 if shared else 0)
        svg.add(f'<line x1="24" y1="{y}" x2="{right}" y2="{y}" stroke="{BLUE}" stroke-width="2"/>')
        svg.text(right - 4, y + 14 if shared else y - 6, split[1], 11, fill=BLUE, anchor="end")

    def box(i):
        c, l, _ = boxes[i]
        return x0 + cw * (c + 0.5), top + lh * l + 21 + bh / 2

    for a, b, color, *opts in arrows:
        (ax, ay), (bx, by) = box(a), box(b)
        up = by < ay
        if ay == by:
            d = f"M{ax + bw / 2} {ay}H{bx - bw / 2}"
        elif ax == bx:
            d = f"M{ax} {ay - bh / 2 if up else ay + bh / 2}V{by + bh / 2 if up else by - bh / 2}"
        elif "vh" in opts:
            d = f"M{ax} {ay - bh / 2 if up else ay + bh / 2}V{by}H{bx - bw / 2}"
        else:
            d = f"M{ax + bw / 2} {ay}H{bx}V{by + bh / 2 if up else by - bh / 2}"
        name = "blue" if color == BLUE else "grey"
        dash = ' stroke-dasharray="4 3"' if "dashed" in opts else ""
        svg.add(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.25"{dash} marker-end="url(#tl-{name})"/>')
    for i, (c, l, label) in boxes.items():
        cx, cy = box(i)
        svg.rect(cx - bw / 2, cy - bh / 2, bw, bh)
        svg.text(cx, cy + 4, label, 11)
    for x, y, t, color, anchor in notes:
        svg.text(x, y, t, 10.5, fill=color, anchor=anchor)
    return svg.render()


def cockroachdb():
    return timeline(
        "CockroachDB checks and replicates each write at its range while the transaction runs",
        "CockroachDB's steps over time and across layers. The gateway node runs the SQL and sends key-value reads "
        "and writes to each range's leaseholder, which checks locks and writes intents. Raft replicates each "
        "intent as it is written. At commit, the gateway fixes the commit timestamp, which a leaseholder may have "
        "pushed past a later read, and the commit is done once a majority of the range's replicas acknowledge it. "
        "Afterwards, every replica applies the commit and its intents become ordinary values.",
        "CockroachDB",
        ["Execute + Check", "Number", "Persist", "~Apply (after commit)"],
        [("Gateway", "SQL on any node; the coordinator"),
         ("Leaseholders", "one per range: locks, timestamp cache"),
         ("Followers", "each range's other replicas")],
        {"run": (0, 0, "run the SQL"), "check": (0, 1, "check locks, write intents"),
         "intent": (0, 2, "replicate each intent"), "num": (1, 0, "fix the commit timestamp"),
         "ack": (2, 2, "a majority acknowledges"), "apply": (3, 2, "resolve intents")},
        [("run", "check", BLUE), ("check", "intent", LINE), ("check", "num", LINE),
         ("num", "ack", BLUE), ("ack", "apply", LINE)],
        (1, "split point: key-value reads and writes, by range"),
        (2, "replication point: Raft log"),
        (3, 2),
        [(448, 168, "pushed past later reads", DIM, "start")])


def aurora():
    return timeline(
        "Aurora runs the transaction on one writer, then persists its redo in storage",
        "Aurora's steps over time and across layers. The one writer runs the transaction, taking locks and changing "
        "pages in its buffer pool, which fetches pages from storage on a miss. It assigns the commit LSN. Storage "
        "persists the redo once 4 of 6 copies acknowledge, and each copy builds pages from it. The writer also "
        "streams redo to read replicas, which apply it to their cached pages: a cache, not a copy.",
        "Aurora",
        ["Execute + Check", "Number", "Persist", "~Apply (after commit)"],
        [("Writer", "SQL, locks, LSNs; exactly one"),
         ("Buffer pools", "the writer's and each replica's"),
         ("Storage service", "log and pages; 6 copies, 3 AZs")],
        {"run": (0, 0, "run, take locks"), "pages": (0, 1, "read and change pages"), "serve": (0, 2, "serve a page"),
         "lsn": (1, 0, "assign the commit LSN"), "ack": (2, 2, "4 of 6 copies acknowledge"),
         "build": (3, 2, "build pages from redo"), "replicas": (3, 1, "replicas apply redo")},
        [("run", "pages", LINE), ("serve", "pages", BLUE), ("run", "lsn", LINE), ("lsn", "ack", BLUE, "vh"),
         ("ack", "build", LINE), ("lsn", "replicas", BLUE, "dashed")],
        (2, "split point: redo down, pages up"),
        (2, "replication point: redo records"),
        (3, 2),
        [(288, 245, "page on a miss", BLUE, "start"), (600, 141, "redo stream", BLUE, "middle"),
         (682, 221, "a cache, not a copy", DIM, "end")])


def dsql():
    return timeline(
        "DSQL runs the transaction first, then checks it, then journals it",
        "DSQL's steps over time and across layers. A query processor runs the transaction, reading rows from "
        "storage as of its start and buffering its writes. At commit, adjudicators check the write set for "
        "conflicts and pick a commit time. Appending to the journal is the commit. Each storage replica then "
        "applies the write sets.",
        "DSQL",
        ["Execute", "Check + Number", "Persist", "~Apply (after commit)"],
        [("Query processors", "SQL; many, stateless"),
         ("Adjudicators", "concurrency control; per key range"),
         ("Journal", "the log; across zones"),
         ("Storage", "rows by timestamp; sharded")],
        {"run": (0, 0, "run, buffer writes"), "serve": (0, 3, "serve rows as of start"),
         "check": (1, 1, "check, pick commit time"), "append": (2, 2, "append: the commit"),
         "apply": (3, 3, "apply write sets")},
        [("serve", "run", BLUE), ("run", "check", BLUE), ("check", "append", LINE), ("append", "apply", LINE, "vh")],
        (1, "split point: row reads; write sets at commit"),
        (3, "replication point: write sets"),
        (3, 3),
        [(288, 256, "row reads", BLUE, "start")])


def calvin():
    return timeline(
        "Calvin orders and persists a transaction before it runs",
        "Calvin's steps over time and across layers. The sequencer numbers and persists transaction inputs above "
        "execution. Every replica then takes locks in log order, executes, and reads and writes its own storage. "
        "Partitions send each other the rows a transaction reads.",
        "Calvin",
        ["Number", "Persist", "Check", "Execute"],
        [("Sequencer", "above execution: the input log"),
         ("Scheduler", "concurrency control"),
         ("Executor", "execution, one per partition"),
         ("Storage", "access methods and disk")],
        {"batch": (0, 0, "batch into an epoch"), "repl": (1, 0, "replicate the batch"),
         "lock": (2, 1, "lock in log order"), "run": (3, 2, "run the transaction"),
         "rw": (3, 3, "read and write rows")},
        [("batch", "repl", LINE), ("repl", "lock", LINE), ("lock", "run", LINE), ("run", "rw", LINE)],
        None,
        (1, "replication point: transaction inputs"),
        (2, 1),
        [(682, 291, "reads cross partitions", BLUE, "end")])


out = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
for name, fig in [("02-two-sequences", two_sequences), ("03-joints-map", joints_map),
                  ("04-replication-paths", replication_paths), ("06-who-orders", who_orders),
                  ("07-decision-tree", decision_tree), ("08-state-placement", state_placement),
                  ("09-cockroachdb", cockroachdb), ("10-aurora", aurora), ("11-dsql", dsql),
                  ("12-calvin", calvin), ("13-space-time", space_time)]:
    open(f"{out}/{name}.svg", "w").write(fig())
