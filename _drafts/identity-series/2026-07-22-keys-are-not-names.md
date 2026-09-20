---
title:  "Keys are not names"
series: "Identity, Part 2"
series_url: "/programming/identity-series-intro.html"
category: programming
date: 2026-07-22
---

> This is Part 2 of a six-part [series on identity](/programming/identity-series-intro.html).
>
> 1. **[Naming and binding](/programming/naming-and-binding.html)** — names stay put, bindings move. Saltzer's lens, from the ARPANET to Kubernetes to PCIe.
> 2. **Keys are not names** — what cryptography can say about who, and why anyone bothers with names at all.
> 3. **[Hosts](/programming/identity-of-hosts.html)** — DNS, X.509 and the Web PKI: forty years of binding names to keys, and the anchors it bottoms out in.
> 4. **[Humans](/programming/identity-of-humans.html)** — accounts, the trusted third party from Kerberos to OIDC, and sessions.
> 5. **[Workloads and hardware](/programming/identity-of-workloads.html)** — secret zero, SPIFFE, federated CI identity, and attestation.
> 6. **[Binding without a CA](/programming/binding-without-a-ca.html)** — first use, webs of trust, transparency logs, and petnames.

The [crypto series](/programming/crypto-series-intro.html) is careful to say that a secure channel tells you "I know who you are and nobody else is listening." The first half of that sentence is a lie, or at least a shorthand. This article is about what the channel actually tells you, why that is not a name, and why we build names on top of it anyway.

- [What cryptography can say](#what-cryptography-can-say)
- [Three meanings of one word](#three-meanings-of-one-word)
- [Why names at all](#why-names-at-all)
- [SPKI drew the line in 1999](#spki-drew-the-line-in-1999)
- [Systems that stop at the key](#systems-that-stop-at-the-key)
- [Zooko's triangle](#zookos-triangle)
- [Three kinds of principal](#three-kinds-of-principal)
- [Four ways a binding gets written](#four-ways-a-binding-gets-written)
- [A binding is a signed statement](#a-binding-is-a-signed-statement)

## What cryptography can say

Every guarantee in the crypto series is relative to a key.

```text
AEAD tag verifies         produced by a holder of K, and unmodified since
signature verifies        produced by the holder of the private key for pk
handshake completes       the peer holds the private key for the certificate it sent
PAKE succeeds             the peer knows the password
```

Not one of those statements contains a name. A TLS handshake with `example.com` proves that the far end holds the private key matching the public key in a certificate. The certificate is what says `example.com`, and the certificate is not a cryptographic object. It is a signed *assertion*, made by a third party, that a particular key belongs to a particular name. Verifying the signature tells you the assertion was made by a holder of the CA's key. It tells you nothing about whether the assertion is true.

This is Saltzer's [binding table](/programming/naming-and-binding.html) again. The handshake resolves one binding — key → channel — and does it perfectly. The certificate is an entry in a different table, name → key, and cryptography's only role there is to make the entry tamper-evident. Who wrote the entry, whether they were entitled to, and whether it is still true, are not things a signature can tell you.

The threat model prologue already said this in one line: [a key is not a name](/programming/threat-model.html). The rest of this series is what follows from taking it seriously.

## Three meanings of one word

Part of why this gets blurred is that "authentication" is used for three things that live on three different layers.

**Message authentication.** A MAC or AEAD tag: these bytes were produced by a holder of K and not modified. Key-relative. Lives in [Cryptographic Primitives](/programming/crypto-primitives.html), and is data protection, not identity.

**Proof of possession.** A live party demonstrates it currently holds a key or secret: a signature over a challenge, a PAKE, the handshake signature over a transcript. Still key-relative. This is what [Proving You Hold a Key](/programming/authentication.html) is about, and it is the whole of what "authentication" means in a protocol specification.

**Binding.** This key belongs to that party. A certificate, a passkey registration, a `known_hosts` line, an attestation report. Not key-relative — it is the step that *introduces* a name — and it is the only one of the three that deserves the word "identity."

Karp's four steps put it the same way. **Identification** is "knowing whom to hold responsible"; **authentication** is "what allows a process to use permissions assigned to an identity." Authentication presupposes that an identity exists and has been tied to something the process can prove it holds. That tying is identification, and it is this series.

## Why names at all

If cryptography only ever deals in keys, and the [authorization series](/programming/capabilities.html) argues at length that authority can be attached directly to keys and references, why does anyone bother with names?

Three reasons, none of them cryptographic.

**Policy is written by humans.** "Let the finance team read this," "only `example.com` may set this cookie," "deploy from `main`." People state intentions in names. A system whose principals are 32-byte strings needs a layer that turns names into keys before any of those intentions can be evaluated, and that layer is a binding service. Object-capability systems escape this only where the human is not in the loop, which is a real and useful place but a bounded one.

**Responsibility attaches to people.** Karp's first step is "knowing whom to hold responsible for authorized actions." A key cannot be sued, fired, or asked to explain itself. If a system ever needs to answer "who did this" in a way that has consequences outside the system, something has to map from the key to a party in the world. This is also why the capabilities article concedes that capability systems lose *global* review: not because they lack accountability, but because their chains of responsibility end at keys rather than at names.

**Continuity across keys.** A person outlives every key they will ever hold. Keys leak, expire, get lost with the laptop, get rotated on a schedule. Something has to stay stable while the keys change underneath, and that something is by definition a name — in Saltzer's terms, the object one level above the binding that moves. A system with no names has no way to say "same Alice, new key" except by having the old key sign the new one, which fails precisely when you need it most: when the old key is gone.

That third reason is the deepest. Notice that it is exactly Saltzer's argument for why a service should not be named by the node it runs on. Names exist to be *the thing that does not change*.

## SPKI drew the line in 1999

The cleanest statement of where identity ends and authorization begins is in a standard almost nobody deployed. SPKI — Simple Public Key Infrastructure, [RFC 2693][rfc2693], by Ellison, Frantz, Lampson, Rivest, Thomas, and Ylönen — was the IETF's attempt to design a certificate format from scratch, having watched X.509 fail to deliver a global directory.

It split certificates into two kinds.

```text
name certificate           issuer says:  name N  ↔  key K
authorization certificate  issuer says:  key K  may do  A,  delegable or not,  until T
```

The first kind is what this series is about. The second kind is what the [authorization series](/programming/authorization-models.html) is about — it is a capability with a signature on it, and macaroons, biscuits, and OAuth access tokens are its descendants.

SPKI's thesis, stated bluntly in the RFC, is that most systems only need the second kind. The key *is* the principal. If a resource wants to know whether K may do A, the most direct answer is a chain of authorization certificates ending in K, and routing that question through a name — K is Alice, Alice is in Finance, Finance may do A — adds two bindings that can be wrong and a global naming authority nobody agreed on.

The name certificates it did keep came from SDSI, Rivest and Lampson's [Simple Distributed Security Infrastructure][sdsi], and they are deliberately *local*. There is no global `alice`. There is `K_bob's alice` — Bob's name for a key — and `K_bob's alice's bank`, a name resolved by following Bob's binding to Alice's key and then Alice's binding for "bank." Names are relative to a key, every principal runs its own name server, and there is no root. It is the petname idea from the [last article](/programming/binding-without-a-ca.html) in certificate form, thirty years early.

Why this matters here: SPKI is the fault line between this series and the next. Every time the authorization series says "identity is not authority," it is standing on SPKI's authorization certificates. Every time this series says "you need a name anyway," it is standing on SDSI's observation that names are fine as long as you know whose namespace you are in.

## Systems that stop at the key

The identity-less design is not a thought experiment. Some of the most reliable infrastructure on the internet never binds a key to a name at all.

**WireGuard.** A peer is a public key. The configuration file lists public keys and the addresses they are allowed to use. There are no certificates, no names, no CA. "Authentication" means the far end proved it holds the private key for one of the configured public keys, and that is the entire identity model. Rotating a peer's key means editing every other peer's config, which is Saltzer's collapsed-layer cost paid knowingly.

**SSH `authorized_keys`.** A file on the server listing public keys, each optionally restricted with `command=`, `from=`, `no-port-forwarding`. The server never learns who you are. It learns that you hold a listed key, and it grants that key whatever the line says. This is a capability list indexed by public key, with caveats — SPKI's authorization certificate rendered as a text file — and it has run the world's servers since 1995.

**Bitcoin addresses.** An address is a hash of a public key. Spending requires a signature under that key. There is no account, no name, no recovery. The design is pure SPKI: the key is the principal, and the ledger is a capability system whose only rule is possession.

**Self-certifying names.** Mazières's [SFS][sfs] (1999) put a hash of the server's public key *in the hostname*, so that resolving the name yields the key with no third party to trust. Tor's `.onion` addresses do the same: a v3 onion address is the public key, base32-encoded. Nothing binds name to key because the name *is* the key. These sit at one corner of the triangle below, and the cost is written on the label: nobody can remember a 56-character onion address.

Every one of these works, and every one of them pays for skipping the binding table in the same coin: key rotation is a rename, there is no recovery from key loss, and the moment a human needs to refer to a principal in conversation, a name gets invented out of band anyway — a comment in the config file, a contact entry, a bookmark.

## Zooko's triangle

Zooko Wilcox-O'Hearn's [2001 observation][zooko] is that a naming system can have at most two of three properties:

```text
human-meaningful     a person can remember and type it
secure               one name resolves to one key, and nobody else can claim it
decentralized        no single authority controls the namespace
```

Read the systems above against it. DNS is meaningful and secure (given the root and its delegates) but centralized. Onion addresses and Bitcoin addresses are secure and decentralized but not meaningful. Petnames and SDSI local names are meaningful and decentralized but not globally secure — my `alice` and your `alice` may be different keys.

The triangle is a statement about *bindings*, not about names. A meaningful, secure, decentralized name would need a binding from human words to keys that everyone agrees on and nobody controls. The [last article](/programming/binding-without-a-ca.html) looks at the systems that claimed to square it, and at what they actually traded away. For now the point is simpler: every identity system in this series chose a corner, and the choice is visible in what it does badly.

## Three kinds of principal

The internet binds keys to three kinds of thing, and the machinery differs enough that each gets its own article.

**Hosts.** The name is a DNS name. The binding service is the Web PKI: a certificate authority checks that you control the name (by DNS, in practice) and signs a certificate. The anchor is a root store shipped with the browser or OS. Forty years of history, in the [next article](/programming/identity-of-hosts.html).

**Humans.** The name is an account — a username at a service, an email address, a phone number. The binding service is a trusted third party the relying party has agreed to believe: a Kerberos KDC, a SAML IdP, an OpenID Connect issuer. The anchor is the issuer's key, fetched over a TLS connection, which means human identity at internet scale is built on top of host identity. The [humans article](/programming/identity-of-humans.html).

**Workloads.** The name is something like `spiffe://prod/payments` or `repo:org/app:ref:refs/heads/main`. The binding service is the platform that launched the workload, because only it knows what it launched. That regresses one layer at a time — the orchestrator vouches for the pod, the cloud vouches for the VM, the silicon vouches for the cloud — until it bottoms out in a hardware vendor's root and an attestation report. The [workloads article](/programming/identity-of-workloads.html).

Three principals, three binding services, three different anchors. And one shared shape.

## Four ways a binding gets written

Across all of them, a name→key binding only ever gets established in four ways. Real systems mix them.

**Configured.** Somebody typed it in. The root store in your browser, the peer list in a WireGuard config, the IdP's issuer URL in your app's settings. There is no chain to follow; this *is* the anchor. Every other method eventually reduces to one of these.

**Certified.** A third party you have a configured binding for signs the assertion. CAs, identity providers, attestation services, SSH certificate authorities. This is the internet's default, because it scales: one configured binding to the issuer covers every binding the issuer ever makes. It is also where the adversary goes, because compromising the issuer forges every binding at once.

**First use.** Bind whatever key shows up the first time, and alarm if it changes. SSH `known_hosts`, Signal safety numbers, passkey registration. It works when the first contact is unlikely to be attacked and the attacker cannot be present every time. It fails silently on exactly the connection you cannot verify.

**Audited.** Do not try to prevent bad bindings; make every binding public and let anyone check. Certificate Transparency, key transparency in WhatsApp and iMessage, the Go checksum database. Wrong bindings still happen. They cannot happen *quietly*.

The [last article](/programming/binding-without-a-ca.html) is about the second half of that list. The next three are mostly about the first half, and about what it cost to learn that certified bindings need auditing.

## A binding is a signed statement

One more thing to fix before the histories, because it makes them easier to read.

Every binding artifact in this series has the same shape, whatever it is called:

```text
issuer          who is asserting this, by key
subject         the name being bound
key             the key it is bound to
validity        from when, until when
purpose         what the binding may be used for
```

An X.509 certificate, a Kerberos ticket, a SAML assertion, an OIDC `id_token`, an SSH certificate, a SPIFFE SVID, a DNSSEC signature, a TPM quote — all of them are that table, serialized differently and signed by the issuer. The [Keys](/programming/keys.html) post in the crypto series calls this the grammar of a proof: who, when, what, what-for, bound-to-what. Reading a new identity system means asking which of those five it fills in and who gets to sign.

And every one of them is recursive. The issuer's key needs its own binding, which needs its own issuer, until the chain hits something *configured*. Where those chains terminate — the roots of trust — is where the next article ends, because that is where host identity really lives.

## References <!-- omit in toc -->

1. [RFC 2693: SPKI Certificate Theory - Ellison et al. (1999)][rfc2693]
2. [SDSI: A Simple Distributed Security Infrastructure - Rivest & Lampson (1996)][sdsi]
3. [From ABAC to ZBAC - Karp, Haury, Davis (2009)][karp-zbac]
4. [Self-certifying File System - Mazières (1999)][sfs]
5. [Names: Decentralized, Secure, Human-Meaningful: Choose Two - Zooko Wilcox-O'Hearn (2001)][zooko]
6. [WireGuard: Next Generation Kernel Network Tunnel - Donenfeld][wireguard]
7. [sshd AUTHORIZED_KEYS FILE FORMAT - OpenSSH][sshd-authorized]

[rfc2693]: https://www.rfc-editor.org/rfc/rfc2693 "RFC 2693: SPKI Certificate Theory"
[sdsi]: https://people.csail.mit.edu/rivest/sdsi11.html "SDSI: A Simple Distributed Security Infrastructure"
[karp-zbac]: https://shiftleft.com/mirrors/www.hpl.hp.com/techreports/2009/HPL-2009-30.pdf "From ABAC to ZBAC: The Evolution of Access Control Models"
[sfs]: https://pdos.csail.mit.edu/papers/sfs:sosp99.pdf "Separating key management from file system security (SFS)"
[zooko]: https://en.wikipedia.org/wiki/Zooko%27s_triangle "Zooko's triangle"
[wireguard]: https://www.wireguard.com/papers/wireguard.pdf "WireGuard: Next Generation Kernel Network Tunnel"
[sshd-authorized]: https://man.openbsd.org/sshd#AUTHORIZED_KEYS_FILE_FORMAT "sshd: AUTHORIZED_KEYS FILE FORMAT"
