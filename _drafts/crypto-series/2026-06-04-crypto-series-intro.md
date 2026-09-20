---
title:  "Applied Crypto"
category: programming
date: 2026-06-04
---

This is the intro to a short series on applied cryptography — not the math, but the engineering: which primitives exist, how they compose into channels, how a party proves it holds a key, and what the key itself is made of and where it lives.

It is the first of three series. This one ends holding a key. The [identity series](/programming/identity-series-intro.html) asks whose key it is. The [authorization series](/programming/authorization-series-intro.html) asks what the holder may do.

## The duality that runs through everything

Every byte that moves over a network forces two independent questions:

1. **Who is this from?** — Certs, passkeys, signatures, tokens all claim to answer it.
2. **Who else can see or change it?** — *data protection.* Confidentiality + integrity: TLS records, AEAD, envelope encryption, end-to-end encryption.

They're **orthogonal**. You can have one without the other: raw Diffie–Hellman gives you a confidential channel with no idea who's on the other end; a bare signature proves origin while hiding nothing. Real systems answer both, at several layers that stack on top of each other.

But be precise about what cryptography can say to the first question, because it is less than the word "authentication" suggests. Every cryptographic guarantee is relative to a *key*. A verified signature means "produced by the holder of this private key." A completed handshake means "the far end holds the key for the certificate it sent." A PAKE means "the far end knows the password." None of that is a name. Cryptography can prove that a party *holds a key*; turning that key into `example.com` or Alice is a separate act — a binding, written by someone you chose to believe — and it is not cryptography. That act is the [identity series](/programming/identity-series-intro.html). This series stops at the key.

So the duality, stated in this series' own terms, is:

- **(a) Is the key doing its job?** Confidentiality, integrity, freshness — all relative to a key. Primitives, channels, and the key material itself.
- **(b) Does the far end hold the key?** Proof of possession, live, over the wire. Passwords, PAKEs, passkeys, handshake signatures.

Here's the way to *feel* the split: **once two parties share a secret, an AEAD turns it into a secure channel almost for free.** So nearly all the real difficulty reduces to *getting that shared secret in the first place* — establishing it safely over a hostile network, and proving to each other that you each hold what you claim. Whether the party who holds it is the *right* party is the question this series hands off.

(There's a subtlety the series keeps returning to: key establishment and proof of possession are *usually* fused but are conceptually separable — Diffie–Hellman is the notable exception that establishes a shared key while proving nothing about who holds it.)

## The spine: follow the key

Every post in the series is about the key at a different point in its life.

**Mechanism — the atoms.** The cryptographic primitives everything else is built from, and the punchline that one primitive (a PRF) underlies encryption, MACs, key derivation, and randomness alike.

**Establishing a shared key — channels.** Key exchange turns "we both hold a secret" into a live secure channel, from a pre-shared key up to fully-negotiated TLS.

**Proving you hold a key.** How a party demonstrates possession of a secret without giving it away: the fifty-year migration from passwords the server sees, to hashes, to PAKEs, to signatures from a key that never leaves the device. Read as a story about *custody*: what the prover holds, what the verifier stores, and what crosses the wire.

**The key itself.** A key is real, physical secret material: where its randomness comes from, where it lives (device vs server, Secure Enclave vs HSM), and how it is wrapped.

**What the channel doesn't give you.** The capstone. A secure channel is the easy part, and the inventory of what it leaves undone is the trailer for the next two series.

## The articles

- **[Prologue: The Changing Internet Threat Model](/programming/threat-model.html)** — the motivation: forty years of the assumed adversary migrating from the wire, to identity binding, to the authenticated counterparty itself. The three layers are the three series, and this is the prologue to all of them.
- **[Part 1: Cryptographic Primitives](/programming/crypto-primitives.html)** — PRFs vs PRPs, block vs stream ciphers, AEAD, and MACs and signatures. The recurring punchline: one primitive (a PRF) underlies encryption, authentication, key derivation, and randomness alike.
- **[Part 2: Key Exchange & Secure Channels](/programming/secure-channels.html)** — establishing the shared secret: the four tiers of channel establishment, from a shared symmetric key up to fully-negotiated TLS, with HPKE / TLS 1.3 / WireGuard / Signal as worked examples.
- **[Part 3: Proving You Hold a Key](/programming/authentication.html)** — the 50-year arc from plaintext passwords to passkeys, read as one long story of moving the secret out of the server's hands: what the prover holds, what the verifier stores, and what crosses the wire.
- **[Part 4: Keys](/programming/keys.html)** — the life of a key: the entropy stack that seeds it, where it lives (device vs server, Secure Enclave vs HSM), and envelope encryption.
- **[Part 5: What a Secure Channel Doesn't Give You](/programming/secure-channel-capstone.html)** — the capstone: thirteen things a perfect channel still leaves for you, two of which — whose key is it, and what may they do — are the next two series.
