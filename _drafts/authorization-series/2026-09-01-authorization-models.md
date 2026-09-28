---
title:  "Authorization models: what every system computes"
series: "Authorization, Part 1"
series_url: "/programming/authorization-series-intro.html"
category: programming
date:   2026-09-01
---

> This is Part 1 of a six-part [series on authorization](/programming/authorization-series-intro.html).
>
> - **[Prologue: Who is the adversary](/programming/who-is-the-adversary.html)** — five positions the attacker has occupied, and why identity stopped being the useful thing to key on.
> - **Part 1: Authorization models** — what every system computes, and who may change it.
> - **[Part 2: How authority is enforced](/programming/authority-enforcement.html)** — what makes any of it binding.
> - **[Part 3: Carriers](/programming/carriers.html)** — decisions that travel with the request.
> - **[Part 4: Capabilities](/programming/capabilities.html)** — authority you hold, not authority you are.
> - **[Part 5: LLM sandboxing](/programming/llm-sandbox.html)** — the gateway, correct and unavoidable.

- [One function, one relation](#one-function-one-relation)
- [The write path](#the-write-path)
  - [Facts: schemas for the matrix](#facts-schemas-for-the-matrix)
    - [Access control lists and capability lists](#access-control-lists-and-capability-lists)
    - [RBAC](#rbac)
    - [ABAC](#abac)
    - [ReBAC](#rebac)
  - [Rules: a policy is a view](#rules-a-policy-is-a-view)
  - [Writers](#writers)
    - [DAC and MAC are not rungs](#dac-and-mac-are-not-rungs)
    - [Policies compose, and the rule is not the same as the edit right](#policies-compose-and-the-rule-is-not-the-same-as-the-edit-right)
- [Materialization: where the boundary falls](#materialization-where-the-boundary-falls)
- [The read path](#the-read-path)
  - [Queries](#queries)
  - [Freshness](#freshness)
- [Real-world examples](#real-world-examples)
- [References](#references)

## One function, one relation

Abstractly, every authorization system evaluates a function of the form[^authzen-shape]:

```text
f(subject, action, resource, context) → allow | deny
```

where:
- **Subject** is who is asking
- **Action** is what they want to do
- **Resource** is what they want it done to
- **Context** is everything else that bears on the answer and belongs to none of the first three: time of day, device information, network location, risk score, whether the country is at war, etc.

Tabulate `f` over subjects and resources and you get a relation. Lampson's access-control matrix has subjects down one axis, objects across the other, and permitted operations in the cells:

```text
             File A    File B    Device C
Alice          rw        r
Bob                      rw        use
```

Read as a table, the matrix is `Allowed(subject, action, resource)`, and every access check is a point query against it: is this row present? Context is the odd one out. It is a parameter of the query, not a column of the table, and nothing stores it.

Seen as a data system, then, `f` is a query. Writers change facts and rules on the write path, checks ask `f` on the read path, and the two paths meet at the view the rules define:

![The Decide column as a data system: writers, facts and rules on the write path, queries and the evaluator on the read path, meeting at the view; materialization decides where the boundary falls; carriers and enforcement extend beyond one database](/assets/authorization/decide-column.svg)

The rest of this article walks the figure. The write path comes first: what the facts look like, how rules turn them into the view, and who may write either. Then the boundary between the paths, which decides how much of the view is computed ahead of time. Then the read path: which questions the view can answer, and how fresh the answers are. The bottom row leaves the database. Enforcement is [Part 2](/programming/authority-enforcement.html), and carriers are [Part 3](/programming/carriers.html).

## The write path

### Facts: schemas for the matrix

The facts are what the store holds, and each model is a different schema for them.

![Data models](/assets/authorization/data-models.svg)

Six ways to write down the same `f`, on one running example. The first five are notations for the rectangle; the last is a different matrix. Going down from ACL to ReBAC, each step stores less and computes more at request time. That is a separate axis from the schema, and [materialization](#materialization-where-the-boundary-falls) takes it up below.

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

#### Access control lists and capability lists

The matrix is mostly empty, so nobody stores it. Real systems store one of its two projections.

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

The same information, transposed. This is the observation that makes people say ACLs and capabilities are dual, and at this level they are. A file descriptor is a capability; `/etc/passwd`'s mode bits are an ACL; both describe cells of the same matrix. In database terms, they are one table stored under two different keys, and the key decides which questions are cheap to ask. The [read path](#queries) comes back to that.

Hold the duality loosely. The matrix describes permissions at an instant. It says nothing about how a cell got filled in, who is allowed to fill in another one, or what happens when Alice hands Bob something. The [capabilities article](/programming/capabilities.html) is mostly about dismantling the duality this suggests. This one stays with the snapshot and asks the one dynamic question the matrix can almost answer: who edits it?

#### RBAC

RBAC inserts a reusable layer *between* subject and permission, so that `Users × Permissions` factors into `(Users × Roles)` and `(Roles × Permissions)`. The saving comes from sharing the middle term across many subjects, not from changing which end of the matrix the data hangs off.

In database terms, RBAC is normalization. It stores two tables, `UserRole` and `RolePermission`, and the matrix is their join. Role explosion is the sign that the schema no longer fits the data.

#### ABAC

ABAC is where the industry landed for anything complicated, with XACML and OPA's Rego as the two main expressions. Both share a shape: a policy document, a set of facts about subject and resource and environment, and an engine that evaluates one against the other at request time.

A table indexed by subject and resource has two axes. Action fits in the cell. Context fits nowhere. There is no coordinate for "between 9 and 5," or "from a managed device," or "while the incident is open." You can fake it by multiplying out subjects — a `finance-daytime` role — but that is role explosion arriving on schedule.

This is the real reason ABAC and its risk-adaptive variants exist. Not because subjects needed richer description, but because `f` grew a fourth argument and the table had no axis for it. Once you are evaluating a predicate at request time, context is free.

#### ReBAC

ReBAC stores the facts as a graph. Each fact is a tuple that names an object, a relation and a subject, and the subject can itself be a set, such as the members of a group. The running example has four:

```text
folder:Projects#owner@Alice
file:A#parent@folder:Projects
group:ops#member@Bob
device:C#use@group:ops
```

None of those tuples says that Alice may write File A. A rule does: the owner of a folder may write what the folder contains. [Zanzibar][zanzibar-google-s-consistent] calls these rules *userset rewrites*, and they are recursive, because groups hold groups and folders hold folders. A check is a reachability query: is there a path from the subject to the resource along relations the rules allow?

Of the five, ReBAC is the only model whose facts need a different data model. ACLs and capability lists are lists, RBAC is two tables, and ABAC is attributes on records. ReBAC is a graph, and its checks are graph queries.

### Rules: a policy is a view

Every model so far has two kinds of state. *Facts* are stored: ACL entries, role assignments, tuples, attributes. *Rules* derive the matrix from them: the join in RBAC, the rewrites in ReBAC, the predicate in ABAC. Datalog draws the same line, between stored facts and the rules that derive new ones, and so does SQL, between tables and views. A policy is a view definition. It says which rows of `Allowed` exist, given the facts.

Here is the ABAC rule from the figure above, in Rego, the language of OPA:

```rego
package files

default allow := false

allow if {
  input.action == "write"
  data.users[input.subject].dept == data.files[input.resource].dept
  input.context.device == "managed"
  input.context.hour >= 9
  input.context.hour < 17
}
```

And here are the first two lines of its body, as a SQL view over the same facts:

```sql
CREATE VIEW allowed AS
  SELECT u.id AS subject, 'write' AS action, f.id AS resource
  FROM users u JOIN files f ON u.dept = f.dept;
```

The pieces line up. `data` holds the stored facts, and comparing `data.users[...]` with `data.files[...]` is the join. `input` is the query, so the check becomes a point query against the view:

```sql
SELECT EXISTS (
  SELECT 1 FROM allowed
  WHERE subject = 'Alice' AND action = 'write' AND resource = 'A'
);
```

A second `allow` rule would be a second branch of a `UNION`. Rego gets this shape from Datalog, which [inspired it][opa-policy-language].

The last three lines of the rule have no SQL counterpart, and that is the ABAC argument again. A view is a table computed from other tables, and a table has no axis for context. The honest SQL translation is a function that takes the context as an argument.

[IDPro's taxonomy][authorization-terminology-mess] lists four policy formats: hardcoded code, a structured document, a declarative language, a database row. They are four ways to write the same view definition, or to skip it:

- **Code.** The rule is an `if` in the application. It is imperative, and changing it takes a deploy.
- **A structured document.** The rule is encoded as data, as in an AWS IAM policy's JSON. It can change without a deploy, and like any encoding it has to evolve without breaking what reads it.
- **A declarative language.** Rego, Cedar, XACML. The rule says what must hold, and the engine works out how to check it, as a database does for SQL.
- **A database row.** No rule at all. The rows of `Allowed` are stored directly, and that is an ACL.

Postgres has the closest real example, and it even uses the word:

```sql
ALTER TABLE files ENABLE ROW LEVEL SECURITY;
CREATE POLICY owner_only ON files USING (owner = current_user);
```

From then on, [Postgres adds][postgres-row-security] the `USING` predicate to every query on `files`, for every role that row-level security applies to. The policy is a view the database applies for you. Here the decision and its enforcement are one act, which is rare, and [Part 2](/programming/authority-enforcement.html) is about everywhere else.

### Writers

Facts and rules say what `f` is. There is a second question underneath it that gets far less attention and turns out to matter more: **who is allowed to change `f`, and where do they go to do it?** A policy that cannot be widened without a deploy is a policy that gets widened to `*` in advance. The cost of granting a legitimate exception is a security property, not an ergonomics complaint, and it is the one that decides whether the system is still enforcing anything six months later.

Karp puts his finger on why it gets neglected. Writing about the earliest identity-based systems:

> IBAC stores permissions in an access matrix, and the IBAC model doesn't include a specification of permissions for changing its entries. That left it to a trusted party, the system administrator.

The matrix has no theory of its own mutation. Every model since is an answer to that gap, and the answers differ from each other far more than the evaluation schemes do. They are all answers about writes, because granting access is a write. The line between facts and rules blurs here. A Linux ACL entry is a rule and a fact at once: it says who may do what, and it is stored on the file like any other attribute. In ReBAC the schema is policy and the relationship tuples are data, yet writing a tuple is how you grant access. So each model's answer is an answer to who may make that write:

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

There is a sharper way to see the split. Ask whether the mutation right is **monotone**. Delegation can only ever hand on less than the holder has, so authority shrinks along every edge. Administrative rights do the opposite: they manufacture authority the grantor does not hold, which is what makes "admin" a different power rather than a larger one. Two very different things wear the same word, and Part 4 depends on keeping them apart.

There is a second question hiding in the same list: *where do you go* to make the change. To give Bob everything Alice has under an ACL, you visit every object. Under a capability list you go to Alice. That is a real operational difference and it is invisible in the evaluation view.

One more thing about writes, before leaning on the matrix too hard. Once cells can be edited, the question you most want to ask — *can this permission ever reach that subject, by any sequence of legal edits* — is undecidable in the general case. Harrison, Ruzzo and Ullman proved it in 1976, and the result is why every tractable model since is a deliberate restriction of the general protection system rather than an implementation of it: take-grant, typed matrices, and the bounded schemes real engines actually ship. Keep it in view for the [capabilities article](/programming/capabilities.html), where the same question comes back as the thing capabilities are worst at.

#### DAC and MAC are not rungs

The clean ladder oversimplifies, and the first two entries are where it does the most damage.

DAC and MAC are usually presented as the first two levels of increasing sophistication in describing a subject. They are not. Neither says anything about how the matrix is indexed. The **D** in discretionary means *the owner may change the matrix at their discretion*. The **M** in mandatory means *the owner may not* — a lattice constrains every edit, including the administrator's. Both are answers to the mutation question and nothing else.

Once you see that, an old confusion goes away. SELinux's type enforcement is a *compression* choice: a security context is the full `user:role:type:level` tuple, and access is decided between types rather than users. MAC is a *mutation* choice. They are complements in that design, which is exactly what you would expect from two answers to two different questions, and not at all what you would expect from two rungs of one ladder.

#### Policies compose, and the rule is not the same as the edit right

One more thing hides in the mutation column, and the MAC row is where it shows.

I wrote that under MAC nobody may change a cell beyond what the lattice permits. That describes the effect and not the mechanism. What is actually happening is that `f` is computed from two policies with two different authors, combined with a conjunction:

```text
f = mandatory ∧ discretionary
```

The owner may still edit the discretionary half freely. They simply cannot relax the other half, because the combining rule is an `and`. Mandatory versus discretionary is a statement about *composition*, not about edit rights.

Once you look for it, composition is everywhere and rarely specified. XACML names its combining algorithms explicitly — deny-overrides, permit-overrides, first-applicable — which is more than most systems do. Real deployments stack an organizational policy, a team policy, a resource owner's settings and a per-request grant, and the rule for combining them is usually whatever the code happens to do.

Part 5 runs into this directly. An agent's effective authority is the conjunction of an org policy, the user's grant, the repository's branch protection and the tool's own rules — four policies, four owners, and no agreed account of how they combine.

## Materialization: where the boundary falls

The view in the figure can be stored in full, stored in part, or computed on every check. Kleppmann calls this the boundary between the write path and the read path. Work on the write path is paid when facts change. Work on the read path is paid when someone asks. Moving the boundary moves the cost, not the answer.

Each model sits somewhere along that line:

- **ACL.** The rows are the view. A check is a lookup. A change that spans many rows, such as "give Bob everything Alice has," is many writes.
- **RBAC.** The two tables are stored, and the join runs at check time. Many systems store the joined result too. Windows expands a user's groups into the access token at logon, which is why a group change waits for the next logon.
- **Zanzibar.** The tuples are stored, and the rewrites run at check time, except for nested groups. Its Leopard index precomputes group membership and keeps it current from the stream of tuple changes, because walking deeply nested groups on every check is slow.
- **ABAC.** Only the attributes are stored. The predicate runs on every check.

The two ends fail in opposite ways. Precompute, and checks are cheap, but every change has to reach every row derived from it, and a row that misses the change is a stale grant. Compute on read, and a change is one write, but every check pays for the derivation and depends on whoever holds the facts.

The data-models figure reads as if the model fixed where the boundary sits. It doesn't. ABAC decisions can be cached, and RBAC can be expanded ahead of time. The schema says what the facts look like. Materialization says when the view is computed, and any schema can move along it.

A materialized view does not have to stay in the store, either. The Windows access token is RBAC, joined at logon and carried by every process the user starts. Once the copy leaves the store, revoking it means reaching the copy. That is the subject of [Part 3](/programming/carriers.html).

## The read path

### Queries

The check is one query: is this row in `Allowed`? Every model answers it. Two more queries matter as much in practice: *what can Alice reach?* and *who can reach File A?* Review, audit and revocation all ask them.

Which of them is cheap depends on the key the facts are stored under. An ACL answers *who can reach File A* with one read, and *what can Alice reach* only by visiting every object. A capability list is the reverse. It is the same asymmetry the Writers section found for edits, now on the read side.

RBAC answers both through its join. ReBAC answers the check by walking the graph, and needs a reverse index for the rest: SpiceDB's `LookupResources` and OpenFGA's `ListObjects` exist for that. ABAC is the hard case. The predicate has to be tried against every resource, unless the engine can turn it into a filter the database runs. OPA's partial evaluation does exactly that: it compiles the policy into query conditions, which turns the policy back into what the Rules section said it was, a view.

[Part 3](/programming/carriers.html) leans on these queries. They are the questions a central store can answer and a capability cannot.

### Freshness

A lookup is not automatically current. The store that answers a check is usually a replica, and a replica can lag behind the write that revoked access.

Zanzibar's paper calls the result the *new enemy problem*. Alice removes Bob from a document's ACL, and then new content is added to the document. If the check on that content reads a replica that has not yet seen the removal, Bob sees content written after he lost access. Zanzibar's fix is the *zookie*. When content changes, the client asks Zanzibar for a zookie and stores it with the content. Later checks on that content pass the zookie, and Zanzibar evaluates them at a snapshot at least as fresh as the one it names. In Kleppmann's terms, that is causal consistency: a check may not see a world older than the write it depends on.

Freshness is a guarantee you ask for, not a property of looking things up. It also qualifies [Part 3](/programming/carriers.html#fresh-or-frozen)'s trade between a fresh lookup and a frozen copy: the lookup is only as fresh as the replica it reads.

Where the evaluator runs — inside the application, as a library, or as a service — is the last choice on the read path. It mostly decides latency and what fails when the evaluator is down. [Part 5](/programming/llm-sandbox.html) deals with it for a PDP in the path of every effect.

## Real-world examples

A system is not one model. It makes a choice on each axis of the figure:

| system | facts | rules | materialization | writers |
| --- | --- | --- | --- | --- |
| POSIX mode bits, NT ACLs | entries on the object | none | stored | the owner |
| Postgres `GRANT`, row-level security | an ACL per object in the catalog; predicates on tables | none for `GRANT`; a predicate per row for RLS | `GRANT` stored; RLS computed per query | the owner, and holders of `GRANT OPTION` |
| S3 bucket policies, AWS IAM condition keys | policy documents; tags on principals and resources | JSON predicates | computed per request | whoever may edit the policy |
| Linux file descriptors, `CAP_*` bounding sets | a table per process | none | stored in the process | the kernel, at `open()` or `exec()` |
| LDAP / Active Directory groups, Kubernetes RBAC, GitHub org roles | memberships and role bindings | a join | per check; AD also expands groups into the logon token | admins, plus whoever holds role-grant rights |
| SELinux type enforcement | labels on processes and objects | type rules, loaded as one policy | computed; decisions cached in the access vector cache | the policy author only (MAC) |
| XACML / Axiomatics, OPA / Rego | attributes, from anywhere | predicates | computed per request | whoever owns the policy |
| Zanzibar, Ory Keto | relation tuples | recursive rewrites | per check; Leopard precomputes nested groups | client services, through writes |
| SpiceDB, OpenFGA | tuples with caveats or conditions | rewrites, plus predicates on edges | per check, with caches | client services, through writes |
| Cedar / AWS Verified Permissions, Oso, Aserto Topaz | entities, relationships and attributes | one language for ReBAC and ABAC | computed per request | policy authors |
| KeyKOS, EROS, seL4, Fuchsia, Cap'n Proto, WASI Preview 2 | references held by each process | none | stored as the references themselves | the holder |

The last row is a different matrix, and [Part 4](/programming/capabilities.html) is about it.

Everything in this article decides at the resource. The PDP looks up what was written and computes `f`. The [next article](/programming/authority-enforcement.html) asks what makes that answer bind on the system where the effect happens. [Part 3](/programming/carriers.html) then asks what changes when the request brings a copy of the decision with it.

## References

1. [The State of the Union of Authorization][state-union-authorization] — the landscape diagram
2. [Protection][protection] — Lampson, 1974; the access matrix
3. [From ABAC to ZBAC: The Evolution of Access Control Models][from-abac-zbac-evolution] — Karp, Haury, Davis; the observation that the matrix has no theory of its own mutation
4. [Type Enforcement][type-enforcement] — why the MAC/RBAC relationship is not a simple ladder
5. [The Ultimate Guide to Choosing the Right Authorization Language][ultimate-guide-choosing-right] — XACML versus Rego
6. [Zanzibar: Google's Consistent, Global Authorization System][zanzibar-google-s-consistent] — relationship-based authorization, the Leopard index, and zookies against the new enemy problem
7. [AuthZEN][authzen] — standardizing the decision-point interface; its [information model][authzen-spec] is where the subject/action/resource/context request is defined
8. [Designing Data-Intensive Applications][ddia] — Kleppmann; facts and derived views, and the boundary between the write path and the read path
9. [OPA policy language][opa-policy-language] — Rego and its Datalog lineage
10. [Postgres row security policies][postgres-row-security] — `CREATE POLICY`, a view the database applies to every query

[authorization-terminology-mess]: https://idpro.org/authorization-terminology-is-a-mess-lets-fix-it/ "Authorization Terminology Is a Mess. Let's Fix It."
[authzen]: https://openid.net/wg/authzen/ "AuthZEN - OpenID Foundation working group"
[authzen-spec]: https://openid.net/specs/authorization-api-1_0.html#name-information-model "Authorization API 1.0: information model - OpenID Foundation"
[ddia]: https://dataintensive.net/ "Designing Data-Intensive Applications"
[from-abac-zbac-evolution]: https://shiftleft.com/mirrors/www.hpl.hp.com/techreports/2009/HPL-2009-30.pdf "From ABAC to ZBAC: The Evolution of Access Control Models"
[opa-policy-language]: https://www.openpolicyagent.org/docs/latest/policy-language/ "Policy Language - Open Policy Agent"
[postgres-row-security]: https://www.postgresql.org/docs/current/ddl-rowsecurity.html "PostgreSQL: Row Security Policies"
[protection]: https://www.microsoft.com/en-us/research/publication/protection/ "Protection"
[rfc4949]: https://datatracker.ietf.org/doc/html/rfc4949 "RFC 4949: Internet Security Glossary, Version 2"
[state-union-authorization]: https://idpro.org/the-state-of-the-union-of-authorization/ "The State of the Union of Authorization"
[type-enforcement]: https://en.wikipedia.org/wiki/Type_enforcement "Type Enforcement"
[ultimate-guide-choosing-right]: https://axiomatics.com/wp-content/uploads/2024/10/the-ultimate-guide-to-choosing-the-right-authorization-language-whitepaper-axiomatics-10-16-2024.pdf "The Ultimate Guide to Choosing the Right Authorization Language"
[zanzibar-google-s-consistent]: https://research.google/pubs/pub48190/ "Zanzibar: Google's Consistent, Global Authorization System"

## Footnotes <!-- omit in toc -->

[^authzen-shape]: This signature doesn't generalize all authorization models by coincidence; it is also the signature that the industry converged on and is in the process of standardizing via [AuthZEN][authzen], the OpenID Foundation's decision-point protocol. It deliberately says nothing about how the answer is reached. It standardizes only the shape of the question, which is a strong signal that the shape is the settled part.

[^access-profile]: [RFC 4949][rfc4949], the Internet Security Glossary, has a name for this row that keeps it away from the word capability: defining the access control matrix, it says "each row is equivalent to an *access profile* for the subject." The glossary does not actually recommend the term — `access profile` is marked "O", meaning non-Internet origin and not for use in Internet documents, and its entry reads only "synonym for capability list." `capability list` is the entry it recommends. The distinction RFC 4949 does draw is the one worth holding on to: a *capability list* enumerates what a subject may reach, while a *capability token* is an unforgeable object whose possession is itself the proof. Part 4 lives in the gap between those two. I keep "capability list" here, which also matches the Linux sense of the word — `CAP_NET_ADMIN` and friends are a per-process list of permitted operations, a row and not a token.
