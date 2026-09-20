---
title:  "Proving You Hold a Key"
series: "Applied Crypto, Part 3"
series_url: "/programming/crypto-series-intro.html"
category: programming
date: 2026-06-08
---

> This is Part 3 of a six-part [series on applied cryptography](/programming/crypto-series-intro.html).
>
> - **[Prologue: The changing internet threat model](/programming/threat-model.html)** — forty years of the adversary migrating from the wire, to the identity binding, to the authenticated counterparty itself.
> - **[Part 1: Cryptographic primitives](/programming/crypto-primitives.html)** — the atoms: PRFs and PRPs, block and stream ciphers, AEAD, MACs and signatures.
> - **[Part 2: Key exchange & secure channels](/programming/secure-channels.html)** — establishing the shared secret, from a pre-shared key up to fully-negotiated TLS.
> - **Part 3: Proving you hold a key** — from plaintext passwords to passkeys: what the prover holds, what the verifier stores, and what crosses the wire.
> - **[Part 4: Keys](/programming/keys.html)** — the life of a key: the entropy that seeds it, where it lives, and how it's wrapped.
> - **[Part 5: What a secure channel doesn't give you](/programming/secure-channel-capstone.html)** — the capstone: the channel is the easy part, and thirteen things it leaves for you.

This is the second half of the [duality](/programming/crypto-series-intro.html): a live party proving it *holds a key or secret*, as opposed to protecting *what* it sends (that's [Key Exchange & Secure Channels](/programming/secure-channels.html)). The two are usually fused in a handshake, but they're separable — and proof of possession has its own 50-year story worth telling on its own.

One thing this post deliberately does not do is say *who* the key belongs to. Everything below is key-relative: the server learns that the party on the wire holds the secret registered under an account, and nothing more. Turning that into a name — an identity — is a separate binding, and it is the subject of the [identity series](/programming/identity-series-intro.html). Read the arc below as a story about *custody*: what the prover holds, what the verifier stores, and what crosses the wire.

- [The actors](#the-actors)
- [History of User Authentication](#history-of-user-authentication)
    - [Phase 1: Plaintext passwords (1960s–70s)](#phase-1-plaintext-passwords-1960s70s)
    - [Phase 2: Hashed passwords (1979, Unix crypt)](#phase-2-hashed-passwords-1979-unix-crypt)
    - [Phase 3: Salted slow hashes (1990s–2010s)](#phase-3-salted-slow-hashes-1990s2010s)
    - [Phase 4: Something-you-have (2FA, ~2010s mainstream)](#phase-4-something-you-have-2fa-2010s-mainstream)
    - [Phase 5: Federated identity (Kerberos 1980s, SAML/OAuth/OIDC 2000s–)](#phase-5-federated-identity-kerberos-1980s-samloauthoidc-2000s)
    - [Phase 6: PAKE — password-authenticated key exchange](#phase-6-pake--password-authenticated-key-exchange)
    - [Phase 7: Public-key authentication — WebAuthn / Passkeys (2018–)](#phase-7-public-key-authentication--webauthn--passkeys-2018)
- [Picking an Auth method: security hierarchy](#picking-an-auth-method-security-hierarchy)

## The actors

Authentication is a conversation between a handful of parties — a client, the resource server it's talking to, and often an identity provider that vouches for it — each holding different resident keys and minting different per-request proofs.

![image](/assets/crypto-series/authentication/meta-map-people.png)

> The grammar of what any proof can claim — who (identity: aud, iss, sub, rpId), when (freshness: iat, exp, jti, nonces), what (content: the bytes the proof commits to), what-for (scope), and bound-to-what (chaining: cnf claims) — is laid out in the secret-material map in [Keys](/programming/keys.html). Read any auth scheme below by asking which of those five it covers and which it omits.

## History of User Authentication

The whole history of server-side authentication is the story of moving the root of trust out of the server's hands. The arc is secret-held-by-server → secret-held-by-server-but-harder-to-crack → secret-held-by-client.

#### Phase 1: Plaintext passwords (1960s–70s)

Early Unix literally stored passwords in /etc/passwd as plaintext. Anyone who could read the file — legitimately or via breach — compromised every account. Network protocols of the era (Telnet, FTP, early HTTP) sent passwords in the clear across the wire. The security model was "trust the admin, trust the network."

#### Phase 2: Hashed passwords (1979, Unix crypt)
Morris and Thompson's insight: store H(password) instead. To verify, hash the input and compare. The server never needs the plaintext again after registration. Huge step — reading the database no longer directly exposes credentials.
Two problems surfaced quickly: identical passwords produced identical hashes (enabling precomputed "rainbow tables" that invert common passwords), and the hashes were fast (crypt(3) was DES-based), so brute-forcing a stolen database was cheap.

#### Phase 3: Salted slow hashes (1990s–2010s)
Add a per-user random salt (different hash for the same password across users, kills rainbow tables) and use a deliberately slow function (bcrypt, PBKDF2, scrypt, Argon2). This is the era we've been discussing. It's what almost every website does today.

But notice the invariant across phases 1–3: the server sees the plaintext password at login time. Even if storage is safe, memory dumps, malicious admins, compromised TLS termination, log files ("oops, we logged request bodies"), and rogue dependencies can all leak credentials in transit through the server. And users reuse passwords, so a breach at one site propagates.

#### Phase 4: Something-you-have (2FA, ~2010s mainstream)

TOTP apps, SMS codes, hardware tokens. Doesn't replace the password, augments it. The server now needs two pieces of evidence, so a stolen password database alone isn't enough. Defense in depth, but the underlying password model is unchanged.

#### Phase 5: Federated identity (Kerberos 1980s, SAML/OAuth/OIDC 2000s–)

Rather than every website holding credentials, delegate auth to an identity provider. Fewer places hold passwords, which reduces breach surface. But it still fundamentally relies on password auth somewhere, just centralized. This phase is the one that is not really about proof of possession at all: an identity provider issues a signed *assertion* that binds a name to a session, and that is identity, not custody. The lineage from Kerberos through SAML to OpenID Connect is the [humans post](/programming/identity-of-humans.html) of the identity series. The delegation protocol that rides alongside it — OAuth's arc from signed requests to bearer tokens and back toward key-bound ones — is [a story about handing over authority](/programming/capabilities.html), and lives in the authorization series.

#### Phase 6: PAKE — password-authenticated key exchange

SRP (1998) and its modern successor OPAQUE (2018+) are beautiful protocols: the client proves knowledge of the password without ever sending it, and the server stores a verifier that's not usefully attackable offline after a breach. Cryptographically, these fix most of the password-era problems while keeping a memorable secret.

They never went mainstream. Too late, too complex to integrate, and passkeys ate the momentum.

#### Phase 7: Public-key authentication — WebAuthn / Passkeys (2018–)

The device generates an asymmetric keypair. The public key goes to the server. The private key never leaves the device (and on most hardware, can't be extracted — it lives in a TPM or Secure Enclave). Login is a signature over a server-issued challenge.

Consequences:
- A server breach yields public keys, which are useless to an attacker.
- Phishing becomes near-impossible because the browser binds each credential to an origin — a fake gooogle.com simply cannot produce a valid google.com signature.
- Password reuse disappears as a concept.

One thing to notice about the registration step: the server trusts whatever public key shows up at sign-up. That is a name → key binding written on first use, and everything after it is proof of possession against that binding. The [identity series](/programming/binding-without-a-ca.html#trust-on-first-use) has more to say about what first-use bindings can and cannot promise.

Passkeys are the endpoint of a 50-year trajectory, and the industry is actively pushing there. Apple, Google, and Microsoft all now ship passkey support by default, and major sites (GitHub, Amazon, Google, PayPal) support passkey-only login.

## Picking an Auth method: security hierarchy

The general rule: match the cost of the authentication to the value being protected, but use passkeys as your default consumer baseline because they meaningfully beat passwords at almost no UX cost.

For low-stakes consumer accounts (forums, media sites, minor services) — a salted, slow-hashed password is genuinely fine. The threat model is "my DB gets leaked" and Argon2 + a decent salt handles it. Adding TOTP optional-2FA covers the "account takeover via credential stuffing" threat for users who enable it.

For anything with real consequences (email, cloud storage, financial, health) — passwords become insufficient because they're phishable. This is where you want passkeys (or at minimum, a phish-resistant second factor like a security key). Passkeys pull their weight here because a single tap provides cryptographic possession proof, biometric inherence, and origin binding — all at once, with better UX than password + TOTP.

For administrative or high-privilege access (cloud root, code signing, DB admin, infrastructure) — hardware tokens with attestation (YubiKey, Titan, smartcard) become appropriate. The key property isn't just stronger crypto; it's that a lost-or-compromised laptop doesn't compromise the token. You want the possession factor to live on a separate device you can physically inventory.

For server-held secrets (database encryption keys, service signing keys, pepper, OAuth client secrets) — KMS/HSM-backed envelope encryption becomes the appropriate architecture. The tradeoff is operational complexity: every service call that needs to read encrypted data has to make a KMS call, which costs latency and money, and you need to think about failure modes if KMS is unreachable. For data that isn't genuinely sensitive, plain AES with a key in config is still sometimes the right call. (The envelope-encryption mechanics are covered in [Keys](/programming/keys.html).)

For service-to-service authentication (backend APIs calling each other) — no human factors apply. You want mutual TLS with client certificates, or signed JWTs where the signing key lives in the HSM. Again, possession is the anchor — a workload identity tied to hardware or to a short-lived credential from a workload identity service.

## References <!-- omit in toc -->

1. [Password Security: A Case History - Morris & Thompson (1979)][morris-thompson]
2. [Authentication - Computer Networks: A Systems Approach][sysapproach-auth]

[morris-thompson]: https://rist.tech.cornell.edu/6431papers/MorrisThompson1979.pdf "Password Security: A Case History - Morris & Thompson (1979)"
[sysapproach-auth]: https://book.systemsapproach.org/security/authentication.html "Authentication - Computer Networks: A Systems Approach"
