---
title:  "Roots of Trust & Attestation"
series: "Applied Crypto, Part 5"
series_url: "/programming/crypto-series-intro.html"
category: programming
date: 2026-06-10
---

The last post, and where the *right-party* arm of the series bottoms out. Every chain of trust we've followed — a TLS cert, a passkey, a session key — terminates at some anchor you trusted *before* the connection began. This post is about those anchors (roots of trust), the mechanism that proves a key really lives behind one (attestation), and it closes with a series capstone: everything a secure channel still doesn't give you.

## What ultimately authenticates a key?

A channel's session keys come out of an ephemeral DH exchange — but what stops an attacker from just running that exchange with you themselves? The answer is that one long-term key in the handshake is *authenticated*, and that authentication chains upward until it hits something you trusted before the connection began.

How is a channel's ephemeral session key ultimately authenticated?

![image](/assets/roots-of-trust-and-attestation/session-key-authentication-chain.png)

There are two chains to the same destination here. The left one is the familiar Web PKI: the leaf cert binds a domain to a key, signed by an intermediate, signed by a Root CA that's baked into your browser. The right one is hardware attestation: an Intel SGX root signs an Intel-issued attestation key, which signs a TDX quote whose `REPORTDATA` commits to the session key's hash. Either way, the session key is only as trustworthy as the out-of-band anchor at the top of its chain.

## Root of Trust

So where do those anchors come from? They're never derived — they're *configured*, out of band, by software vendors, OS installs, and DHCP.

![image](/assets/roots-of-trust-and-attestation/roots-of-trust-out-of-band.png)

Others that we could include:

**CT log keys.** Modern Chrome and Safari refuse certs that don't carry Signed Certificate Timestamps from a list of trusted Certificate Transparency logs (currently ~5-6 active). The public keys of those logs are baked into browser source code, just like the CA roots. Without them, the cert chain alone isn't sufficient for trust.

**NTP server addresses + (optionally) NTS roots.** Cert validity windows are time-bounded, so every cert check depends on a clock that's roughly right. NTP server IPs arrive via DHCP or hardcoded fallback (`pool.ntp.org`, `time.apple.com`). Plain NTP is unauthenticated; Network Time Security adds a TLS-rooted chain on top, which means it ultimately leans on Root CAs anyway.

**OS and package signing keys.** The browser binary itself was installed by `apt`/`dnf`/`pacman`/the Mac App Store/Windows Update, each with their own keyring (Debian release key, Apple notarization key, Microsoft Authenticode roots). Whatever signed `firefox.deb` is upstream of every Root CA decision Firefox makes.

**UEFI Secure Boot Platform Key.** The firmware-level root that authorized booting the OS that's running the browser. Burned in by the OEM at manufacture, with Microsoft's KEK enrolled as the de facto standard for x86. This is the deepest software-level trust anchor on a typical machine — everything else descends from it.

**Other hardware vendor roots.** AMD's SEV-SNP root, Apple's Secure Enclave root, ARM's TrustZone roots, every TPM manufacturer's EK CA. Same pattern as Intel SGX Root, just different silicon.

And tying back to where the conversation started: **blockchain genesis hashes** are the same kind of object. Ethereum's chain is defined by a specific genesis block whose hash is hardcoded in clients; "which chain is the real chain" is answered by `apt-get install geth` shipping that constant. Self-certifying keys at the application layer, sure, but the *configuration* that picks one chain over a fork lives in the same out-of-band place as the Root CA bundle.

## Attestation: the REMITS lens

Proving that a key really lives behind one of those hardware roots — rather than just claiming to — is **attestation**. Red Hat's REMITS model is a clean lens for reading any attestation scheme, hardware or cloud.

Redhat's REMITS model:
![image](/assets/roots-of-trust-and-attestation/remits-model.png)



## TPM

![image](/assets/roots-of-trust-and-attestation/remits-tpm.png)

TODO: figure out which of the 2 below diagrams is correct

![image](/assets/roots-of-trust-and-attestation/tpm-key-hierarchy-1.png)

![image](/assets/roots-of-trust-and-attestation/tpm-key-hierarchy-2.png)

## CVMs

### AMD

![image](/assets/roots-of-trust-and-attestation/remits-amd-sev.png)


### Intel DCAP

![image](/assets/roots-of-trust-and-attestation/intel-dcap-key-hierarchy.png)


In the REMITS model:
![image](/assets/roots-of-trust-and-attestation/remits-intel-dcap.png)

## Cloud Attestation of CVMs: to vTPM or not

Seems like vTPMs are more about the cloud provider decision, not the underlying hardware: Azure uses vTPM model whereas Google doesn't

### vTPM (Azure)



![image](/assets/roots-of-trust-and-attestation/azure-vtpm-two-run-chain.png)

In the first run, we use hardware-provided evidence against the cloud provider’s own attestation architecture (such as Microsoft Azure Attestation). If successful, this first run unlocks the secrets necessary to build a vTPM (e.g. from persistent storage). How this is done precisely appears to rely on proprietary, non open-source Microsoft software. The root of trust in that first run is in hardware, namely an AMD root key (ARK) in the current SEV instances.
![image](/assets/roots-of-trust-and-attestation/azure-vtpm-run1-amd-remits.png)

A second run will then start with the vTPM as a root of trust, and the secrets become accessible through the standard mechanisms specified for all TPMs, which we described above. Except for the root of trust being a vTPM instead of a physical TPM, the second run is otherwise equivalent.
![image](/assets/roots-of-trust-and-attestation/azure-vtpm-run2-remits.png)


### Real TPM (Google)

Main difference seems to be that Google's identity is completely independent from the hardware chain of trust, and needs to be verified independently?

![image](/assets/roots-of-trust-and-attestation/gcp-dual-pki-chains.png)

PKI #1 — Intel DCAP (left, guest evidence). Intel SGX/TDX root CA → PCK platform CA (Intel's provisioning service) → PCK cert bound to the platform's TCB level → TD quote carrying MRTD + RTMRs, signed by the Intel-provisioned quoting-enclave attestation key. This is the exact same direct Intel-rooted quote you get on paravisor-free GCP TDX — no Google software in the signing path. The RTMR event log is the structural analog of your "TPM event logs": it's the human-readable explanation of what the RTMR values mean, and the quote signs over the RTMRs that summarize it.

PKI #2 — Google Titan (right, platform evidence). Titan/Google root CA → per-Titan-chip identity cert (the unique keying material minted at chip manufacture) → host firmware report from first-instruction integrity (Titan held the AP in reset and verified the boot firmware before the very first instruction) → a machine-identity attestation asserting this physical box is in the fleet. The "fleet ledger" leaf is literally the append-only hardware ledger from the Apple quote you pasted; machine identity is checked against it.

## Capstone: what a secure channel still doesn't give you

We've now walked the whole stack — primitives, channels, keys, authentication, and the roots everything anchors in. Worth ending on the humbling part: a secure channel is the *easy* part. Analogously to https://thume.ca/2020/05/17/pipes-kill-productivity/, we can describe cryptographic pipes (secure channels) as:
- Rootless. A secure channel reduces "trust the network" to "trust a key" but never eliminates trust — somebody has to anchor the key out of band. PKI, TOFU, hardcoded fingerprints, DNSSEC, blockchain registries, key transparency logs. This is the exact same bootstrap problem Kademlia has, just shifted into crypto-space. Every system reinvents it. (This bootstrap problem is exactly the roots-of-trust section above.)
- Unauthorized. Authentication answers "who"; it doesn't answer "may they". You will write the authz layer. Every time. Capabilities (macaroons, biscuits), ACLs, role tables, OPA — all of it lives above the channel.
- Nameless. Public keys aren't names. You will build, or import, a naming layer (Zooko's triangle applies: secure / human-meaningful / decentralized — pick two). Petnames, ENS, DNS-over-something, .onion vanity, GPG WoT. All ad hoc, none portable.
- Stale. Keys leak, certs expire, devices get lost, employees quit. You need rotation, revocation, and a story for "this was Alice and now isn't." CRL/OCSP, short-lived certs (SPIFFE), key transparency, ratchets. The state machine for "current trust" is its own distributed system.
- Brittle (cryptographically). Algorithms get deprecated faster than your dependency tree updates. SHA-1, RC4, MD5, soon RSA-2048 and ECDH against a quantum adversary. Cipher agility is the "Mismatched" problem on hard mode — you can't just add a JSON field, you have to renegotiate primitives without opening a downgrade attack. (See the negotiation-as-footgun discussion in [Key Exchange & Secure Channels](/programming/secure-channels.html) — agility is exactly the attack surface TLS keeps getting burned by.)
- Leaky. The channel encrypts content but not envelope: who talks to whom, when, how often, how much. Traffic analysis, timing, sizes, fingerprintable handshakes (JA3/JA4). Padding, cover traffic, mixnets — and each of those is its own pile of work.
- Replayable. A single channel handles ordering inside its lifetime, but the moment your message escapes the channel (queued, logged, persisted, cross-session) freshness becomes your problem again. Nonces, timestamps, sequence numbers, idempotency keys — all rebuilt at the app layer.
- Pairwise. Secure channels are 2-party by construction. Groups need entirely different primitives (MLS, Signal Sender Keys, fan-out + per-member channels). Naively gluing N pairwise channels together gets you O(N) keys and zero forward secrecy guarantees as a group.
- Oracular. Composing crypto creates oracles. Padding oracles, downgrade oracles, error-message oracles, timing oracles at trust boundaries. Hume's "untrusted" said validate your inputs; crypto pipes say also don't let your error messages distinguish failure modes, which is much harder to remember.
- Non-committing. AEAD proves "this ciphertext wasn't tampered with" — not "this is the only key that decrypts it." AES-GCM and ChaCha20-Poly1305 let an attacker craft one ciphertext that verifies under multiple keys, which is the engine behind partitioning-oracle attacks (they broke Shadowsocks) and a footgun for password-based, multi-recipient, and key-rotation schemes. You need a committing AEAD; the gap is spelled out in [Cryptographic Primitives](/programming/crypto-primitives.html).
- Misusable. The APIs are foot-guns. Reuse a GCM nonce → catastrophic. Use ECB → meme. Roll your own → don't. "Misuse-resistant cryptography" exists as a research area precisely because of how much code paying the crypto tax still gets it wrong.
- Side-channeled. Even a correct implementation leaks through cache timing, branch prediction, power, EM. Constant-time code is a discipline most app developers never learn and most languages don't help with.
- Metadata-stateful. Sessions, ratchets, resumption tickets, 0-RTT early-data caches — they all carry state that has to survive crashes, sync across replicas, and not get rolled back (else replay). Your "stateless web service" has a stateful crypto layer underneath whether you want it or not.

Secure channel ≈ "I know who you are and nobody else is listening." Everything that gives that fact operational meaning — multiplexing, negotiating, routing, budgeting, naming, authorizing, scoring, recovering — lives above it.

> Hume's was "try really hard not to write a distributed system." Yours could be "try really hard not to build your own crypto layer — but also notice that even using a great off-the-shelf one (TLS, Noise, libp2p, Signal) only pays down maybe three of these dimensions. The rest are yours, forever, and the industry pretends they aren't." That framing — "the secure channel is the easy part; the productivity tax is everything around it" — would land hard.

## References <!-- omit in toc -->

1. [Learn About Confidential Computing Attestation (REMITS) - Red Hat][redhat-cc-attestation]
2. [TPM Keys - Eric Chiang][chiang-tpm-keys]
3. [Expanding Private Cloud Compute - Apple Security][apple-pcc]
4. [OpenTitan][opentitan]
5. [Pipes Kill Productivity - Tristan Hume][thume-pipes]

[redhat-cc-attestation]: https://www.redhat.com/en/blog/learn-about-confidential-computing-attestation "Learn About Confidential Computing Attestation (REMITS) - Red Hat"
[chiang-tpm-keys]: https://ericchiang.github.io/post/tpm-keys/ "TPM Keys - Eric Chiang"
[apple-pcc]: https://security.apple.com/blog/expanding-pcc/ "Expanding Private Cloud Compute - Apple Security"
[opentitan]: https://opentitan.org/ "OpenTitan"
[thume-pipes]: https://thume.ca/2020/05/17/pipes-kill-productivity/ "Pipes Kill Productivity - Tristan Hume"
