---
title:  "Attestation Models"
category: programming
date: 2026-06-14
---

Redhat's REMITS model:
![image](/assets/attestation-models/remits-model.png)



## TPM

![image](/assets/attestation-models/remits-tpm.png)

TODO: figure out which of the 2 below diagrams is correct

![image](/assets/attestation-models/tpm-key-hierarchy-1.png)

![image](/assets/attestation-models/tpm-key-hierarchy-2.png)

## CVMs

### AMD

![image](/assets/attestation-models/remits-amd-sev.png)


### Intel DCAP

![image](/assets/attestation-models/intel-dcap-key-hierarchy.png)


In the REMITS model:
![image](/assets/attestation-models/remits-intel-dcap.png)

## Cloud Attestation of CVMs: to vTPM or not

Seems like vTPMs are more about the cloud provider decision, not the underlying hardware: Azure uses vTPM model whereas Google doesn't

### vTPM (Azure)



![image](/assets/attestation-models/azure-vtpm-two-run-chain.png)

In the first run, we use hardware-provided evidence against the cloud provider’s own attestation architecture (such as Microsoft Azure Attestation). If successful, this first run unlocks the secrets necessary to build a vTPM (e.g. from persistent storage). How this is done precisely appears to rely on proprietary, non open-source Microsoft software. The root of trust in that first run is in hardware, namely an AMD root key (ARK) in the current SEV instances.
![image](/assets/attestation-models/azure-vtpm-run1-amd-remits.png)

A second run will then start with the vTPM as a root of trust, and the secrets become accessible through the standard mechanisms specified for all TPMs, which we described above. Except for the root of trust being a vTPM instead of a physical TPM, the second run is otherwise equivalent.
![image](/assets/attestation-models/azure-vtpm-run2-remits.png)


### Real TPM (Google)

Main difference seems to be that Google's identity is completely independent from the hardware chain of trust, and needs to be verified independently?

![image](/assets/attestation-models/gcp-dual-pki-chains.png)

PKI #1 — Intel DCAP (left, guest evidence). Intel SGX/TDX root CA → PCK platform CA (Intel's provisioning service) → PCK cert bound to the platform's TCB level → TD quote carrying MRTD + RTMRs, signed by the Intel-provisioned quoting-enclave attestation key. This is the exact same direct Intel-rooted quote you get on paravisor-free GCP TDX — no Google software in the signing path. The RTMR event log is the structural analog of your "TPM event logs": it's the human-readable explanation of what the RTMR values mean, and the quote signs over the RTMRs that summarize it.

PKI #2 — Google Titan (right, platform evidence). Titan/Google root CA → per-Titan-chip identity cert (the unique keying material minted at chip manufacture) → host firmware report from first-instruction integrity (Titan held the AP in reset and verified the boot firmware before the very first instruction) → a machine-identity attestation asserting this physical box is in the fleet. The "fleet ledger" leaf is literally the append-only hardware ledger from the Apple quote you pasted; machine identity is checked against it.

# References

- https://www.redhat.com/en/blog/learn-about-confidential-computing-attestation
- https://ericchiang.github.io/post/tpm-keys/
- https://security.apple.com/blog/expanding-pcc/
