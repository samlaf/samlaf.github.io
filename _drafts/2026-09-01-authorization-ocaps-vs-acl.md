---
title:  "Where authority lives: ACLs, capabilities, and delegation"
category: programming
date:   2026-09-01
---

> This is the first of three articles on authorization.
>
> 1. **Where authority lives** — how a system represents authority, and how authority moves between principals.
> 2. **How authority is enforced** — what makes those limits non-bypassable.
> 3. **LLM sandboxing** — making the gateway correct and unavoidable when the workload is an agent.

- [The matrix and its two projections](#the-matrix-and-its-two-projections)
- [Capabilities are not transposed ACLs](#capabilities-are-not-transposed-acls)
  - [Possession is authorization](#possession-is-authorization)
- [The mainstream models all live on the ACL side](#the-mainstream-models-all-live-on-the-acl-side)
- [Identity is not authority](#identity-is-not-authority)
  - [Tokens as reified decisions](#tokens-as-reified-decisions)
- [Delegation](#delegation)
- [Revocation, propagation, review](#revocation-propagation-review)
  - [The patches converge](#the-patches-converge)
  - [The convergence is not symmetric](#the-convergence-is-not-symmetric)
  - [Complete over the intended state, not the reachable state](#complete-over-the-intended-state-not-the-reachable-state)
- [Policy and mechanism](#policy-and-mechanism)
- [Local authority versus global knowledge](#local-authority-versus-global-knowledge)
  - [What running both looks like](#what-running-both-looks-like)
- [Where this leaves us](#where-this-leaves-us)
- [References](#references)


Ask what authorization is and you will get an answer about deciding. Can Alice read this file? Is this token valid? Does this role include that permission. Deciding matters, but it is the second question. The first is where the answer lives before anyone asks.

A system has to put authority somewhere. It can keep a list at each resource naming who may touch it. It can hand each subject a set of unforgeable references to the things it may touch. It can keep a database of relationships and compute the answer on demand. These are not implementation details that wash out at scale. Each one makes a different set of questions cheap and a different set expensive, and the expensive questions are the ones that eventually break your architecture.

This article is about representation and propagation only. It deliberately does not answer *what authority should exist* — that is a policy question, and it belongs to the third article. It also does not answer what stops a program from ignoring the representation entirely. That is the second article.

![image](/assets/authorization-ocaps-vs-acl/auth-models.png)

*From [The State of the Union of Authorization](https://idpro.org/the-state-of-the-union-of-authorization/).*

## The matrix and its two projections

Start with the simplest model that captures the problem. Lampson's access-control matrix has subjects down one axis, objects across the other, and permitted operations in the cells.

```text
             File A    File B    Device C
Alice          rw        r
Bob                      rw        use
```

Nobody stores the matrix. It is mostly empty, and it changes constantly. So real systems store one of its two projections.

Store it by column, at the resource, and you get an **access control list**:

```text
File A → Alice: rw
File B → Alice: r, Bob: rw
Device C → Bob: use
```

Store it by row, at the subject, and you get a **capability list**:

```text
Alice → File A: rw, File B: r
Bob   → File B: rw, Device C: use
```

The same information, transposed. This is the observation that makes people say ACLs and capabilities are dual, and at this level they are. A file descriptor is a capability; `/etc/passwd`'s mode bits are an ACL; both describe cells of the same matrix.

Hold that claim loosely. The matrix describes permissions at an instant. It says nothing about how a cell got filled in, who is allowed to fill in another one, or what happens when Alice hands Bob something. Every interesting difference between ACLs and capabilities lives in those dynamics, which the matrix does not model. The rest of this article is mostly about dismantling the duality it suggests.

## Capabilities are not transposed ACLs

Mark Miller's [Capability Myths Demolished](https://cgi.cse.unsw.edu.au/~cs9242/20/papers/Miller_YS_03.pdf) is the canonical statement that the transposition story is wrong, or at least badly incomplete. The strong version of the idea — the **object-capability model** — adds properties the matrix cannot express.

An object capability is an unforgeable reference that both *designates* an object and *conveys* the authority to invoke it. The consequences compound:

- **Unforgeability.** You cannot manufacture a capability by guessing. There is no global namespace from which to recover an object by naming it.
- **Designation and authority coincide.** Saying *which* object and saying *that you may use it* are the same act. Lacking authority therefore means lacking a name, which is the property the confused deputy turns on, as we will see.
- **Delegation is reference-passing.** To give Bob authority, hand him the reference. No registry updates, no central grant.
- **Attenuation.** You can wrap a reference in a proxy that forwards a subset of operations, and hand that on instead. The wrapper has to be airtight: Midori found that a caller handed a `File` could downcast it back to the wider type it really was, which took language-level restrictions on casting to close.
- **Reachability bounds authority.** What a subject can ever affect is the transitive closure of the references it holds. Absence of a reference is a hard limit, not a denied request.
- **No ambient authority.** A subject acts only through references it was given. It has no background powers it can invoke by virtue of who it is.

That last property is the real dividing line, and it is invisible in the matrix. In a Unix process, opening a file requires only a *name* — the authority comes from the process's identity, floating in the background. In an ocap system, the name *is* the authority, and you only have names someone handed you.

It is worth saying exactly which half of the transposition survives, because one half does. The claim bundles two things: that the data sits at the subject rather than at the object, and that both representations carry the same information. For a capability list both are true, and the duality is real. For object capabilities only the first is.

A matrix row is flat. Alice holding a reference to Bob, who holds a reference to X, is not the cell `Alice: rw X`. Bob mediates. Bob can refuse, revoke, log, or forward only a subset. The matrix has nowhere to write that down, no way to make Bob a row and a column at once, and no vocabulary for rights once "rights" means whatever interface Bob happens to expose.

Three things get called capabilities and only one of them has these properties:

```text
capability list
    a row of the matrix; the kernel keeps it; ambient
    authority usually still exists alongside it

bearer token
    a string that grants access to whoever presents it;
    forgeable if guessable, copyable, and usually names
    a resource in a global namespace

object capability
    unforgeable reference, designation = authority,
    delegable, attenuable, no ambient authority
```

A file descriptor is close to the third. An API key is firmly the second. Conflating them is how discussions about capabilities go wrong.

The file descriptor is worth sitting with, because `open` is the conversion between the two regimes. A pathname is plain data naming a slot in a global namespace. The descriptor it returns is a handle in a small per-process table that previous authorization decisions populated. [`pidfd` does the same for processes](/programming/everything-is-a-file.html), turning a guessable, reusable integer into possession of one specific object.

### Possession is authorization

The bearer idea long predates computers, and the examples are worth having in mind because they make the tradeoffs concrete.

- **Value.** Casino chips, gift cards, subway tokens, postage stamps, gold, money orders.
- **Access.** House keys, coat check tickets, locker keys.
- **Authority.** Signet rings and royal seals — pressing the seal was the proof.
- **Computing.** OAuth bearer tokens, API keys, session cookies, pre-signed S3 URLs, "anyone with this link can edit", SSH private keys, TOTP seeds.

Notice what happened to almost all of them. Cash has serial numbers. Gift cards have activation systems. Crypto has a public ledger. Bearer instruments make theft, fraud, and enforcement hard, so registries creep in. The useful question is never whether something is bearer or registered, but where on that spectrum it sits and what the drift toward registration cost.

## The mainstream models all live on the ACL side

Before going further it is worth placing the models you actually use. The usual progression — DAC, MAC, RBAC, ABAC, ReBAC — reads as a story about increasing sophistication. It is more precisely a story about increasingly elaborate ways to describe **the subject**.

```text
DAC   WHO (this identity) can do WHAT to WHICH resource
MAC   WHO (this clearance) can do WHAT to WHICH (this classification)
RBAC  WHICH ROLES (groups of subjects) can do WHAT to WHICH
ABAC  WHICH ATTRIBUTES (of subject, resource, action, environment)
ReBAC WHICH RELATIONSHIPS connect this subject to this resource
```

![image](/assets/authorization-ocaps-vs-acl/access-control-models.png)

Every one of these keeps authority at the resource, or in a policy store that speaks on the resource's behalf, and looks the subject up when a request arrives. They are refinements of the ACL projection, not alternatives to it. The subject presents an identity; the system decides.

That ladder describes the subject. A second axis describes what happens to the access relation itself, and it is the more useful of the two:

```text
ACL     store the relation
RBAC    factor the relation     subject → role → permission
ABAC    compute the relation    a predicate over attributes
ReBAC   derive the relation     a graph plus composition rules
```

Store, factor, compute, derive. Each is cheaper to administer than the one before and more expensive to evaluate, which is the entire trade.

This also disposes of a confusion worth naming. RBAC is sometimes described as putting the ACL on the subject. It is not — that is a capability list. RBAC inserts a reusable layer *between* subject and permission, so that `Users × Permissions` factors into `(Users × Roles)` and `(Roles × Permissions)`. The saving comes from sharing the middle term across many subjects, not from changing which end of the matrix the data hangs off.

The clean ladder also oversimplifies. MAC is not simply "RBAC plus levels": SELinux's type enforcement is a prerequisite for MAC and a first step toward multilevel security, and its security context is the full `user:role:type:level` tuple rather than a single clearance. Type enforcement and RBAC are complements in that design, not rungs.

ABAC is where the industry landed for anything complicated, with XACML and OPA's Rego as the two main expressions. Both share a shape: a policy document, a set of facts about subject and resource and environment, and an engine that evaluates one against the other at request time.

Which is exactly the cost capabilities are trying to avoid.

There is a sharper way to state this section's title. Project every model onto the matrix and watch what happens to the information.

```text
ACL               reindex by column              exact, invertible
capability list   reindex by row                 exact, invertible
RBAC              expand the roles               exact
ABAC              evaluate the predicate         exact
ReBAC             run the check over every pair  exact

ocap graph        flatten reachability           lossy
```

The first five are notations for a matrix. Running them backwards is underdetermined — you cannot recover which factorization, which predicate, or which tuples produced a given set of cells — but running them forwards is faithful. Each is a compression scheme for the same object, which is exactly why they form one family.

Flattening an object-capability graph is not faithful. `Alice: rw X` is a true statement about what Alice can eventually cause and a false statement about the authority she holds, and that difference is the entire reason the graph exists. So an ocap graph is not a sixth notation for the matrix. It is not a notation for the matrix at all.

One thing does survive the projection: a single cell can be materialized as a handle, which is the pipeline this article ends on. Materializing cells one at a time is not the same as recovering the structure.

## Identity is not authority

The credential a subject presents can carry wildly different amounts of already-decided authority. It helps to see this as a ladder.

```text
identity              "This is Alice."
   ↓                  The verifier must decide everything.

attributes            "Alice is a manager in Finance."
   ↓                  The verifier still decides, with better facts.

scoped token          "Bearer of this may read the billing API."
   ↓                  Most of the decision is already made.

capability            "Bearer of this may read invoice 4471,
                       until 17:00, once."
                      The decision is made. Verification is all
                      that remains.
```

Going down the ladder moves work from request time to issue time. This is the sense in which capabilities "shift left": the hard policy evaluation happens once, when the capability is minted, and every subsequent use is a cheap validity check. Pre-signed S3 URLs do exactly this. So do OAuth access tokens and Kubernetes service account tokens. The authorization server does the expensive relationship and attribute work; the resource server checks a signature.

A second axis cuts across the ladder, and conflating the two causes real bugs:

```text
bearer              whoever holds it may use it
proof-of-possession holder must additionally prove they
                    control a key bound to the credential
```

A capability can be bearer or PoP. An identity assertion can be bearer or PoP. The mTLS-bound token and the string in an `Authorization` header sit at the same rung of the ladder and have completely different theft properties.

### Tokens as reified decisions

Macaroons, JWTs, and OAuth access tokens are none of the architectures discussed so far. They are **artifacts**: a previous authorization, serialized so a later request need not return to the decision-maker and reconstruct it.

The "cached decision" framing is close but not exact. A verifier still checks signature, issuer, audience, and expiry, and often consults current resource state. A JWT frequently carries *claims* from which the resource server makes a fresh decision rather than a final allow.

[Macaroons](https://static.googleusercontent.com/media/research.google.com/en/us/pubs/archive/41892.pdf) go furthest toward being genuine reified capabilities. A holder can attenuate one by appending caveats — repository, method, time window, request budget, a required third-party discharge — without the root key and without going back to the issuer:

```text
may access GitHub
    only repository X
    only pull-request operations
    before 17:00
    for sandbox Y
```

That is attenuation as a property of the artifact rather than of a process profile. The constraints travel with the token instead of living in some verifier's memory. It matters: a stolen macaroon is worth only what its caveats already permitted.

## Delegation

Delegation is where the two representations stop resembling each other, and it is the heart of the matter.

Three different things get called delegation, and article three depends on keeping them apart:

- **Administrative delegation.** Alice gains the power to grant others access to X. She is not exercising authority over X; she is exercising authority over the *policy* about X. This is what "admin" usually means.
- **On-behalf-of delegation.** Bob acts *as* Alice. Impersonation, `sudo -u`, OAuth's actor claim, service accounts that assume a user's identity. Bob's effective authority is Alice's entire authority.
- **Authority delegation.** Alice gives Bob a specific power she holds, and only that. Bob acts as himself, holding one more thing than he did before.

The mechanics differ sharply by representation. Under central policy:

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

That is the whole operation. No store, no round trip, nobody else informed. Which is simultaneously the feature and the problem.

Attenuation then chains naturally:

```text
Alice   read + write, all of repo
    ↓
Bob     read only
    ↓
Agent   read only, subdirectory Y, expires in 10 minutes
```

Each step hands on strictly less. Nobody consults a policy engine. Nobody can hand on more than they hold, which is a structural guarantee rather than a rule someone enforces.

## Revocation, propagation, review

Saltzer and Schroeder saw the problem in 1975 and argued against capabilities — gently, and at the end of a section, but unmistakably. Their [Protection of Information in Computer Systems](https://www.cs.virginia.edu/~evans/cs551/saltzer/) identifies three objections:

1. **Revocation.** You cannot un-give a reference.
2. **Propagation control.** Alice can pass it to anyone, and you cannot see or stop it.
3. **Review and audit.** You cannot answer "who holds authority over X?" by inspecting X.

Their conclusion is one of the most consequential recommendations in the field:

> The most effective way of preserving some of the useful properties of capabilities is to limit their free copyability to the bottom most implementation layer of a computer system… The authorizations implemented by the capability system are then systematically maintained as an image of some higher level authorization description, usually some kind of an access control list system.

Capabilities as a fast bottom layer, governed by an ACL system above. That design won completely. Unix, Windows, POSIX — file descriptors underneath, mode bits and ACLs on top. The entire identity-management industry is downstream of this paragraph.

The object-capability response is that S&S identified real problems and drew the wrong conclusion. Revocation has good answers: Redell's indirection — interpose a forwarder you can sever — is described in S&S's own paper, and it is the seed of what later became the membrane pattern. Propagation can be controlled by being careful about which references you hand out in the first place. Audit survives in local form, and it is worth being precise about what that does and does not buy.

Meanwhile, the argument runs, ACL systems have pathologies of their own that are worse than what they fix. Norm Hardy's [The Confused Deputy](https://www.cs.utexas.edu/~witchel/S25-380L/papers/hardy88confused.pdf) is the canonical statement: a program holding ambient authority is asked by an untrusted caller to do something, and cannot tell which of its powers the request was entitled to invoke. The compiler writes to the billing file because it *can*, and because the request named a path rather than carrying a reference. Designation and authority came apart, and the deputy got confused in the gap.

There is a nice piece of historical irony here: the web copy of the S&S paper that everyone links to was put online by Norm Hardy.

### The patches converge

Here is the part that took me a while to see. Each side's fix for its own weakness imports the other side's core mechanism.

![image](/assets/authorization-ocaps-vs-acl/acl-vs-ocaps.png)

**Capabilities adding revocation.** You introduce indirection: the token no longer grants access directly, it points at something that can be invalidated. But that something lives in a table mapping tokens to validity. That table is a registry. You have rebuilt the ACL's central lookup with an extra hop. Expiry is the same move — you need a clock authority and a check on use.

**Capabilities adding global audit.** Answering "who holds what?" across a whole system requires tracking holders. That is a list of principals and their permissions.

**Capabilities adding policy-based issuance.** "Only managers get this capability" requires an identity system that knows who is a manager.

**ACLs adding confused-deputy protection.** Label the data, make every endorsement explicit, propagate the original caller's identity into the request context so the deputy can say on whose behalf it acts. The check now has enough information to be right.

### The convergence is not symmetric

The three capability-side patches import machinery: a registry, a list, an identity system. Each one works whether or not the capability holder cooperates. The ACL-side patch imports a discipline. It works only if the deputy uses it.

That gap has a clean statement. ACL-plus-context makes the correct answer **expressible** — AWS's `sts:ExternalId` and `aws:SourceArn`, propagated caller identity, request-context claims all exist so a deputy *can* be right. It still has to ask. Object capabilities make the incorrect answer **unrepresentable**. Lacking authority means lacking a name, so there is no wrong question to ask.

The difference shows up precisely when the deputy is careless, and Hardy's compiler was careless rather than malicious. Nobody attacked it. Someone wrote it without considering the question. ACL-plus-context is exactly as reliable as the deputy's diligence, and diligence does not survive scale.

The capability claim needs its own limit, though, and Miller is explicit about it. A program holding two references can still use the wrong one. Unifying designation and authority removes *ambient* authority, not *excess* authority. It does not make the deputy careful. It shrinks the set of things carelessness can reach. Midori hit this directly: components accumulated “big bags” of capabilities because threading them individually was tedious, which is least authority losing to ergonomics rather than to theory.

Which explains what the systems that actually shipped this did. Capsicum, `openat` everywhere, WASI preopens, seccomp, SPIFFE's short-lived scoped SVIDs, macaroon caveats — none of them improve how a resource is designated. All of them reduce what the process holds. That is the attenuation chain above, arriving as fifteen years of engineering practice rather than as a diagram.

There is a name for the underlying distinction. The next article calls it unnameability versus adjudication.

So the honest summary is not that one wins outright. It is that a system with real-world requirements ends up needing both mechanisms, and the interesting design question is which one you put at the core.

### Complete over the intended state, not the reachable state

Review, the third objection, deserves more care than revocation and propagation, because the ACL answer to it is weaker than it looks.

A relationship store like [Zanzibar](https://research.google/pubs/pub48190/) answers it directly, and its tuple graph is a complete picture of policy. But policy binds only where the code consults the PDP. The service still holds ambient credentials to the database. A code path that opens a connection directly, a deserialization bug, a compromised dependency — none of those appear in the graph, and none are stopped by it. The audit is complete over the state you intended, not the state a compromised process can reach.

Object capabilities invert this exactly. There is no global view. But what you *can* see is reachability itself, and reachability is the thing that constrains a compromised component.

So capability auditability is not zero. It is local rather than global, and Miller's **"only connectivity begets connectivity"** is the load-bearing claim. A reference arrives in exactly four ways: initial conditions, creation, endowment, or introduction. Midori made the first of those an artifact you can read — a manifest, consulted at load time. That bounds how the graph can evolve, which makes a component's authority analyzable from its boundary.

A Wasm component's import list is the concrete version. It enumerates, statically and exhaustively, everything the component can reach — exhaustive by construction rather than by policy discipline. As audit surfaces go, that is a good one, arguably better than a tuple query.

It answers a different question, though. "What can this component do?" rather than "who can touch this resource?" Auditors want the second.

## Policy and mechanism

There is a second lens on this, and it is the one that finally made the whole thing click for me: the separation of policy from mechanism.

![image](/assets/authorization-ocaps-vs-acl/keys-vs-cards.png)

**A physical key fuses policy and mechanism.** The shape of the key *is* the policy. The lock pins *are* the mechanism. They are literally the same object. Simple, fast, offline, and unchangeable — to change the policy you change the lock.

**A card key with a central ACL separates them.** The reader is the mechanism; it verifies identity. The database is the policy; it decides rights. You get dynamic updates, central revocation, and audit logs. You also get a dependency on an online check and centralized infrastructure.

**A capability token puts policy back in the artifact.** The token carries its own authorization. The mechanism is reduced to cryptographic verification.

Which looks like regression, and initially I read it as capabilities violating a principle I care about. It isn't, quite. The fusion is real, but what got fused is different:

```text
physical key   policy = key shape          permanent
capability     policy = token claims       temporal, scoped, revocable
```

It is a physical key that dissolves after an hour, only works during business hours, can be remotely deactivated, and changes shape depending on which door it is presented to. The bearer model's offline simplicity, with the database model's contextual control.

![image](/assets/authorization-ocaps-vs-acl/mechanism-policy-separation.png)

The generalization is that **policy/mechanism separation is not a binary but a question of where the seam sits**. You can push the seam down to the lock, out to a database, or into the credential. The third article's whole architecture is a specific choice about where to put that seam for agents.

## Local authority versus global knowledge

Lampson states the administrative case bluntly in [a 2020 retrospective](https://arxiv.org/pdf/2011.02455):

> Only ACLs work for managing the policy, because the manager's question is, "Who has access to this resource?" It's okay to make short-term copies of parts of it into capabilities (usually called file descriptors), which are faster to check.

Hence the slogan: capabilities are cached ACL decisions.

The slogan is right about a real thing and wrong about another. Sort the questions by who asks them.

A capability answers one question, perfectly and locally:

> May the holder of this perform operation X?

No lookup, no network, no identity resolution. The answer is in your hand.

A central authorization store answers the questions a capability cannot:

> Who can perform X?
> What can Alice access?
> Revoke everything derived from Alice's grant.
> Which of these ten thousand records may Alice see?

That last one deserves its own name. **Reverse indexability** — filtering a result set by authorization rather than checking one access — is the question that breaks capability systems in practice, and it is why data-centric authorization systems like Zanzibar exist. You cannot build a list page by asking the user to present every capability they might hold.

So:

> **Capabilities scale as an execution mechanism. Centralized authorization state scales as an administrative and query mechanism.**

Which resolves the argument without declaring a winner. ACLs are the right interface for humans managing policy. Capabilities are the right interface for programs enforcing it. Which one belongs at the core of your system depends on which question you most need to answer rigorously.

The sharper version of that is about principals. Zanzibar's are people and organizational relations: they change independently of the code, non-programmers have to modify them, and they must be enumerable and revocable on demand. Ocap's are code objects, where the topology is a program-structure question and the adversary is a buggy or hostile component rather than an over-privileged employee. Running both is normal rather than incoherent — Zanzibar-style relations at the user-facing boundary, capability discipline for confinement below it. Midori is the evidence. It is the most committed object-capability system anyone has shipped, and Duffy's retrospective still names policy management and the user-facing side as the part they left under-explored.

For a multi-user file server, the administrative question dominates and ACLs win. For a separation kernel running mutually suspicious components where you want a provable bound on blast radius, the propagation question dominates and capabilities win.

That second case is worth one more paragraph, because it is where the "cached decision" framing genuinely undersells what is happening. In seL4, the capability graph is not an optimization of some authoritative ACL kept elsewhere. There is no elsewhere. The graph *is* the authority, and its static structure is the thing being reasoned about — not any individual access decision. Nothing is being cached, because there is no original.

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

## Where this leaves us

We now have two ways to say what authority exists and how it travels, and a reasonable account of when to reach for each. A capability graph bounds what a component can ever reach. An ACL lets an administrator answer who can reach a resource. A macaroon carries an attenuated grant across a process boundary without a round trip.

None of that stops anything.

A representation is a description. A program that ignores the description is not violating the capability model — it is operating outside it. Something has to make the description true: has to guarantee that every attempt to cause an effect actually encounters the check, that the check cannot be tampered with, and that no path around it exists.

That is the reference monitor, and it is the second article in this series.

## References

- [The Protection of Information in Computer Systems](https://www.cs.virginia.edu/~evans/cs551/saltzer/) — Saltzer and Schroeder, including the three objections to capabilities and the recommendation that shaped every mainstream OS
- [Capability Myths Demolished](https://cgi.cse.unsw.edu.au/~cs9242/20/papers/Miller_YS_03.pdf) — Miller, Yee, Shapiro on the duality myth, designation, and confinement
- [Robust Composition](http://www.erights.org/talks/thesis/markm-thesis.pdf) — Miller's thesis; ambient versus excess authority, and "only connectivity begets connectivity"
- [The Confused Deputy](https://www.cs.utexas.edu/~witchel/S25-380L/papers/hardy88confused.pdf) — Hardy, 1988
- [Authorization (Lampson)](https://arxiv.org/pdf/2011.02455) — the "caps are cached ACL decisions" position
- [Macaroons: Cookies with Contextual Caveats](https://static.googleusercontent.com/media/research.google.com/en/us/pubs/archive/41892.pdf) — attenuable bearer capabilities
- [JWT, RFC 7519](https://www.rfc-editor.org/rfc/rfc7519.html) and [OAuth 2.0, RFC 6749](https://www.rfc-editor.org/rfc/rfc6749.html)
- [The State of the Union of Authorization](https://idpro.org/the-state-of-the-union-of-authorization/) — the landscape diagram
- [Type Enforcement](https://en.wikipedia.org/wiki/Type_enforcement) — why the MAC/RBAC relationship is not a simple ladder
- [The Ultimate Guide to Choosing the Right Authorization Language](https://axiomatics.com/wp-content/uploads/2024/10/the-ultimate-guide-to-choosing-the-right-authorization-language-whitepaper-axiomatics-10-16-2024.pdf) — XACML versus Rego
- [Objects as Secure Capabilities](https://joeduffyblog.com/2015/11/10/objects-as-secure-capabilities/) — Duffy on Midori; the capability oracle at `main`, no mutable statics, and where it fell short
- [Capsicum: Practical Capabilities for UNIX](https://www.usenix.org/conference/usenixsecurity10/capsicum-practical-capabilities-unix) — ambient authority removed from a real Unix
- [Zanzibar: Google's Consistent, Global Authorization System](https://research.google/pubs/pub48190/) — relationship-based authorization and reverse indexability
