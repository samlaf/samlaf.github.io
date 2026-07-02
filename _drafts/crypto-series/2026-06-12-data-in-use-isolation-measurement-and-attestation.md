---
title:  "Data in Use: Isolation, Measurement, and Attestation"
series: "Applied Crypto, Part 8"
series_url: "/programming/crypto-series-intro.html"
category: programming
date: 2026-06-12
---

Data in use is the state crypto has the hardest time with. Stored data can be ciphertext. Data in transit can be protected inside a channel. But computation needs plaintext somewhere: in registers, memory, a process, an enclave, a VM, a database engine, or an AI agent's context window.

So the data-in-use question is:

> Why should I believe this key is controlled by the code and environment I intended, rather than by the OS, hypervisor, cloud provider, malware, or an impostor?

The answer is a combination of **isolation**, **measurement**, and **attestation**.

## Cube coordinates

```text
Concerns:
  secrecy, correctness, origin-of-code, admissibility, freshness

Data state:
  in use / processing

Reasoning layers:
  threat → property → capability → policy → mechanism

Control modality:
  technology, wrapped by verifier policy and operational process
```

The in-use ladder looks like:

```text
Threat:
  malicious process, compromised OS, hostile hypervisor, cloud admin, side channel, bad dependency

Property:
  memory confidentiality, runtime integrity, code identity, admissibility

Capability:
  isolation, measurement, remote attestation, secret release

Policy:
  which vendor roots, TCB versions, measurements, PCR/RTMR values, and freshness rules are acceptable?

Mechanism:
  MMU, process isolation, sandboxing, TPMs, measured boot, SGX/TDX, SEV-SNP, vTPMs, CVM attestation
```

## Isolation: the first in-use control

The oldest data-in-use mechanism is not a TEE; it is the reference monitor.

- the MMU keeps one process from reading another process's pages
- the kernel enforces file descriptors, users, capabilities, namespaces
- seccomp/eBPF restricts syscalls
- containers and hypervisors isolate workloads
- language runtimes sandbox code
- browsers isolate origins

This is mediated access rather than self-protecting data. The data is plaintext inside the authorized process; the security claim is that other processes cannot reach it except through mediated interfaces.

The weakness is obvious: if the mediator is compromised, the plaintext is exposed. A malicious kernel can read process memory. A hostile hypervisor can inspect a VM. A cloud operator may control the host below your workload. Data-in-use mechanisms below are attempts to shrink or re-anchor that trusted computing base.

## Measurement: naming the computation

Before a verifier can decide whether code is acceptable, the platform needs a stable name for what ran. That name is a **measurement**: a cryptographic digest of code, configuration, boot state, or runtime events.

Measured boot extends registers as the system boots:

```text
PCR := H(PCR || event)
```

Intel TDX uses RTMRs; TPMs use PCRs; secure boot chains measure firmware, bootloaders, kernels, initrds, policies, and sometimes application code. The measurement does not say the code is good. It says the code is *this* code.

That distinction is load-bearing:

```text
measurement verifies  ≠ code is safe
measurement verifies  = code/environment matches a known digest
```

Policy supplies the missing step: which measurements are acceptable for this secret or request?

## Attestation: authentication of a computation environment

Attestation is authentication pointed at a runtime environment.

Normal authentication says:

```text
this key belongs to Alice / example.com / PayrollService
```

Attestation says:

```text
this key is controlled by code with measurement M
running under platform state S
under hardware/vendor root R
fresh for nonce N
```

The verifier checks a signed report, quote, or certificate chain, then applies policy:

```text
Is the vendor root trusted?
Is the TCB version acceptable?
Are the measurements expected?
Is the quote fresh?
Is this workload allowed to receive this secret?
```

A valid quote is not authorization. It is evidence consumed by authorization policy.

## What ultimately authenticates a key?

A channel's session keys come out of an ephemeral DH exchange — but what stops an attacker from just running that exchange with you themselves? One long-term key in the handshake is authenticated, and that authentication chains upward until it hits something trusted before the connection began.

![image](/assets/roots-of-trust-and-attestation/session-key-authentication-chain.png)

There are two chains to the same destination here. The left one is the familiar Web PKI: the leaf cert binds a domain to a key, signed by an intermediate, signed by a Root CA baked into your browser. The right one is hardware attestation: an Intel SGX/TDX root signs an attestation key, which signs a quote whose report data commits to a session key hash. Either way, the session key is only as trustworthy as the out-of-band anchor at the top and the verifier policy that accepts it.

## Roots of trust are out-of-band anchors

Roots are never derived by crypto. They are configured.

![image](/assets/roots-of-trust-and-attestation/roots-of-trust-out-of-band.png)

Examples:

**CA roots.** Browsers and OSes ship root stores. The Web PKI works because clients accept those roots as anchors for certificate chains.

**CT log keys.** Modern browsers require Signed Certificate Timestamps from trusted Certificate Transparency logs. The log public keys are also shipped in browser policy.

**NTP / time roots.** Certificate validation depends on time. NTP server addresses arrive via DHCP or hardcoded fallback. Network Time Security then leans on TLS roots.

**OS and package signing keys.** The browser binary and root store were installed by an OS/package manager with its own signing roots.

**UEFI Secure Boot Platform Key.** Firmware decides which bootloaders are accepted before the OS starts.

**Hardware vendor roots.** Intel, AMD, Apple, ARM, TPM manufacturers, cloud providers — each attestation ecosystem starts with vendor roots accepted by verifier policy.

**Blockchain genesis hashes.** A client ships a genesis hash or checkpoint. "Which chain is real?" begins as an out-of-band software choice.

Attestation chains may be cryptographic, but root acceptance is policy.

## The REMITS lens

Red Hat's REMITS model is a useful way to read any attestation scheme: who measures, who attests, what evidence is produced, which reference values are checked, and what secret or decision follows.

![image](/assets/roots-of-trust-and-attestation/remits-model.png)

The recurring pattern:

```text
attester produces evidence
verifier checks evidence against reference values
relying party releases a secret or accepts the workload
```

The secret-release step is where attestation meets key management. A KMS, secret manager, or verifier releases a key only if the quote is fresh and the measurement matches policy.

## TPMs

A TPM gives a machine hardware-backed keys, PCRs, sealed storage, and quotes. It is not magic isolation; it is a root for measurement and key operations.

![image](/assets/roots-of-trust-and-attestation/remits-tpm.png)

A TPM can:

- generate or protect non-extractable keys
- extend PCRs with boot measurements
- seal secrets to PCR values
- quote PCR values with an attestation key
- prove, via an endorsement chain, that the attestation key belongs to a real TPM

Two things are easy to confuse:

1. **Sealing** — the TPM releases a secret locally only when PCRs match.
2. **Quoting** — the TPM signs PCRs so a remote verifier can decide.

TODO: figure out which of the 2 below diagrams is correct.

![image](/assets/roots-of-trust-and-attestation/tpm-key-hierarchy-1.png)

![image](/assets/roots-of-trust-and-attestation/tpm-key-hierarchy-2.png)

## Confidential VMs and TEEs

Confidential computing tries to protect a guest workload from the host infrastructure. The claim is no longer merely "the cloud authenticates this VM" but "this VM's memory and initial state are protected from the host, and the guest can prove what it is."

### AMD SEV-SNP

AMD SEV-SNP protects VM memory and provides attestation rooted in AMD keys.

![image](/assets/roots-of-trust-and-attestation/remits-amd-sev.png)

The verifier checks the report, TCB, chip/platform chain, and measurement. Policy decides whether that platform/version/measurement may receive the secret.

### Intel DCAP / TDX

Intel DCAP provides a PKI for quote verification: Intel root → platform certs → quote-signing material → quote over measurements and report data.

![image](/assets/roots-of-trust-and-attestation/intel-dcap-key-hierarchy.png)

In the REMITS model:

![image](/assets/roots-of-trust-and-attestation/remits-intel-dcap.png)

The important detail is that the quote can commit to application data, often a hash of an ephemeral public key. That binds the attested environment to the secure channel you are about to use.

## Cloud attestation of CVMs: vTPM or direct hardware quote

Cloud providers differ in where they put the abstraction boundary. Some expose a vTPM-shaped interface; others expose a more direct hardware quote plus cloud platform evidence.

### vTPM model: Azure-style two-run chain

In the vTPM model, the first trust decision uses hardware-provided evidence against the cloud provider's attestation architecture. If successful, that first run unlocks secrets needed to construct or restore a vTPM. The second run then uses the vTPM as the guest-facing root.

![image](/assets/roots-of-trust-and-attestation/azure-vtpm-two-run-chain.png)

First run, hardware-rooted:

![image](/assets/roots-of-trust-and-attestation/azure-vtpm-run1-amd-remits.png)

Second run, vTPM-rooted:

![image](/assets/roots-of-trust-and-attestation/azure-vtpm-run2-remits.png)

The benefit is a standard TPM interface for guests. The cost is an extra provider-specific layer whose construction and persistence semantics matter.

### Direct quote plus platform identity: Google-style split

In a direct model, the guest evidence may chain to Intel/AMD while platform identity chains separately to the cloud provider's hardware root.

![image](/assets/roots-of-trust-and-attestation/gcp-dual-pki-chains.png)

You then verify two things:

1. **Guest evidence** — the quote says the measured VM/workload is running under an acceptable hardware TCB.
2. **Platform evidence** — the provider says this physical machine is a legitimate member of its fleet.

Those are different trust statements. Combining them is verifier policy.

## Secret release

Attestation becomes useful when it gates a secret:

```text
workload generates ephemeral key pair
workload asks platform for quote over hash(ephemeral public key)
verifier checks quote and measurement
verifier encrypts secret to ephemeral public key
only the attested workload can decrypt
```

This is the in-use analog of authentication plus key exchange. The quote binds the session key to the measured environment; the verifier policy decides whether that environment is allowed to receive the secret.

## What attestation does not solve

Attestation is easy to oversell.

- It proves a measurement, not source-code virtue.
- It says little about bugs in measured code.
- It depends on vendor roots and revocation feeds.
- It can be undermined by side channels.
- It can be undermined by a verifier policy that accepts too much.
- It does not solve authorization: acceptable code still needs least privilege.
- It does not solve availability: a TEE can still crash, be DoSed, or lose its sealing keys.
- It does not remove supply-chain trust: the measured binary came from somewhere.

The strongest honest claim is:

```text
this key is bound to this measured environment under this root, fresh for this verifier
```

Everything after that is policy.

## References <!-- omit in toc -->

1. [Learn About Confidential Computing Attestation (REMITS) - Red Hat][redhat-cc-attestation]
2. [TPM Keys - Eric Chiang][chiang-tpm-keys]
3. [Expanding Private Cloud Compute - Apple Security][apple-pcc]
4. [OpenTitan][opentitan]
5. [Trusted Platform Module - Wikipedia][tpm]
6. [AMD SEV-SNP Firmware ABI Specification][amd-sev]
7. [Intel Trust Domain Extensions][intel-tdx]

[redhat-cc-attestation]: https://www.redhat.com/en/blog/learn-about-confidential-computing-attestation "Learn About Confidential Computing Attestation (REMITS) - Red Hat"
[chiang-tpm-keys]: https://ericchiang.github.io/post/tpm-keys/ "TPM Keys - Eric Chiang"
[apple-pcc]: https://security.apple.com/blog/expanding-pcc/ "Expanding Private Cloud Compute - Apple Security"
[opentitan]: https://opentitan.org/ "OpenTitan"
[tpm]: https://en.wikipedia.org/wiki/Trusted_Platform_Module "Trusted Platform Module - Wikipedia"
[amd-sev]: https://www.amd.com/system/files/TechDocs/56860.pdf "AMD SEV-SNP Firmware ABI Specification"
[intel-tdx]: https://www.intel.com/content/www/us/en/developer/tools/trust-domain-extensions/overview.html "Intel Trust Domain Extensions"
