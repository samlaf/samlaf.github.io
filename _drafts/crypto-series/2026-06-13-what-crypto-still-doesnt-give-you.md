---
title:  "What Crypto Still Doesn't Give You"
series: "Applied Crypto, Capstone"
series_url: "/programming/crypto-series-intro.html"
category: programming
date: 2026-06-13
---

Crypto is powerful because it lets data partially protect itself. A ciphertext can sit in a hostile object store; a signature can be verified by a stranger; a secure channel can cross an untrusted network; an attestation quote can carry evidence about code running on someone else's machine.

But the security cube is larger than crypto.

```text
For each property/concern,
in each data state,
against each threat,
choose a function/capability,
define the policy,
enforce it with mechanisms,
wrapped by technical/process/human controls.
```

Crypto is one mechanism family in that sentence. It mostly serves confidentiality, integrity, origin, attribution, and some privacy properties. It does not eliminate roots, naming, authorization, revocation, availability, governance, or humans.

This is the negative-space post.

## Cube coordinates

```text
Concerns:
  all

Data states:
  at rest | in transit | in use

Reasoning layers:
  the gaps around crypto mechanisms

Control modality:
  technology + process + human
```

## Rootless

A secure channel reduces "trust the network" to "trust a key." It does not eliminate trust.

Somebody has to decide which key is Bob's:

- Web PKI root store
- TOFU cache
- pinned fingerprint
- DNSSEC root
- blockchain genesis hash
- package signing key
- hardware vendor root
- attestation root
- key-transparency log

The root is configured out of band. Crypto authenticates chains; it does not choose the first anchor.

## Unauthorized

Authentication answers **who**. Authorization answers **may they**.

TLS can prove the peer controls a certificate. A passkey can prove the user holds a device-bound private key. A signature can prove a release key signed an artifact. None of those facts decides whether this request may delete a record, unwrap a DEK, mint a token, or release a secret.

You still need policy:

```text
subject may perform action on object under context
```

And you still need an enforcement mechanism: KMS, IAM, database permissions, API gateway, OS kernel, smart contract, verifier policy, or application code.

## Nameless

Public keys are not names.

A raw key can be self-authenticating, but it is not human-meaningful. A DNS name is human-meaningful, but it needs a naming authority. A decentralized name avoids a central CA, but then you inherit the governance and fork-choice problem of the naming system.

Zooko's triangle — secure, human-meaningful, decentralized; pick two — keeps reappearing:

- Web PKI: human-meaningful + secure-ish, not decentralized.
- Tor `.onion`: secure + decentralized, not human-meaningful.
- Web of Trust: decentralized + human-meaningful in aspiration, weak at scale.
- ENS/blockchain naming: tries to buy all three with a ledger, but the client still ships a genesis/root choice.

Crypto binds keys to statements. Naming decides which statements humans can use.

## Stale

Keys leak. Certs expire. Employees leave. Devices get lost. Packages are yanked. TCB versions become vulnerable. Measurements that were acceptable yesterday may be forbidden today.

Crypto proofs are often timeless unless you add time:

- certificate validity windows
- OCSP / CRLs / short-lived certs
- token expiry
- key rotation
- transparency logs
- revocation lists
- ratchets
- firmware/TCB revocation
- verifier policy updates

Revocation is a distributed-systems problem wearing a cryptographic hat.

## Killable

Crypto can hurt availability.

- Expensive handshakes create DoS surface.
- Lost keys are permanent denial of access.
- Ransomware is confidentiality turned against the owner.
- KMS outages can make encrypted data unavailable.
- Certificate expiry can take down production.
- Revocation mistakes can brick fleets.

Availability mostly lives in redundancy, rate limits, capacity, isolation, admission control, backup/restore, and operational discipline — not in ciphers.

## Brittle

Algorithms age. Defaults rot. Dependencies lag.

MD5, SHA-1, RC4, DES, export RSA, static DH, CBC padding constructions — all were acceptable until they weren't. RSA-2048 and today's elliptic-curve assumptions face the quantum timer. Even when the primitive remains sound, composition mistakes create downgrade, oracle, and misuse attacks.

Cryptographic agility is necessary over decades but dangerous in protocols. Negotiation creates attack surface; no-negotiation designs create migration pain. There is no free axis.

## Leaky

Encryption hides content. It does not automatically hide the envelope:

- who talks to whom
- when
- how often
- how much
- packet sizes
- timing
- handshake fingerprints
- routing metadata
- access patterns

Padding, cover traffic, mixnets, onion routing, PIR, ORAM, batching, and local processing all attack parts of this problem. Each has its own cost. Content confidentiality is not traffic-analysis resistance.

## Replayable

A secure channel orders bytes inside one connection. The moment a message escapes the channel — queued, logged, persisted, retried, cached, restored from backup — freshness becomes your problem again.

You need some combination of:

- nonces
- sequence numbers
- timestamps
- idempotency keys
- replay caches
- signed checkpoints
- monotonic counters
- application-level state machines

AEAD proves a ciphertext was produced under the key. It does not prove this is the first, latest, or intended time it was used.

## Pairwise

Secure channels are naturally two-party. Groups are a different problem.

Naively building a group out of pairwise channels gives you:

- O(N) or O(N²) key state
- unclear membership semantics
- hard revocation
- weak group forward secrecy
- awkward sender authentication
- state-synchronization bugs

MLS, Signal Sender Keys, threshold crypto, group ratchets, and broadcast encryption exist because pairwise secure channels do not scale into group security by themselves.

## Oracular

Crypto systems become oracles at their boundaries.

- padding oracles
- decryption oracles
- partitioning oracles
- timing oracles
- downgrade oracles
- error-message oracles
- login/token introspection oracles
- attestation-verifier oracles

The primitive may be correct, while the system leaks one bit per query until the secret is gone. "Do not reveal why verification failed" is easy to say and hard to maintain across logs, retries, metrics, and UX.

## Non-committing

AEAD proves "this ciphertext wasn't tampered with under this key." It does not necessarily prove "this ciphertext belongs to exactly one key."

AES-GCM and ChaCha20-Poly1305 are non-committing: an attacker can sometimes craft one ciphertext that decrypts and verifies under multiple different keys. That is the engine behind partitioning-oracle attacks, and it matters for password-based encryption, multi-recipient schemes, key rotation, JWE, age-like formats, and any design where "which key worked?" leaks information.

If your protocol needs key commitment, choose a committing AEAD or add an explicit commitment.

## Misusable

Crypto APIs are foot-guns.

- reuse a GCM nonce → catastrophic
- use ECB → pattern leak
- decrypt before verifying tag → RUP bug
- compare MACs non-constant-time → timing leak
- sign the wrong transcript → identity misbinding
- forget associated data → context swap
- accept `alg=none` → self-own
- roll your own protocol → probably broken

Misuse-resistant cryptography exists because correct primitive use is not the same as correct system design.

## Side-channeled

A cryptographic implementation can be logically perfect and physically leaky.

Secrets escape through:

- timing
- cache state
- branch prediction
- speculative execution
- power draw
- electromagnetic emanations
- acoustic signals
- memory deduplication
- page faults

Constant-time code, masking, blinding, hardware isolation, and side-channel testing live below the API. "The math is sound" and "the deployed system does not leak the key" are different claims.

## Metadata-stateful

Modern crypto systems carry state even when the application wants to be stateless:

- session tickets
- replay caches
- ratchet state
- nonce counters
- key epochs
- resumption PSKs
- transparency log checkpoints
- attestation nonces
- 0-RTT early-data state
- certificate/key rotation state

That state has to survive crashes, replicate safely, avoid rollback, and not fork across regions. Crypto often smuggles a distributed system into your stateless service.

## Human-process-governance gaps

McCumber's third axis is the reminder: technology controls are wrapped by process and humans.

Crypto does not decide:

- who can approve root-store changes
- who reviews IAM grants
- who holds break-glass authority
- how recovery ceremonies work
- how often access is recertified
- whether engineers understand key destruction
- whether admins rubber-stamp prompts
- whether incentives reward bypassing controls

A perfect mechanism enforcing a bad policy through a broken process is still a broken system.

## The final picture

A secure channel roughly buys:

```text
I know which key I am talking to,
and outsiders cannot read or tamper with these bytes in transit.
```

That is valuable, but narrow. It says little about stored data, running code, authorization, naming, revocation, metadata, recovery, governance, or the authenticated counterparty's honesty.

So the series ends where it began:

```text
For each property/concern,
in each data state,
against each threat,
choose a function/capability,
define the policy,
enforce it with mechanisms,
wrapped by technical/process/human controls.
```

Crypto is one of those mechanism families. Use it. Do not ask it to be the whole cube.

## References <!-- omit in toc -->

1. [Pipes Kill Productivity - Tristan Hume][thume-pipes]
2. [Partitioning Oracle Attacks - Len, Grubbs & Ristenpart][partitioning-oracle]
3. [How to Abuse and Fix Authenticated Encryption Without Key Commitment - Albertini et al.][key-commitment]
4. [Authenticated Encryption - Wikipedia][ae-wiki]
5. [Hardware-Based Side-Channel Attacks (survey) - ACM][sidechannel-survey]

[thume-pipes]: https://thume.ca/2020/05/17/pipes-kill-productivity/ "Pipes Kill Productivity - Tristan Hume"
[partitioning-oracle]: https://www.usenix.org/conference/usenixsecurity21/presentation/len "Partitioning Oracle Attacks - Len, Grubbs & Ristenpart"
[key-commitment]: https://www.usenix.org/conference/usenixsecurity22/presentation/albertini "How to Abuse and Fix Authenticated Encryption Without Key Commitment - Albertini et al."
[ae-wiki]: https://en.wikipedia.org/wiki/Authenticated_encryption "Authenticated encryption - Wikipedia"
[sidechannel-survey]: https://dl.acm.org/doi/10.1145/3357613.3357627 "Hardware-based side-channel attacks (survey) - ACM"
