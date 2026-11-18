---
title:  "Agreement"
category: programming
date: 2026-11-14
---

Every replicated system makes two kinds of promise. One is to its clients: what a read may return, and which transactions may interleave. The other is about its own machines: how many may crash, how slow the network may get, and whether the system still makes progress. Most writing covers one side. Database papers name isolation and consistency levels. Distributed systems papers prove when consensus is possible. This series connects the two, and asks one question throughout: which promises force the machines to coordinate, and how much? Coordination comes in three amounts. Some promises need none: every node answers on its own. Some need overlap: each read meets every write quorum. The rest need agreement, which is consensus, the most expensive kind. The stakes keep rising. Hardware gets cheaper every year, but a round trip between machines doesn't get shorter, which is why [Helland][helland-uncoordinated] writes that "coordination is the only remaining hard problem." The series is named for the top of the ladder, because that is where most of the cost lies.

[Carving a database at its joints](/programming/carving-a-database-at-its-joints.html) treats each replica group as one node that decides what commits. This series opens that node up.

## Safety and liveness

[Lamport][lamport-proving] (1977) split the properties of a concurrent system in two. A *safety* property says nothing bad ever happens: a read never returns a value that was overwritten. A *liveness* property says something good eventually happens: every request gets an answer. [Alpern and Schneider][alpern-schneider] (1985) proved that every property is a safety property combined with a liveness property.[^properties] Consensus itself has this shape. Two of its properties are safety: *agreement*, no two processes decide differently, and *validity*, the decision is a value someone proposed. The third is liveness: *termination*, every correct process eventually decides. So the series is about when machines must agree, and safety and liveness are how it measures what agreeing costs. It takes them in that order:

- **Part 1 is liveness alone.** Does an operation finish, whatever the scheduler, the network, or a crash does? Progress conditions rank the answers, from wait-free down to obstruction-free.
- **Part 2 is safety.** Isolation and consistency say which results an operation may return. Safety alone is free: a system that never answers never answers wrongly. So the price of each guarantee is the liveness it gives up, measured on Part 1's ladder.
- **Part 3 is both at once.** A replication protocol must never break safety, whatever fails, and quorum intersection is what guarantees it. It must also keep answering, and it buys that with spare replicas, a leader, timeouts, or randomness.

[^properties]: Here a *property* is a rule you can judge from one run of the system. A run is the whole system's execution, every client and every transaction interleaved, which database theory calls a *history*. Isolation and consistency are judged on one history: a write-skew cycle, or a read that returns an overwritten value, shows up in it. Many requirements aren't of that kind. Here are the requirements [DDIA][ddia] lists, plus a few more, sorted by what they are judged on:

    | Judged on | Functional: which answers are correct | Nonfunctional: how well |
    | --- | --- | --- |
    | One history: safety | right answers: what F gives, in an order that isolation and consistency allow; durability | every request answered within 100 ms |
    | One history: liveness | every transaction eventually commits or aborts | none: a nonfunctional promise names a number, and a number turns "eventually" into a deadline |
    | A set of histories: hyperproperty | determinism: the same input gives the same output | p99 latency, throughput, availability as a percentage, noninterference: secrets don't leak into what others can see |
    | Many deployments | the same answers on 3 nodes or 30 | scalability |
    | No runs at all | | maintainability |

    A deadline turns liveness into safety, because a missed deadline shows at a finite moment. [Clarkson and Schneider][hyperproperties] (2008) call properties of a set of runs *hyperproperties*, and show that each one splits into hypersafety and hyperliveness the same way. Every row holds under a failure model, such as "while at most f nodes crash." Fault tolerance is not a property of its own: it is that assumption, and it applies to a p99 target as much as to durability. It also says who can fail: machines, the network, software, or people. [Who fails?](/programming/who-fails.html) covers the faults that replication can't mask.

    The main functional requirement is that the system computes the function F you want. With concurrent operations, that takes two parts. A sequential specification, F, says what each operation returns when operations run one at a time: a read returns the last write. Isolation and consistency say which orders of the concurrent operations count. Every answer must be what F gives, for some order they allow. Herlihy and Wing defined linearizability this way. "Every answer is right" is partial correctness, a safety property, and "every operation eventually answers" is termination, a liveness property. Together they are total correctness.

    Rice's theorem is about exactly this question: whether a program computes a given function. No algorithm can decide it for every program, and the same holds for any other nontrivial semantic property. That holds for safety and liveness alike. But a safety violation always shows in a finite prefix of a run, so a monitor can catch it as it happens. [Schneider][enforceable] (2000) showed that runtime monitors can enforce exactly the safety properties. Jepsen works this way: checking whether one history is linearizable is decidable, though NP-complete, while checking whether a database only ever produces linearizable histories is not. A liveness bug never shows in a finite run, so a test can only check it with a deadline, which makes it safety.

## The map

![Left: isolation and consistency levels, colored by availability. Right: when consensus is possible, by failure model and network timing](/assets/agreement-series/data-systems-vs-consensus.png)

The left half is what a replicated store promises its clients. The right half is when its replicas can agree at all, for each failure model and network timing. The note at the bottom is where the series starts. CAP and FLP ask for different kinds of progress. CAP asks every live node to answer, whatever the network does. FLP asks only that the system finish eventually. Those are two rungs on one ladder, and Part 1 builds that ladder.

Part 2 draws the arrows between the halves. Some promises on the left need no agreement at all. Some need only a quorum. The rest need consensus, which puts them on the right. Part 3 then works mostly in the crash, partially synchronous cell, where most real systems live, with a detour into Byzantine protocols. It asks how a replica group keeps agreeing while machines fail.

## Where each part sits

[Carving a database at its joints](/programming/carving-a-database-at-its-joints.html) answers the top box: who decides what commits. This series fills in the rest:

```
┌──────────────────────────────────────────────────────────────────────────┐
│ DATABASE                                                                 │
│                                                                          │
│ Who decides what commits?                                                │
│   no-decider             single-, owner-, or separate-decider            │
│   writes merge, so       a decider sees every conflict, and rejects      │
│   nothing to reject      or delays a transaction that breaks the level   │
│                                                                          │
│ Safety         isolation needs agreement                                 │
│ Liveness       detect or mask a dead 2PC coordinator or lock holder      │
└───────┬───────────────────────────────┬──────────────────────────────────┘
        │ merge, or timestamps          │ a decider that survives failures
        │                               │ needs an agreed order
┌───────▼───────────────────────────────▼──────────────────────────────────┐
│ EACH REPLICA GROUP                                                       │
│                                                                          │
│ Order          none (merge) ── timestamps ── agreed (a leader, EPaxos)   │
│ Write quorum   Q2 = 1 ── 2 ── majority ── N                              │
│ Must meet Q2   Q1, leader change: the next leader learns every commit    │
│                R, read: the read is fresh                                │
│                                                                          │
│ Safety         consistency needs overlap                                 │
│ Liveness       detect the leader, and every replica if Q2 = N;           │
│                mask the rest                                             │
└───────▲──────────────────────────────────────────────────────────────────┘
        │ only rows, keys, or transactions can merge or commute
┌───────┴──────────────────────────────────────────────────────────────────┐
│ PAYLOAD                                                                  │
│                                                                          │
│ What crosses?  transactions · rows, keys · objects · pages               │
└──────────────────────────────────────────────────────────────────────────┘
```

Each box makes both kinds of promise. For safety, isolation lives in the top box. A decider sees every conflict, and rejects or delays any transaction that would break the level. One decider on one machine needs only locks. A decider that must survive failures is a replica group, and keeping each decision across a failure takes an agreed order, which is consensus. Consistency lives in the middle box. A read is fresh when it overlaps every write quorum, and that takes no agreement at all: timestamps are enough to order the writes. For liveness, each box has something whose failure must either be detected, which stalls work until a timeout fires, or be masked, so that work carries on. Part 2 explains why the safety line falls where it does, and Part 3 works through the middle box. The bottom box is carving's again: what a group ships limits which writes can merge.

## The articles

1. **[Progress conditions](/programming/progress-conditions.html)** — *liveness*. How much an operation depends on the scheduler. Wait-free, lock-free, and obstruction-free, from Herlihy and Shavit's table. A crash is a thread the scheduler never runs again, so the same ladder measures fault tolerance. ZooKeeper is wait-free for its clients, but not underneath. Paxos is only obstruction-free, and a leader or randomness buys the rest.
2. **[Isolation, consistency, and consensus](/programming/isolation-consistency-and-consensus.html)** — *safety*. Isolation and consistency are separate axes, and every named level picks a rung on each. What each rung costs: nothing, a quorum, or consensus, and how much liveness each one keeps. Why preventing a lost update forces consensus, from Herlihy's consensus numbers. And how, once you have consensus, you could have invented state machine replication.
3. **[Replication in four cells](/programming/replication-in-four-cells.html)** — *both*. Alex Miller's replication spectrum redrawn as a two-by-two grid: one leader or none, writes to a quorum or to all. Where consensus runs in each cell, the quorum rules that keep every cell safe, and the hybrids that stay live by taking a fast path in one cell and falling back to another.

The series builds on [What makes a system distributed that a multiprocessor is not?](/programming/multiprocessors-are-distributed-systems.html): Part 1 starts in shared memory and moves to message passing. [BFT Broadcast](/blockchain/bft-broadcast.html) covers the broadcast side of state machine replication, which Part 2 ends on.

[lamport-proving]: https://lamport.azurewebsites.net/pubs/proving.pdf "Proving the Correctness of Multiprocess Programs"
[alpern-schneider]: https://doi.org/10.1016/0020-0190%2885%2990056-0 "Defining Liveness"
[ddia]: https://dataintensive.net/ "Designing Data-Intensive Applications"
[helland-uncoordinated]: https://pathelland.substack.com/p/i-am-so-glad-im-uncoordinated "I Am So Glad I'm Uncoordinated"
[hyperproperties]: https://www.cs.cornell.edu/fbs/publications/Hyperproperties.pdf "Hyperproperties"
[enforceable]: https://www.cs.cornell.edu/fbs/publications/EnfSecPols.pdf "Enforceable Security Policies"
