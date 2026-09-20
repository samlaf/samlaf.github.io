---
title:  "Authorization models: what every system computes"
series: "Authorization, Part 1"
series_url: "/programming/authorization-series-intro.html"
category: programming
date:   2026-09-01
---

> This is Part 1 of a four-part [series on authorization](/programming/authorization-series-intro.html).
>
> 1. **Authorization models** — what every system computes, and who may change it.
> 2. **[Capabilities](/programming/capabilities.html)** — authority you hold, not authority you are.
> 3. **[How authority is enforced](/programming/authority-enforcement.html)** — what makes any of it binding.
> 4. **[LLM sandboxing](/programming/llm-sandbox.html)** — the gateway, correct and unavoidable.

- [The shape of the question](#the-shape-of-the-question)
  - [Every model is a way of not evaluating f](#every-model-is-a-way-of-not-evaluating-f)
  - [Context is the term the table cannot hold](#context-is-the-term-the-table-cannot-hold)
- [The matrix and its two projections](#the-matrix-and-its-two-projections)
  - [`open` is the conversion](#open-is-the-conversion)
  - [Make both axes the same set](#make-both-axes-the-same-set)
- [Who may change a cell](#who-may-change-a-cell)
  - [DAC and MAC are not rungs](#dac-and-mac-are-not-rungs)
  - [Policies compose, and the rule is not the same as the edit right](#policies-compose-and-the-rule-is-not-the-same-as-the-edit-right)
  - [What the factoring costs](#what-the-factoring-costs)
  - [One family, one notation](#one-family-one-notation)
- [Identity is not authority](#identity-is-not-authority)
  - [The four steps](#the-four-steps)
  - [Where, and when](#where-and-when)
  - [Tokens as reified decisions](#tokens-as-reified-decisions)
- [Five concerns, not one axis](#five-concerns-not-one-axis)
- [Where this leaves us](#where-this-leaves-us)
- [References](#references)


Ask what authorization is and you will get an answer about deciding. Can Alice read this file? Is this token valid? Does this role include that permission. Deciding matters, but it is the second question. The first is where the answer lives before anyone asks.

A system has to put authority somewhere. It can keep a list at each resource naming who may touch it. It can hand each subject a set of unforgeable references to the things it may touch. It can keep a database of relationships and compute the answer on demand. These are not implementation details that wash out at scale. Each one makes a different set of questions cheap and a different set expensive, and the expensive questions are the ones that eventually break your architecture.

Underneath both sits a question that is easy to skip: **who is allowed to change the answer, and where do they go to do it?** The models differ more on that than on anything else, and almost nobody sorts them by it.

This article is about representation and mutation only. It deliberately does not answer *what authority should exist* — that is a policy question, and it belongs to the fourth article. It also does not answer what stops a program from ignoring the representation entirely. That is the third.

![image](/assets/authorization/auth-models.png)

*From [The State of the Union of Authorization](https://idpro.org/the-state-of-the-union-of-authorization/).*

## The shape of the question

Deciding is the second question, but it is still worth writing down precisely what gets decided — because every model below is a different way of *avoiding* that computation.

Strip away the storage and every authorization system evaluates the same function:

```text
f(subject, action, resource, context) → allow | deny
```

**Subject** is who is asking. **Action** is what they want to do. **Resource** is what they want it done to. **Context** is everything else that bears on the answer and belongs to none of the first three: time of day, device posture, network location, risk score, whether the country is at war.

That signature is not a convenient abstraction I am imposing. The industry converged on it and then standardized it. [AuthZEN](https://openid.net/wg/authzen/), the OpenID Foundation's decision-point protocol, defines its request as exactly those four objects — subject, action, resource, context — and its response as a boolean. It deliberately says nothing about how the answer is reached. It standardizes only the shape of the question, which is a strong signal that the shape is the settled part.

### Every model is a way of not evaluating f

Nobody stores `f`. It is astronomically large and it changes constantly. So every access control model is a scheme for producing `f`'s answers without ever writing `f` down, and they differ in which argument they attack:

```text
ACL               tabulate f, indexed by resource
capability list   tabulate f, indexed by subject

RBAC              factor the subject      f(role(s), a, r)
MAC               factor both ends        label(s) ⊒ label(r)
ABAC              do not tabulate         a predicate over s, a, r, c
ReBAC             derive from a graph     is r reachable from s
                                          along an allowed path?

object capability tabulate f by subject, over a square matrix
```

Read that list and the usual ladder stops looking like increasing sophistication. RBAC is a factoring. MAC is a different factoring. ABAC gives up on tabulation and computes. ReBAC gives up on enumeration and derives. Each buys smaller storage with more work at request time, and that is the whole trade.

The last line is the one this series is really about, and notice how little it differs from the second. An object capability evaluates `f` the same way a capability list does: look in the subject's row. Whatever makes it interesting is not in this column at all. The word *square* is doing all the work, and the rest of the article is about unpacking it.

### Context is the term the table cannot hold

One argument of `f` deserves separate attention, because its arrival is what broke the older models.

A table indexed by subject and resource has two axes. Action fits in the cell. Context fits nowhere. There is no coordinate for "between 9 and 5," or "from a managed device," or "while the incident is open." You can fake it by multiplying out subjects — a `finance-daytime` role — but that is role explosion arriving on schedule.

This is the real reason ABAC and its risk-adaptive variants exist. Not because subjects needed richer description, but because `f` grew a fourth argument and the table had no axis for it. Once you are evaluating a predicate at request time, context is free.

It is also the argument with the worst behaviour over time, and the [third article](/programming/authority-enforcement.html) takes that apart: each of `f`'s terms resolves against state someone else can change, on its own clock, and context is the one people model least and check least.

## The matrix and its two projections

Tabulating `f` over subjects and resources gives the picture everything else is a reaction to. Start with the simplest model that captures the problem. Lampson's access-control matrix has subjects down one axis, objects across the other, and permitted operations in the cells.

```text
             File A    File B    Device C
Alice          rw        r
Bob                      rw        use
```

The matrix is a tabulation, so nobody stores it either — it is mostly empty. Real systems store one of its two projections.

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

Hold that claim loosely. The matrix describes permissions at an instant. It says nothing about how a cell got filled in, who is allowed to fill in another one, or what happens when Alice hands Bob something. The [next article](/programming/capabilities.html) is mostly about dismantling the duality this suggests. This one stays with the snapshot and asks the one dynamic question the matrix can almost answer: who edits it?

### `open` is the conversion

The two projections meet in a system call you use every day, and it is worth sitting with because the difference is visible in the types.

A pathname is plain data. It names a slot in a global namespace, anyone can utter one, and uttering it conveys nothing. The descriptor `open` returns is a handle in a small per-process table that previous authorization decisions populated. You cannot guess one, and holding it is the whole of your permission to act.

So `open` converts a name into a handle, and the check happens exactly once, at the conversion. [`pidfd` does the same for processes](/programming/everything-is-a-file.html), turning a guessable, reusable integer into possession of one specific object.

Every architecture in these four articles is a variation on where you put that conversion and how much you can do on the far side of it.

### Make both axes the same set

The matrix assumes something it never argues for: that the world divides cleanly into subjects who act and resources that are acted upon. Alice is a row. File A is a column. Nothing is both.

That assumption is what makes mediation inexpressible. If Alice holds a reference to Bob, and Bob holds a reference to X, the matrix wants to record `Alice: rw X`. That is wrong. Bob is in the middle, and Bob can refuse, revoke, log, or forward only a subset. To write it down you would need Bob to be a row *and* a column at once, and in a rectangular matrix he cannot be.

So drop the assumption. Let both axes range over the same set of entities, and read a cell as *which of Y's operations may X invoke*:

```text
          Alice    Bob    File A    Logger
Alice        —     call     rw         —
Bob          —       —      r        write
File A       —       —       —         —
Logger       —       —       —         —
```

Everything still works. ACLs and capability lists are the special case where the entity set partitions into two disjoint halves, so the bottom-left block is empty by construction and you may as well draw the matrix rectangular. Nothing is lost by squaring it; things become expressible that were not.

Three of them, and each is a rung the older models could not reach.

**Mediation.** Bob is a row and a column. `Alice → Bob → X` is two cells, not one, and the difference between them is the entire value of a proxy.

**Communication as an access decision.** A cell `(Alice, Bob)` is a subject reaching a subject. Whether Alice may *talk to* Bob is now the same kind of question as whether Alice may read a file, answered by the same mechanism. In a rectangular matrix there is nowhere to ask it, which is why every model above treats connectivity as someone else's problem — the network's, the linker's, the runtime's.

**A mutation rule written in the matrix's own terms.** Every model so far needs an outside notion of who may edit: an owner, an administrator, a lattice, a policy document. A square matrix can state its own rule. *Alice may write into Bob's row only if her own row already reaches both Bob and the thing she is granting.* Authority moves only along edges that already exist.

That last one is the whole of the next article compressed into a sentence, and it is why the entity set also has to be allowed to grow: attenuation means minting a new proxy, which is a new row and a new column appearing at runtime.

## Who may change a cell

Everything so far is about evaluating `f`. There is a second question underneath it that gets far less attention and turns out to matter more: **who is allowed to change `f`, and where do they go to do it?**

Karp puts his finger on why it gets neglected. Writing about the earliest identity-based systems:

> IBAC stores permissions in an access matrix, and the IBAC model doesn't include a specification of permissions for changing its entries. That left it to a trusted party, the system administrator.

The matrix has no theory of its own mutation. Every model since is an answer to that gap, and the answers differ from each other far more than the evaluation schemes do.

```text
ACL / DAC          the owner
MAC                nobody, beyond the lattice
RBAC               admins, plus whoever holds role-grant rights
ABAC               whoever owns the policy document
ReBAC              whoever may write tuples
capability list    still the administrator
object capability  the holder
```

Six of those seven answers are a version of "someone with administrative standing," and they all have to be supplied from outside the model. The seventh is the rule the square matrix states about itself, and it is the argument of the next article.

There is a sharper way to see the split. Ask whether the mutation right is **monotone**. Delegation can only ever hand on less than the holder has, so authority shrinks along every edge. Administrative rights do the opposite: they manufacture authority the grantor does not hold, which is what makes "admin" a different power rather than a larger one. Two very different things wear the same word, and article two depends on keeping them apart.

There is a second question hiding in the same list: *where do you go* to make the change. To give Bob everything Alice has under an ACL, you visit every object. Under a capability list you go to Alice. That is a real operational difference and it is invisible in the evaluation view.

### DAC and MAC are not rungs

The clean ladder oversimplifies, and the first two entries are where it does the most damage.

DAC and MAC are usually presented as the first two levels of increasing sophistication in describing a subject. They are not. Neither says anything about how the matrix is indexed. The **D** in discretionary means *the owner may change the matrix at their discretion*. The **M** in mandatory means *the owner may not* — a lattice constrains every edit, including the administrator's. Both are answers to the mutation question and nothing else.

Once you see that, an old confusion goes away. SELinux's type enforcement is a *compression* choice: a security context is the full `user:role:type:level` tuple, and access is decided between types rather than users. MAC is a *mutation* choice. They are complements in that design, which is exactly what you would expect from two answers to two different questions, and not at all what you would expect from two rungs of one ladder.

### Policies compose, and the rule is not the same as the edit right

One more thing hides in the mutation column, and the MAC row is where it shows.

I wrote that under MAC nobody may change a cell beyond what the lattice permits. That describes the effect and not the mechanism. What is actually happening is that `f` is computed from two policies with two different authors, combined with a conjunction:

```text
f = mandatory ∧ discretionary
```

The owner may still edit the discretionary half freely. They simply cannot relax the other half, because the combining rule is an `and`. Mandatory versus discretionary is a statement about *composition*, not about edit rights.

Once you look for it, composition is everywhere and rarely specified. XACML names its combining algorithms explicitly — deny-overrides, permit-overrides, first-applicable — which is more than most systems do. Real deployments stack an organizational policy, a team policy, a resource owner's settings and a per-request grant, and the rule for combining them is usually whatever the code happens to do.

The fourth article runs into this directly. An agent's effective authority is the conjunction of an org policy, the user's grant, the repository's branch protection and the tool's own rules — four policies, four owners, and no agreed account of how they combine.

### What the factoring costs

Read the evaluation list as a cost curve and it is a genuine progression:

```text
ACL     store the relation
RBAC    factor the relation     subject → role → permission
ABAC    compute the relation    a predicate over attributes
ReBAC   derive the relation     a graph plus composition rules
```

Store, factor, compute, derive. Each is cheaper to administer than the one before and more expensive to evaluate, which is the entire trade.

![image](/assets/authorization/access-control-models.png)

This also disposes of a confusion worth naming. RBAC is sometimes described as putting the ACL on the subject. It is not — that is a capability list. RBAC inserts a reusable layer *between* subject and permission, so that `Users × Permissions` factors into `(Users × Roles)` and `(Roles × Permissions)`. The saving comes from sharing the middle term across many subjects, not from changing which end of the matrix the data hangs off.

ABAC is where the industry landed for anything complicated, with XACML and OPA's Rego as the two main expressions. Both share a shape: a policy document, a set of facts about subject and resource and environment, and an engine that evaluates one against the other at request time.

### One family, one notation

There is a sharper way to state what the evaluation list shows. Project every model back onto the matrix and watch what happens to the information.

```text
ACL               reindex by column              exact, invertible
capability list   reindex by row                 exact, invertible
RBAC              expand the roles               exact
ABAC              evaluate the predicate         exact
ReBAC             run the check over every pair  exact

ocap graph        flatten reachability           lossy
```

The first five are notations for a matrix. Running them backwards is underdetermined — you cannot recover which factorization, which predicate, or which tuples produced a given set of cells — but running them forwards is faithful. Each computes the same `f`, which is exactly why they form one family.

The last line is the lossy one, and now we can say exactly which step loses the information. An object-capability graph *is* a matrix — the square one. What is not faithful is squashing it back into a rectangle by declaring some entities to be subjects and the rest to be resources.

`Alice: rw X` is a true statement about what Alice can eventually cause and a false statement about the authority she holds. The projection computes reachability and throws away the path, so Bob disappears from a description of a system whose entire structure is that Bob is in the middle. Two more things go with him: every cell that was a subject talking to a subject, and the rule that said which cells could be written next.

One thing does survive. A single cell can be materialized as a handle, which is the pipeline the fourth article is built on. Materializing cells one at a time is not the same as recovering the structure.

## Identity is not authority

Every model in that family decides at the resource. The subject presents a credential and the system works out what it means. But the credential can carry wildly different amounts of already-decided authority, and the difference is worth a ladder of its own.

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

Going down the ladder moves work from request time to issue time. This is the sense in which capabilities "shift left": the hard policy evaluation happens once, when the credential is minted, and every subsequent use is a cheap validity check. Pre-signed S3 URLs do exactly this. So do OAuth access tokens and Kubernetes service account tokens. The authorization server does the expensive relationship and attribute work; the resource server checks a signature.

One thing the ladder does not tell you is whether the credential is a bearer instrument or bound to a key the holder must prove control of. That axis is orthogonal — an identity assertion can be either, and so can a capability — and it is [the crypto series' subject](/programming/authentication.html), which follows the fifty-year migration from bearer tokens to key-bound ones in detail. The only thing to carry here is that an mTLS-bound token and a string in an `Authorization` header can sit at the same rung of this ladder and have completely different theft properties.

### The four steps

The ladder mixes up something the next article needs kept apart, so it is worth fixing the vocabulary now. Karp decomposes access control into four steps:

```text
Identification    knowing whom to hold responsible for authorized actions
Authentication    what allows a process to use permissions assigned to
                  an identity
Authorization     granting a permission; this is the act that expresses
                  policy
Access decision   deciding whether or not to honor a particular request
```

These are easy to conflate and worth separating even in an ordinary system. On Unix, identification is creating the account. Authentication lets a process prove it runs on your behalf. Putting an entry in an ACL is an act of authorization. Checking that ACL is the access decision.

Everything in the table above performs the last three in the resource's domain, and authentication and the access decision at request time. That is not the only arrangement available, and the [next article](/programming/capabilities.html) is largely about what changes when you move them.

### Where, and when

Two questions about those four steps get collapsed constantly, and separating them is worth doing once, carefully.

**Where** is the authorization decision made — in the resource's domain, or the subject's?

**When** is it made — at request time, or settled in advance and carried along?

They look like the same question and they are not. Two systems already in this article prove it.

```text
                  where              when
presigned URL     resource owner     in advance
ZBAC token        subject's domain   in advance
```

Same binding time. Opposite jurisdiction. And everything that makes the second interesting — no federated identity, no shared vocabulary of roles, no need to tell your counterparty how your organization is structured — follows from the *where*, not the *when*.

This matters because "shift left" is a claim about **when**, and it gets read as a claim about **where**. Moving a decision earlier buys you latency and offline operation. Moving it into the subject's domain buys you cross-organizational scale. You can have either without the other, and most systems that claim the second have only bought the first.

The **when** axis has a cost that shows up later in this series and is worth naming now: a decision settled in advance is a decision that can go stale. The third article takes apart exactly which of `f`'s four arguments can move underneath you between the moment of decision and the moment of effect.

### Tokens as reified decisions

Macaroons, JWTs, and OAuth access tokens are none of the architectures discussed so far. They are **artifacts**: a previous authorization, serialized so a later request need not return to the decision-maker and reconstruct it.

The "cached decision" framing is close but not exact. A verifier still checks signature, issuer, audience, and expiry, and often consults current resource state. A JWT frequently carries *claims* from which the resource server makes a fresh decision rather than a final allow.

[Macaroons](https://static.googleusercontent.com/media/research.google.com/en/us/pubs/archive/41892.pdf) go furthest. A holder can attenuate one by appending caveats — repository, method, time window, request budget, a required third-party discharge — without the root key and without going back to the issuer:

```text
may access GitHub
    only repository X
    only pull-request operations
    before 17:00
    for sandbox Y
```

That is attenuation as a property of the artifact rather than of a process profile. The constraints travel with the token instead of living in some verifier's memory, and a stolen macaroon is worth only what its caveats already permitted.

## Five concerns, not one axis

Everything above treats authorization as one question with competing answers. It is not, and a great many arguments about it are category errors — comparing a policy engine to a credential format to a communication model as though they were rival answers to the same thing.

![image](/assets/authorization/authorization-concerns.png)

Pulled apart, there are five separable concerns:

```text
1  identity & authentication   who is this?
                               passwords, passkeys, mTLS, OIDC
                               → the crypto series

2  policy & decision           f(subject, action, resource, context)
                               OPA, Cedar, Zanzibar, XACML, AuthZEN

3  delegation                  how is authority requested, issued, passed on?
                               OAuth 2, GNAP, SPKI, macaroon caveats

4  credential                  what artifact carries the authority?
                               JWT, macaroon, biscuit, opaque handle

5  communication & reference   how do subjects reach objects at all?
                               URLs, gRPC, service mesh, Cap'n Proto,
                               file descriptors
```

Most real systems mix and match. OAuth is a delegation protocol plus a credential format that leaves policy and communication entirely alone. Zanzibar is a policy engine with nothing to say about credentials. A macaroon is a credential that happens to carry its own attenuation rules. Cap'n Proto is a communication model that carries authority as a side effect of how you address things.

Which is the useful frame for the rest of the series. The industry has spent twenty years building columns two, three and four, and they are genuinely good now. Column five is nearly empty, almost nobody treats it as an authorization concern at all — and it is the only place where the property that distinguishes capabilities from tokens can live.

## Where this leaves us

We have a way to say what authority exists, a way to say who may change it, and a vocabulary for the five jobs a complete system has to do. What we do not yet have is a straight answer about the one word that keeps appearing in every column.

"Capability" has meant four different things in this article alone — a row of the matrix, a scoped token, an artifact carrying caveats, an unforgeable reference. Those are not the same thing, most of the famous objections are true of some and false of others, and the differences decide what you can build. That is the next article.

And none of it stops anything. A representation is a description. A program that ignores the description is not violating the model — it is operating outside it. Something has to make the description true: has to guarantee that every attempt to cause an effect actually encounters the check, that the check cannot be tampered with, and that no path around it exists.

That is the reference monitor, and it is the third article.

## References

- [The State of the Union of Authorization](https://idpro.org/the-state-of-the-union-of-authorization/) — the landscape diagram
- [Protection](https://www.microsoft.com/en-us/research/publication/protection/) — Lampson, 1974; the access matrix
- [From ABAC to ZBAC: The Evolution of Access Control Models](https://shiftleft.com/mirrors/www.hpl.hp.com/techreports/2009/HPL-2009-30.pdf) — Karp, Haury, Davis; the four steps, and the observation that the matrix has no theory of its own mutation
- [Type Enforcement](https://en.wikipedia.org/wiki/Type_enforcement) — why the MAC/RBAC relationship is not a simple ladder
- [The Ultimate Guide to Choosing the Right Authorization Language](https://axiomatics.com/wp-content/uploads/2024/10/the-ultimate-guide-to-choosing-the-right-authorization-language-whitepaper-axiomatics-10-16-2024.pdf) — XACML versus Rego
- [Zanzibar: Google's Consistent, Global Authorization System](https://research.google/pubs/pub48190/) — relationship-based authorization
- [Macaroons: Cookies with Contextual Caveats](https://static.googleusercontent.com/media/research.google.com/en/us/pubs/archive/41892.pdf) — attenuable bearer capabilities
- [JWT, RFC 7519](https://www.rfc-editor.org/rfc/rfc7519.html) and [OAuth 2.0, RFC 6749](https://www.rfc-editor.org/rfc/rfc6749.html)
- [AuthZEN](https://openid.net/wg/authzen/) — standardizing the decision-point interface
