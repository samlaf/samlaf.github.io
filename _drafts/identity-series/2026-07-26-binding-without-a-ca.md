---
title:  "Binding without a CA"
series: "Identity, Part 6"
series_url: "/programming/identity-series-intro.html"
category: programming
date: 2026-07-26
---

> This is Part 6 of a six-part [series on identity](/programming/identity-series-intro.html).
>
> 1. **[Naming and binding](/programming/naming-and-binding.html)** — names stay put, bindings move. Saltzer's lens, from the ARPANET to Kubernetes to PCIe.
> 2. **[Keys are not names](/programming/keys-are-not-names.html)** — what cryptography can say about who, and why anyone bothers with names at all.
> 3. **[Hosts](/programming/identity-of-hosts.html)** — DNS, X.509 and the Web PKI: forty years of binding names to keys, and the anchors it bottoms out in.
> 4. **[Humans](/programming/identity-of-humans.html)** — accounts, the trusted third party from Kerberos to OIDC, and sessions.
> 5. **[Workloads and hardware](/programming/identity-of-workloads.html)** — secret zero, SPIFFE, federated CI identity, and attestation.
> 6. **Binding without a CA** — first use, webs of trust, transparency logs, and petnames.

Three articles, three kinds of principal, and one shape every time: an issuer you configured signs a binding you then believe. CAs, identity providers, orchestrators, chip vendors. The issuer is the design's strength — one configured binding covers millions of certified ones — and its target, because compromising the issuer forges them all.

Some settings have no issuer both sides will accept. Two people who want to message each other without trusting the messaging company. An operator SSHing into their own machines. Peers on a network with no operator at all. This last article is about what they do instead, and what each alternative gives up. It ends where the [authorization series](/programming/authorization-series-intro.html) begins: with the observation that for many purposes you never needed the name.

- [Trust on first use](#trust-on-first-use)
- [The web of trust, and why it died](#the-web-of-trust-and-why-it-died)
- [Self-certifying names](#self-certifying-names)
- [Petnames](#petnames)
- [Transparency: audit instead of prevent](#transparency-audit-instead-of-prevent)
- [Blockchain names](#blockchain-names)
- [Every deployed system is a mix](#every-deployed-system-is-a-mix)
- [Where this leaves the name](#where-this-leaves-the-name)

## Trust on first use

SSH shipped in 1995 with no infrastructure at all. The first time you connect to a host, the client shows you a fingerprint and asks whether to trust it. Say yes and it writes the binding — hostname → key — into `known_hosts`. Every later connection checks the key against that line, and if it changes you get the famous warning that the remote host identification has changed and someone may be doing something nasty.

That is a binding written at first contact with an unbounded lifetime, and its properties fall straight out of the [first article](/programming/naming-and-binding.html#turning-the-lens-on-keys). It is cheap: no issuer, no chain, one local table. It is robust against an attacker who shows up *later*, which is most attackers. It is blind on exactly the connection you could not verify — the first one — and it fails silently there, because a man in the middle on first contact produces a fingerprint that looks like any other. And the warning it does give is so common in practice, after reinstalls and rehosting, that people learned to delete the line and reconnect.

Signal's safety numbers are the same mechanism with an optional out-of-band step: bind on first contact, alert on change, and let two people compare a code in person if they care. Passkey registration is TOFU too, at the account level: the site trusts whatever public key shows up at sign-up. And HTTP Public Key Pinning was TOFU for the web, and the [hosts article](/programming/identity-of-hosts.html#pinning-early-binding-and-why-it-died) covers why a first-use binding that every browser caches for months could not survive key rotation at web scale.

OpenSSH grew a tiny CA in 2010 — [SSH certificates][ssh-certs], where a host or user key is signed by an operator-run authority and clients configure one `@cert-authority` line instead of thousands of host keys. It is the certified model at the smallest possible scale, and the fact that operators reach for it as soon as they have more than a handful of machines is a fair summary of TOFU's limits.

## The web of trust, and why it died

PGP (1991) tried to make the binding social. You sign the keys of people whose identity you have verified; they sign others; a stranger's key is trusted if enough signatures from keys you trust lead to it. Keyservers hold the keys and the signatures. Key-signing parties were the on-boarding ritual. No CA, no company, no government: name → key bindings written by the people who actually knew.

It was decentralized and it was secure in Zooko's sense, and it did not scale past the communities that built it, for reasons that are instructive:

- **Trust does not compose the way the model assumed.** That I verified Bob's passport says nothing about how carefully Bob verified Carol's. Trust levels and thresholds tried to model this and made the UX worse without making the inference sound.
- **Revocation had no reach.** A revocation certificate had to propagate to everyone who held a copy of the key, and keyservers were eventually consistent at best. The scope of a binding is where copies of it live, and PGP keys lived everywhere.
- **The keyservers could not be defended.** They accepted any signature on any key, so in 2019 [attackers attached tens of thousands of signatures][sks-attack] to prominent developers' keys, making them so large that importing one broke GnuPG. Short key IDs had already been shown to collide trivially ([Evil32][evil32], 2014). The successor server, `keys.openpgp.org`, verifies email addresses before publishing a key — which is a certification step, and an admission.
- **Nobody would do the work.** Verifying a stranger's identity carefully is slow and unpleasant, and almost everyone signed keys carelessly or not at all, so the graph that was supposed to carry trust was mostly noise.

The web of trust is the one model in this series that tried to make *humans* the binding service at scale, and the result is the strongest evidence that certified bindings won for a reason. People will configure a root once. They will not certify strangers on demand.

## Self-certifying names

If binding a name to a key is the hard part, make the name *be* the key.

Mazières's [SFS][sfs] (1999) did this for file servers: a hostname carried a hash of the server's public key, so resolving the name gave you the key with nothing to trust. Tor's v3 `.onion` addresses are the modern version — the address is the service's Ed25519 public key, base32-encoded, and there is no lookup, no issuer, and no way to claim an address you do not hold the key for. IPFS content identifiers, Bitcoin addresses, magnet links, and the peer IDs in every DHT are the same trick applied to content and to nodes.

Self-certifying names are secure and decentralized and occupy Zooko's third corner: nobody can remember `pg6mmjiyjmcrsslvykfwnntlaru7p5svn6y2ymmju6nubxndf4pscryd.onion`. So they always arrive with a second name attached — a bookmark, a link on a page you already trust, a QR code — and *that* binding, from the memorable thing to the self-certifying thing, is where the security question moved. Phishing an onion service means getting a victim to follow a link to the wrong 56 characters, and the DuckDuckGo-shaped indexes that people actually use to find onion addresses are certified bindings in everything but name.

Which is the general lesson. Self-certification does not remove the binding problem. It moves it to the layer above, where it is called "how did you get this link."

## Petnames

Marc Stiegler's [petname systems][petnames] (2005), drawing on Miller and on SDSI, make that layer explicit and argue it is the *right* place for the human-meaningful name.

There are three kinds of name, and the triangle says no single name can be all three:

```text
key           secure, global, not meaningful         a public key, an onion address
petname       meaningful, local, secure              my name for this key, in my own table
nickname      meaningful, global, not secure         what the key's owner calls itself
```

A petname system keeps the key as the real identifier, lets each user attach their own private label to it, and shows the *nickname* only as a hint that must never be trusted on its own. Your phone's contact list is a petname system: the number is the key, "Mum" is the petname, and the caller-ID name the network supplies is the nickname you have learned to distrust. Browser bookmarks, SSH `config` host aliases, and the `# alice's laptop` comments in a WireGuard file are all petnames for keys.

Introduction is how petnames propagate. Alice, whom you already have a petname for, sends you Carol's key with her own petname for it attached; you may adopt it or choose your own. Trust moves along edges that already exist, which is the [capabilities article's](/programming/capabilities.html#the-six-properties) "only connectivity begets connectivity" applied to names, and it is why petname systems and object-capability systems come out of the same tradition. SDSI's linked local names — `K_bob's alice's bank` — are petnames with a formal semantics.

What petnames give up is the global, secure, meaningful name — the thing DNS approximates by being centralized. What they gain is that there is no issuer to compromise. The first time a wallet shows you a contact's address as `Mum` instead of `0x4f…`, or a browser shows a site you have visited under the label you gave it, that is Stiegler's design reaching production, thirty years after SDSI proposed it.

## Transparency: audit instead of prevent

Every approach so far tries to get the binding *right*. Transparency accepts that bindings will sometimes be wrong and makes it impossible for a wrong one to go unseen.

Certificate Transparency, from the [hosts article](/programming/identity-of-hosts.html#transparency-audit-instead-of-prevent), is the deployed proof: every certificate goes into public append-only logs, browsers require proof of inclusion, and domain owners watch for certificates they did not request. Misissuance did not stop. It stopped being quiet, and the CAs that misissued lost their place in the root store.

The messaging world took a decade to follow, because the problem is harder. A CA issues a public certificate; an end-to-end messaging provider holds a *directory* of user → key bindings and hands them out privately, and a malicious or coerced provider can hand one user a wrong key without anyone else seeing. [CONIKS][coniks] (2015) showed how to fix that: the provider commits to its whole directory in a Merkle tree, publishes the root, and gives each lookup a proof of inclusion, so a client can check that the key it received is the one everyone else would receive and that its own binding has not changed behind its back. Keybase built its sigchains on similar ideas; Google published a Key Transparency design in 2017; [WhatsApp deployed][whatsapp-kt] an auditable key directory in 2023, [Apple shipped][apple-ckv] iMessage Contact Key Verification the same year, and Signal followed.

The same move has been applied to bindings that are not about people at all. The [Go checksum database][go-sumdb] is a transparency log for module name → content hash, so that a module proxy cannot serve one developer a different `v1.2.3` than everyone else. Sigstore's Rekor logs artifact signatures, from the [workloads article](/programming/identity-of-workloads.html#sigstore-identity-for-code).

Transparency does not eliminate configured trust. The log's own key is an anchor; a log that forks its history — showing one view to the victim and another to the auditors — has to be caught by gossip between clients or by independent witnesses cosigning the log's roots. What transparency changes is *what* the anchor has to be trusted to do. A CA must be trusted to be honest. A log only has to be trusted to be consistent, and consistency is a property other parties can check.

## Blockchain names

The blockchain answer to Zooko is to run the binding service as a global consensus protocol. Aaron Swartz's [Squaring the Triangle][swartz] (2011) argued that a public ledger could give names that are meaningful, secure, and decentralized at once; Namecoin shipped it months later, and the Ethereum Name Service (2017) is the version people actually use, binding `alice.eth` to an address that anyone can resolve by reading the chain.

It works, at a price. The anchor is the genesis hash and the client software, which the hosts article's [roots of trust](/programming/identity-of-hosts.html#roots-of-trust) already listed among the configured bindings — decentralized consensus over which chain is real, centralized distribution of the constant that says so. There is no recovery: lose the key that controls the name and the name is gone, forever, along with anything bound to it. Names are first-come, and squatting followed immediately. And the triangle did not actually bend. `alice.eth` is meaningful and globally unique, and it is secure exactly to the extent that the chain's consensus and your client's view of it are, which is a more expensive way to be a registry than the one DNS already had.

## Every deployed system is a mix

Laid out one at a time the alternatives look like rivals. Every system that actually ships uses several of them, at different layers, and the interesting design work is in deciding which layer gets which.

```text
Signal        TOFU on first contact; safety numbers for out-of-band confirmation;
              a phone number, bound by SMS, as the global name; key transparency
              to audit the directory; the app store's signing key as the anchor

SSH           TOFU for hosts by default; an SSH CA once there are enough of them;
              authorized_keys as an identity-less capability list; petnames in
              ~/.ssh/config

the web       a certified binding from a CA; audited by CT; hardened by CAA and
              multi-perspective validation; DNS as the name; bookmarks and the
              autocomplete bar as petnames; the OS's root store as the anchor

a wallet      self-certifying addresses; ENS as an optional certified name;
              a contact list of petnames; the client binary as the anchor
```

The pattern is that certified bindings do the bootstrap, because nothing else scales to strangers; transparency does the accountability, because nothing else catches a compromised issuer; petnames do the human layer, because nothing else is both meaningful and local; and TOFU does the edges, where there is no issuer and the first contact is probably fine.

## Where this leaves the name

Six articles ago the [intro](/programming/identity-series-intro.html) asked why we build names on top of keys at all, and gave three reasons: policy is written by humans, responsibility attaches to people, and a person outlives every key they will hold. Nothing in this series has undermined those. Every alternative to the CA either reintroduced a name at the layer above (self-certification), kept the name and changed who writes the binding (TOFU, the web of trust, transparency), or kept the name and changed where it is stored (petnames).

What the series has narrowed is *what the name is for*. Karp's first step, identification, is knowing whom to hold responsible. That is what a name buys and it is all a name buys. It does not tell you what the named party may do, and the [capabilities article](/programming/capabilities.html) spends its length on systems — `authorized_keys`, SPKI authorization certificates, object references, macaroons — that skip the name entirely and attach authority straight to the key or the reference, because for the question *may this request proceed* the name was a detour.

So the honest summary of identity is this. A name is the object that stays still while keys move. Binding one to a key is not cryptography; it is a statement by an issuer you chose to believe, and everything in these articles is about who that issuer is, how long the statement lasts, and what happens when it is wrong. Once you know whose key it is, you have finished identification. Whether they may do anything is the [next series](/programming/authorization-series-intro.html), and its first move is to ask whether you needed to know.

## References <!-- omit in toc -->

1. [ssh-keygen: CERTIFICATES - OpenSSH][ssh-certs]
2. [SKS Keyserver Network Under Attack - Robert J. Hansen (2019)][sks-attack]
3. [Evil 32: Check Your GPG Fingerprints][evil32]
4. [Self-certifying File System - Mazières (1999)][sfs]
5. [An Introduction to Petname Systems - Marc Stiegler (2005)][petnames]
6. [CONIKS: Bringing Key Transparency to End Users - Melara et al. (2015)][coniks]
7. [Deploying key transparency at WhatsApp - Meta Engineering (2023)][whatsapp-kt]
8. [iMessage Contact Key Verification - Apple Security (2023)][apple-ckv]
9. [Proposal: Secure the Public Go Module Ecosystem - Go (2019)][go-sumdb]
10. [Squaring the Triangle - Aaron Swartz (2011)][swartz]

[ssh-certs]: https://man.openbsd.org/ssh-keygen#CERTIFICATES "ssh-keygen: CERTIFICATES"
[sks-attack]: https://gist.github.com/rjhansen/67ab921ffb4084c865b3618d6955275f "SKS Keyserver Network Under Attack"
[evil32]: https://evil32.com/ "Evil 32: Check Your GPG Fingerprints"
[sfs]: https://pdos.csail.mit.edu/papers/sfs:sosp99.pdf "Separating key management from file system security (SFS)"
[petnames]: http://www.skyhunter.com/marcs/petnames/IntroPetNames.html "An Introduction to Petname Systems"
[coniks]: https://www.usenix.org/conference/usenixsecurity15/technical-sessions/presentation/melara "CONIKS: Bringing Key Transparency to End Users"
[whatsapp-kt]: https://engineering.fb.com/2023/04/13/security/whatsapp-key-transparency/ "Deploying key transparency at WhatsApp"
[apple-ckv]: https://security.apple.com/blog/imessage-contact-key-verification/ "iMessage Contact Key Verification"
[go-sumdb]: https://go.dev/blog/module-mirror-launch "Module Mirror and Checksum Database Launched"
[swartz]: http://www.aaronsw.com/weblog/squarezooko "Squaring the Triangle: Secure, Decentralized, Human-Readable Names"
