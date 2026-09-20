---
title:  "Humans: accounts, identity providers, and sessions"
series: "Identity, Part 4"
series_url: "/programming/identity-series-intro.html"
category: programming
date: 2026-07-24
---

> This is Part 4 of a six-part [series on identity](/programming/identity-series-intro.html).
>
> 1. **[Naming and binding](/programming/naming-and-binding.html)** — names stay put, bindings move. Saltzer's lens, from the ARPANET to Kubernetes to PCIe.
> 2. **[Keys are not names](/programming/keys-are-not-names.html)** — what cryptography can say about who, and why anyone bothers with names at all.
> 3. **[Hosts](/programming/identity-of-hosts.html)** — DNS, X.509 and the Web PKI: forty years of binding names to keys, and the anchors it bottoms out in.
> 4. **Humans** — accounts, the trusted third party from Kerberos to OIDC, and sessions.
> 5. **[Workloads and hardware](/programming/identity-of-workloads.html)** — secret zero, SPIFFE, federated CI identity, and attestation.
> 6. **[Binding without a CA](/programming/binding-without-a-ca.html)** — first use, webs of trust, transparency logs, and petnames.

A host has one name and a well-defined owner. A person has dozens of names, owns none of them outright, and cannot hold a private key. This article is about how the internet binds keys to people anyway: what an account is, why every large-scale answer has the same three-party shape, where OpenID Connect actually sits relative to OAuth, and what happens after login — the session — which is where most of the real security lives.

- [What is a person's name?](#what-is-a-persons-name)
- [Accounts, and recovery as the weakest binding](#accounts-and-recovery-as-the-weakest-binding)
- [The trusted third party](#the-trusted-third-party)
  - [Needham–Schroeder and Kerberos](#needhamschroeder-and-kerberos)
  - [SAML: the same shape, through a browser](#saml-the-same-shape-through-a-browser)
  - [OpenID, OAuth, and the login that was not one](#openid-oauth-and-the-login-that-was-not-one)
  - [OpenID Connect](#openid-connect)
- [The id_token is not the access_token](#the-id_token-is-not-the-access_token)
- [What the relying party actually trusts](#what-the-relying-party-actually-trusts)
- [Sessions](#sessions)
  - [The cookie is a binding with a lifetime](#the-cookie-is-a-binding-with-a-lifetime)
  - [Stateful or stateless](#stateful-or-stateless)
  - [Continuous evaluation](#continuous-evaluation)
- [Passkeys did not remove the identity provider](#passkeys-did-not-remove-the-identity-provider)
- [Where a human's chain bottoms out](#where-a-humans-chain-bottoms-out)

## What is a person's name?

Run the [Saltzer test](/programming/naming-and-binding.html) on the identifiers we actually use for people, and ask which table each one really lives in.

**A username** is a local name. `alice` at GitHub and `alice` at Slack are unrelated, and each service is the sole authority for its own namespace. This is SDSI's model from the [previous article](/programming/keys-are-not-names.html#spki-drew-the-line-in-1999) — names relative to a principal — and it is why "Alice" is never a global identifier for a person on the internet.

**An email address** is the closest thing to a global name, and it is built out of the host binding. The domain part is delegated through DNS; the local part is bound by whoever runs mail for that domain. `alice@example.com` names a mailbox, and it names a person only because the mail operator says so. It is the name most accounts are ultimately anchored in, which makes mail operators identity providers whether they wanted the job or not.

**A phone number** is the name of an attachment point on the telephone network. It is used as a person's name everywhere — SMS second factors, WhatsApp and Signal identity, bank verification — and it fails exactly the way the ARPANET names failed. Move the number to a different device, by SIM swap or carrier port-out fraud, and every system that treated it as a person's name follows the attacker. The first article called this the mail example with money attached. It is one of the most exploited bindings on the internet, and it persists because it is the only global human identifier most people already have.

None of these is a key. A person's name is bound to a key, when it is, through an *account*.

## Accounts, and recovery as the weakest binding

An account is a local name at a service plus the credentials that may act as it. Registration writes the binding: it ties the name to a verifier — a password hash, a passkey's public key, a phone number for codes. Login is proof of possession against that verifier, which is the [crypto series' story](/programming/authentication.html) and not repeated here.

What the crypto series does not cover is that every account has a second binding that is usually weaker than the first: **recovery**. A passkey cannot be phished, and a good password hash cannot be cracked, and neither matters if "forgot password" sends a link to an email address whose own recovery goes to a phone number. The account's real security is the minimum over every path that can rebind it, and the recovery paths are the ones nobody threat-models.

This is a binding-table observation. Registration binds name → verifier. Recovery is a second, standing authorization to *rewrite* that binding, held by whoever controls the recovery channel. In Saltzer's terms the account's effective anchor is not its credential but its recovery root, and for most consumer accounts that root is a mailbox or a phone number — the two identifiers above that are not really names for people at all.

Services that take this seriously do what the hosts article's CAs did: they narrow the binding's scope. Recovery codes that live only with the user, recovery contacts who must confirm, cooling-off periods, and — at the far end — no recovery at all, which is the Bitcoin model and the reason lost keys are lost.

## The trusted third party

Every account is local. The internet has tens of thousands of services, and a person cannot maintain a well-bound account at each. The solution the industry converged on is old, and it has the same three-party shape every time it recurs: a party both sides already trust vouches for one to the other.

```text
                   ┌──────────────────┐
                   │  identity        │  holds the user's real credential
                   │  provider        │  issues signed assertions
                   └───────┬──────────┘
        authenticates      │      assertion
              ┌────────────┘              └────────────┐
              ▼                                        ▼
        ┌──────────┐      presents assertion     ┌───────────┐
        │  user    │ ───────────────────────────►│  relying  │  verifies against
        └──────────┘                             │  party    │  the IdP's key
                                                 └───────────┘
```

The identity provider is a certificate authority for people. The assertion is a certificate — issuer, subject, validity, audience, signed — with a lifetime of minutes instead of days. And the relying party's trust reduces to one configured binding: *this* issuer, identified by *this* key.

### Needham–Schroeder and Kerberos

The shape first appears in [Needham and Schroeder's 1978 paper][needham-schroeder], where a trusted server that shares a secret key with every principal issues session keys between pairs of them. MIT's Project Athena turned that into **Kerberos** in the late 1980s ([v5: RFC 1510][rfc1510] in 1993, [RFC 4120][rfc4120] in 2005), and Windows 2000 made it the authentication protocol of every corporate network on earth.

The pieces map directly onto the diagram. The Key Distribution Center is the identity provider. A **ticket** is the assertion: the KDC encrypts "this is Alice, valid until T, here is a session key" under the *service's* key, so the service can decrypt it and nobody else can forge it. The user first obtains a ticket-granting ticket by proving knowledge of their password, then trades it for per-service tickets without re-entering anything — which is single sign-on, in 1988.

Two details matter for what follows. A ticket is *audience-bound*: it is encrypted to one service, and that service cannot replay it elsewhere. And the KDC's trust boundary is the **realm**, with cross-realm trust configured explicitly between KDCs. Both ideas come back with different names.

### SAML: the same shape, through a browser

Kerberos assumes every party shares a secret with the KDC in advance, which works inside one organization and not across the internet. The Security Assertion Markup Language ([SAML 1.0][saml] in 2002, 2.0 in 2005) redid the shape with public-key signatures and with the browser as the transport.

The user visits a service provider, is redirected to their identity provider, authenticates there, and is redirected back carrying a signed XML **assertion**: subject, issuer, audience, conditions, attributes. The service provider verifies the signature against the IdP's public key, which it obtained from the IdP's *metadata* document during setup. That metadata exchange is the configured binding; everything after it is certified.

SAML is what "enterprise SSO" means to this day. It also introduced the web's version of the front-channel problem the [threat model](/programming/threat-model.html) mentions: the assertion travels through the user's browser, so it can be intercepted, replayed, or substituted, and much of SAML's complexity — and its long history of XML signature-wrapping bugs — is defending that path.

### OpenID, OAuth, and the login that was not one

Consumer identity took a different road and got lost for a decade.

**OpenID 1.0** (2005, Brad Fitzpatrick at LiveJournal) tried to make a URL your identity: prove you control `alice.livejournal.com` and any site can log you in. It was decentralized and human-meaningful, it failed the third corner of [Zooko's triangle](/programming/keys-are-not-names.html#zookos-triangle) badly enough — phishing, confusing UX, nobody wanting to run a provider — that it never reached ordinary users.

**OAuth** (1.0 in 2007, 2.0 in 2012) was not an identity protocol at all. It solved delegation: let a third-party app act on your Twitter account without your password. The [capabilities article](/programming/capabilities.html#the-oauth-arc) covers its arc. What matters here is what happened next. Developers noticed that after an OAuth flow they held a token that could call `/me` on the provider's API, and started using that as login: if the token returns Alice's profile, this must be Alice.

It was not. An OAuth access token has no *audience* for the client. It says "the bearer may call this API on Alice's behalf," not "Alice is present at *this* app right now." Any malicious app that Alice had ever authorized could take its own token for her, present it to a second app's login endpoint, and be logged in as her. The token substitution attack is a direct consequence of using an authorization artifact where an identity assertion was needed — SPKI's two certificate types confused in production, at scale, for years.

### OpenID Connect

**OpenID Connect** (final in [February 2014][oidc-core]) fixed this by putting a real identity assertion inside the OAuth flow. Alongside the access token, the provider returns an **`id_token`**: a signed JWT with `iss` (who issued it), `sub` (a stable identifier for the user *at this issuer*), `aud` (the client it was issued to), `exp` and `iat`, and a `nonce` the client chose. The client verifies the signature against the issuer's published keys and checks that `aud` is itself.

That is a SAML assertion, which is a Kerberos ticket, which is Needham–Schroeder — with JSON instead of XML instead of DES. Three decades, one shape.

Two pieces of OIDC plumbing are the parts to remember, because they are where trust actually enters:

- **Discovery.** The issuer publishes `https://issuer/.well-known/openid-configuration`, which points at its endpoints and at a **JWKS** document containing its current signing keys. The client fetches these over TLS.
- **`sub` is local to the issuer.** OIDC deliberately does not define a global user identifier. The same person is `sub: 1234` at one provider and `sub: a8f3…` at another, and the *pair* `(iss, sub)` is the name. This is SDSI again: every issuer runs its own namespace, and the relying party keeps a table mapping each issuer's local names to its own accounts.

## The id_token is not the access_token

OIDC's decision to ride on OAuth means every login flow returns two tokens, and they belong to two different series.

```text
id_token        "Alice authenticated at issuer I, for client C, at time T"
                an identity assertion — this series
                verified by the client, never sent to an API

access_token    "the bearer may call API R with scope S"
                an authorization artifact — the authorization series
                opaque to the client, presented to the resource server
```

The `id_token` binds a name to a session at the client. The `access_token` conveys authority to a resource. Most confusion about "logging in with OAuth" is a confusion between these two objects, and the [authorization models article](/programming/authorization-models.html#identity-is-not-authority) has a ladder that puts them on different rungs. The one thing they share is the axis that ladder calls orthogonal: either can be a bearer artifact or bound to a key the holder must prove, and the migration from the first to the second is the [crypto series' story](/programming/authentication.html).

## What the relying party actually trusts

Follow an OIDC login to its anchor and it is instructive how little of it is about the person.

The relying party trusts an `id_token` because its signature verifies under a key from the issuer's JWKS. It trusts the JWKS because it fetched it from `https://accounts.example.com/.well-known/…` over TLS. It trusts that TLS connection because a certificate bound `accounts.example.com` to a key, signed by a CA in its root store. That certificate was issued to whoever controlled the DNS name at issuance time.

So a human's identity at internet scale rests on a host's identity, which rests on DNS, which rests on a root store and a root-hints file. Everything in the [hosts article](/programming/identity-of-hosts.html) is load-bearing for every login on the web, and an attacker who can hijack an IdP's domain — by DNS, by BGP, by a misissued certificate — can mint an `id_token` for anyone at any relying party that trusts it.

The only thing the relying party ever configured was the issuer URL and a client ID. That is the configured binding. The person never appears in it.

## Sessions

Login is one round trip. Everything after it — hours, days, weeks of requests — happens under a **session**, and the session is where most of the actual security lives and least of the writing.

The crypto series' [secure channels post](/programming/secure-channels.html) draws the distinction: a channel protects bytes between two endpoints for one connection; a session is the application's notion of a continuing relationship that outlives any channel. A session is a binding too, from an identifier the browser will present to the principal who authenticated, with a lifetime.

### The cookie is a binding with a lifetime

Netscape invented the cookie in 1994 to give the stateless web a memory, and it was standardized in [RFC 2109][rfc2109] (1997) and rewritten in [RFC 6265][rfc6265] (2011). A session cookie is a bearer instrument: whoever presents it is the user, which is why session theft is the payoff of most web attacks and why cookie attributes — `Secure`, `HttpOnly`, `SameSite`, `__Host-` prefixes — exist to narrow who can present it.

The binding's lifetime is the design decision. Short sessions re-authenticate constantly and users hate them; long sessions mean a stolen cookie works for a month and a fired employee stays logged in. The usual compromise is a short access credential that is silently renewed from a longer-lived **refresh token**, so that the frequently-presented artifact is short-lived and the long-lived one is presented rarely and only to the issuer. Sliding expiry — extend on activity, expire on idleness — is the same idea keyed to behaviour.

### Stateful or stateless

There are two ways to represent a session, and they are the [enforcement article's](/programming/authority-enforcement.html#what-can-change-between-check-and-use) re-evaluate-or-materialize trade in miniature.

A **stateful** session stores a record server-side and hands the browser an opaque key. Every request looks the record up. Revocation is trivial — delete the row — and the cost is a lookup per request and a store every server can reach.

A **stateless** session puts the claims in the cookie itself, signed: a JWT. No lookup, no shared store, and *no revocation*. The binding is a copy in the browser, and there is no mechanism to reach it, so the only control is expiry. This is why stateless sessions are paired with short lifetimes and refresh tokens, and why "just use JWTs for sessions" is the [first article's](/programming/naming-and-binding.html) scope-of-a-binding lesson waiting to be relearned.

### Continuous evaluation

Both approaches share a deeper problem: the session was bound at login, and the facts it was bound on drift. The user's device gets compromised, their password is reset elsewhere, they leave the company, the IdP revokes their account. The relying party's session knows none of this. Its binding is stale and nothing tells it.

OIDC added back-channel logout so an issuer can notify relying parties that a session ended. The OpenID Foundation's [Shared Signals Framework][ssf] and CAEP generalize it: issuers emit events — credential changed, device posture failed, session revoked — and relying parties subscribe. The industry name for the goal is *continuous access evaluation*, and it is an admission that a login is a binding with a lifetime, and that the lifetime should be governed by the binding service rather than by a timer set at issuance.

## Passkeys did not remove the identity provider

It is tempting to read passkeys as the end of this story: the user holds a private key, the site holds a public key, no third party. That is true at *one* site, and it is a genuine improvement in how the credential is held — the [crypto series](/programming/authentication.html) covers why.

It does not change the three-party shape at scale. A passkey binds a key to an account *at one relying party*; registration is trust on first use, and the account's recovery path is unchanged. Across relying parties, the dominant flow is still to passkey into Google or Apple or Microsoft and then OpenID Connect out to everyone else. The passkey replaced the password at the IdP. The IdP is still there.

And synced passkeys moved the anchor one level up. A passkey that syncs through iCloud Keychain or Google Password Manager is recoverable from the *platform account*, so the platform account is now the recovery root for every passkey it holds. That is a new binding service with a new configured anchor — your Apple ID — and the platform vendors are now the largest identity providers on earth by a different route.

## Where a human's chain bottoms out

A host's chain ends at a root store. Where does a person's end?

For most people, today, at a platform account and a phone number, mutually recoverable from each other — which is a cycle, not an anchor, and the reason account-takeover is an industry. Governments are the other candidate. The EU's [Digital Identity Wallet][eudi] and the mobile driving licence standards put a state-issued credential on a phone, and the W3C's [Verifiable Credentials][vc] model gives it the SPKI shape: an issuer signs a statement about a subject's key, the holder presents it, the verifier checks the issuer. That would make the state the configured anchor for people the way root programs are for hosts, with everything that implies in both directions.

Either way the structure is the one this series keeps finding. A person is a name. The name is bound to keys through accounts, the accounts through providers, the providers through the Web PKI, and the Web PKI through a file that shipped with the operating system. The next article follows the same chain for a principal that is much easier to bind, because the thing doing the binding is the thing that created it.

## References <!-- omit in toc -->

1. [Using Encryption for Authentication in Large Networks of Computers - Needham & Schroeder (1978)][needham-schroeder]
2. [RFC 1510: The Kerberos Network Authentication Service (V5) (1993)][rfc1510]
3. [RFC 4120: The Kerberos Network Authentication Service (V5) (2005)][rfc4120]
4. [SAML 2.0 Specifications - OASIS][saml]
5. [OpenID Connect Core 1.0][oidc-core]
6. [RFC 2109: HTTP State Management Mechanism (1997)][rfc2109]
7. [RFC 6265: HTTP State Management Mechanism (2011)][rfc6265]
8. [Shared Signals Framework - OpenID Foundation][ssf]
9. [EU Digital Identity Wallet][eudi]
10. [Verifiable Credentials Data Model 2.0 - W3C][vc]

[needham-schroeder]: https://dl.acm.org/doi/10.1145/359657.359659 "Using Encryption for Authentication in Large Networks of Computers"
[rfc1510]: https://www.rfc-editor.org/rfc/rfc1510 "RFC 1510: The Kerberos Network Authentication Service (V5)"
[rfc4120]: https://www.rfc-editor.org/rfc/rfc4120 "RFC 4120: The Kerberos Network Authentication Service (V5)"
[saml]: https://docs.oasis-open.org/security/saml/v2.0/ "SAML 2.0 Specifications - OASIS"
[oidc-core]: https://openid.net/specs/openid-connect-core-1_0.html "OpenID Connect Core 1.0"
[rfc2109]: https://www.rfc-editor.org/rfc/rfc2109 "RFC 2109: HTTP State Management Mechanism"
[rfc6265]: https://www.rfc-editor.org/rfc/rfc6265 "RFC 6265: HTTP State Management Mechanism"
[ssf]: https://openid.net/wg/sharedsignals/ "Shared Signals Working Group - OpenID Foundation"
[eudi]: https://ec.europa.eu/digital-building-blocks/sites/display/EUDIGITALIDENTITYWALLET "EU Digital Identity Wallet"
[vc]: https://www.w3.org/TR/vc-data-model-2.0/ "Verifiable Credentials Data Model 2.0"
