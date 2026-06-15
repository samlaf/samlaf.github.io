---
title:  "Applied Crypto: The Changing Internet Threat Model"
category: programming
date: 2026-06-14 00:06:00
---

All the machinery in this series — keys, channels, authentication, attestation — exists to defend against an adversary. The interesting question is *where* you assume that adversary lives, and the forty-year answer hasn't been a straight line. It's been a loop.

There are three places a threat can live:

- **On the wire** — the network between two endpoints.
- **In the identity binding** — *is this key really Bob's?*
- **In the authenticated counterparty itself** — Bob is provably Bob, and Bob is hostile.

The field named that third, hardest threat almost immediately ([Lowe][ns-lowe], 1995), then spent two decades looking away from it — solving identity binding with PKI, and formally *assuming* the endpoints themselves were honest ([RFC 3552][rfc3552]) — before circling back to it in the 2020s. Everything else in the series is a response to one stop on this loop.

## 1983 · Dolev–Yao: the saboteur on the wire

[Dolev and Yao][dolev-yao] start in a world where public-key cryptography exists in principle but nobody knows how to *use* it safely. Their saboteur is on the network, can read everything passing through it, and can act as a legitimate participant in protocols. The open question of the era is foundational: can any protocol built from these primitives preserve secrecy at all, given an adversary with these capabilities? The threat model is maximally pessimistic about the channel and treats the protocol logic itself as the thing under test.

## 1995 · Lowe: the threat is a legitimate participant

[Lowe's attack][ns-lowe] on the Needham–Schroeder protocol is the result that reframes what "security" even means. He shows that even with perfect cryptography and perfect key binding, a *legitimate* participant — Mallory, with his own real key pair — can exploit the protocol's role structure to impersonate Alice to Bob, just by relaying messages Alice willingly sent him. The attack isn't about broken crypto or stolen identities; it's about the protocol logic failing to bind a message to the *role* its sender was playing. The lesson: the channel and the keys can be perfect, and the protocol can still be broken. Dangerous actors don't need to be on the wire; they can be sitting at the other end of an authenticated session. The field had its hardest threat in hand in 1995 — and then largely set it aside for twenty years.

## 1990s–2000s · PKI: identity binding becomes infrastructure

The [PKI][web-pki] wave operationalizes identity binding at scale — X.509, certificate authorities, the Web PKI. This closes the "is this really Bob's key" gap that Dolev-Yao had left as an exercise for protocol designers. In practice, this is the moment when "who am I talking to" stops being something each protocol has to solve from scratch and becomes infrastructure. Crucially, PKI solves *impersonation* — Mallory can no longer claim to be Alice — but it says nothing about whether the correctly-identified party at the other end is honest. The Lowe-style threat, where Mallory is genuinely Mallory and exploits the protocol from a legitimate role, is entirely untouched by PKI. The cost of PKI's success is that subsequent threat models start to *assume* identity binding works and turn their attention elsewhere.

## 2003 · RFC 3552: codifying the wire attacker

By the time the IETF codifies its working threat model, the assumed adversary has migrated almost entirely onto the channel. [RFC 3552][rfc3552] explicitly stipulates that *endpoints are not compromised* and worries about an attacker who can read, drop, modify, and inject on the wire. The document's whole architecture of passive vs. active attacks, confidentiality vs. integrity, is organized around a wire-level adversary. It's worth being precise about what this assumption is doing: PKI did not eliminate the malicious-counterparty threat — it only eliminated impersonation. RFC 3552 handles the residual threat by *declaring it out of scope*, not by defending against it. PKI made that stipulation feel reasonable — if you know exactly who you're talking to, the residual worry shifts to the wire — but the stipulation itself is doing the work, not the cryptography. The Lowe-style threat never went away; it was simply set aside.

## 2019 · Arkko: the threat moves back inside the session

Jari Arkko's [IETF draft][arkko] argues that the stipulation was always a stipulation, not a theorem, and it's no longer tenable. TLS, QUIC, and HTTPS have largely defeated the channel attacker. Meanwhile, the threat has moved fully *inside* the authenticated session — to counterparties who are correctly identified, correctly authenticated, and correctly behaving cryptographically, but who are malicious, coerced, or commercially misaligned with the user. PKI tells you Google is really Google; it doesn't tell you Google won't sell your data. The proposed rewrite of RFC 3552's core assumption is the formal acknowledgment: instead of "end-systems have not been compromised," the new baseline is "the *implementing* end-system has not been compromised, but the other parties may be."

## 2020s · the frontier: your supply chain, and cheap attackers

Arkko's draft predates the two developments that have since made its point undeniable.

**The counterparty is now your dependencies.** The malicious-but-authenticated party Lowe described no longer needs to be at the other end of a session — it can be code running *inside* your own process, installed deliberately, signed, and trusted. The [XZ Utils backdoor][xz-backdoor] (CVE-2024-3094) is the purest example: a maintainer spent roughly two years building legitimate trust in an upstream project, then shipped a hidden backdoor — a textbook Lowe attack at the scale of the global software supply chain. Package registries have made this routine rather than exceptional: typosquatted and malicious packages on npm and PyPI, and [malware smuggled through the Arch User Repository][aur-malware], all exploit the fact that "I installed it from the official source" was never the same as "it is safe." Your dependency manifest is a list of authenticated counterparties you've chosen to trust.

The subversion can run deeper than any code you could in principle read. An *algorithm substitution attack* swaps a correct primitive for a look-alike that behaves identically but leaks secrets to whoever planted it — the backdoored [Dual_EC_DRBG][dual-ec] random-number generator, shipped as the default in RSA's BSAFE library, is the canonical real-world case. The thing you trusted to produce randomness *was* the adversary. (There's a whole research literature on these "kleptographic" attacks; the engineering takeaway is that "the implementation is honest" is itself a trust assumption, not a given.)

**And the attacker got cheap.** LLMs are collapsing the cost and skill floor of the very attacks whose rarity used to bound the threat model. Automated vulnerability discovery, convincing spear-phishing at scale, and machine-generated malware turn what were once rare, expert capabilities into commodities — so the quiet "is this attacker realistic?" assumption behind every out-of-scope stipulation needs revisiting. And AI agents are themselves a new kind of authenticated counterparty: an agent acting with your credentials, steered by a prompt-injected instruction, is *exactly* Lowe's legitimate-participant-gone-rogue — now running inside your own tooling.

## Coming full circle

Forty years on, the field is back where Lowe left it in 1995: the cryptographic identity is impeccable, the channel is encrypted, every signature verifies — and the dangerous actor is a legitimate participant. What's changed is scale. It's no longer a single Mallory in a three-message protocol; it's cloud providers, BFT leaders, upstream maintainers, and AI agents — all correctly authenticated, any of them potentially hostile. The protocol's role structure, not the channel, is where the adversary lives.

This is the lens for the rest of the series: as you read about channels, keys, and authentication, notice that each defends a *different* assumed adversary — and that the frontier today is the authenticated-but-untrustworthy counterparty, which is exactly what confidential computing and [attestation](/programming/roots-of-trust-and-attestation.html) try to address.

## References <!-- omit in toc -->

1. [Dolev–Yao model - Wikipedia][dolev-yao]
2. [Needham–Schroeder protocol & Lowe's attack - Wikipedia][ns-lowe]
3. [Public Key Infrastructure - Wikipedia][web-pki]
4. [RFC 3552: Security Considerations Guidelines - IETF][rfc3552]
5. [An Internet Threat Model (draft-arkko) - Jari Arkko][arkko]
6. [XZ Utils Backdoor (CVE-2024-3094) - Wikipedia][xz-backdoor]
7. [Preliminary Analysis of AUR Malware - ioctl.fail][aur-malware]
8. [Dual_EC_DRBG (the backdoored RNG) - Wikipedia][dual-ec]

[dolev-yao]: https://en.wikipedia.org/wiki/Dolev%E2%80%93Yao_model "Dolev–Yao model - Wikipedia"
[ns-lowe]: https://en.wikipedia.org/wiki/Needham%E2%80%93Schroeder_protocol "Needham–Schroeder protocol & Lowe's attack - Wikipedia"
[web-pki]: https://en.wikipedia.org/wiki/Public_key_infrastructure "Public Key Infrastructure - Wikipedia"
[rfc3552]: https://datatracker.ietf.org/doc/html/rfc3552 "RFC 3552: Guidelines for Writing RFC Text on Security Considerations - IETF"
[arkko]: https://datatracker.ietf.org/doc/html/draft-arkko-arch-internet-threat-model-01 "An Internet Threat Model (draft-arkko-arch-internet-threat-model-01) - Jari Arkko"
[xz-backdoor]: https://en.wikipedia.org/wiki/XZ_Utils_backdoor "XZ Utils backdoor (CVE-2024-3094) - Wikipedia"
[aur-malware]: https://ioctl.fail/preliminary-analysis-of-aur-malware/ "Preliminary analysis of AUR malware - ioctl.fail"
[dual-ec]: https://en.wikipedia.org/wiki/Dual_EC_DRBG "Dual_EC_DRBG (the backdoored RNG) - Wikipedia"
