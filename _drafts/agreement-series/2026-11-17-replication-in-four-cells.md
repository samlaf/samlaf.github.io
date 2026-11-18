---
title:  "Replication in four cells"
series: "Agreement, Part 3"
series_url: "/programming/agreement-series-intro.html"
category: programming
date:   2026-11-17
---

> This is Part 3 of a three-part [series on agreement](/programming/agreement-series-intro.html).
>
> 1. **[Progress conditions](/programming/progress-conditions.html)** — *liveness*: how much an operation depends on the scheduler, why a crash is a thread that never runs again, and why Paxos is only obstruction-free.
> 2. **[Isolation, consistency, and consensus](/programming/isolation-consistency-and-consensus.html)** — *safety*: two separate axes, how much liveness each rung gives up, why isolation needs consensus, and how state machine replication follows.
> 3. **Replication in four cells** — *both*: Miller's spectrum as a two-by-two grid, quorum rules that keep each cell safe, and leaders, timeouts, and hybrids that keep it live.

Alex Miller has a complaint: every discussion of replication is about Raft. In [Data Replication Design Spectrum][miller-spectrum], he places replication algorithms on one axis, by how they handle a failure. At one end, quorums *mask* it: the survivors carry on. At the other end, reconfiguration *detects* it: the group stops, swaps out the failed node, and resumes. Raft sits in between. Its followers mask failures, but its leader's failure must be detected.

I agree with most of his argument. This post redraws his axis as a two-by-two grid. The grid shows why his spectrum has exactly three points, where consensus hides in each design, and how the best recent protocols move between cells: a fast path for the common case, and a fallback that is always correct.

This post looks inside one replica group. [Carving a database at its joints](/programming/carving-a-database-at-its-joints.html) treats each group as one decider, and asks which group settles each conflict. Here the question is how that group keeps working when its machines fail.

The first two parts of this series took correctness apart. [Progress conditions](/programming/progress-conditions.html) covered liveness: whether an operation finishes. [Isolation, consistency, and consensus](/programming/isolation-consistency-and-consensus.html) covered safety: what an operation may return, and which operations need consensus at all. A replication protocol needs both at once, and gets them from different places. Quorum intersection keeps every path safe, whatever fails. Masking failures, electing a leader, or using randomness keeps the protocol live. Miller's axis measures the second half: a design that masks a failure keeps answering, and one that detects it stalls until a timeout fires.

- [Miller's spectrum](#millers-spectrum)
- [Four cells](#four-cells)
- [Where consensus runs](#where-consensus-runs)
- [Three quorums, two rules](#three-quorums-two-rules)
- [The bottom-left cell: register or consensus](#the-bottom-left-cell-register-or-consensus)
- [Fast paths and fallbacks](#fast-paths-and-fallbacks)
  - [Operation axis: pay for order only when needed](#operation-axis-pay-for-order-only-when-needed)
  - [Leader axis: the leader as a hint](#leader-axis-the-leader-as-a-hint)
  - [Quorum axis: a bigger quorum for fewer rounds](#quorum-axis-a-bigger-quorum-for-fewer-rounds)
  - [The limits each hybrid works around](#the-limits-each-hybrid-works-around)
- [How a hybrid switches](#how-a-hybrid-switches)
- [Choosing a cell](#choosing-a-cell)

## Miller's spectrum

Miller sorts replication into three classes:

- **Quorums:** losing any member is tolerated, and replication carries on. Cassandra, ABD, and leaderless Paxos work this way.
- **Reconfiguration:** every write goes to every replica. On a failure, replication halts until the failed node is replaced. Chain replication, PacificA, Kafka, and FoundationDB work this way.
- **Leadered consensus:** Raft and Multi-Paxos. "The followers act like quorum replication, but having a leader bumps it one tick towards reconfiguration."

His follow-up talk, [Enough With All The Raft][miller-raft], makes two points I fully agree with.

**Leader election is reconfiguration.** When a Raft leader dies, request processing halts, a timeout fires, an election runs, and requests resume. When a replica dies under reconfiguration, the same thing happens. In Miller's words: "It's literally the same diagram. I just deleted some nodes." If one bothers you, so should the other.

**Availability is a latency target.** A request is unavailable when it takes longer than its deadline. If failover finishes inside the deadline, nothing went down. In his later talk, [Please Implement A Quorum Database][miller-quorum], he puts it more bluntly: "availability is just a latency SLO."

He ends with two rules:

> Use Quorums or Raft if you can't have any other supporting service to help with group membership.
> Use Reconfiguration or Raft if you must handle high, single-item contention.

I differ on two points, and the rest of the post builds on them.

1. **Raft's advantage is not on Miller's metrics.** He compares storage, bandwidth, round trips, and unavailability, and Raft never wins. But Raft gives each group one total order. Any replica can take a local snapshot, a lagging replica catches up on only what it missed, and read-modify-write is easy. His quorum talk lists exactly these as its wishlist for leaderless designs. Reconfiguration gets the same order from its primary, which is why his second rule pairs it with Raft.
2. **Reconfiguration doesn't avoid consensus; it moves it.** Its data path needs no consensus, but membership changes do. They go to a separate service. [Where consensus runs](#where-consensus-runs) shows why.

## Four cells

Two questions sort every design: does one leader propose every operation, and how many replicas must each write reach?

```
              writes reach a quorum (Q2 < N)     writes reach all (Q2 = N)
             ┌──────────────────────────────────┬──────────────────────────────┐
 one leader  │ Raft, Multi-Paxos                │ PacificA, chain replication  │
             │ Miller: leadered consensus       │ Miller: reconfiguration      │
             ├──────────────────────────────────┼──────────────────────────────┤
 no leader   │ Paxos, EPaxos, Accord, ABD       │ Hermes                       │
             │ Miller: quorums                  │ Miller: reconfiguration      │
             └──────────────────────────────────┴──────────────────────────────┘
```

Miller's classes are regions of the grid. Reconfiguration takes the whole right column: he files Hermes there, though any Hermes replica can coordinate a write.

The grid also explains his unavailability numbers. A design must detect the failure of its leader, if it has one, and of every replica that each write must reach. Count those nodes:

| Cell | Must detect | Chance a random failure stalls writes (Miller, f = 2) |
| --- | --- | --- |
| One leader, quorum | the leader | 1 in 5: 20% |
| No leader, quorum | nothing | 0% |
| Either row, all | every replica | 100% |

Four cells give only three values. A leader adds one node to the set. Writing to every replica adds all of them, and the leader is already among them. So for failure handling, Miller's single axis is correct, and the grid shows where its three points come from.

The leader axis still matters for throughput. Any Hermes replica can take a write, so by Miller's count, Hermes gets 33% write bandwidth to PacificA's 16.7%.[^aurora]

[^aurora]: The top-left shape also appears at other joints of an engine. Aurora has one writer, whose failure must be detected. Below it, storage persists each write to four of six copies with no leader per segment, so a failed copy is simply outvoted. Raft is the same pattern at the key-value joint.

## Where consensus runs

Every cell solves consensus somewhere. The cells differ in where, and how often:

|  | Writes reach a quorum | Writes reach all |
| --- | --- | --- |
| **One leader** | Consensus elects the leader, inside the group, once per term. The leader then orders every operation. | An outside service fixes membership and picks the primary. The primary orders every operation. |
| **No leader** | Either consensus runs per operation (Paxos, EPaxos, Accord), or none runs at all, because timestamps order the writes (ABD). | An outside service fixes membership. Timestamps order the writes (Hermes). |

The right column needs an outside service for a simple reason. Say a group of f + 1 replicas writes to all of them. After one failure, no write can finish until the dead node leaves the group. Agreeing on that change takes consensus, and consensus that tolerates f failures needs 2f + 1 nodes. The survivors are too few, so someone else must decide. Lamport, Malkhi, and Zhou formalize this as [Vertical Paxos][vertical-paxos]: a data path that writes to every replica, steered by a configuration master.

[Cheap Paxos][cheap-paxos] (Lamport and Massa, 2004) sits between the columns. It runs f + 1 main replicas plus f auxiliary nodes that join only to reconfigure. That is reconfiguration with the membership service moved inside the group.

This puts Miller's "40% cheaper" in context. Reconfiguration needs f + 1 data replicas, where Raft needs 2f + 1. But the count leaves out the membership service. That is fair when one service steers many groups, as in Kafka or FoundationDB, and less fair for a single group. Raft can also narrow the gap with auxiliary nodes that hold no data.

The left column runs consensus inside the group. A leader runs it once per term, to win the election, and then orders operations without it. A leaderless design pays per operation, unless its operations need no agreed order at all. [The bottom-left cell](#the-bottom-left-cell-register-or-consensus) covers that split.

## Three quorums, two rules

A replica group uses quorums in three roles, but only two rules constrain them, and both are about the write quorum:

| Quorum | Must intersect | Why |
| --- | --- | --- |
| Write (Q2) | nothing, if there is a leader | the leader already orders the writes |
| Leader change (Q1) | every write quorum | the new leader must learn any write the old one might have committed, and block the old one from finishing more |
| Read (R) | every write quorum | the read must see the latest committed write |

A leader change is a kind of read. Paxos's first phase reads the accepted values from Q1, and adds one step a plain read skips: each replica promises to ignore older leaders. In the terms of Gifford's [weighted voting][gifford] (1979), Q1 and R are read quorums, and Q2 is the write quorum.

[Flexible Paxos][flexible-paxos] (Howard, Malkhi, and Spiegelman, 2016) showed that the two must intersect only each other: Q1 + Q2 > N. Majorities for both is one choice among many:

- **Q2 below a majority:** writes get cheaper, but a leader change needs more than a majority, so elections get fragile.
- **Q2 = majority:** classic Paxos and Raft.
- **Q2 = N:** then Q1 = 1, and any single replica can serve reads. This is the right column of the grid. One failed replica blocks every write until membership changes.

So Miller's two columns are two points on Flexible Paxos's axis. The grid splits them at Q2 < N, not at the majority, because that is where a follower's failure stops being masked.

**The rule that disappears.** Gifford also required write quorums to intersect each other, so that two writers would see each other's version numbers. Flexible Paxos drops that rule, because a leader orders the writes. Take the leader away and the rule comes back. In [Fast Paxos][fast-paxos], clients write straight to replicas, and any two fast quorums and one classic quorum must share a node. That three-way overlap is why a fast quorum is about three quarters of the replicas. A leader is what lets write quorums be small and disjoint.

**Reads have two routes.** A quorum read overlaps every write quorum (R + Q2 > N), as in ABD. Raft's ReadIndex instead asks the leader, who confirms it still leads by reaching enough nodes to overlap every *leader-change* quorum. A lease replaces that round with a promise about time. [Making reads go brrrr](/programming/making-reads-go-brr.html) covers both routes.

## The bottom-left cell: register or consensus

The leaderless, quorum cell holds two kinds of protocol, and [Gryff][gryff] (Burke, Cheng, and Lloyd, NSDI 2020) names the line between them: stable versus unstable order.

- **A register needs no final order.** Each write fully defines the new state. A replica can apply w4 before it hears of w3, and ignore w3 when it arrives late. That is why ABD finishes even in a fully asynchronous network.
- **A read-modify-write needs a final order.** Its result depends on the value before it, so its place in the order must be fixed before anyone trusts the result. The FLP result says no deterministic protocol can always fix it in an asynchronous network.

Operations fall on a range between the two:

```
 needs no order ◀──────────────────────────────────────────▶ needs a final order
 blind write        commutative       escrow             read-modify-write
 (ABD register)     (increments)      (commutes until    (compare-and-swap,
                                       near the limit)    debit with a check)
```

[Isolation, consistency, and consensus](/programming/isolation-consistency-and-consensus.html) explains why the line falls there: a register has consensus number 1, and compare-and-swap has consensus number ∞. This post only needs the consequence. A leaderless design pays for consensus on exactly the operations that need a final order.

## Fast paths and fallbacks

Butler Lampson's [Hints for Computer System Design][lampson-hints] (1983) has a rule that fits every protocol below:

> Handle normal and worst cases separately as a rule, because the requirements for the two are quite different: The normal case must be fast. The worst case must make some progress.

Each hybrid runs a fast path in one cell and falls back to another. Each axis of the grid has its own:

```
              writes reach a quorum (Q2 < N)                 writes reach all (Q2 = N)
             ◀─────────────────────────── quorum axis ───────────────────────────▶
                                  deploy time: Flexible Paxos
                         runtime: Fast Paxos, FaB, Alpenglow, Zyzzyva
             ┌──────────────────────────────────────────────┬────────────────────┐
 one leader  │ Raft, Multi-Paxos                            │ PacificA, chain    │
             │      ▲                                       │                    │
             │      │ leader axis                           │                    │
             │      │ QuePaxa, Ditto                        │                    │
             ├──────┼───────────────────────────────────────┼────────────────────┤
 no leader   │      ▼                                       │ Hermes             │
             │ consensus ◀─── operation axis ────▶ register │                    │
             │                     Gryff                    │                    │
             │ EPaxos, Accord                           ABD │                    │
             └──────────────────────────────────────────────┴────────────────────┘
```

### Operation axis: pay for order only when needed

Gryff runs reads and writes as a multi-writer ABD register, and read-modify-writes through EPaxos. Its *carstamps* put both kinds in one order, so a write can't slip between a read-modify-write and the value it read. Reads and writes never wait on consensus.

Other designs move operations toward the cheap end of the range:

- **[CURP][curp]** (NSDI 2019) sends commutative operations to witnesses and returns in one round trip. Only conflicting operations wait for the leader to order them.
- **[EPaxos][epaxos]** and **[Accord][accord]** take one round when an operation conflicts with nothing in flight, and a second round when it does.
- **[Escrow][escrow]** (O'Neil, 1986) lets increments and decrements commute while no ordering could break the constraint. A balance far above zero can take concurrent debits without agreeing on their order.
- **Nil-externality** ([Skyros][skyros], SOSP 2021) defers ordering any operation that returns no state, until someone observes its effect.

Miller's quorum talk lands here too: its fictional bill-splitting database becomes feasible only once its transfers use escrow and its log appends are nil-external.

### Leader axis: the leader as a hint

[QuePaxa][quepaxa] (Tennage et al., SOSP 2023) keeps a leader, but only as a fast path. Normally, a designated leader commits in one round trip. If that fails, any proposer can decide. From the second round on, the protocol is leaderless and fully asynchronous, and each round succeeds with probability at least one half. Proposers attach random priorities, so concurrent proposers help each other instead of dueling, as Paxos proposers do.

QuePaxa replaces timeouts with *hedging delays*: other proposers join after a short delay. A false start costs only redundant work, never liveness, so the delay can be aggressive. A multi-armed bandit tunes the leader choice and the delays.

Raft has a fallback too, but its fallback is an election triggered by a timeout, which assumes the network is partly synchronous. QuePaxa's fallback assumes nothing about timing. In Miller's terms, QuePaxa removes Raft's one detection point. A slow leader costs a hedging delay instead of an election. Chandra, Hadzilacos, and Toueg showed that an eventual leader is the weakest extra power that solves consensus at all, and [Progress conditions](/programming/progress-conditions.html) covers why. QuePaxa gets the same power from randomness, and keeps the leader for speed: an asynchronous protocol costs O(n²) messages per decision, and the fast path keeps that at O(n).

Byzantine protocols have the same pattern. [Ditto][ditto] (Gelashvili et al., 2022) and [Bolt-Dumbo Transformer][bdt] (Lu et al., 2022) pair a fast, partly synchronous path with an asynchronous fallback.

### Quorum axis: a bigger quorum for fewer rounds

A protocol can decide in fewer rounds if more replicas answer. [Fast Paxos][fast-paxos] decides in one round with about three quarters of the replicas, and falls back to two rounds with a majority. Solana's [Alpenglow][alpenglow] does the same with stake. Its fast path finalizes a block after one round of votes from 80% of stake. Its fallback takes two rounds at 60% each. Any 80% quorum and any 60% quorum overlap, because 80 + 60 > 100, so the two paths can never finalize conflicting blocks. Both run at once, and finality comes from whichever finishes first.

The price follows a known rule. To decide in one round while e of n replicas fail, you need extra replicas:

| Failure model | Bound | With e = f |
| --- | --- | --- |
| Crash ([Lamport, 2006][lamport-lower-bounds]) | n > 2e + f | n > 3f, as in Fast Paxos |
| Byzantine ([Martin and Alvisi, 2006][fab]) | n ≥ 3f + 2e + 1 | n ≥ 5f + 1 |

[Kuznetsov, Tonkikh, and Zhang][kuznetsov] later tightened the Byzantine bound to 5f − 1.

A database and a blockchain pay this price in different currencies. A database adds replicas. A blockchain can't add stake, so it lowers f instead. Alpenglow tolerates 20% malicious stake, where classic Byzantine protocols tolerate 33%. In return it gets one round, plus tolerance for another 20% of stake that is merely offline.

[Zyzzyva][zyzzyva] (Kotla et al., 2007) takes this to the end of the axis. Its fast path needs replies from all 3f + 1 replicas. With fewer replies, the client falls back to collecting 2f + 1 and sending them back as a commit certificate.

Flexible Paxos sits on the same axis, but fixes its trade at deploy time instead of switching at runtime. Every write runs phase 2, so phase 2 gets the small quorum. Leader changes are rare, so phase 1 gets the big one.

### The limits each hybrid works around

| Axis | Fast path | Fallback | The limit | Examples |
| --- | --- | --- | --- | --- |
| Operation | no final order needed | consensus | Herlihy (1991): registers can't solve consensus | Gryff, CURP, EPaxos, Accord |
| Leader | a leader, in one round trip | leaderless, asynchronous, randomized | FLP (1985): no deterministic consensus in an asynchronous network with even one crash | QuePaxa, Ditto, Bolt-Dumbo Transformer |
| Quorum, at runtime | a bigger quorum, in one round | a majority, in more rounds | Lamport (2006), Martin and Alvisi (2006): one round costs 2e extra replicas | Fast Paxos, FaB, Alpenglow, Zyzzyva |
| Quorum, at deploy time | a small write quorum | a big leader-change quorum | quorum intersection: Q1 + Q2 > N | Flexible Paxos |

The limits are not all the same kind. FLP and Herlihy's result are impossibility results, and a hybrid avoids them by taking the expensive path only when it must. Both forbid only a liveness guarantee, never safety: Paxos stays safe in a fully asynchronous network, and registers can solve consensus if obstruction-free is enough. The one-round bounds are prices: you can't avoid them, only choose the currency. Quorum intersection is a safety condition that people long read as stricter than it is.

## How a hybrid switches

The switch from fast path to fallback is where hybrids break, and Miller's axis applies to the switch itself. There are three ways to switch:

- **On a timeout.** Raft's election, a PBFT view change, Zyzzyva's client. This is detection, so it inherits reconfiguration's problems: too short a timeout causes false switches, and too long a timeout stalls.
- **By aborting and handing off.** [Abstract][abstract] (Aublin et al., "The Next 700 BFT Protocols," 2015) builds protocols from instances that can abort and hand their state to the next.
- **By running both at once.** Alpenglow counts each vote toward both paths. QuePaxa comes close with hedging. No one has to detect a failure, so this masks it.

Running both at once also helps with slow nodes. A bigger fast quorum waits on more replicas, so it is more exposed to stragglers. When both paths run at once, a straggler costs a fall to the slow path, not a stall.

## Choosing a cell

Miller's rules, restated on the grid:

- **No separate membership service?** Stay in the left column.
- **Heavy contention on single items?** Use the top row, where a leader orders operations, or shrink what needs an order along the operation axis.
- **Tight tail latency?** Use the bottom row, or a hybrid whose fallback masks failures.
- **Bound by storage?** Use the right column, or Flexible Paxos and auxiliary nodes in the left one.

Raft is the top-left cell, with a timeout as its switch. Miller calls its one unique advantage "its unrelenting, unwavering mediocrity," and that is fair: it is never the best cell, and never a bad one. The protocols worth watching are the ones that don't pick a cell at all. They run fast in one and fall back to another, and switch without waiting on a timer.

## References <!-- omit in toc -->

1. [Data Replication Design Spectrum][miller-spectrum] — Miller, 2024; quorums, reconfiguration, and leaders, compared on storage, bandwidth, latency, and unavailability
2. [Enough With All The Raft][miller-raft] — Miller, 2025; leader election is reconfiguration, and Raft's "unwavering mediocrity"
3. [Please Implement A Quorum Database][miller-quorum] — Miller; leaderless consensus, commutativity, and escrow
4. [Vertical Paxos and Primary-Backup Replication][vertical-paxos] — Lamport, Malkhi, Zhou, PODC 2009; a write-all data path steered by a configuration master
5. [Cheap Paxos][cheap-paxos] — Lamport, Massa, DSN 2004; f + 1 main processors and f auxiliary ones
6. [Weighted Voting for Replicated Data][gifford] — Gifford, SOSP 1979; read and write quorums
7. [Flexible Paxos: Quorum Intersection Revisited][flexible-paxos] — Howard, Malkhi, Spiegelman, 2016; only phase-1 and phase-2 quorums must intersect
8. [Fast Paxos][fast-paxos] — Lamport, 2006; one-round decisions with larger quorums
9. [Gryff: Unifying Consensus and Shared Registers][gryff] — Burke, Cheng, Lloyd, NSDI 2020; registers for reads and writes, EPaxos for read-modify-writes
10. [Hints for Computer System Design][lampson-hints] — Lampson, 1983; handle normal and worst cases separately
11. [Exploiting Commutativity for Practical Fast Replication][curp] — Park, Ousterhout, NSDI 2019; CURP
12. [There Is More Consensus in Egalitarian Parliaments][epaxos] — Moraru, Andersen, Kaminsky, SOSP 2013; EPaxos
13. [CEP-15: General Purpose Transactions][accord] — Apache Cassandra; Accord
14. [The Escrow Transactional Method][escrow] — O'Neil, TODS 1986
15. [Exploiting Nil-Externality for Fast Replicated Storage][skyros] — Ganesan et al., SOSP 2021; Skyros
16. [QuePaxa: Escaping the Tyranny of Timeouts in Consensus][quepaxa] — Tennage et al., SOSP 2023; a leader fast path over a randomized asynchronous core
17. [Jolteon and Ditto][ditto] — Gelashvili et al., 2022; Byzantine consensus with an asynchronous fallback
18. [Bolt-Dumbo Transformer][bdt] — Lu et al., 2022; an optimistic path over asynchronous consensus
19. [Alpenglow: a new consensus for Solana][alpenglow] — Anza; one round at 80% of stake, or two at 60%
20. [Lower Bounds for Asynchronous Consensus][lamport-lower-bounds] — Lamport, 2006; fast learning needs n > 2e + f
21. [Fast Byzantine Consensus][fab] — Martin, Alvisi, IEEE TDSC 2006; FaB Paxos
22. [Revisiting Optimal Resilience of Fast Byzantine Consensus][kuznetsov] — Kuznetsov, Tonkikh, Zhang, PODC 2021; 5f − 1 suffices
23. [Zyzzyva: Speculative Byzantine Fault Tolerance][zyzzyva] — Kotla et al., SOSP 2007
24. [The Next 700 BFT Protocols][abstract] — Aublin et al., TOCS 2015; Abstract, composable protocol instances

[miller-spectrum]: https://transactional.blog/blog/2024-data-replication-design-spectrum "Data Replication Design Spectrum"
[miller-raft]: https://transactional.blog/talk/enough-with-all-the-raft "Enough With All The Raft"
[miller-quorum]: https://transactional.blog/talk/please-implement-a-quorum-database "Please Implement A Quorum Database"
[vertical-paxos]: https://lamport.azurewebsites.net/pubs/vertical-paxos.pdf "Vertical Paxos and Primary-Backup Replication"
[cheap-paxos]: https://lamport.azurewebsites.net/pubs/web-dsn-submission.pdf "Cheap Paxos"
[gifford]: https://doi.org/10.1145/800215.806583 "Weighted Voting for Replicated Data"
[flexible-paxos]: https://arxiv.org/abs/1608.06696 "Flexible Paxos: Quorum Intersection Revisited"
[fast-paxos]: https://www.microsoft.com/en-us/research/publication/fast-paxos/ "Fast Paxos"
[gryff]: https://www.usenix.org/conference/nsdi20/presentation/burke "Gryff: Unifying Consensus and Shared Registers"
[lampson-hints]: https://www.microsoft.com/en-us/research/publication/hints-for-computer-system-design/ "Hints for Computer System Design"
[curp]: https://www.usenix.org/conference/nsdi19/presentation/park "Exploiting Commutativity For Practical Fast Replication"
[epaxos]: https://doi.org/10.1145/2517349.2517350 "There Is More Consensus in Egalitarian Parliaments"
[accord]: https://cwiki.apache.org/confluence/display/CASSANDRA/CEP-15%3A+General+Purpose+Transactions "CEP-15: General Purpose Transactions"
[escrow]: https://doi.org/10.1145/7239.7265 "The Escrow Transactional Method"
[skyros]: https://doi.org/10.1145/3477132.3483543 "Exploiting Nil-Externality for Fast Replicated Storage"
[quepaxa]: https://bford.info/pub/os/quepaxa/quepaxa.pdf "QuePaxa: Escaping the Tyranny of Timeouts in Consensus"
[ditto]: https://arxiv.org/abs/2106.10362 "Jolteon and Ditto: Network-Adaptive Efficient Consensus with Asynchronous Fallback"
[bdt]: https://arxiv.org/abs/2103.09425 "Bolt-Dumbo Transformer: Asynchronous Consensus As Fast As the Pipelined BFT"
[alpenglow]: https://anza.xyz/blog/alpenglow-a-new-consensus-for-solana "Alpenglow: a new consensus for Solana"
[lamport-lower-bounds]: https://lamport.azurewebsites.net/pubs/lower-bound.pdf "Lower Bounds for Asynchronous Consensus"
[fab]: https://doi.org/10.1109/TDSC.2006.35 "Fast Byzantine Consensus"
[kuznetsov]: https://arxiv.org/abs/2102.12825 "Revisiting Optimal Resilience of Fast Byzantine Consensus"
[zyzzyva]: https://doi.org/10.1145/1294261.1294267 "Zyzzyva: Speculative Byzantine Fault Tolerance"
[abstract]: https://doi.org/10.1145/2658994 "The Next 700 BFT Protocols"

## Footnotes <!-- omit in toc -->
