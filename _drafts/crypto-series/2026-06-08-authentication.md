---
title:  "Authentication"
series: "Applied Crypto, Part 3"
series_url: "/programming/crypto-series-intro.html"
category: programming
date: 2026-06-08
---

This is the identity arm of the [split](/programming/crypto-series-intro.html): proving *who* a party is, as opposed to protecting *what* they send (that's [Key Exchange & Secure Channels](/programming/secure-channels.html)). The two are usually fused in a handshake, but they're separable — and authentication has its own 50-year story worth telling on its own.

Authentication runs in two directions, and they arrived in the opposite order you'd guess. **Server authentication** — your browser proving it's really talking to `google.com` and not an impostor — is the older problem and the one that runs silently on *every* HTTPS connection, login or not; it's the job of the Web PKI. **User (client) authentication** — a human or device proving identity *to* the server — is the visible login step, and its 50-year arc fills most of this post. **Mutual authentication** (mTLS) is just both at once. The [threat-model post](/programming/threat-model.html) named server authentication as "the identity binding" — layer 2, *is this key really Bob's?* — but left the mechanism for here.

## The actors

Authentication is a conversation between a handful of parties — a client, the resource server it's talking to, and often an identity provider that vouches for it — each holding different resident keys and minting different per-request proofs.

![image](/assets/authentication/meta-map-people.png)

> The grammar of what any proof can claim — who (identity: aud, iss, sub, rpId), when (freshness: iat, exp, jti, nonces), what (content: the bytes the proof commits to), what-for (scope), and bound-to-what (chaining: cnf claims) — is laid out in the secret-material map in [Keys](/programming/keys.html). Read any auth scheme below by asking which of those five it covers and which it omits.

## Server Authentication & the Web PKI

The user-auth story below is about moving the root of trust *out of the server's hands*. Server authentication has the mirror-image arc: moving it *out of any single CA's hands*. A public key is not a name — nothing in the bytes of `google.com`'s public key says "google.com" — so something has to vouch for the binding, and the whole history is about who that voucher is and how much you're forced to trust them.

You can read an X.509 certificate through the same five-part grammar as any other proof: **who** (the `subject` / Subject Alternative Names — the domains), **when** (the `notBefore`/`notAfter` validity window), **what-for** (key-usage and extended-key-usage extensions — "this key may sign TLS handshakes, not mint other certs"), and **bound-to-what** (the issuer's signature, chaining the leaf upward). The leaf binds a domain to a key, an intermediate signs the leaf, a root CA signs the intermediate — and the root's public key was baked into your browser or OS out of band, which is the [Roots of Trust](/programming/roots-of-trust-and-attestation.html) story, the anchor every chain terminates at.

#### Phase 1: Self-signed & TOFU (pre-PKI)

With no third party to vouch, you either accept a self-signed cert blindly or trust-on-first-use — pin the key the first time you see it and scream if it ever changes. SSH host keys still work exactly this way (`The authenticity of host ... can't be established`). TOFU is genuinely fine when you talk to the same server repeatedly, but it can't bootstrap trust with a server you've never met — which is the entire web.

#### Phase 2: Hierarchical CAs — X.509 & the Web PKI (1978 →)

Loren Kohnfelder's 1978 MIT thesis coined the word *certificate*: a signed statement binding a name to a key, so you no longer need an online directory lookup for every party. ITU standardized the format as X.509 (1988; the v3 extensions everyone actually uses arrived in 1996, profiled for the internet as RFC 5280). Netscape wired it into SSL in the mid-90s, and a commercial CA industry grew up to sign certs for a fee. The model: trust a fixed set of root CAs preinstalled in your browser, and transitively trust anything they sign. This is *still* the Web PKI — but notice the trust is blind and global: **any** trusted CA can vouch for **any** domain, so the system is only as strong as its single weakest CA.

#### Phase 3: Automating issuance — ACME & Let's Encrypt (2015)

For two decades certs cost money and were issued by hand, so most of the web stayed on plaintext HTTP. Let's Encrypt (ISRG, 2015) made domain-validated certs free and fully automated via the ACME protocol (RFC 8555): prove you control a domain by serving a token at a well-known URL or publishing a DNS record, and a cert drops out — scriptable end to end. HTTPS went from minority to near-universal in a few years. This is the **DV** (domain-validated) tier — "controls the domain," nothing more; the **OV** and **EV** tiers additionally vet the legal *organization*, but browsers quietly stopped giving EV any special UI treatment around 2019, conceding that users never read it.

#### Phase 4: Auditing the CAs — Certificate Transparency (2013 →)

Blind global trust broke exactly as you'd expect: the Comodo and DigiNotar compromises (2011) minted valid certs for domains like `google.com`, and nobody could *see* it had happened (the [threat-model post](/programming/threat-model.html) tells that story). Certificate Transparency (RFC 6962) is the fix: every cert must be logged in append-only, publicly-auditable logs, and Chrome and Safari reject certs that don't carry proof of logging. A bogus cert can still be *minted*, but no longer *invisibly* — domain owners monitor the logs for certs they never requested. CAA DNS records (which CAs are even permitted to issue for a domain) and multi-perspective domain validation (check domain control from several network vantage points, so a local BGP hijack can't fool it) are the same move: stop trusting a single CA blindly, constrain and audit it instead.

#### Phase 5: Shrinking the trust window — short-lived certs

Revocation is PKI's chronic weak spot — the "stale" problem from the [capstone](/programming/roots-of-trust-and-attestation.html). CRLs (download every revoked serial) grew too big; OCSP (ask the CA live, per connection) leaked your browsing history to the CA and added latency; OCSP stapling (the *server* fetches and attaches a fresh signed status) fixed privacy and latency but was never reliably deployed. The blunt answer that won was to make certs so short-lived that revocation barely matters: maximum lifetimes have ratcheted from 825 days to 398 (Sept 2020), and the CA/Browser Forum has voted to reach 47 days by 2029. A cert that expires in weeks is its own revocation.

#### The alternatives: who else can vouch?

Hierarchical CAs aren't the only way to bind a key to an identity. Each alternative is really a different answer to "who vouches, and for what?":

- **Web of Trust (PGP, 1991).** No CAs — users sign each other's keys, and trust propagates through whoever you've personally chosen as "introducers" (Zimmermann's "decentralized fault-tolerant web of confidence"). Decentralized and human-meaningful, but it never scaled: key-signing parties are friction, and trust paths between strangers are rarely short or legible.
- **SPKI/SDSI (RFC 2693, 1999).** Grew out of frustration with X.509's complexity, and made a radical move: *the key is the principal* — don't bind keys to global real-world identities at all, bind them to **authorizations** and **local names**, with the verifier often also the issuer (an "authorization loop"). Closer in spirit to today's capability tokens (macaroons, biscuits) than to the Web PKI.
- **DANE (RFC 6698, 2012).** Anchor certs in DNSSEC instead of CAs — publish the cert's fingerprint in a DNS record signed up the DNS hierarchy. Trades the CA cartel for the DNS root; browsers never adopted it.
- **Decentralized PKI / key transparency.** Blockchain naming (Namecoin, ENS) and W3C DIDs let each entity act as its own root authority, anchored in a distributed ledger rather than a CA — and the [roots-of-trust](/programming/roots-of-trust-and-attestation.html) post notes a blockchain genesis hash is just one more out-of-band anchor. Meanwhile key transparency (CONIKS, then Google / WhatsApp / iMessage key transparency) applies CT's "log everything" idea to *end-user* keys, so an E2EE provider can't swap in a wiretap key without leaving a public, auditable trace.

These map cleanly onto Zooko's triangle (secure / human-meaningful / decentralized — pick two, from the [capstone](/programming/roots-of-trust-and-attestation.html)): the Web PKI takes human-meaningful + secure and sacrifices decentralization (you trust the CA cartel); Web of Trust reaches for human-meaningful + decentralized and gives up reliable security at scale; self-certifying names (a Tor `.onion` address, a raw public-key fingerprint) are secure + decentralized but not human-meaningful; and blockchain naming is the bet that a global ledger can finally square all three.

Notice the throughline — the same one the user-auth arc has below: every step after Phase 2 (CT, CAA, multi-perspective validation, short lifetimes, and every decentralized alternative) pushes the root of trust *out of any single CA's hands*. Server auth and user auth are one de-trusting trajectory pointed in opposite directions.

#### Mutual TLS

Everything above authenticates the *server* to the client. mTLS makes it symmetric: the client also presents a cert, and the server validates it against its own trust anchor. On the open web this is rare (users don't carry certs), but it's the backbone of *service-to-service* authentication inside infrastructure — a workload's identity *is* an X.509 cert (SPIFFE/SPIRE issue exactly these), and possession of the matching private key is the proof. Same possession anchor as a passkey, just with no human in the loop — which reconnects to the service-to-service tier of the [security hierarchy](#picking-an-auth-method-security-hierarchy) below.

## History of User Authentication

The whole history of user authentication is the story of moving the root of trust out of the server's hands. The arc is secret-held-by-server → secret-held-by-server-but-harder-to-crack → secret-held-by-client.

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
7. [Public Key Infrastructure - Wikipedia][pki-wiki]
8. [Internet X.509 PKI Certificate and CRL Profile - RFC 5280][rfc5280]
9. [Automatic Certificate Management Environment (ACME) - RFC 8555][rfc8555]
10. [Certificate Transparency - RFC 6962][rfc6962]
11. [SPKI Certificate Theory - RFC 2693][rfc2693]
12. [DNS-Based Authentication of Named Entities (DANE) - RFC 6698][rfc6698]

[morris-thompson]: https://rist.tech.cornell.edu/6431papers/MorrisThompson1979.pdf "Password Security: A Case History - Morris & Thompson (1979)"
[sysapproach-auth]: https://book.systemsapproach.org/security/authentication.html "Authentication - Computer Networks: A Systems Approach"
[rfc6749]: https://datatracker.ietf.org/doc/html/rfc6749 "The OAuth 2.0 Authorization Framework - RFC 6749"
[rfc9700]: https://datatracker.ietf.org/doc/html/rfc9700 "Best Current Practice for OAuth 2.0 Security - RFC 9700"
[rfc9635]: https://datatracker.ietf.org/doc/html/rfc9635 "Grant Negotiation and Authorization Protocol (GNAP) - RFC 9635"
[hammer-road-to-hell]: https://hueniverse.com/oauth-2-0-and-the-road-to-hell-8eec45921529 "OAuth 2.0 and the Road to Hell - Eran Hammer"
[pki-wiki]: https://en.wikipedia.org/wiki/Public_key_infrastructure "Public Key Infrastructure - Wikipedia"
[rfc5280]: https://datatracker.ietf.org/doc/html/rfc5280 "Internet X.509 Public Key Infrastructure Certificate and CRL Profile - RFC 5280"
[rfc8555]: https://datatracker.ietf.org/doc/html/rfc8555 "Automatic Certificate Management Environment (ACME) - RFC 8555"
[rfc6962]: https://datatracker.ietf.org/doc/html/rfc6962 "Certificate Transparency - RFC 6962"
[rfc2693]: https://datatracker.ietf.org/doc/html/rfc2693 "SPKI Certificate Theory - RFC 2693"
[rfc6698]: https://datatracker.ietf.org/doc/html/rfc6698 "DNS-Based Authentication of Named Entities (DANE: TLSA) - RFC 6698"
