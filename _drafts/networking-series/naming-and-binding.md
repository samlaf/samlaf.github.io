# Naming and binding: Saltzer, RINA, and a Seismic node

TODO: reconcile with the intro (which already has "networking is IPC") and identity series which already has an article about Saltzer's naming and binding.

Notes from a conversation about listen addresses, firewalls and multihoming,
read through two lenses:

- J. Saltzer, [RFC 1498, *On the Naming and Binding of Network Destinations*](https://www.rfc-editor.org/info/rfc1498/)
  (written 1982, published as an RFC in 1993).
- J. Day's [Recursive InterNetwork Architecture](https://en.wikipedia.org/wiki/Recursive_Internetwork_Architecture)
The tables are my reading of both, not something either author tabulates in
this form. Where the fit is loose, the text says so.

## 1. Saltzer's four levels

Saltzer separates four things a sender might mean by "destination", because
each one changes for different reasons and on a different timescale:

| Level | Question | Changes when |
| --- | --- | --- |
| service | *what* do I want? | a service moves to, or is replicated on, other machines |
| node | *which machine* provides it? | a machine gets another network attachment, or moves |
| attachment point | *where* does that machine plug into the network? | the topology changes |
| path | *how* do packets get there? | routes change |

Each arrow between levels is a binding, and each binding can in principle be
many-to-many and change over time. That is his argument for keeping them
separate. He doesn't claim the many-to-many cases are common: mostly each
binding is one-to-one, and an architecture shows its flaws in the exceptions.

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

**Why he stopped at four.** As I read the paper, its subject is one question,
what a sender has to name to get data to a destination, analyzed within one
network level. A connection isn't a destination, so it is out of scope, and
he doesn't develop the idea that the same structure repeats in the layer
below. Day does both: connections get their own identifiers, and the pattern
recurses.

## 2. Saltzer's levels in the Internet stack

Ordered by Saltzer's levels, not by protocol layer:

| Saltzer level | Internet name | Example | Bound to the next level by |
| --- | --- | --- | --- |
| service | hostname + port | `rpc.example.com`, `https` | DNS for the address, a well-known port or an SRV record for the port |
| node | **none** | — | — |
| attachment point | IP address | `10.0.0.4` | routing |
| path | route | via `r1` | — |

Two things in the Internet don't sit cleanly on a Saltzer level:

- **The transport endpoint `(IP, port)` sits where the node should be.** It
  is a service identifier (the port) glued to an attachment point (the IP).
  With no node level to hang the service on, the Internet put the service
  identifier in the transport header, next to the address. So L4 isn't below
  the node; it is where service and attachment point got fused.
- **A TCP connection is bound to two attachment points.** Its identity is the
  four values `(src IP, src port, dst IP, dst port)`, fixed when it opens. That
  is Saltzer's main complaint in practice: a connection dies when an address
  changes, and it can't span two addresses. Later protocols patch exactly
  this:
  - QUIC names the connection with connection IDs that survive an address
    change;
  - MPTCP lets one connection use several addresses.

DNS looks like it fills the node gap, but it doesn't: a hostname resolves to
attachment points (addresses), skipping the node.

### One service, many nodes: DNS, VIPs and anycast

![Saltzer's four levels, and how a request to payments.example.com actually reaches a backend](/assets/networking-series/saltzer-levels-on-the-internet.png)

The top row is Saltzer's model with an example name at each level. The
node-id has no Internet counterpart: that is the gap above. The bottom row is
one common path from a service name to a backend.

A replicated service needs a one-to-many service → node binding. The
Internet has three places to put it, and each puts it at a different level:

| Mechanism | The address the client gets names | Who picks the node | When | A change takes effect |
| --- | --- | --- | --- | --- |
| DNS | one replica's attachment point | the resolver and the client, from the record set | at each lookup | when caches expire, which can be after the TTL |
| VIP + load balancer | the service | the load balancer, from its backend table | at each new connection | at the next connection |
| anycast | the service, at every site that announces it | every router on the path | at each packet | as soon as BGP converges |

**DNS.** The binding lives in a directory outside the network, and each
client keeps its own copy. It is cheap and needs no new machines. But a dead
replica stays in client caches until they expire, and the operator can't
move a connection once it is open.

**VIP.** DNS returns one address, and that address names the service, not a
machine. This is the diagram's VIP nuance: the name has the form of an
attachment point but is used as a service name. Saltzer warns against
exactly this inference: a name's form doesn't tell you what kind of object
it names. The load balancer binds the VIP to a backend for each new
connection, usually by hashing the five-tuple (IPVS,
[Maglev](https://www.usenix.org/conference/nsdi16/technical-sessions/presentation/eisenbud)).
The cost is that the load balancer now sits on the path, so it must be
replicated too, and that brings the same binding problem back one level down.

**Anycast.** Many sites announce the same prefix, and routing delivers each
packet to the nearest one. The path binding does the service binding: there
is no directory and no load balancer, only routes.
[Cloudflare's 2013 architecture](https://blog.cloudflare.com/cloudflares-architecture-eliminating-single-p/)
uses anycast twice:

- **Across data centers.** Every data center announces the same IPs to the
  Internet.
- **Inside a data center.** Every server announces those IPs to the local
  router over BGP. Each server sets its own route weight, and the router
  prefers the lowest. The post describes an experiment with equal weights,
  where the router hashes source IP, destination IP and port to pick a
  server, which keeps a flow on one server.

A failure is a withdrawn route. A crashed process, server, switch or router
takes its announcements with it, and traffic moves to the next nearest
server or site. There is no load balancer box to fail.

The catch is that routing knows nothing about connections. If a route
changes in the middle of a TCP connection, its packets arrive at a site with
no state for it.
[Hendriks et al. (2025)](https://arxiv.org/html/2503.14351v1) measure a
subtler effect. Load balancers in transit networks hash header fields, so two
flows from the same client can reach different anycast sites. They found this
for 4.4% of responsive IPv4 /24 prefixes, mostly residential networks, with
an average round-trip difference of 30 ms between the two sites. Each flow
still stays on one path, so connections survive. But the operator no longer
decides which site serves which client.

**In practice, they stack.** The diagram's bottom row uses all three, one per
binding:

1. DNS binds the human-readable name to a VIP.
2. BGP and ECMP bind the VIP to one of several load balancers: anycast inside
   the data center.
3. The load balancer binds each connection to a backend.

Each binding hides the one below it from the one above. The client sees one
address for the life of the connection, while the operator changes the
backends behind it freely.

### One layer down: the same pattern at L2

| Saltzer at L3 (IP) | The same at L2 (Ethernet) |
| --- | --- |
| node | the IP layer on this host, a user of the link |
| attachment point, named by an IP address | the interface, named by a MAC address |
| node → attachment point binding | ARP/NDP: IP address → MAC |
| path | switching |

An IP address is two things at once: the attachment-point name in the IP
layer, and the name the IP layer uses when it talks to the link layer. ARP is
the directory that binds that name to an L2 address.

### The weak host model sits at that boundary

What an IP address names depends on the host model (RFC 1122):

- **Strong host model:** an address belongs to its interface, and a packet for
  it is accepted only on that interface. The address names an attachment
  point.
- **Weak host model (Linux's default):** an address belongs to the host, and a
  packet for it is accepted on any interface. The address names something
  closer to Saltzer's missing node.

## 3. What `bind()` restricts

A connection is identified by four values. For an incoming connection,
`bind()` sets only the destination half: which of this host's addresses, and
which port. A listening socket never constrains the source; any remote
address that can get a packet here can connect. Restricting sources takes a
firewall in the path, a filter on the host (nftables, systemd's
`IPAddressAllow=`), or the application closing connections from the wrong
peer.

| Bind address | Accepts connections sent to | Who can reach it |
| --- | --- | --- |
| `127.0.0.1` | loopback only | only the host: the kernel drops `127.0.0.0/8` arriving on any other interface |
| `0.0.0.0` | any of this host's IPv4 addresses, including ones added later | anyone who can route to one of them |
| `[::]` | any IPv6 address, usually IPv4 too on Linux | same |
| one specific IP | that address only | anyone who can route to it. Under the weak host model that includes a neighbor on *another* interface's network who crafts a frame for it |

So `bind(X)` restricts to an attachment point only in the sense that routing
normally delivers packets for `X` through `X`'s interface. To pin a socket to
an interface, use `SO_BINDTODEVICE` (systemd: `BindToDevice=` in a socket
unit), or an input-interface firewall rule.

## 4. Fan-out and fan-in at each layer

| Layer | One → many | Many → one |
| --- | --- | --- |
| service | one service on many nodes: replicas behind a load balancer | one address serving many sites: virtual hosting, where the HTTP `Host` header or TLS SNI picks the site |
| L4 | one process, many ports: Seismic's attestation service on `:7878` and `:7879` | one listening port, many connections told apart by the remote address and port; `SO_REUSEPORT` lets several sockets share one port |
| L3 | one interface, many IPs: secondary addresses, in any subnets | one IP, many hosts: anycast, a VRRP floating IP, NAT |
| L2 | one NIC, many MACs (macvlan); one NIC, many L2 networks (VLANs) | many NICs, one interface: bonding (LACP or active-backup) |

```
                     ┌──────────────────────── host ─────────────────────────┐
 L4  ports           │   :7878    :7879                :443                  │
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

Almost every many-to-many case above is achieved by inserting a new layer or
a translator, not natively:

- **Bonding** adds a virtual interface (`bond0`); IP still sees one interface.
- **Virtual hosting** adds a name the transport never sees: `Host` or SNI.
- **NAT** adds a translation table in the network.
- **Load balancing** adds a proxy.
- **QUIC and MPTCP** add a connection name that IP and TCP lack.

That pattern is Day's argument for RINA.

## 5. RINA

### Networking is IPC, and a layer is a DIF

In RINA, networking is inter-process communication, and a layer is a
**DIF** (distributed IPC facility): a set of cooperating **IPC processes**
(IPCPs), one per member system, that together provide flows to the
applications above them. A DIF has a **scope**: one link, a datacenter, a
provider, the whole Internet. Every DIF runs the same mechanisms, with
policies chosen for its scope.

There is no separate transport layer. Every DIF does its own data transfer,
error control and flow control, so the TCP/IP split, with reliability in one
layer and addressing in another, doesn't exist.

### Every layer has the same three names

Saltzer's structure appears in every DIF, not just at L2/L3:

| Concept | In DIF N | Saltzer's level |
| --- | --- | --- |
| application name | the name of a user of DIF N, registered in DIF N's directory | service |
| address | the IPCP's address inside DIF N; internal, never shown to applications | **node** |
| point of attachment | the IPCP's address in the DIF *below* (N−1) | attachment point |
| route | computed by DIF N over its own addresses | path |

The key move: **addresses name nodes, and a point of attachment is just the
address one layer down**. There is no separate kind of name for attachment
points.

### Whose name is registered where

The application name differs at every layer, because each DIF has different
users. Only the top DIF's users are end applications. The users of every
lower DIF are the IPC processes of the DIF above, and an IPCP is itself an
application process with a name of its own.

```
 DIF            registered user (by name)           member IPCP on host H, and its address
 ──────────────────────────────────────────────────────────────────────────────────────────
 internet-DIF   "web-server"  (an application)  ◄── IPCP "inet@H",  address 7.12
                                                          │ is itself a user of ↓
 wifi-DIF       "inet@H"      (the IPCP above)  ◄── IPCP "wifi@H",  address 3
                                                          │ uses the radio ↓
```

`inet@H` has one name and two addresses:

- **Name `inet@H`:** assigned once, and registered in each lower DIF it uses.
- **Address `7.12` in internet-DIF:** its node address.
- **Address `3` in wifi-DIF:** its point of attachment.

Nothing has to be kept in sync across layers. When internet-DIF needs to
reach a neighboring IPCP, it asks wifi-DIF for a flow to that neighbor's
*name*, and wifi-DIF resolves the name to an address in its own directory.

The Internet conflates the two. The IP layer's "name" at L2 is its IP address
(ARP looks a neighbor up by IP address), so an IP address is both the
L2-facing name and the L3 address. RINA keeps a name and an address separate
in every layer.

Routing in DIF N runs on node addresses. For each next hop it then picks one
of the lower-layer flows that reach that node:

- **Multihoming is native.** A node with two attachments is one address in
  DIF N with two lower flows, and losing one is a local failover.
- **Mobility is native.** Moving changes the lower attachments, not the
  address in the DIF above.
- **Connections survive both.** Applications hold a **port-id**, a local
  handle the DIF hands out when it sets up a flow. Connections are identified
  by connection-endpoint ids internal to the DIF. Neither is an address, so
  an address change doesn't break a flow.

### Why recurse, if multihoming and mobility are already solved?

Recursion isn't the multihoming fix. It's how RINA handles **scope**, and it
is also part of what makes mobility cheap:

- **Bounded routing state.** A DIF routes only among its own members. Nesting
  small DIFs under larger ones keeps every routing table small, as hierarchy
  does, but with whole layers rather than address prefixes.
- **Policies per scope.** A lossy radio link wants aggressive local
  retransmission; a backbone wants the opposite. Each DIF picks its own
  error-control, flow-control and security policies.
- **Mobility stays local.** A phone moving between cells changes attachments
  in a small access DIF. The DIF above sees the same node address, and only
  the small DIF does any updating. Without the extra layer, every move would
  be visible network-wide.
- **Isolation.** Membership is by enrollment. A provider's internal DIF is
  invisible to its customers, and a VPN is just one more DIF.

The number of layers isn't fixed: you add a DIF wherever a new scope or
policy is needed. Today's Internet already does this ad hoc with VLANs, MPLS,
VXLAN overlays, VPNs and tunnels, each with its own mechanisms. RINA's claim
is that these should all be the same mechanism.

### Security: enrollment and flow allocation

- **Enrollment.** To join a DIF, an IPCP must authenticate under the DIF's
  enrollment policy. Non-members can't address members at all, because
  addresses never leave the DIF.
- **Flow allocation.** An application asks for a flow by destination
  application name. The DIF looks the name up in its directory and applies
  access control before any flow exists. The destination can refuse.

Proponents argue this makes firewalls unnecessary. That claim comes from
research prototypes, not from deployments at scale.

### Internet vs. RINA

| Concern | Internet | RINA |
| --- | --- | --- |
| service name | DNS name + well-known port | application name, in the DIF's directory |
| node name | none | the IPCP's address in the DIF |
| attachment point | IP address (L3), MAC (L2) | the address in the DIF below |
| connection identity | four values: two addresses, two ports | connection-endpoint ids inside the DIF; the application holds a port-id |
| directory | DNS, outside the stack | each DIF's own, used when a flow is set up |
| access control | firewalls on addresses and ports | enrollment, and checks when a flow is set up |
| layers | a fixed stack, plus ad hoc tunnels and overlays | as many DIFs as scopes need, one set of mechanisms |

## 6. A Seismic node through both lenses

- **Listen addresses.** `0.0.0.0` means every attachment point this host has;
  `127.0.0.1` is a host-scoped network (a DIF of one machine, in RINA terms).
  Neither restricts who connects.
- **Azure address translation.** The VM's only attachment point is its private
  IP. The public IP belongs to Azure's network fabric, which binds it to the
  private one: a binding layer maintained by the host. In RINA terms, the
  virtual network and the Internet are two DIFs, and NAT is a workaround at
  their border.
- **The three planes are three DIFs.**
  - Consensus is closest to RINA: membership is the validator set, peers
    authenticate by public key before anything else, and nodes are named by
    key, not location.
  - Tx gossip is open: joining requires only the `seismic` fork id.
  - Enclave peer RPC authenticates nothing at join time; every exchange
    carries its own attestation.
- **The node name is a key, and the manifest is the directory.** IP has no
  node level, so Seismic supplies one: the summit public key names the node,
  and the network manifest binds it to `IP:port`. The founding harvest is the
  moment that binding is captured, and its quote is what makes it
  trustworthy. The launch-time continuity check verifies it still holds.
- **Localhost shows both models.**
  - Internet style: a TCP port on `127.0.0.1` is a well-known name any local
    user can claim. That is SEI-626 (another user takes reth's `:8545` while
    reth is down).
  - RINA style: the custodian's Unix socket. Its name is a filesystem path
    whose directory permissions control who can create it. Each connection's
    identity (`SO_PEERCRED`) is known when the connection is set up, and the
    `--allow` grants accept or refuse each call per peer. reth's Engine API
    socket, gated by the `engine-api` group, follows the same pattern.
- **The operator-only rule on `:7879`.** Today it is a firewall rule on an
  address and port, enforced by the cloud fabric: by the host, which the TEE
  threat model distrusts. RINA would put the harvest in an operator-only DIF.
  But enrollment needs a credential, and before the config POST the guest has
  nothing to check the operator against: the image is generic and measured,
  so it can't know the operator. That is the same gap as `:8080`, where
  whoever POSTs first configures the box: trust on first use. The ways to
  close it:
  - bake an operator key into the image, which means one image per operator;
  - deliver it through host metadata (IMDS, custom data), which hands trust
    back to the host;
  - accept trust on first use and supervise the window, which is what
    network founding does today.
