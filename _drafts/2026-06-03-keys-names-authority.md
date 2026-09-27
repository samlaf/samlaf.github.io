---
title:  "Keys, names and authority"
category: programming
date: 2026-06-03
---

This page is the map for three series. Each one follows the same request, from a subject to an object, and each one stops at a different question. The [applied crypto series](/programming/crypto-series-intro.html) ends holding a key. The [identity series](/programming/identity-series-intro.html) asks whose key it is. The [authorization series](/programming/authorization-series-intro.html) asks what the holder may do.

## One request, four stages

A request passes through four stages on its way to an effect:

- **Designate:** a name resolves to an object. The kernel walks a path, DNS maps a host, a table maps a file descriptor to an open file.
- **Reach:** the request is carried to whatever serves the object. A syscall boundary, a route, an IPC endpoint.
- **Authenticate:** the system learns who is asking, which usually means checking that the asker holds a key.
- **Decide:** something evaluates whether this subject may do this to this object.

Each stage has three rows:

- **Written:** what the stage rests on, and who may write it. A certificate, an account, a rule, a route. All of it is set before the request arrives.
- **Request:** what the stage computes while the request is in flight.
- **Enforced:** what makes the stage binding. A name that resolves to nothing, a packet with no route, a key nobody else holds, a check nobody can go around.

Two regions sit outside the cells. **Carriers** are copies of something written that travel with the request, so the stage does not have to look it up: a certificate, a session cookie, a scoped token. **Bindings** are artifacts that serve several stages at once. A capability designates, reaches and decides in one object.

The [authorization series intro](/programming/authorization-series-intro.html#from-a-chain-to-a-grid) derives the grid from NIST's trust chain, and explains why enforcement is a row rather than a stage.

## Three regions

![One grid, three series: the regions each series covers](/assets/series/three-series-grid.svg)

- **Applied crypto** covers the Authenticate column below its Written row: proving you hold a key, and keeping it where nobody else can use it. It also covers a secure channel, which makes delivery tamperproof, and the machinery every cell is built from: primitives, AEAD, entropy and key wrapping.
- **Identity** covers most of the Written row. Its lens is the binding: who may write it, and when it stops being true. It applies that lens to names bound to places (DNS and routes, after Saltzer) and to names bound to keys (the Web PKI, identity providers, attestation). It also covers carriers of identity: certificates, `id_token`s and session cookies.
- **Authorization** covers the Decide column, the Enforced row, carriers of decisions, and bindings.

Only two cells are shared. Designate · Written is where names come from: identity covers how names are bound, and authorization covers how a subject comes to hold one. Reach · Enforced is delivery with no way around it: crypto makes the channel tamperproof, and authorization makes sure every path passes a decider.

## The adversary

TODO: merge the two prologues into one history here. The crypto prologue has three layers: the wire, the identity binding, and the authenticated counterparty. The authorization prologue has five positions, and positions 2 to 5 break down crypto's third layer. One history would run from the wire to the data a delegate reads.

## Seams to resolve

TODO: these are the places where two series currently cover the same idea. Each needs one home and links from the others.

- **Carrier theory.** Identity Part 1's binding time, and "the scope of a binding is where copies of it live," is the general theory. Authorization Part 2 applies it to decisions.
- **OAuth.** Identity Part 4 and Crypto Part 3 both send readers to authorization for OAuth. Its home is authorization Part 2, with custody linked to Crypto Part 3.
- **The grammar of a signed statement.** Crypto Part 4 and Identity Part 2 define the same table with different field names. Keep one definition, in Crypto Part 4.
- **Saltzer.** Identity Part 1 is the theory behind the Designate and Reach columns. The authorization series should cite it once the identity series is published.
- **Who may rewrite.** Recovery in Identity Part 4 is the Authenticate version of "who may change the policy" in Authorization Part 1.
- **Data protection.** Crypto's other half, envelope and end-to-end encryption, sits outside the grid. It may belong in the Enforced row, as the one kind of enforcement that needs no monitor in the path: holding the key is the check.
