---
title:  "Where the adversary lives"
series: "Keys, names and authority, Prologue"
series_url: "/programming/keys-names-authority.html"
category: programming
date: 2026-06-03
---

> This is the prologue to three series: [applied cryptography](/programming/crypto-series-intro.html), [identity](/programming/identity-series-intro.html) and [authorization](/programming/authorization-series-intro.html). The [map](/programming/keys-names-authority.html) shows how they fit together.

- [1 · On the wire: the network between endpoints](#1--on-the-wire-the-network-between-endpoints)
- [2 · In the identity binding: *is this key really Bob's?*](#2--in-the-identity-binding-is-this-key-really-bobs)
- [3 · At the gate: someone without credentials](#3--at-the-gate-someone-without-credentials)
- [4 · Inside the boundary: Bob is provably Bob, and hostile](#4--inside-the-boundary-bob-is-provably-bob-and-hostile)
- [5 · Code running as you](#5--code-running-as-you)
- [6 · A delegate you authorized](#6--a-delegate-you-authorized)
- [7 · The data the delegate reads](#7--the-data-the-delegate-reads)
- [Aside - Adversary Model](#aside---adversary-model)
- [Where the frontier is now](#where-the-frontier-is-now)

Every mechanism in these three series exists to stop someone. A key, a certificate, a list at a resource, a monitor in the path: each one is a claim about *someone*. Secret from whom, bound by whom, non-bypassable by whom. Change the adversary, and the same mechanism goes from sufficient to decorative without a line of it changing.

So it is worth asking where the adversary lives before describing what stops them. Over sixty years the answer has moved seven times. It always moved inward, and always because the previous position got closed:

1. **On the wire** — the network between two endpoints. *(Now largely solved.)*
2. **In the identity binding** — *is this key really Bob's?* *(Now infrastructure.)*
3. **At the gate** — someone without credentials, trying to get some. *(Now infrastructure.)*
4. **Inside the boundary** — Bob is provably Bob, and Bob is hostile. *(Outgrown rather than solved.)*
5. **Code running as you** — a program holding everything you can do. *(Never closed.)*
6. **A delegate you authorized** — software acting for you, with authority you handed it. *(Live.)*
7. **The data the delegate reads** — an agent whose intent is assembled from what it reads. *(The open frontier.)*

For each, it helps to separate three things that often happened *decades apart*: the **threat**, the **theory** that modelled it, and the **implementation** that finally shipped — plus the attacks that broke those implementations in between. The recurring pattern: a threat is *modelled* long before it's *defeated*, and the deployed system gets broken many times along the way.

![Timeline of seven adversary positions, from the wire to the data a delegate reads, 1966 to today, showing each threat modelled years before it was defeated, and the last three still open](/assets/series/threat-model/threat-model-timeline.svg)

## 1 · On the wire: the network between endpoints

**Threat.** A passive eavesdropper reads your traffic; an active attacker drops, modifies, and injects it (a man-in-the-middle).

**Theory.** [Dolev and Yao][dolev-yao] (1983) formalized exactly this adversary — full control of the network — and that model is still the one we use today. Two decades later, [RFC 3552][rfc3552] (2003) made it the IETF's *default*: assume the endpoints are honest and the wire is hostile. Note the gap — the *model* of the wire attacker predates a deployed protocol that actually beats it by decades.

**Implementation — and the setup/usage split.** SSL (1995) → TLS 1.0 (1999) → TLS 1.2 with AEAD (2008) → TLS 1.3 (2018). The model was clear the whole time; the *implementations* leaked for twenty years. But the key realization is that a channel has two phases with completely different security stories:

- **Setup (the handshake) is the battleground.** The handshake negotiates versions and ciphersuites, and that negotiation is the soft underbelly: [FREAK and Logjam][logjam] (2015) downgrade a victim onto deliberately-weak export crypto without breaking any primitive. This is why cryptographic agility is now seen as a footgun — and why the negotiation-free designs from the [channels post](/programming/secure-channels.html) (Noise, WireGuard) sidestep the entire downgrade class by baking the ciphersuite into the protocol name rather than negotiating it. (Orthogonally, Heartbleed (2014) was a memory bug in OpenSSL — the library is its own attack surface, separate from the protocol.)
- **Usage (the record phase) is solved.** Once a key is established and you protect bytes with an AEAD, steady-state traffic is essentially unbreakable — there is nothing left for a wire attacker to do. The historical record-layer attacks (BEAST 2011, CRIME 2012, Lucky 13 2013, POODLE 2014) were all against *pre-AEAD* constructions — CBC modes and TLS-level compression — and AEAD plus TLS 1.3 retired them. The symmetric cipher underneath matured the same way: [DES][des] (standardized 1977) shipped with a suspiciously short 56-bit key and was brute-forced by 1998, and the open [AES][aes] competition (2001) replaced it — public scrutiny as the antidote to a quietly-weakened standard, the same openness-vs-subversion theme as the Dual_EC RNG in §5. (The remaining caveats are precise ones the [primitives post](/programming/crypto-primitives.html) covers: key-commitment, RUP, side channels.)

So the wire is the *solved* part: modern AEAD usage is airtight, and TLS 1.3 hardened setup by amputating most of the legacy negotiation those attacks rode in on. Which is precisely why the threat moved on.

## 2 · In the identity binding: *is this key really Bob's?*

**Threat.** A perfectly secure channel to the *wrong party*. The attacker breaks no crypto at all — he hands you his own public key, and you faithfully encrypt everything to him.

**Theory.** [Diffie–Hellman][dh] (1976) gave us public keys, but a key is not a name. *Binding* a given key to the right identity — proving this key really is `example.com`'s — is a separate, unglamorous problem, and exactly the one [PKI exists to solve](/programming/identity-of-hosts.html). It is not a cryptographic problem at all, which is why it gets its own [series on identity](/programming/identity-series-intro.html). (That's distinct from *naming*: whether a human-meaningful name can simultaneously be unforgeable and decentralized is a further trilemma — [Zooko's triangle](/programming/keys-are-not-names.html#zookos-triangle) — which shows up a layer up again.)

**Implementation (and its breaks).** [PKI][web-pki] — X.509, certificate authorities, the Web PKI (1990s–2000s) — turned identity binding into infrastructure, so each protocol stopped solving "who am I talking to" from scratch. Its failures are about trusting the wrong *issuer*: the Comodo and DigiNotar CA compromises (2011) minted valid certificates for domains they had no business signing, which is what drove [Certificate Transparency][ct] (2013+). Crucially, PKI solved impersonation by a stranger's *key* — and *only* that. It says nothing about who else holds Bob's credentials, or whether Bob is honest. Those are the next two positions.

## 3 · At the gate: someone without credentials

**Threat.** The attacker has no credentials and wants some. They are not a user of your system, and the whole question is whether they become one. They guess a password, replay a leaked one, or phish one.

**Theory and implementation.** This is the position most people still picture when they hear "access control," and it is the one where authorization does the least work. The engineering is all authentication. [Morris and Thompson][morris-thompson] (1979) described how Unix stopped storing passwords in the clear and started salting and hashing them. [Kerberos][kerberos] (1988) kept passwords off the network. Then came the long arc to [passkeys][passkeys] (2022), which [Part 3 of the crypto series](/programming/authentication.html) traces: move the secret out of the server's hands, and bind it to the origin so it cannot be phished. The breaks are breaches. [RockYou][rockyou] (2009) leaked 32 million plaintext passwords, and credential stuffing replays leaks like it against every login form. Accounts, sessions and recovery are [Part 4 of the identity series](/programming/identity-of-humans.html). Authorization's contribution here is a list, checked once the gate has decided who is knocking.

**Why it moved.** Authentication became infrastructure. It is not perfect, but it is good enough that attacking the gate stopped being the cheapest route in. The cheapest route is to already be inside.

## 4 · Inside the boundary: Bob is provably Bob, and hostile

**Threat.** A legitimate participant, hostile. Every signature verifies, the channel is encrypted, and they log in correctly every time, because the credential is theirs.

**Theory.** Two fields reached this adversary from opposite ends.

Operating systems got there first, and fast. The foundational theory took about six years. Lampson's [access matrix][access-matrix] (1971) gave the field the object it still reasons with. Graham and Denning (1972) worked out its protection rules. [Bell and LaPadula][blp] (1973) formalized what a military confinement policy even means. [Harrison, Ruzzo and Ullman][hru] (1976) proved that in the general case you cannot decide whether a given permission will ever leak to a given subject. The safety problem is undecidable, which is why every tractable model since is a deliberate restriction of the general one. And Lampson's confinement problem (1973) asked the question the authorization series keeps returning to: can a program you run on someone else's behalf be stopped from leaking what it sees?

Protocols got there later. [Lowe's attack][ns-lowe] on the Needham–Schroeder authentication protocol (1995) showed that with *perfect* crypto and *perfect* key binding, a legitimate participant — Mallory, holding his own real key pair — can still subvert a protocol by exploiting its *role structure*, relaying messages to impersonate Alice to a third party. The lesson: the channel and the keys can be flawless and the protocol still broken. The field had this threat in hand in 1995, and then shelved it for twenty years, because a secure channel plus PKI *felt* like enough. [Arkko's draft][arkko] (2019) re-opened it formally: the new baseline should be "the *implementing* end-system isn't compromised, but the other parties may be."

**Implementation.** Unix file permissions, then decades later the mandatory-access-control systems that actually implemented Bell and LaPadula, such as [SELinux][selinux] (2000). [Part 1 of the authorization series](/programming/authorization-models.html) is largely an account of this machinery.

And it was never only theoretical. A hostile endpoint has been part of the internet since its infancy: the [Morris worm][morris] (1988) turned thousands of legitimate hosts into attackers overnight by exploiting buffer overflows and weak passwords — the first worm to hit the early internet at scale, though the self-replicating idea traces back to the benign Creeper program on the ARPANET in 1971. By the time RFC 3552 wrote down "endpoints are not compromised" in 2003, that had been a convenient fiction for fifteen years. Today the hostile party can be the infrastructure itself: [confidential computing and attestation](/programming/identity-of-workloads.html) try to defend a workload against the cloud host it runs on.

**Why it moved.** It didn't get solved so much as outgrown. Keying on identity works here. The subject is a person, the person has intent, and holding them to a policy is coherent. The trouble starts when the thing taking the action is not the person.

## 5 · Code running as you

**Threat.** A program, carrying your full authority because it inherited it by running as you. It need not be malicious. It only needs to be talked into using a power it holds for a purpose it was not asked for.

**Theory.** [Saltzer and Schroeder][saltzer-schroeder] named the cure in 1975: every program should run with the least authority its job requires. [Hardy][confused-deputy] named the disease in 1988, after watching a compiler be persuaded to overwrite a billing file it was merely *able* to reach — the confused deputy. Note the thirteen-year gap, and note which came first. The [capability][capabilities] tradition had the structural answer even earlier: Dennis and Van Horn (1966), then KeyKOS and the systems [Part 4 of the authorization series](/programming/capabilities.html) is about. All of them make designating a thing and holding authority over it the same act, so there is no name an attacker can utter to borrow a power they were never given.

**Implementation.** Essentially none, on the platform where it mattered most. The desktop operating system shipped position-four controls into a position-five world and still does: every program you launch holds everything you can do. Mobile platforms bought some of it back with per-app permissions and per-app storage, twenty years late and only for one class of software.

The software supply chain turned this position into the routine one. The [xz backdoor][xz-backdoor] (2024) was a trusted maintainer who spent two years earning commit rights and then shipped a backdoor. Malware on [npm, PyPI, and the AUR][aur-malware] is now routine. Every one of these runs with the whole authority of whoever installed it. Even a primitive can be subverted: [Dual_EC_DRBG][dual-ec] was a standard random number generator with a suspected backdoor.

**Why it didn't move.** This one never closed. It accumulated. Positions six and seven are both built on top of an unfixed position five, which is why the confused deputy keeps reappearing in each of them wearing new clothes.

## 6 · A delegate you authorized

**Threat.** Software acting for you, on purpose, with authority you deliberately handed it — and exercising that authority for something you did not intend. An OAuth client, a service account, a CI job, an integration. Nothing is stolen and nobody is impersonated.

**Theory and implementation.** This is the position where the industry did real work, because delegation became the normal way software is composed and the bill arrived quickly. OAuth 1.0 (2007) and [2.0][oauth2] (2012) made third-party delegation routine. Scopes, audiences and short expiry made it survivable. [Macaroons][macaroons] (2014) showed that a credential can carry its own attenuation, so a delegate can hand on strictly less than it holds. [Part 3 of the authorization series](/programming/carriers.html) is mostly about how well that worked and where it stopped short.

Arkko's sharper point lives here: the cryptographic endpoints often aren't the *real* ends at all. A CDN terminates your TLS, so the "server" you share a key with isn't the origin. And a delegated-authorization flow like OAuth is a triangle, not a line. It deliberately splits a trusted server-to-server *back channel* from a browser-mediated *front channel*, because those legs face different attackers. Front-channel interception of the authorization code is exactly why [PKCE][pkce] (2015) exists. Every delegate and intermediary is one more authenticated party you're trusting, so the two-party "secure channel" is, at internet scale, a convenient fiction.

**Why it moved.** It didn't, entirely — this is a live position. But it rests on an assumption that held until recently: the delegate's *plan* is fixed. You grant a CI job the authority its pipeline needs because you can read the pipeline. When the plan stops being knowable in advance, the scoping story stops working.

## 7 · The data the delegate reads

**Threat.** The delegate's intent is assembled at runtime out of documents, pages, issues, and tool output — any of which an attacker may have written. There is no subject to blame, no credential was stolen, and the agent is behaving exactly as designed. It read something and did what it said.

**Theory.** [Greshake and co-authors][greshake] gave it a name in 2023, indirect prompt injection, and the literature since has been enormous. But the shape is Hardy's, thirty-five years on. The injected text supplies a designator — a path, a URL, a repository. The agent's ambient authority supplies the rest. It is a confused deputy whose confusion is now the normal operating mode rather than a bug, because reading untrusted input and acting on it *is* the product. LLMs also change the economics on the attacker's side: they cheapen the attacks whose rarity used to bound the model.

**Implementation.** Open. The cure is probably the old one: take away the ambient authority, so that the injected designator names nothing worth having. How far that gets you in practice is still being worked out. The [LLM sandboxing article](/programming/llm-sandbox.html) works through it for coding agents.

## Aside - Adversary Model

The wire attacker this article opens with is just one point in a much bigger space. An [adversary][adversary-crypto] is classified along orthogonal axes: *passive* (eavesdrop only) vs *active* (deviate, drop, inject); *computationally bounded* vs unbounded; *static* vs **adaptive** (picks new targets as it learns); *non-mobile* vs *mobile* (corruptions come and go over time). Dolev–Yao is one coordinate in that space — an active, bounded attacker who owns the network — and its computational cousin is the IND-CPA / IND-CCA game in [Cryptographic Primitives](/programming/crypto-primitives.html). The [distributed-systems literature][adversary-models] populates the rest, classifying corruption of *participants* (passive → crash → omission → **Byzantine**) rather than of the wire. The engineering stance that falls out is **zero-trust**: assume a strong, adaptive adversary at *every* boundary and trust nothing implicitly — which stops being paranoia the moment you accept position 4 above, where an authenticated participant can itself be hostile (and where Byzantine fault tolerance, threshold crypto, and blockchains live).

Those axes don't fit on a plane, so the cleanest way to read an adversary is as a *polyline* crossing one axis per feature (a [parallel-coordinates][parallel-coords] plot): the higher it rides, the stronger the attacker. Two things are worth stressing. First, the axes are orthogonal to *what* is attacked — an *adaptive*, *mobile*, *Byzantine* adversary describes a set of corrupted nodes as readily as the wire. Byzantine-on-the-wire is just active injection à la Dolev–Yao (benign drops and noise sit lower, as crash/omission), and *mobile* corruption that comes and goes is exactly what forces proactive secret-sharing/recovery. Second, *unbounded* compute has a practically important midpoint: a **quantum** adversary is unbounded only *with respect to today's elliptic-curve and RSA assumptions* (via Shor) — not against symmetric crypto or post-quantum schemes — which is why "harvest now, decrypt later" is a passive attacker on a quantum timer.

![Parallel-coordinates plot of the adversary model: four orthogonal axes — behaviour (passive→crash→omission→Byzantine), compute (bounded→quantum→unbounded), targeting (static→adaptive), and mobility (non-mobile→mobile) — each applying to the wire or a corrupted node, with a passive eavesdropper, Dolev–Yao, a quantum harvest-now-decrypt-later attacker, and a mobile Byzantine node drawn as polylines](/assets/series/threat-model/adversary-axes.svg)

Once the adversary is inside the machine, one more ladder matters: how much of the machine they own. An attacker may control only the input a program reads, or run arbitrary code in it, or own its kernel. That ladder decides what any enforcer is worth, so [Part 2 of the authorization series](/programming/authority-enforcement.html#who-is-the-attacker) draws it.

TODO: related with content of this thread: https://x.com/ittaia/status/2020963847134454041

## Where the frontier is now

The story isn't that the threat *moved* on its own. We kept *solving* the outer positions, so the adversary kept relocating to whatever was still open. The wire took thirty-five years to genuinely secure (Dolev–Yao's 1983 model to TLS 1.3 in 2018). Identity binding and the gate became infrastructure. What is left is inside: the authenticated party who is hostile, the code that runs as you, the delegate you trusted, and the data that delegate reads. Position five never closed, and six and seven are built on top of it.

The seven positions are also the three series:

- **The wire** is the [applied crypto series](/programming/crypto-series-intro.html): primitives, channels, keys.
- **The identity binding** is the [identity series](/programming/identity-series-intro.html): DNS, the Web PKI, identity providers, attestation, and the roots they all bottom out in.
- **The gate** is shared. Crypto Part 3 covers proving you hold a key, and identity Part 4 covers accounts and sessions.
- **Positions four to six** are the [authorization series](/programming/authorization-series-intro.html). It asks what a correctly identified party may do, and what makes the answer bind when the party is a program.
- **Position seven** is the [LLM sandboxing article](/programming/llm-sandbox.html), which applies all three series to AI agents.

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
18. [Password Security: A Case History - Morris and Thompson][morris-thompson]
19. [Kerberos - Wikipedia][kerberos]
20. [Passkey - Wikipedia][passkeys]
21. [RockYou data breach - Wikipedia][rockyou]
22. [Access Control Matrix - Wikipedia][access-matrix]
23. [Bell–LaPadula Model - Wikipedia][blp]
24. [HRU (security) - Wikipedia][hru]
25. [Security-Enhanced Linux - Wikipedia][selinux]
26. [The Protection of Information in Computer Systems - Saltzer and Schroeder][saltzer-schroeder]
27. [The Confused Deputy - Norm Hardy][confused-deputy]
28. [Capability-based Security - Wikipedia][capabilities]
29. [RFC 6749: The OAuth 2.0 Authorization Framework - IETF][oauth2]
30. [RFC 7636: Proof Key for Code Exchange (PKCE) - IETF][pkce]
31. [Macaroons: Cookies with Contextual Caveats][macaroons]
32. [Not What You've Signed Up For: Indirect Prompt Injection - Greshake et al.][greshake]

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
[morris-thompson]: https://dl.acm.org/doi/10.1145/359168.359172 "Password Security: A Case History - Morris and Thompson"
[kerberos]: https://en.wikipedia.org/wiki/Kerberos_(protocol) "Kerberos (protocol) - Wikipedia"
[passkeys]: https://en.wikipedia.org/wiki/Passkey_(authentication) "Passkey - Wikipedia"
[rockyou]: https://en.wikipedia.org/wiki/RockYou "RockYou - Wikipedia"
[access-matrix]: https://en.wikipedia.org/wiki/Access_control_matrix "Access control matrix - Wikipedia"
[blp]: https://en.wikipedia.org/wiki/Bell%E2%80%93LaPadula_model "Bell–LaPadula model - Wikipedia"
[hru]: https://en.wikipedia.org/wiki/HRU_(security) "HRU (security) - Wikipedia"
[selinux]: https://en.wikipedia.org/wiki/Security-Enhanced_Linux "Security-Enhanced Linux - Wikipedia"
[saltzer-schroeder]: https://www.cs.virginia.edu/~evans/cs551/saltzer/ "The Protection of Information in Computer Systems - Saltzer and Schroeder"
[confused-deputy]: https://www.cs.utexas.edu/~witchel/S25-380L/papers/hardy88confused.pdf "The Confused Deputy - Norm Hardy"
[capabilities]: https://en.wikipedia.org/wiki/Capability-based_security "Capability-based security - Wikipedia"
[oauth2]: https://datatracker.ietf.org/doc/html/rfc6749 "RFC 6749: The OAuth 2.0 Authorization Framework - IETF"
[pkce]: https://datatracker.ietf.org/doc/html/rfc7636 "RFC 7636: Proof Key for Code Exchange by OAuth Public Clients - IETF"
[macaroons]: https://static.googleusercontent.com/media/research.google.com/en/us/pubs/archive/41892.pdf "Macaroons: Cookies with Contextual Caveats"
[greshake]: https://arxiv.org/abs/2302.12173 "Not What You've Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection - Greshake et al."
