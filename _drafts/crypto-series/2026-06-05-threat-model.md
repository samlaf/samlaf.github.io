---
title:  "Threat Models Across Data States"
series: "Applied Crypto, Part 1"
series_url: "/programming/crypto-series-intro.html"
category: programming
date: 2026-06-05
---

All the machinery in this series — keys, algorithms, authorization, channels, authentication, storage encryption, and attestation — exists to defend against an adversary. The interesting question is not just *how strong* the adversary is, but **where the adversary lives**.

McCumber's data-state axis gives the clean split:

```text
data in transit  → the network and protocol boundary
data at rest     → disks, databases, object stores, backups
data in use      → processes, CPUs, OSes, hypervisors, enclaves, agents
```

The old version of this post was mostly the internet threat model: the adversary moved from the wire, to identity binding, to the authenticated counterparty itself. That is still the central story for **data in transit**, but it is only one face of the cube. Stored data and running computation have their own threat models.

## Cube coordinates

```text
Concerns:
  secrecy, correctness, origin, attribution, uptime, unlinkability

Data states:
  at rest | in transit | in use

Reasoning layer:
  threat

Control modality:
  technology threats + process/human threats
```

## Adversary vocabulary

A threat model first names the adversary's powers.

Along behavior:

- **Passive** — observes only.
- **Active** — drops, modifies, injects, reorders, replays.
- **Crash / omission / Byzantine** — distributed-systems vocabulary for nodes that halt, omit messages, or behave arbitrarily.

Along resources:

- **Computationally bounded** — cannot break assumed-hard problems.
- **Quantum** — breaks RSA/ECC assumptions via Shor, but not symmetric crypto at equivalent strength or post-quantum schemes.
- **Unbounded** — information-theoretic adversary.

Along targeting:

- **Static** — targets chosen in advance.
- **Adaptive** — corrupts new targets as it learns.
- **Mobile** — corruptions come and go over time.

And along location:

- **Wire attacker** — controls the network.
- **Storage attacker** — gets copies of stored bytes or controls storage service behavior.
- **Execution attacker** — controls or observes the environment where plaintext is processed.
- **Participant attacker** — is an authenticated party behaving maliciously.

Dolev–Yao is one coordinate in that space: an active attacker who owns the network while endpoints are honest. Modern systems often need the stronger stance: assume a strong, adaptive adversary at *every* boundary, including authenticated participants.

![Parallel-coordinates plot of the adversary model: four orthogonal axes — behaviour (passive→crash→omission→Byzantine), compute (bounded→quantum→unbounded), targeting (static→adaptive), and mobility (non-mobile→mobile) — each applying to the wire or a corrupted node, with a passive eavesdropper, Dolev–Yao, a quantum harvest-now-decrypt-later attacker, and a mobile Byzantine node drawn as polylines](/assets/threat-model/adversary-axes.svg)

## 1 · Data in transit: the internet threat model

Data in transit is the classic crypto story. Over forty years, the assumed internet adversary migrated through three layers:

1. **On the wire** — the network between two endpoints.
2. **In the identity binding** — *is this key really Bob's?*
3. **Inside the authenticated session** — Bob is provably Bob, and Bob is hostile.

For each, separate three things that often happened decades apart: the **threat**, the **theory** that modeled it, and the **implementation** that finally shipped.

![Timeline of internet threat models across three layers — the wire, identity binding, and inside the session — from 1976 to today, showing each threat modelled years before it was defeated](/assets/threat-model/threat-model-timeline.svg)

### 1.1 · On the wire

**Threat.** A passive eavesdropper reads your traffic; an active attacker drops, modifies, injects, reorders, and replays it.

**Theory.** [Dolev and Yao][dolev-yao] (1983) formalized this adversary — full network control — and [RFC 3552][rfc3552] (2003) made it the IETF default: assume endpoints are honest and the wire is hostile.

**Implementation.** SSL (1995) → TLS 1.0 (1999) → TLS 1.2 with AEAD (2008) → TLS 1.3 (2018). The model was clear long before the deployed protocol was clean.

A channel has two phases with different threat surfaces:

- **Setup is the battleground.** The handshake negotiates versions, ciphersuites, identities, keys, and transcript binding. Downgrade attacks like [FREAK and Logjam][logjam] exploit negotiation rather than breaking primitives. This is why modern fixed-suite designs like Noise and WireGuard intentionally minimize agility.
- **Usage is mostly solved.** Once a fresh session key exists and traffic is protected by an AEAD, the steady-state wire attacker has little left to do. The historical record-layer attacks — BEAST, CRIME, Lucky 13, POODLE — were attacks on pre-AEAD modes, compression, or downgradeable legacy.

So for in-transit content, the modern answer is clear:

```text
key establishment + endpoint authentication + AEAD records
```

### 1.2 · In the identity binding

**Threat.** A secure channel to the wrong party. The attacker breaks no cryptography; he hands you his own public key and you faithfully encrypt everything to him.

**Theory.** [Diffie–Hellman][dh] (1976) gave public keys, but a key is not a name. Binding a key to an identity — proving this key really is `example.com`'s — is separate from key exchange.

**Implementation.** PKI — X.509, certificate authorities, the Web PKI — turned identity binding into infrastructure. Its failures are about trusting the wrong issuer: Comodo and DigiNotar (2011) minted valid certificates for domains they had no business signing, which drove [Certificate Transparency][ct].

PKI solved impersonation, not honesty. It says this is really `example.com`; it does not say `example.com` is safe, authorized, uncompromised, or benevolent.

### 1.3 · Inside the authenticated session

**Threat.** Bob is provably Bob — every signature verifies, the channel is encrypted — and Bob is hostile. The dangerous actor is a legitimate participant.

**Theory.** [Lowe's attack][ns-lowe] on Needham–Schroeder (1995) showed that perfect crypto and perfect key binding can still leave a protocol broken. A legitimate participant can exploit role structure and relay messages to cause another party to misinterpret who said what.

[Arkko's draft][arkko] (2019) reopened the point for the internet architecture: the baseline should no longer be "endpoints are honest." The implementing endpoint may be uncompromised, but the other participants, delegates, intermediaries, or authenticated counterparties may be adversarial.

**Implementation frontier.** OAuth already admits the channel is a triangle: a browser-mediated front channel and a server-to-server back channel face different attackers. CDNs terminate TLS before the origin. Service meshes authenticate workloads that may still be buggy or hostile. AI agents act with valid credentials under prompt-injected instructions. The threat has moved inside the set of authenticated parties.

This is the bridge from secure channels to authorization, policy, and attestation: authentication proves which principal acted; it does not prove the action should be trusted.

## 2 · Data at rest: the storage threat model

Data at rest is not a weaker version of data in transit. The adversary gets time, copies, backups, and operational mistakes.

### 2.1 · Stolen or copied storage

**Threat.** An attacker obtains a disk, laptop, phone, EBS snapshot, database dump, S3 bucket, backup archive, VM image, or log bundle.

**Property.** Confidentiality of stored content.

**Mechanisms.** Full-disk encryption, object/field encryption, envelope encryption, KMS/HSM-held keys, client-side encryption.

The crucial difference from transit: stored ciphertext may be attacked indefinitely. If the encryption scheme is password-derived, the adversary can run an offline guessing attack. If the key later leaks, old data may fall. If a quantum adversary is plausible, "harvest now, decrypt later" applies to any public-key wrapping vulnerable to future quantum breaks.

### 2.2 · Malicious or curious storage operator

**Threat.** The storage layer faithfully stores bytes but should not see plaintext — a cloud admin, database operator, backup provider, or compromised object-store credential.

**Property.** Confidentiality from the storage operator; integrity against modification or swap.

**Mechanisms.** Client-side encryption, AEAD associated data, signatures, Merkle trees, transparency logs, KMS separation of duties.

This is where "encryption at rest" can be misleading. Server-side encryption by the same cloud account protects against lost disks and some infrastructure failures; it may not protect against the service that also holds the keys. Client-side encryption moves the trust boundary upward, but also moves key management burden to the client.

### 2.3 · Rollback and stale state

**Threat.** An attacker restores an old but valid encrypted state: last month's database, a previous authorization policy, an old package index, a stale keyset.

**Property.** Freshness / current integrity.

**Mechanisms.** Version numbers, monotonic counters, signed checkpoints, append-only logs, quorum replication, transparency logs, trusted timestamps.

AEAD proves the ciphertext was produced under the key. It does not prove this is the latest ciphertext. Storage needs its own replay defense.

### 2.4 · Ransomware and lost keys

**Threat.** The owner loses useful access: keys are destroyed, files are re-encrypted by malware, backups are deleted, or KMS becomes unavailable.

**Property.** Availability and utility.

**Mechanisms.** Backups, recovery drills, immutable retention, offline copies, key recovery/escrow policy, separation of duties.

Crypto is double-edged here. It protects confidentiality, but a lost key is perfect denial of access. Ransomware is just unauthorized encryption plus extortion. No cipher solves the recovery policy; the answer is operational.

## 3 · Data in use: the processing threat model

Data in use is the hardest state because plaintext must exist somewhere. If code can compute on the data, some execution environment can see it.

### 3.1 · Malicious process or compromised OS

**Threat.** Another process reads memory, malware runs as the user, the OS is compromised, or a dependency executes with legitimate privileges.

**Property.** Confidentiality and integrity of runtime state.

**Mechanisms.** Process isolation, MMU/page tables, language sandboxes, seccomp/eBPF, containers, capability systems, least privilege, memory-safe languages, constant-time implementations.

This is the classic access-control/reference-monitor route. The data is plaintext while used; protection comes from mediation and isolation.

### 3.2 · Hostile hypervisor or cloud operator

**Threat.** The infrastructure running the workload is not fully trusted: malicious host OS, hypervisor, cloud admin, or compromised management plane.

**Property.** Confidentiality/integrity of memory and code identity despite hostile infrastructure.

**Mechanisms.** Confidential VMs, TEEs, AMD SEV-SNP, Intel TDX/SGX, TPMs/vTPMs, measured boot, remote attestation, secret release based on measurements.

This is where [Data in Use: Isolation, Measurement, and Attestation](/programming/data-in-use-isolation-measurement-and-attestation.html) lives. Attestation does not say "this code is good"; it says "this key is held by code with measurement M under root R." A verifier policy must still decide whether M and R are acceptable.

### 3.3 · Side channels

**Threat.** The protocol is logically secure, but the implementation leaks through timing, cache state, power, EM, branch prediction, speculative execution, page faults, or shared hardware.

**Property.** Confidentiality of secrets during computation.

**Mechanisms.** Constant-time code, masking, blinding, cache partitioning, hardware isolation, side-channel testing.

Side channels are data-in-use attacks against the physical or microarchitectural execution channel the protocol did not model.

### 3.4 · Supply chain and authenticated bad code

**Threat.** The code doing the computation is itself malicious or compromised: backdoored dependency, malicious maintainer, poisoned package, compromised CI, prompt-injected agent with valid credentials.

**Property.** Integrity of computation and intent.

**Mechanisms.** Code signing, reproducible builds, package transparency, dependency pinning, sandboxing, least privilege, review, provenance, SLSA-style build attestations.

This is the in-use version of the authenticated-counterparty frontier. The actor may have a valid signature, token, maintainer account, or workload identity. The protocol's role structure and policy decide whether that authenticated actor can cause harm.

## 4 · Threats to the controls themselves

The controls are also attack surfaces.

| Control | Threat |
|---|---|
| RNG / entropy | weak seed, VM clone, backdoored CSPRNG like Dual_EC |
| Key storage | leaked `.env`, memory disclosure, HSM misuse, bad backup |
| Public-key binding | bad CA, stale root, key transparency failure |
| Authorization policy | overbroad IAM, confused deputy, bad scope, stale grant |
| KMS | unavailable, misconfigured, admin bypass, audit disabled |
| Attestation | compromised vendor root, stale TCB, misleading measurement, verifier accepts too much |
| Human process | rubber-stamped approval, phished admin, bad incident response |

This is why the series separates mechanisms from policy and roots. A primitive can be sound while the key is stolen, the root is wrong, or the policy says yes to the wrong subject.

## Where the frontier is now

The story is not that one threat replaced another. It is that each solved layer exposes the next boundary:

```text
wire attacker          → secure channels
wrong public key       → PKI / authentication
stolen stored bytes    → encryption / KMS
plaintext during use   → isolation / attestation
valid but hostile actor → authorization / protocol design / least privilege
lost or locked data    → recovery / availability / governance
```

The frontier today is the authenticated-but-untrustworthy participant: a cloud host, package maintainer, OAuth client, service workload, AI agent, or enclave measurement that verifies correctly but may still do the wrong thing.

That's the lens for the rest of the series. Each article occupies a different part of the cube: keys and algorithms give the mechanism substrate; policy decides who may use them; authentication binds keys to identities; channels protect transit; storage protects rest; attestation tries to say something meaningful about use.

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
[aur-malware]: https://ioctl.fail/preliminary-analysis-of-aur-malware/ "Preliminary analysis of AUR Malware - ioctl.fail"
[dual-ec]: https://en.wikipedia.org/wiki/Dual_EC_DRBG "Dual_EC_DRBG (the backdoored RNG) - Wikipedia"
[adversary-models]: https://decentralizedthoughts.github.io/2019-06-07-modeling-the-adversary/ "Modeling the Adversary - Decentralized Thoughts"
[adversary-crypto]: https://en.wikipedia.org/wiki/Adversary_(cryptography) "Adversary - Wikipedia"
[des]: https://en.wikipedia.org/wiki/Data_Encryption_Standard "Data Encryption Standard - Wikipedia"
[aes]: https://en.wikipedia.org/wiki/Advanced_Encryption_Standard "Advanced Encryption Standard - Wikipedia"
[morris]: https://en.wikipedia.org/wiki/Morris_worm "Morris worm - Wikipedia"
