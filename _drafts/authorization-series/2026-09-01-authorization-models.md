---
title:  "Authorization models: what every system computes"
series: "Authorization, Part 1"
series_url: "/programming/authorization-series-intro.html"
category: programming
date:   2026-09-01
---

> This is Part 1 of a six-part [series on authorization](/programming/authorization-series-intro.html).
>
> 0. **[Prologue: Who is the adversary](/programming/who-is-the-adversary.html)** — five positions the attacker has occupied, and why identity stopped being the useful thing to key on.
> 1. **Authorization models** — what every system computes, and who may change it.
> 2. **[Carriers](/programming/carriers.html)** — decisions that travel with the request.
> 3. **[Capabilities](/programming/capabilities.html)** — authority you hold, not authority you are.
> 4. **[How authority is enforced](/programming/authority-enforcement.html)** — what makes any of it binding.
> 5. **[LLM sandboxing](/programming/llm-sandbox.html)** — the gateway, correct and unavoidable.

- [Mathematical Framework](#mathematical-framework)
- [Data Models](#data-models)
  - [Access Control Matrix: ACL and Capability Lists](#access-control-matrix-acl-and-capability-lists)
  - [RBAC](#rbac)
  - [ABAC](#abac)
- [Real World Examples](#real-world-examples)
- [Policy Modification](#policy-modification)
  - [DAC and MAC are not rungs](#dac-and-mac-are-not-rungs)
  - [Policies compose, and the rule is not the same as the edit right](#policies-compose-and-the-rule-is-not-the-same-as-the-edit-right)
- [References](#references)

Despite security and authorization having been parts of computer science and programming for decades, the field is still [evolving rapidly][state-union-authorization]:

![](/assets/authorization/auth-timeline.png)

While still being quite fragmented in practice, there is a growing understanding of the underlying principles that govern how authority is represented and managed, and we are starting to see a convergence on the fundamental abstractions that underlie all models. The [series intro](/programming/authorization-series-intro.html) lays out the parts of an authorization system and six columns for describing one. This article covers three of them: Model and Policy, what the rules mean and how they are written, and Administration, who may change them.

## Mathematical Framework

Abstractly, every authorization system evaluates a function of the form[^authzen-shape]:

```text
f(subject, action, resource, context) → allow | deny
```

where:
- **Subject** is who is asking
- **Action** is what they want to do
- **Resource** is what they want it done to
- **Context** is everything else that bears on the answer and belongs to none of the first three: time of day, device information, network location, risk score, whether the country is at war, etc.

## Data Models

The authorization function is stateful, and hence there are different ways to represent it and manage it.

![Data models](/assets/authorization/data-models.svg)

Six ways to write down the same `f`, on one running example. The first five are notations for the rectangle; the last is a different matrix. Going down from ACL to ReBAC, each step means smaller storage and easier to administer, with more work at request time, and that is the whole trade.

| model | how `f` is represented | subject | resource | context | projected back onto the matrix |
| --- | --- | --- | --- | --- | --- |
| **ACL** | stored, indexed by resource | enumerated identity | one list per object | none | reindex by column — exact, invertible |
| **capability list** | stored, indexed by subject | enumerated identity | one list per subject | none | reindex by row — exact, invertible |
| **RBAC** | factored: subject → role → permission | coarsened into roles, the shared middle term | enumerated per role | none; faking it explodes the role set | expand the roles — exact |
| **ABAC** | not stored; a predicate evaluated per request | attributes, open-ended | attributes | first-class, the axis a table does not have | evaluate the predicate over every pair — exact |
| **ReBAC** | derived from a graph of tuples | graph node, reached through groups | fine-grained through hierarchy, without enumeration | none in Zanzibar; per-edge caveats in SpiceDB and OpenFGA | run the check over every pair — exact |
| **object capability** | held as references, over a square matrix | any entity | any entity — subjects and resources are one set | n/a: authority is held, not decided per request | flatten reachability — **lossy** |

The last column is what makes them one family. Each model is a denormalized encoding of the same matrix, and a check is that encoding reified into a view for a single `(subject, action, resource, context)` point. Forwards is faithful. Backwards is underdetermined — you cannot recover which factorization, which predicate, or which tuples produced a given set of cells.

Only the last row is lossy, and it is worth saying exactly where. An object-capability graph *is* a matrix — the [square one](/programming/capabilities.html#squaring-the-matrix). What is not faithful is squashing it back into a rectangle by declaring some entities to be subjects and the rest to be resources. `Alice: rw X` is a true statement about what Alice can eventually cause and a false statement about the authority she holds: the projection computes reachability and throws away the path, so Bob disappears from a description of a system whose entire structure is that Bob is in the middle. Two more things go with him: every cell that was a subject talking to a subject, and the rule that said which cells could be written next.

### Access Control Matrix: ACL and Capability Lists

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

Store it by row, at the subject, and you get a **capability list**[^access-profile]:

```text
Alice → File A: rw, File B: r
Bob   → File B: rw, Device C: use
```

The same information, transposed. This is the observation that makes people say ACLs and capabilities are dual, and at this level they are. A file descriptor is a capability; `/etc/passwd`'s mode bits are an ACL; both describe cells of the same matrix.

Hold that claim loosely. The matrix describes permissions at an instant. It says nothing about how a cell got filled in, who is allowed to fill in another one, or what happens when Alice hands Bob something. The [capabilities article](/programming/capabilities.html) is mostly about dismantling the duality this suggests. This one stays with the snapshot and asks the one dynamic question the matrix can almost answer: who edits it?

Worth knowing what the matrix cannot answer before leaning on it. Once cells can be edited, the question you most want to ask — *can this permission ever reach that subject, by any sequence of legal edits* — is undecidable in the general case. Harrison, Ruzzo and Ullman proved it in 1976, and the result is why every tractable model since is a deliberate restriction of the general protection system rather than an implementation of it: take-grant, typed matrices, and the bounded schemes real engines actually ship. Keep it in view for the [capabilities article](/programming/capabilities.html), where the same question comes back as the thing capabilities are worst at.

### RBAC

RBAC inserts a reusable layer *between* subject and permission, so that `Users × Permissions` factors into `(Users × Roles)` and `(Roles × Permissions)`. The saving comes from sharing the middle term across many subjects, not from changing which end of the matrix the data hangs off.

### ABAC

ABAC is where the industry landed for anything complicated, with XACML and OPA's Rego as the two main expressions. Both share a shape: a policy document, a set of facts about subject and resource and environment, and an engine that evaluates one against the other at request time.

A table indexed by subject and resource has two axes. Action fits in the cell. Context fits nowhere. There is no coordinate for "between 9 and 5," or "from a managed device," or "while the incident is open." You can fake it by multiplying out subjects — a `finance-daytime` role — but that is role explosion arriving on schedule.

This is the real reason ABAC and its risk-adaptive variants exist. Not because subjects needed richer description, but because `f` grew a fourth argument and the table had no axis for it. Once you are evaluating a predicate at request time, context is free.

## Real World Examples

| system | model |
| --- | --- |
| POSIX mode bits, NT ACLs, Postgres `GRANT`, S3 bucket policies | ACL |
| Linux file descriptors, `CAP_*` bounding sets | capability list |
| LDAP / Active Directory groups, Kubernetes RBAC, GitHub org roles | RBAC |
| SELinux type enforcement | type-based compression of the matrix, with MAC mutation |
| XACML / Axiomatics, OPA / Rego, AWS IAM condition keys | ABAC |
| Zanzibar, Ory Keto | ReBAC |
| SpiceDB, OpenFGA | ReBAC with per-edge context (caveats, conditions) |
| Cedar / AWS Verified Permissions, Oso, Aserto Topaz | ReBAC and ABAC in one language |
| KeyKOS, EROS, seL4, Fuchsia, Cap'n Proto, WASI Preview 2 | object capability |

## Policy Modification

Everything so far is about evaluating `f`. There is a second question underneath it that gets far less attention and turns out to matter more: **who is allowed to change `f`, and where do they go to do it?**. A policy that cannot be widened without a deploy is a policy that gets widened to `*` in advance. The cost of granting a legitimate exception is a security property, not an ergonomics complaint, and it is the one that decides whether the system is still enforcing anything six months later.

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

Six of those seven answers are a version of "someone with administrative standing," and they all have to be supplied from outside the model. The seventh is the rule the [square matrix](/programming/capabilities.html#squaring-the-matrix) states about itself, and it is the argument of the capabilities article.

There is a sharper way to see the split. Ask whether the mutation right is **monotone**. Delegation can only ever hand on less than the holder has, so authority shrinks along every edge. Administrative rights do the opposite: they manufacture authority the grantor does not hold, which is what makes "admin" a different power rather than a larger one. Two very different things wear the same word, and Part 3 depends on keeping them apart.

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

Part 5 runs into this directly. An agent's effective authority is the conjunction of an org policy, the user's grant, the repository's branch protection and the tool's own rules — four policies, four owners, and no agreed account of how they combine.

Everything in this article decides at the resource. The PDP looks up what was written and computes `f`. The [next article](/programming/carriers.html) asks what changes when the request brings a copy of the decision with it.

## References

1. [The State of the Union of Authorization][state-union-authorization] — the landscape diagram
2. [Protection][protection] — Lampson, 1974; the access matrix
3. [From ABAC to ZBAC: The Evolution of Access Control Models][from-abac-zbac-evolution] — Karp, Haury, Davis; the observation that the matrix has no theory of its own mutation
4. [Type Enforcement][type-enforcement] — why the MAC/RBAC relationship is not a simple ladder
5. [The Ultimate Guide to Choosing the Right Authorization Language][ultimate-guide-choosing-right] — XACML versus Rego
6. [Zanzibar: Google's Consistent, Global Authorization System][zanzibar-google-s-consistent] — relationship-based authorization
7. [AuthZEN][authzen] — standardizing the decision-point interface; its [information model][authzen-spec] is where the subject/action/resource/context request is defined

[authzen]: https://openid.net/wg/authzen/ "AuthZEN - OpenID Foundation working group"
[authzen-spec]: https://openid.net/specs/authorization-api-1_0.html#name-information-model "Authorization API 1.0: information model - OpenID Foundation"
[from-abac-zbac-evolution]: https://shiftleft.com/mirrors/www.hpl.hp.com/techreports/2009/HPL-2009-30.pdf "From ABAC to ZBAC: The Evolution of Access Control Models"
[protection]: https://www.microsoft.com/en-us/research/publication/protection/ "Protection"
[rfc4949]: https://datatracker.ietf.org/doc/html/rfc4949 "RFC 4949: Internet Security Glossary, Version 2"
[state-union-authorization]: https://idpro.org/the-state-of-the-union-of-authorization/ "The State of the Union of Authorization"
[type-enforcement]: https://en.wikipedia.org/wiki/Type_enforcement "Type Enforcement"
[ultimate-guide-choosing-right]: https://axiomatics.com/wp-content/uploads/2024/10/the-ultimate-guide-to-choosing-the-right-authorization-language-whitepaper-axiomatics-10-16-2024.pdf "The Ultimate Guide to Choosing the Right Authorization Language"
[zanzibar-google-s-consistent]: https://research.google/pubs/pub48190/ "Zanzibar: Google's Consistent, Global Authorization System"

## Footnotes <!-- omit in toc -->

[^authzen-shape]: This signature doesn't generalize all authorization models by coincidence; it is also the signature that the industry converged on it and is in the process of standardizing via [AuthZEN][authzen], the OpenID Foundation's decision-point protocol. It deliberately says nothing about how the answer is reached. It standardizes only the shape of the question, which is a strong signal that the shape is the settled part.

[^access-profile]: [RFC 4949][rfc4949], the Internet Security Glossary, has a name for this row that keeps it away from the word capability: defining the access control matrix, it says "each row is equivalent to an *access profile* for the subject." The glossary does not actually recommend the term — `access profile` is marked "O", meaning non-Internet origin and not for use in Internet documents, and its entry reads only "synonym for capability list." `capability list` is the entry it recommends. The distinction RFC 4949 does draw is the one worth holding on to: a *capability list* enumerates what a subject may reach, while a *capability token* is an unforgeable object whose possession is itself the proof. Part 3 lives in the gap between those two. I keep "capability list" here, which also matches the Linux sense of the word — `CAP_NET_ADMIN` and friends are a per-process list of permitted operations, a row and not a token.
