---
title:  "What a Secure Channel Doesn't Give You"
series: "Applied Crypto, Part 5"
series_url: "/programming/crypto-series-intro.html"
category: programming
date: 2026-06-10
---

> This is Part 5 of a six-part [series on applied cryptography](/programming/crypto-series-intro.html).
>
> - **[Prologue: The changing internet threat model](/programming/threat-model.html)** — forty years of the adversary migrating from the wire, to the identity binding, to the authenticated counterparty itself.
> - **[Part 1: Cryptographic primitives](/programming/crypto-primitives.html)** — the atoms: PRFs and PRPs, block and stream ciphers, AEAD, MACs and signatures.
> - **[Part 2: Key exchange & secure channels](/programming/secure-channels.html)** — establishing the shared secret, from a pre-shared key up to fully-negotiated TLS.
> - **[Part 3: Proving you hold a key](/programming/authentication.html)** — from plaintext passwords to passkeys: what the prover holds, what the verifier stores, and what crosses the wire.
> - **[Part 4: Keys](/programming/keys.html)** — the life of a key: the entropy that seeds it, where it lives, and how it's wrapped.
> - **Part 5: What a secure channel doesn't give you** — the capstone: the channel is the easy part, and thirteen things it leaves for you.

The last post. We've walked the whole stack — primitives, channels, proof of possession, and the keys underneath all of it — and we end holding a key we can use and prove we hold. Worth closing on the humbling part: that was the *easy* part. Everything that turns "I share a key with the holder of pk" into a system somebody can use lives above the channel, and this post is the inventory.

Two of the biggest items get their own series. Knowing *whose* key it is — anchoring it in a name, a root of trust, an attestation — is the [identity series](/programming/identity-series-intro.html). Knowing what the holder *may do* is the [authorization series](/programming/authorization-series-intro.html). The rest are yours.

## What a secure channel still doesn't give you

Analogously to Tristan Hume's [Pipes Kill Productivity][thume-pipes], we can describe cryptographic pipes (secure channels) as:
- Rootless. A secure channel reduces "trust the network" to "trust a key" but never eliminates trust — somebody has to anchor the key out of band. PKI, TOFU, hardcoded fingerprints, DNSSEC, blockchain registries, key transparency logs. This is the exact same bootstrap problem Kademlia has, just shifted into crypto-space. Every system reinvents it. (This bootstrap problem is the [roots of trust](/programming/identity-of-hosts.html#roots-of-trust) the identity series bottoms out in.)
- Unauthorized. Authentication answers "who"; it doesn't answer "may they". You will write the authz layer. Every time. Capabilities (macaroons, biscuits), ACLs, role tables, OPA — all of it lives above the channel, and all of it is the [authorization series](/programming/authorization-series-intro.html).
- Nameless. Public keys aren't names. You will build, or import, a naming layer (Zooko's triangle applies: secure / human-meaningful / decentralized — pick two). Petnames, ENS, DNS-over-something, .onion vanity, GPG WoT. All ad hoc, none portable. This is the whole [identity series](/programming/identity-series-intro.html), and [Keys are not names](/programming/keys-are-not-names.html) is where it starts.
- Stale. Keys leak, certs expire, devices get lost, employees quit. You need rotation, revocation, and a story for "this was Alice and now isn't." CRL/OCSP, short-lived certs (SPIFFE), key transparency, ratchets. The state machine for "current trust" is its own distributed system — the identity series reads it as a [binding with a lifetime](/programming/naming-and-binding.html#turning-the-lens-on-keys), and the [hosts post](/programming/identity-of-hosts.html#revocation-and-shortening-the-binding-instead) follows the Web PKI's forty-year argument with it.
- Brittle (cryptographically). Algorithms get deprecated faster than your dependency tree updates. SHA-1, RC4, MD5, soon RSA-2048 and ECDH against a quantum adversary. Cipher agility is the "Mismatched" problem on hard mode — you can't just add a JSON field, you have to renegotiate primitives without opening a downgrade attack. (See the negotiation-as-footgun discussion in [Key Exchange & Secure Channels](/programming/secure-channels.html) — agility is exactly the attack surface TLS keeps getting burned by.)
- Leaky. The channel encrypts content but not envelope: who talks to whom, when, how often, how much. Traffic analysis, timing, sizes, fingerprintable handshakes (JA3/JA4). Padding, cover traffic, mixnets — and each of those is its own pile of work.
- Replayable. A single channel handles ordering inside its lifetime, but the moment your message escapes the channel (queued, logged, persisted, cross-session) freshness becomes your problem again. Nonces, timestamps, sequence numbers, idempotency keys — all rebuilt at the app layer.
- Pairwise. Secure channels are 2-party by construction. Groups need entirely different primitives (MLS, Signal Sender Keys, fan-out + per-member channels). Naively gluing N pairwise channels together gets you O(N) keys and zero forward secrecy guarantees as a group.
- Oracular. Composing crypto creates oracles. Padding oracles, downgrade oracles, error-message oracles, timing oracles at trust boundaries. Hume's "untrusted" said validate your inputs; crypto pipes say also don't let your error messages distinguish failure modes, which is much harder to remember.
- Non-committing. AEAD proves "this ciphertext wasn't tampered with" — not "this is the only key that decrypts it." AES-GCM and ChaCha20-Poly1305 let an attacker craft one ciphertext that verifies under multiple keys, which is the engine behind partitioning-oracle attacks (they broke Shadowsocks) and a footgun for password-based, multi-recipient, and key-rotation schemes. You need a committing AEAD; the gap is spelled out in [Cryptographic Primitives](/programming/crypto-primitives.html).
- Misusable. The APIs are foot-guns. Reuse a GCM nonce → catastrophic. Use ECB → meme. Roll your own → don't. "Misuse-resistant cryptography" exists as a research area precisely because of how much code paying the crypto tax still gets it wrong.
- Side-channeled. Even a correct implementation leaks through cache timing, branch prediction, power, EM. Constant-time code is a discipline most app developers never learn and most languages don't help with.
- Metadata-stateful. Sessions, ratchets, resumption tickets, 0-RTT early-data caches — they all carry state that has to survive crashes, sync across replicas, and not get rolled back (else replay). Your "stateless web service" has a stateful crypto layer underneath whether you want it or not.

Secure channel ≈ "I know who you are and nobody else is listening." Everything that gives that fact operational meaning — multiplexing, negotiating, routing, budgeting, naming, authorizing, scoring, recovering — lives above it.

> Hume's was "try really hard not to write a distributed system." Yours could be "try really hard not to build your own crypto layer — but also notice that even using a great off-the-shelf one (TLS, Noise, libp2p, Signal) only pays down maybe three of these dimensions. The rest are yours, forever, and the industry pretends they aren't." That framing — "the secure channel is the easy part; the productivity tax is everything around it" — would land hard.

## References <!-- omit in toc -->

1. [Pipes Kill Productivity - Tristan Hume][thume-pipes]

[thume-pipes]: https://thume.ca/2020/05/17/pipes-kill-productivity/ "Pipes Kill Productivity - Tristan Hume"
