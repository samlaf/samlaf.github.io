---
title:  "Authorization, Policy, and Reference Monitors"
series: "Applied Crypto, Part 4"
series_url: "/programming/crypto-series-intro.html"
category: programming
date: 2026-06-08
---

Crypto protects bytes. **Policy decides who may do what.**

Those are different questions. A signature can prove that Alice signed a request; it does not decide whether Alice is allowed to delete the database. TLS can prove you are talking to `api.example.com`; it does not decide whether this client may call `POST /refunds`. Envelope encryption can make an object unreadable without a key; it does not decide who may unwrap that key.

This post is the non-crypto half of the enforcement story: **authorization, policy, and reference monitors**. It is where the security cube's reasoning ladder becomes explicit:

```text
property → capability/function → policy → mechanism
```

For confidentiality and integrity, there are two dominant enforcement routes:

| Route | Style | Core mechanism |
|---|---|---|
| **Self-protecting data** | Bind the decision early into keys, tokens, ciphertexts, or signatures. | crypto |
| **Mediated access** | Decide at access time by asking a trusted guard. | reference monitor / access control |

The two routes are not rivals. Real systems compose them.

## Cube coordinates

```text
Concerns:
  secrecy, correctness, origin, attribution, access

Data states:
  at rest | in transit | in use

Reasoning layers:
  capability → policy → mechanism

Control modality:
  technology + process, with human review around high-risk decisions
```

## Authentication, authorization, audit

The classic split is:

```text
authentication: who are you?
authorization:  what may you do?
audit/accounting: what did you do?
```

Authentication produces a claim about identity or origin: this request came from Alice; this server controls `example.com`; this workload holds a SPIFFE identity; this enclave produced a quote with measurement `M`.

Authorization consumes that claim and decides whether an action is allowed.

Audit records what happened so future humans, machines, or courts can reconstruct it.

AAA, IAAA, and Lampson's Gold Standard all live here. They are **capability/function** frameworks, not property frameworks. They answer *what kind of security service do I need?* — authenticate, authorize, account/audit — not *what counts as a violation?*.

## Policy as a predicate over an event

A policy is not merely a PDF in a compliance folder. In the technical sense, a policy is a predicate over an access event:

```text
subject S may perform action A on object O under context C
```

Examples:

```text
PayrollService may call KMS.Decrypt on payroll KEKs from prod VPCs.

Alice may read her own medical record, but not Bob's.

The release bot may sign artifacts only after CI passed on main.

An enclave may receive the database key only if its quote contains measurement M,
TCB version >= V, and a fresh nonce from the verifier.
```

This is why policy is the only multi-W layer in the ladder. It is about **who** may do **what** to **which** object, **when/where/under what context**.

## Early binding: crypto compiles policy into keys

Crypto often makes authorization feel invisible because the policy is bound early.

```text
encrypt to Bob's public key
issue a token with scope=read:payroll
wrap a DEK for PayrollService
sign an artifact with the release key
seal a secret to TPM PCR values
release a database password only to an enclave measurement
```

After that binding, the mechanism is local and simple:

```text
key-holder can decrypt
private-key holder can sign
MAC-key holder can authenticate
public-key holder can verify
```

This is the power of crypto: the data can protect itself across untrusted storage and untrusted networks. The guard does not need to be online when the ciphertext is copied or the signature is verified.

But the cost is that the decision is now hard to change. If Bob's key leaks, old ciphertexts are exposed. If Alice leaves the company, old files encrypted to her key remain decryptable unless you re-encrypt or wrapped the data keys through a revocable mediator. If a token is bearer and long-lived, whoever steals it gets the authority until expiry. Crypto gives you offline enforcement by freezing part of policy into key material.

## Late binding: reference monitors decide at access time

Access control binds later. A request arrives; a trusted mediator checks the current policy; only then does the operation happen.

```text
subject S requests action A on object O under context C
PEP intercepts request
PDP evaluates policy
PEP allows or denies
logger records the decision
```

The classic abstraction is the **reference monitor**: an enforcement mechanism that is always invoked, tamper-proof, and small enough to reason about. Operating-system kernels, hypervisors, database permission engines, API gateways, IAM systems, KMSes, Kubernetes admission controllers, browser same-origin policy, and smart-contract VMs are all reference-monitor-shaped.

Late binding buys dynamism:

- revoke Alice now
- require MFA only for risky actions
- deny access outside business hours
- check device posture
- log every decrypt
- apply emergency break-glass rules
- roll out a new policy without re-encrypting every object

The cost is that the mediator must be trusted and available. If the reference monitor is bypassed, the policy evaporates. If the KMS is down, your encrypted data may be unavailable. Late binding trades offline self-protection for online control.

## The XACML split: PEP / PDP / PAP / PIP

The access-control world names the pieces precisely:

| Component | Role |
|---|---|
| **PEP** — Policy Enforcement Point | The gate. It intercepts the request and enforces allow/deny. |
| **PDP** — Policy Decision Point | The brain. It evaluates policy and returns a decision. |
| **PAP** — Policy Administration Point | The editor. It creates/stores the policies. |
| **PIP** — Policy Information Point | The context fetcher. It supplies attributes: user role, device posture, resource label, time, location, risk score. |

That last piece matters because real policy is contextual. ABAC is the general form: authorization depends on attributes of the subject, object, action, and environment.

## Policy models

Different policy models are different languages for the same event predicate.

| Model | Shape | Best for |
|---|---|---|
| **ACL** | Object lists allowed subjects/actions. | Files, buckets, simple resources. |
| **Capabilities** | Subject holds an unforgeable token granting authority. | Delegation, object capabilities, macaroons, bearer/proof tokens. |
| **DAC** | Owners decide permissions. | Unix-ish discretionary sharing. |
| **MAC** | System labels dominate user choice. | Classified systems, mandatory boundaries. |
| **RBAC** | Users get roles; roles get permissions. | Enterprises and admin consoles. |
| **ABAC** | Rules over attributes/context. | Cloud IAM, zero-trust, dynamic environments. |

The classic formal models are more specialized:

- **Bell–LaPadula** — confidentiality: no-read-up, no-write-down.
- **Biba** — integrity: no-read-down, no-write-up.
- **Clark–Wilson** — integrity through well-formed transactions and separation of duty.
- **Brewer–Nash / Chinese Wall** — dynamic conflict-of-interest.

These are **policy models**. They are not mechanisms. A kernel, database, KMS, or API gateway may enforce them; the model itself is the rule-set.

## Mechanisms that enforce policy

A policy becomes real only when some mechanism mediates operations:

| State | Mediated-access mechanisms |
|---|---|
| **At rest** | file permissions, database row-level security, S3 bucket policy, KMS/IAM, secret managers, backup ACLs |
| **In transit** | API gateways, mTLS authorization, OAuth scopes, sender-constrained tokens, service mesh policy |
| **In use** | MMU/page tables, process isolation, seccomp/eBPF, containers, hypervisors, enclave admission, Kubernetes admission controllers |

Notice that several of these mechanisms use crypto internally. OAuth uses signed tokens; mTLS uses certificates; KMS uses HSM-held keys; enclaves use attestation signatures. But their *job* is policy enforcement. Crypto is a mechanism inside a larger reference-monitor-shaped system.

## KMS as the canonical hybrid

Envelope encryption is the pattern where the two enforcement families visibly meet:

```text
object plaintext
  encrypted under a DEK
ciphertext + wrapped DEK stored in object store
DEK wrapped under KEK
KEK lives in KMS/HSM
KMS policy decides who may unwrap
```

The object store does not need to be trusted with plaintext. The ciphertext is self-protecting. But decryption is late-bound by KMS policy: every unwrap can check IAM, network context, key state, quota, break-glass rules, and audit settings.

This pattern is why "crypto vs access control" is the wrong fight. The useful architecture is:

```text
crypto protects data when the mediator is absent or untrusted
access control governs key use when the mediator is present
```

## Policy around authentication and attestation

Authentication also needs policy. A verifier must decide which proofs count.

```text
Which CA roots are trusted?
Which certificate usages are acceptable?
Which OIDC issuers and audiences are allowed?
Which passkey origins match this relying party?
Which TPM/TDX/SEV measurements are admissible?
Which token scopes authorize this API call?
```

The mechanism can verify a signature. Policy decides whether that signer is acceptable for this purpose.

This is the recurring pattern:

```text
signature verifies      ≠ signer is authorized
certificate chains      ≠ this root should be trusted
attestation quote valid ≠ this measurement may see the secret
OAuth token valid       ≠ this scope is enough for this operation
```

## Process and human controls

McCumber's third axis shows up around policy more than anywhere else. Technical policy is surrounded by process and humans:

- who can edit IAM policy?
- who approves production access?
- how often are grants reviewed?
- who can trigger break-glass?
- how are root keys rotated?
- how are emergency revocations handled?
- how do admins avoid rubber-stamping prompts?

A perfect PDP cannot save a policy written by the wrong people, approved through the wrong process, or bypassed by social pressure. This is where separation of duties, change control, review ceremonies, incident response, and audit culture belong.

## The punchline

Policy is invariant across mechanism families:

```text
who may do what to which object under which context?
```

Crypto and reference monitors differ mainly in **when** that policy decision is bound.

```text
crypto:             early binding into keys/tokens/ciphertexts/signatures
reference monitor:  late binding at access time
KMS:                crypto for the data, late binding for the key
```

Everything else in the series keeps using this distinction. Secure channels bind peers and keys early in a handshake; storage systems late-bind decryption through KMS; authentication proves identity but leaves authorization to policy; attestation verifies a measurement but still needs a verifier policy saying which measurements are acceptable.

## References <!-- omit in toc -->

1. [Computer Security Technology Planning Study — Anderson Report][anderson]
2. [Protection — Butler Lampson][lampson]
3. [XACML Reference Architecture — OASIS][xacml]
4. [Bell–LaPadula Model - Wikipedia][blp]
5. [Biba Model - Wikipedia][biba]
6. [Role-Based Access Control - NIST][nist-rbac]
7. [Attribute Based Access Control - NIST SP 800-162][nist-abac]

[anderson]: https://csrc.nist.gov/csrc/media/publications/conference-paper/1998/10/08/proceedings-of-the-21st-nissc-1998/documents/early-cs-papers/ande72.pdf "Computer Security Technology Planning Study — Anderson Report"
[lampson]: https://dl.acm.org/doi/10.1145/361011.361067 "Protection — Butler Lampson"
[xacml]: https://www.oasis-open.org/standard/xacmlv3-0/ "eXtensible Access Control Markup Language (XACML) Version 3.0"
[blp]: https://en.wikipedia.org/wiki/Bell%E2%80%93LaPadula_model "Bell–LaPadula model - Wikipedia"
[biba]: https://en.wikipedia.org/wiki/Biba_Model "Biba Model - Wikipedia"
[nist-rbac]: https://csrc.nist.gov/projects/role-based-access-control "Role Based Access Control - NIST"
[nist-abac]: https://csrc.nist.gov/publications/detail/sp/800-162/final "Guide to Attribute Based Access Control (ABAC) Definition and Considerations - NIST SP 800-162"
