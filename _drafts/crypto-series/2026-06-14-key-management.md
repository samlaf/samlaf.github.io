# Key Generation / Exchange / Management

Any real system has to answer two orthogonal questions for every byte that moves: who is this from (identity) and who else can see it (data protection). Both questions get answered at multiple layers, and the layers compose.
1. Identity layers: TLS server cert (transport), mTLS client cert or app-layer login — password/passkey/OAuth (request), session token — cookie/JWT (subsequent requests in a session), workload identity for service-to-service.
2. Data-protection layers: TLS record layer (in transit), payload encryption inside queues/caches (in motion-but-at-rest), DEK/KEK envelope encryption (storage), E2E encryption between end users (server-as-relay).

## Meta-Map

First the secrets/data:
![image](https://hackmd.io/_uploads/S1pQzlskMg.png)

> The middle-right cell is the one that rewards reading carefully, because it's the universal grammar of what any proof can claim: who (identity — aud, iss, sub, rpId), when (freshness — iat, exp, jti, nonces), what (content — the bytes the proof commits to, like the TLS transcript or DPoP's htm/htu/ath), what-for (scope — OAuth scopes, X.509 key-usage extensions), and bound-to-what (chaining — cnf claims that tie one proof to another's key). Any new auth scheme you encounter, you can read it by asking which of these five it covers and which it omits. Bearer access tokens cover identity + freshness + scope, but skip chaining and content — which is exactly the gap DPoP fills by adding cnf to the token and htm/htu/ath/jti to the per-request proof. mTLS-bound tokens fill the same gap differently, by using the TLS-layer client cert as the chaining anchor. Same problem, two solutions, both visible in the grid.

And then the people:
![image](https://hackmd.io/_uploads/B1rPfxjJze.png)

## Client-Server Session

A typical client-server session looks like:
1. Wire Channel security (TLS): server's identity is authenticated via certificate, ephemeral DH establishes a shared secret, HKDF derives AEAD session keys. This happens before any application bytes flow.
2. In-transit data protection: from here we have a secure channel protection the data in transit
3. User authentication: inside the TLS channel, the user (or their device) proves identity — password, passkey, OAuth token. This is app-layer.
4. (app-layer) Session establishment: server issues a short-lived token (cookie, JWT) so subsequent requests skip step 2.
5. In-use and At-rest Data protection: now you can layer authenticated encryption for data at rest (DEK/KEK), for queue payloads, for cached blobs, or for end-to-end-encrypted content between users.

TODO: actually at both wire and app-layers, we should separate channel establishment from authentication. They are often combined, but don't have to be, and are conceptually separate:
> Generally, session key establishment protocols perform authentication. A notable exception is Diffie-Hellman, as described below, so the terms authentication protocol and session key establishment protocol are almost synonymous.
> https://book.systemsapproach.org/security/authentication.html

Note that mTLS can be used to authenticate the user in step 1. See https://docs.secureauth.com/iam/blog/sender-constrained-access-tokens-mtls-vs-dpop

## 1. Channel Establishment

![image](https://hackmd.io/_uploads/SyQLVA8p-g.png)


Tier 1 — Symmetric only. Both parties already share a key. This is your DEK/KEK story, your in-house service-to-service encryption, anywhere the key distribution problem is already solved out-of-band. Just AEAD (AES-GCM, ChaCha20-Poly1305).

Tier 2 — Non-interactive PKE. Sender knows the recipient's public key and produces a sealed message with no handshake. Recipient doesn't need to be online. This is the email-style model. HPKE lives here. So do older constructions like libsodium's crypto_box_seal, age, and PGP.

Tier 3 — Interactive channel, fixed ciphersuite. Both parties online, simple handshake, no negotiation — the algorithms are baked into the protocol design. Noise lives here. WireGuard, Signal's underlying X3DH, the Lightning Network, WhatsApp's transport — all built on Noise patterns.

Tier 4 — Interactive channel, full negotiation. TLS. Versioned, ciphersuite-agile, extension-rich, certificate-based PKI integration. The Swiss Army knife when you need to talk to arbitrary clients on the open internet.

TODO: The arrow direction is the wrong message. "More interactive = more advanced" is the implicit story the 1D axis tells, and modern crypto thinking is largely the opposite. The history of TLS is the history of negotiation-driven attacks: FREAK, Logjam, POODLE, BEAST, CRIME, ROBOT, downgrade-dance variants — most of those exploit version or ciphersuite negotiation, not the underlying primitives. Cryptographic agility is now widely seen as a footgun. WireGuard's whole pitch is "we ripped out the negotiation." Trevor Perrin designed Noise so the ciphersuite is part of the protocol name (e.g. Noise_IK_25519_ChaChaPoly_BLAKE2s), never negotiated. DJB has written at length about why he considers algorithm agility harmful. So the honest reading of that axis is: rightward = more flexible at the cost of more attack surface and a harder security proof. Not better — more compatible with the open internet, which is a different thing.

![image](https://hackmd.io/_uploads/H1laCxNyGx.png)

#### Noise-Style Protocol Composition Recipes

![image](https://hackmd.io/_uploads/rJ7anGEkGx.png)

Both HPKE base mode and TLS 1.2 with an RSA cipher suite are instantiations of the same composition: static-recipient KEM → KDF → AEAD. The sender contributes fresh randomness, the recipient contributes a long-term static private key, and the KEM lets both ends up with a shared key K that seeds the symmetric key schedule. Only what fills the KEM slot differs. Forward secrecy is impossible here because `sk_R` is reused across all senders — compromising it tomorrow decrypts every HPKE message anyone has ever sent to that recipient. That's a deliberate trade for async usability, not a bug. age and libsodium sealed boxes have the same shape.



![image](https://hackmd.io/_uploads/S1wqNz4yGe.png)

TLS 1.3's whole forward-secrecy story lives in those two ephemerals: both sides erase them after the handshake, so even a future compromise of `cert_priv` doesn't decrypt past sessions. The certificate key never participates in the DH — it only signs the transcript, which is exactly why this composition can't be expressed as a Noise pattern. Noise authenticates with static-key DH; TLS authenticates with signatures. Different primitive choice, different proof structure.

![image](https://hackmd.io/_uploads/BykjVzNkGg.png)

WireGuard is the cleanest example of a Noise pattern in production. The four DHs cover every combination of {ephemeral, static} across both sides; mixing them in order into BLAKE2s gives mutual identity authentication (`ss`), forward secrecy (`ee`), and identity binding (`es`, `se`) all at once — with no signatures, no negotiation, and a ciphersuite literally baked into the protocol name. The 2-minute forced rekey is what gives the partial post-compromise security from the matrix: a stolen session state ages out within 120 seconds.

![image](https://hackmd.io/_uploads/H1Ai4MVyzl.png)

Signal's choreography is denser because it has to be async. Alice can't ECDH against a freshly-generated Bob ephemeral — Bob is offline. Instead she ECDHs against keys Bob uploaded to the server earlier, and the *combination of which DH involves which key* is what does the work: `DH1` uses Alice's identity (so Bob knows it's her), `DH2` uses Bob's identity (so Alice knows it's him), `DH3` and `DH4` inject freshness from Alice's ephemeral and Bob's one-time prekey. Mixing all four into HKDF means an attacker would have to compromise *every* key type to break the session. The output seeds the Double Ratchet, which is where the per-message forward secrecy and the round-trip-driven post-compromise security come from. PQXDH adds an ML-KEM encapsulation in parallel — same shape, hybrid KEM.

## 2. AEAD

TODO: link to cipher modes, AEAD material, etc. in https://hackmd.io/_I_ShulgRTCr2rmJwvh2JA

## 3. History of User Authentication

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


## 4. Picking an Auth method: security hierarchy

The general rule: match the cost of the authentication to the value being protected, but use passkeys as your default consumer baseline because they meaningfully beat passwords at almost no UX cost.

For low-stakes consumer accounts (forums, media sites, minor services) — a salted, slow-hashed password is genuinely fine. The threat model is "my DB gets leaked" and Argon2 + a decent salt handles it. Adding TOTP optional-2FA covers the "account takeover via credential stuffing" threat for users who enable it.

For anything with real consequences (email, cloud storage, financial, health) — passwords become insufficient because they're phishable. This is where you want passkeys (or at minimum, a phish-resistant second factor like a security key). Passkeys pull their weight here because a single tap provides cryptographic possession proof, biometric inherence, and origin binding — all at once, with better UX than password + TOTP.

For administrative or high-privilege access (cloud root, code signing, DB admin, infrastructure) — hardware tokens with attestation (YubiKey, Titan, smartcard) become appropriate. The key property isn't just stronger crypto; it's that a lost-or-compromised laptop doesn't compromise the token. You want the possession factor to live on a separate device you can physically inventory.

For server-held secrets (database encryption keys, service signing keys, pepper, OAuth client secrets) — KMS/HSM-backed envelope encryption becomes the appropriate architecture. The tradeoff is operational complexity: every service call that needs to read encrypted data has to make a KMS call, which costs latency and money, and you need to think about failure modes if KMS is unreachable. For data that isn't genuinely sensitive, plain AES with a key in config is still sometimes the right call.

For service-to-service authentication (backend APIs calling each other) — no human factors apply. You want mutual TLS with client certificates, or signed JWTs where the signing key lives in the HSM. Again, possession is the anchor — a workload identity tied to hardware or to a short-lived credential from a workload identity service.

## 5. In-use and At-rest encryption

This is a whole other world; this is where TEE enclaves live for in-use protection, and for data-at-rest, see https://samlaf.github.io/programming/searchable-client-side-encrypted-database.html

## References

https://fystack.io/blog/dek-kek-the-industry-standard-to-protect-highly-sensitive-data-part-1
https://stephenroughley.com/2019/06/09/concepts-of-compliant-data-encryption/
https://news.ycombinator.com/item?id=24379120
https://joyofcryptography.com/pdf/chap11.pdf
https://blog.trailofbits.com/2025/01/28/best-practices-for-key-derivation/
https://rist.tech.cornell.edu/6431papers/MorrisThompson1979.pdf
https://neilmadden.blog/2021/04/08/from-kems-to-protocols/
https://rlc.vlinder.ca/ecdh-kem/
https://book.systemsapproach.org/security/authentication.html
