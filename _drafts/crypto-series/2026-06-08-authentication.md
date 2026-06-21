---
title:  "Authentication"
series: "Applied Crypto, Part 3"
series_url: "/programming/crypto-series-intro.html"
category: programming
date: 2026-06-08
---

This is the identity arm of the [split](/programming/crypto-series-intro.html): proving *who* a party is, as opposed to protecting *what* they send (that's [Key Exchange & Secure Channels](/programming/secure-channels.html)). The two are usually fused in a handshake, but they're separable — and authentication has its own 50-year story worth telling on its own.

## The actors

Authentication is a conversation between a handful of parties — a client, the resource server it's talking to, and often an identity provider that vouches for it — each holding different resident keys and minting different per-request proofs.

![image](/assets/authentication/meta-map-people.png)

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


## The OAuth arc: delegated authorization

Phase 5's "delegate to an identity provider" deserves its own look, because OAuth's *own* evolution recapitulates this series' recurring lesson — a flexible framework gets patched for a decade until the patches become the baseline. It's also the cleanest real-world example of the "right party" problem: how do you let a third party act on your behalf *without* handing over your password?

**OAuth 1.0 / 1.0a (2007, RFC 5849) — signature-based.** Every request was cryptographically signed by the client using shared secrets (HMAC-SHA1 or RSA), so security didn't depend on the transport. The cost was brutal implementation complexity — the "signature base string" canonicalization (sorting params, percent-encoding exactly right) was where everyone's implementation broke. 1.0a was a 2009 patch closing a session-fixation flaw in the request-token handoff.

**OAuth 2.0 (2012, RFC 6749 + 6750) — a deliberate break.** It dropped request signing in favor of bearer tokens ("possession = access") and offloaded confidentiality entirely to TLS, which made clients vastly easier to write. It also redefined itself as a *framework* rather than a protocol — many optional grant types and extension points. Eran Hammer, the lead editor, resigned and pulled his name, arguing the flexibility traded interoperability and security for enterprise extensibility ("the road to hell"). He was partly right: the next decade was spent patching the framework — PKCE (RFC 7636), device flow, token introspection, mTLS, DPoP, and eventually the Security BCP (RFC 9700) — because "framework with too many choices" produced a long tail of insecure deployments.

**OAuth 2.1 (in progress) — consolidation, not new mechanics.** As of early 2026 it's still a draft (`draft-ietf-oauth-v2-1`), intended to replace and obsolete RFC 6749 and the bearer-token RFC 6750. It folds the decade of best practices into the baseline: PKCE mandatory for the authorization-code flow, the implicit grant and the resource-owner-password-credentials grant removed, bearer tokens forbidden in query strings, exact redirect-URI matching. Major providers already treat the retired grants as deprecated regardless of the draft's formal status.

**"OAuth 3" → GNAP (RFC 9635, October 2024) — the clean-slate redesign.** It began as Justin Richer's XYZ / "transactional authorization" draft, merged with Aaron Parecki's XAuth, and standardized as GNAP. The headline differences from OAuth 2: clients no longer need to be registered in advance (the client describes itself at the start of the flow via a negotiated request rather than relying on a pre-issued `client_id`/`client_secret`), and it's intent/negotiation-based with **key-bound (proof-of-possession) tokens as the default** rather than bearer tokens.

The twist worth knowing: GNAP is "OAuth 3" only in spirit, not in adoption. It's a finished standard, but because it's not backward-compatible with the enormous OAuth 2 ecosystem, the practical momentum went to OAuth 2.1's "clean up what everyone already runs" path. So the real-world story is OAuth 2 → hardened OAuth 2 (2.1), with GNAP as the published-but-largely-unadopted next-generation design sitting alongside it.

Notice the same shape as the [threat-model arc](/programming/threat-model.html) and the password→passkey story above: the meaningful movement is away from *bearer* tokens ("possession = access," trust the transport) toward *proof-of-possession / key-bound* tokens — pushing security back onto a key the holder controls. That's the exact migration the rest of this series keeps finding.

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
3. [The OAuth 2.0 Authorization Framework - RFC 6749][rfc6749]
4. [Best Current Practice for OAuth 2.0 Security - RFC 9700][rfc9700]
5. [Grant Negotiation and Authorization Protocol (GNAP) - RFC 9635][rfc9635]
6. [OAuth 2.0 and the Road to Hell - Eran Hammer][hammer-road-to-hell]

[morris-thompson]: https://rist.tech.cornell.edu/6431papers/MorrisThompson1979.pdf "Password Security: A Case History - Morris & Thompson (1979)"
[sysapproach-auth]: https://book.systemsapproach.org/security/authentication.html "Authentication - Computer Networks: A Systems Approach"
[rfc6749]: https://datatracker.ietf.org/doc/html/rfc6749 "The OAuth 2.0 Authorization Framework - RFC 6749"
[rfc9700]: https://datatracker.ietf.org/doc/html/rfc9700 "Best Current Practice for OAuth 2.0 Security - RFC 9700"
[rfc9635]: https://datatracker.ietf.org/doc/html/rfc9635 "Grant Negotiation and Authorization Protocol (GNAP) - RFC 9635"
[hammer-road-to-hell]: https://hueniverse.com/oauth-2-0-and-the-road-to-hell-8eec45921529 "OAuth 2.0 and the Road to Hell - Eran Hammer"
