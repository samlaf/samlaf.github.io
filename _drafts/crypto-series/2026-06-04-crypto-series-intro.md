---
title:  "Applied Crypto in the Security Cube"
category: programming
date: 2026-06-04
---

This is a series on applied cryptography — not the math, but the engineering: which keys and algorithms exist, how they compose into channels, storage systems, authentication, authorization, and attestation, and where all the trust ultimately bottoms out.

The series is organized by one sentence:

> For each **property/concern**, in each **data state**, against each **threat**, choose a **function/capability**, define the **policy**, enforce it with **mechanisms**, wrapped by **technical / process / human controls**.

That is the working expansion of the McCumber cube for software engineers. McCumber gave us **CIA × storage/transmission/processing × technology/policy/people**.

![alt text](/assets/crypto-series-intro/mccumber-cube.png)

This series keeps that, but splits McCumber's third axis into the two orthogonal things it blends — *how abstract* the control is, and *what material* it is made of:

```text
concern × data-state × layer × modality
```

Where:

```text
concern    — what's at stake   (each has a defender name = property, an attacker name = threat)
data-state — where the data is : at rest | in transit | in use
layer      — how abstract      : capability/function → policy → mechanism
modality   — what material     : technology | process/practice | human/education
```

The `layer` and `modality` axes are perpendicular: every control has both an *altitude* (capability/policy/mechanism) and a *material* (tech/process/human) — a reference monitor is a `(mechanism, tech)` control; a four-eyes deploy checklist is `(mechanism, process)`; a written classification standard is `(policy, process)`. The same three altitudes recur in every material.

The `concern` axis carries two names for each thread — the **property** you want to hold and the **threat** you defend against are the same thing seen from the two sides:

| Concern | Property · *defender's name* | Threat · *attacker's name* |
|---|---|---|
| **secrecy** | confidentiality | information disclosure |
| **correctness** | integrity | tampering |
| **origin** | authenticity | spoofing |
| **attribution** | accountability / non-repudiation | repudiation |
| **unlinkability** | anonymity | linking / profiling |
| **uptime** | availability | denial of service |

The meta-post, **[A Taxonomy of Security Taxonomies](/programming/security-acronyms.html)**, is the expanded map. This series is the applied-crypto slice of that map.

## The two enforcement families

For confidentiality and integrity of data objects, there are two dominant enforcement styles:

| Enforcement style | Core idea | Examples |
|---|---|---|
| **Self-protecting data** | Put the protection on the bytes themselves. If you lack the key, ciphertext is unreadable or tampering is detectable. | AEAD, MACs, signatures, commitments, encrypted objects |
| **Mediated access** | Put a trusted guard in front of operations. Every read/write/execute request is checked at access time. | reference monitors, ACL/RBAC/ABAC, IAM, KMS policy, OS kernels, database guards |

Crypto is the first family. Access control is the second. Real systems almost always combine them:

```text
ciphertext in object storage
wrapped DEK beside it
KEK in KMS/HSM
IAM policy decides who may unwrap
reference monitor enforces the decision
audit log records the use
```

The important distinction is **when policy binds**.

**Crypto tends to bind early.** You encrypt to Bob's public key, issue a token with a scope, wrap a DEK for a service, or sign an artifact with a release key. The authorization decision is compiled into a key, token, ciphertext, or signature. That works offline and survives untrusted storage/transit, but revocation and context changes are hard.

**Reference monitors bind late.** A subject requests an action on an object under some context, and a policy decision point says yes or no *now*. That is dynamic, revocable, context-aware, and auditable — but it requires an online trusted mediator.

KMS is the hybrid pattern: crypto protects the stored bytes, and access control late-binds use of the decryption key.

## Kerckhoffs's split: keys vs algorithms

Kerckhoffs's principle says the design should remain secure even when the adversary knows the system; only the key is secret. So the first two mechanism posts split crypto into its two halves:

```text
secret authority material:  keys
public transformation code: algorithms
```

A cipher, MAC, signature scheme, KDF, or handshake pattern is public machinery. A key is the authority to make that machinery do something security-relevant: decrypt, authenticate, sign, unwrap, derive, attest, or delegate. Much of applied crypto is really key engineering: where the key comes from, who may use it, whether it can be extracted, how it rotates, and what root of trust says it belongs to the right party.

## The data-state axis

The same concern changes shape depending on where the data is:

| Concern | At rest | In transit | In use |
|---|---|---|---|
| **Secrecy** | envelope encryption, disk encryption, read-control | TLS, WireGuard, E2EE | process isolation, TEEs, minimization |
| **Correctness** | MACs, signatures, hash trees, write-control | AEAD, sequence numbers, transcript hashes | measured boot, sandboxing, verified code |
| **Origin** | signed artifacts, package provenance, KMS caller identity | certificates, mTLS, passkeys, signed tokens | workload identity, enclave identity, device identity |
| **Attribution** | audit logs, signed releases | signed requests, non-repudiable messages | tamper-evident logs, measured execution |
| **Unlinkability** | metadata minimization, private indexes | padding, mixnets, onion routing | PIR, query privacy, local processing |
| **Uptime** | backups, recovery, key escrow tradeoffs | rate limits, cookies, retries | redundancy, failover, resource isolation |

Availability is deliberately not a major crypto topic. Crypto can support availability indirectly — for example by authenticating admission-control cookies or protecting backups — but it mostly *subtracts* from availability: expensive handshakes enable DoS, lost keys destroy access, and ransomware is confidentiality turned against you. The [availability appendix](/programming/availability.html) gives that leg its own short treatment — the capability/policy/mechanism breakdown of rate-limiting, redundancy, backup/recovery, and incident response — for the places later articles need to point to it.

## The articles

1. **[Threat Models Across Data States](/programming/threat-model.html)** — the threat layer of the cube: data in transit, at rest, and in use. The old internet story remains, but becomes one section of a larger map.
2. **[Keys: Secret Material and Authority](/programming/keys.html)** — the secret half of crypto mechanisms: entropy, custody, lifecycle, key policy, KMS/HSMs, Secure Enclaves, TPMs, DEK/KEK, rotation, revocation, recovery.
3. **[Algorithms: Public Crypto Mechanisms](/programming/crypto-primitives.html)** — the public half: PRFs/PRPs, hashes, KDFs, CSPRNGs, AEAD, MACs, signatures, freshness, misuse resistance, key commitment.
4. **[Authorization, Policy, and Reference Monitors](/programming/authorization-policy-reference-monitors.html)** — the missing non-crypto half: authentication vs authorization vs audit, policy as a predicate over an access event, ACL/RBAC/ABAC, Bell–LaPadula/Biba, PEP/PDP, IAM, KMS policy, and early vs late binding.
5. **[Authentication, Certificates, Roots, and Delegation](/programming/authentication.html)** — origin and identity: proof of possession, binding statements, trust anchors, verifier policy, Web PKI, passkeys, mTLS, OAuth/OIDC/GNAP.
6. **[Data in Transit: Key Exchange & Secure Channels](/programming/secure-channels.html)** — the in-transit composition: DH/KEM + HKDF + AEAD, TLS, HPKE, Noise, WireGuard, Signal, replay/downgrade/freshness tradeoffs.
7. **[Data at Rest: Storage, KMS, and Recovery](/programming/data-at-rest-storage-kms-and-recovery.html)** — the storage composition: disk/object/database encryption, envelope encryption, KMS/HSMs, signed artifacts, backups, rollback, ransomware, deletion, recovery.
8. **[Data in Use: Isolation, Measurement, and Attestation](/programming/data-in-use-isolation-measurement-and-attestation.html)** — the processing composition: process isolation, sandboxes, TPMs, measured boot, SGX/TDX, SEV-SNP, vTPMs, cloud attestation, and secret release.
9. **[What Crypto Still Doesn't Give You](/programming/what-crypto-still-doesnt-give-you.html)** — the negative space: roots, naming, authorization, revocation, metadata, replay, group state, side channels, availability, and governance.

Two companion pages sit outside the numbered arc — read either when you need it, not in sequence:

- **[A Taxonomy of Security Taxonomies](/programming/security-acronyms.html)** — the full map this series is a slice of: concern × data-state × layer × modality, and where every acronym (CIA, AAA, STRIDE, BLP, …) lands on it.
- **[Availability: Uptime, Redundancy, and Recovery](/programming/availability.html)** — the one CIA leg crypto doesn't carry, given its own capability/policy/mechanism breakdown: rate-limiting, redundancy, backup/recovery, incident response.

The throughline is simple: crypto lets data protect itself, but it never eliminates policy. It moves policy into keys, roots, tokens, measurements, and verifier decisions — and the rest of the security cube is still there waiting for you.
