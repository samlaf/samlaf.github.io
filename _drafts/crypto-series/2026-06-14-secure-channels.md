---
title:  "Applied Crypto 2: Key Exchange & Secure Channels"
category: programming
date: 2026-06-14 00:02:00
---

This is the data-protection arm of the [identity / data-protection duality](/programming/crypto-series-intro.html): how two parties agree on a shared key and protect bytes in transit. (The identity arm — proving *who* the other party is — gets its own [Authentication](/programming/authentication.html) post; the two are usually fused in practice but conceptually separate.)

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

## Rootless unauthorized nameless stale brittle leaky replayable pairwise oracular misusable pipes kill productivity

Analogously to https://thume.ca/2020/05/17/pipes-kill-productivity/, we can describe cryptographic pipes (secure channels) as:
- Rootless. A secure channel reduces "trust the network" to "trust a key" but never eliminates trust — somebody has to anchor the key out of band. PKI, TOFU, hardcoded fingerprints, DNSSEC, blockchain registries, key transparency logs. This is the exact same bootstrap problem Kademlia has, just shifted into crypto-space. Every system reinvents it. (This bootstrap problem is the whole subject of [Keys & Roots of Trust](/programming/keys-and-roots-of-trust.html).)
- Unauthorized. Authentication answers "who"; it doesn't answer "may they". You will write the authz layer. Every time. Capabilities (macaroons, biscuits), ACLs, role tables, OPA — all of it lives above the channel.
- Nameless. Public keys aren't names. You will build, or import, a naming layer (Zooko's triangle applies: secure / human-meaningful / decentralized — pick two). Petnames, ENS, DNS-over-something, .onion vanity, GPG WoT. All ad hoc, none portable.
- Stale. Keys leak, certs expire, devices get lost, employees quit. You need rotation, revocation, and a story for "this was Alice and now isn't." CRL/OCSP, short-lived certs (SPIFFE), key transparency, ratchets. The state machine for "current trust" is its own distributed system.
- Brittle (cryptographically). Algorithms get deprecated faster than your dependency tree updates. SHA-1, RC4, MD5, soon RSA-2048 and ECDH against a quantum adversary. Cipher agility is the "Mismatched" problem on hard mode — you can't just add a JSON field, you have to renegotiate primitives without opening a downgrade attack. (See the negotiation-as-footgun discussion under Channel Establishment above — agility is exactly the attack surface TLS keeps getting burned by.)
- Leaky. The channel encrypts content but not envelope: who talks to whom, when, how often, how much. Traffic analysis, timing, sizes, fingerprintable handshakes (JA3/JA4). Padding, cover traffic, mixnets — and each of those is its own pile of work.
- Replayable. A single channel handles ordering inside its lifetime, but the moment your message escapes the channel (queued, logged, persisted, cross-session) freshness becomes your problem again. Nonces, timestamps, sequence numbers, idempotency keys — all rebuilt at the app layer.
- Pairwise. Secure channels are 2-party by construction. Groups need entirely different primitives (MLS, Signal Sender Keys, fan-out + per-member channels). Naively gluing N pairwise channels together gets you O(N) keys and zero forward secrecy guarantees as a group.
- Oracular. Composing crypto creates oracles. Padding oracles, downgrade oracles, error-message oracles, timing oracles at trust boundaries. Hume's "untrusted" said validate your inputs; crypto pipes say also don't let your error messages distinguish failure modes, which is much harder to remember.
- Misusable. The APIs are foot-guns. Reuse a GCM nonce → catastrophic. Use ECB → meme. Roll your own → don't. "Misuse-resistant cryptography" exists as a research area precisely because of how much code paying the crypto tax still gets it wrong.
- Side-channeled. Even a correct implementation leaks through cache timing, branch prediction, power, EM. Constant-time code is a discipline most app developers never learn and most languages don't help with.
- Metadata-stateful. Sessions, ratchets, resumption tickets, 0-RTT early-data caches — they all carry state that has to survive crashes, sync across replicas, and not get rolled back (else replay). Your "stateless web service" has a stateful crypto layer underneath whether you want it or not.

Secure channel ≈ "I know who you are and nobody else is listening." Everything that gives that fact operational meaning — multiplexing, negotiating, routing, budgeting, naming, authorizing, scoring, recovering — lives above it.

> Hume's was "try really hard not to write a distributed system." Yours could be "try really hard not to build your own crypto layer — but also notice that even using a great off-the-shelf one (TLS, Noise, libp2p, Signal) only pays down maybe three of these dimensions. The rest are yours, forever, and the industry pretends they aren't." That framing — "the secure channel is the easy part; the productivity tax is everything around it" — would land hard.

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

Arkko's draft argues that the stipulation was always a stipulation, not a theorem, and it's no longer tenable. TLS, QUIC, and HTTPS have largely defeated the channel attacker. Meanwhile, the threat has moved fully *inside* the authenticated session — to counterparties who are correctly identified, correctly authenticated, and correctly behaving cryptographically, but who are malicious, coerced, or commercially misaligned with the user. PKI tells you Google is really Google; it doesn't tell you Google won't sell your data. The proposed rewrite of RFC 3552's core assumption is the formal acknowledgment: instead of "end-systems have not been compromised," the new baseline is "the *implementing* end-system has not been compromised, but the other parties may be."

### Coming full circle

We're back to a Lowe-style world where the dangerous actor is a legitimate participant — except now at the scale of cloud providers, BFT leaders, and centralized infrastructure, rather than a single Mallory in a three-message protocol. The cryptographic identity is impeccable, the channel is encrypted, the signatures all verify, and the threat is still real. Forty years of threat-model evolution have brought the field back to the realization Lowe forced on it in 1995: the protocol's role structure, not the channel, is where the adversary lives.

## References

https://neilmadden.blog/2021/04/08/from-kems-to-protocols/
https://rlc.vlinder.ca/ecdh-kem/
https://book.systemsapproach.org/security/authentication.html
https://docs.secureauth.com/iam/blog/sender-constrained-access-tokens-mtls-vs-dpop
https://thume.ca/2020/05/17/pipes-kill-productivity/
