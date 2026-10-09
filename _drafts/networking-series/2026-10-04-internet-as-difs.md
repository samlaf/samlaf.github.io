---
title:  "The Internet as DIFs"
series: "Networking, Part 3"
series_url: "/programming/networking-series-intro.html"
category: programming
date: 2026-10-04
---

> This is Part 3 of a seven-part [series on networking](/programming/networking-series-intro.html).
>
> 1. **[Networking is IPC](/programming/networking-is-ipc.html)** — one table of every way two parties exchange messages, and the same functions repeating at every boundary.
> 2. **[Naming and binding](/programming/naming-and-binding.html)** — Saltzer's four levels, why IP:port does two jobs, and why every many-to-many case needs a translator.
> 3. **The Internet as DIFs** — Saltzer's levels inside a RINA layer, a web service read rank by rank, and what overlays like Tailscale are missing.
> 4. **[Interconnects are networks](/programming/interconnects-are-networks.html)** — PCIe is a packet network wearing a 1992 bus costume.
> 5. **[Ring buffers](/programming/ring-buffers.html)** — shared memory plus a doorbell, compared on five axes.
> 6. **A packet's path through Linux** *(not yet written)* — from the NIC's descriptor ring to `recv()`, and the ways around it.
> 7. **[From IPC to RPC](/programming/ipc-to-rpc.html)** — what a request/reply protocol adds on top of a flow, and where RPC ends.

[Part 2](/programming/naming-and-binding.html) ended on a pattern. Almost every many-to-many binding on the Internet comes from inserting a new layer or a translator: a bond, a proxy, a NAT table, a connection ID. John Day reads that pattern as evidence that the layers were drawn wrong. This article applies Saltzer's four levels inside one layer of Day's architecture, RINA. Then it reads today's Internet rank by rank, as a stack of layers that each rebuild some of the same machinery. Last, it asks why NAT survives when overlays already exist above IP.

- [A layer is a DIF](#a-layer-is-a-dif)
- [Saltzer's levels inside one DIF](#saltzers-levels-inside-one-dif)
- [Why recurse, if multihoming and mobility are already solved?](#why-recurse-if-multihoming-and-mobility-are-already-solved)
- [Security: enrollment and flow allocation](#security-enrollment-and-flow-allocation)
- [Internet vs. RINA](#internet-vs-rina)
- [A web service, rank by rank](#a-web-service-rank-by-rank)
- [Upper layers, but no common one](#upper-layers-but-no-common-one)

## A layer is a DIF

In RINA a layer is a **DIF** (distributed IPC facility): a set of cooperating **IPC processes**, one per member system, that together give flows to the applications above. [Part 1](/programming/networking-is-ipc.html) covers what every DIF does. Two points matter here:

- **A DIF has a scope**: one link, a datacenter, a provider, the whole Internet. Every DIF runs the same mechanisms, with policies chosen for its scope. DIFs stack, and Day calls a DIF's position in the stack its **rank**.
- **There is no separate transport layer.** Every DIF does its own data transfer, error control and flow control. In Day's view, IP and TCP together are one layer.

### Ouroboros, a descendant

RINA isn't the only recursive design. [Ouroboros](https://ouroboros.rocks/wiki/Ouroboros) grew out of the IRATI team's work implementing RINA. Dimitri Staessens and Sander Vrijders started a fresh prototype in 2016, and by late 2017 it had diverged enough that they stopped calling it RINA. It keeps the core idea: one layer design, repeated at every scope, and applications that ask for a flow to a name and state what they need from it. It changes several details:

- **Two kinds of layer.** Unicast and broadcast are separate mechanisms, so Ouroboros has unicast layers and broadcast layers. Enrolling in a layer means joining a broadcast group.
- **Reliability moves into the application.** Retransmission and flow control run in a library linked into each application, not in the layer. RINA assumes the IPC between an application and its layer is itself reliable. Ouroboros doesn't, which is the end-to-end argument applied to RINA.
- **No common management protocol.** Ouroboros dropped CDAP, RINA's single protocol for layer management, which its authors considered overengineered.
- **Registration happens outside the application.** A management tool registers names in a layer and binds them to programs. The directory that maps names to addresses is a distributed hash table.

Ouroboros runs today in user space on Linux, BSD and macOS, over Ethernet, UDP or another Ouroboros layer. Like RINA, it is a prototype, not a deployment. This series uses RINA's vocabulary, DIFs, ranks and IRATI's list of components, because most of the literature does. Where the two designs differ, the text follows RINA.

## Saltzer's levels inside one DIF

Saltzer's four levels appear in every DIF, at every rank. Within DIF N:

| Saltzer | RINA in DIF N | How a sender gets to the next row |
| --- | --- | --- |
| service | **application name**: a user of DIF N | the directory: application name → address of the member where it's registered |
| node | **address** of an IPC process in DIF N: location-dependent, but not tied to any interface | routing: a route to that address |
| path | **route**: a sequence of N-addresses, computed by DIF N's routing | forwarding: for each next hop, pick a working point of attachment |
| point of attachment | a **flow**, or port, into DIF N−1 that the IPC process reaches neighbors through | DIF N−1 takes over from here |

The rows are in a different order from Saltzer's, on purpose. Saltzer's chain runs service → node → attachment point → path. In a DIF, routing runs on node addresses, so the path comes before the attachment point. Routing chooses which members to go through. Forwarding then chooses which attachment reaches the next one. Because those are separate steps, multihoming is easy. A node with two attachments keeps one address, routes target the address, and forwarding uses whichever attachment works. The IPC process learns which attachments reach which neighbors when it enrolls with them.

A client in RINA asks the DIF for a flow to an application name, such as "api-front". The DIF's directory finds that application's current address. The name says what, and the address, internal to the DIF, says where.

### A point of attachment is a flow from above, an address from below

What is a point of attachment, exactly? From DIF N's side, it is a flow into DIF N−1. The IPC process holds a port-id for it and nothing else. It never sees an address in DIF N−1, because addresses never leave their DIF. When it needs a neighbor, it asks DIF N−1 for a flow to that neighbor's *name*, and DIF N−1 resolves the name in its own directory.

From inside DIF N−1, the same attachment is an address: the address of the IPC process that delivers the flow. So one rank's node is the next rank's point of attachment:

```
rank N+1   application name ──► address(N+1) ──► point of attachment = a flow into DIF N
                                                         │ which is reached at
rank N                                       address(N)  ◄┘   ──► point of attachment = a flow into DIF N−1
                                                                        │
rank N−1                                                      address(N−1) ◄┘ ...
```

This is Saltzer's definition of an address, made recursive. He said an object's address is the name of whatever it's bound to. A node at rank N+1 is bound to a flow, and that flow lands at an address at rank N. That address is a node name at rank N and an attachment point at rank N+1. There is no separate kind of name for attachment points.

### Whose name is registered where

The application names differ at every rank, because each DIF has different users. Only the top DIF's users are end applications. The users of every lower DIF are the IPC processes of the DIF above, and an IPC process is itself an application with a name of its own.

```
 DIF            registered user (by name)           member IPC process on host H, and its address
 ──────────────────────────────────────────────────────────────────────────────────────────────────
 internet-DIF   "web-server"  (an application)  ◄── IPC process "inet@H",  address 7.12
                                                          │ is itself a user of ↓
 wifi-DIF       "inet@H"      (the IPCP above)  ◄── IPC process "wifi@H",  address 3
                                                          │ uses the radio ↓
```

`inet@H` has one name and two addresses:

- **Name `inet@H`:** assigned once, and registered in each lower DIF it uses.
- **Address `7.12` in internet-DIF:** its node address.
- **Address `3` in wifi-DIF:** where its point of attachment lands.

Nothing has to be kept in sync across ranks. When internet-DIF needs to reach a neighboring IPC process, it asks wifi-DIF for a flow to that neighbor's name, and wifi-DIF looks the name up in its own directory.

The Internet conflates the two. The IP layer's "name" in the link layer is its IP address, because ARP looks a neighbor up by IP address. So an IP address is both the name the link layer knows it by and the node's address at L3. RINA keeps a name and an address separate at every rank. Three things follow:

- **Multihoming is native.** A node with two attachments is one address in DIF N with two lower flows, and losing one is a local failover.
- **Mobility is native.** Moving changes the lower attachments, not the address in the DIF above.
- **Connections survive both.** Applications hold a **port-id**, a local handle the DIF hands out when it sets up a flow. Connections are identified by connection-endpoint ids internal to the DIF. Neither is an address, so an address change doesn't break a flow. QUIC's connection IDs are the same split, added to the Internet after the fact.

## Why recurse, if multihoming and mobility are already solved?

Recursion isn't the multihoming fix. It's how RINA handles **scope**, and it is also part of what makes mobility cheap:

- **Bounded routing state.** A DIF routes only among its own members. Nesting small DIFs under larger ones keeps every routing table small, as hierarchy does, but with whole layers rather than address prefixes.
- **Policies per scope.** A lossy radio link wants aggressive local retransmission; a backbone wants the opposite. Each DIF picks its own error-control, flow-control and security policies.
- **Mobility stays local.** A phone moving between cells changes attachments in a small access DIF. The DIF above sees the same node address, and only the small DIF does any updating. Without the extra layer, every move would be visible network-wide.
- **Isolation.** Membership is by enrollment. A provider's internal DIF is invisible to its customers, and a VPN is just one more DIF.

The number of layers isn't fixed: you add a DIF wherever a new scope or policy is needed. The Internet already stacks layers this way, below IP and above it. [The upper layers section](#upper-layers-but-no-common-one) looks at the ones above.

## Security: enrollment and flow allocation

- **Enrollment.** To join a DIF, an IPC process must authenticate under the DIF's enrollment policy. Non-members can't address members at all, because addresses never leave the DIF.
- **Flow allocation.** An application asks for a flow by destination application name. The DIF looks the name up in its directory and applies access control before any flow exists. The destination can refuse.

Proponents argue this makes firewalls unnecessary. That claim comes from research prototypes, not from deployments at scale.

## Internet vs. RINA

| Concern | Internet | RINA |
| --- | --- | --- |
| service name | DNS name + well-known port | application name, in the DIF's directory |
| node name | none | the IPC process's address in the DIF |
| attachment point | IP address (L3), MAC (L2) | a flow into the DIF below |
| connection identity | four values: two addresses, two ports | connection-endpoint ids inside the DIF; the application holds a port-id |
| directory | DNS, outside the stack | each DIF's own, used when a flow is set up |
| access control | firewalls on addresses and ports | enrollment, and checks when a flow is set up |
| layers | a fixed stack, plus ad hoc tunnels and overlays | as many DIFs as scopes need, one set of mechanisms |

## A web service, rank by rank

Take an ordinary service. A client reaches `api.example.com`. A front proxy on a cloud VM answers on the public address `203.0.113.7:443`. It sends `/orders` to a backend at `10.0.0.4:8080` and `/search` to one at `10.0.0.5:8080`, over the cloud provider's private network.

Read as DIFs, the HTTP service is an upper layer with three members: the client, the front and a backend. It runs over two different DIFs at once. From the client to the front, it uses the public internet. From the front to the backend, it uses the cloud's virtual network. The front is a relay between them.

```
                         client               front                 backend
 HTTP service              ●───────────────────●─────────────────────●
                           │                   │                     │
 public internet           ●───────────────────●                     │
                      198.51.100.9        203.0.113.7                │
                                               │ cloud NAT           │
 cloud VNet                                    ●─────────────────────●
                                           10.0.0.2              10.0.0.4
                                               │                     │
 datacenter fabric                             ●─────────────────────●
                                            host A                host B
```

The VM holds only its private address, `10.0.0.2`. The public address belongs to the cloud's network, which binds it to the private one. In RINA terms, the virtual network and the internet are two DIFs, and that NAT is a workaround at their border.

Below these, the public internet runs over provider backbones, and every DIF eventually runs over links. Here are Saltzer's four levels at each rank:

- **service:** the names of the DIF's users, which is what you ask it to reach;
- **node:** a member's address within the DIF;
- **attachment point:** how a member attaches to the DIF below;
- **path:** the route between members.

Bold marks where TCP/IP collapses two levels into one.

| Rank (DIF) | Service | Node | Attachment point | Path |
| --- | --- | --- | --- | --- |
| HTTP service | `api.example.com` + `/orders`, `/search` | **none of its own: borrows the front's and backends' IP:port** | TCP connections: client → `front:443`, front → `10.0.0.4:8080` | client → front → backend, chosen by DNS and then the front's table of paths |
| public internet (IP and TCP together) | **IP:port: a well-known port standing in for the name** | **IP address** | **the same IP address: it names the interface** | BGP AS paths between providers, IGP routes inside each, all computed on attachment points |
| cloud VNet | private IP:port listeners, such as the backend's `:8080` | private IP: it survives moves between hosts, so it's node-like | the current physical host's address in the fabric | VNet routes, mostly a single hop in the provider's software-defined network |
| provider backbone | its users: customers' border routers | router ID or loopback address, kept apart from interface addresses | router interfaces on long-haul links | MPLS paths or segment-routing lists, traffic-engineered |
| datacenter fabric | its users: virtual networks and their VMs (private IPs) | host address in the fabric | host NIC and top-of-rack switch port | ECMP across the leaf-spine; the private IP → host address mapping is its directory |
| link (Ethernet LAN or VLAN) | its users: IP interfaces; ARP is the directory (IP → MAC) | **MAC address: it also names the interface** | switch port | spanning tree and learning bridges |
| node-local (inside one machine) | socket path, or `127.0.0.1:port` | — (a single node) | file descriptor, in the kernel | none: a copy in kernel memory |

Below the link sits the medium itself: fiber, copper or radio. Day doesn't count it as a DIF, since it names and routes nothing. IRATI wraps such media in "shim DIFs" so the layer above sees the usual API.

The backbone and fabric rows follow published designs, not any one provider's documentation. Microsoft's [VL2](https://www.microsoft.com/en-us/research/publication/vl2-a-scalable-and-flexible-data-center-network/) gives each server an application address and a separate location address, with a directory system that maps one to the other. Google's [Andromeda](https://www.usenix.org/conference/nsdi18/presentation/dalton) describes the virtual network layer that runs over such a fabric. Backbones keep a router's identity apart from its interfaces for the same reason: a loopback address stays reachable when any one link fails.

Reading down the table:

- **The levels are clean below the internet.** The backbone separates router IDs from interfaces. The fabric separates private IPs from host addresses. The datacenter world rebuilt the missing node level wherever it controlled both ends.
- **The levels collapse where TCP/IP is exposed.** That is the internet row, and the HTTP row, which borrows the internet's names. The link row collapses too, as Saltzer noted for Ethernet in 1982.

The node-local row shows both models side by side. A TCP port on `127.0.0.1` is a well-known name that any local user can claim: Part 2's unauthenticated registration. A Unix socket works more like a DIF. Its name is a filesystem path, and the directory's permissions decide who may create it. The kernel tells the server who each client is when the connection is set up (`SO_PEERCRED`), so the server can accept or refuse per peer. Docker's socket, gated by the `docker` group, works this way.

### Overlays that keep the levels apart

Some networks built over IP keep Saltzer's levels apart from the start. Each names a node by a key and locates it by IP:port:

| Rank (DIF) | Service | Node | Attachment point | Path |
| --- | --- | --- | --- | --- |
| devp2p (Ethereum) | subprotocols, such as `eth/68` and `snap/1` | node ID, derived from the node's public key | IP:port from the node's signed discovery record | Kademlia distance on node IDs to find peers, then gossip through them |
| BFT validator network | one channel per message type | validator public key | IP:port from the validator set's peer list | direct: a full mesh |
| [iroh](https://docs.iroh.computer/concepts/endpoints) | protocols, chosen by ALPN | EndpointId: an Ed25519 public key | home relay URL and direct IP:ports, from a record signed by that key | direct when NAT traversal succeeds, otherwise through the relay |

A node named by a key and located by IP:port is the identifier/locator split. LISP (the Locator/ID Separation Protocol) and HIP (the Host Identity Protocol) proposed the same split for IP itself. These overlays get it without changing IP, because they control both ends.

One caveat: in devp2p, "routing on node names" holds for discovery's Kademlia table. Blocks and transactions spread by gossip over whatever peers a node has.

## Upper layers, but no common one

Upper layers do exist on top of TCP/IP, and you can stack as many as you like. The accurate claim is narrower: TCP/IP has no *common* upper layer in its architecture. Each application builds its own, and each one builds only part of a DIF.

### The web service, component by component

Take the HTTP service from the table above, with its client, front and backends, and check it against the components every DIF has, as [Part 1](/programming/networking-is-ipc.html) lists them: An SDU (service data unit) is RINA's word for a message a user hands to a DIF.

| RINA component | HTTP service today | Status |
| --- | --- | --- |
| ***Data transfer*** | | |
| SDU delimiting | HTTP message framing; HTTP/2 frames | has |
| data transfer | requests and responses | has |
| relaying and multiplexing | proxies relay; HTTP/2 multiplexes streams | has |
| SDU protection | TLS, but per hop, and by default only from client to front | partial |
| ***Data transfer control*** | | |
| transmission, retransmission, flow control | TCP or QUIC underneath; HTTP/2 adds per-stream flow control | borrowed |
| ***Layer management*** | | |
| addresses | none: IP:port from below | missing |
| namespace management | hostnames from DNS registrars; paths made up per front | borrowed, ad hoc |
| directory | two unrelated ones: DNS (hostname → IP) and the front's path map (path → backend) | borrowed, static |
| application registration | none: a backend can't announce "I serve `/orders`", so the front polls it with health checks | missing |
| enrollment | none: clients just connect, and backends join when someone edits the front's config | missing |
| authentication when joining | TLS authenticates the server's name only | partial |
| flow allocation | TCP connect, then TLS, then a request: no way to ask for properties, and access control only through the front's own checks | partial |
| routing between relays | none: each relay's next hop is static config, and a CDN → origin chain is wired by hand | missing |
| shared state about the layer (RINA's RIB) and a protocol to manage it (CDAP) | none: each proxy holds its own static view | missing |
| resource allocation | per-front rate and connection limits | ad hoc |
| security management | certificates and firewall rules, each configured separately | ad hoc |
| mobility, multihoming | tied to IP addresses | missing |

HTTP moves data well. What it lacks is everything that lets a layer manage itself: addresses of its own, applications that register, members that enroll, relays that route among themselves, and a shared picture of who is where. TCP/IP pushes all of that onto people and config files: DNS records, proxy configs, health checks.

### How close other overlays come

Other overlays fill some of those gaps. Here are the layer management rows again, for the HTTP service and three overlays that each go further:

| Component | HTTP service | Service mesh (Istio) | Tailscale | iroh |
| --- | --- | --- | --- | --- |
| addresses | missing: IP:port from below | borrowed: pod IPs | **has**: a `100.x.y.z` per machine, kept across networks | **has**: the EndpointId, a public key |
| directory | DNS and the front's path map, both static | **has**: the control plane pushes live endpoints to every sidecar (xDS) | **has**: the coordination server sends each machine its peers' keys and current endpoints | **has**: signed records over DNS, or mDNS on a LAN |
| application registration | missing: health checks | **has**: pods register through Kubernetes service discovery | missing: a service is a port on a machine's address | partial: an endpoint accepts named protocols (ALPN), but nobody can look up who offers one |
| enrollment | missing | **has**: each workload gets an mTLS certificate when it starts | **has**: log in through an identity provider, then register a WireGuard key | missing: anyone with a key can connect |
| flow allocation and access control | partial: the front's own checks | partial: per-request authorization policy | partial: rules on machines and ports, enforced by every machine | partial: dial a key and a protocol; the application accepts or refuses |
| routing between relays | missing: static config | partial: routes pushed as config, inside a cluster | partial: one relay hop (DERP), or subnet routers set up by hand | missing: one relay hop |
| shared state about the layer | missing | central: the control plane | central: the coordination server | only the directory |
| data transfer control | borrowed: TCP or QUIC | borrowed: TCP | borrowed: the users' own TCP, inside the tunnel | **has**: QUIC |
| mobility, multihoming | missing | inside one cluster | **has**: addresses survive network changes | **has**: a connection moves between relay and direct paths |
| scope | anything that speaks HTTP | one cluster, or a few | one organization's machines | one application's endpoints |

Each one gets close in a different way, and each stops short for its own reason:

- **A service mesh** has the most complete layer management: a live directory, registration, enrollment, policy. But it manages a layer whose addresses it borrows, inside one cluster, for the protocols its proxies understand.
- **Tailscale** comes closest to a whole DIF, at the wrong rank. It rebuilds the node level the internet lacks: its own addresses, enrollment, a directory and mobility. But it carries IP packets, so its users name each other by IP:port again. The service level stays collapsed: no application names, no registration, and access control on ports. Tailscale is a better internet DIF, not a service DIF.
- **iroh** starts from the other end. It names nodes by key and brings its own transport, QUIC, so it has data transfer control the others borrow. It leaves enrollment and registration to each application.

The mesh and Tailscale also run all of their layer management from one control plane. In RINA, each member keeps that state in its own RIB, and how members keep their RIBs in sync is a policy of the DIF.

None of them adds all of it, and none shares an API with the others.

### So why does NAT still exist?

Because NAT works for unmodified applications. An upper layer only helps the programs that join it: Tailscale needs a client, and an HTTP proxy only carries HTTP. NAT sits at the internet rank and quietly handles every application's traffic. TCP/IP offers no general "join an upper layer" step that every application gets for free, so the transparent hack won.

What RINA adds is not upper layers. It is the *same* layer, with the same mechanisms and the same API, repeated at every rank. Every application gets naming, registration, enrollment, flow allocation and routing from whatever DIF it uses. Today each overlay reinvents some of them, differently: HTTP a little, a mesh most of the management, Tailscale the node level, iroh its own way.

## References

- J. Day, *Patterns in Network Architecture: A Return to Fundamentals*, Prentice Hall, 2008.
- E. Grasa et al., [Recursive InterNetwork Architecture, Investigating RINA as an Alternative to TCP/IP (IRATI)](https://www.riverpublishers.com/pdf/ebook/chapter/RP_9788793519114C16.pdf), River Publishers, 2017.
- J. Saltzer, [RFC 1498, *On the Naming and Binding of Network Destinations*](https://www.rfc-editor.org/info/rfc1498/), 1993 (written 1982).
- A. Greenberg et al., [VL2: A Scalable and Flexible Data Center Network](https://www.microsoft.com/en-us/research/publication/vl2-a-scalable-and-flexible-data-center-network/), SIGCOMM 2009.
- M. Dalton et al., [Andromeda: Performance, Isolation, and Velocity at Scale in Cloud Network Virtualization](https://www.usenix.org/conference/nsdi18/presentation/dalton), NSDI 2018.
- J. Iyengar, M. Thomson (eds.), [RFC 9000, *QUIC: A UDP-Based Multiplexed and Secure Transport*](https://www.rfc-editor.org/info/rfc9000/), 2021.
- D. Farinacci et al., [RFC 9300, *The Locator/ID Separation Protocol (LISP)*](https://www.rfc-editor.org/info/rfc9300/), 2022.
- [iroh documentation](https://docs.iroh.computer/): endpoints, address lookup and relays.
- [Tailscale: How Tailscale works](https://tailscale.com/blog/how-tailscale-works).
- [Envoy: xDS configuration API overview](https://www.envoyproxy.io/docs/envoy/latest/api-docs/xds_protocol).
- [Istio: Security concepts](https://istio.io/latest/docs/concepts/security/).
- D. Staessens, S. Vrijders, [Design of the Ouroboros packet network](https://arxiv.org/abs/2001.09707), arXiv:2001.09707, 2020.
- D. Staessens, [How does Ouroboros relate to RINA, the Recursive InterNetwork Architecture?](https://ouroboros.rocks/blog/2021/03/20/how-does-ouroboros-relate-to-rina-the-recursive-internetwork-architecture/), 2021.
- [Ouroboros wiki](https://ouroboros.rocks/wiki/Ouroboros).
