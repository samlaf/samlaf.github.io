---
title:  "Naming and binding"
series: "Networking, Part 2"
series_url: "/programming/networking-series-intro.html"
category: programming
date: 2026-10-03
---

> This is Part 2 of a seven-part [series on networking](/programming/networking-series-intro.html).
>
> 1. **[Networking is IPC](/programming/networking-is-ipc.html)** — one table of every way two parties exchange messages, and the same functions repeating at every boundary.
> 2. **Naming and binding** — Saltzer's four levels, why IP:port does two jobs, and why every many-to-many case needs a translator.
> 3. **[The Internet as DIFs](/programming/internet-as-difs.html)** — Saltzer's levels inside a RINA layer, a web service read rank by rank, and what overlays like Tailscale are missing.
> 4. **[Interconnects are networks](/programming/interconnects-are-networks.html)** — PCIe is a packet network wearing a 1992 bus costume.
> 5. **[Ring buffers](/programming/ring-buffers.html)** — shared memory plus a doorbell, compared on five axes.
> 6. **A packet's path through Linux** *(not yet written)* — from the NIC's descriptor ring to `recv()`, and the ways around it.
> 7. **[From IPC to RPC](/programming/ipc-to-rpc.html)** — what a request/reply protocol adds on top of a flow, and where RPC ends.

Every message needs a destination, and "destination" is ambiguous. It can mean the service you want, the machine that runs it, the place that machine plugs into the network, or the route that gets you there. Jerry Saltzer pulled those four apart in 1982, in a note later published as [RFC 1498, *On the Naming and Binding of Network Destinations*](https://www.rfc-editor.org/info/rfc1498/). This article reads the Internet through his four levels: where it keeps them apart, where it collapses them, and what the collapses cost.

The tables are my reading of the paper, not something Saltzer tabulates in this form. Where the fit is loose, the text says so. [Part 3](/programming/internet-as-difs.html) takes the same levels into RINA, where they repeat at every layer.

- [Saltzer's four levels](#saltzers-four-levels)
- [Saltzer's own examples](#saltzers-own-examples)
- [Saltzer's levels in the Internet](#saltzers-levels-in-the-internet)
- [What `bind()` restricts](#what-bind-restricts)
- [Fan-out and fan-in at each layer](#fan-out-and-fan-in-at-each-layer)

## Saltzer's four levels

Saltzer separates four things a sender might mean by "destination", because each one changes for different reasons and on a different timescale:

| Level | Question | Changes when |
| --- | --- | --- |
| service | *what* do I want? | a service moves to, or is replicated on, other machines |
| node | *which machine* provides it? | a machine gets another network attachment, or moves |
| attachment point | *where* does that machine plug into the network? | the topology changes |
| path | *how* do packets get there? | routes change |

Each object keeps its own stable name. What changes is the binding between levels. A service shouldn't change its name when it moves to another machine, and a machine shouldn't change its name when it plugs in somewhere else. Delivering a message to a service means resolving three bindings in turn: a node that runs the service, an attachment point of that node, and a path to that attachment point.

In this scheme, an address isn't a different kind of thing from a name. **An object's address is the name of whatever it is bound to.** A node's address is the name of its attachment point. An attachment point's address is the name of a path. So "is this a name or an address?" isn't a question about the identifier. It is a question about which binding table you are reading.

Each binding can in principle be many-to-many and change over time. That is his argument for keeping the levels separate. He doesn't claim the many-to-many cases are common: mostly each binding is one-to-one, and an architecture shows its flaws in the exceptions.

```
 SERVICE              NODE                ATTACHMENT POINT        PATH
 (what)               (which machine)     (where it plugs in)     (how to reach it)

 "rpc" ─────────┬───► node-A ──────┬────► 10.0.0.4 ─────────┬──► via router r1
                │       ▲          │                        └──► via router r2
 "metrics" ─────┼───────┘          └────► 192.168.1.4 ─────────► via router r3
                │
                └───► node-B ─────────┬─► 10.0.0.5 ────────────► via router r4
                                      │
 node-C ──────────────────────────────┘   (anycast / NAT / floating IP:
                                            two nodes, one address)
```

| Binding | One → many | Many → one |
| --- | --- | --- |
| service → node | a service replicated on several nodes | one node runs several services |
| node → attachment point | multihoming: a node with several addresses | anycast, NAT, floating IP: several nodes behind one address |
| attachment point → path | several routes to one attachment point | one path ends at one attachment point, except multicast |

**Why he stopped at four.** As I read the paper, its subject is one question, what a sender has to name to get data to a destination, analyzed within one network level. A connection isn't a destination, so it is out of scope, and he doesn't develop the idea that the same structure repeats in the layer below. Day does both: connections get their own identifiers, and the pattern recurses.

## Saltzer's own examples

![Saltzer's examples: the clean model, Ethernet's 48-bit identifiers, and ARPANET host names, by where each public name binds](/assets/networking-series/saltzer-examples.png)

The paper works through one hypothetical and two real networks. Each shows a different way the four levels get collapsed.

**The DIALOG table: what a binding table records.** Saltzer imagines a table entry saying that "the Lockheed DIALOG Service is running on node 5". Three bindings are involved, but the table holds only one. The name "Lockheed DIALOG Service" is bound to the service almost permanently. The name "5" is bound to the node for the long term. The table records only that DIALOG runs on node 5 *right now*, because that is what's expected to change. So editing the table doesn't rename the service. A real rename means changing every program, document and note that holds the old name. **The scope of a binding is where copies of it live.**

**Ethernet: a deliberate collapse.** On the then-new Ethernet, a node can attach anywhere on the cable and brings its own 48-bit identifier, which its interface listens for. Is that the attachment point's name or the node's? Both: the design binds them to one identifier, permanently. Saltzer credits the gains. A node can move without changing any records, a whole level of binding tables disappears, and a node on two networks can show the same name on both. Then he finds where it leaks. To attach one node twice to the same Ethernet, you must give it two identifiers. Every table that treats the identifier as a node name now sees two nodes. Use one identifier for both, and you can't send to one interface rather than the other. Removing a binding level buys simplicity and gives up what that level's flexibility provided.

**ARPANET: an accidental collapse.** ARPANET host names look like names for machines or services. In fact they name attachment points: "RADC-Multics" means IMP 18, port 0. Saltzer's proof is short. Attach the same Honeywell machine to a second port, and it needs a second name. One machine with two names means the name can't be naming the machine. Mail shows the cost. Any of BBN's four PDP-10s could accept mail for the others. But if the one you named was down, you had to know to try another host name, which looked like a different service. The replicas existed. The load balancer was a human.

**One name server can do two bindings.** Saltzer closes by noting that the three bindings don't need three mechanisms. Usually one name server takes a service name and returns a list of attachment points. That performs the first two bindings at once and may leave the final pick to the client. A distributed routing algorithm then does the third binding without anyone noticing. That is a description of DNS, written before DNS shipped.

In each example, Saltzer doesn't ask "is this a name or an address?" He asks which object the identifier's binding table really ties it to, and what happens when the thing you assumed was permanent has to move.

## Saltzer's levels in the Internet

Ordered by Saltzer's levels, not by protocol layer:

| Saltzer level | Internet name | Example | Bound to the next level by |
| --- | --- | --- | --- |
| service | hostname + port | `api.example.com`, `https` | DNS for the address, a well-known port or an SRV record for the port |
| node | **none** | — | — |
| attachment point | IP address | `10.0.0.4` | routing |
| path | route | via `r1` | — |

DNS looks like it fills the node gap, but it doesn't. It is Saltzer's name server: a hostname resolves straight to attachment points, skipping the node.

### Why IP:port does two jobs

When a client connects to `203.0.113.7:443`, that one string carries two answers:

- **Where.** `203.0.113.7` locates the destination on the Internet. Strictly, it names an interface: an attachment point, not a node.
- **Which application.** `443` stands for "the HTTPS server". It is a well-known number playing the role of a service name.

This is the ARPANET's collapse, carried forward. With no node level to hang the service on, the Internet put the service identifier in the transport header, next to the address. So L4 isn't a level below the node. It is where service and attachment point got glued together.

Folding both into IP:port causes five problems:

- **A service can't move without changing its name.** Renumbering breaks every client, so DNS is used to paper over it.
- **One service per IP:port.** Everything a browser reaches has to share `:443`, so separate services get folded together behind one proxy, which tells them apart by `Host` header and path.
- **Registration is unauthenticated.** Whichever process binds a port first *is* that service. On a shared host, any local user can take `127.0.0.1:8545` while the real server is down, and its clients will talk to the impostor.
- **The name reveals the location.** Anyone who learns an address can try it, so hiding backends takes firewalls.
- **Connections break when an address changes.** TCP builds a connection's identity from four values, `(src IP, src port, dst IP, dst port)`, fixed when it opens. A connection dies when an address changes, and it can't span two addresses.

Later protocols patch the last one. QUIC names each connection with connection IDs that are separate from addresses, which is why a QUIC connection survives a phone's switch from Wi-Fi to cellular. MPTCP lets one TCP connection use several addresses. [Part 3](/programming/internet-as-difs.html) shows the general version of that fix: a layer that keeps service names, node addresses and connection identifiers apart.

### One service, many nodes: DNS, VIPs and anycast

![Saltzer's four levels, and how a request to payments.example.com actually reaches a backend](/assets/networking-series/saltzer-levels-on-the-internet.png)

The top row is Saltzer's model with an example name at each level. The node-id has no Internet counterpart: that is the gap above. The bottom row is one common path from a service name to a backend.

A replicated service needs a one-to-many service → node binding. The Internet has three places to put it, and each puts it at a different level:

| Mechanism | The address the client gets names | Who picks the node | When | A change takes effect |
| --- | --- | --- | --- | --- |
| DNS | one replica's attachment point | the resolver and the client, from the record set | at each lookup | when caches expire, which can be after the TTL |
| VIP + load balancer | the service | the load balancer, from its backend table | at each new connection | at the next connection |
| anycast | the service, at every site that announces it | every router on the path | at each packet | as soon as BGP converges |

**DNS.** The binding lives in a directory outside the network, and each client keeps its own copy. It is cheap and needs no new machines. But a dead replica stays in client caches until they expire, and the operator can't move a connection once it is open.

**VIP.** DNS returns one address, and that address names the service, not a machine. This is the diagram's VIP nuance: the name has the form of an attachment point but is used as a service name. Saltzer warns against exactly this inference: a name's form doesn't tell you what kind of object it names. The load balancer binds the VIP to a backend for each new connection, usually by hashing the five-tuple (IPVS, [Maglev](https://www.usenix.org/conference/nsdi16/technical-sessions/presentation/eisenbud)). The cost is that the load balancer now sits on the path, so it must be replicated too, and that brings the same binding problem back one level down.

**Anycast.** Many sites announce the same prefix, and routing delivers each packet to the nearest one. The path binding does the service binding: there is no directory and no load balancer, only routes. [Cloudflare's 2013 architecture](https://blog.cloudflare.com/cloudflares-architecture-eliminating-single-p/) uses anycast twice:

- **Across data centers.** Every data center announces the same IPs to the Internet.
- **Inside a data center.** Every server announces those IPs to the local router over BGP. Each server sets its own route weight, and the router prefers the lowest. The post describes an experiment with equal weights, where the router hashes source IP, destination IP and port to pick a server, which keeps a flow on one server.

A failure is a withdrawn route. A crashed process, server, switch or router takes its announcements with it, and traffic moves to the next nearest server or site. There is no load balancer box to fail.

The catch is that routing knows nothing about connections. If a route changes in the middle of a TCP connection, its packets arrive at a site with no state for it. [Hendriks et al. (2025)](https://arxiv.org/html/2503.14351v1) measure a subtler effect. Load balancers in transit networks hash header fields, so two flows from the same client can reach different anycast sites. They found this for 4.4% of responsive IPv4 /24 prefixes, mostly residential networks, with an average round-trip difference of 30 ms between the two sites. Each flow still stays on one path, so connections survive. But the operator no longer decides which site serves which client.

**In practice, they stack.** The diagram's bottom row uses all three, one per binding:

1. DNS binds the human-readable name to a VIP.
2. BGP and ECMP bind the VIP to one of several load balancers: anycast inside the data center.
3. The load balancer binds each connection to a backend.

Each binding hides the one below it from the one above. The client sees one address for the life of the connection, while the operator changes the backends behind it freely.

### Kubernetes runs each binding as a control loop

Kubernetes builds the same stack in software, and keeps every binding live:

- **Service → pod.** The scheduler places pods on machines. The EndpointSlice controller keeps publishing which pods currently back each Service, and updates the list every time a pod dies or a rollout moves on.
- **Pod → attachment point.** The CNI plugin gives each pod an IP when it starts. That IP names the pod's interface, not the pod, and a new pod gets a new one. That is why "never hardcode pod IPs" is a rule.
- **Attachment point → path.** Left to the network plugin: VXLAN overlays, BGP, eBPF or cloud routes. Kubernetes only promises that every pod can reach every pod IP.

A **ClusterIP** is a VIP that no interface holds. kube-proxy, or an eBPF program, rewrites the destination of each new connection to a live pod IP. Clients that resolve a name once and cache the address forever would break under pod churn. A ClusterIP gives them an address that never changes, and moves the late binding below them, where they can't cache it.

A **headless Service** drops the VIP. DNS returns the pod IPs directly, as in the DNS row above, and the client has to re-resolve when they change. Clients that already handle rebinding use it: database drivers, StatefulSet peers, gossip protocols.

Like Saltzer's name server, an EndpointSlice fuses the first two bindings. It records pod IPs, not pods, so the data path goes from service name straight to attachment points. The node level exists, since the scheduler bound each pod to a machine, but the data path never sees it.

### What an IP address names: the host model

What an IP address names depends on the host model (RFC 1122):

- **Strong host model:** an address belongs to its interface, and a packet for it is accepted only on that interface. The address names an attachment point.
- **Weak host model (Linux's default):** an address belongs to the host, and a packet for it is accepted on any interface. The address names something closer to Saltzer's missing node.

## What `bind()` restricts

A connection is identified by four values. For an incoming connection, `bind()` sets only the destination half: which of this host's addresses, and which port. A listening socket never constrains the source; any remote address that can get a packet here can connect. Restricting sources takes a firewall in the path, a filter on the host (nftables, systemd's `IPAddressAllow=`), or the application closing connections from the wrong peer.

| Bind address | Accepts connections sent to | Who can reach it |
| --- | --- | --- |
| `127.0.0.1` | loopback only | only the host: the kernel drops `127.0.0.0/8` arriving on any other interface |
| `0.0.0.0` | any of this host's IPv4 addresses, including ones added later | anyone who can route to one of them |
| `[::]` | any IPv6 address, usually IPv4 too on Linux | same |
| one specific IP | that address only | anyone who can route to it. Under the weak host model that includes a neighbor on *another* interface's network who crafts a frame for it |

So `bind(X)` restricts to an attachment point only in the sense that routing normally delivers packets for `X` through `X`'s interface. To pin a socket to an interface, use `SO_BINDTODEVICE` (systemd: `BindToDevice=` in a socket unit), or an input-interface firewall rule.

## Fan-out and fan-in at each layer

| Layer | One → many | Many → one |
| --- | --- | --- |
| service | one service on many nodes: replicas behind a load balancer | one address serving many sites: virtual hosting, where the HTTP `Host` header or TLS SNI picks the site |
| L4 | one process, many ports: a server with a public port and an admin port | one listening port, many connections told apart by the remote address and port; `SO_REUSEPORT` lets several sockets share one port |
| L3 | one interface, many IPs: secondary addresses, in any subnets | one IP, many hosts: anycast, a VRRP floating IP, NAT |
| L2 | one NIC, many MACs (macvlan); one NIC, many L2 networks (VLANs) | many NICs, one interface: bonding (LACP or active-backup) |

```
                     ┌──────────────────────── host ─────────────────────────┐
 L4  ports           │   :8080    :9090                :443                  │
                     │      ╲     ╱                      │                    │
 L3  IP addresses    │     10.0.0.4   192.168.7.5     10.0.2.9               │  ← two IPs on one interface
                     │          ╲     ╱                  │                    │
 L2  interfaces      │           eth0                  bond0                  │
                     │             │                  ╱      ╲               │  ← bonding: one interface,
 L1  NICs            │           nic0              nic1      nic2             │    two NICs
                     └─────────────┼─────────────────┼─────────┼──────────────┘
                                 switch            switch    switch
```

### Where the neat story breaks

Almost every many-to-many case above is achieved by inserting a new layer or a translator, not natively:

- **Bonding** adds a virtual interface (`bond0`); IP still sees one interface.
- **Virtual hosting** adds a name the transport never sees: `Host` or SNI.
- **NAT** adds a translation table in the network.
- **Load balancing** adds a proxy.
- **QUIC and MPTCP** add a connection name that IP and TCP lack.

That pattern is Day's argument for RINA, and [Part 3](/programming/internet-as-difs.html) takes it up.

## References

- J. Saltzer, [RFC 1498, *On the Naming and Binding of Network Destinations*](https://www.rfc-editor.org/info/rfc1498/), 1993 (written 1982).
- R. Braden (ed.), [RFC 1122, *Requirements for Internet Hosts: Communication Layers*](https://www.rfc-editor.org/info/rfc1122/), 1989.
- D. Eisenbud et al., [Maglev: A Fast and Reliable Software Network Load Balancer](https://www.usenix.org/conference/nsdi16/technical-sessions/presentation/eisenbud), NSDI 2016.
- Cloudflare, [Cloudflare's architecture: eliminating single points of failure](https://blog.cloudflare.com/cloudflares-architecture-eliminating-single-p/), 2013.
- R. Hendriks et al., [Load-Balancing versus Anycast: A First Look at Operational Challenges](https://arxiv.org/html/2503.14351v1), 2025.
- [Kubernetes: Service](https://kubernetes.io/docs/concepts/services-networking/service/) and EndpointSlice concepts.
- [Thread on RFC 1498 and Kubernetes](https://x.com/samlafer/status/2077846060353905120), 2026.
