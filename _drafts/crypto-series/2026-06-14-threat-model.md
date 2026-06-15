---
title:  "Applied Crypto: The Changing Internet Threat Model"
category: programming
date: 2026-06-14 00:06:00
---

All the machinery in this series — keys, channels, authentication, attestation — exists to defend against an adversary, and the interesting story is that *where* we assume that adversary lives has moved steadily over forty years. This prologue traces that migration; everything else in the series is a response to one stop or another along it.

## The Changing Internet Threat Model

The history of internet security can be read as a steady migration of *where* the threat is assumed to live — from the wire, to identity binding, to the authenticated counterparty itself. Four moments mark the transitions.

### Dolev-Yao (1983): the saboteur on the wire

Dolev and Yao start in a world where public-key cryptography exists in principle but nobody knows how to *use* it safely. Their saboteur is on the network, can read everything passing through it, and can act as a legitimate participant in protocols. The open question of the era is foundational: can any protocol built from these primitives preserve secrecy at all, given an adversary with these capabilities? The threat model is maximally pessimistic about the channel and treats the protocol logic itself as the thing under test.

### Lowe's attack on Needham-Schroeder (1995): the punctuation mark

Lowe's attack is the result that reframes what "security" even means. He shows that even with perfect cryptography and perfect key binding, a *legitimate* participant — Mallory, with his own real key pair — can exploit the protocol's role structure to impersonate Alice to Bob, just by relaying messages Alice willingly sent him. The attack isn't about broken crypto or stolen identities; it's about the protocol logic failing to bind a message to the *role* its sender was playing. The lesson: the channel and the keys can be perfect, and the protocol can still be broken. Dangerous actors don't need to be on the wire; they can be sitting at the other end of an authenticated session.

### PKI deployment (1990s–2000s): operationalizing identity

The PKI wave operationalizes identity binding at scale — X.509, certificate authorities, the Web PKI. This closes the "is this really Bob's key" gap that Dolev-Yao had left as an exercise for protocol designers. In practice, this is the moment when "who am I talking to" stops being something each protocol has to solve from scratch and becomes infrastructure. Crucially, PKI solves *impersonation* — Mallory can no longer claim to be Alice — but it says nothing about whether the correctly-identified party at the other end is honest. The Lowe-style threat, where Mallory is genuinely Mallory and exploits the protocol from a legitimate role, is entirely untouched by PKI. The cost of PKI's success is that subsequent threat models start to *assume* identity binding works and turn their attention elsewhere, leaving the question of malicious-but-authenticated counterparties largely unaddressed.

### RFC 3552 (2003): codifying the channel attacker

By the time the IETF codifies its working threat model, the assumed adversary has migrated almost entirely onto the channel. RFC 3552 explicitly stipulates that *endpoints are not compromised* and worries about an attacker who can read, drop, modify, and inject on the wire. The document's whole architecture of passive vs. active attacks, confidentiality vs. integrity, is organized around a wire-level adversary. It's worth being precise about what this assumption is doing: PKI did not eliminate the malicious-counterparty threat — it only eliminated impersonation. RFC 3552 handles the residual threat by *declaring it out of scope*, not by defending against it. PKI made that stipulation feel reasonable — if you know exactly who you're talking to, the residual worry shifts to the wire — but the stipulation itself is doing the work, not the cryptography. The Lowe-style threat never went away; it was simply set aside.

### Arkko's proposal (2019): the threat moves inside the session

Jari Arkko's [ietf draft](https://datatracker.ietf.org/doc/html/draft-arkko-arch-internet-threat-model-01) argues that the stipulation was always a stipulation, not a theorem, and it's no longer tenable. TLS, QUIC, and HTTPS have largely defeated the channel attacker. Meanwhile, the threat has moved fully *inside* the authenticated session — to counterparties who are correctly identified, correctly authenticated, and correctly behaving cryptographically, but who are malicious, coerced, or commercially misaligned with the user. PKI tells you Google is really Google; it doesn't tell you Google won't sell your data. The proposed rewrite of RFC 3552's core assumption is the formal acknowledgment: instead of "end-systems have not been compromised," the new baseline is "the *implementing* end-system has not been compromised, but the other parties may be."

### Coming full circle

We're back to a Lowe-style world where the dangerous actor is a legitimate participant — except now at the scale of cloud providers, BFT leaders, and centralized infrastructure, rather than a single Mallory in a three-message protocol. The cryptographic identity is impeccable, the channel is encrypted, the signatures all verify, and the threat is still real. Forty years of threat-model evolution have brought the field back to the realization Lowe forced on it in 1995: the protocol's role structure, not the channel, is where the adversary lives.

This is the lens for the rest of the series: as you read about channels, keys, and authentication, notice that each defends a *different* assumed adversary — and that the frontier today is the authenticated-but-untrustworthy counterparty, which is exactly what confidential computing and [attestation](/programming/roots-of-trust-and-attestation.html) try to address.
