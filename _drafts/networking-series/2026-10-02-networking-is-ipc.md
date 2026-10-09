---
title:  "Networking is IPC"
series: "Networking, Part 1"
series_url: "/programming/networking-series-intro.html"
category: programming
date: 2026-10-02
---

> This is Part 1 of a seven-part [series on networking](/programming/networking-series-intro.html).
>
> 1. **Networking is IPC** — one table of every way two parties exchange messages, and the same functions repeating at every boundary.
> 2. **[Naming and binding](/programming/naming-and-binding.html)** — Saltzer's four levels, why IP:port does two jobs, and why every many-to-many case needs a translator.
> 3. **[The Internet as DIFs](/programming/internet-as-difs.html)** — Saltzer's levels inside a RINA layer, a web service read rank by rank, and what overlays like Tailscale are missing.
> 4. **[Interconnects are networks](/programming/interconnects-are-networks.html)** — PCIe is a packet network wearing a 1992 bus costume.
> 5. **[Ring buffers](/programming/ring-buffers.html)** — shared memory plus a doorbell, compared on five axes.
> 6. **A packet's path through Linux** *(not yet written)* — from the NIC's descriptor ring to `recv()`, and the ways around it.
> 7. **[From IPC to RPC](/programming/ipc-to-rpc.html)** — what a request/reply protocol adds on top of a flow, and where RPC ends.

Here is every way I could think of for two parties to exchange messages, from a function call to a message broker. Each row is one mechanism. Each column is one thing you might want from it. A green check means the mechanism provides it natively, amber means partly or conditionally, and a dash means it's absent and you build it yourself.

![Table: IPC mechanisms grouped by the boundary they cross, and which functions each provides natively](/assets/networking-series/ipc-mechanisms-table.png)

The rows are grouped by the boundary the message crosses:

1. **Same address space.** Nothing is crossed. A function call is the degenerate case.
2. **Same kernel.** A process boundary, with the kernel in the middle.
3. **Across a hypervisor.** A VM boundary, with the hypervisor in the middle.
4. **Across a network.** A machine boundary.
5. **Brokered.** A third party sits in the path and keeps state of its own.
6. **Application protocols.** Layered on any of the above.

Three things stand out once the table is filled in. The same handful of columns matter at every boundary. Every row leaves some of them empty. And the mechanisms that fill the gaps are the same mechanisms, reinvented with new names.

- [The same columns at every boundary](#the-same-columns-at-every-boundary)
- [The gaps are where the work goes](#the-gaps-are-where-the-work-goes)
- [One facility, repeated](#one-facility-repeated)
- [Where the model strains](#where-the-model-strains)

## The same columns at every boundary

A function call fills every column for free. Ordering is program order. Framing is the ABI. Message types are the function's signature. The request ID is the stack frame, which also gives you the reply address. Concurrency is threads. Peer identity is trivial, since there is only one party.

Cross one boundary and the columns start emptying. A pipe gives you ordered bytes and nothing else: no framing beyond the atomicity of writes up to `PIPE_BUF`, no message types, no way to match a reply to a request. A Unix socket adds peer identity through `SO_PEERCRED`, which the kernel can vouch for because it created both ends. Shared memory with a futex gives you nothing at all, just bytes both sides can see and a way to sleep until the other side says so.

Further out, the same columns come back filled by different machinery. TCP rebuilds ordering with sequence numbers and retransmission. SCTP adds framing and multiplexing. QUIC fills almost every column: streams for multiplexing, connection IDs for session resume, TLS for crypto and identity. A Xen ring with xenstore fills almost as many, from the other direction: shared pages, request IDs, a per-ring event channel, and a directory service for finding the other end.

None of these columns is specific to networking, or to virtualization, or to the kernel. They are what any two processes need in order to talk, at any distance.

## The gaps are where the work goes

A dash is not a missing feature. It is a decision about who does the work. The layer leaves the function to its users, and every user that needs it builds it.

This is the end-to-end argument, read from below. Saltzer, Reed and Clark's [paper](https://web.mit.edu/Saltzer/www/publications/endtoend/endtoend.pdf) says a function like reliable delivery "can completely and correctly be implemented only with the knowledge and help of the application standing at the endpoints." So a layer that leaves it out isn't negligent. It is assuming the ends will do it anyway, and declining to charge everyone for a partial version. The table shows what that costs in practice:

- **TCP has no framing.** So every protocol on top of it invents one: HTTP/1.1's `Content-Length` and chunked encoding, gRPC's length prefix, the length prefix in nearly every custom protocol.
- **UDP has nothing but ports.** So QUIC rebuilds everything above it: reliability, multiplexing, flow control, session resume, crypto. Mosh does the same for a terminal, so that a session survives a laptop changing networks.
- **virtio-serial has named ports and an ordered byte stream.** An RPC system on top of it, such as the Gondolin row at the bottom, adds a length prefix, message types, request IDs, multiplexing by ID, and a snapshot to resume from.
- **Shared memory has nothing.** So every fast row is shared memory plus a protocol: a ring of descriptors, head and tail indices, and a doorbell. The rings get [their own article](/programming/ring-buffers.html).

Read the bottom group again with this in mind. SSH, mosh, gRPC and Gondolin each fill the gaps of whatever they run on. "Inherits" in the first column means they took reliability from below; everything to its right they built themselves.

## One facility, repeated

John Day's answer to the table is that this repetition isn't an accident. It is the structure of the problem. In [*Patterns in Network Architecture*](https://en.wikipedia.org/wiki/Recursive_Internetwork_Architecture) he takes Metcalfe's 1972 line, that networking is interprocess communication, as a design rule. If networking is IPC, then a network layer and a pipe are the same kind of thing: a facility that gives processes a channel to each other. They differ only in how far apart the processes are.

RINA, the architecture built on that rule, has one kind of layer, the **DIF** (distributed IPC facility). A DIF is a set of cooperating IPC processes, one per member system, that together give flows to the applications above. Every DIF provides the same service and has the same internal structure. The IRATI project's [overview of RINA](https://www.riverpublishers.com/pdf/ebook/chapter/RP_9788793519114C16.pdf) lists what every IPC process does:

- **Data transfer:** delimiting, addressing, sequencing, relaying, multiplexing, lifetime termination, error check, encryption.
- **Data transfer control:** flow control and retransmission control.
- **Layer management:** enrollment, routing, flow allocation, namespace management, resource allocation, security management.

Most of the table's columns are on that list:

| Column | RINA function |
| --- | --- |
| reliable ordered | sequencing, retransmission control |
| framing | delimiting |
| mux + flow ctl | multiplexing, flow control |
| crypto | SDU protection: integrity and encryption |
| peer identity | enrollment, and access control at flow allocation |
| session resume | partly structural: flows aren't bound to addresses |
| msg types, req/resp IDs | not a layer function: the application protocol's job |

The last two rows are the honest part of the mapping. A RINA flow survives an address change, because connections are identified inside the layer and never by address; [Part 3](/programming/internet-as-difs.html) works through why. But resuming after the process at one end restarts is still the application's problem. And message types and request IDs belong above the layer entirely. RINA puts them in a single application protocol, CDAP, which [Part 7](/programming/ipc-to-rpc.html) returns to.

### Layers differ by scope, not by function

In the OSI and TCP/IP models a layer is a unit of modularity: transport does reliability, network does routing, link does framing. In RINA a layer is a "distributed resource allocator" over some range of bandwidth, delay and scale. A DIF over one radio link, one over a datacenter and one over the whole Internet run the same functions. They pick different policies, because a lossy one-hop link and a lossless backbone want opposite things.

That reading makes sense of the table's row groups. They are scopes: one address space, one kernel, one hypervisor, one network, one broker. Each group re-solves the same columns because each one is a new scope, with its own costs and its own trust.

It also explains how many layers there should be: as many as there are scopes that need their own policies. The IRATI chapter puts it bluntly: "This is a network design question, not an architecture question." The Internet already stacks scopes this way, with VLANs, MPLS, VXLAN, VPNs and tunnels. It just builds each one from scratch with its own mechanisms. Above IP, overlays from HTTP proxies to Tailscale do the same, and [Part 3](/programming/internet-as-difs.html#upper-layers-but-no-common-one) looks at why each one builds only part of a layer. So does the rest of the table: virtio, Xen rings, VMBus and D-Bus each invented their own framing, IDs and flow control for a new scope.

### Mechanism is fixed, policy varies

If every layer runs the same functions, what makes TCP different from SCTP, or a virtqueue from a Xen ring? Policy. Matta's group at Boston University make this precise in [Declarative Transport](https://www.cs.bu.edu/fac/matta/Papers/hotnets7-paper40.pdf), subtitled "No more transport protocols to design, only policies to specify."

They split RINA's error and flow control protocol in two:

- **DTP**, the data transfer protocol, holds what must travel with the data: delimiting and fragmentation, sequence numbers, addresses and checksums.
- **DTCP**, the data transfer control protocol, holds the mechanisms that run alongside: acknowledgement, retransmission, flow control and congestion control. Each one is switched on by policy, and has policies of its own: cumulative or selective acks, which PDUs to resend on a timeout.

Whether a flow has a DTCP at all is a policy too. Without one, each PDU is sent once, at whatever rate the layer below allows. That is UDP. Add flow control and retransmission with cumulative acks and you have something TCP-shaped. Add flow control without retransmission, which the IRATI team used for their VM experiments, and you have something the Internet doesn't offer as a transport at all.

Through this lens, a dash in the table is a null policy. A row is a choice of policies at one scope. A new protocol is usually a new combination of old mechanisms.

The idea is older than RINA. The [x-Kernel](https://dl.acm.org/doi/10.1109/32.67579) (1991) built protocol stacks out of small protocol objects that could be stacked in any order. [Horus](https://dl.acm.org/doi/10.1145/227210.227229) (1996) did the same for group communication: it built a virtual synchrony stack out of microprotocols, each adding one property, such as ordering, membership or flow control.

### Pick the lowest layer that reaches

A RINA application asks for a flow to another application by name, with the service it needs. The system picks a DIF whose scope covers the destination. IRATI's shim DIF for hypervisors shows the payoff. An application in a VM whose peer is on the host uses the hypervisor's shared-memory channel directly, as a DIF, with nothing stacked on it. In their host-to-VM tests, that beat both an emulated e1000 and virtio-net, which make the guest pretend there is an Ethernet link where there is only shared memory.

Today a programmer makes that choice by hand, by picking a row. Same host: a Unix socket. Across a VM boundary: vsock. Across a network: TCP or QUIC. Each choice comes with its own API, its own addressing and its own gaps to fill. Move the peer and you rewrite the code. Day's point is that the choice of scope should be the system's job, not the programmer's.

## Where the model strains

The table also shows where the uniform picture is cleaner on paper than in practice.

- **Shared memory isn't a flow.** RINA's service is message passing. The fastest rows in the table, shared memory with a futex, io_uring's rings and RDMA's queue pairs, expose memory both sides can touch, and leave the protocol to the user. A DIF can be built on top of them, as IRATI's hypervisor shim is, but they aren't DIFs themselves.
- **Trust shapes the design as much as scope.** A Xen ring is built for two guests that distrust each other. A virtqueue was built for a trusted hypervisor and is being hardened now that confidential VMs distrust it. io_uring trusts its consumer and distrusts its producer. Same mechanisms, but the trust model decides which ones get validated, copied or bounced. The [ring buffers article](/programming/ring-buffers.html) treats trust as its own axis.
- **It is still mostly research.** RINA has prototypes, IRATI among them, and results like the ones above. Ouroboros, a design that grew out of the IRATI work, has another ([Part 3](/programming/internet-as-difs.html#ouroboros-a-descendant)). Neither has deployments at scale. The structural argument stands on its own. The performance claims are early.

None of this weakens the main point of the table. The same few functions appear at every boundary, every layer leaves some of them to the layer above, and the layer above builds them with the same mechanisms again. The rest of the series follows that pattern down to the hardware, and up to RPC.

## References

- J. Day, *Patterns in Network Architecture: A Return to Fundamentals*, Prentice Hall, 2008.
- J. Day, I. Matta, K. Mattar, "Networking is IPC: a guiding principle to a better Internet", CoNEXT 2008.
- E. Grasa et al., [Recursive InterNetwork Architecture, Investigating RINA as an Alternative to TCP/IP (IRATI)](https://www.riverpublishers.com/pdf/ebook/chapter/RP_9788793519114C16.pdf), River Publishers, 2017.
- N. Hutchinson, L. Peterson, [The x-Kernel: An Architecture for Implementing Network Protocols](https://dl.acm.org/doi/10.1109/32.67579), IEEE Transactions on Software Engineering, 1991.
- R. van Renesse, K. Birman, S. Maffeis, [Horus: A Flexible Group Communication System](https://dl.acm.org/doi/10.1145/227210.227229), Communications of the ACM, 1996.
- [Declarative Transport: No more transport protocols to design, only policies to specify](https://www.cs.bu.edu/fac/matta/Papers/hotnets7-paper40.pdf), Boston University, HotNets-VII submission, 2008.
- J. Saltzer, D. Reed, D. Clark, [End-to-end arguments in system design](https://web.mit.edu/Saltzer/www/publications/endtoend/endtoend.pdf), ACM TOCS, 1984. Summary: [End-to-end principle (Wikipedia)](https://en.wikipedia.org/wiki/End-to-end_principle).
