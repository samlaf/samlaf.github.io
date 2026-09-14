---
title:  "Where authority lives: ACLs, capabilities, and delegation"
category: programming
date:   2026-09-01
---

> This is the first of three articles on authorization.
>
> 1. **Where authority lives** — how a system represents authority, and how authority moves between principals.
> 2. **How authority is enforced** — what makes those limits non-bypassable.
> 3. **LLM sandbox = compute isolation + authority mediation** — how the two combine for agents.

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
- **Designation and authority coincide.** Saying *which* object and saying *that you may use it* are the same act. This is what kills the confused deputy, as we will see.
- **Delegation is reference-passing.** To give Bob authority, hand him the reference. No registry updates, no central grant.
- **Attenuation.** You can wrap a reference in a proxy that forwards a subset of operations, and hand that on instead.
- **Reachability bounds authority.** What a subject can ever affect is the transitive closure of the references it holds. Absence of a reference is a hard limit, not a denied request.
- **No ambient authority.** A subject acts only through references it was given. It has no background powers it can invoke by virtue of who it is.

That last property is the real dividing line, and it is invisible in the matrix. In a Unix process, opening a file requires only a *name* — the authority comes from the process's identity, floating in the background. In an ocap system, the name *is* the authority, and you only have names someone handed you.

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

The clean ladder also oversimplifies. MAC is not simply "RBAC plus levels": SELinux's type enforcement is a prerequisite for MAC and a first step toward multilevel security, and its security context is the full `user:role:type:level` tuple rather than a single clearance. Type enforcement and RBAC are complements in that design, not rungs.

ABAC is where the industry landed for anything complicated, with XACML and OPA's Rego as the two main expressions. Both share a shape: a policy document, a set of facts about subject and resource and environment, and an engine that evaluates one against the other at request time.

Which is exactly the cost capabilities are trying to avoid.

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

The object-capability response is that S&S identified real problems and drew the wrong conclusion. Revocation has good answers: Redell's indirection — interpose a forwarder you can sever — is described in S&S's own paper, and it is the seed of what later became the membrane pattern. Propagation can be controlled by being careful about which references you hand out in the first place. Audit is recoverable by other means.

Meanwhile, the argument runs, ACL systems have pathologies of their own that are worse than what they fix. Norm Hardy's [The Confused Deputy](https://www.cs.utexas.edu/~witchel/S25-380L/papers/hardy88confused.pdf) is the canonical statement: a program holding ambient authority is asked by an untrusted caller to do something, and cannot tell which of its powers the request was entitled to invoke. The compiler writes to the billing file because it *can*, and because the request named a path rather than carrying a reference. Designation and authority came apart, and the deputy got confused in the gap.

There is a nice piece of historical irony here: the web copy of the S&S paper that everyone links to was put online by Norm Hardy.

### The patches converge

Here is the part that took me a while to see. Each side's fix for its own weakness imports the other side's core mechanism.

![image](/assets/authorization-ocaps-vs-acl/acl-vs-ocaps.png)

**Capabilities adding revocation.** You introduce indirection: the token no longer grants access directly, it points at something that can be invalidated. But that something lives in a table mapping tokens to validity. That table is a registry. You have rebuilt the ACL's central lookup with an extra hop. Expiry is the same move — you need a clock authority and a check on use.

**Capabilities adding audit.** Answering "who holds what?" requires tracking holders. That is a list of principals and their permissions.

**Capabilities adding policy-based issuance.** "Only managers get this capability" requires an identity system that knows who is a manager.

**ACLs adding confused-deputy protection.** Label the data, make every endorsement explicit, check types at boundaries. You are scoping authority to specific operations and trust levels — converging on the capability claim that authority should travel with the action rather than float around the deputy's identity.

So the honest summary is not that one wins. It is that a system with real-world requirements ends up needing both mechanisms, and the interesting design question is which one you put at the core.

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

## Where this leaves us

We now have two ways to say what authority exists and how it travels, and a reasonable account of when to reach for each. A capability graph bounds what a component can ever reach. An ACL lets an administrator answer who can reach a resource. A macaroon carries an attenuated grant across a process boundary without a round trip.

None of that stops anything.

A representation is a description. A program that ignores the description is not violating the capability model — it is operating outside it. Something has to make the description true: has to guarantee that every attempt to cause an effect actually encounters the check, that the check cannot be tampered with, and that no path around it exists.

That is the reference monitor, and it is the second article in this series.

## References

- [The Protection of Information in Computer Systems](https://www.cs.virginia.edu/~evans/cs551/saltzer/) — Saltzer and Schroeder, including the three objections to capabilities and the recommendation that shaped every mainstream OS
- [Capability Myths Demolished](https://cgi.cse.unsw.edu.au/~cs9242/20/papers/Miller_YS_03.pdf) — Miller, Yee, Shapiro on the duality myth, designation, and confinement
- [The Confused Deputy](https://www.cs.utexas.edu/~witchel/S25-380L/papers/hardy88confused.pdf) — Hardy, 1988
- [Authorization (Lampson)](https://arxiv.org/pdf/2011.02455) — the "caps are cached ACL decisions" position
- [Macaroons: Cookies with Contextual Caveats](https://static.googleusercontent.com/media/research.google.com/en/us/pubs/archive/41892.pdf) — attenuable bearer capabilities
- [JWT, RFC 7519](https://www.rfc-editor.org/rfc/rfc7519.html) and [OAuth 2.0, RFC 6749](https://www.rfc-editor.org/rfc/rfc6749.html)
- [The State of the Union of Authorization](https://idpro.org/the-state-of-the-union-of-authorization/) — the landscape diagram
- [Type Enforcement](https://en.wikipedia.org/wiki/Type_enforcement) — why the MAC/RBAC relationship is not a simple ladder
- [The Ultimate Guide to Choosing the Right Authorization Language](https://axiomatics.com/wp-content/uploads/2024/10/the-ultimate-guide-to-choosing-the-right-authorization-language-whitepaper-axiomatics-10-16-2024.pdf) — XACML versus Rego
- [Zanzibar: Google's Consistent, Global Authorization System](https://research.google/pubs/pub48190/) — relationship-based authorization and reverse indexability
