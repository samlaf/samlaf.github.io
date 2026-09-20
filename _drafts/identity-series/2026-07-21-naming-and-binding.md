---
title:  "Naming and binding"
series: "Identity, Part 1"
series_url: "/programming/identity-series-intro.html"
category: programming
date: 2026-07-21
---

> This is Part 1 of a six-part [series on identity](/programming/identity-series-intro.html).
>
> 1. **Naming and binding** — names stay put, bindings move. Saltzer's lens, from the ARPANET to Kubernetes to PCIe.
> 2. **[Keys are not names](/programming/keys-are-not-names.html)** — what cryptography can say about who, and why anyone bothers with names at all.
> 3. **[Hosts](/programming/identity-of-hosts.html)** — DNS, X.509 and the Web PKI: forty years of binding names to keys, and the anchors it bottoms out in.
> 4. **[Humans](/programming/identity-of-humans.html)** — accounts, the trusted third party from Kerberos to OIDC, and sessions.
> 5. **[Workloads and hardware](/programming/identity-of-workloads.html)** — secret zero, SPIFFE, federated CI identity, and attestation.
> 6. **[Binding without a CA](/programming/binding-without-a-ca.html)** — first use, webs of trust, transparency logs, and petnames.

Before keys, before certificates, before anyone asks who is on the other end of a connection: what is a name, and what does it mean for one thing to be *bound* to another? Jerry Saltzer answered that in 1982 for network destinations, and [RFC 1498][rfc1498] is the version most people read. It has nothing to say about security. It is the best thing ever written about identity anyway, because every identity system in this series is a binding service, and every identity failure is one of the failures he catalogued.

- [Four objects, three bindings](#four-objects-three-bindings)
- [Kubernetes is the paper, mechanized](#kubernetes-is-the-paper-mechanized)
- [Real-world examples](#real-world-examples)
- [PCIe](#pcie)
- [Turning the lens on keys](#turning-the-lens-on-keys)

## Four objects, three bindings

Saltzer's whole argument is that the endless confusion around "names vs. addresses vs. routes" dissolves if you borrow the operating-systems concept of *binding*. He identifies four kinds of objects that may be named as the destination of a packet: **services**, **nodes**, **network attachment points**, and **paths**. Each object gets a stable name of its own, and what changes over time is not the name but the *bindings* between the layers. A service shouldn't change its name when it migrates from one machine to another, and a machine shouldn't change its name when it moves from one attachment point to another.

The operational consequence is that delivering a packet to a *service* requires resolving three bindings in sequence: find a node the service runs on, find an attachment point that node is connected to, find a path to that attachment point. And he insists on a distinction that most systems blur: a judgment that a particular binding can be made at design time and never changed shouldn't confuse the question of what bindings are *in principle* present. The ARPANET's sin, in his telling, was collapsing these layers — using attachment-point addresses as node names and well-known sockets as service names — so that when anything moved, the identifiers broke.

An *address*, in this scheme, is not a different kind of thing from a name. It is the name of whatever object the current one is bound to. A node's address is the name of its attachment point; an attachment point's address is the name of a path. Once you see that, "is this a name or an address" stops being a question about the identifier and becomes a question about which binding table you are looking at.

## Kubernetes is the paper, mechanized

Kubernetes is almost a literal mechanization of this framework, which is why the paper reads so presciently. Mapping the three bindings:

**Binding 1 (service → node) is the scheduler plus the endpoint controller.** The stable service name is the Service object's DNS name (`payments.prod.svc.cluster.local`). The "node" in Saltzer's sense is really the Pod — the thing that hosts a service instance and can be destroyed and recreated elsewhere. The kube-scheduler performs this binding explicitly, and in a lovely terminological echo, it does so by writing a `Binding` object to the `pods/binding` subresource. On the discovery side, the EndpointSlice controller continuously publishes which pods currently back the service. This is Saltzer's "binding service" for layer 1, implemented as a control loop rather than a directory lookup: the binding is re-executed automatically every time a pod dies or a deployment rolls.

**Binding 2 (node → attachment point) is CNI IPAM.** When kubelet sets up a pod's sandbox, the CNI plugin allocates a pod IP — that IP is the attachment point, and it names the interface, not the pod. This is exactly Saltzer's distinction: the pod keeps its identity (name, UID) conceptually while its attachment point is ephemeral, and the reason "never hardcode pod IPs" is a rule is precisely his early-binding failure mode. Interestingly, Kubernetes *collapses* bindings 1 and 2 in the resolution path: an EndpointSlice records pod IPs directly, so resolvers go from service name straight to attachment points without ever consulting the node layer. The service→node binding exists (the scheduler made it) but it's invisible to the dataplane.

**Binding 3 (attachment point → path) is delegated to the CNI dataplane.** Routing between pod IPs — VXLAN overlays, Calico's BGP, Cilium's eBPF, cloud VPC routes — is deliberately kept out of Kubernetes' core model. The flat "every pod can reach every pod IP" contract means Kubernetes only guarantees binding 3 is *solvable* and leaves the mechanism to the network, which is very much in the spirit of the paper (and of Saltzer's end-to-end argument generally).

The most interesting Kubernetes-specific wrinkle is the ClusterIP, because it looks like a violation of Saltzer's taxonomy but is actually a clever exploitation of it. A ClusterIP is syntactically an attachment-point address, but nothing is attached to it — no interface anywhere has that IP. It's a service *name* rendered in address clothing. The reason this works is that the actual binding resolution happens in the dataplane: kube-proxy (iptables/IPVS) or eBPF rewrites the destination per-connection to a live pod IP. This is a hack around the exact early-binding pathology Saltzer describes: legacy clients that resolve DNS once and cache the IP forever would break under pod churn, so Kubernetes gives them a permanently-stable pseudo-address and moves the late binding below them, where it can't be cached away. The binding service also "makes a choice" among multiple instances — Saltzer explicitly notes that a service may run on several nodes and the resolution mechanism must select one — which in Kubernetes is just the load-balancing decision in the DNAT step.

Headless services are the escape hatch that restores the pure Saltzer model: DNS returns the pod IPs (the raw output of bindings 1+2) directly, and the *client* assumes responsibility for re-resolving when bindings change. That's why they're used by clients that already have rebinding machinery — database drivers, StatefulSet peers, gossip protocols.

So the one-line summary: Saltzer argued that all three bindings must be treated as dynamic and re-discoverable *in principle*, even when systems of his era froze them at design time. Kubernetes is what you get when you take "in principle" seriously and build a reconciliation loop for each binding — the scheduler re-executes binding 1, CNI re-executes binding 2 on every pod start, and the endpoint/proxy machinery propagates the results so that the only durable identifier anyone holds is the service name, exactly as the paper prescribes.

## Real-world examples

![](/assets/identity-series/naming-and-binding/bindings-examples.png)

The paper works through three examples (plus one hypothetical that sets them up), and each one is chosen to show a different way the four-object/three-binding model gets collapsed or confused in real systems.

**The Lockheed DIALOG table (the setup).** Before the "real-world" section proper, Saltzer uses a hypothetical network table recording that "the Lockheed DIALOG Service is running on node 5" to make a subtle point about what a binding table actually expresses. There are three different bindings involved, but only one is recorded in that table: the name "Lockheed DIALOG Service" is associated with a specific service on a quite permanent basis, the name "5" is assigned to a particular node on a long-term basis, and neither of those is expressed in a single easily-changed table — the only thing the table expresses is that DIALOG is currently operating on node 5, because that's the association expected to change. The design mistake is believing this table lets you rename the DIALOG service by editing the entry — a real name change would require changing user programs, documentation, scribbled notes, and advertising copy. In modern terms: an EndpointSlice lets you rebind a Service to different pods; it does not let you rename the Service, because the service name is bound into every client's config, code, and humans' heads. **The scope of a binding is defined by where copies of it live.** Hold onto that sentence; it is the whole theory of certificate revocation.

**Ethernet 48-bit identifiers: attachment point collapses into node.** The first real example is the then-new Xerox/DEC/Intel Ethernet. The concept of a network attachment point is elusive on an Ethernet because it collapses into the node name: a node can physically attach anywhere along the cable and brings with it a 48-bit unique identifier that its interface watches for. That identifier should probably be thought of as the attachment point's name — yet since the node supplies it from its own memory, an equally reasonable view is that it names the node itself. This way of using Ethernet binds the node name and attachment point name to be the same identifier, permanently. Saltzer is fair about the tradeoff — the permanent binding means a node can move physically without changing any network records, one whole level of binding tables is omitted (especially valuable for internetwork routing), and a dual-homed node can present the same name to both networks. But then he finds the corner case where the collapsed model leaks: if you want one node connected to two attachment points on the same Ethernet, the only way to make the second point independently addressable is to give the node two different 48-bit identifiers — which fools every record that treats the ID as a node name into believing there are two nodes. Use the same identifier on both and there's no way to intentionally direct a message to one interface rather than the other. The lesson: eliminating a binding level buys simplicity but permanently forfeits the functionality that binding's flexibility provided. (This exact ambiguity is still with us — multi-NIC hosts where each interface gets its own MAC and higher layers happily model them as separate "hosts," and in the K8s world, Multus-attached pods that appear as distinct endpoints per network.)

**ARPANET NCP names: everything collapses into the attachment point.** The second example is the inverse failure — instead of node and attachment point merging by design, human-friendly names got bound to the wrong layer by accident. ARPANET NCP names look, from their mnemonics, like node or service names, but they're actually names of attachment points: "RADC-Multics" names the attachment point at IMP 18, port 0. Reattaching the Honeywell 68/80 to a different port requires either that users learn a new name for the service or a table change in all other nodes — and needing to change more than one table is the tip-off that something deeper is going on: what's really happening is a change of the permanent name of an attachment point. His proof that the name belongs to the attachment point and not the node is elegant: attaching that same Honeywell in parallel to a second ARPANET port would require assigning it a second character-string identity. One machine, two names — so the name can't be naming the machine.

Then comes the best part, the mail example, which is essentially "life before the Service abstraction": any of the four PDP-10s at BBN can accept mail for any of the others (likewise the PDP-10 groups at ISI and MIT), but if the node you try to send mail to is down, the customer must realize the same service is available by asking for a different node using what appears to be a different service name — because in the ARPANET the name is not of a service bound to a node bound to an attachment point, but directly the name of an attachment point. The replica set exists; the load balancer is a human. Failover is a user retyping a hostname. This is precisely the gap that a ClusterIP + endpoint rebinding fills: the missing binding-1 indirection meant every client had to internalize the service→node mapping themselves, and keep it current by folklore. (Its modern descendant is anyone hardcoding `pod-2.mydb.svc` instead of the Service name and being surprised during a rollout.)

**The final observation: the three binding services need not be mechanically distinct.** There's usually only one identifiable service, a "name server," which starts with a service name and returns a list of attachment points — thereby performing both the first and second conceptual bindings at once, possibly leaving the final choice of attachment point to the customer — while path choice is accomplished by a distributed routing algorithm that provides the third binding without anyone noticing. That's a strikingly exact description of Kubernetes thirty years early: EndpointSlice resolution fuses bindings 1 and 2 (service name → pod IPs, node layer invisible), the "partial binding" whose final choice is delayed is kube-proxy's per-connection backend selection, and binding 3 is the CNI's routing fabric doing its work "without anyone noticing."

What ties the three examples together is his diagnostic method: in each case he doesn't ask "is this a name or an address?" but "which object does this identifier's binding table actually attach it to, and what happens when the thing you assumed was permanent needs to move?" The Ethernet example shows a deliberate, mostly-beneficial collapse; the ARPANET shows an accidental one that pushed rebinding costs onto every user; and the name-server point shows that keeping the bindings *conceptually* separate doesn't require separate machinery — which is the loophole every practical system, Kubernetes included, exploits.

## PCIe

Saltzer is a *fantastic* lens for this — and PCIe turns out to be a textbook case of one of his warnings, committed at industrial scale for 30 years. His scheme: four object types — services, nodes, attachment points, paths — with three changeable bindings between them (service→node, node→attachment point, attachment point→path). Let's place the PCIe vocabulary into those slots.

**Service** = the *function* in the PCI sense, or more precisely what a driver wants: "an NVMe controller," "a GPU." Its names are the class code and vendor:device ID. Saltzer's "service name resolution... identify the nodes that run the service" is literally driver matching: `MODULE_DEVICE_TABLE(pci, ...)` is a table binding service names (ID/class patterns) to driver code, and enumeration plus the driver core act as his "name server" — walk config space, read the ID registers, resolve which attachment points offer the service you want.

**Network attachment point** = the **BDF**. This is the load-bearing identification. Bus/device/function does not name the card — it names *the place in the tree where the card currently sits*. Move an NVMe drive to a different slot and its BDF changes while everything about the device is unchanged. That is precisely Saltzer's ARPANET example: names like RADC-Multics that look like node or service names but are in fact names of network attachment points, so reattaching the node elsewhere forces everyone to learn a new name. Every sysadmin who has had `eth0` or `/dev/sda` shuffle after adding a card has re-lived that paragraph. And notice that Linux's fix wore the diagnosis on its sleeve: `enp5s0` and `/dev/disk/by-path/pci-0000:05:00.0-...` are honest attachment-point names — the path *is* the name — while `/dev/disk/by-id/` and MAC-based naming reach for node names instead. The by-path/by-id split in udev is exactly Saltzer's taxonomy rendered as symlinks.

**Node** — and here's the sharpest observation the RFC enables — **PCIe has no node namespace at all.** Saltzer notes Ethernet *collapsed* node name into attachment point name (the 48-bit MAC serves as both, with the advantages and the dual-homing curiosity he walks through). PCIe went further and simply deleted the node from the fabric's naming scheme. There is no fabric-level identifier that follows a device across slots. Node identity exists only out-of-band, smuggled in at other layers: the VPD serial number, the device serial number extended capability, a NIC's MAC, an NVMe subsystem's NQN. When software needs "same device as last boot" semantics, it must escape the PCIe namespace entirely — which is why persistent device naming is perennially messy. The missing binding service in Saltzer's triad ("node name location") is missing because the nouns it binds don't exist in config space.

**Path/route** = the chain of links and bridges from root port to endpoint. PCIe never names routes explicitly — instead, the route is *encoded in the attachment-point namespace itself*. The bus number in a BDF isn't an arbitrary label; because of the secondary/subordinate containment invariant, the number determines the unique path down the tree, and each bridge's `(sec, sub)` interval plus address windows are the route tables. In Saltzer's terms, the attachment-point name is hierarchical in a way that makes route lookup a sequence of interval checks. This also explains a pathology: since the names are *derived from* the topology, they cannot survive topology change — hotplug a switch and buses may renumber, i.e., attachment points get renamed. A namespace that embeds routes buys trivial routing at the cost of name stability, which is the exact trade Saltzer's framework predicts.

His subtlety about *which binding lives in the easily-changed table* also maps cleanly. Service→node (the function is baked into the silicon): permanent, no table. Node→attachment point: bound by physical slotting plus enumeration order — changeable only with a screwdriver or a rescan. Attachment point→path: this is the one in mutable tables — the bridge bus registers and windows, rewritten at every enumeration. And his warning about the design mistake — believing a binding table confers renameability it doesn't have — is the standing bug class where software (VFIO assignment configs, passthrough setups, monitoring that keys on BDF) treats an attachment-point name as a node name and breaks the day the PCIe topology shifts underneath it.

Two smaller correspondences worth savoring. BARs fit his recursive definition that an address of an object is the name of whatever it's bound to: an MMIO range is a second name for an attachment point, bound to it via the nested bridge windows — PCIe runs two parallel namespaces (IDs and addresses) over the same paths, with two parallel route tables. And SR-IOV is his dual-attachment Ethernet curiosity inverted: one physical node deliberately presenting many attachment points (VF routing IDs), with the same resulting confusion about how many "devices" exist — ask anyone who's stared at an IOMMU group.

Finally, the RFC's central instrument — *binding time* — gives the one-line summary of why PCIe naming feels flimsier than Ethernet's: a MAC is bound at manufacture, a BDF is minted fresh at every enumeration. Early-bound names are stable and location-opaque; late-bound names are cheap and route-encoding. PCIe chose maximally late binding for its only namespace, then thirty years of software proceeded to use those names as if they were early-bound. Saltzer would have seen that one coming in 1982.

## Turning the lens on keys

None of the above mentions a key, and that is the point. The rest of this series does nothing but apply Saltzer's method to a different stack of objects. Here is the stack.

```text
principal          the party you could hold responsible: a company, a person, a program
name               what humans and policy use to refer to it: example.com, alice@, spiffe://…
key                what cryptography uses to refer to it: a public key, a fingerprint
channel            the connection you are actually holding right now
```

And the bindings between them, each with its own binding service and its own table:

```text
principal → name    registration: a registrar, an HR system, an account sign-up form
name → key          certification: a CA, an identity provider, a DNS zone, an attestation service
key → channel       the handshake: the peer proves it holds the private key, live
```

The crypto series covers the bottom row completely, and it is the *easy* row — a signature over a transcript, verified in microseconds. This series is the middle row. The top row is barely a technical question at all, and yet every identity system leans on it: a domain is yours because a registrar's database says so, an account is yours because a recovery email says so.

Every one of Saltzer's diagnostics transfers.

**Which table does this identifier really live in?** A phone number looks like a name for a person. It is the name of an attachment point on the telephone network, and SIM-swap fraud is the ARPANET mail example with money attached: reattach the number to a different node and every system that used it as a person's name follows the attacker. An IP address in a firewall rule, a MAC in an allowlist, the metadata-service address a cloud VM reads its credentials from — all attachment-point names doing a principal's job.

**Collapsing a level buys simplicity and forfeits flexibility.** SPKI's slogan "the key *is* the principal" is Ethernet's move: collapse name into key, drop a binding table, and every system that was going to look up name→key can skip the lookup. The cost is the same too. Rotate the key and you have renamed yourself, and every place that held a copy of the old key has to learn the new one. Systems that stop at the key — WireGuard peers, SSH `authorized_keys`, Bitcoin addresses — pay exactly this cost, and the [next article](/programming/keys-are-not-names.html) is about when it is worth paying.

**The scope of a binding is where copies of it live.** A certificate says "this key is `example.com`" and then gets copied into every client that ever connects. Revoking it means reaching every copy, which is why CRLs, OCSP, and CRLSets are all unsatisfying and why the industry's actual answer, in the [hosts article](/programming/identity-of-hosts.html), was to shorten the binding's lifetime until revocation stopped mattering. A session cookie has the same shape at a smaller scale: one copy, in one browser, and the [humans article](/programming/identity-of-humans.html) is largely about how long to let it live.

**Binding time.** A pinned certificate, a hardcoded fingerprint, a `known_hosts` entry: design-time bindings, stable and cheap to check, and broken the day the thing they point at moves. HTTP Public Key Pinning died for the same reason hardcoding pod IPs is a rule violation. A certificate with a 47-day lifetime, an `id_token` that lasts five minutes, a SPIFFE SVID rotated hourly: late bindings, re-resolved constantly, and the failure mode inverts — now the binding service has to be available all the time, and *it* becomes the thing you trust.

That last trade is the one to carry forward. Saltzer's binding service was a name server, and the only thing it could get wrong was returning a stale address. When the binding is name→key, the binding service is a certificate authority, an identity provider, a chip vendor — and what it can get wrong is telling you that an attacker's key is your bank's. The name server became the adversary's most valuable target, and the rest of this series is the history of what happened next.

## References <!-- omit in toc -->

1. [RFC 1498: On the Naming and Binding of Network Destinations - Saltzer (1993)][rfc1498]
2. [Thread on RFC 1498 and Kubernetes - samlafer][samlaf-thread]
3. [RFC 2693: SPKI Certificate Theory][rfc2693]
4. [Kubernetes Service and EndpointSlice concepts][k8s-service]

[rfc1498]: https://www.rfc-editor.org/rfc/rfc1498 "RFC 1498: On the Naming and Binding of Network Destinations"
[samlaf-thread]: https://x.com/samlafer/status/2077846060353905120 "Thread on RFC 1498 and Kubernetes"
[rfc2693]: https://www.rfc-editor.org/rfc/rfc2693 "RFC 2693: SPKI Certificate Theory"
[k8s-service]: https://kubernetes.io/docs/concepts/services-networking/service/ "Kubernetes: Service"
