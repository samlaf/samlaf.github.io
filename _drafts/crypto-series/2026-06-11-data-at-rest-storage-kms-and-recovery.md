---
title:  "Data at Rest: Storage, KMS, and Recovery"
series: "Applied Crypto, Part 7"
series_url: "/programming/crypto-series-intro.html"
category: programming
date: 2026-06-11
---

Data at rest is where crypto stops looking like a handshake and starts looking like operations.

A TLS connection has a beginning and an end. A stored object may live for years, be copied into backups, move across regions, survive employee turnover, outlive algorithms, get restored after ransomware, and need to be deleted on purpose. The core mechanism is still simple — encrypt bytes with an AEAD — but the hard parts are lifecycle and policy: who may unwrap the key, how long the data exists, how rollback is detected, how recovery works, and what happens when keys are lost.

## Cube coordinates

```text
Concerns:
  secrecy, correctness, possession, utility, attribution, uptime

Data state:
  at rest

Reasoning layers:
  threat → property → capability → policy → mechanism

Control modality:
  technology + process + human
```

The storage version of the series' main distinction is:

```text
self-protecting data:  encrypted / MACed / signed objects
mediated access:       KMS, IAM, database guards, file permissions, backup controls
```

Good storage security uses both.

## Threats to data at rest

The obvious threat is stolen media: a laptop, phone, disk, backup tape, EBS snapshot, S3 bucket, database dump, or object-store credential leaks. But storage threats are broader than disclosure.

| Threat | Property hit | Typical control |
|---|---|---|
| Stolen disk/laptop | confidentiality, possession | full-disk encryption, device keys |
| Leaked database snapshot | confidentiality | field/object encryption, KMS, access review |
| Malicious storage admin | confidentiality, integrity | client-side encryption, envelope encryption, audit, separation of duties |
| Backup compromise | confidentiality, integrity | encrypted backups, signed manifests, restricted restore path |
| Ransomware | availability, possession, integrity | immutable backups, offline copies, recovery drills |
| Rollback/stale restore | integrity, freshness | versioning, append-only logs, signed checkpoints |
| Silent corruption | integrity, utility | hashes, MACs, erasure coding, scrubbing |
| Lost key | availability, utility | recovery policy, escrow tradeoffs, rotation discipline |
| Over-retention | privacy, compliance | deletion policy, key destruction, retention automation |

The important asymmetry: encryption protects confidentiality even when storage is stolen, but it can hurt availability. Lose the only key and the data is gone. Ransomware is the same mechanism pointed the wrong way: confidentiality against the owner.

## Desired properties

For stored data, CIA splits into several sharper concerns:

- **Secrecy** — unauthorized parties cannot read the content.
- **Correctness/integrity** — unauthorized parties cannot undetectably modify it.
- **Freshness** — an old valid version cannot be replayed as current.
- **Possession/control** — the owner can retain or deliberately relinquish control.
- **Utility** — the bytes are usable when needed; ciphertext with a lost key is available but useless.
- **Attribution** — sensitive reads/writes/decrypts can be tied to an actor.
- **Availability** — data survives failures, extortion, deletion mistakes, and regional outages.

Crypto directly helps with secrecy and integrity. It helps with attribution through signatures and audit-log integrity. It helps with deletion only indirectly through key destruction. Availability comes mostly from redundancy, backups, recovery drills, and operational controls.

## Mechanism 1: full-disk encryption

Full-disk encryption protects a device or volume while it is powered off. The disk holds ciphertext; a boot-time secret unlocks the volume key; the OS sees plaintext after unlock.

This is excellent against theft of inert media:

```text
stolen laptop off → attacker sees ciphertext
cloud snapshot copied without key → attacker sees ciphertext
```

But it does little once the machine is running:

```text
compromised OS → plaintext available
malware running as user → reads through filesystem
cloud admin with live access path → depends on platform controls
```

Full-disk encryption is therefore an **at-rest** control, not an **in-use** control. It moves the problem from "protect every sector" to "protect the unlock key and the running system."

## Mechanism 2: object / field encryption

Application-level encryption protects individual objects, fields, or records before they hit storage.

```text
plaintext record
  → AEAD(key, nonce, associated_data, plaintext)
  → ciphertext + tag + metadata
```

The associated data should bind the ciphertext to context that must not be swapped:

```text
object id
schema version
tenant id
purpose
creation time
key id
```

That prevents an attacker from moving ciphertext from one row, tenant, or purpose to another while keeping the tag valid. AEAD authenticates both the encrypted plaintext and the unencrypted associated metadata.

Object encryption is what you want when the storage layer itself is not trusted with plaintext: object stores, queues, caches, browser sync, multi-tenant databases, and client-side encrypted systems.

## Mechanism 3: envelope encryption

Envelope encryption is the standard scalable pattern:

```text
DEK = random data-encryption key
ciphertext = AEAD(DEK, plaintext)
wrapped_DEK = KMS.Encrypt(KEK, DEK)
store(ciphertext, wrapped_DEK, key_id, metadata)
```

To read:

```text
DEK = KMS.Decrypt(wrapped_DEK)
plaintext = AEAD.Open(DEK, ciphertext)
```

The **DEK** is per object, per file, per table, or per tenant. The **KEK** is the long-lived key-encryption key held by KMS/HSM and usually never exported.

This buys three things:

1. **Blast-radius control.** A leaked DEK exposes only the objects under that DEK.
2. **Cheap rotation.** Rotate the KEK by rewrapping DEKs, not re-encrypting terabytes.
3. **Late-bound policy.** Every unwrap can ask IAM/KMS policy whether this caller may decrypt now.

Envelope encryption is the canonical hybrid of crypto and access control: ciphertext self-protects in storage; KMS mediates key use at read time.

## KMS and HSMs

A KMS is a reference monitor for key operations. An HSM is the hardware boundary that keeps high-value keys non-extractable. Cloud KMS products combine both: an API surface with IAM policy, backed by software or hardware key isolation.

The useful question is not "is the data encrypted?" but:

```text
Who can call Decrypt?
From where?
For which key?
Under which context?
Is the key enabled?
Is the request logged?
Can an admin bypass it?
Can the key be exported?
Can it be scheduled for destruction?
How is recovery handled?
```

KMS policy is late binding. It lets you revoke access without rewriting all ciphertext. But it also makes KMS an availability dependency and a concentrated trust point.

## Integrity at rest

Encryption alone does not give integrity unless it is authenticated encryption. For stored objects, use an AEAD or a separate MAC/signature.

The choice depends on who needs to verify:

| Need | Mechanism |
|---|---|
| Only key-holders verify and produce tags | MAC / AEAD |
| Anyone can verify but only signer can produce | signature |
| Detect accidental corruption | hash/checksum |
| Prove inclusion/history | Merkle tree, transparency log, append-only log |
| Detect rollback | signed checkpoint, monotonic counter, external timestamp, quorum state |

The difference between MACs and signatures matters more at rest than it first appears. A MAC proves "someone with the shared key made this." A signature can prove to a third party which private key signed. That is why software releases, package registries, certificate logs, and audit records lean on signatures.

## Rollback and freshness

A ciphertext can be perfectly valid and still stale. If an attacker restores last month's encrypted database, every AEAD tag may verify. The cryptography proves the bytes were produced under the key; it does not prove they are the current bytes.

Freshness needs state outside the object:

- monotonically increasing version numbers
- append-only logs
- signed checkpoints
- transparency logs
- trusted timestamps
- quorum replication
- TPM monotonic counters, with caveats
- application-level idempotency and sequence state

This is the at-rest version of replay. A secure channel orders bytes inside one connection; storage systems need their own freshness story across crashes, restores, replicas, and backups.

## Backups and ransomware

Availability lives here, and crypto is ambivalent. Encryption protects backups from disclosure; immutable/offline backups protect against ransomware; but lost keys or encrypted-by-attacker data destroy utility.

A realistic backup policy needs:

- encrypted backup media
- separate backup credentials
- immutable or append-only retention windows
- offline or cross-account copies
- restore drills
- signed manifests or hashes to detect tampering
- key escrow/recovery decisions made explicitly
- documented break-glass access

The uncomfortable tradeoff: the stronger your key non-recovery story, the more permanent accidental loss becomes. The stronger your escrow/recovery story, the more attractive the escrow path becomes to attackers. There is no purely cryptographic answer; this is process and human control around cryptographic material.

## Deletion and crypto-shredding

Deleting encrypted data can sometimes mean deleting the key. If every object is encrypted under a unique DEK, and that DEK is irrecoverably destroyed, the ciphertext becomes useless. This is **crypto-shredding**.

It is attractive because deleting all replicas of a blob is hard; deleting a small key may be easier. But it only works if:

- the DEK was not copied elsewhere
- plaintext was not cached/logged/indexed
- backups do not retain the key
- derived keys cannot be regenerated
- deletion actually destroys all recovery paths

Again: crypto gives the primitive, process decides whether the promise is true.

## Data-at-rest policy

Storage policy answers questions like:

```text
Which data must be encrypted?
At what granularity: disk, table, field, object, tenant?
Who may decrypt?
Who may rotate keys?
Who may schedule key destruction?
How long is data retained?
What is the backup retention period?
Who can restore production data?
Is break-glass allowed?
Are decrypts logged and reviewed?
What associated data must be authenticated?
Which algorithms and key sizes are permitted?
```

Those policies are enforced by a mix of mechanisms: application code, database permissions, KMS/IAM, HSM non-extractability, object-store policy, deployment pipelines, backup systems, and audit logs.

## Storage across the four axes

Putting the cube together:

| Layer | Storage example |
|---|---|
| **Threat** | leaked DB snapshot, malicious admin, ransomware, rollback |
| **Property** | confidentiality, integrity, freshness, availability |
| **Capability** | encryption, key management, access control, backup/recovery, audit |
| **Policy** | who may decrypt, rotate, restore, delete; retention and recovery rules |
| **Mechanism** | AEAD, DEK/KEK, KMS/HSM, IAM, signatures, hash trees, immutable backups |
| **Control modality** | technology plus rotation runbooks, access reviews, recovery ceremonies |

## The punchline

Data at rest is not "encrypt the database". It is:

```text
protect stored bytes with crypto,
late-bind key use with policy,
record access with audit,
preserve utility with recovery,
and decide explicitly who can destroy or restore what.
```

The mechanism is AEAD. The system is key management.

## References <!-- omit in toc -->

1. [DEK/KEK: The Industry Standard to Protect Sensitive Data - Fystack][fystack-dek-kek]
2. [Concepts of Compliant Data Encryption - Stephen Roughley][roughley-compliant-enc]
3. [Best Practices for Key Derivation - Trail of Bits][tob-kdf]
4. [Authenticated Encryption - Wikipedia][ae-wiki]
5. [Amazon S3 Server-Side Encryption - AWS][aws-s3-sse]
6. [Cloud KMS Documentation - Google Cloud][gcp-kms]

[fystack-dek-kek]: https://fystack.io/blog/dek-kek-the-industry-standard-to-protect-highly-sensitive-data-part-1 "DEK/KEK: The Industry Standard to Protect Sensitive Data - Fystack"
[roughley-compliant-enc]: https://stephenroughley.com/2019/06/09/concepts-of-compliant-data-encryption/ "Concepts of Compliant Data Encryption - Stephen Roughley"
[tob-kdf]: https://blog.trailofbits.com/2025/01/28/best-practices-for-key-derivation/ "Best Practices for Key Derivation - Trail of Bits"
[ae-wiki]: https://en.wikipedia.org/wiki/Authenticated_encryption "Authenticated encryption - Wikipedia"
[aws-s3-sse]: https://docs.aws.amazon.com/AmazonS3/latest/userguide/serv-side-encryption.html "Protecting data with server-side encryption - Amazon S3"
[gcp-kms]: https://cloud.google.com/kms/docs "Cloud Key Management Service Documentation - Google Cloud"
