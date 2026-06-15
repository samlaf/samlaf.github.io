---
title:  "Applied Crypto 1: Cryptographic Primitives"
category: programming
date: 2026-06-14 00:05:00
---

Cryptographic primitives are the atoms everything else is built from. The same machinery serves confidentiality, authentication, key derivation, and randomness alike — the recurring punchline below is that a single primitive (a PRF) is hiding behind most of them.

## Primitives: PRFs vs PRPs

Long-term trend: the PRP era (DES, AES) is being supplemented by a PRF era (ChaCha, BLAKE3) where the primitive matches the way we actually use it. The diagram I drew has two roots today — HMAC and AES — but in fifteen years the dominant root might just be a single fast PRF that does everything.

![image](/assets/crypto-primitives/prf-vs-prp-tree.png)

The bottom row is the punchline I want to drive home. A stream cipher, a CSPRNG, and a KDF's expand step are all the same machine — a PRF run in counter mode, producing a long pseudorandom output stream. They differ only in where the key comes from and what you do with the output:
- Stream cipher: key from user/handshake → output XORed with plaintext to encrypt
- CSPRNG: key from entropy pool → output handed to whoever called random()
- HKDF-Expand: key from the Extract step → output sliced up into individual derived keys
- Deterministic-nonce signing (RFC 6979): key derived from (private_key, message) → output is the per-signature nonce

Once you see that, you stop memorizing them as separate things. They're all "PRF in counter mode" with different framing.

### Block vs Stream Cipher

![image](/assets/crypto-primitives/block-vs-stream-cipher.png)

The vocabulary is genuinely overloaded. Four terms, two axes.

Primitive shape (what the underlying function looks like):
- Block cipher: takes a fixed-size block (128 bits for AES), produces same-size output, invertible with the key. AES, DES, Twofish, Serpent.
- Stream cipher primitive: takes a key + nonce + counter, produces a keystream block. Forward-only, no inverse. ChaCha20, Salsa20, RC4 (broken, don't use).

Usage mode (how the primitive is wrapped to encrypt messages):
- Block-cipher mode: encrypts each plaintext block by feeding it through the primitive (possibly chained with previous blocks). CBC, ECB, XTS. Requires an invertible primitive.
- Stream-cipher mode: generates a keystream by calling the primitive on a counter, then XORs with plaintext. CTR, GCM, ChaCha20-Poly1305. Only needs forward calls.

So the four combinations:
- Block primitive + block mode: AES-CBC, AES-XTS. Classical.
- Block primitive + stream mode: AES-CTR, AES-GCM. Modern default.
- Stream primitive + stream mode: ChaCha20-Poly1305, Salsa20. Native fit.
- Stream primitive + block mode: doesn't really exist — you can't run CBC with ChaCha20 because there's no inverse.

The trend over the last decade has been to abandon the upper-left quadrant (block-mode usage) and standardize on the lower two — either AES-GCM (block primitive, stream mode) for hardware acceleration on Intel/ARM, or ChaCha20-Poly1305 (native stream) for software performance on CPUs without AES instructions.

## Tweakable Encryption

Freshness is the goal. Nonces were the first clean formalization of how to deliver it, by surfacing a uniqueness contract at the mode-level API. Tweaks then provided a richer primitive that makes mode construction easier, by letting the mode designer derive freshness from context however they want rather than imposing a contract on the caller. XTS is the extreme case — pure position-derived tweaks, no nonce at all, freshness fully internal — accepted because disk encryption can't fit nonces anywhere. SIV is the other extreme — freshness from the plaintext itself, defending against the failure mode where nonces get reused — accepted because that failure mode keeps happening in real systems. Deoxys-II combines both ideas, using a tweakable primitive to build a nonce-based AEAD that's also misuse-resistant.

![image](/assets/crypto-primitives/freshness-vs-primitive-grid.png)

Progression for how this came about (not exactly historical, but at least useful mental model):
1. Probabilistic encryption (Goldwasser-Micali, 1984): caller must supply randomness (formally hidden, practically not).
    - The encryption algorithm itself flips coins. The caller's only job is to call it. Randomness is hidden inside. The model assumes perfect internal randomness; in practice the IV leaked to the API and callers had to supply something random, but the formalism pretended otherwise. Caller's burden: theoretically nothing; practically, supply random IVs.
2. Nonce-based encryption (Rogaway, 2004): caller must supply uniqueness — much weaker, much easier to actually achieve.
    - The IV is surfaced as an explicit input. Security is defined relative to "the caller never reuses it." Caller's burden: uniqueness, not randomness. A counter works; a timestamp works; anything non-repeating works.
3. Tweakable block ciphers (Liskov-Rivest-Wagner, 2002): caller can do whatever, but now they're working with a different primitive whose security guarantee is "different tweaks give independent-looking permutations" rather than "encryption looks random.".
    - Getting probabilistic-looking output is back on the caller, at the mode level — but the primitive makes designing those modes much simpler.
    - The tweak is also explicit and caller-supplied. But there's no uniqueness requirement at all on the tweak. You may reuse (K, T) freely. Caller's burden: whatever you want — there's no contract on tweak values per se.

## MACs & Signatures

The same primitives that encrypt also authenticate — which is the whole reason this article is about *cryptographic* primitives, not just encryption. Integrity and origin authentication fall out of the same PRF/PRP machinery, just pointed at a different question: not "can an eavesdropper read this?" but "was this produced by someone holding the key, and has it been tampered with?"

**MACs (symmetric authentication).** A Message Authentication Code is a PRF keyed with a shared secret: `tag = PRF(key, message)`. Anyone with the key can produce or verify the tag; nobody else can forge one. The common constructions are just different PRFs:
- HMAC — a PRF built from a hash (HMAC-SHA256). The generic, conservative default.
- GMAC / Poly1305 — fast one-time MACs over a polynomial; they're the authentication half of AES-GCM / ChaCha20-Poly1305.
- CMAC — a PRP (AES) turned into a MAC via CBC-style chaining.

**AEAD = encryption + MAC, fused.** This is where the two halves of this article meet. An authenticated-encryption mode runs a stream-cipher mode for confidentiality *and* a MAC for integrity under one key schedule, so you can't forget the integrity half (the classic mistake that breaks "encrypt-only" designs). AES-GCM = AES-CTR + GMAC. ChaCha20-Poly1305 = ChaCha20 keystream + Poly1305. The tweakable modes from the previous section (Deoxys-II, SIV) are AEADs too, just with stronger freshness guarantees. Whenever an application reaches for "encryption," it almost always wants an AEAD, not raw confidentiality — which is why the [channel](/programming/secure-channels.html) post treats AEAD as the default once a handshake has produced session keys.

**Signatures (asymmetric authentication).** A MAC's limitation is that verifying requires the same secret used to sign — so the verifier can also forge. Signatures break that symmetry: a private key signs, and a *public* key verifies, so anyone can check authenticity without being able to forge. That asymmetry is what makes signatures the backbone of identity at a distance — certificates, software signing, the passkey login in the [Authentication](/programming/authentication.html) post, the quote-signing keys in the [Attestation](/programming/roots-of-trust-and-attestation.html) post. RSA, ECDSA (NIST curves), and EdDSA (Ed25519) are the workhorses; the deterministic-nonce trick in EdDSA / RFC 6979 is, again, just a PRF over `(private_key, message)` — the same "PRF in counter mode" idea from the diagram above, reused to avoid catastrophic nonce reuse.

The throughline: a MAC is the integrity twin of symmetric encryption, and a signature is the integrity twin of asymmetric encryption. Confidentiality hides content; authentication binds it to a holder of a key. Real protocols always want both — which is why AEAD fuses them, and why the channel and authentication posts lean on these primitives constantly.

## References <!-- omit in toc -->

1. [The Joy of Cryptography (ch. 11) - Mike Rosulek][joc-ch11]
2. [Best Practices for Key Derivation - Trail of Bits][tob-kdf]

[joc-ch11]: https://joyofcryptography.com/pdf/chap11.pdf "The Joy of Cryptography (ch. 11) - Mike Rosulek"
[tob-kdf]: https://blog.trailofbits.com/2025/01/28/best-practices-for-key-derivation/ "Best Practices for Key Derivation - Trail of Bits"
