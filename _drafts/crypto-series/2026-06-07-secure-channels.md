---
title:  "Data in Transit: Key Exchange & Secure Channels"
series: "Applied Crypto, Part 6"
series_url: "/programming/crypto-series-intro.html"
category: programming
date: 2026-06-10
---

This is the **data-in-transit** chapter: how two parties establish keys over a hostile network and use those keys to protect bytes in motion.

The whole post rests on one observation: **once two parties share a secret, an AEAD turns it into a secure channel almost trivially.** So the hard part is not record protection; it is establishing the shared secret, binding it to the right peer, and preventing replay/downgrade/misbinding during setup.

## Cube coordinates

```text
Concerns:
  secrecy, correctness, origin, freshness, partial unlinkability

Data state:
  in transit

Reasoning layers:
  threat → property → capability → policy → mechanism

Control modality:
  mostly technology, with process around roots/cert lifecycle
```

The in-transit ladder looks like:

```text
Threat:
  eavesdropping, tampering, replay, MITM, downgrade, wrong-party key binding

Property:
  confidentiality, integrity, peer authentication, freshness, forward secrecy

Capability:
  key establishment + secure channel + endpoint authentication

Policy:
  which roots, peer names, ciphers, protocol versions, 0-RTT rules, client-auth rules?

Mechanism:
  DH/KEM, HKDF, AEAD, certificates, TLS, HPKE, Noise, WireGuard, Signal
```

Any real system answers identity and data-protection questions at multiple layers:

1. **Identity layers** — TLS server cert, mTLS client cert, app-layer login, OAuth token, session cookie/JWT, workload identity.
2. **Data-protection layers** — TLS records in transit, payload encryption inside queues/caches, envelope encryption for storage, E2E encryption between users.

This article is about the transport/channel layer. Authentication, authorization, storage, and in-use protections get their own posts.

## The bootstrap: which channel do you start with?

Symmetric crypto needs both parties to *already* share a key — so the real question is what channel you use to establish it in the first place.

- A **private channel** — historically a courier with a briefcase handcuffed to his wrist, a face-to-face meeting, or a [trusted carrier pigeon][histcrypto]. If you have one, you've essentially won: send a key over it once and AEAD handles everything after. Pre-shared keys, your DEK/KEK setup, and hardcoded fingerprints are the modern versions.
- A **public channel** — the open internet, where the adversary sees the bootstrap message too. This is the hard case, and the one that *created* modern cryptography: Diffie–Hellman and public-key encryption exist precisely to establish a shared secret over a channel the attacker fully controls. Every tier below is a way to win that bootstrap over a public channel.

## A typical client-server session

A typical client-server session looks like:
1. Wire Channel security (TLS): server's identity is authenticated via certificate, ephemeral DH establishes a shared secret, HKDF derives AEAD session keys. This happens before any application bytes flow.
2. In-transit data protection: from here we have a secure channel protection the data in transit
3. User authentication: inside the TLS channel, the user (or their device) proves identity — password, passkey, OAuth token. This is app-layer.
4. (app-layer) Session establishment: server issues a short-lived token (cookie, JWT) so subsequent requests skip step 2.
5. In-use and At-rest Data protection: now you can layer authenticated encryption for data at rest (DEK/KEK), for queue payloads, for cached blobs, or for end-to-end-encrypted content between users.

Key establishment and authentication are usually fused, but conceptually separate. Raw Diffie–Hellman establishes a shared key while authenticating nobody. TLS 1.3 establishes an ephemeral shared key and authenticates the server by signing the transcript with a certificate key. WireGuard authenticates with static-key DH instead of signatures. mTLS can authenticate the client in the transport layer; OAuth or passkeys can authenticate the user later inside the already-secure channel.

A *session* and a *channel* also aren't the same thing. A **channel** is a transport-level construct that protects bytes between two endpoints — one TLS connection. A **session** is the application's notion of a continuing relationship ("you're still logged in"), carried by a cookie or token, outliving any single channel and surviving reconnects. The old [OSI session layer][osi-session] tried to standardize this and never cleanly fit TCP/IP, but the split is real: channels protect data *in transit*; sessions maintain identity over time.

## Channel Establishment

![image](/assets/secure-channels/channel-establishment-tiers.png)


Tier 1 — Symmetric only. Both parties already share a key. This is your DEK/KEK story, your in-house service-to-service encryption, anywhere the key distribution problem is already solved out-of-band. Just AEAD (AES-GCM, ChaCha20-Poly1305).

Tier 2 — Non-interactive PKE. Sender knows the recipient's public key and produces a sealed message with no handshake. Recipient doesn't need to be online. This is the email-style model. HPKE lives here. So do older constructions like libsodium's crypto_box_seal, age, and PGP.

Tier 3 — Interactive channel, fixed ciphersuite. Both parties online, simple handshake, no negotiation — the algorithms are baked into the protocol design. Noise lives here. WireGuard, Signal's underlying X3DH, the Lightning Network, WhatsApp's transport — all built on Noise patterns.

Tier 4 — Interactive channel, full negotiation. TLS. Versioned, ciphersuite-agile, extension-rich, certificate-based PKI integration. The Swiss Army knife when you need to talk to arbitrary clients on the open internet.

The tiers are not a progress axis. Rightward means more interactivity and flexibility, not "more secure." TLS needs negotiation because arbitrary clients meet arbitrary servers on the open internet. Noise and WireGuard deliberately avoid that flexibility because negotiation is attack surface: FREAK, Logjam, POODLE, BEAST, CRIME, ROBOT, and downgrade-dance variants exploited version/ciphersuite flexibility more than primitive weakness. The modern bias is: bake in the suite when you can; negotiate only when interoperability forces you.

![image](/assets/secure-channels/protocol-property-matrix.png)

#### Noise-Style Protocol Composition Recipes

![image](/assets/secure-channels/kem-composition-hpke-vs-tls12.png)

Both HPKE base mode and TLS 1.2 with an RSA cipher suite are instantiations of the same composition: static-recipient KEM → KDF → AEAD. The sender contributes fresh randomness, the recipient contributes a long-term static private key, and the KEM lets both ends up with a shared key K that seeds the symmetric key schedule. Only what fills the KEM slot differs. Forward secrecy is impossible here because `sk_R` is reused across all senders — compromising it tomorrow decrypts every HPKE message anyone has ever sent to that recipient. That's a deliberate trade for async usability, not a bug. age and libsodium sealed boxes have the same shape.



![image](/assets/secure-channels/tls13-key-exchange.png)

TLS 1.3's whole forward-secrecy story lives in those two ephemerals: both sides erase them after the handshake, so even a future compromise of `cert_priv` doesn't decrypt past sessions. The certificate key never participates in the DH — it only signs the transcript, which is exactly why this composition can't be expressed as a Noise pattern. Noise authenticates with static-key DH; TLS authenticates with signatures. Different primitive choice, different proof structure.

![image](/assets/secure-channels/wireguard-noise-ik.png)

WireGuard is the cleanest example of a Noise pattern in production. The four DHs cover every combination of {ephemeral, static} across both sides; mixing them in order into BLAKE2s gives mutual identity authentication (`ss`), forward secrecy (`ee`), and identity binding (`es`, `se`) all at once — with no signatures, no negotiation, and a ciphersuite literally baked into the protocol name. The 2-minute forced rekey is what gives the partial post-compromise security from the matrix: a stolen session state ages out within 120 seconds.

![image](/assets/secure-channels/signal-x3dh.png)

Signal's choreography is denser because it has to be async. Alice can't ECDH against a freshly-generated Bob ephemeral — Bob is offline. Instead she ECDHs against keys Bob uploaded to the server earlier, and the *combination of which DH involves which key* is what does the work: `DH1` uses Alice's identity (so Bob knows it's her), `DH2` uses Bob's identity (so Alice knows it's him), `DH3` and `DH4` inject freshness from Alice's ephemeral and Bob's one-time prekey. Mixing all four into HKDF means an attacker would have to compromise *every* key type to break the session. The output seeds the Double Ratchet, which is where the per-message forward secrecy and the round-trip-driven post-compromise security come from. PQXDH adds an ML-KEM encapsulation in parallel — same shape, hybrid KEM.

## AEAD

Once a handshake has produced session keys, the bytes themselves are protected with an AEAD (AES-GCM, ChaCha20-Poly1305). The mechanics — how an AEAD fuses a stream-cipher mode with a MAC so you can't forget the integrity half — live in the MACs & Signatures section of [Algorithms: Public Crypto Mechanisms](/programming/crypto-primitives.html).

Establishing the key is the easy, well-understood part. Everything a secure channel *doesn't* give you — naming, authorization, revocation, replay protection across sessions, group keying, storage, in-use secrecy, metadata privacy — is surveyed in the series capstone, [What Crypto Still Doesn't Give You](/programming/what-crypto-still-doesnt-give-you.html).

## Side channels

Everything above secures the *logical* channel — the bytes an attacker sees on the wire. But a cryptographically flawless implementation can still leak the key through a **side channel**: timing differences, power draw ([differential power analysis][dpa]), electromagnetic emanations, acoustic noise, or shared-microarchitecture effects like cache timing and speculative execution (Spectre/Meltdown). The secret escapes through a channel the protocol never modelled. Defenses are their own discipline — constant-time code, masking, blinding, physical shielding — and they live *below* the API you call, which is why "the math is sound" and "the deployed system doesn't leak the key" are very different claims. This really deserves its own article; the [side-channel literature][sidechannel-survey] and [NIST's physical-security testing][dpa] are good entry points.

## References <!-- omit in toc -->

1. [From KEMs to Protocols - Neil Madden][madden-kems]
2. [ECDH as a KEM - Vlinder][vlinder-ecdh-kem]
3. [Authentication - Computer Networks: A Systems Approach][sysapproach-auth]
4. [Sender-Constrained Access Tokens: mTLS vs DPoP - SecureAuth][secureauth-mtls-dpop]
5. [History of Cryptography (the "secure channel" courier) - Wikipedia][histcrypto]
6. [OSI Session Layer - Wikipedia][osi-session]
7. [Hardware-Based Side-Channel Attacks (survey) - ACM][sidechannel-survey]
8. [A Testing Methodology for Side-Channel Resistance - NIST][dpa]

[madden-kems]: https://neilmadden.blog/2021/04/08/from-kems-to-protocols/ "From KEMs to Protocols - Neil Madden"
[vlinder-ecdh-kem]: https://rlc.vlinder.ca/ecdh-kem/ "ECDH as a KEM - Vlinder"
[sysapproach-auth]: https://book.systemsapproach.org/security/authentication.html "Authentication - Computer Networks: A Systems Approach"
[secureauth-mtls-dpop]: https://docs.secureauth.com/iam/blog/sender-constrained-access-tokens-mtls-vs-dpop "Sender-Constrained Access Tokens: mTLS vs DPoP - SecureAuth"
[histcrypto]: https://en.wikipedia.org/wiki/History_of_cryptography "History of cryptography - Wikipedia"
[osi-session]: https://en.wikipedia.org/wiki/Session_layer "Session layer (OSI) - Wikipedia"
[sidechannel-survey]: https://dl.acm.org/doi/10.1145/3357613.3357627 "Hardware-based side-channel attacks (survey) - ACM"
[dpa]: https://csrc.nist.gov/csrc/media/events/physical-security-testing-workshop/documents/papers/physecpaper19.pdf "A testing methodology for side-channel resistance - NIST"
