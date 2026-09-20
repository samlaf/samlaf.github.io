---
title:  "Identity"
category: programming
date: 2026-07-20
---

This is the intro to a short series on identity — not identity *management*, but the structure underneath it: what it means to say a key belongs to someone, who gets to write that fact down, how long it stays true, and what the internet actually does about it for hosts, humans, and workloads.

## The gap between two series

The [applied crypto series](/programming/crypto-series-intro.html) ends holding a key. It can make a channel with it, protect bytes under it, and prove to a counterparty that it holds it. What it cannot do is say *whose* key it is. Every cryptographic statement is relative to a key — "produced by the holder of K," "readable only by the holder of K" — and no amount of cryptography turns K into `example.com` or Alice.

The [authorization series](/programming/authorization-series-intro.html) starts one step further along. It assumes a subject and asks what that subject may do, and it spends four articles arguing that the subject often should not be a name at all.

Between them sits the question this series is about. Karp splits access control into four steps, and the split shows where the seam is:

```text
Identification    knowing whom to hold responsible          ← this series
Authentication    proving the right to use an identity      ← crypto series
Authorization     granting a permission                     ← authorization series
Access decision   honoring a particular request             ← authorization series
```

Identification is the act of tying a key to a party you could point at. It is not cryptography, though it is signed with cryptography. It is *trust configuration*: someone writes down "K is Alice," and everything downstream believes them.

## Everything here is a binding

The organizing idea comes from an unlikely place — a 1993 RFC by Jerry Saltzer about network addressing. His observation was that the endless confusion around names, addresses and routes dissolves once you separate the *objects* from the *bindings* between them. A name is stable. What moves is the binding, and the two questions worth asking about any binding are who may write it and when it was written.

Identity is that framework pointed at keys. A certificate is a binding of a name to a key, with a validity window. A login session is a binding of a cookie to a principal, with a lifetime. An attestation report is a binding of a key to a piece of measured software. Certificate transparency, key transparency and web-of-trust signatures are three different answers to *who may write the binding*. Short-lived certificates and revocation lists are two different answers to *when it stops being true*.

The first article sets that lens up in the domain Saltzer wrote it for, with Kubernetes and PCIe as worked examples, because the failure modes are easier to see in a network than in a PKI. Every article after it is the same lens on a different kind of principal.

## Three kinds of principal

The internet binds keys to three kinds of thing, and the machinery is different for each.

**Hosts** are named by DNS and bound by the Web PKI. Forty years of history, most of it the story of the wrong layer being trusted and the fix arriving twenty years late.

**Humans** are named by accounts, and bound by a trusted third party: a Kerberos KDC, a SAML identity provider, an OpenID Connect issuer. Every one of those is a certificate authority for people, issuing certificates that last minutes. What comes after — the session — is where most of the real security lives and least of the writing.

**Workloads** have no fingers to type a password with and no slot to plug a certificate into. Their identity has to come from the platform that launched them, which pushes the question down one layer at a time until it reaches silicon: attestation.

## Why names at all

The authorization series makes a case that many systems never needed a name — that a key, or an unforgeable reference, is a perfectly good principal on its own. This series does not disagree. SPKI said the same thing in 1999, and split its certificates into *name* certificates and *authorization* certificates precisely so you could skip the first kind. The last article looks at the systems that took that seriously: first-use trust, self-certifying names, petnames, transparency logs.

But names persist for reasons that are not cryptographic. Policy is written by humans, in human words. Responsibility attaches to people, not keys. And a person outlives every key they will ever hold, so *something* has to stay stable while the keys rotate underneath. That something is a name, and this series is about how it gets bound.

## The articles

- **[Part 1: Naming and binding](/programming/naming-and-binding.html)** — names stay put, bindings move. Saltzer's four objects and three bindings, the ARPANET's mistake, and why Kubernetes and PCIe are the cleanest modern examples of getting it right and wrong.
- **[Part 2: Keys are not names](/programming/keys-are-not-names.html)** — what cryptography can say about *who* (nothing), SPKI's split between name and authorization certificates, the three kinds of principal, and the four ways a binding ever gets written.
- **[Part 3: Hosts](/programming/identity-of-hosts.html)** — HOSTS.TXT to DNS to DNSSEC, X.500 to X.509 to the Web PKI, the CA failures and the fixes (CT, CAA, ACME, 47-day certificates), and the roots of trust it all bottoms out in.
- **[Part 4: Humans](/programming/identity-of-humans.html)** — accounts, recovery as the weakest binding, the trusted third party from Needham–Schroeder through Kerberos and SAML to OpenID Connect, the `id_token` / `access_token` seam, and sessions.
- **[Part 5: Workloads and hardware](/programming/identity-of-workloads.html)** — secret zero, cloud instance identity, SPIFFE, OIDC federation for CI, Sigstore, and attestation with TPMs and confidential VMs.
- **[Part 6: Binding without a CA](/programming/binding-without-a-ca.html)** — trust on first use, the web of trust and why it died, self-certifying names, petnames, transparency logs, and blockchain names. Ends where the authorization series begins.
