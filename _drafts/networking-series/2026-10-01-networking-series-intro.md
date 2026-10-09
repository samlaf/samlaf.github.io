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

The top half is distributed systems: what correctness means, which histories of operations are legal, and the protocols that replicate state to deliver them. I've written about parts of it before, in [Multiprocessors are distributed systems](/programming/multiprocessors-are-distributed-systems.html) and [BFT broadcast](/blockchain/bft-broadcast.html). It deserves its own series. Shadaj Laddad's [*Distributed Systems Programming Has Stalled*](https://www.shadaj.me/writing/distributed-programming-stalled) is a good way into it: the systems in those boxes have moved on, and the way we program them mostly hasn't.

This series covers the bottom half: from RPC down to the wire. That half has a reputation for being a pile of unrelated protocols. The point of the series is that it isn't.

### The map, level by level

Each box has protocols and systems that live in it. Some appear in more than one box, because they bundle several levels into one product.

| Level | The question it answers | Examples |
| --- | --- | --- |
| application invariants | what does correctness mean here? | `balance >= 0`, one owner per item, stock never below zero; enforced by application code, database constraints or smart contracts |
| distributed objects and state | what exists, and what can clients do to it? | objects with their own operations: CORBA, Java RMI, Cap'n Proto, gRPC services. A few operations over named objects: REST, 9P, SNMP, CMIP, CDAP. Stores: etcd, Redis, SQL databases, distributed shared memory |
| consistency semantics | which histories of operations are legal? | linearizable (etcd, Spanner), serializable (most SQL databases), causal (COPS, Isis's `cbcast`), eventual (DNS, Dynamo), strong eventual (CRDTs), session guarantees (Bayou) |
| replication and coordination | how do the replicas get there? | consensus: Paxos, Raft, Viewstamped Replication. Byzantine consensus: PBFT, HotStuff. Group communication: virtual synchrony (Isis, Horus, Spread, JGroups), atomic broadcast. Quorum replication (Dynamo), two-phase commit, CRDT gossip and anti-entropy |
| RPC and messaging | how does a request find its reply? | Sun RPC, CORBA's IIOP, Java RMI, gRPC, Thrift, JSON-RPC, Cap'n Proto RPC, CDAP. Publish/subscribe: Kafka, MQTT |
| IPC service semantics | what does a flow promise? | reliable byte stream (TCP, a QUIC stream), reliable messages (SCTP, `SOCK_SEQPACKET`), unreliable datagrams (UDP, QUIC datagrams), multicast (IP multicast, Ouroboros broadcast layers) |
| IPC mechanisms and policies | how does a layer keep that promise? | sequencing, acknowledgement, retransmission, windows and congestion control, as TCP, QUIC, RINA's EFCP and Ouroboros's FRCP each combine them |
| recursive IPC | over what scope? | the layers in [Part 3](/programming/internet-as-difs.html)'s rank table, from an HTTP service down to an Ethernet link; PCIe and the shared-memory rings of Parts 4 and 5 |
| physical link | over what medium? | Ethernet PHYs, PCIe lanes, fiber, radio |

### Where virtual synchrony sits

Virtual synchrony fills three boxes at once. Ken Birman's Isis toolkit, which introduced it in the 1980s, offered:

- **An object abstraction.** A named process group was a replicated object. Joining a group meant taking a replica, and a newcomer got the current state by state transfer.
- **A choice of consistency.** A multicast to the group could be FIFO-ordered (`fbcast`), causally ordered (`cbcast`) or totally ordered (`abcast`). Each was delivered within an agreed *view*: the list of members at that moment.
- **A mechanism.** A group membership service turned each member's timeouts into failure events that every member agreed on, and the multicast protocols ran inside each view.

So is it a distributed object abstraction with full consensus? Partly. Agreeing on each new view is a consensus problem, and Isis solved it once per membership change rather than once per message. Inside a view, the default multicast is cheaper and weaker than consensus: a message delivered to a member that crashes right after may never reach the others. Birman's [history of the model](https://www.cs.cornell.edu/ken/history.pdf) explains the choice: most updates touched caches or other state that a restarted member rebuilds anyway. When an application needed more, a *uniform* multicast gave consensus-strength delivery, at consensus cost. Paxos-based systems later added the same reconfigurable membership, and Birman notes that the two families have largely converged.

### How RINA reads the map

Does RINA subsume this map? Mostly, but not by making every box a DIF. RINA has two kinds of distributed facility:

- A **DAF** (distributed application facility) is a set of application processes cooperating on some task. Each member keeps a RIB, its view of the objects the members share, and the members keep their RIBs in step with CDAP.
- A **DIF** is a DAF whose task is IPC.

The two halves of the map line up with those two:

- **The bottom half is DIFs.** "Recursive IPC" is the stack of DIFs at different scopes. "IPC mechanisms and policies" is what each DIF runs, and "IPC service semantics" is what it promises its users.
- **The top half is the anatomy of one DAF.** Its boxes don't differ by scope, as DIFs do. They describe one distributed application at different levels. A replicated key-value store such as etcd fills all of them: keys and values are its objects, linearizability is its semantics, Raft is its mechanism and gRPC is its messaging.
- **Every DIF contains a DAF.** A DIF's layer management is itself a distributed application, with the same anatomy:

| Box in the map | In a DIF's layer management |
| --- | --- |
| objects and state | the RIB: members, addresses, routes, the directory |
| consistency semantics | how closely the members' RIBs must agree, set by policy; routing usually settles for eventual agreement |
| replication and coordination | enrollment, routing updates, directory updates |
| RPC and messaging | CDAP |
| IPC | flows from the DIF itself, or from the DIF below |

So the map recurses twice. The bottom half recurses by scope, one DIF on another. The top half recurs inside every layer, as that layer's management.

Ouroboros, the RINA descendant in [Part 3](/programming/internet-as-difs.html#ouroboros-a-descendant), draws the bottom of the map differently. Its layers deliver packets with no promise of reliability or order. A library at each end adds those, so the ends fill the "IPC service semantics" box, not the layer. It has no CDAP, so layer management has no single object protocol. And its broadcast layers supply the named group that atomic broadcast and virtual synchrony start from, without their ordering or agreement. Those would be a protocol on top, as Isis was on top of IP multicast.

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
- K. Birman, [A History of the Virtual Synchrony Replication Model](https://www.cs.cornell.edu/ken/history.pdf), in *Replication: Theory and Practice*, Springer, 2010.
- Y. Wang, F. Esposito, I. Matta, J. Day, [RINA: An Architecture for Policy-Based Dynamic Service Management](http://csr.bu.edu/rina/papers/BUCS-TR-2013-014.pdf), Boston University technical report BUCS-TR-2013-014, 2013.
- D. Staessens, S. Vrijders, [Design of the Ouroboros packet network](https://arxiv.org/abs/2001.09707), arXiv:2001.09707, 2020.
- J. Saltzer, [RFC 1498, *On the Naming and Binding of Network Destinations*](https://www.rfc-editor.org/info/rfc1498/), 1993 (written 1982).
- J. Saltzer, D. Reed, D. Clark, [End-to-end arguments in system design](https://web.mit.edu/Saltzer/www/publications/endtoend/endtoend.pdf), ACM TOCS, 1984.
