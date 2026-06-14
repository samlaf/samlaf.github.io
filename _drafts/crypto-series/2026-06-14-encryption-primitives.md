---
title:  "Encryption Primitives"
category: programming
date: 2026-06-14
---

## Where Keys Live

![image](/assets/encryption-primitives/where-keys-live-device-vs-server.png)

## Entropy Stack

![image](/assets/encryption-primitives/entropy-stack.png)


The middle track (blue) — the "normal" case for DH, session keys, random salts, IVs, any key you generate at runtime on a general-purpose computer. Your question "where does DH's seed entropy come from?" lands here. A Diffie–Hellman exchange starts when each party picks a random scalar — their ephemeral private key — and for Curve25519 that's just 32 random bytes. Those bytes come from the OS CSPRNG, which on Linux is the ChaCha20-based generator behind getrandom() and /dev/urandom (on macOS it's similar; Windows has CryptGenRandom / BCryptGenRandom). A CSPRNG is deterministic — given the same seed it produces the same output — so it's only as good as its seed. Which sends the question one level deeper.

The OS seed comes from physical entropy harvested by the kernel from several sources mixed together: CPU hardware RNG instructions (RDRAND/RDSEED on Intel/AMD, which internally use thermal noise in the silicon), timing jitter from interrupts and disk operations, keystrokes and mouse movements on desktop systems, clock skew between oscillators, and on some platforms, dedicated on-board TRNGs. The kernel hashes all of this together into an entropy pool and uses it to seed (and periodically reseed) the CSPRNG. The CSPRNG's job is whitening — taking whatever biased, potentially-correlated physical noise got sampled and producing uniformly distributed output indistinguishable from random.

So DH's seed ultimately comes from thermal motion of electrons (in CPU hardware RNGs), quantum tunneling noise (in some dedicated TRNGs), and the chaotic timing of physical events (interrupts, user input). The security of every DH handshake on the internet reduces, at bottom, to "thermodynamics makes the future unpredictable." Which is a genuinely beautiful fact if you sit with it.

The right track (purple) — keys that live in hardware. Your second question: Secure Enclaves and HSMs have their own TRNGs, distinct from the OS's. These are dedicated silicon circuits — typically ring oscillators whose phase drift is sampled, or avalanche noise from biased diodes, or quantum effects in some high-end HSMs — running a hardware-entropy-driven CSPRNG entirely inside the secure boundary. When your Secure Enclave generates a new passkey, the private key is created using the Enclave's internal TRNG and never exists anywhere else. Same for the root KEK in an HSM: generated internally, never emitted. The OS isn't involved because the whole point is that even a compromised OS can't influence the key. This is why FIPS 140-3 certification requires HSMs to have their own certified entropy source.

The left track (coral) — passwords. The entropy source here is human cognition, which is terrible at randomness. A user-chosen password might have 20–50 bits of actual entropy despite having 60+ bits of notional key length, because humans cluster around dictionary words, common patterns, and familiar dates. No amount of post-processing can add entropy that wasn't there — information theory forbids it. What Argon2 and friends do is add work factor: a low-entropy secret is still low-entropy, but now each guess takes 100ms and 64 MB of RAM, which multiplies the attacker's cost by a billion or so. The salt alone is uniformly random (from the middle track), so the stored hash looks high-entropy from the outside, but the secret itself is still constrained by what fit in someone's head.

## Primitives: PRFs vs PRPs

Long-term trend: the PRP era (DES, AES) is being supplemented by a PRF era (ChaCha, BLAKE3) where the primitive matches the way we actually use it. The diagram I drew has two roots today — HMAC and AES — but in fifteen years the dominant root might just be a single fast PRF that does everything.

![image](/assets/encryption-primitives/prf-vs-prp-tree.png)

The bottom row is the punchline I want to drive home. A stream cipher, a CSPRNG, and a KDF's expand step are all the same machine — a PRF run in counter mode, producing a long pseudorandom output stream. They differ only in where the key comes from and what you do with the output:
- Stream cipher: key from user/handshake → output XORed with plaintext to encrypt
- CSPRNG: key from entropy pool → output handed to whoever called random()
- HKDF-Expand: key from the Extract step → output sliced up into individual derived keys
- Deterministic-nonce signing (RFC 6979): key derived from (private_key, message) → output is the per-signature nonce

Once you see that, you stop memorizing them as separate things. They're all "PRF in counter mode" with different framing.

### Block vs Stream Cipher

![image](/assets/encryption-primitives/block-vs-stream-cipher.png)

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

![image](/assets/encryption-primitives/freshness-vs-primitive-grid.png)

Progression for how this came about (not exactly historical, but at least useful mental model):
1. Probabilistic encryption (Goldwasser-Micali, 1984): caller must supply randomness (formally hidden, practically not).
    - The encryption algorithm itself flips coins. The caller's only job is to call it. Randomness is hidden inside. The model assumes perfect internal randomness; in practice the IV leaked to the API and callers had to supply something random, but the formalism pretended otherwise. Caller's burden: theoretically nothing; practically, supply random IVs.
2. Nonce-based encryption (Rogaway, 2004): caller must supply uniqueness — much weaker, much easier to actually achieve.
    - The IV is surfaced as an explicit input. Security is defined relative to "the caller never reuses it." Caller's burden: uniqueness, not randomness. A counter works; a timestamp works; anything non-repeating works.
3. Tweakable block ciphers (Liskov-Rivest-Wagner, 2002): caller can do whatever, but now they're working with a different primitive whose security guarantee is "different tweaks give independent-looking permutations" rather than "encryption looks random.".
    - Getting probabilistic-looking output is back on the caller, at the mode level — but the primitive makes designing those modes much simpler.
    - The tweak is also explicit and caller-supplied. But there's no uniqueness requirement at all on the tweak. You may reuse (K, T) freely. Caller's burden: whatever you want — there's no contract on tweak values per se.
