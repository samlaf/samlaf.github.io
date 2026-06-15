---
title:  "Applied Crypto"
category: programming
date: 2026-06-04
---

This is the intro to a short series on applied cryptography — not the math, but the engineering: which primitives exist, how they compose into channels and authentication, and where all the trust ultimately bottoms out.

## The duality that runs through everything

Every byte that moves over a network forces two independent questions:

1. **Who is this from?** — *identity / authentication.* Certs, passkeys, signatures, tokens.
2. **Who else can see or change it?** — *data protection.* Confidentiality + integrity: TLS records, AEAD, envelope encryption, end-to-end encryption.

They're **orthogonal**. You can have one without the other: raw Diffie–Hellman gives you a confidential channel with no idea who's on the other end; a bare signature proves origin while hiding nothing. Real systems answer both, at several layers that stack on top of each other — and almost every topic in this series is one half of that duality, pointed at one layer.

Here's the way to *feel* the split: **once two parties share a secret, an AEAD turns it into a secure channel almost for free.** So nearly all the real difficulty reduces to the two sub-problems of getting that shared secret in the first place — **(a) establishing it safely**, and **(b) knowing it's shared with the *right* party.** (a) is the data-protection arm (key exchange, plus the key material itself); (b) is the identity arm (authentication, plus the roots of trust that make any identity believable).

(There's a subtlety the series keeps returning to: key establishment and authentication are *usually* fused but are conceptually separable — Diffie–Hellman is the notable exception that establishes a shared key while authenticating nobody.)

## Three pillars

**Mechanism — the atoms.** The cryptographic primitives everything else is built from.

**Establishing the shared secret — data protection.** Key exchange turns "we both hold a secret" into a live secure channel; and the secret itself, a real key, has a lifecycle of generation, custody, and protection.

**Knowing it's the right party — identity.** A shared secret is worthless if it's shared with an impostor. This arm is authentication (how a party proves itself) and the roots of trust + attestation that make any identity claim believable — where, ultimately, all trust bottoms out.

## The articles

1. **[The Changing Internet Threat Model](/programming/threat-model.html)** *(prologue)* — the motivation: forty years of the assumed adversary migrating from the wire, to identity binding, to the authenticated counterparty itself. The lens for everything that follows.
2. **[Cryptographic Primitives](/programming/crypto-primitives.html)** — PRFs vs PRPs, block vs stream ciphers, AEAD, and MACs and signatures. The recurring punchline: one primitive (a PRF) underlies encryption, authentication, key derivation, and randomness alike.
3. **[Key Exchange & Secure Channels](/programming/secure-channels.html)** — establishing the shared secret: the four tiers of channel establishment, from a shared symmetric key up to fully-negotiated TLS, with HPKE / TLS 1.3 / WireGuard / Signal as worked examples.
4. **[Authentication](/programming/authentication.html)** — knowing it's the right party: the 50-year arc from plaintext passwords to passkeys (and OAuth's parallel 1.0 → 2.0 → GNAP arc), read as one long story of moving the root of trust out of the server's hands.
5. **[Keys](/programming/keys.html)** — the life of a key: the entropy stack that seeds it, where it lives (device vs server, Secure Enclave vs HSM), and envelope encryption.
6. **[Roots of Trust & Attestation](/programming/roots-of-trust-and-attestation.html)** — where every chain of trust terminates: out-of-band anchors, then the hardware mechanism that *proves* a key lives behind one (TPMs, confidential VMs, vTPMs, cloud attestation, via Red Hat's REMITS lens). Ends with a series capstone — everything a secure channel still *doesn't* give you.
