---
title:  "The Changing Internet Threat Model"
series: "Applied Crypto, Prologue"
series_url: "/programming/crypto-series-intro.html"
category: programming
date: 2026-06-05
---

All the machinery in this series — keys, channels, authentication, attestation — exists to defend against an adversary. The interesting question is *where* you assume that adversary lives, and over forty years the frontier has moved.

There are three places a threat can live:

1. **On the wire** — the network between two endpoints. *(Now largely solved.)*
2. **In the identity binding** — *is this key really Bob's?* *(Now infrastructure.)*
3. **Inside the authenticated session** — Bob is provably Bob, and Bob is hostile. *(The open frontier.)*

For each, it helps to separate three things that often happened *decades apart*: the **threat**, the **theory** that modelled it, and the **implementation** that finally shipped — plus the attacks that broke those implementations in between. The recurring pattern: a threat is *modelled* long before it's *defeated*, and the deployed system gets broken many times along the way.

![Timeline of internet threat models across three layers — the wire, identity binding, and inside the session — from 1976 to today, showing each threat modelled years before it was defeated](/assets/threat-model/threat-model-timeline.svg)

## 1 · On the wire: the network between endpoints

**Threat.** A passive eavesdropper reads your traffic; an active attacker drops, modifies, and injects it (a man-in-the-middle).

**Theory.** [Dolev and Yao][dolev-yao] (1983) formalized exactly this adversary — full control of the network — and that model is still the one we use today. Two decades later, [RFC 3552][rfc3552] (2003) made it the IETF's *default*: assume the endpoints are honest and the wire is hostile. Note the gap — the *model* of the wire attacker predates a deployed protocol that actually beats it by decades.

**Implementation — and the setup/usage split.** SSL (1995) → TLS 1.0 (1999) → TLS 1.2 with AEAD (2008) → TLS 1.3 (2018). The model was clear the whole time; the *implementations* leaked for twenty years. But the key realization is that a channel has two phases with completely different security stories:

- **Setup (the handshake) is the battleground.** The handshake negotiates versions and ciphersuites, and that negotiation is the soft underbelly: [FREAK and Logjam][logjam] (2015) downgrade a victim onto deliberately-weak export crypto without breaking any primitive. This is why cryptographic agility is now seen as a footgun — and why the negotiation-free designs from the [channels post](/programming/secure-channels.html) (Noise, WireGuard) sidestep the entire downgrade class by baking the ciphersuite into the protocol name rather than negotiating it. (Orthogonally, Heartbleed (2014) was a memory bug in OpenSSL — the library is its own attack surface, separate from the protocol.)
- **Usage (the record phase) is solved.** Once a key is established and you protect bytes with an AEAD, steady-state traffic is essentially unbreakable — there is nothing left for a wire attacker to do. The historical record-layer attacks (BEAST 2011, CRIME 2012, Lucky 13 2013, POODLE 2014) were all against *pre-AEAD* constructions — CBC modes and TLS-level compression — and AEAD plus TLS 1.3 retired them. The symmetric cipher underneath matured the same way: [DES][des] (standardized 1977) shipped with a suspiciously short 56-bit key and was brute-forced by 1998, and the open [AES][aes] competition (2001) replaced it — public scrutiny as the antidote to a quietly-weakened standard, the same openness-vs-subversion theme as the Dual_EC RNG in §3. (The remaining caveats are precise ones the [primitives post](/programming/crypto-primitives.html) covers: key-commitment, RUP, side channels.)

So the wire is the *solved* part: modern AEAD usage is airtight, and TLS 1.3 hardened setup by amputating most of the legacy negotiation those attacks rode in on. Which is precisely why the threat moved on.

## 2 · In the identity binding: *is this key really Bob's?*

**Threat.** A perfectly secure channel to the *wrong party*. The attacker breaks no crypto at all — he hands you his own public key, and you faithfully encrypt everything to him.

**Theory.** [Diffie–Hellman][dh] (1976) gave us public keys, but a key is not a name. *Binding* a given key to the right identity — proving this key really is `example.com`'s — is a separate, unglamorous problem, and exactly the one PKI exists to solve. (That's distinct from *naming*: whether a human-meaningful name can simultaneously be unforgeable and decentralized is a further trilemma — Zooko's triangle — which shows up a layer up, in the [capstone](/programming/roots-of-trust-and-attestation.html).)

**Implementation (and its breaks).** [PKI][web-pki] — X.509, certificate authorities, the Web PKI (1990s–2000s) — turned identity binding into infrastructure, so each protocol stopped solving "who am I talking to" from scratch. Its failures are about trusting the wrong *issuer*: the Comodo and DigiNotar CA compromises (2011) minted valid certificates for domains they had no business signing, which is what drove [Certificate Transparency][ct] (2013+). Crucially, PKI solved *impersonation* — and *only* impersonation. It says nothing about whether the correctly-identified party is honest, which is exactly the next threat.

## 3 · Inside the session: the authenticated counterparty itself

**Threat.** Bob is provably Bob — every signature verifies, the channel is encrypted — and Bob is hostile. The dangerous actor is a *legitimate, authenticated* participant.

**Theory.** This was modelled startlingly early. [Lowe's attack][ns-lowe] on the Needham–Schroeder authentication protocol (1995) showed that with *perfect* crypto and *perfect* key binding, a legitimate participant — Mallory, holding his own real key pair — can still subvert a protocol by exploiting its *role structure*, relaying messages to impersonate Alice to a third party. The lesson: the channel and the keys can be flawless and the protocol still broken. The field had its hardest threat in hand in 1995 — and then shelved it for twenty years, because a secure channel plus PKI *felt* like enough. [Arkko's draft][arkko] (2019) re-opened it formally: the new baseline should be "the *implementing* end-system isn't compromised, but the other parties may be."

And it was never only theoretical. A hostile endpoint has been part of the internet since its infancy: the [Morris worm][morris] (1988) turned thousands of legitimate hosts into attackers overnight by exploiting buffer overflows and weak passwords — the first worm to hit the early internet at scale, though the self-replicating idea traces back to the benign Creeper program on the ARPANET in 1971. By the time RFC 3552 wrote down "endpoints are not compromised" in 2003, that had been a convenient fiction for fifteen years.

Arkko's sharper point is that the cryptographic endpoints often aren't the *real* ends at all. A CDN terminates your TLS, so the "server" you share a key with isn't the origin. And a [delegated-authorization flow like OAuth](/programming/authentication.html) is a triangle, not a line — it deliberately splits a trusted server-to-server *back channel* from a browser-mediated *front channel*, because those legs face different attackers (front-channel authorization-code interception is exactly why PKCE exists). Every delegate and intermediary is one more authenticated party you're trusting, so the two-party "secure channel" is, at internet scale, a convenient fiction.

**Implementation (the live frontier).** This is the unsolved layer. [Confidential computing and attestation](/programming/roots-of-trust-and-attestation.html) try to defend against malicious *infrastructure* — a hostile cloud host running your workload. But the authenticated counterparty is increasingly your own software: the [xz backdoor][xz-backdoor] (2024) was a trusted maintainer who spent two years earning commit rights and then shipped a backdoor, and malware on [npm, PyPI, and the AUR][aur-malware] is now routine; even the primitive itself can be subverted ([Dual_EC_DRBG][dual-ec]). And LLMs change the economics: they cheapen the attacks whose rarity used to bound the model, and an AI agent acting with your credentials under a prompt-injected instruction is *exactly* Lowe's legitimate-participant-gone-rogue — now running inside your own tooling.

## Aside - Adversary Model

The wire attacker this section opens with is just one point in a much bigger space. An [adversary][adversary-crypto] is classified along orthogonal axes: *passive* (eavesdrop only) vs *active* (deviate, drop, inject); *computationally bounded* vs unbounded; *static* vs **adaptive** (picks new targets as it learns); *non-mobile* vs *mobile* (corruptions come and go over time). Dolev–Yao is one coordinate in that space — an active, bounded attacker who owns the network — and its computational cousin is the IND-CPA / IND-CCA game in [Cryptographic Primitives](/programming/crypto-primitives.html). The [distributed-systems literature][adversary-models] populates the rest, classifying corruption of *participants* (passive → crash → omission → **Byzantine**) rather than of the wire. The engineering stance that falls out is **zero-trust**: assume a strong, adaptive adversary at *every* boundary and trust nothing implicitly — which stops being paranoia the moment you accept layer 3 below, where an authenticated participant can itself be hostile (and where Byzantine fault tolerance, threshold crypto, and blockchains live).

Those axes don't fit on a plane, so the cleanest way to read an adversary is as a *polyline* crossing one axis per feature (a [parallel-coordinates][parallel-coords] plot): the higher it rides, the stronger the attacker. Two things are worth stressing. First, the axes are orthogonal to *what* is attacked — an *adaptive*, *mobile*, *Byzantine* adversary describes a set of corrupted nodes as readily as the wire. Byzantine-on-the-wire is just active injection à la Dolev–Yao (benign drops and noise sit lower, as crash/omission), and *mobile* corruption that comes and goes is exactly what forces proactive secret-sharing/recovery. Second, *unbounded* compute has a practically important midpoint: a **quantum** adversary is unbounded only *with respect to today's elliptic-curve and RSA assumptions* (via Shor) — not against symmetric crypto or post-quantum schemes — which is why "harvest now, decrypt later" is a passive attacker on a quantum timer.

![Parallel-coordinates plot of the adversary model: four orthogonal axes — behaviour (passive→crash→omission→Byzantine), compute (bounded→quantum→unbounded), targeting (static→adaptive), and mobility (non-mobile→mobile) — each applying to the wire or a corrupted node, with a passive eavesdropper, Dolev–Yao, a quantum harvest-now-decrypt-later attacker, and a mobile Byzantine node drawn as polylines](/assets/threat-model/adversary-axes.svg)

TODO: related with content of this thread: https://x.com/ittaia/status/2020963847134454041

## Where the frontier is now

The story isn't that the threat *moved* on its own — it's that we kept *solving* the inner layers, so the adversary kept relocating to whatever was still open. The wire took thirty-five years to genuinely secure (Dolev–Yao's 1983 model to TLS 1.3 in 2018); identity binding became infrastructure; and what's left is the threat Lowe already saw in 1995, now at the scale of cloud providers, upstream maintainers, and AI agents — all correctly authenticated, any of them potentially hostile. The protocol's role structure, not the channel, is where the adversary lives.

That's the lens for the rest of the series: each post defends a *different* assumed adversary, and the frontier today is the authenticated-but-untrustworthy counterparty — which is exactly what [attestation](/programming/roots-of-trust-and-attestation.html) tries to pin down.

## References <!-- omit in toc -->

1. [Diffie–Hellman Key Exchange - Wikipedia][dh]
2. [Dolev–Yao Model - Wikipedia][dolev-yao]
3. [Needham–Schroeder Protocol & Lowe's Attack - Wikipedia][ns-lowe]
4. [Public Key Infrastructure - Wikipedia][web-pki]
5. [Certificate Transparency][ct]
6. [RFC 3552: Security Considerations Guidelines - IETF][rfc3552]
7. [Transport Layer Security (history & attacks) - Wikipedia][tls]
8. [The Logjam Attack - weakdh.org][logjam]
9. [An Internet Threat Model (draft-arkko) - Jari Arkko][arkko]
10. [XZ Utils Backdoor (CVE-2024-3094) - Wikipedia][xz-backdoor]
11. [Preliminary Analysis of AUR Malware - ioctl.fail][aur-malware]
12. [Dual_EC_DRBG (the backdoored RNG) - Wikipedia][dual-ec]
13. [Modeling the Adversary - Decentralized Thoughts][adversary-models]
14. [Adversary - Wikipedia][adversary-crypto]
15. [Data Encryption Standard - Wikipedia][des]
16. [Advanced Encryption Standard - Wikipedia][aes]
17. [Morris Worm - Wikipedia][morris]

[dh]: https://en.wikipedia.org/wiki/Diffie%E2%80%93Hellman_key_exchange "Diffie–Hellman key exchange - Wikipedia"
[dolev-yao]: https://en.wikipedia.org/wiki/Dolev%E2%80%93Yao_model "Dolev–Yao model - Wikipedia"
[ns-lowe]: https://en.wikipedia.org/wiki/Needham%E2%80%93Schroeder_protocol "Needham–Schroeder protocol & Lowe's attack - Wikipedia"
[web-pki]: https://en.wikipedia.org/wiki/Public_key_infrastructure "Public Key Infrastructure - Wikipedia"
[ct]: https://certificate.transparency.dev/ "Certificate Transparency"
[rfc3552]: https://datatracker.ietf.org/doc/html/rfc3552 "RFC 3552: Guidelines for Writing RFC Text on Security Considerations - IETF"
[tls]: https://en.wikipedia.org/wiki/Transport_Layer_Security "Transport Layer Security (history & attacks) - Wikipedia"
[logjam]: https://weakdh.org/ "The Logjam Attack - weakdh.org"
[arkko]: https://datatracker.ietf.org/doc/html/draft-arkko-arch-internet-threat-model-01 "An Internet Threat Model (draft-arkko-arch-internet-threat-model-01) - Jari Arkko"
[xz-backdoor]: https://en.wikipedia.org/wiki/XZ_Utils_backdoor "XZ Utils backdoor (CVE-2024-3094) - Wikipedia"
[aur-malware]: https://ioctl.fail/preliminary-analysis-of-aur-malware/ "Preliminary analysis of AUR malware - ioctl.fail"
[dual-ec]: https://en.wikipedia.org/wiki/Dual_EC_DRBG "Dual_EC_DRBG (the backdoored RNG) - Wikipedia"
[adversary-models]: https://decentralizedthoughts.github.io/2019-06-07-modeling-the-adversary/ "Modeling the Adversary - Decentralized Thoughts"
[adversary-crypto]: https://en.wikipedia.org/wiki/Adversary_(cryptography) "Adversary (cryptography) - Wikipedia"
[parallel-coords]: https://en.wikipedia.org/wiki/Parallel_coordinates "Parallel coordinates - Wikipedia"
[des]: https://en.wikipedia.org/wiki/Data_Encryption_Standard "Data Encryption Standard - Wikipedia"
[aes]: https://en.wikipedia.org/wiki/Advanced_Encryption_Standard "Advanced Encryption Standard - Wikipedia"
[morris]: https://en.wikipedia.org/wiki/Morris_worm "Morris worm - Wikipedia"
