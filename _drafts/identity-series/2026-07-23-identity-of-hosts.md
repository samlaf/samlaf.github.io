---
title:  "Hosts: DNS, X.509 and the Web PKI"
series: "Identity, Part 3"
series_url: "/programming/identity-series-intro.html"
category: programming
date: 2026-07-23
---

> This is Part 3 of a six-part [series on identity](/programming/identity-series-intro.html).
>
> 1. **[Naming and binding](/programming/naming-and-binding.html)** — names stay put, bindings move. Saltzer's lens, from the ARPANET to Kubernetes to PCIe.
> 2. **[Keys are not names](/programming/keys-are-not-names.html)** — what cryptography can say about who, and why anyone bothers with names at all.
> 3. **Hosts** — DNS, X.509 and the Web PKI: forty years of binding names to keys, and the anchors it bottoms out in.
> 4. **[Humans](/programming/identity-of-humans.html)** — accounts, the trusted third party from Kerberos to OIDC, and sessions.
> 5. **[Workloads and hardware](/programming/identity-of-workloads.html)** — secret zero, SPIFFE, federated CI identity, and attestation.
> 6. **[Binding without a CA](/programming/binding-without-a-ca.html)** — first use, webs of trust, transparency logs, and petnames.

A host's identity is a DNS name, and the internet's answer to "is this key really `example.com`'s" is the Web PKI. This article is the history of both, read as two [binding tables](/programming/naming-and-binding.html) — name → address, and name → key — and of the forty years it took to notice that the second one was built on top of the first.

- [Names before keys: HOSTS.TXT to DNS](#names-before-keys-hoststxt-to-dns)
  - [DNSSEC, and the fix that never shipped](#dnssec-and-the-fix-that-never-shipped)
- [X.500 and the directory that never existed](#x500-and-the-directory-that-never-existed)
- [The Web PKI](#the-web-pki)
  - [What a certificate actually binds](#what-a-certificate-actually-binds)
  - [The weakest-link problem](#the-weakest-link-problem)
- [The repairs](#the-repairs)
  - [Pinning: early binding, and why it died](#pinning-early-binding-and-why-it-died)
  - [Transparency: audit instead of prevent](#transparency-audit-instead-of-prevent)
  - [CAA and multi-perspective validation: hardening the DNS dependency](#caa-and-multi-perspective-validation-hardening-the-dns-dependency)
  - [ACME: automating the binding](#acme-automating-the-binding)
  - [Revocation, and shortening the binding instead](#revocation-and-shortening-the-binding-instead)
- [What ultimately authenticates a key?](#what-ultimately-authenticates-a-key)
- [Roots of trust](#roots-of-trust)

## Names before keys: HOSTS.TXT to DNS

For its first fifteen years the internet's name→address binding table was a single text file. `HOSTS.TXT` was maintained by the Network Information Center at SRI, and every host fetched a copy by FTP. [RFC 952][rfc952] (1985) documents the format, by which point the file was already unworkable: one editor, one copy, a growth rate that outran the bandwidth to distribute it, and names colliding as fast as new sites joined.

Paul Mockapetris's DNS ([RFC 882 and 883][rfc882], 1983; [RFC 1034 and 1035][rfc1034], 1987) fixed it with a move that turns out to be the template for everything in this series: **it distributed the authority to write the binding**. A zone is the unit of administration. Whoever runs the zone for `example.com` writes the bindings under it, and nobody else can. The root delegates to the TLDs, the TLDs delegate to registrants, and the answer to Saltzer's question — who may change this table, and where do they go — is written into the tree.

This is also the name server Saltzer describes at the end of RFC 1498: it takes a service name and hands back attachment points, fusing his first two bindings in one lookup. What DNS did not do, at all, was authenticate the answer. A resolver asked a question over UDP and believed whichever reply arrived first with the right transaction ID. Cache poisoning was understood in the early 1990s and became a headline in 2008, when [Dan Kaminsky][kaminsky] showed it could be done reliably against every deployed resolver in about ten seconds.

### DNSSEC, and the fix that never shipped

DNSSEC signs the bindings. Each zone holds a key, signs its records, and publishes a hash of its key in the parent zone, so a resolver can walk from a configured root key down to any record and verify every step. [RFC 2065][rfc2065] came out in 1997; the redesign that is actually deployed ([RFC 4033–4035][rfc4033]) came out in 2005; the root zone was finally signed in July 2010, and the root key was [rolled for the first time][ksk-rollover] in 2018.

That is a chain of certified bindings with a configured anchor — exactly the shape the [previous article](/programming/keys-are-not-names.html) set out — and it made an obvious next step available. If the DNS is authenticated, put the host's *key* in it. That is DANE ([RFC 6698][rfc6698], 2012): a `TLSA` record under `_443._tcp.example.com` naming the certificate or key the server will present. The CA becomes optional. The registrar, who already controls the name, controls the binding to the key directly.

Browsers never shipped it. Chrome experimented with DNSSEC-stapled certificates in 2011 and [removed the code][langley-dane] a year later. The reasons Langley gave are worth listing, because they recur every time a cleaner design meets deployment:

- DNSSEC deployment was thin and validation was rare, so the chain often could not be built.
- Many home routers and hotel networks stripped or mangled the records — the last-mile problem.
- The root and many TLDs used 1024-bit RSA, weaker than the CA roots browsers already trusted.
- It replaced ~150 CAs with one hierarchy of governments and registrars, which not everyone considered an improvement.

The internet ended up with two parallel binding services for the same name — DNS for the address, the Web PKI for the key — and, as the rest of this article shows, the second one quietly depends on the first anyway.

## X.500 and the directory that never existed

X.509 was not designed for the web. It was designed in 1988 as the authentication framework for **X.500**, the CCITT's plan for a single global electronic directory. Every person and organization on earth would have a Distinguished Name — `C=US, O=Acme, OU=Sales, CN=Alice Smith` — and the directory would let you look anyone up. A certificate bound a Distinguished Name to a key so the directory could be authenticated.

The directory never existed. X.500 required a global naming authority that governments and telcos would run cooperatively, and the internet grew instead. But the certificate format survived its parent, and its assumptions came with it: a single global hierarchy of names, and a naming authority at the top of it.

The first attempt to graft that onto the internet was Privacy Enhanced Mail ([RFC 1421–1424][rfc1421], 1993), which proposed a single Internet Policy Certification Authority at the root, with every organization's CA chaining to it. It failed for the same reason X.500 did. Nobody wanted to be under one root, and nobody agreed on whose.

Ellison and Schneier's [Ten Risks of PKI][ten-risks] (2000) is the post-mortem, and the risk they put first is the one this series keeps circling: "Who do we trust, and for what?" A CA's signature is a statement by a company you have never heard of, and the client that verifies it usually cannot say what the statement means. The X.500 assumption that names were globally meaningful, and that binding them to keys was a clerical task, was the thing that never survived contact.

## The Web PKI

What actually deployed was messier. Netscape shipped SSL 2.0 in 1995 with X.509 certificates for server identity, and RSA spun VeriSign out the same year to sell them. A certificate authority's job became: check that the applicant controls the domain, sign a certificate binding the domain to their key, get your root into the browser. Anyone whose root was in the browser could vouch for any name on the internet.

X.509 version 3 (1996, later [RFC 5280][rfc5280]) added extensions, and one of them quietly abandoned X.500: `subjectAltName`, where the DNS name goes. The Distinguished Name is still in every certificate, and browsers have not looked at it for server identity in years. The binding that matters is `dNSName` → public key.

### What a certificate actually binds

It is worth being precise about the entry in the table, because it is narrower than the padlock icon suggests.

A domain-validated certificate says: *at issuance time, a party that controlled this DNS name asked us to bind it to this key*. Control is demonstrated by responding to a challenge — serving a file at `http://example.com/.well-known/acme-challenge/…`, or publishing a `TXT` record. Both challenges resolve through DNS. So the Web PKI's name → key binding is a *derived* binding: it is issued to whoever can make the name → address binding point at them, for the few seconds the CA is looking.

This is why the two histories in this article are one history. Whoever controls DNS for a name can obtain a certificate for it. That includes the registrant, the registrar, the DNS host, anyone who has poisoned the CA's resolver, and — as [the 2018 hijack of Amazon's Route 53 prefixes][bgp-mew] demonstrated against MyEtherWallet — anyone who can announce the DNS server's IP range over BGP for long enough to answer a challenge. DANE would have made the dependency explicit. The Web PKI made it implicit, then spent a decade discovering it.

Extended Validation certificates tried to bind more — a legal entity, verified by paperwork — and browsers displayed the company name in green. The extra binding was real but unusable: users did not notice when it was absent, [Stripe, Inc. of Kentucky][ev-stripe] could get one, and by 2019 Chrome and Firefox had removed the UI. The lesson generalizes. A binding only protects a decision that some verifier actually makes.

### The weakest-link problem

The Web PKI has one structural flaw and every incident in its history is that flaw exercised. Any trusted root can issue for any name. There is no relationship between the hierarchy of names and the set of CAs, so the security of `google.com`'s binding is the security of the *least* careful of ~150 organizations, some of them government-run, several of them acquired and re-acquired.

- **2011, Comodo.** A reseller's account was compromised and used to issue certificates for `mail.google.com`, `login.yahoo.com`, `login.live.com`, `addons.mozilla.org`.
- **2011, DigiNotar.** A Dutch CA was fully compromised; over five hundred certificates were issued, including a wildcard for `*.google.com` that was used to intercept Gmail for roughly 300,000 users in Iran. DigiNotar was removed from every root store and went bankrupt within weeks. It remains the clearest demonstration that a binding service *is* the target.
- **2012, Trustwave** sold a subordinate CA to a customer for the explicit purpose of intercepting TLS on its own network — a legitimate certificate for every site on the internet, by design.
- **2013, TURKTRUST** mistakenly issued two intermediate certificates to customers who should have received leaf certificates; one was used to issue for `*.google.com`.
- **2015, CNNIC / MCS Holdings.** Another intermediate, another `google.com` certificate, another root removed.
- **2016–2018, WoSign, StartCom, Symantec.** Misissuance and backdated certificates discovered largely through Certificate Transparency logs. Google [announced a staged distrust of Symantec][symantec-distrust], at the time the largest CA by volume, and completed it in October 2018.

Note the pattern in the last group: the failures were *found in the logs*. That is the repair below doing its job.

## The repairs

The Web PKI could not be replaced, so it was patched, and the patches are a catalogue of the four ways a binding can be written from the [previous article](/programming/keys-are-not-names.html#four-ways-a-binding-gets-written).

### Pinning: early binding, and why it died

If you know which key `example.com` should have, refuse anything else. Chrome shipped a hardcoded pin list for Google properties in 2011, which is how the DigiNotar certificate was caught. HTTP Public Key Pinning ([RFC 7469][rfc7469], 2015) generalized it: a site sends a header naming the keys it will use, and the browser remembers.

It was removed from Chrome in 2019. In Saltzer's vocabulary, HPKP is a design-time binding cached in every client, and it broke the way design-time bindings break: a site that lost or rotated its key locked out every visitor for the pin's lifetime, an attacker who could set one header could brick a site (*hostile pinning*), and the recovery path required a second key kept somewhere safer than the first. The scope of a binding is where copies of it live, and a pin lived in every browser on earth.

Pinning survives in mobile apps and in machine-to-machine settings, where the client and server are operated by the same party and rotation can be coordinated. It died for the open web because the web's whole design is that client and server have never met.

### Transparency: audit instead of prevent

Certificate Transparency ([RFC 6962][rfc6962], 2013; [RFC 9162][rfc9162], 2021) gives up on preventing misissuance and makes it impossible to hide. Every certificate is submitted to append-only public logs; the log returns a Signed Certificate Timestamp; browsers refuse certificates that do not carry SCTs from enough independent logs. Chrome made this mandatory for all certificates in April 2018.

The effect is that `google.com` can watch the logs for certificates it did not request, and anyone can audit any CA's entire output. Misissuance still happens. It happens in public, and it gets a CA distrusted. Almost every root-store removal since 2016 started with someone reading a log.

The trust model shifts in a way the [last article](/programming/binding-without-a-ca.html) returns to: the logs' own keys are now anchors, baked into the browser next to the CA roots, and a log that misbehaves needs its own detection (gossip, witnesses). Transparency does not remove the need for configured trust. It moves it to a party whose only job is to be boring.

### CAA and multi-perspective validation: hardening the DNS dependency

Since the Web PKI depends on DNS, two repairs went into DNS.

**CAA** ([RFC 6844][rfc6844], 2013; mandatory for CAs since September 2017) lets a domain publish which CAs may issue for it. It restores the one relationship the Web PKI lacked — between the name hierarchy and the set of issuers — and it does it in the name owner's own zone. It does not help against an attacker who controls DNS, since they can rewrite the CAA record too, but it eliminates the accidental class of misissuance and it turns "any CA, any name" into "the CAs this name has chosen."

**Multi-perspective issuance corroboration** (required by the CA/Browser Forum from 2025) makes the CA run its domain-validation challenge from several network vantage points at once. A BGP hijack that fools the CA's datacenter in Virginia has to fool the ones in Frankfurt and Singapore too. It is a direct response to the MyEtherWallet attack, and it is the Web PKI acknowledging in its own rules that its binding is derived from routing.

### ACME: automating the binding

Let's Encrypt launched in December 2015 and its protocol, ACME, became [RFC 8555][rfc8555] in 2019. It automated domain validation end to end: a client proves control of a name, receives a certificate, and renews it without a human. Certificates became free, the encrypted share of web traffic went from under half to nearly all of it in five years, and Let's Encrypt became the largest CA on the internet.

For this series the important effect is not the price. It is that automation made **short bindings** possible, which made the next repair possible.

### Revocation, and shortening the binding instead

A certificate is an entry copied into every client that connects. When the key leaks, you have to un-copy it, and every mechanism for doing so has been a compromise:

- **CRLs** — the CA publishes a signed list of revoked serials. Lists grew to megabytes and clients stopped fetching them.
- **OCSP** ([RFC 2560][rfc2560], 1999; [RFC 6960][rfc6960]) — ask the CA about one certificate, live. It leaked browsing history to CAs, added latency, and clients "soft-failed" when the responder was down, so an attacker who could block OCSP could use a revoked certificate. OCSP stapling let the server attach a fresh response, which helped where it was deployed.
- **Browser-side summaries** — Chrome's CRLSets (2012) and Firefox's CRLite ship a compressed set of revocations with the browser. Effective, but the browser vendor decides what fits.

Let's Encrypt shut its OCSP responders down in 2025 and moved to CRLs only. The industry's real answer was different: stop making bindings that last long enough to need revoking. Maximum certificate lifetimes went from five years to 39 months (2015), to 825 days (2018), to 398 days (2020, after Apple forced the issue), and under the CA/Browser Forum's [2025 ballot][cabf-br] they fall to 200 days in 2026, 100 in 2027, and **47 days** in 2029.

That is Saltzer's binding-time trade made deliberately. A short binding is re-resolved constantly, so a stale copy ages out on its own and revocation matters less. The cost is the one the [first article](/programming/naming-and-binding.html#turning-the-lens-on-keys) named: the binding service has to be available all the time, and issuance itself becomes the availability-critical path. A CA outage used to be an inconvenience for people renewing this month. At 47 days it is an outage for the internet.

## What ultimately authenticates a key?

Step back to the handshake. A channel's session keys come out of an ephemeral Diffie–Hellman exchange — so what stops an attacker from just running that exchange with you themselves? The answer is that one long-term key in the handshake is *authenticated*, and that authentication chains upward until it hits something you trusted before the connection began.

![image](/assets/crypto-series/roots-of-trust-and-attestation/session-key-authentication-chain.png)

There are two chains to the same destination here. The left one is the Web PKI as this article has described it: the leaf certificate binds a domain to a key, signed by an intermediate, signed by a root CA baked into your browser. The right one is hardware attestation, the subject of the [workloads article](/programming/identity-of-workloads.html): an Intel root signs an attestation key, which signs a quote whose `REPORTDATA` commits to the session key's hash. Either way, the session key is only as trustworthy as the out-of-band anchor at the top of its chain.

## Roots of trust

So where do those anchors come from? They're never derived — they're *configured*, out of band, by software vendors, OS installs, and DHCP.

![image](/assets/crypto-series/roots-of-trust-and-attestation/roots-of-trust-out-of-band.png)

The CA root bundle is the one everyone knows, but a typical machine holds far more configured bindings than that, and every one of them is upstream of the padlock.

**CT log keys.** Modern Chrome and Safari refuse certificates that don't carry Signed Certificate Timestamps from a list of trusted logs. The public keys of those logs are baked into browser source code, just like the CA roots. Without them, the certificate chain alone isn't sufficient for trust.

**NTP server addresses, and optionally NTS roots.** Certificate validity windows are time-bounded, so every check depends on a clock that's roughly right — and the shorter certificates get, the more it matters. NTP server addresses arrive via DHCP or hardcoded fallback (`pool.ntp.org`, `time.apple.com`). Plain NTP is unauthenticated; Network Time Security adds a TLS-rooted chain on top, which means it ultimately leans on the CA roots anyway.

**DNS root hints and the root KSK.** The addresses of the thirteen root server clusters ship in a file with every resolver, and the DNSSEC root key ships with every validating one. The name → address table has its own anchor, and everything above depended on it.

**OS and package signing keys.** The browser binary itself was installed by `apt`, `dnf`, `pacman`, the Mac App Store or Windows Update, each with its own keyring: the Debian release key, Apple's notarization key, Microsoft's Authenticode roots. Whatever signed `firefox.deb` is upstream of every root-store decision Firefox makes.

**UEFI Secure Boot Platform Key.** The firmware-level root that authorized booting the OS that's running the browser. Burned in by the OEM at manufacture, with Microsoft's key enrolled as the de facto standard for x86. This is the deepest software-level trust anchor on a typical machine — everything else descends from it.

**Hardware vendor roots.** Intel's SGX/TDX root, AMD's SEV-SNP root, Apple's Secure Enclave root, ARM's TrustZone roots, every TPM manufacturer's endorsement-key CA. Same pattern, different silicon, and the subject of the [workloads article](/programming/identity-of-workloads.html).

**Blockchain genesis hashes** are the same kind of object. Ethereum's chain is defined by a specific genesis block whose hash is hardcoded in clients; "which chain is the real chain" is answered by `apt-get install geth` shipping that constant. Self-certifying keys at the application layer, sure, but the *configuration* that picks one chain over a fork lives in the same out-of-band place as the root bundle.

Which is the note to end host identity on. Forty years of protocol design, and the answer to "why do you believe this key is `example.com`" is: because a file that shipped with your operating system said to believe the people who said so. Every certified binding is a configured binding with extra steps. The steps are what make it scale, and the configured part is what makes it possible to attack.

## References <!-- omit in toc -->

1. [RFC 952: DoD Internet Host Table Specification][rfc952]
2. [RFC 882: Domain Names — Concepts and Facilities - Mockapetris (1983)][rfc882]
3. [RFC 1034: Domain Names — Concepts and Facilities (1987)][rfc1034]
4. [Dan Kaminsky - Wikipedia][kaminsky]
5. [RFC 2065: Domain Name System Security Extensions (1997)][rfc2065]
6. [RFC 4033: DNS Security Introduction and Requirements (2005)][rfc4033]
7. [Root KSK Rollover - ICANN][ksk-rollover]
8. [RFC 6698: DANE TLSA (2012)][rfc6698]
9. [Why not DANE in browsers - Adam Langley][langley-dane]
10. [RFC 1421: Privacy Enhancement for Internet Electronic Mail (1993)][rfc1421]
11. [Ten Risks of PKI - Ellison & Schneier (2000)][ten-risks]
12. [RFC 5280: Internet X.509 PKI Certificate and CRL Profile][rfc5280]
13. [BGP leaks and cryptocurrencies - Cloudflare (2018)][bgp-mew]
14. [Extended Validation Certificates are Dead - Troy Hunt][ev-stripe]
15. [Chrome's Plan to Distrust Symantec Certificates - Google (2017)][symantec-distrust]
16. [RFC 7469: Public Key Pinning Extension for HTTP][rfc7469]
17. [RFC 6962: Certificate Transparency (2013)][rfc6962]
18. [RFC 9162: Certificate Transparency Version 2.0 (2021)][rfc9162]
19. [RFC 6844: DNS Certification Authority Authorization][rfc6844]
20. [RFC 8555: Automatic Certificate Management Environment][rfc8555]
21. [RFC 2560: Online Certificate Status Protocol][rfc2560]
22. [RFC 6960: OCSP][rfc6960]
23. [Baseline Requirements - CA/Browser Forum][cabf-br]

[rfc952]: https://www.rfc-editor.org/rfc/rfc952 "RFC 952: DoD Internet Host Table Specification"
[rfc882]: https://www.rfc-editor.org/rfc/rfc882 "RFC 882: Domain Names — Concepts and Facilities"
[rfc1034]: https://www.rfc-editor.org/rfc/rfc1034 "RFC 1034: Domain Names — Concepts and Facilities"
[kaminsky]: https://en.wikipedia.org/wiki/Dan_Kaminsky "Dan Kaminsky - Wikipedia"
[rfc2065]: https://www.rfc-editor.org/rfc/rfc2065 "RFC 2065: Domain Name System Security Extensions"
[rfc4033]: https://www.rfc-editor.org/rfc/rfc4033 "RFC 4033: DNS Security Introduction and Requirements"
[ksk-rollover]: https://www.icann.org/resources/pages/ksk-rollover "Root KSK Rollover - ICANN"
[rfc6698]: https://www.rfc-editor.org/rfc/rfc6698 "RFC 6698: The DNS-Based Authentication of Named Entities (DANE) TLSA"
[langley-dane]: https://www.imperialviolet.org/2015/01/17/notdane.html "Why not DANE in browsers - ImperialViolet"
[rfc1421]: https://www.rfc-editor.org/rfc/rfc1421 "RFC 1421: Privacy Enhancement for Internet Electronic Mail"
[ten-risks]: https://www.schneier.com/academic/archives/2000/01/ten_risks_of_pki.html "Ten Risks of PKI - Ellison & Schneier"
[rfc5280]: https://www.rfc-editor.org/rfc/rfc5280 "RFC 5280: Internet X.509 Public Key Infrastructure Certificate and CRL Profile"
[bgp-mew]: https://blog.cloudflare.com/bgp-leaks-and-crypto-currencies/ "BGP leaks and cryptocurrencies - Cloudflare"
[ev-stripe]: https://www.troyhunt.com/extended-validation-certificates-are-dead/ "Extended Validation Certificates are Dead - Troy Hunt"
[symantec-distrust]: https://security.googleblog.com/2017/09/chromes-plan-to-distrust-symantec.html "Chrome's Plan to Distrust Symantec Certificates"
[rfc7469]: https://www.rfc-editor.org/rfc/rfc7469 "RFC 7469: Public Key Pinning Extension for HTTP"
[rfc6962]: https://www.rfc-editor.org/rfc/rfc6962 "RFC 6962: Certificate Transparency"
[rfc9162]: https://www.rfc-editor.org/rfc/rfc9162 "RFC 9162: Certificate Transparency Version 2.0"
[rfc6844]: https://www.rfc-editor.org/rfc/rfc6844 "RFC 6844: DNS Certification Authority Authorization (CAA) Resource Record"
[rfc8555]: https://www.rfc-editor.org/rfc/rfc8555 "RFC 8555: Automatic Certificate Management Environment (ACME)"
[rfc2560]: https://www.rfc-editor.org/rfc/rfc2560 "RFC 2560: X.509 Internet PKI Online Certificate Status Protocol"
[rfc6960]: https://www.rfc-editor.org/rfc/rfc6960 "RFC 6960: X.509 Internet PKI Online Certificate Status Protocol - OCSP"
[cabf-br]: https://cabforum.org/working-groups/server/baseline-requirements/ "Baseline Requirements - CA/Browser Forum"
