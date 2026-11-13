"""Generate figures 02a, 02b, 03c, 03d, and 03e for the "Carving a database at its joints" post.

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


def who_orders():
    layers = [("Application", False), ("SQL", False), ("Access methods", False),
              ("Buffer pool + log", False), ("Disk", True)]
    # Per joint: split family, then (name, mechanism lines) entries for each ordering column.
    rows = [
        ("Shared nothing",
         [("Routed shards", ["Vitess, Citus: each shard locks its", "rows, and 2PC joins shards"])],
         [("Deterministic", ["Calvin: the input log fixes the", "order before any partition runs"])]),
        ("Shared key-value store",
         [("Range owners", ["CockroachDB, Spanner: each", "leaseholder locks its range"])],
         [("Unbundled", ["DSQL: adjudicators check", "write sets at commit"])]),
        ("Shared buffer pool",
         [("Object owners", ["FaRM: each primary locks its", "objects at commit"])],
         [("Disaggregated memory", ["NAM-DB: the writer locks records", "by compare-and-swap"]),
          ("Coherent caches", ["Oracle RAC: global locks; its split", "point sits one joint lower"])]),
        ("Shared disk",
         [("Page owners", ["Aurora Multi-Master (retired):", "storage takes the first write to",
                           "a page; the other writer aborts"])],
         [("Log-based storage", ["Aurora: the one writer is the", "ordering point, above the split"])]),
    ]
    sx, sw, bh = 20, 110, 30
    cols = [(150, 180), (340, 205), (555, 195)]
    above, line_h, entry_gap = 26, 13, 20
    # Each joint's line sits a fixed distance below the box above it; the space below
    # the line grows with the number of mechanism lines in its tallest cell.
    ys, y, box_y = [], 132, []
    for name, owners, other in rows:
        box_y.append(y)
        jy = y + bh + above
        ys.append(jy)
        def depth(entries):
            return sum(len(m) * line_h for _, m in entries) + entry_gap * (len(entries) - 1)
        y = jy + max(depth(owners), depth(other)) + 16
    box_y.append(y)
    h = y + bh + 20
    svg = Svg(760, h, "Which nodes decide, at each joint. Each row is a joint and the family that splits the data there. "
              "Shared nothing: routed shards, such as Vitess and Citus, let each shard lock its rows, with 2PC "
              "between shards; Calvin's input log fixes the order before any partition runs. Shared key-value "
              "store: CockroachDB and Spanner let each leaseholder lock its range; DSQL's adjudicators check write "
              "sets at commit. Shared buffer pool: FaRM's primaries lock their objects at commit; NAM-DB's writer "
              "locks records by compare-and-swap. Oracle RAC also orders at this joint, with global locks and "
              "coherent caches, though it splits one joint lower. Shared disk: in Aurora Multi-Master, now retired, "
              "storage takes the first write to each page and the other writer aborts; plain Aurora has one writer, "
              "which is itself the ordering point, above the split.")
    svg.header("Which nodes decide, at each joint",
               ["Each row is a joint, and the family that splits there. Within a family, the two designs differ in",
                "who runs the ordering point. Oracle RAC orders one joint above its split."])
    heads = [("Split point", "the family", BLUE), ("Orders on the data owners", "the nodes that hold the data decide", DIM),
             ("Orders elsewhere", "something else decides", DIM)]
    for (cx, _), (t, sub, color) in zip(cols, heads):
        svg.text(cx + 6, 102, t, 12, 600, color, "start")
        svg.text(cx + 6, 118, sub, 10.5, fill=DIM, anchor="start")
    for i, (name, store) in enumerate(layers):
        svg.rect(sx, box_y[i], sw, bh, STORE if store else WHITE)
        svg.text(sx + sw / 2, box_y[i] + 19, name, 11)
    for jy, (fam, owners, other) in zip(ys, rows):
        svg.add(f'<line x1="{sx + sw / 2}" y1="{jy}" x2="{cols[0][0]}" y2="{jy}" stroke="{LINE}" stroke-width="1" stroke-dasharray="2 3"/>')
        cx, cw = cols[0]
        svg.line(cx + 2, jy, cx + cw - 4, BLUE, False)
        svg.text(cx + 6, jy - 7, fam, 12, 600, anchor="start")
        for (cx, cw), entries in zip(cols[1:], [owners, other]):
            svg.add(f'<line x1="{cx + 2}" y1="{jy}" x2="{cx + cw - 4}" y2="{jy}" stroke="{DIM}" stroke-width="2.5" stroke-dasharray="5 3"/>')
            ty = jy
            for k, (nm, mech) in enumerate(entries):
                if k == 0:
                    svg.text(cx + 6, jy - 7, nm, 12, 600, anchor="start")
                else:
                    ty += entry_gap - 2
                    svg.text(cx + 6, ty, nm, 12, 600, anchor="start")
                for m in mech:
                    ty += line_h
                    svg.text(cx + 6, ty + 1, m, 10.5, fill=DIM, anchor="start")
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
              "a blue line then splits each replica into two partitions, which execute every transaction. Both end "
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
    # Per design: (name, examples, writers, [(kind, cell lines)] for locks, cache, log).
    rows = [
        ("Read replicas", "Postgres, MySQL", "one",
         [(ONE, ["the primary"]), (ONE, ["the primary"]), (ONE, ["the primary's WAL"])]),
        ("Routed shards", "Vitess, Citus", "many",
         [(SPLIT, ["per shard"]), (SPLIT, ["per shard"]), (SPLIT, ["per shard"])]),
        ("Deterministic", "Calvin", "many",
         [(SPLIT, ["per partition,", "in log order"]), (SPLIT, ["per partition"]),
          (STREAM, ["one input log,", "merged by epoch"])]),
        ("Range owners", "CockroachDB, Spanner", "many",
         [(SPLIT, ["per range, at", "its leaseholder"]), (SPLIT, ["per node, for", "its own ranges"]),
          (SPLIT, ["Raft log", "per range"])]),
        ("Unbundled", "DSQL", "many",
         [(SPLIT, ["adjudicators,", "per key range"]), (SPLIT, ["in storage,", "per key range"]),
          (STREAM, ["the journal, one", "shared service"])]),
        ("Object owners", "FaRM", "many",
         [(SPLIT, ["per object,", "at its primary"]), (NONE, ["none: reads go", "to the primary"]),
          (SPLIT, ["per primary, copied", "to its backups"])]),
        ("Disaggregated memory", "NAM-DB", "many",
         [(SPLIT, ["per record, by CAS", "in memory servers"]), (NONE, ["none"]),
          (STEP, ["per compute thread,", "merged at recovery"])]),
        ("Coherent caches", "Oracle RAC", "many",
         [(SPLIT, ["per resource, at", "its master node"]), (STEP, ["one per node, coherent;", "a master per block"]),
          (STEP, ["one per node,", "merged by SCN"])]),
        ("Log-based storage", "Aurora", "one",
         [(ONE, ["the one writer"]), (ONE, ["the writer's;", "replicas follow redo"]),
          (ONE, ["written by the writer,", "kept by storage"])]),
    ]
    heads = [("Locks", "who checks conflicts"), ("Cache", "hot pages or rows"),
             ("Log", "the order, made durable")]
    nx, cx0, cw, gap, wx = 20, 180, 160, 8, 690
    top, rh, rgap = 124, 40, 5
    legend_y = top + len(rows) * (rh + rgap) + 22
    h = legend_y + 40
    svg = Svg(760, h, "Where each design keeps the state that orders writes: locks, cache, and log. "
              "Read replicas and Aurora keep locks, cache, and log in one node, and have one writer. Every design "
              "with many writers splits its locks, so that each slice has one owner: per shard, partition, range, "
              "key range, object, record, or resource. Caches are split, absent, or kept coherent. Logs vary most: "
              "split per shard or range, one per node and merged, or one shared stream, as in Calvin and DSQL.")
    svg.header("Where each design keeps the state that orders writes",
               ["Every design with many writers splits its locks, so each slice has one owner. Caches and logs have",
                "more options: a log can stay one per node and be merged, or be one stream that every writer shares."])
    for i, (t, sub) in enumerate(heads):
        x = cx0 + i * (cw + gap)
        svg.text(x + cw / 2, 100, t, 12, 600)
        svg.text(x + cw / 2, 114, sub, 10, fill=DIM)
    svg.text(wx + 20, 100, "Writers", 12, 600)

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

    for r, (name, ex, writers, cells) in enumerate(rows):
        y = top + r * (rh + rgap)
        svg.text(nx, y + 17, name, 11.5, 600, anchor="start")
        svg.text(nx, y + 31, ex, 10, fill=DIM, anchor="start")
        for i, (kind, lines) in enumerate(cells):
            cell(cx0 + i * (cw + gap), y, kind, lines)
        svg.text(wx + 20, y + rh / 2 + 4, writers, 11, 600 if writers == "many" else 400,
                 FG if writers == "many" else DIM)

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


out = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
open(f"{out}/02b-two-sequences.svg", "w").write(two_sequences())
open(f"{out}/03c-replication-paths.svg", "w").write(replication_paths())
open(f"{out}/02a-joints-map.svg", "w").write(joints_map())
open(f"{out}/03d-who-orders.svg", "w").write(who_orders())
open(f"{out}/03e-state-placement.svg", "w").write(state_placement())
