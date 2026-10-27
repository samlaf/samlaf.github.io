---
title:  "Packets and circuits"
series: "Networking, Part 5"
series_url: "/programming/networking-series-intro.html"
category: programming
date: 2026-10-06
---

> This is Part 5 of a nine-part [series on networking](/programming/networking-series-intro.html).
>
> 1. **[Networking is IPC](/programming/networking-is-ipc.html)** — one table of every way two parties exchange messages, and the same functions repeating at every boundary.
> 2. **[Naming and binding](/programming/naming-and-binding.html)** — Saltzer's four levels, why IP:port does two jobs, and six ways to carry out a binding.
> 3. **[The Internet as DIFs](/programming/internet-as-difs.html)** — Saltzer's levels inside a RINA layer, a web service read rank by rank, and what overlays like Tailscale are missing.
> 4. **[Future internets](/programming/future-internets.html)** — NDN, SCION and RINA each rewrite a different one of Saltzer's levels.
> 5. **Packets and circuits** — what circuit switching bundled, virtual circuits from X.25 to MPLS, and why Google put circuits back under its packet fabric.
> 6. **[Interconnects are networks](/programming/interconnects-are-networks.html)** — PCIe is a packet network wearing a 1992 bus costume.
> 7. **[Ring buffers](/programming/ring-buffers.html)** — shared memory plus a doorbell, compared on five axes.
> 8. **A packet's path through Linux** *(not yet written)* — from the NIC's descriptor ring to `recv()`, and the ways around it.
> 9. **[From IPC to RPC](/programming/ipc-to-rpc.html)** — what a request/reply protocol adds on top of a flow, and where RPC ends.

[Part 4](/programming/future-internets.html) opened with two internets that came before the Internet: X.25 and CYCLADES. X.25 set up a virtual circuit before it sent anything. CYCLADES sent datagrams and let the ends sort it out. That fight, circuits against packets, is usually told as settled: packets won, and the Internet is the proof.

The rest of this series assumes it. But a provider backbone in [Part 3's rank table](/programming/internet-as-difs.html#a-web-service-rank-by-rank) runs MPLS, which is a virtual circuit. Google's datacenter fabric runs over optical circuit switches. The fight isn't settled, because "circuit switching" was never one choice. It was three choices sold together, and modern networks buy them separately.

- [Three choices in one word](#three-choices-in-one-word)
  - [Where the forwarding state lives](#where-the-forwarding-state-lives)
- [Virtual circuits: X.25, ATM, MPLS](#virtual-circuits-x25-atm-mpls)
- [RFC 3439: are packets really simpler?](#rfc-3439-are-packets-really-simpler)
  - [Layering considered harmful](#layering-considered-harmful)
- [Circuits under packets](#circuits-under-packets)
- [Day: setup and reservation are policies](#day-setup-and-reservation-are-policies)
- [References](#references)

## Three choices in one word

A telephone call made three choices at once:

1. **What the switch moves.** A telephone switch connects a signal path: a timeslot, a wavelength, a pair of wires. It never looks at the data. A packet switch moves one packet at a time, and reads each header to decide where it goes.
2. **Whether the path is set up first.** Dialing sets up the path before anyone speaks. A datagram network sets up nothing, and decides the path for each packet as it arrives.
3. **Whether capacity is reserved.** A call holds its share of every link for as long as it lasts, used or not. Packets share links statistically: whoever has data sends, and queues absorb the bursts.

A phone call says yes to all three. Best-effort IP says no to all three. Everything else in networking sits somewhere in between, and that is why the terms confuse people. Here is the space, as a decision tree:

![Decision tree: packet switching splits into datagram and virtual circuit, each with or without reservation; circuit switching splits into provisioned and reconfigured circuits](/assets/networking-series/switching-decision-tree.png)

The first split is the only one about mechanism: does the switch read the data, or not? Below it, the packet side has two independent yes/no questions. The circuit side has one, because a circuit always commits its resources while it is up.

Two points the tree makes easy to miss:

- **A circuit can still be dynamic.** The telephone network set up a new circuit for every call and tore it down at the end. Google's optical switches, [below](#circuits-under-packets), rewire a datacenter as demand changes. What makes something a circuit is that, once connected, it carries traffic without inspecting it.
- **"Sharing" means two different things.** Time-division and wavelength-division multiplexing (TDM, WDM) let many circuits share one fiber, but each circuit still owns its timeslot or wavelength. Statistical multiplexing is different: many flows share one capacity, and nobody owns any of it. When IP runs over an optical circuit, both happen at once. The circuit owns its wavelength, and the packets inside it share that wavelength statistically. That is packet switching on top of circuit switching.

### Where the forwarding state lives

The second choice, setting up a path first, is a binding in [Part 2](/programming/naming-and-binding.html)'s sense. It binds a destination to a path. The difference between the designs is when that binding happens, and where the switches keep it:

| Design | When the path is bound | Forwarding state in each switch | What the packet carries |
| --- | --- | --- | --- |
| telephone circuit | once, when the call is set up | one entry per call: this timeslot in, that one out | nothing: there are no packets |
| virtual circuit (X.25, ATM, MPLS) | once, when the connection is set up | one entry per connection: this label in, that label and port out | a short label, meaningful on one link only |
| datagram (IP) | at every hop, for every packet | one entry per destination prefix, shared by all traffic | the full destination address |
| source route (SCION, segment routing) | once, by the sender | none per destination or per flow | the whole path |
| NDN | at every hop, per request | one entry per pending request, in the PIT | the name of the data |

The virtual-circuit label is worth a second look. It isn't an address. It names one connection on one link, and each switch rewrites it for the next link. In Part 2's terms, the first switch binds by encapsulation, pushing a label in front of the packet, and every switch after that binds by translation. That makes a label switch a NAT for connections, and it pays the cost Part 2 found in every NAT: it must hold state for every connection that passes through it. A datagram router holds state per destination, which is why the Internet's core scales with the number of prefixes, not the number of conversations.

## Virtual circuits: X.25, ATM, MPLS

A virtual circuit keeps the setup and drops the dedicated path. The switches forward packets, and the links are shared statistically, but each packet follows the path its connection set up. Three generations of it matter.

**X.25** (CCITT, 1976) was the carriers' packet network. A call request set up a virtual circuit, hop by hop, and each hop retransmitted lost packets and controlled flow. The network promised reliable, ordered delivery. CYCLADES, Louis Pouzin's French research network, promised nothing: datagrams, with reliability left to the hosts. TCP/IP took the CYCLADES side, and the end-to-end argument later explained why.

**ATM** (1990s) cut every packet into 53-byte cells: a 5-byte header and 48 bytes of payload. A cell's header carries a virtual path and virtual circuit identifier (VPI/VCI), which, like any label, means something on one link only. Circuits were either provisioned by an operator (PVCs) or set up on demand by signaling (SVCs). ATM's service classes ran from constant bit rate, a reserved circuit in all but name, to "unspecified bit rate", which is best effort. ATM was meant to carry voice, video and data on one network. It ended up carrying IP, which [RFC 3439](#layering-considered-harmful) prices below.

**MPLS** began in 1996 and 1997 as several vendor efforts, Cisco's tag switching and Ipsilon's IP switching among them, and became [RFC 3031](https://www.rfc-editor.org/info/rfc3031/) in 2001. The first reason for it was speed. An IP router does a longest-prefix match on every packet. A label switch does an exact match on a 20-bit label, which was much easier to build into hardware at the time. Routers soon learned to do prefix matches at line rate, and that reason went away. MPLS stayed, for two others:

- **Traffic engineering.** IP sends every packet for a prefix down the shortest path. A label-switched path (LSP) can follow any path the operator picks, so heavy flows can be steered around a busy link.
- **VPNs.** A label can name a customer as well as a path. [BGP/MPLS IP VPNs](https://www.rfc-editor.org/info/rfc4364/) carry many customers' overlapping private address spaces over one backbone, kept apart by labels.

The tree's two packet-side questions show up in how an LSP gets set up. LDP builds LSPs that simply follow the routing protocol's shortest paths, with nothing reserved: a virtual circuit without reservation. [RSVP-TE](https://www.rfc-editor.org/info/rfc3209/) signals an explicit path, and each router on it sets bandwidth aside: a virtual circuit with reservation. The datagram side has the same two leaves. Plain IP reserves nothing. [RSVP](https://www.rfc-editor.org/info/rfc2205/), the protocol RSVP-TE grew from, lets an IP flow reserve capacity at each router on its path, with no connection setup underneath. RSVP never spread across the public Internet. Coarse priority classes ([DiffServ](https://www.rfc-editor.org/info/rfc2475/)) did, because they need no state per flow.

The newest step moves MPLS toward SCION. [Segment routing](https://www.rfc-editor.org/info/rfc8402/) writes the path into the packet as a stack of labels, one per segment, and each router pops its own. The core no longer keeps any state per LSP. That is [Part 4](/programming/future-internets.html#beacons-segments-and-paths)'s packet-carried forwarding state, inside one provider, without SCION's cryptography.

## RFC 3439: are packets really simpler?

Packet switching won the argument on two claims: that statistical multiplexing uses links more efficiently, and that a stateless router is simpler than a switch that tracks calls. In 2002 Randy Bush and David Meyer, both long-time Internet operators, tested both claims in [RFC 3439, *Some Internet Architectural Guidelines and Philosophy*](https://www.rfc-editor.org/info/rfc3439/). Its section 5 is titled "Packet versus Circuit Switching: Fundamental Differences". They didn't find what the conventional story predicts.

**Efficiency.** Statistical multiplexing should let packet networks run their links fuller. They cite Odlyzko and Coffman's measurements: IP links averaged between 3% and 20% utilization, from corporate networks to commercial backbones. Long-haul voice lines averaged about 33%. Internet traffic is bursty and hard to forecast, so operators add capacity early and in large steps. The efficiency is real in theory and spent in practice.

**Simplicity.** Here the numbers run the other way too:

| | Internet router | Transport (circuit) switch |
| --- | --- | --- |
| software | 8–10 million instructions | about 3 million |
| line card logic | 30+ million gates, a CPU | 7.5 million gates, no CPU |
| packet buffers | 300 MB per card | none |
| forwarding table | yes | none: it maps ingress timeslots to egress timeslots |

A router must parse headers, do a longest-prefix match, generate ICMP errors, and buffer about a round trip's worth of traffic so that TCP's congestion control works. A circuit switch knows in advance when each timeslot arrives and where it goes. Their conclusion: "as data rates get large, it becomes more and more complex to switch packets, while circuit switching scales more or less linearly."

They name the cause *hop-by-hop independence*. Every IP router decides on its own, for every packet, with no memory of a connection. That is what makes IP robust. It is also why every router must be able to do everything, and why debugging an IP network can mean visiting every router on a path to find a fault that was outside your network all along. Virtual-circuit networks don't have that property, which is what made them easier for carriers to operate.

None of this argues for replacing IP with circuits. The RFC's broader point is the *simplicity principle*: complexity, not any one design, is what drives a network's cost. But it does make the claim "packets are simpler" depend on the layer. At the edge, where traffic is bursty and unpredictable, packets win. In the core, where traffic between big aggregates is smooth and predictable, circuits can be the simpler machine. That is the bet Google made, [below](#circuits-under-packets).

### Layering considered harmful

Section 3 of the same RFC lists what a layer does:

- **error control**, which makes the channel more reliable;
- **flow control**, which keeps a fast sender from flooding a slow peer;
- **fragmentation**, which divides large data into smaller pieces and reassembles them;
- **multiplexing**, which lets several higher-level sessions share one lower-level connection;
- **connection setup**, a handshake with the peer;
- **addressing and naming**.

That is nearly the list of functions [Part 1](/programming/networking-is-ipc.html#one-facility-repeated) took from RINA. Bush and Meyer see the same thing Day sees: every layer does the same jobs again. The two draw opposite conclusions.

Bush and Meyer conclude that layers are expensive. Each one repeats work, hides information the others need, and adds its own failures. Their example is a *convergence layer*, which they call "Everything Over Some Layer": the idea that one technology, whether ATM, MPLS, DWDM or IP, should carry all others. IP over ATM shows the cost. A 40-byte TCP acknowledgment gains an 8-byte SNAP header and an 8-byte AAL5 trailer, which no longer fits in one 48-byte cell payload. So it takes two cells: 106 bytes on the wire to carry 40. On a DS3 line, the RFC adds it all up to a loss of about 31% of the line rate. Their advice is to separate concerns side by side, not stack them.

Day concludes that layers are fine, and that the waste comes from building each one differently. IP over ATM stacked two layers that solved the same problems with unrelated mechanisms, and neither one could see the other's policies. The cell tax is the price of that mismatch, not of the layering itself. A RINA stack would have two DIFs running one mechanism, each tuned to its scope. Proponents argue that makes repetition cheap. Bush and Meyer would answer that the cost is operational as much as computational, and that a layer you don't need costs something however it is built. Both readings explain the same history.

## Circuits under packets

[Part 6](/programming/interconnects-are-networks.html#three-interconnect-models-why-networking-won) argues that shared buses are extinct, and that everything is now packets over two-party links. That is true of what the switches forward. It isn't always true of the links.

Google's datacenter network, Jupiter, used to be a Clos fabric: aggregation blocks of servers, joined through a layer of spine switches. [*Jupiter Evolving*](https://research.google/pubs/jupiter-evolving-transforming-googles-datacenter-network-via-optical-circuit-switches-and-software-defined-networking/) (SIGCOMM 2022) describes what replaced it. The spine is gone. The aggregation blocks connect to each other directly, through a layer of MEMS-based optical circuit switches (OCS). An OCS is a set of tiny mirrors that steer light from one fiber to another. It never converts light to electrical signals, and it never reads a packet. So, as RFC 3439 predicted, its cost doesn't grow with the line rate: the same switch carries whatever speed the optics at the two ends run.

Software reconfigures those circuits as the traffic between blocks shifts, which the paper calls *topology engineering*. Packet switching still happens in the aggregation blocks, which share each circuit statistically among all their flows. The paper reports 5x higher speed and capacity, 30% lower capital cost and 41% lower power than the fabric it replaced. It also reports that the direct-connect design matches a Clos fabric's throughput on production traffic.

Google's TPU v4 supercomputer uses the same idea one level down. [Its ISCA 2023 paper](https://arxiv.org/abs/2304.01433) joins 64 racks into a 4,096-chip machine through 48 optical circuit switches. The circuits are set per job, so each training run gets the torus shape that suits it. The paper puts the switches and their optics at under 5% of the system's cost and under 3% of its power.

This is the decision tree's right-most leaf: a dynamic circuit. It works here because the demand between whole aggregation blocks changes slowly compared with packets, and because one operator owns both the circuits and the packets that ride them. RFC 3439's reading holds. Circuits win where traffic is aggregated and predictable, and packets win where it isn't. Google uses each where it fits.

In [Part 3](/programming/internet-as-difs.html#a-web-service-rank-by-rank)'s rank table, the OCS sits below the datacenter fabric row. It is closer to the medium than to a layer. Day doesn't count the medium as a DIF, because it names and routes nothing. An OCS doesn't route anything either, packet by packet. But its management does rewire it, which makes it a medium that the layer above can reshape.

## Day: setup and reservation are policies

Day worked on ARPANET protocols from the 1970s and on the OSI reference model, so he saw the X.25 against CYCLADES fight up close. In *Patterns in Network Architecture*, he sides with neither camp. He reads connection-oriented and connectionless as two ends of one scale: how much state the protocol machines share, and how much they commit in advance. Connectionless isn't zero shared state. Every IP router shares routing state with its neighbors, and every host must enroll with an address before it sends. It is the minimum shared state. A circuit is the maximum.

In RINA, where a flow sits on that scale is a policy. An application asks a DIF for a flow to a name and states the service it needs. The DIF's flow allocator chooses how to provide it. It can set up nothing and route every packet on its own, or reserve resources along a fixed path. One DIF can do both, for different flows. The Internet gets the same range by stacking separate technologies: best-effort IP on top, MPLS with RSVP-TE below, optical circuits below that. Each one has its own signaling, its own management and its own names. Day's complaint is the one [Part 3](/programming/internet-as-difs.html#upper-layers-but-no-common-one) made about overlays: the Internet already has the layers, but builds each one from scratch.

Read this way, the decision tree's packet side is [Part 1](/programming/networking-is-ipc.html#mechanism-is-fixed-policy-varies)'s "mechanism is fixed, policy varies" applied to switching. "Connection setup?" and "Reservation?" are switches a DIF can flip per flow, as DTCP's retransmission and flow control are. The tree's first split is different. A circuit switch doesn't delimit, relay or multiplex PDUs. It has no PDUs. No policy turns a packet switch into a circuit switch. That is the one place where packets and circuits really are different machines.

So the old dichotomy survives, but lower than its name suggests. It isn't about connections, or reservations, or fixed paths. Those are policies, and modern networks mix them freely. It is about whether anything along the path reads the data. Everything above that line is a choice of policy. Below it is the medium, which the layers above can rewire but never inspect.

## References

- R. Bush, D. Meyer, [RFC 3439, *Some Internet Architectural Guidelines and Philosophy*](https://www.rfc-editor.org/info/rfc3439/), 2002.
- J. Day, *Patterns in Network Architecture: A Return to Fundamentals*, Prentice Hall, 2008.
- E. Rosen, A. Viswanathan, R. Callon, [RFC 3031, *Multiprotocol Label Switching Architecture*](https://www.rfc-editor.org/info/rfc3031/), 2001.
- D. Awduche et al., [RFC 3209, *RSVP-TE: Extensions to RSVP for LSP Tunnels*](https://www.rfc-editor.org/info/rfc3209/), 2001.
- R. Braden et al., [RFC 2205, *Resource ReSerVation Protocol (RSVP)*](https://www.rfc-editor.org/info/rfc2205/), 1997.
- S. Blake et al., [RFC 2475, *An Architecture for Differentiated Services*](https://www.rfc-editor.org/info/rfc2475/), 1998.
- E. Rosen, Y. Rekhter, [RFC 4364, *BGP/MPLS IP Virtual Private Networks (VPNs)*](https://www.rfc-editor.org/info/rfc4364/), 2006.
- C. Filsfils et al., [RFC 8402, *Segment Routing Architecture*](https://www.rfc-editor.org/info/rfc8402/), 2018.
- L. Poutievski et al., [Jupiter Evolving: Transforming Google's Datacenter Network via Optical Circuit Switches and Software-Defined Networking](https://research.google/pubs/jupiter-evolving-transforming-googles-datacenter-network-via-optical-circuit-switches-and-software-defined-networking/), SIGCOMM 2022.
- A. Vahdat, [Jupiter evolving: Reflecting on Google's data center network transformation](https://cloud.google.com/blog/topics/systems/the-evolution-of-googles-jupiter-data-center-network), Google Cloud blog, 2022.
- N. Jouppi et al., [TPU v4: An Optically Reconfigurable Supercomputer for Machine Learning with Hardware Support for Embeddings](https://arxiv.org/abs/2304.01433), ISCA 2023.
- J. Saltzer, D. Reed, D. Clark, [End-to-end arguments in system design](https://web.mit.edu/Saltzer/www/publications/endtoend/endtoend.pdf), ACM TOCS, 1984.
