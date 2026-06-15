---
title:  "Applied Crypto 2: Key Exchange & Secure Channels"
category: programming
date: 2026-06-14 00:04:00
---

This is the data-protection arm of the [identity / data-protection duality](/programming/crypto-series-intro.html): how two parties agree on a shared key and protect bytes in transit. (The identity arm — proving *who* the other party is — gets its own [Authentication](/programming/authentication.html) post; the two are usually fused in practice but conceptually separate.)

The whole post rests on one observation: **once two parties share a secret, an AEAD turns it into a secure channel almost trivially.** So the entire difficulty is *safely establishing that shared secret* — which is what everything below is about. (The other half of the problem, knowing the secret is shared with the *right* party, is [Authentication](/programming/authentication.html) and [Roots of Trust & Attestation](/programming/roots-of-trust-and-attestation.html).)

Any real system has to answer two orthogonal questions for every byte that moves: who is this from (identity) and who else can see it (data protection). Both questions get answered at multiple layers, and the layers compose.
1. Identity layers: TLS server cert (transport), mTLS client cert or app-layer login — password/passkey/OAuth (request), session token — cookie/JWT (subsequent requests in a session), workload identity for service-to-service.
2. Data-protection layers: TLS record layer (in transit), payload encryption inside queues/caches (in motion-but-at-rest), DEK/KEK envelope encryption (storage), E2E encryption between end users (server-as-relay).

## A typical client-server session

A typical client-server session looks like:
1. Wire Channel security (TLS): server's identity is authenticated via certificate, ephemeral DH establishes a shared secret, HKDF derives AEAD session keys. This happens before any application bytes flow.
2. In-transit data protection: from here we have a secure channel protection the data in transit
3. User authentication: inside the TLS channel, the user (or their device) proves identity — password, passkey, OAuth token. This is app-layer.
4. (app-layer) Session establishment: server issues a short-lived token (cookie, JWT) so subsequent requests skip step 2.
5. In-use and At-rest Data protection: now you can layer authenticated encryption for data at rest (DEK/KEK), for queue payloads, for cached blobs, or for end-to-end-encrypted content between users.

TODO: actually at both wire and app-layers, we should separate channel establishment from authentication. They are often combined, but don't have to be, and are conceptually separate:
> Generally, session key establishment protocols perform authentication. A notable exception is Diffie-Hellman, as described below, so the terms authentication protocol and session key establishment protocol are almost synonymous.
> https://book.systemsapproach.org/security/authentication.html

Note that mTLS can be used to authenticate the user in step 1. See https://docs.secureauth.com/iam/blog/sender-constrained-access-tokens-mtls-vs-dpop

## Channel Establishment

![image](/assets/secure-channels/channel-establishment-tiers.png)


Tier 1 — Symmetric only. Both parties already share a key. This is your DEK/KEK story, your in-house service-to-service encryption, anywhere the key distribution problem is already solved out-of-band. Just AEAD (AES-GCM, ChaCha20-Poly1305).

Tier 2 — Non-interactive PKE. Sender knows the recipient's public key and produces a sealed message with no handshake. Recipient doesn't need to be online. This is the email-style model. HPKE lives here. So do older constructions like libsodium's crypto_box_seal, age, and PGP.

Tier 3 — Interactive channel, fixed ciphersuite. Both parties online, simple handshake, no negotiation — the algorithms are baked into the protocol design. Noise lives here. WireGuard, Signal's underlying X3DH, the Lightning Network, WhatsApp's transport — all built on Noise patterns.

Tier 4 — Interactive channel, full negotiation. TLS. Versioned, ciphersuite-agile, extension-rich, certificate-based PKI integration. The Swiss Army knife when you need to talk to arbitrary clients on the open internet.

TODO: The arrow direction is the wrong message. "More interactive = more advanced" is the implicit story the 1D axis tells, and modern crypto thinking is largely the opposite. The history of TLS is the history of negotiation-driven attacks: FREAK, Logjam, POODLE, BEAST, CRIME, ROBOT, downgrade-dance variants — most of those exploit version or ciphersuite negotiation, not the underlying primitives. Cryptographic agility is now widely seen as a footgun. WireGuard's whole pitch is "we ripped out the negotiation." Trevor Perrin designed Noise so the ciphersuite is part of the protocol name (e.g. Noise_IK_25519_ChaChaPoly_BLAKE2s), never negotiated. DJB has written at length about why he considers algorithm agility harmful. So the honest reading of that axis is: rightward = more flexible at the cost of more attack surface and a harder security proof. Not better — more compatible with the open internet, which is a different thing.

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

Once a handshake has produced session keys, the bytes themselves are protected with an AEAD (AES-GCM, ChaCha20-Poly1305). The mechanics — how an AEAD fuses a stream-cipher mode with a MAC so you can't forget the integrity half — live in the MACs & Signatures section of [Cryptographic Primitives](/programming/crypto-primitives.html).

Establishing the key is the easy, well-understood part. Everything a secure channel *doesn't* give you — naming, authorization, revocation, replay protection across sessions, group keying — is surveyed in the series capstone at the end of [Roots of Trust & Attestation](/programming/roots-of-trust-and-attestation.html).

## References <!-- omit in toc -->

1. [From KEMs to Protocols - Neil Madden][madden-kems]
2. [ECDH as a KEM - Vlinder][vlinder-ecdh-kem]
3. [Authentication - Computer Networks: A Systems Approach][sysapproach-auth]
4. [Sender-Constrained Access Tokens: mTLS vs DPoP - SecureAuth][secureauth-mtls-dpop]

[madden-kems]: https://neilmadden.blog/2021/04/08/from-kems-to-protocols/ "From KEMs to Protocols - Neil Madden"
[vlinder-ecdh-kem]: https://rlc.vlinder.ca/ecdh-kem/ "ECDH as a KEM - Vlinder"
[sysapproach-auth]: https://book.systemsapproach.org/security/authentication.html "Authentication - Computer Networks: A Systems Approach"
[secureauth-mtls-dpop]: https://docs.secureauth.com/iam/blog/sender-constrained-access-tokens-mtls-vs-dpop "Sender-Constrained Access Tokens: mTLS vs DPoP - SecureAuth"
