---
title:  "Workloads and hardware: secret zero and attestation"
series: "Identity, Part 5"
series_url: "/programming/identity-series-intro.html"
category: programming
date: 2026-07-25
---

> This is Part 5 of a six-part [series on identity](/programming/identity-series-intro.html).
>
> 1. **[Naming and binding](/programming/naming-and-binding.html)** — names stay put, bindings move. Saltzer's lens, from the ARPANET to Kubernetes to PCIe.
> 2. **[Keys are not names](/programming/keys-are-not-names.html)** — what cryptography can say about who, and why anyone bothers with names at all.
> 3. **[Hosts](/programming/identity-of-hosts.html)** — DNS, X.509 and the Web PKI: forty years of binding names to keys, and the anchors it bottoms out in.
> 4. **[Humans](/programming/identity-of-humans.html)** — accounts, the trusted third party from Kerberos to OIDC, and sessions.
> 5. **Workloads and hardware** — secret zero, SPIFFE, federated CI identity, and attestation.
> 6. **[Binding without a CA](/programming/binding-without-a-ca.html)** — first use, webs of trust, transparency logs, and petnames.

A human can type a password. A host has a DNS name someone registered. A workload — a process, a container, a VM, a CI job — has neither. It comes into existence with nothing, and the first question it faces is how to prove who it is to anyone. This article is about the answer the industry converged on, which is that *the thing that launched you knows who you are*, and about what happens when you follow that answer down through the orchestrator, the cloud, and the hypervisor until it reaches silicon.

- [Secret zero](#secret-zero)
- [The platform is the identity provider](#the-platform-is-the-identity-provider)
  - [Cloud instance identity](#cloud-instance-identity)
  - [Kubernetes service accounts](#kubernetes-service-accounts)
  - [SPIFFE](#spiffe)
- [Federation: the workload's issuer as an OIDC provider](#federation-the-workloads-issuer-as-an-oidc-provider)
  - [Sigstore: identity for code](#sigstore-identity-for-code)
- [When the platform is the adversary](#when-the-platform-is-the-adversary)
- [Attestation: the REMITS lens](#attestation-the-remits-lens)
- [TPM](#tpm)
- [Confidential VMs](#confidential-vms)
  - [AMD SEV-SNP](#amd-sev-snp)
  - [Intel TDX and DCAP](#intel-tdx-and-dcap)
- [Cloud attestation: to vTPM or not](#cloud-attestation-to-vtpm-or-not)
  - [vTPM (Azure)](#vtpm-azure)
  - [Dual PKI (Google)](#dual-pki-google)
- [What attestation binds](#what-attestation-binds)

## Secret zero

Every credential a workload holds was delivered to it somehow. A database password in an environment variable, a cloud key in a config file, a certificate mounted into a container. Each one was put there by something that decided this workload deserved it — and *that* decision needed to identify the workload. Push the question back one step at a time and you reach the credential that unlocks all the others, and you have to explain how it got there without a credential to authorize it.

This is **secret zero**, and it has exactly one honest solution. Some party that already trusts itself has to observe the workload being created and vouch for it, using facts about the workload it can verify without asking the workload: what image it runs, which node it is on, which account launched it. Identity for workloads is not something the workload proves. It is something the platform *asserts*, in the same three-party shape the [humans article](/programming/identity-of-humans.html#the-trusted-third-party) found for people.

The whole history below is a sequence of platforms taking on that job, each one delegating to the one beneath it.

## The platform is the identity provider

### Cloud instance identity

AWS added IAM roles for EC2 in 2012: attach a role to an instance, and any process on it can fetch temporary credentials from the **instance metadata service** at `169.254.169.254` with an unauthenticated HTTP GET. The VM is the principal, the hypervisor's knowledge of which VM is asking is the binding, and the credentials rotate automatically. The other clouds shipped the same design.

Notice what identifies the workload: the ability to reach an address. That is an attachment-point name doing a principal's job, the [first article's](/programming/naming-and-binding.html#turning-the-lens-on-keys) recurring mistake, and it failed accordingly. Any code on the instance that could be made to issue an HTTP request to an attacker-chosen URL — server-side request forgery — could fetch the instance's credentials. The 2019 Capital One breach worked this way, and [IMDSv2][imdsv2] (November 2019) responded by requiring a `PUT` to obtain a session token first, with a default hop limit of one so that forwarded requests from containers or proxies fail. The identity still comes from *being the VM*; the change narrowed who on the VM could exercise it.

The metadata service also returns a signed **instance identity document** — instance ID, account, region, image — which is a certificate for the VM, signed by the cloud, verifiable by anyone with the cloud's public key. It is the first appearance in this article of the pattern that everything below refines: the launcher signs a statement about what it launched.

### Kubernetes service accounts

Kubernetes has the same problem one layer up. A pod needs to call the API server, and other pods, and it started with the same shortcut: a long-lived bearer token generated at service-account creation, stored in a Secret, and mounted into every pod. Tokens never expired, were not bound to any pod, and were valid anywhere they were presented.

**Bound service account tokens** (beta in 1.12, GA in 1.20) fixed each of those. The kubelet requests a token from the API server on the pod's behalf via `TokenRequest`; the token is a JWT with an expiry measured in hours, an `aud` naming who may accept it, and claims binding it to a specific pod UID so that it dies with the pod. Since 1.24 the legacy secrets are no longer created by default.

Look at who wrote the binding. The kubelet observed the pod being created and asked the API server to certify it; the API server signed a statement about the pod's identity. Neither asked the pod anything. The pod's identity is a fact the platform knows because the platform *made* the pod.

### SPIFFE

The Secure Production Identity Framework for Everyone ([SPIFFE][spiffe], a CNCF project since 2018) generalizes this into an identity standard that is not tied to one orchestrator or one cloud.

A workload's name is a **SPIFFE ID**, a URI like `spiffe://prod.example.com/payments/api`. The scheme names a **trust domain**, and everything under it is a path the operator chooses. The binding is an **SVID** — SPIFFE Verifiable Identity Document — which is either an X.509 certificate with the SPIFFE ID in `subjectAltName` or a JWT with it in `sub`, short-lived and rotated automatically. The trust domain's root keys form a **bundle** that relying parties configure once.

The interesting part is how SPIRE, the reference implementation, decides what to issue, because it is secret zero solved by stacking:

```text
node attestation        the SPIRE server verifies the node using something the
                        platform already vouches for: a cloud instance identity
                        document, a Kubernetes node token, a TPM

workload attestation    the SPIRE agent on that node identifies a connecting
                        process using kernel-observed facts: its PID, its cgroup,
                        the pod and service account the container runtime says
                        it belongs to, its binary's hash

registration            an operator has stated which (node selectors, workload
                        selectors) map to which SPIFFE ID
```

The workload connects to the agent over a Unix domain socket — reachable only from the node, which is the [enforcement article's](/programming/authority-enforcement.html) unnameability doing identity work — and receives an SVID for whichever ID its selectors match. It never presents a credential. Its identity is entirely a function of facts observed about it from outside.

Service meshes are where most people meet SPIFFE without knowing it. Istio issues X.509 SVIDs to every sidecar and uses them for mutual TLS between services, so `payments` can be sure it is talking to `ledger` because the mesh's CA said so, having verified with the API server which pod the sidecar belongs to. The Web PKI's shape, inside one cluster, with the platform as CA.

## Federation: the workload's issuer as an OIDC provider

Every one of the systems above issues signed statements about workloads. The obvious next step is for one platform to trust another's statements, and the industry did it by reusing the human protocol.

The Kubernetes API server has been an [OpenID Connect issuer][k8s-sa-issuer] since 1.21: it publishes `/.well-known/openid-configuration` and a JWKS, so any relying party that speaks OIDC can verify its service account tokens. GitHub Actions added [OIDC tokens][gha-oidc] in 2021: a job can request a JWT whose claims include the repository, the workflow, the branch, and the event that triggered it, signed by GitHub. GitLab, CircleCI, Buildkite and the others followed.

On the receiving side, the clouds added **workload identity federation**: configure AWS, GCP or Azure to trust GitHub's issuer, write a policy mapping claims to a role — `repo:acme/api` on `ref:refs/heads/main` may assume `deploy-prod` — and the job exchanges its OIDC token for cloud credentials that last minutes. No long-lived cloud key stored in the CI system. Nothing to leak.

This is the [humans article's](/programming/identity-of-humans.html#openid-connect) diagram with the nouns changed. GitHub is the identity provider; the job is the user; AWS is the relying party; the configured binding is GitHub's issuer URL and the claim-mapping policy. The `sub` is local to the issuer, as OIDC always intended, and the relying party keeps a table translating it. The protocol built for people turned out to be the protocol for machines, because the shape was never about people.

### Sigstore: identity for code

[Sigstore][sigstore] (2021) takes federation one step further and uses it to bind identity to *artifacts*. To sign a container image or a release, a developer or CI job authenticates to an OIDC issuer, presents the `id_token` to **Fulcio**, and receives a certificate binding that identity — an email address, or a GitHub workflow — to an ephemeral signing key, valid for ten minutes. They sign, and the signature and certificate are recorded in **Rekor**, an append-only transparency log. The key is discarded.

Every piece of the last two articles is in that flow. A CA (Fulcio) issuing a short-lived certificate on the strength of an OIDC assertion. A transparency log so that misissuance is public. And a name — `repo:acme/api:ref:refs/heads/main` — that a verifier can write a policy about, which is the reason names exist at all. What Sigstore removed was the long-lived signing key, and with it the key-management problem that had kept most software unsigned.

## When the platform is the adversary

Everything above trusts the platform. The kubelet vouches for the pod, the cloud vouches for the VM, the CI provider vouches for the job. That is fine when the platform is yours, or when your threat model stops at the cloud provider's front door.

The [threat model prologue](/programming/threat-model.html) argues that the frontier has moved past that door. The live question is the *authenticated but hostile* counterparty — and for a workload, the most powerful counterparty is the infrastructure it runs on. A hypervisor can read a VM's memory. A cloud operator can snapshot a disk. If the platform's word is the only binding a workload has, the platform can forge it.

Attestation is the answer: get the vouching done by something *below* the platform, with a key the platform cannot access, that measures what actually booted. The vouching party becomes the silicon vendor, and the binding it signs is not "this is pod X" but "this key lives inside hardware that is running software with hash H."

## Attestation: the REMITS lens

Proving that a key really lives behind a hardware root — rather than just claiming to — is **attestation**. Red Hat's REMITS model is a clean lens for reading any attestation scheme, hardware or cloud, because it separates the roles that every scheme has to fill: a root that is trusted by configuration, evidence generated by the hardware, a measurement of what is running, a verifier that checks the evidence against a policy, and a secret or credential released only on success.

![image](/assets/crypto-series/roots-of-trust-and-attestation/remits-model.png)

Read against this series: attestation is a certified binding, and the issuer is the chip vendor. What differs from a CA is what the subject is. A certificate binds a *name* to a key. An attestation report binds a *measurement* to a key — the hash of the firmware, kernel, and initial image that booted — and turning that hash back into a name someone can write a policy about ("this is our sealed release build") is the verifier's job.

## TPM

The Trusted Platform Module is the oldest and most widely deployed attestation root, and every scheme after it borrows its vocabulary.

![image](/assets/crypto-series/roots-of-trust-and-attestation/remits-tpm.png)

The TPM ships with an **endorsement key** (EK) whose certificate is signed by the manufacturer — the configured binding at the bottom of the chain. Because the EK is a decryption key rather than a signing key, the TPM creates an **attestation key** (AK) and proves to a verifier that the AK lives in the same TPM as a certified EK. The AK then signs **quotes**: the current values of the platform configuration registers (PCRs), which the firmware and bootloader have extended with hashes of every stage they loaded. The event log that accompanies a quote is the human-readable explanation of how the PCRs got their values, and the quote signs the summary.

TODO: figure out which of the two diagrams below is correct.

![image](/assets/crypto-series/roots-of-trust-and-attestation/tpm-key-hierarchy-1.png)

![image](/assets/crypto-series/roots-of-trust-and-attestation/tpm-key-hierarchy-2.png)

## Confidential VMs

Confidential VMs put the root inside the CPU instead of on a separate chip, and extend the guarantee from "this is what booted" to "and the hypervisor cannot read it." The chain has the same shape.

### AMD SEV-SNP

![image](/assets/crypto-series/roots-of-trust-and-attestation/remits-amd-sev.png)

AMD's root key (ARK) signs a signing key (ASK), which signs a per-chip versioned key (VCEK). The VCEK signs attestation reports containing the launch measurement of the guest and a field the guest can fill in — typically the hash of a key it just generated, so that the report binds the measured software to a key the guest holds.

### Intel TDX and DCAP

![image](/assets/crypto-series/roots-of-trust-and-attestation/intel-dcap-key-hierarchy.png)

Intel's chain runs from an Intel root CA through a provisioning CA to a per-platform PCK certificate bound to the platform's TCB level, and from there to a quoting enclave whose attestation key signs quotes over the trust domain's measurement registers (`MRTD` and the runtime `RTMR`s) plus the guest-supplied `REPORTDATA`. DCAP is the packaging that lets a verifier check all of this without calling Intel at attestation time.

![image](/assets/crypto-series/roots-of-trust-and-attestation/remits-intel-dcap.png)

## Cloud attestation: to vTPM or not

Cloud providers have to expose this to tenants, and they made different choices about whether to put a virtual TPM in the path. The choice is the provider's, not the hardware's: Azure uses a vTPM model on the same AMD silicon that Google exposes directly.

### vTPM (Azure)

![image](/assets/crypto-series/roots-of-trust-and-attestation/azure-vtpm-two-run-chain.png)

In the first run, hardware-provided evidence is checked against the cloud provider's own attestation service (Microsoft Azure Attestation). If it passes, that run unlocks the secrets needed to build a vTPM, for example from persistent storage. How this is done precisely appears to rely on proprietary, closed-source Microsoft software. The root of trust in that first run is in hardware — the AMD root key on current SEV instances.

![image](/assets/crypto-series/roots-of-trust-and-attestation/azure-vtpm-run1-amd-remits.png)

A second run then starts with the vTPM as its root of trust, and secrets become accessible through the standard TPM mechanisms described above. Except for the root being a vTPM rather than a physical one, the second run is otherwise equivalent.

![image](/assets/crypto-series/roots-of-trust-and-attestation/azure-vtpm-run2-remits.png)

### Dual PKI (Google)

Google's approach keeps the platform's identity completely independent from the hardware chain of trust, so a verifier checks two chains.

![image](/assets/crypto-series/roots-of-trust-and-attestation/gcp-dual-pki-chains.png)

**PKI 1 — Intel DCAP (guest evidence).** Intel root CA → PCK platform CA → PCK certificate bound to the platform's TCB level → TD quote carrying `MRTD` and the `RTMR`s, signed by the Intel-provisioned quoting-enclave attestation key. This is the same direct Intel-rooted quote you get on paravisor-free GCP TDX — no Google software in the signing path. The RTMR event log is the structural analog of a TPM event log: the human-readable explanation of what the register values mean, with the quote signing over the registers that summarize it.

**PKI 2 — Google Titan (platform evidence).** Titan/Google root CA → per-Titan-chip identity certificate, minted at chip manufacture → host firmware report from first-instruction integrity, where Titan held the application processor in reset and verified the boot firmware before its first instruction → a machine-identity attestation asserting that this physical box is in the fleet. The fleet-ledger leaf is the same kind of append-only hardware ledger Apple describes for [Private Cloud Compute][apple-pcc]: machine identity is checked against a log of every machine that was ever manufactured into the fleet.

## What attestation binds

Attestation closes the regression that opened this article. Secret zero asked how a workload gets its first credential; the answer was that its launcher vouches for it; and the objection was that the launcher might lie. Attestation moves the vouching to a key the launcher cannot reach, held by silicon, certified by the vendor at manufacture.

But it is still a binding, with all of Saltzer's properties. The subject is a measurement, which is the least human-meaningful name in this series — secure and decentralized in [Zooko's](/programming/keys-are-not-names.html#zookos-triangle) terms, and useless to a policy author until a verifier maps it to "our release build." The anchor is the vendor's root, configured out of band exactly like a CA root, and a compromised or coerced vendor forges every attestation at once. And the lifetime question is real: a measurement is bound at boot, and a workload that is compromised at runtime still produces the same quote, which is why attestation is a statement about what *started* and not about what is *happening*.

That is the whole series so far in one object. A signed statement, from an issuer you configured, binding a key to a name, for a while. Hosts get it from a CA, humans from an identity provider, workloads from their platform, and platforms from their silicon. The [last article](/programming/binding-without-a-ca.html) asks what happens when there is no issuer you are willing to configure.

## References <!-- omit in toc -->

1. [Defense in depth: IMDSv2 - AWS Security Blog][imdsv2]
2. [Managing Service Accounts - Kubernetes][k8s-sa]
3. [Service Account Issuer Discovery - Kubernetes][k8s-sa-issuer]
4. [SPIFFE Overview][spiffe]
5. [About security hardening with OpenID Connect - GitHub Actions][gha-oidc]
6. [Sigstore][sigstore]
7. [Learn About Confidential Computing Attestation (REMITS) - Red Hat][redhat-cc-attestation]
8. [TPM Keys - Eric Chiang][chiang-tpm-keys]
9. [Expanding Private Cloud Compute - Apple Security][apple-pcc]
10. [OpenTitan][opentitan]

[imdsv2]: https://aws.amazon.com/blogs/security/defense-in-depth-open-firewalls-reverse-proxies-ssrf-vulnerabilities-ec2-instance-metadata-service/ "Defense in depth: open firewalls, reverse proxies, SSRF vulnerabilities, EC2 instance metadata service"
[k8s-sa]: https://kubernetes.io/docs/reference/access-authn-authz/service-accounts-admin/ "Managing Service Accounts - Kubernetes"
[k8s-sa-issuer]: https://kubernetes.io/docs/tasks/configure-pod-container/configure-service-account/#serviceaccount-token-volume-projection "Service account token volume projection - Kubernetes"
[spiffe]: https://spiffe.io/docs/latest/spiffe-about/overview/ "SPIFFE Overview"
[gha-oidc]: https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect "About security hardening with OpenID Connect - GitHub Docs"
[sigstore]: https://www.sigstore.dev/ "Sigstore"
[redhat-cc-attestation]: https://www.redhat.com/en/blog/learn-about-confidential-computing-attestation "Learn About Confidential Computing Attestation (REMITS) - Red Hat"
[chiang-tpm-keys]: https://ericchiang.github.io/post/tpm-keys/ "TPM Keys - Eric Chiang"
[apple-pcc]: https://security.apple.com/blog/expanding-pcc/ "Expanding Private Cloud Compute - Apple Security"
[opentitan]: https://opentitan.org/ "OpenTitan"
