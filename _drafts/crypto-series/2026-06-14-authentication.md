---
title:  "Applied Crypto 3: Authentication"
category: programming
date: 2026-06-14 00:03:00
---

This is the identity arm of the [duality](/programming/crypto-series-intro.html): proving *who* a party is, as opposed to protecting *what* they send (that's [Key Exchange & Secure Channels](/programming/secure-channels.html)). The two are usually fused in a handshake, but they're separable — and authentication has its own 50-year story worth telling on its own.

## The actors

Authentication is a conversation between a handful of parties — a client, the resource server it's talking to, and often an identity provider that vouches for it — each holding different resident keys and minting different per-request proofs.

![image](/assets/authentication/meta-map-people.png)

> The grammar of what any proof can claim — who (identity: aud, iss, sub, rpId), when (freshness: iat, exp, jti, nonces), what (content: the bytes the proof commits to), what-for (scope), and bound-to-what (chaining: cnf claims) — is laid out in the secret-material map in [Keys & Roots of Trust](/programming/keys-and-roots-of-trust.html). Read any auth scheme below by asking which of those five it covers and which it omits.

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

Rather than every website holding credentials, delegate auth to an identity provider. Fewer places hold passwords, which reduces breach surface. But it still fundamentally relies on password auth somewhere, just centralized.

#### Phase 6: PAKE — password-authenticated key exchange

SRP (1998) and its modern successor OPAQUE (2018+) are beautiful protocols: the client proves knowledge of the password without ever sending it, and the server stores a verifier that's not usefully attackable offline after a breach. Cryptographically, these fix most of the password-era problems while keeping a memorable secret.

They never went mainstream. Too late, too complex to integrate, and passkeys ate the momentum.

#### Phase 7: Public-key authentication — WebAuthn / Passkeys (2018–)

The device generates an asymmetric keypair. The public key goes to the server. The private key never leaves the device (and on most hardware, can't be extracted — it lives in a TPM or Secure Enclave). Login is a signature over a server-issued challenge.

Consequences:
- A server breach yields public keys, which are useless to an attacker.
- Phishing becomes near-impossible because the browser binds each credential to an origin — a fake gooogle.com simply cannot produce a valid google.com signature.
- Password reuse disappears as a concept.

Passkeys are the endpoint of a 50-year trajectory, and the industry is actively pushing there. Apple, Google, and Microsoft all now ship passkey support by default, and major sites (GitHub, Amazon, Google, PayPal) support passkey-only login.


## Picking an Auth method: security hierarchy

The general rule: match the cost of the authentication to the value being protected, but use passkeys as your default consumer baseline because they meaningfully beat passwords at almost no UX cost.

For low-stakes consumer accounts (forums, media sites, minor services) — a salted, slow-hashed password is genuinely fine. The threat model is "my DB gets leaked" and Argon2 + a decent salt handles it. Adding TOTP optional-2FA covers the "account takeover via credential stuffing" threat for users who enable it.

For anything with real consequences (email, cloud storage, financial, health) — passwords become insufficient because they're phishable. This is where you want passkeys (or at minimum, a phish-resistant second factor like a security key). Passkeys pull their weight here because a single tap provides cryptographic possession proof, biometric inherence, and origin binding — all at once, with better UX than password + TOTP.

For administrative or high-privilege access (cloud root, code signing, DB admin, infrastructure) — hardware tokens with attestation (YubiKey, Titan, smartcard) become appropriate. The key property isn't just stronger crypto; it's that a lost-or-compromised laptop doesn't compromise the token. You want the possession factor to live on a separate device you can physically inventory.

For server-held secrets (database encryption keys, service signing keys, pepper, OAuth client secrets) — KMS/HSM-backed envelope encryption becomes the appropriate architecture. The tradeoff is operational complexity: every service call that needs to read encrypted data has to make a KMS call, which costs latency and money, and you need to think about failure modes if KMS is unreachable. For data that isn't genuinely sensitive, plain AES with a key in config is still sometimes the right call. (The envelope-encryption mechanics are covered in [Keys & Roots of Trust](/programming/keys-and-roots-of-trust.html).)

For service-to-service authentication (backend APIs calling each other) — no human factors apply. You want mutual TLS with client certificates, or signed JWTs where the signing key lives in the HSM. Again, possession is the anchor — a workload identity tied to hardware or to a short-lived credential from a workload identity service.

## References

https://rist.tech.cornell.edu/6431papers/MorrisThompson1979.pdf
https://book.systemsapproach.org/security/authentication.html
