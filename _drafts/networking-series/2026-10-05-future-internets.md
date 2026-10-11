---
title:  "Future internets"
series: "Networking, Part 4"
series_url: "/programming/networking-series-intro.html"
category: programming
date: 2026-10-05
---

> This is Part 4 of an eight-part [series on networking](/programming/networking-series-intro.html).
>
> 1. **[Networking is IPC](/programming/networking-is-ipc.html)** — one table of every way two parties exchange messages, and the same functions repeating at every boundary.
> 2. **[Naming and binding](/programming/naming-and-binding.html)** — Saltzer's four levels, why IP:port does two jobs, and six ways to carry out a binding.
> 3. **[The Internet as DIFs](/programming/internet-as-difs.html)** — Saltzer's levels inside a RINA layer, a web service read rank by rank, and what overlays like Tailscale are missing.
> 4. **Future internets** — NDN, SCION and RINA each rewrite a different one of Saltzer's levels.
> 5. **[Interconnects are networks](/programming/interconnects-are-networks.html)** — PCIe is a packet network wearing a 1992 bus costume.
> 6. **[Ring buffers](/programming/ring-buffers.html)** — shared memory plus a doorbell, compared on five axes.
> 7. **A packet's path through Linux** *(not yet written)* — from the NIC's descriptor ring to `recv()`, and the ways around it.
> 8. **[From IPC to RPC](/programming/ipc-to-rpc.html)** — what a request/reply protocol adds on top of a flow, and where RPC ends.

An internet is any set of separately run networks joined into one. The Internet, with a capital I, is one of them. X.25 and CYCLADES came before it, and research groups have been building others since the mid-2000s. Three get most of the attention: NDN, SCION and RINA. The Dutch [2STiC](https://2stic.nl/enabling-trust-in-network-services-through-secure-stable-and-transparent-internets.html) programme studies all three side by side.

They are usually listed together as "future Internet architectures", which makes them sound like rivals for one job. Read through [Part 2](/programming/naming-and-binding.html)'s lens, they mostly aren't. Each one rewrites a different one of Saltzer's levels, and leaves the others close to how the Internet has them. [Part 3](/programming/internet-as-difs.html) already covers RINA in depth, so this article spends most of its time on the other two. Then it turns them on the series itself: each one rejects an assumption that Parts 1 to 3 make.

- [One table](#one-table)
- [NDN: name the data](#ndn-name-the-data)
  - [Two packets, three tables](#two-packets-three-tables)
  - [What Saltzer would see](#what-saltzer-would-see)
  - [Trust moves into the data](#trust-moves-into-the-data)
  - [What it costs](#what-it-costs)
- [SCION: choose the path](#scion-choose-the-path)
  - [Isolation domains](#isolation-domains)
  - [Beacons, segments and paths](#beacons-segments-and-paths)
  - [What Saltzer would see in SCION](#what-saltzer-would-see-in-scion)
  - [What it costs, and where it runs](#what-it-costs-and-where-it-runs)
- [RINA and Ouroboros: name the node, repeat the layer](#rina-and-ouroboros-name-the-node-repeat-the-layer)
- [The identifier/locator split](#the-identifierlocator-split)
- [Side by side](#side-by-side)
- [What they say about this series](#what-they-say-about-this-series)
- [Many internets at once](#many-internets-at-once)
- [References](#references)

## One table

| Architecture | Saltzer level it changes | What a packet names | Who picks the path | Status |
| --- | --- | --- | --- | --- |
| Internet | none: it collapses node into attachment point | an interface | routers, hop by hop | deployed |
| NDN | service: name the data, not a host | data | routers, per name prefix; any cache can answer | testbeds |
| SCION | path: the sender picks it and every hop can check it | an AS, then a host inside it | the sender, from path segments | in production |
| RINA / Ouroboros | node, and the layering itself | a node, inside one layer | each layer, within its own scope | prototypes |
| LISP / HIP / ILNP | node, added beside IP | a node ID, mapped to a locator | routers, after a mapping lookup | niche |

The Internet row is Part 2's diagnosis. There is no node level: an IP address names an interface, and DNS maps service names straight to interfaces. Every other row is a repair, and each one repairs a different level:

- **NDN** works at the service level. A packet names the data it wants, and hosts drop out of the request.
- **SCION** works at the path level. The sender chooses a route and writes it into the packet.
- **RINA** works at the node level and on the layering. Addresses name nodes, and the same layer repeats at every scope.
- **The identifier/locator split** also works at the node level, but keeps IP and adds a mapping beside it.

NDN and SCION also pull in opposite directions on a second axis. [Navigate or declare](/programming/navigate-or-declare.html) asks whether a caller walks a system's structure or names what it wants and lets the system find the way. NDN is the most declarative network ever built: you say what you want, and any copy will do. SCION is navigational on purpose: the sender sees the structure because it wants control over it.

## NDN: name the data

Van Jacobson started from an observation in a [2006 talk](https://www.youtube.com/watch?v=oCZMoY3q2uM). The Internet was designed for conversations between hosts, but most of what it carries is people fetching named content. Who serves the bytes rarely matters. What matters is which bytes you get, and whether they are the right ones. His group built that idea into CCN ([*Networking Named Content*](https://dl.acm.org/doi/10.1145/1658939.1658941), CoNEXT 2009). [Named Data Networking](https://named-data.net/) continued it from 2010, as one of four projects in the US National Science Foundation's Future Internet Architecture program.

### Two packets, three tables

NDN has two packet types, and neither carries an address:

- An **Interest** carries the name of the data it wants, such as `/ucla/videos/demo.mpg/v3/s0`.
- A **Data** packet carries that name, the content, and the producer's signature.

Names are hierarchical, like a pathname, and usually readable. They are not hashes. A Data packet never carries a hash of itself. But an Interest can add the packet's SHA-256 digest as the last name component, and then only that exact Data packet matches.

Each NDN router, a *forwarder*, keeps three tables:

- The **Content Store** caches Data packets that passed through.
- The **Pending Interest Table** (PIT) records each Interest that is waiting for Data, and the faces it came in on. A *face* is NDN's word for an interface, a tunnel, or a local application.
- The **Forwarding Information Base** (FIB) maps name prefixes to the faces that lead toward producers.

```
             Interest: /ucla/videos/demo.mpg/v3/s0
 consumer ─────────────────► R1 ─────────────────► R2 ─────────────────► producer
                                                                         (serves /ucla/videos)
             at each router:
             1. Content Store: is the Data cached? Then answer from here.
             2. PIT: is this name already pending? Then add the face and stop.
             3. FIB: longest-prefix match on the name, and forward.

             Data: name + content + producer's signature
 consumer ◄───────────────── R1 ◄───────────────── R2 ◄───────────────── producer

             at each router: send it out every face in the PIT entry,
             cache a copy, and delete the entry
```

Data retraces the Interest's path, because each router remembers where the Interest came from. Nothing else in the packet says where to go. That one rule has several consequences:

- **One Interest brings back at most one Data packet.** The receiver controls the flow by how many Interests it sends.
- **Multicast is free.** If a thousand consumers ask for the same segment, each router forwards the first Interest and adds the other faces to its PIT entry. One copy of the Data comes back and fans out.
- **Nothing arrives unasked.** A router drops Data that matches no pending Interest. A producer can't push to a consumer, and an attacker can't spray Data at one.

### What Saltzer would see

Part 2 described delivery as three bindings in turn: a service to a node, the node to an attachment point, and the attachment point to a path. NDN drops the first two from the packet. An Interest names the service directly, at the granularity of one packet of data. No node or attachment point appears in it. The FIB still has faces, so attachment points still exist inside each router. But they never appear on the wire as names that a sender has to know.

Saltzer's DIALOG example asked what happens when a service moves to another node. In NDN, the question mostly disappears. The data has no home that the name points at. Any router that cached it, or any producer that serves the prefix, can answer.

### Trust moves into the data

The Internet secures channels. TLS proves you are talking to `example.com`, and then trusts whatever that server sends. NDN can't work that way, because a cache answers as often as the producer does. So it secures each packet. Every Data packet must carry a signature, and the signature can carry a *KeyLocator*, usually the name of the key that made it. The consumer checks the signature, whoever delivered the bytes.

That moves the hard question, not removes it. A signature proves a key signed the data. It doesn't prove that key may speak for `/ucla/videos`. NDN answers that with *trust schemas*: rules that say which key names may sign which data names. That is a name → key binding service, the subject of the whole [identity series](/programming/identity-series-intro.html).

### What it costs

- **Routing on names.** Routers forward on name prefixes, so the routing system has to carry name prefixes. That works today only because names are hierarchical and group by prefix, as IP addresses do. Structure comes back because routing needs it. For names the global routing system doesn't know, an Interest can carry a *forwarding hint*: the name of a network that does know, such as the producer's provider. That is a locator, added back for the cases where the name alone can't be routed.
- **Pull only.** Nothing arrives unasked, so anything that looks like a push has to be built from Interests: a consumer polls, or keeps an Interest waiting until data exists. Phone calls, notifications and server-initiated messages all need a pattern on top.
- **Names are visible.** Every router reads every name, so it sees what you ask for, unless the application encrypts or obscures its names.
- **State per Interest.** Every router keeps a PIT entry for every pending Interest. That is what gives NDN free multicast and no unasked traffic. It also means an attacker can fill PITs with Interests for names that will never be answered.

NDN fits content distribution, where many receivers want the same bytes and nobody cares who serves them. It fits worst for a private conversation between two hosts, which is the job IP was built for. It runs today as a research testbed, an overlay of about twenty routers on four continents.

## SCION: choose the path

The Internet's path level belongs to BGP. Each network picks its next hop by its own policy. Senders get whatever path results, can't see it, and can't change it. A misconfigured or malicious network can announce someone else's prefix and pull their traffic toward itself. [SCION](https://scion-architecture.net/) gives the path level to the sender. It came out of Adrian Perrig's group, first at Carnegie Mellon and then at ETH Zurich, with the [first paper](https://doi.org/10.1109/SP.2011.45) in 2011.

### Isolation domains

SCION groups autonomous systems (ASes) into **isolation domains** (ISDs), for example one per jurisdiction. Each ISD agrees on a **Trust Root Configuration** (TRC): a signed document that lists the ISD's root keys and the rules for changing them. A few **core ASes** in each ISD manage the TRC and connect the ISD to other ISDs.

There is no single global root of trust. Each ISD trusts its own TRC, and a compromised or careless ISD can't forge paths inside another one. This is the trust structure of the Web PKI turned inside out. In the Web PKI, every browser trusts every CA for every name, as the [hosts article](/programming/identity-of-hosts.html) explains. In SCION, trust is scoped by domain.

### Beacons, segments and paths

Paths are built in three steps.

1. **Beaconing.** Core ASes send *beacons* down through their ISD, and across to other cores. Each AS a beacon passes through adds a *hop field*: the interface it came in on, the interface it leaves by, and a MAC that only that AS can compute and check. Each AS also signs its entry, under a certificate that chains to the TRC.
2. **Registration.** The beacons become *path segments*. An *up segment* leads from a leaf AS to a core. A *core segment* links two cores. A *down segment* leads from a core to a leaf. ASes register their segments with path servers, so others can look them up.
3. **Combination.** A host that wants to reach another looks up segments, combines up to three of them into one path, and writes the whole path into each packet's header.

```
 ISD 1                                ISD 2
┌────────────────────┐               ┌────────────────────┐
│ core AS A ═════════╪═══════════════╪═════════ core AS C │
│    │               │  core segment │               │    │
│    │ up segment    │               │  down segment │    │
│    │               │               │               │    │
│ leaf AS X          │               │          leaf AS Y │
│    host h          │               │             host k │
└────────────────────┘               └────────────────────┘

 the path h writes into each packet to k:
   up segment X → A  +  core segment A → C  +  down segment C → Y
 one hop field per AS: in interface, out interface, and a MAC only that AS can check
```

A border router reads the next hop field, checks its own MAC, and sends the packet out the interface the field names. It keeps no table of destinations. SCION calls this *packet-carried forwarding state*: the packet itself says where it goes, and every router on the way can confirm the route was really issued.

A SCION address has two parts: the ISD and AS, then a host address that only means something inside that AS, such as `1-ff00:0:110,10.0.0.1`. Inside an AS, packets ride over ordinary IP and UDP.

### What Saltzer would see in SCION

SCION rewrites exactly one level. The path, which IP leaves to routers and hides from senders, becomes something the sender names. The sender sees several paths to a destination and picks one by latency, by cost, or by which ISDs it avoids. It can use several at once, and switch to another the moment one fails, without waiting for routing to converge.

It leaves the other levels where the Internet has them. A host is still named by an AS and an address inside that AS: an attachment point, with no node level above it. Services are still found by DNS and port numbers. A host that moves to another AS still gets a new address. SCION repairs the path and the trust beneath it, and leaves Part 2's node and service problems alone.

That is the navigational choice, made deliberately. [Navigate or declare](/programming/navigate-or-declare.html) argues that exposing structure buys speed, predictability and control, and costs flexibility. SCION wants the control. A bank that must prove its payments never crossed a given country needs to see and choose the path, and a declarative network can't offer that.

### What it costs, and where it runs

- **Bigger headers.** Every packet carries its whole path, with one 12-byte hop field per AS.
- **Smarter hosts.** Someone has to look up segments, combine them, and choose. Usually that's a daemon on the host, or a library.
- **A new control plane.** Beaconing, path servers and a PKI per ISD replace BGP. Paths expire and must be refreshed.

SCION is the only one of the three in production. The Secure Swiss Finance Network has carried the Swiss SIC and euroSIC payment systems over SCION since June 2022. Part of the reason is that it changes the least. Hosts still have IP addresses inside their AS, applications still use sockets, and only the routing between ASes is new. A network can join without anyone else changing. That is the same deployment advantage [Worse is Better](/programming/worse-is-better-examples.html#tcpip-vs-rina) credits to IP itself.

## RINA and Ouroboros: name the node, repeat the layer

[Part 3](/programming/internet-as-difs.html) covers both, so briefly: RINA repairs the node level, and then changes the layering.

- **The node gets a name.** An address names an IPC process, which is a node in one layer, never an interface. It depends on location, but only inside its own layer. Applications are found by name through the layer's directory, and addresses never leave the layer.
- **The layer repeats.** The same IPC layer, a DIF, repeats at every scope, from one link to the whole Internet, with policies chosen per scope.

Ouroboros keeps that core and changes several details, which [Part 3 lists](/programming/internet-as-difs.html#ouroboros-a-descendant). Both remain prototypes.

Unlike NDN and SCION, RINA doesn't rewrite one level and leave the rest. It keeps all four of Saltzer's levels apart, and repeats them in every layer. That is its strength. It is also where its costs come from:

- **Everything changes at once.** A new application API, a new layer under it, and new management in every layer. SCION asks an AS to change its border routers. RINA asks every host, router and application to adopt a new model, and gives no single step that pays off on its own.
- **Policy is open-ended.** "Only policies to specify" means someone has to choose them, for every layer, and two layers with different policies have to work together. The Internet fixed its policies in protocols. RINA moves that work to whoever designs each network.
- **Enrollment assumes someone to enroll with.** A DIF admits members under one enrollment policy. That fits a network one organization runs. Who sets the policy for a DIF that spans the whole Internet, run by providers that don't trust each other, is the question SCION's isolation domains were built to answer. I haven't found a full answer to it in the RINA literature.
- **Every rank adds a header.** Each DIF carries its own addresses and connection ids, and runs the same mechanisms again. Proponents answer that today's stacks already pay this for VXLAN, MPLS and tunnels, without sharing any mechanisms between them.

RINA fits networks where one operator controls several scopes at once: a datacenter, a carrier's access and core networks, the layers inside one machine. It fits worst where it most needs to win: the public Internet, where nobody controls every scope, and every application already speaks IP.

## The identifier/locator split

The best-known repairs to the node level keep IP and add a stable identifier beside it:

- **[LISP](https://www.rfc-editor.org/info/rfc9300/)**, the Locator/ID Separation Protocol, splits addresses into endpoint identifiers (EIDs) and routing locators (RLOCs). Routers at the edge of a site wrap packets in an outer header addressed to a locator, after asking a mapping system which locator serves the EID. It was first built to slow the growth of the global routing table. Its current specification presents it mainly as a way to build overlays.
- **[HIP](https://www.rfc-editor.org/info/rfc7401/)**, the Host Identity Protocol, names each host by a public key. Applications use a 128-bit hash of the key where they would use an IPv6 address (IPv4 applications get a 32-bit local stand-in), and IP addresses become locators that can change under a running connection.
- **[ILNP](https://www.rfc-editor.org/info/rfc6740/)**, the Identifier-Locator Network Protocol, in its IPv6 form, splits the 128 bits of an IPv6 address into a 64-bit locator and a 64-bit node identifier.

Part 3 shows the same split [in overlays](/programming/internet-as-difs.html#overlays-that-keep-the-levels-apart): devp2p, iroh and validator networks name a node by a key and locate it by IP:port.

Day considers the split a wrong turn. His book calls "the current infatuation with the 'loc/id split' problem" a dead end. The trouble, in his reading, isn't that IP addresses are locators. An address should depend on location; that is what lets routers aggregate. The trouble is that IP addresses name the wrong object. As he put it on the end2end list in 2006: "IP addresses by naming the interface are points of attachments." And: "We have no application names and no node addresses." A split adds a second namespace and a mapping system beside the broken one. RINA names nodes to begin with, so there is nothing to split.

That is a fair criticism of IP, but it doesn't make the mapping go away. Something still has to map a stable name to a changing location. In RINA, that is each DIF's directory, which maps application names to addresses, and is updated when an application moves. The application name is the identifier, and the address is the locator. RINA scopes the split to one layer and repeats it at every rank, instead of adding it once beside IP. [Navigate or declare](/programming/navigate-or-declare.html) makes the general point: the indirection never disappears, you only choose who carries it. The overlays in Part 3 make the practical one. They carry the split themselves, over IP, and they work.

## Side by side

| | Internet | NDN | SCION | RINA |
| --- | --- | --- | --- | --- |
| What a request names | an interface and a port | data | an AS and a host, plus a path | an application |
| Who chooses the path | routers | routers, per name prefix; a cache can answer early | the sender | each layer, within its scope |
| Where trust is anchored | the Web PKI, above the network | the producer's key, on every packet | the TRC, per ISD | enrollment, per DIF |
| What an application does | connect a socket to IP:port | send an Interest for a name | open a socket and pick a path | ask for a flow to a name, stating what it needs |
| Runs over IP today? | — | yes, over UDP tunnels | yes, over IP inside each AS | yes, through shim layers over Ethernet and UDP |

What each one leaves alone says as much as what it changes:

- **NDN** changes what a packet names, and keeps the Internet's shape: a thin waist, simple routers, and routing on hierarchical prefixes.
- **SCION** changes who picks the path, and keeps host-centric naming. A host is still an address inside a network.
- **RINA** changes the most. It keeps nothing from IP's naming, and builds the same layer at every scope.

## What they say about this series

Parts 1 to 3 read the Internet through two lenses: Day's IPC model and Saltzer's naming. NDN and SCION are useful here because neither fits those lenses cleanly. Each one rejects something both lenses take for granted.

**NDN rejects "networking is IPC".** Metcalfe's line, and Day's whole architecture, start from two processes that want to talk. Jacobson starts from the opposite claim: the Internet was built for conversations between hosts, and most of what it carries now is dissemination, many receivers fetching the same named bytes. Saltzer's levels share Day's starting point. They name a *destination*, and NDN has none. Read through Saltzer, NDN rewrites the service level. Read on its own terms, it drops the question Saltzer was answering. A RINA reading puts it back in the frame: fetching and caching named data is a distributed application, which can run over a DIF like any other. Both readings hold. Which one you prefer depends on whether you think conversation or dissemination is the common case.

**SCION rejects "the path is the layer's business".** Part 2 had routing do the last binding "without anyone noticing". Part 1 said choosing the scope should be the system's job, not the programmer's. Inside a DIF, the route is internal: the user names a destination, and the layer picks the way. SCION's answer is that this is only safe when you trust whoever picks. Across networks run by different organizations, in different countries, that trust is what's missing, so the sender takes the path back. It pays the navigational price: more work for the host, and less freedom for the network to change underneath it.

**Both start from trust.** This series has judged architectures by how cleanly they keep names apart. NDN and SCION were shaped as much by a different question: who has to be trusted, and for what? NDN trusts the producer's key, not the channel. SCION trusts each ISD's root, not one global one. RINA's answer, enrollment per DIF, is the one this series has examined least. It is easy to see inside a network that one operator runs, and much harder across many.

So the lenses hold, with limits. "The same functions at every boundary" holds for conversations, and Parts 5 to 8 are about conversations: a PCIe link, a ring buffer, an RPC. Whether the public Internet should be built around conversations is the question NDN raises. This series doesn't settle it.

## Many internets at once

The 2STiC programme makes a case that changes the question. It is a Dutch research programme, started in 2019, that has involved AMS-IX, NLnet Labs, SIDN Labs, SURF, TU Delft, and the universities of Amsterdam and Twente. Its argument: the Internet isn't broken. The problem it solves has changed. So stop patching one internet to fit every new application, and run new internets beside it. Their example is a delivery drone. An urban air traffic control service steers it over SCION, because that traffic must not be hijacked. The people who send and receive the package reach the same service over the ordinary Internet. Applications pick the internet that fits.

RINA reads the same idea from below. The Internet already is many internets, stacked: Part 3's [rank table](/programming/internet-as-difs.html#a-web-service-rank-by-rank) found seven layers between an HTTP service and a machine's own sockets, each with its own names. RINA's complaint is not that there are many. It is that each one is built differently.

And the narrow waist keeps winning, now as the layer underneath. NDN runs over UDP tunnels. SCION runs over IP inside each AS. RINA reaches the world through shim layers over Ethernet and UDP. Every future internet is deployed first as an overlay on the present one. Whichever succeeds will, for a long time, be one more layer in Part 3's table.

## References

- J. Saltzer, [RFC 1498, *On the Naming and Binding of Network Destinations*](https://www.rfc-editor.org/info/rfc1498/), 1993 (written 1982).
- C. Hesselman et al., [Enabling trust in network services through secure, stable, and transparent internets](https://2stic.nl/enabling-trust-in-network-services-through-secure-stable-and-transparent-internets.html), 2STiC, 2019.
- V. Jacobson, [A New Way to Look at Networking](https://www.youtube.com/watch?v=oCZMoY3q2uM), Google Tech Talk, 2006.
- V. Jacobson et al., [Networking Named Content](https://dl.acm.org/doi/10.1145/1658939.1658941), CoNEXT 2009.
- [NDN Packet Format Specification](https://docs.named-data.net/NDN-packet-spec/current/), including names, implicit digests and forwarding hints.
- Y. Yu et al., [Schematizing Trust in Named Data Networking](https://dl.acm.org/doi/10.1145/2810156.2810170), ICN 2015.
- X. Zhang et al., [SCION: Scalability, Control, and Isolation on Next-Generation Networks](https://doi.org/10.1109/SP.2011.45), IEEE S&P 2011.
- [SCION documentation: overview](https://docs.scion.org/en/latest/overview.html).
- SIX, [Secure Swiss Finance Network](https://www.six-group.com/dam/download/banking-services/events/2022/ssfn.pdf), 2022.
- J. Day, *Patterns in Network Architecture: A Return to Fundamentals*, Prentice Hall, 2008.
- J. Day, [post to end2end-interest](https://mailman.postel.org/pipermail/end2end-interest/2006-April/005911.html), April 2006.
- D. Farinacci et al., [RFC 9300, *The Locator/ID Separation Protocol (LISP)*](https://www.rfc-editor.org/info/rfc9300/), 2022.
- R. Moskowitz et al., [RFC 7401, *Host Identity Protocol Version 2 (HIPv2)*](https://www.rfc-editor.org/info/rfc7401/), 2015.
- R. Atkinson, S. Bhatti, [RFC 6740, *Identifier-Locator Network Protocol (ILNP) Architectural Description*](https://www.rfc-editor.org/info/rfc6740/), 2012.
