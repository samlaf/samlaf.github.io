---
title:  "Capabilities: authority you hold, not authority you are"
category: programming
date:   2026-09-02
---

> This is the second of four articles on authorization.
>
> 1. **[Authorization models](/programming/authorization-models.html)** — what every system computes, and who may change it.
> 2. **Capabilities** — authority you hold, not authority you are.
> 3. **[How authority is enforced](/programming/authority-enforcement.html)** — what makes any of it binding.
> 4. **[LLM sandboxing](/programming/llm-sandbox.html)** — the gateway, correct and unavoidable.

- [Four things get called capabilities](#four-things-get-called-capabilities)
  - [The six properties](#the-six-properties)
  - [Where the real systems land](#where-the-real-systems-land)
- [Designation and authority](#designation-and-authority)
  - [The confused deputy is structural](#the-confused-deputy-is-structural)
- [Possession is authorization](#possession-is-authorization)
- [When and where the decision happens](#when-and-where-the-decision-happens)
  - [Cannot, not do not](#cannot-not-do-not)
- [Delegation](#delegation)
  - [The OAuth arc](#the-oauth-arc)
  - [Service chaining](#service-chaining)
  - [The control you think you have](#the-control-you-think-you-have)
- [Granularity, and the two routes down](#granularity-and-the-two-routes-down)
- [The three objections](#the-three-objections)
  - [Revocation needs composability](#revocation-needs-composability)
  - [Accountability is the one ACLs lose](#accountability-is-the-one-acls-lose)
  - [The patches converge](#the-patches-converge)
  - [The convergence is not symmetric](#the-convergence-is-not-symmetric)
  - [Complete over the intended state, not the reachable state](#complete-over-the-intended-state-not-the-reachable-state)
- [Policy and mechanism](#policy-and-mechanism)
- [Local authority versus global knowledge](#local-authority-versus-global-knowledge)
  - [What running both looks like](#what-running-both-looks-like)
- [Where the property can be bought](#where-the-property-can-be-bought)
- [References](#references)


The [previous article](/programming/authorization-models.html) ended by splitting authorization into five concerns and noting that four of them — policy, delegation, credential format, identity — are where the industry has spent twenty years. The fifth is communication, and it is where the only structural difference between capabilities and everything else lives.

This article is about that difference. It is also about a word that has been ruined by overuse. "Capability" names at least four distinct things, the arguments people have about capabilities are usually arguments about different ones, and most of the famous objections are true of some and false of others.

## Four things get called capabilities

Miller, Yee and Shapiro's [Capability Myths Demolished](https://cgi.cse.unsw.edu.au/~cs9242/20/papers/Miller_YS_03.pdf) is the paper that sorts this out, and its central move is to define four models rather than two.

```text
Model 1   ACLs as columns
          authority stored at the resource; the subject presents a name

Model 2   capabilities as rows
          a row of the access matrix, held by the kernel on the subject's
          behalf; what a C-list is

Model 3   capabilities as keys
          unforgeable, copyable tokens; hand one to anyone you like;
          what the key metaphor describes

Model 4   object capabilities
          unforgeable references; designation and authority are one thing;
          you can only pass one to someone you can already reach
```

Model 1 is what you run. Model 4 is what every major capability system actually implements. Models 2 and 3 are how capabilities get *explained* — as a naive reading of Lampson's matrix, and as the key metaphor — and both explanations are wrong in ways that generate the standard objections.

### The six properties

The paper separates the models with six tests. This table is the densest thing in these four articles and it is worth reading slowly.

| | | M1 ACLs | M2 rows | M3 keys | M4 ocaps |
|---|---|---|---|---|---|
| **A** | Does designating a resource always convey its authority? | no *(impossible)* | unspecified | **no** | yes |
| **B** | Can subjects create new subjects? | no *(in practice)* | yes | yes | yes |
| **C** | Is the power to edit authorities aggregated by subject? | no *(in practice)* | yes | yes | yes |
| **D** | Must subjects select which authority to use? | no | **no** | yes | yes |
| **E** | Are resources also subjects? | unspecified | unspecified | **no** | yes |
| **F** | Must X already reach Y to pass Y an authority? | unspecified | unspecified | **no** | yes |

Four of these deserve names you will use again.

**Property A — no designation without authority.** Saying *which* object and saying *that you may use it* are the same act. The key model fails this, and the failure is easy to miss: you can hold a key without knowing which door it opens, and you can point at a door without holding its key. Designator and authority travel separately and something has to recombine them.

**Property D — no ambient authority.** You must select the authority you exercise. Unix fails this: `open()` takes a path and no credential, and the call simply succeeds or fails. Miller's image for ambient authority is a world of doors and no keys, where a door opens if it deems you worthy.

**Property E — composability.** Resources are also subjects. Without it you cannot build a revocable forwarder, because a forwarder is a resource that is also a subject.

**Property F — access-controlled delegation channels.** To hand Bob a capability you must already hold a capability to Bob. This is Miller's **"only connectivity begets connectivity"** stated as a test, and it is the property everything else in this article eventually reduces to.

E and F are the [previous article's](/programming/authorization-models.html#make-both-axes-the-same-set) square matrix, arriving as tests. **E is the squaring itself** — one entity set on both axes, so a thing can be a row and a column at once. **F is the mutation rule the square matrix can state about itself** — you may write into Bob's row only if your own row already reaches both Bob and the authority you are handing over. Everything else in the table is a consequence of being able to say those two things.

Two things fall out immediately. Confinement fails in Model 3 precisely because F fails — if you can hand a key to anyone you can talk to, and you can talk to anyone, authority leaks wherever it likes. Revocation fails in Model 3 precisely because E fails — no composability, no forwarder to sever. So the two most famous objections to capabilities are *true statements about the key model*, which is the model everyone has in their head.

### Where the real systems land

The models are not academic. Three worked examples:

**Unix file descriptors** are nearly Model 4 and fall short on exactly one property. A descriptor is unforgeable, designation and authority coincide, and you must select one to act. But the channel that carries a descriptor between processes is a Unix socket, and that socket is governed by an ACL. So confining descriptor propagation depends on the ACL system rather than on the capability system. F fails at the seam.

**POSIX capabilities** fit Model 2 on every property above and still cannot support least privilege, because the set of resources is finite and fixed. Miller adds a seventh test for this — **Property G, dynamic resource creation** — and notes that no model limited to a static set of resources can have enough expressive detail to describe least authority on a live system.

**SPKI certificates** are Model 3. They designate a resource separately from conveying authority, and propagation is unrestricted: the holder may hand a copy to anyone.

That last one matters more than it looks, because SPKI is the shape most distributed "capability" systems take.

## Designation and authority

Property A has a second name, from a completely different tradition. Alan Karp, who built E-speak at HP and spent fifteen years arguing about this, states the same thing as a claim about *requests*:

> The root cause of the problem is that the authentication presented with the request is necessarily independent of the request, which means the authentication necessarily represents all the permissions assigned to me.

That is Property A read from the wire rather than from the object graph. A credential that arrives alongside a request, rather than inside it, cannot be specific to the request. It therefore carries everything its holder has.

Karp calls the resulting family **autheNtication-Based Access Control** — NBAC — and the point of the ugly capitalization is that identity, roles and attributes are the same architecture. All three answer "who is asking," and the answer is independent of what is being asked. His alternative, **authoriZation-Based Access Control** or ZBAC, presents an authorization with the request instead.

The two vocabularies are worth holding at once. Miller is describing an object graph; Karp is describing a protocol. They are making the same claim.

### The confused deputy is structural

Norm Hardy's [The Confused Deputy](https://www.cs.utexas.edu/~witchel/S25-380L/papers/hardy88confused.pdf) is the canonical failure. A compiler holds write access to a billing file. A user invokes it and names the billing file as the destination for debugging output. The compiler overwrites the billing data, because it *can*, and because the request named a path rather than carrying a reference.

The usual reading is that the compiler was careless. Miller's reading is sharper:

> The problem is not caused by the compiler using access that it should not have. The problem is that it exercises its authority to write to BILL for the wrong purpose.

And the reason it cannot tell is Property D. If you cannot identify which authority you are using, you cannot associate a purpose with it. With keys you could label each one on receipt — *this one is for billing, that one came from the user* — but labelling is impossible when keys appear on the ring without your knowledge. Which is what ambient authority is.

Karp's version adds the cure. Alice invokes the compiler and delegates read on the input and write on the output. She only holds read on the billing file, so an attempt to delegate write to it fails at the source. The attack does not get as far as the deputy.

There is a nice piece of historical irony here: the web copy of Saltzer and Schroeder everyone links to was put online by Norm Hardy.

## Possession is authorization

Model 3 long predates computers, and the physical examples make the tradeoffs concrete.

- **Value.** Casino chips, gift cards, subway tokens, postage stamps, gold, money orders.
- **Access.** House keys, coat check tickets, locker keys.
- **Authority.** Signet rings and royal seals — pressing the seal was the proof.
- **Computing.** OAuth bearer tokens, API keys, session cookies, pre-signed S3 URLs, "anyone with this link can edit", SSH private keys, TOTP seeds.

Notice what happened to almost all of them. Cash has serial numbers. Gift cards have activation systems. Crypto has a public ledger. Share links grow expiry dates and access logs.

That drift has a mechanism, and it is the two missing properties. Without E there is no forwarder to sever, so revocation has to come from a central table that says which tokens are still good. Without F you cannot bound where a token went, so finding out requires logging every use. Registries creep into bearer systems because a registry is the cheapest substitute for composability and confinement.

The useful question is never whether something is bearer or registered. It is where on that spectrum it sits, and which of E and F it gave up to get there.

## When and where the decision happens

Karp's second contribution is a decomposition that predicts failures rather than costs. Access control has four steps:

```text
Identification    knowing whom to hold responsible
Authentication    proving the right to use an identity
Authorization     granting a permission; this is where policy lives
Access decision   deciding whether to honor a particular request
```

Everyone agrees on the steps. The interesting question is *when* each happens and *in whose jurisdiction*.

```text
                   NBAC (identity / role / attribute)      ZBAC
                   where           when                    where           when
Identification     user domain     before request          user domain     before request
Authentication     service domain  at request time         user domain     before request
Authorization      service domain  before request          user domain     before request
Access decision    service domain  at request time         service domain  at request time
```

One row moves, and everything follows from it. Under NBAC the authorization decision happens in the service's domain, so the service must know who you are, which means your identity must be meaningful there, which means federated identity, single sign-on, PKI rationalization, and agreement on the meaning of every role and attribute you present.

Under ZBAC the decision happens in your own domain, before you ask. The service verifies an authorization rather than resolving an identity.

The payoff is cross-domain, and it is the part the duality story completely misses:

> After all, if my company signs a contract with your company, you have no way of knowing which of the permissions granted to my company should be granted to me; only my company knows.

Under NBAC that policy has to be communicated and reconciled. Under ZBAC my company takes a token from yours and delegates me a subset. No federated identity, no shared lexicon of roles, and your company learns nothing about my company's internal structure.

### Cannot, not do not

Karp is careful about a distinction that is easy to blur. He does not claim ACL systems *do not* support the kinds of sharing we need. He claims they *cannot*, and the argument is short enough to check.

The authentication accompanying a request is independent of the request. So the access decision allows the request if *any* of the requester's permissions matches it. So there is no place to attach a specific right to a specific argument.

His example is `cp File1 File2`. Get the arguments backwards and you destroy File1, and no ACL, role, attribute or relationship graph can save you, because the mechanism has nowhere to write down "this argument carries read and that one carries write." Pass open handles instead and the wrong order simply fails: the process tries to write to something it opened read-only.

The same structure explains malware. Every program you run authenticates as you, so every program you run holds everything you hold.

## Delegation

Three different things get called delegation, and keeping them apart matters for the rest of the series:

- **Administrative delegation.** Alice gains the power to grant others access to X. She is not exercising authority over X; she is exercising authority over the *policy* about X. This is what "admin" usually means.
- **On-behalf-of delegation.** Bob acts *as* Alice. Impersonation, `sudo -u`, OAuth's actor claim, service accounts that assume a user's identity. Bob's effective authority is Alice's entire authority.
- **Authority delegation.** Alice gives Bob a specific power she holds, and only that. Bob acts as himself, holding one more thing than he did before.

The mechanics differ sharply. Under central policy:

```text
Alice grants Bob access to X
        ↓
record an authorization fact in the store
        ↓
Bob's next request is evaluated against the new fact
```

Under capabilities:

```text
Alice ─── cap(X) ───► Bob
```

That is the whole operation. No store, no round trip, nobody else informed.

Attenuation then chains:

```text
Alice   read + write, all of repo
    ↓
Bob     read only
    ↓
Agent   read only, subdirectory Y, expires in 10 minutes
```

Each step hands on strictly less. Nobody consults a policy engine, and nobody can hand on more than they hold — a structural guarantee rather than a rule someone enforces.

### The OAuth arc

Nothing mainstream got built that way, and the clearest evidence is OAuth — the protocol most delegation on the internet actually runs through. It exists to answer one question: how do you let a third party act on your behalf *without* handing over your password? Every version has answered with on-behalf-of delegation, and the twenty-year revision history is worth reading for what it never changed.

**OAuth 1.0 / 1.0a (2007, RFC 5849) — signature-based.** Every request was cryptographically signed by the client using shared secrets (HMAC-SHA1 or RSA), so security didn't depend on the transport. The cost was brutal implementation complexity — the "signature base string" canonicalization (sorting params, percent-encoding exactly right) was where everyone's implementation broke. 1.0a was a 2009 patch closing a session-fixation flaw in the request-token handoff.

**OAuth 2.0 (2012, RFC 6749 + 6750) — a deliberate break.** It dropped request signing in favor of bearer tokens ("possession = access") and offloaded confidentiality entirely to TLS, which made clients vastly easier to write. It also redefined itself as a *framework* rather than a protocol — many optional grant types and extension points. Eran Hammer, the lead editor, resigned and pulled his name, arguing the flexibility traded interoperability and security for enterprise extensibility ("the road to hell"). He was partly right: the next decade was spent patching the framework — PKCE (RFC 7636), device flow, token introspection, mTLS, DPoP, and eventually the Security BCP (RFC 9700) — because "framework with too many choices" produced a long tail of insecure deployments.

**OAuth 2.1 (in progress) — consolidation, not new mechanics.** As of early 2026 it's still a draft (`draft-ietf-oauth-v2-1`), intended to replace and obsolete RFC 6749 and the bearer-token RFC 6750. It folds the decade of best practices into the baseline: PKCE mandatory for the authorization-code flow, the implicit grant and the resource-owner-password-credentials grant removed, bearer tokens forbidden in query strings, exact redirect-URI matching. Major providers already treat the retired grants as deprecated regardless of the draft's formal status.

**"OAuth 3" → GNAP (RFC 9635, October 2024) — the clean-slate redesign.** It began as Justin Richer's XYZ / "transactional authorization" draft, merged with Aaron Parecki's XAuth, and standardized as GNAP. The headline differences from OAuth 2: clients no longer need to be registered in advance (the client describes itself at the start of the flow via a negotiated request rather than relying on a pre-issued `client_id`/`client_secret`), and it's intent/negotiation-based with **key-bound (proof-of-possession) tokens as the default** rather than bearer tokens.

The twist worth knowing: GNAP is "OAuth 3" only in spirit, not in adoption. It's a finished standard, but because it's not backward-compatible with the enormous OAuth 2 ecosystem, the practical momentum went to OAuth 2.1's "clean up what everyone already runs" path. So the real-world story is OAuth 2 → hardened OAuth 2 (2.1), with GNAP as the published-but-largely-unadopted next-generation design sitting alongside it.

Across all four, the movement is away from *bearer* tokens ("possession = access," trust the transport) toward *proof-of-possession / key-bound* tokens — pushing security back onto a key the holder controls. That is the same migration the [crypto series](/programming/threat-model.html) traces from plaintext passwords to passkeys, and it is real progress on how a credential is *held*.

It is progress on nothing else. Notice what four redesigns never touched: the third party still acts as you, with whatever the scope string happens to cover, and no version of the protocol lets you hand over one specific power and only that. A scope is a coarse label on an impersonation, not an attenuation of an authority — on-behalf-of delegation wearing authority delegation's clothes. The gap stayed open that long because closing it needs the fifth concern, communication: a way for the delegate to *reach* one object and nothing else. No delegation protocol touches that, which is why none of them could have closed it.

### Service chaining

The three kinds of delegation stay abstract until a request crosses more than one service, so here is the case that does the damage.

Alice invokes Bob's backup service, passing a reference to the service that will supply the data. Bob implements his backup using Carol's copy service, which takes an input reference and an output reference.

Under NBAC, whose credentials does Bob present to Carol?

**His own.** Then Alice can name a service Carol may use and Alice may not, and the result comes back to Alice. Alice has mounted a confused deputy attack on Carol.

**Alice's.** Then Bob can take any action at Carol's service that Alice is permitted, whether or not Alice wanted it. Provider chaining — passing both sets of attributes — is worse than either, because it grants the union.

Karp's summary is that "in many cases, neither nor both is correct." A Navy evaluation of exactly this architecture resolved it two ways: declare the middle service fully trusted, or reduce it to a router that only forwards user-signed requests. Both define the problem away, and both break down the moment a partner organization is involved.

Under ZBAC there is no question of credentials. Alice delegates the input capability to Bob. Bob delegates it onward to Carol along with the output capability. Carol ends with exactly what the job needs, and it can be revoked when the job completes.

Keep this shape in mind. The fourth article is about agents calling tools that call other agents, and this is that problem with different nouns.

### The control you think you have

The standard objection to all of this is that easy delegation means losing control. Karp's answer is worth quoting because it is an empirical claim, not a philosophical one:

> The fact is that any control that you might think you had is an illusion. People will find workarounds, and those workarounds usually violate the assumptions behind your security architecture, resulting in worse security.

Make delegation hard and people share credentials. You blocked the transfer of a little authority and got the transfer of all of it, with the audit trail destroyed on the way out.

## Granularity, and the two routes down

There is an axis the access matrix cannot see at all: how small is the thing that holds authority?

![image](/assets/authorization/pola-granularity.png)

*Finer-grained least authority is safer. Karp's ladder, with the systems that reached each rung.*

Two different mechanisms walk down this ladder, and conflating them causes real confusion — because sandboxes, containers, seccomp and LSMs plainly do get below the user, and none of them are capability systems.

**Subtraction from outside.** Someone authors a policy, in a global namespace, naming a subject. SELinux type enforcement is an access matrix whose subjects are types rather than users; a seccomp profile is a list keyed to a process; a container is a namespace configuration. These are Model 1 with a finer principal. Authority inside the box remains completely ambient: within a container, `open("/etc/passwd")` still works by name and still succeeds because of who you are.

**Construction from inside.** The reference *is* the grant. Nothing is authored, because a per-instance, per-argument, per-call grant is just the reference that was passed.

The first route costs a policy artifact per descent, written in a vocabulary the program does not itself use — paths, types, syscall numbers, labels. The cost grows as the box shrinks, which is why nobody writes a fresh seccomp profile per request. And it bottoms out: you cannot write an LSM policy about which objects inside a process may invoke which methods, because at that granularity the policy author would be rewriting the program. Every system on the bottom two rungs is a language or a runtime rather than a supervisor, and that is not a coincidence.

Three axes are now in play, and the rest of the series keeps them apart:

```text
granularity   how small is the principal?              this article
designation   selected and joined, or ambient?         this article
enforcement   unnameability or adjudication?           article three
```

They are independent. `chroot` removes names while leaving ambient authority intact over everything still visible, so it buys unnameability without buying designation. A container is fine-grained and fully ambient. The mechanisms for the extrinsic route are article three's subject.

It is worth seeing those two routes as a matched pair rather than as two unrelated topics, because they are aiming at the same thing. Both are trying to make a subject's row in the [square matrix](/programming/authorization-models.html#make-both-axes-the-same-set) small. Construction starts from an empty row and adds by reference-passing; subtraction starts from a full one and cuts columns away. The reason both exist is that construction asks the program to cooperate — to accept a reference instead of opening a path — and most programs were not written to. Subtraction asks the program for nothing, which is why it is what you reach for when you did not write the binary.

## The three objections

Saltzer and Schroeder saw the problem in 1975 and argued against capabilities — gently, and at the end of a section, but unmistakably. [The Protection of Information in Computer Systems](https://www.cs.virginia.edu/~evans/cs551/saltzer/) raises three:

1. **Revocation.** You cannot un-give a reference.
2. **Propagation control.** Alice can pass it to anyone, and you cannot see or stop it.
3. **Review and audit.** You cannot answer "who holds authority over X?" by inspecting X.

Their conclusion is one of the most consequential recommendations in the field:

> The most effective way of preserving some of the useful properties of capabilities is to limit their free copyability to the bottom most implementation layer of a computer system… The authorizations implemented by the capability system are then systematically maintained as an image of some higher level authorization description, usually some kind of an access control list system.

Capabilities as a fast bottom layer, governed by an ACL system above. That design won completely. Unix, Windows, POSIX — file descriptors underneath, mode bits and ACLs on top. The entire identity-management industry is downstream of this paragraph.

Here is what the four-model table does to it. Objections one and two are **true of Model 3 and false of Model 4**. Propagation is uncontrollable exactly when Property F is missing; revocation is impossible exactly when Property E is missing. The objections survive fifty years of rebuttal because the key metaphor is the one everyone reasons with, and in the key metaphor they are correct.

### Revocation needs composability

The standard answer is Redell's indirection: interpose a forwarder you can sever. It is described in Saltzer and Schroeder's own paper, and it is the seed of what later became the membrane pattern.

The reason it works in Model 4 and not in Model 3 is Property E. A forwarder has to be a resource that is also a subject. Where resources and subjects are separate type categories — where you have doors on one side and keys on the other — there is nowhere to put one.

### Accountability is the one ACLs lose

The third objection deserves more care, because the ACL's answer to it is weaker than it looks.

Alice wants Bob to watch a document in a SharePoint area. Under an ACL she asks Carol, the owner, to add Bob. Now consider what got recorded. The audit log says *Carol* created Bob's access. Nothing anywhere says Alice asked for it.

Then Alice wants it undone. Should Carol honor the request? There is no metadata naming Alice as the delegator, and even if there were, Dave might have granted Bob the same access for his own reasons. Remove it and Dave's work breaks.

Under ZBAC the delegation chain carries responsibility. It is the record that says Alice is answerable for Bob's access, it is the metadata that decides whether Alice may revoke, and revoking one authorization disturbs no other. This is Karp's sixth aspect of sharing, and it is the physical-world property we take entirely for granted:

> If Marc finds a new scratch on his car, he knows to ask me to pay for the repair. It's up to me to collect from my neighbor.

So capabilities do not lose accountability. They lose *global* review, which is a different thing, and which the next two sections are about.

### The patches converge

Each side's fix for its own weakness imports the other side's core mechanism.

![image](/assets/authorization/acl-vs-ocaps.png)

**Capabilities adding revocation.** Introduce indirection: the token no longer grants access directly, it points at something that can be invalidated. But that something lives in a table mapping tokens to validity, and a table is a registry. You have rebuilt the ACL's central lookup with an extra hop. Expiry is the same move — you need a clock authority and a check on use.

**Capabilities adding global audit.** Answering "who holds what?" across a whole system requires tracking holders. That is a list of principals and their permissions.

**Capabilities adding policy-based issuance.** "Only managers get this capability" requires an identity system that knows who is a manager.

**ACLs adding confused-deputy protection.** Label the data, make every endorsement explicit, propagate the original caller's identity into the request context so the deputy can say on whose behalf it acts. The check now has enough information to be right.

### The convergence is not symmetric

The three capability-side patches import machinery: a registry, a list, an identity system. Each works whether or not the capability holder cooperates. The ACL-side patch imports a discipline. It works only if the deputy uses it.

That gap has a clean statement. ACL-plus-context makes the correct answer **expressible** — AWS's `sts:ExternalId` and `aws:SourceArn`, propagated caller identity, request-context claims all exist so a deputy *can* be right. It still has to ask. Object capabilities make the incorrect answer **unrepresentable**. Lacking authority means lacking a name, so there is no wrong question available.

The difference shows up precisely when the deputy is careless, and Hardy's compiler was careless rather than malicious. Nobody attacked it. Someone wrote it without considering the question. ACL-plus-context is exactly as reliable as the deputy's diligence, and diligence does not survive scale.

The capability claim needs its own limit, though, and Miller is explicit about it. A program holding two references can still use the wrong one. Unifying designation and authority removes *ambient* authority, not *excess* authority. It does not make the deputy careful; it shrinks the set of things carelessness can reach. Midori hit this directly: components accumulated "big bags" of capabilities because threading them individually was tedious, which is least authority losing to ergonomics rather than to theory.

That is a real finding about program internals, and it should not be generalized to users. At the user level the ergonomics have been solved and demonstrated. CapDesk turned acts of designation into acts of authorization — drag a file's icon onto an editor and the system starts the editor holding exactly that file. Polaris did it for Windows XP applications. Karp's team hid it so thoroughly in a file-sharing tool that a user asked them how to turn security on.

Which also explains what the systems that shipped this actually did. Capsicum, `openat` everywhere, WASI preopens, seccomp, SPIFFE's short-lived scoped SVIDs, macaroon caveats — none of them improve how a resource is designated. All of them reduce what the process holds. That is the attenuation chain arriving as fifteen years of engineering practice rather than as a diagram.

### Complete over the intended state, not the reachable state

A relationship store like [Zanzibar](https://research.google/pubs/pub48190/) answers the review question directly, and its tuple graph is a complete picture of policy. But policy binds only where the code consults the decision point. The service still holds ambient credentials to the database. A code path that opens a connection directly, a deserialization bug, a compromised dependency — none of those appear in the graph, and none are stopped by it. The audit is complete over the state you **intended**, not the state a compromised process can **reach**.

Object capabilities invert this exactly. There is no global view. But what you can see is reachability itself, and reachability is the thing that constrains a compromised component.

So capability auditability is not zero. It is local rather than global, and "only connectivity begets connectivity" is the load-bearing claim. A reference arrives in exactly four ways: initial conditions, creation, endowment, or introduction. Midori made the first of those an artifact you can read — a manifest, consulted at load time. That bounds how the graph can evolve, which makes a component's authority analyzable from its boundary.

A Wasm component's import list is the concrete version. It enumerates, statically and exhaustively, everything the component can reach — exhaustive by construction rather than by policy discipline. As audit surfaces go, that is a good one, arguably better than a tuple query.

It answers a different question, though. "What can this component do?" rather than "who can touch this resource?" Auditors want the second.

## Policy and mechanism

There is a second lens on all of this, and it is the one that finally made the whole thing click for me: the separation of policy from mechanism.

![image](/assets/authorization/keys-vs-cards.png)

**A physical key fuses policy and mechanism.** The shape of the key *is* the policy. The lock pins *are* the mechanism. They are literally the same object. Simple, fast, offline, and unchangeable — to change the policy you change the lock.

**A card key with a central ACL separates them.** The reader is the mechanism; it verifies identity. The database is the policy; it decides rights. You get dynamic updates, central revocation, and audit logs. You also get a dependency on an online check and centralized infrastructure.

**A capability token puts policy back in the artifact.** The token carries its own authorization. The mechanism is reduced to cryptographic verification.

That third panel is the picture everyone draws, and it is Model 3. Worth being explicit, because the metaphor is doing quiet damage. A key ring gets Property D right — you must select a key — and gets A, E and F wrong. You can hold a key without knowing its door. A key is not itself a lock. And you may hand a copy to anyone you can physically reach, which in the physical world is anyone at all.

So the key metaphor teaches the correct lesson about ambient authority and the wrong lesson about confinement and revocation. It is a good picture of why capabilities are fast and offline, and a bad picture of what makes them safe.

The fusion in the third panel is real, but what got fused is different:

```text
physical key   policy = key shape          permanent
capability     policy = token claims       temporal, scoped, revocable
```

It is a physical key that dissolves after an hour, only works during business hours, can be remotely deactivated, and changes shape depending on which door it is presented to. The bearer model's offline simplicity, with the database model's contextual control.

![image](/assets/authorization/mechanism-policy-separation.png)

The generalization is that **policy/mechanism separation is not a binary but a question of where the seam sits**. You can push the seam down to the lock, out to a database, or into the credential. The fourth article's whole architecture is a specific choice about where to put that seam for agents.

## Local authority versus global knowledge

Lampson states the administrative case bluntly in [a 2020 retrospective](https://arxiv.org/pdf/2011.02455):

> Only ACLs work for managing the policy, because the manager's question is, "Who has access to this resource?" It's okay to make short-term copies of parts of it into capabilities (usually called file descriptors), which are faster to check.

Hence the slogan: capabilities are cached ACL decisions.

The slogan is right about a real thing and wrong about another, and the wrongness is worth being precise about, because the obvious rebuttal is also wrong.

A capability answers one question, perfectly and locally: *may the holder of this perform operation X?* No lookup, no network, no identity resolution.

A central authorization store answers the questions a capability cannot: who can perform X, what can Alice access, revoke everything derived from Alice's grant, and which of these ten thousand records may Alice see. That last one deserves its own name. **Reverse indexability** — filtering a result set by authorization rather than checking one access — is why data-centric systems like Zanzibar exist. You cannot build a list page by asking the user to present every capability they might hold.

But it does not follow that capabilities have no administrative story. Karp's architecture has one, and it is centralized: a local domain authority holds the delegable authority its organization received, decides which users get which subsets, mints tokens, and revokes them. That is a store, an admin console and a lifecycle. Mint proxies rather than raw references and you get revocation without importing an ACL at the resource.

So the honest version is not that capabilities do execution and ACLs do administration:

> **Wherever authority is minted, someone keeps a store. The question is not whether there is a store, but how many there are and whose jurisdiction each sits in.**

ACLs put one store at the resource. ZBAC puts a store in each issuing domain. Object capabilities put one at every issuer, including every object that hands out a proxy. What capabilities genuinely lack is a *global* view — which is the previous section, arriving from the other direction.

The sharper version of the tradeoff is about principals. Zanzibar's are people and organizational relations: they change independently of the code, non-programmers modify them, and they must be enumerable and revocable on demand. Ocap's are code objects, where the topology is a program-structure question and the adversary is a buggy or hostile component rather than an over-privileged employee. Running both is normal — Zanzibar-style relations at the user-facing boundary, capability discipline for confinement below it. Midori is the evidence: the most committed object-capability system anyone has shipped, and Duffy's retrospective still names policy management and the user-facing side as the part they left under-explored.

For a multi-user file server, the administrative question dominates and ACLs win. For a separation kernel running mutually suspicious components where you want a provable bound on blast radius, the propagation question dominates and capabilities win.

That second case is where the "cached decision" framing genuinely undersells what is happening. In seL4, the capability graph is not an optimization of some authoritative ACL kept elsewhere. There is no elsewhere. The graph *is* the authority, and its static structure is the thing being reasoned about — not any individual access decision. Nothing is being cached, because there is no original.

So the synthesis looks like this, and it is deliberately one-directional:

```text
global, queryable policy        ← the administrative question
        ↓
authorization decision
        ↓
materialized authority          ← the execution question
        ↓
capability
```

Centralized policy decides what authority should exist. Capabilities represent and safely propagate authority once it exists. Most real systems want the top half for administration and the bottom half for enforcement, and the interesting engineering is in the arrow between them.

### What running both looks like

The arrow is a component, and it is worth being concrete about what it does.

Take `GET /docs/4471`. An edge service resolves Alice's session — it is the only thing in the system that knows the string `alice`. It asks the relationship store `check(user:alice, viewer, doc:4471)`, or a `list` query when it is building an index page. On allow it does *not* pass "alice, approved" downstream. It mints a handle that designates document 4471 and conveys read, and hands that on.

Everything below holds only the handle. The renderer, the thumbnailer, and the export worker have no database credentials and no way to name document 4472. The thumbnailer's copy is attenuated further — read-only, thirty seconds — by wrapping the reference it already holds, with no second trip to the policy store.

That last constraint carries the whole design. If the renderer fetches the row over the service's own superuser connection, the check was advisory, and every code path that skips it reaches everything. The capability layer is not an optimization of the ACL check. It is what closes the gap between the intended state and the reachable state.

Capsicum is this architecture compressed into one process: open what policy permits by path, then call `cap_enter()`, after which the process can never name anything new. Pre-signed URLs are the same architecture stretched across a network, where IAM decides at signing time and the holder never touches IAM.

Midori pushed the seam all the way to program startup. Mutable statics were a compile error, and there was no `DateTime.Now` — to read the clock you asked for a `Clock`. Authority entered through a manifest that the application model read at load time and used to endow `main`, and from there it moved only by reference-passing. The manifest is the declarative, reviewable, human-facing artifact. Everything after it is capability discipline.

Revocation across the seam is the obvious objection, and the answer is the familiar one: short lifetimes, indirection you can sever, or a notification channel from the policy store to whoever minted. Flask built the third, and the next article takes it apart.

The second cost is that audit becomes two stories. The tuple graph answers "who can reach document 4471", complete over the intended state. The capability graph answers "what can the thumbnailer reach", complete over the reachable state. Both are real, neither subsumes the other, and joining them is not a solved problem.

## Where the property can be bought

Everything above reduces to Property F, and Property F has a precondition that nobody states plainly.

> **To pass a capability only to someone you can already reach, something must be able to deny communication.**

That is not a design preference. It is an infrastructure requirement, and it explains every data point in this article at once:

```text
seL4                 the kernel mediates all IPC              Model 4
a language heap      references are the only way to reach     Model 4
Cap'n Proto vats     the overlay controls who can address whom Model 4
Cloudflare workerd   the runtime mediates every binding       Model 4

Unix file descriptors passed over ACL-controlled sockets      nearly
chroot                names removed, authority still ambient  not a capability system
physical keys         the world is a universal channel        Model 3
the open internet     IP is a universal channel               Model 3
```

**Every object-capability system that has ever worked is inside something that mediates communication.** A kernel, a language runtime, a VM boundary, an RPC overlay. That is not an implementation accident. It is Property F being purchasable only where connectivity is already controlled.

Which settles the question of capabilities on the internet, and the answer is not the one the maximalists give, nor the one the skeptics give.

The internet is *covered* in capabilities. Pre-signed S3 URLs, "anyone with this link can edit", GitHub fine-grained tokens, SPIFFE SVIDs, macaroons, biscuits. A Bitcoin private key is a bearer capability to spend a UTXO, works globally, and requires no relationship with anyone. The share link may be the most successful sharing mechanism ever deployed, it crosses every organizational boundary there is, and it is a capability.

Every one of them is Model 3. And Model 3 is exactly the model whose myths are true.

The obstacle is not that you fail to own both endpoints — HTTP and TLS do not require that either. It is that the internet's product *is* universal connectivity. Any host may address any other host, so nothing can deny communication, so F is unavailable in principle rather than in practice. You can approximate it with unguessable designators and confidentiality — Waterken did exactly this, with object capabilities as HTTPS URLs — but that is F-by-obscurity rather than F-by-construction. Anyone who learns the string may use it, and nothing prevents the holder from publishing it.

So: use Model 4 inside your boundaries, expect Model 3 across them, and know which one you are in. Where you control the substrate — a kernel, a runtime, a sandbox, an RPC fabric you designed — the property is nearly free and you should take it. Where you do not, macaroons and their relatives are Model 3 done about as well as Model 3 can be done: attenuable without a round trip, caveats travelling with the artifact, verifiable by a server that has never heard of you.

The gap in between is a missing standard rather than a law of nature, and Karp has been asking for it since 2009:

> There is no standard for chained, attenuated delegation, which is an opportunity for an IEEE standards group. […] We must start on these standards before the IoT world becomes embedded in our lives. If we don't, we'll end up with walled gardens, an AOL of Things.

The fourth article is about a system that has the substrate and threw the property away.

## References

- [Capability Myths Demolished](https://cgi.cse.unsw.edu.au/~cs9242/20/papers/Miller_YS_03.pdf) — Miller, Yee, Shapiro; the four models and the six properties
- [Robust Composition](http://www.erights.org/talks/thesis/markm-thesis.pdf) — Miller's thesis; ambient versus excess authority, and "only connectivity begets connectivity"
- [From ABAC to ZBAC: The Evolution of Access Control Models](https://shiftleft.com/mirrors/www.hpl.hp.com/techreports/2009/HPL-2009-30.pdf) — Karp, Haury, Davis; NBAC versus ZBAC, service chaining, and the four steps
- [Access Control for IoT: A Position Paper](https://alanhkarp.com/publications/Access-Control-for-IoT.pdf) — Karp; the six aspects of sharing, and why delegation control is an illusion
- [The Confused Deputy](https://www.cs.utexas.edu/~witchel/S25-380L/papers/hardy88confused.pdf) — Hardy, 1988
- [The Protection of Information in Computer Systems](https://www.cs.virginia.edu/~evans/cs551/saltzer/) — Saltzer and Schroeder; the three objections and the recommendation that shaped every mainstream OS
- [Authorization (Lampson)](https://arxiv.org/pdf/2011.02455) — the "caps are cached ACL decisions" position
- [Macaroons: Cookies with Contextual Caveats](https://static.googleusercontent.com/media/research.google.com/en/us/pubs/archive/41892.pdf) — attenuable bearer capabilities
- [Objects as Secure Capabilities](https://joeduffyblog.com/2015/11/10/objects-as-secure-capabilities/) — Duffy on Midori; the capability oracle at `main`, no mutable statics, and where it fell short
- [Capsicum: Practical Capabilities for UNIX](https://www.usenix.org/conference/usenixsecurity10/capsicum-practical-capabilities-unix) — ambient authority removed from a real Unix
- [E and CapDesk: POLA for the Distributed Desktop](https://web.archive.org/web/2020/http://www.combex.com/tech/edesk.html) — Stiegler and Miller; designation as authorization in a user interface
- [Joe-E: A Security-Oriented Subset of Java](https://www.cs.berkeley.edu/~daw/papers/joe-e-ndss10.pdf) — Mettler, Wagner, Close; object references as capabilities, enforced by a verifier
- [Waterken](http://waterken.sourceforge.net/) — object capabilities as HTTPS URLs
- [The OAuth 2.0 Authorization Framework - RFC 6749](https://datatracker.ietf.org/doc/html/rfc6749)
- [Best Current Practice for OAuth 2.0 Security - RFC 9700](https://datatracker.ietf.org/doc/html/rfc9700)
- [Grant Negotiation and Authorization Protocol (GNAP) - RFC 9635](https://datatracker.ietf.org/doc/html/rfc9635) — key-bound tokens by default, and the ecosystem that did not follow
- [OAuth 2.0 and the Road to Hell](https://hueniverse.com/oauth-2-0-and-the-road-to-hell-8eec45921529) — Hammer's resignation over framework-versus-protocol
- [Zanzibar: Google's Consistent, Global Authorization System](https://research.google/pubs/pub48190/) — relationship-based authorization and reverse indexability
