---
title:  "Applied Crypto: A Field Map"
category: programming
date: 2026-06-14 00:00:00
---

This is the intro to a short series on applied cryptography — not the math, but the engineering: which primitives exist, how they compose into channels and authentication, and where all the trust ultimately bottoms out.

## The duality that runs through everything

Every byte that moves over a network forces two independent questions:

1. **Who is this from?** — *identity / authentication.* Certs, passkeys, signatures, tokens.
2. **Who else can see or change it?** — *data protection.* Confidentiality + integrity: TLS records, AEAD, envelope encryption, end-to-end encryption.

They're **orthogonal**. You can have one without the other: raw Diffie–Hellman gives you a confidential channel with no idea who's on the other end; a bare signature proves origin while hiding nothing. Real systems answer both, at several layers that stack on top of each other — and almost every topic in this series is one half of that duality, pointed at one layer.

(There's a subtlety the series keeps returning to: key establishment and authentication are *usually* fused but are conceptually separable — Diffie–Hellman is the notable exception that establishes a shared key while authenticating nobody.)

## Three pillars

**Mechanism — the atoms.** The cryptographic primitives everything else is built from, and where their randomness comes from.

**Composition — the two arms of the duality.** How you establish a shared key and protect data in transit (the data-protection arm), and how a party proves who they are (the identity arm).

**Trust anchoring — where it bottoms out.** A secure channel reduces "trust the network" to "trust a key" — but never to *nothing*. Something has to anchor that key out of band: PKI roots baked into your browser, a key fused into hardware, a measurement signed by a manufacturer. This pillar is about that anchor, and about *proving* a key really lives behind one (attestation).

## The articles

1. **[Cryptographic Primitives](/programming/crypto-primitives.html)** — PRFs vs PRPs, block vs stream ciphers, AEAD, MACs and signatures, and the entropy stack that seeds them all. The recurring punchline: one primitive (a PRF) underlies encryption, authentication, key derivation, and randomness alike.
2. **[Key Exchange & Secure Channels](/programming/secure-channels.html)** — the four tiers of channel establishment, from a shared symmetric key up to fully-negotiated TLS, with HPKE / TLS 1.3 / WireGuard / Signal as worked examples — and a closing look at everything a secure channel *doesn't* give you.
3. **[Authentication](/programming/authentication.html)** — the 50-year arc from plaintext passwords to passkeys, read as one long story of moving the root of trust out of the server's hands.
4. **[Keys & Roots of Trust](/programming/keys-and-roots-of-trust.html)** — where secret material actually lives (device vs server, Secure Enclave vs HSM), envelope encryption, and the out-of-band anchors that every chain of trust terminates in.
5. **[Attestation Models](/programming/attestation-models.html)** — the hardware mechanism that *proves* a key lives behind a real root of trust: TPMs, confidential VMs, vTPMs, and cloud attestation, all read through Red Hat's REMITS framework.

## A theme to watch

Three of these posts tell the *same story from different angles*: the trust anchor keeps moving. Authentication moves it from the server to the client. The threat-model history (closing out the channels post) moves the adversary from the wire to the authenticated counterparty. And the trust pillar shows it all bottoming out in out-of-band, hardware-rooted anchors. Read in order, the series descends from the primitives at the top to the silicon at the bottom — and finds the same shape at every layer.
