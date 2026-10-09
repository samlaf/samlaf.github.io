---
title:  "Names, keys and bindings"
series: "Identity, Part 1"
series_url: "/programming/identity-series-intro.html"
category: programming
date: 2026-07-21
---

> This is Part 1 of a six-part [series on identity](/programming/identity-series-intro.html).
>
> 1. **Names, keys and bindings** — names stay put, bindings move. Saltzer's lens on network destinations, turned on keys.
> 2. **[Keys are not names](/programming/keys-are-not-names.html)** — what cryptography can say about who, and why anyone bothers with names at all.
> 3. **[Hosts](/programming/identity-of-hosts.html)** — DNS, X.509 and the Web PKI: forty years of binding names to keys, and the anchors it bottoms out in.
> 4. **[Humans](/programming/identity-of-humans.html)** — accounts, the trusted third party from Kerberos to OIDC, and sessions.
> 5. **[Workloads and hardware](/programming/identity-of-workloads.html)** — secret zero, SPIFFE, federated CI identity, and attestation.
> 6. **[Binding without a CA](/programming/binding-without-a-ca.html)** — first use, webs of trust, transparency logs, and petnames.

Before keys, before certificates, before anyone asks who is on the other end of a connection: what is a name, and what does it mean for one thing to be *bound* to another? Jerry Saltzer answered that in 1982 for network destinations, and [RFC 1498][rfc1498] is the version most people read. It has nothing to say about security. It is the best thing ever written about identity anyway, because every identity system in this series is a binding service, and every identity failure is one of the failures he catalogued.

- [Four objects, three bindings](#four-objects-three-bindings)
- [Turning the lens on keys](#turning-the-lens-on-keys)

## Four objects, three bindings

Saltzer's argument is that the confusion around names, addresses and routes goes away once you separate objects from the bindings between them. He names four kinds of destination: **services**, **nodes**, **network attachment points** and **paths**. Each one keeps a stable name. What changes over time is the binding between levels: a service moves to another machine, or a machine plugs in somewhere else. In this scheme an address is not a different kind of thing from a name. It is the name of whatever an object is bound to.

The [networking series](/programming/naming-and-binding.html) works through the paper in full, with the Internet, Kubernetes and PCIe as examples. Three of Saltzer's lessons carry over to keys, and the rest of this article uses them:

- **The scope of a binding is where copies of it live.** Saltzer imagines a table saying that the Lockheed DIALOG service runs on node 5. Editing that entry moves the service. It doesn't rename it, because the service's name is copied into every program, document and note that uses it.
- **Collapsing a level buys simplicity and gives up flexibility.** Ethernet binds a node and its attachment point to one 48-bit identifier. A whole level of tables disappears, until a node needs two attachments on the same cable and has to pretend to be two nodes.
- **A name bound to the wrong level pushes rebinding onto users.** ARPANET host names named attachment points, not machines. Several hosts could accept each other's mail, but when the one you named was down, you had to know to type a different host name for the same service. The replicas existed. The load balancer was a human.

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

**Binding time.** A pinned certificate, a hardcoded fingerprint, a `known_hosts` entry: design-time bindings, stable and cheap to check, and broken the day the thing they point at moves. HTTP Public Key Pinning died for the same reason hardcoded IP addresses break. A certificate with a 47-day lifetime, an `id_token` that lasts five minutes, a SPIFFE SVID rotated hourly: late bindings, re-resolved constantly, and the failure mode inverts — now the binding service has to be available all the time, and *it* becomes the thing you trust.

That last trade is the one to carry forward. Saltzer's binding service was a name server, and the only thing it could get wrong was returning a stale address. When the binding is name→key, the binding service is a certificate authority, an identity provider, a chip vendor — and what it can get wrong is telling you that an attacker's key is your bank's. The name server became the adversary's most valuable target, and the rest of this series is the history of what happened next.

## References <!-- omit in toc -->

1. [RFC 1498: On the Naming and Binding of Network Destinations - Saltzer (1993)][rfc1498]
2. [RFC 2693: SPKI Certificate Theory][rfc2693]

[rfc1498]: https://www.rfc-editor.org/rfc/rfc1498 "RFC 1498: On the Naming and Binding of Network Destinations"
[rfc2693]: https://www.rfc-editor.org/rfc/rfc2693 "RFC 2693: SPKI Certificate Theory"
