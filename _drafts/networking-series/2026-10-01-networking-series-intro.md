---
title:  "Networking"
category: programming
date: 2026-10-01
---

Every system that talks to another one answers the same questions. How is one message told apart from the next? What happens when one is lost? Who is on the other end? How does a reply find its request? A function call answers them for free. A pipe answers some. TCP answers others. A virtqueue, a Kafka topic and a PCIe link each answer their own subset, with their own mechanisms and their own vocabulary.

This series argues that they are all one problem, solved again at every boundary. Robert Metcalfe put it in one line in 1972: networking is interprocess communication. John Day spent the next decades taking that line seriously, and the result is RINA, the Recursive InterNetwork Architecture. Its claim is that a network layer is not a module with its own special functions. It is the same IPC facility, repeated at different scopes, with policies tuned to each one.

## The map

Here is the stack the series works with, from what the application cares about down to the wire:

```
┌──────────────────────────────────────────────────────┐
│              APPLICATION INVARIANTS                  │
│                                                      │
│ "What does correctness mean for this application?"   │
│ balance >= 0, unique owner, inventory >= 0, etc.     │
└────────────────────────┬─────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────┐
│        DISTRIBUTED OBJECT / STATE ABSTRACTION        │
│                                                      │
│ CORBA / Cap'n Proto objects / KV store / DB / DSM    │
│                                                      │
│ "What objects/state exist and what operations        │
│  can clients perform on them?"                       │
└────────────────────────┬─────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────┐
│             STATE CONSISTENCY SEMANTICS              │
│                                                      │
│ "What histories of those operations are legal?"      │
│                                                      │
│ linearizable                                         │
│ sequentially consistent                              │
│ causally consistent                                  │
│ serializable                                         │
│ eventual / strong eventual                           │
│ session guarantees, etc.                             │
└────────────────────────┬─────────────────────────────┘
                         │
                    implemented by
                         ▼
┌──────────────────────────────────────────────────────┐
│          REPLICATION / COORDINATION MECHANISMS       │
│                                                      │
│ Paxos / Raft / Viewstamped Replication               │
│ virtual synchrony / atomic broadcast                 │
│ quorum replication                                   │
│ transactions / 2PC / concurrency control             │
│ CRDTs / gossip / anti-entropy                        │
└────────────────────────┬─────────────────────────────┘
                         │
                    communicate via
                         ▼
┌──────────────────────────────────────────────────────┐
│                 RPC / MESSAGING                      │
│                                                      │
│ request/reply, message IDs, method calls,            │
│ responses, serialization, cancellation               │
└────────────────────────┬─────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────┐
│              IPC SERVICE SEMANTICS                   │
│                                                      │
│ message / stream                                     │
│ reliable / unreliable                                │
│ ordered / unordered                                  │
│ latency-sensitive / partial delivery                 │
└────────────────────────┬─────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────┐
│          RINA IPC MECHANISMS + POLICIES              │
│                                                      │
│ sequencing, retransmission, fragmentation,           │
│ flow control, scheduling, rate control, QoS ...      │
└────────────────────────┬─────────────────────────────┘
                         │
                         ▼
                    recursive IPC
                         │
                         ▼
                    physical link
```

The top half is distributed systems: what correctness means, which histories of operations are legal, and the protocols that replicate state to deliver them. I've written about parts of it before, in [Multiprocessors are distributed systems](/programming/multiprocessors-are-distributed-systems.html) and [BFT broadcast](/blockchain/bft-broadcast.html). It deserves its own series.

This series covers the bottom half: from RPC down to the wire. That half has a reputation for being a pile of unrelated protocols. The point of the series is that it isn't.

## Three lenses

Three ideas do most of the work:

- **Day's IPC model.** Every layer runs the same mechanisms: delimiting, sequencing, retransmission, flow control, multiplexing, protection. What changes from one layer to the next is the scope it covers and the policies it picks. A layer exists because a new scope needs its own policies, not because a new function needs a home.
- **Saltzer's naming and binding.** A destination can mean a service, a node, an attachment point or a path, and each binding between them changes on its own schedule. Many of the Internet's patches, from DNS to QUIC connection IDs, fix a binding the original design collapsed. Others, from NAT to VPN overlays, stand in for the common layer above IP that the design left out.
- **The end-to-end argument.** Saltzer again, with Reed and Clark: a function like reliable delivery can only be complete at the ends. Anything in the middle is a performance enhancement. Every "build it yourself" cell in this series is that argument in practice.

## The articles

1. **[Networking is IPC](/programming/networking-is-ipc.html)** — one table of every way two parties exchange messages, from a function call to a broker, grouped by the boundary each one crosses. Read down a column and the same functions repeat at every scope. Read the gaps and you see what each layer leaves to the one above.
2. **[Naming and binding](/programming/naming-and-binding.html)** — Saltzer's four levels and his own examples, why IP:port does two jobs, how DNS, VIPs, anycast and Kubernetes bind one service to many nodes, what `bind()` actually restricts, and why every many-to-many case needs a translator.
3. **[The Internet as DIFs](/programming/internet-as-difs.html)** — Saltzer's levels inside one RINA layer, and why one rank's node is the next rank's attachment point. Then a web service read rank by rank, from HTTP down to the link, and why NAT outlives every overlay built above IP.
4. **[Interconnects are networks](/programming/interconnects-are-networks.html)** — PCIe is a packet network wearing a 1992 bus costume. Where it puts reliability, why that doesn't violate the end-to-end argument, how enumeration is addressing and routing under another name, and why a PCIe address names the slot, not the card.
5. **[Ring buffers](/programming/ring-buffers.html)** — the one data structure under every fast row of the table: shared memory plus a doorbell. NIC descriptor rings, NVMe, virtqueues, Xen, io_uring and AF_XDP compared on five axes, the last of which is trust.
6. **A packet's path through Linux** — from the NIC's DMA into a descriptor ring, through NAPI, `sk_buff` and the socket buffer, to `recv()`. Then the ways around it: DPDK, AF_XDP, RDMA. *(Not yet written.)*
7. **[From IPC to RPC](/programming/ipc-to-rpc.html)** — what a request/reply protocol adds on top of a flow: message types, request IDs, cancellation, and failure semantics. Why every completion queue is an RPC protocol, and where RPC stops and distributed objects begin.

## References

- J. Day, *Patterns in Network Architecture: A Return to Fundamentals*, Prentice Hall, 2008.
- J. Day, I. Matta, K. Mattar, "Networking is IPC: a guiding principle to a better Internet", CoNEXT 2008.
- D. Staessens, S. Vrijders, [Design of the Ouroboros packet network](https://arxiv.org/abs/2001.09707), arXiv:2001.09707, 2020.
- J. Saltzer, [RFC 1498, *On the Naming and Binding of Network Destinations*](https://www.rfc-editor.org/info/rfc1498/), 1993 (written 1982).
- J. Saltzer, D. Reed, D. Clark, [End-to-end arguments in system design](https://web.mit.edu/Saltzer/www/publications/endtoend/endtoend.pdf), ACM TOCS, 1984.
