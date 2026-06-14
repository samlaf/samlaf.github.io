# Secure Channels Root of Trust

How is a channel's ephemeral session key ultimately authenticated?

![image](https://hackmd.io/_uploads/Sy490U4yMl.png)

## Root of Trust

![image](https://hackmd.io/_uploads/Hy_iWvNkzx.png)

Others that we could include:

**CT log keys.** Modern Chrome and Safari refuse certs that don't carry Signed Certificate Timestamps from a list of trusted Certificate Transparency logs (currently ~5-6 active). The public keys of those logs are baked into browser source code, just like the CA roots. Without them, the cert chain alone isn't sufficient for trust.

**NTP server addresses + (optionally) NTS roots.** Cert validity windows are time-bounded, so every cert check depends on a clock that's roughly right. NTP server IPs arrive via DHCP or hardcoded fallback (`pool.ntp.org`, `time.apple.com`). Plain NTP is unauthenticated; Network Time Security adds a TLS-rooted chain on top, which means it ultimately leans on Root CAs anyway.

**OS and package signing keys.** The browser binary itself was installed by `apt`/`dnf`/`pacman`/the Mac App Store/Windows Update, each with their own keyring (Debian release key, Apple notarization key, Microsoft Authenticode roots). Whatever signed `firefox.deb` is upstream of every Root CA decision Firefox makes.

**UEFI Secure Boot Platform Key.** The firmware-level root that authorized booting the OS that's running the browser. Burned in by the OEM at manufacture, with Microsoft's KEK enrolled as the de facto standard for x86. This is the deepest software-level trust anchor on a typical machine — everything else descends from it.

**Other hardware vendor roots.** AMD's SEV-SNP root, Apple's Secure Enclave root, ARM's TrustZone roots, every TPM manufacturer's EK CA. Same pattern as Intel SGX Root, just different silicon.

And tying back to where the conversation started: **blockchain genesis hashes** are the same kind of object. Ethereum's chain is defined by a specific genesis block whose hash is hardcoded in clients; "which chain is the real chain" is answered by `apt-get install geth` shipping that constant. Self-certifying keys at the application layer, sure, but the *configuration* that picks one chain over a fork lives in the same out-of-band place as the Root CA bundle.

## Rootless unauthorized nameless stale brittle leaky replayable pairwise oracular misusable pipes kill productivity

Analogously to https://thume.ca/2020/05/17/pipes-kill-productivity/, we can describe cryptographic pipes (secure channels) as:
- Rootless. A secure channel reduces "trust the network" to "trust a key" but never eliminates trust — somebody has to anchor the key out of band. PKI, TOFU, hardcoded fingerprints, DNSSEC, blockchain registries, key transparency logs. This is the exact same bootstrap problem Kademlia has, just shifted into crypto-space. Every system reinvents it.
- Unauthorized. Authentication answers "who"; it doesn't answer "may they". You will write the authz layer. Every time. Capabilities (macaroons, biscuits), ACLs, role tables, OPA — all of it lives above the channel.
- Nameless. Public keys aren't names. You will build, or import, a naming layer (Zooko's triangle applies: secure / human-meaningful / decentralized — pick two). Petnames, ENS, DNS-over-something, .onion vanity, GPG WoT. All ad hoc, none portable.
- Stale. Keys leak, certs expire, devices get lost, employees quit. You need rotation, revocation, and a story for "this was Alice and now isn't." CRL/OCSP, short-lived certs (SPIFFE), key transparency, ratchets. The state machine for "current trust" is its own distributed system.
- Brittle (cryptographically). Algorithms get deprecated faster than your dependency tree updates. SHA-1, RC4, MD5, soon RSA-2048 and ECDH against a quantum adversary. Cipher agility is the "Mismatched" problem on hard mode — you can't just add a JSON field, you have to renegotiate primitives without opening a downgrade attack.
- Leaky. The channel encrypts content but not envelope: who talks to whom, when, how often, how much. Traffic analysis, timing, sizes, fingerprintable handshakes (JA3/JA4). Padding, cover traffic, mixnets — and each of those is its own pile of work.
- Replayable. A single channel handles ordering inside its lifetime, but the moment your message escapes the channel (queued, logged, persisted, cross-session) freshness becomes your problem again. Nonces, timestamps, sequence numbers, idempotency keys — all rebuilt at the app layer.
- Pairwise. Secure channels are 2-party by construction. Groups need entirely different primitives (MLS, Signal Sender Keys, fan-out + per-member channels). Naively gluing N pairwise channels together gets you O(N) keys and zero forward secrecy guarantees as a group.
- Oracular. Composing crypto creates oracles. Padding oracles, downgrade oracles, error-message oracles, timing oracles at trust boundaries. Hume's "untrusted" said validate your inputs; crypto pipes say also don't let your error messages distinguish failure modes, which is much harder to remember.
- Misusable. The APIs are foot-guns. Reuse a GCM nonce → catastrophic. Use ECB → meme. Roll your own → don't. "Misuse-resistant cryptography" exists as a research area precisely because of how much code paying the crypto tax still gets it wrong.
- Side-channeled. Even a correct implementation leaks through cache timing, branch prediction, power, EM. Constant-time code is a discipline most app developers never learn and most languages don't help with.
- Metadata-stateful. Sessions, ratchets, resumption tickets, 0-RTT early-data caches — they all carry state that has to survive crashes, sync across replicas, and not get rolled back (else replay). Your "stateless web service" has a stateful crypto layer underneath whether you want it or not.

Secure channel ≈ "I know who you are and nobody else is listening." Everything that gives that fact operational meaning — multiplexing, negotiating, routing, budgeting, naming, authorizing, scoring, recovering — lives above it.

> Hume's was "try really hard not to write a distributed system." Yours could be "try really hard not to build your own crypto layer — but also notice that even using a great off-the-shelf one (TLS, Noise, libp2p, Signal) only pays down maybe three of these dimensions. The rest are yours, forever, and the industry pretends they aren't." That framing — "the secure channel is the easy part; the productivity tax is everything around it" — would land hard.

## The Changing Internet Threat Model

The history of internet security can be read as a steady migration of *where* the threat is assumed to live — from the wire, to identity binding, to the authenticated counterparty itself. Four moments mark the transitions.

### Dolev-Yao (1983): the saboteur on the wire

Dolev and Yao start in a world where public-key cryptography exists in principle but nobody knows how to *use* it safely. Their saboteur is on the network, can read everything passing through it, and can act as a legitimate participant in protocols. The open question of the era is foundational: can any protocol built from these primitives preserve secrecy at all, given an adversary with these capabilities? The threat model is maximally pessimistic about the channel and treats the protocol logic itself as the thing under test.

### Lowe's attack on Needham-Schroeder (1995): the punctuation mark

Lowe's attack is the result that reframes what "security" even means. He shows that even with perfect cryptography and perfect key binding, a *legitimate* participant — Mallory, with his own real key pair — can exploit the protocol's role structure to impersonate Alice to Bob, just by relaying messages Alice willingly sent him. The attack isn't about broken crypto or stolen identities; it's about the protocol logic failing to bind a message to the *role* its sender was playing. The lesson: the channel and the keys can be perfect, and the protocol can still be broken. Dangerous actors don't need to be on the wire; they can be sitting at the other end of an authenticated session.

### PKI deployment (1990s–2000s): operationalizing identity

The PKI wave operationalizes identity binding at scale — X.509, certificate authorities, the Web PKI. This closes the "is this really Bob's key" gap that Dolev-Yao had left as an exercise for protocol designers. In practice, this is the moment when "who am I talking to" stops being something each protocol has to solve from scratch and becomes infrastructure. Crucially, PKI solves *impersonation* — Mallory can no longer claim to be Alice — but it says nothing about whether the correctly-identified party at the other end is honest. The Lowe-style threat, where Mallory is genuinely Mallory and exploits the protocol from a legitimate role, is entirely untouched by PKI. The cost of PKI's success is that subsequent threat models start to *assume* identity binding works and turn their attention elsewhere, leaving the question of malicious-but-authenticated counterparties largely unaddressed.

### RFC 3552 (2003): codifying the channel attacker

By the time the IETF codifies its working threat model, the assumed adversary has migrated almost entirely onto the channel. RFC 3552 explicitly stipulates that *endpoints are not compromised* and worries about an attacker who can read, drop, modify, and inject on the wire. The document's whole architecture of passive vs. active attacks, confidentiality vs. integrity, is organized around a wire-level adversary. It's worth being precise about what this assumption is doing: PKI did not eliminate the malicious-counterparty threat — it only eliminated impersonation. RFC 3552 handles the residual threat by *declaring it out of scope*, not by defending against it. PKI made that stipulation feel reasonable — if you know exactly who you're talking to, the residual worry shifts to the wire — but the stipulation itself is doing the work, not the cryptography. The Lowe-style threat never went away; it was simply set aside.

### Arkko's proposal (2019): the threat moves inside the session

Arkko's draft argues that the stipulation was always a stipulation, not a theorem, and it's no longer tenable. TLS, QUIC, and HTTPS have largely defeated the channel attacker. Meanwhile, the threat has moved fully *inside* the authenticated session — to counterparties who are correctly identified, correctly authenticated, and correctly behaving cryptographically, but who are malicious, coerced, or commercially misaligned with the user. PKI tells you Google is really Google; it doesn't tell you Google won't sell your data. The proposed rewrite of RFC 3552's core assumption is the formal acknowledgment: instead of "end-systems have not been compromised," the new baseline is "the *implementing* end-system has not been compromised, but the other parties may be."

### Coming full circle

We're back to a Lowe-style world where the dangerous actor is a legitimate participant — except now at the scale of cloud providers, BFT leaders, and centralized infrastructure, rather than a single Mallory in a three-message protocol. The cryptographic identity is impeccable, the channel is encrypted, the signatures all verify, and the threat is still real. Forty years of threat-model evolution have brought the field back to the realization Lowe forced on it in 1995: the protocol's role structure, not the channel, is where the adversary lives.

## References

https://opentitan.org/
