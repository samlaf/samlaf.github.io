---
title:  "Authorization is a database problem"
series: "Authorization, Part 1"
series_url: "/programming/authorization-series-intro.html"
category: programming
date:   2026-09-01
---

> This is Part 1 of a four-part [series on authorization](/programming/authorization-series-intro.html).
>
> - **Part 1: Authorization is a database problem** — what every system computes, and who may change it.
> - **[Part 2: How authority is enforced](/programming/authority-enforcement.html)** — what makes any of it binding.
> - **[Part 3: Carriers](/programming/carriers.html)** — decisions that travel with the request.
> - **[Part 4: Capabilities](/programming/capabilities.html)** — authority you hold, not authority you are.

- [The write path](#the-write-path)
  - [Facts: schemas for the matrix](#facts-schemas-for-the-matrix)
    - [Access control lists and capability lists](#access-control-lists-and-capability-lists)
    - [RBAC](#rbac)
    - [ReBAC](#rebac)
    - [ABAC](#abac)
  - [Rules: a policy is a view](#rules-a-policy-is-a-view)
  - [Writers](#writers)
- [Materialization: where the boundary falls](#materialization-where-the-boundary-falls)
- [The read path](#the-read-path)
  - [Queries](#queries)
  - [Freshness](#freshness)
- [Stateful checks](#stateful-checks)
- [Real-world examples](#real-world-examples)
- [References](#references)

Abstractly, every authorization system evaluates a function of the form[^authzen-shape]:

```text
f(subject, action, resource, context) → allow | deny
```

where:
- **Subject** is who is asking
- **Action** is what they want to do
- **Resource** is what they want it done to
- **Context** is everything else that bears on the answer and belongs to none of the first three: time of day, device information, network location, risk score, whether the country is at war, etc.

Any real system needs to instantiate f, and the clearest way to understand the distinction between the various authorization models is to see them from a database perspective. Writers change facts and rules on the write path, whereas checks query `f` on the read path, and the two paths meet at the view the rules define[^planes]:

![The Decide column as a data system: writers, facts and rules on the write path, queries and the evaluator on the read path, meeting at the view, whose cells can hold conditions on the request's context; materialization decides where the boundary falls](/assets/authorization/decide-column.svg)

The rest of this article walks the figure. The write path comes first: what the facts look like, how rules turn them into the view, and who may write either. Then the boundary between the paths, which decides how much of the view is computed ahead of time. Finally the read path: which questions the view can answer, and how fresh the answers are. What lies beyond one database comes later in the series.

## The write path

### Facts: schemas for the matrix

The facts are what the store holds, and each model is a different schema for them. The table writes down the same `f` six ways, on one running example: Alice and Bob, two files and a device. The first five are notations for the rectangle; the last is [a different matrix](/programming/capabilities.html#squaring-the-matrix). Going down from ACL to ABAC, each step stores less and computes more at request time. That is a separate axis from the schema, and [materialization](#materialization-where-the-boundary-falls) takes it up below.

| model | how `f` is represented | subject | resource | context |
| --- | --- | --- | --- | --- |
| **ACL** | stored, indexed by resource | enumerated identity | one list per object | none |
| **capability list** | stored, indexed by subject | enumerated identity | one list per subject | none |
| **RBAC** | factored: subject → role → permission | coarsened into roles, the shared middle term | enumerated per role | none; faking it explodes the role set |
| **ReBAC** | derived from a graph of tuples | graph node, reached through groups | fine-grained through hierarchy, without enumeration | none in Zanzibar; per-edge caveats in SpiceDB and OpenFGA |
| **ABAC** | not stored; a predicate evaluated per request | attributes, open-ended | attributes | first-class, the axis a table does not have |
| **object capability** | held as references, over a square matrix | any entity | any entity — subjects and resources are one set | n/a: authority is held, not decided per request |

#### Access control lists and capability lists

The matrix is mostly empty, so nobody stores it. Real systems store one of its two projections. Store it by column, at the resource, and you get an **access control list**. Store it by row, at the subject, and you get a **capability list**[^access-profile]:

![The access-control matrix for Alice and Bob, stored by column as an access control list and by row as a capability list](/assets/authorization/facts-acl.svg)

The same information, transposed. This is the observation that makes people say ACLs and capabilities are dual, and at this level they are. A file descriptor is a capability; `/etc/passwd`'s mode bits are an ACL; both describe cells of the same matrix. In database terms, they are one table stored under two different keys, and the key decides which questions are cheap to ask. The [read path](#queries) comes back to that.

Hold the duality loosely. The matrix describes permissions at an instant. It says nothing about how a cell got filled in, who is allowed to fill in another one, or what happens when Alice hands Bob something. The [capabilities article](/programming/capabilities.html) is mostly about dismantling the duality this suggests. This one stays with the snapshot and asks the one dynamic question the matrix can almost answer: who edits it?

#### RBAC

RBAC inserts a reusable layer *between* subject and permission, so that `Users × Permissions` factors into `(Users × Roles)` and `(Roles × Permissions)`. The saving comes from sharing the middle term across many subjects, not from changing which end of the matrix the data hangs off.

![RBAC: Alice, Carol and Dan hold the editor role, which grants rw on File A and r on File B; Bob holds the operator role, which grants rw on File B and use on Device C](/assets/authorization/facts-rbac.svg)

In database terms, RBAC is normalization. It stores two tables, `UserRole` and `RolePermission`, and the matrix is their join. Role explosion is the sign that the schema no longer fits the data.

#### ReBAC

ReBAC stores the facts as a graph. Each fact is a tuple that names an object, a relation and a subject, and the subject can itself be a set, such as the members of a group. The running example has four:

![ReBAC: the four tuples, and the graph they form. Alice owns the Projects folder, which is the parent of File A. Bob is a member of ops, which may use Device C.](/assets/authorization/facts-rebac.svg)

None of those tuples says that Alice may write File A. A rule does: the owner of a folder may write what the folder contains. [Zanzibar][zanzibar-google-s-consistent] calls these rules *userset rewrites*, and they are recursive, because groups hold groups and folders hold folders. A check is a reachability query: is there a path from the subject to the resource along relations the rules allow?

#### ABAC

ABAC is where the industry landed for anything complicated, with XACML and OPA's Rego as the two main expressions. Both share a shape: a policy document, a set of facts about subject and resource and environment, and an engine that evaluates one against the other at request time.

![ABAC: the request's subject, resource, action and context feed a predicate that permits a write when the departments match, during working hours, from a managed device](/assets/authorization/facts-abac.svg)

A table indexed by subject and resource has two axes. Action fits in the cell. Context fits nowhere. There is no coordinate for "between 9 and 5," or "from a managed device," or "while the incident is open." You can fake it by multiplying out subjects — a `finance-daytime` role — but that is role explosion arriving on schedule.

This is the real reason ABAC and its risk-adaptive variants exist. Not because subjects needed richer description, but because `f` grew a fourth argument and the table had no axis for it. Once you are evaluating a predicate at request time, context is free.

ReBAC has since borrowed this. Zanzibar's tuples carry no context. SpiceDB and OpenFGA let a tuple carry a condition: SpiceDB calls it a *caveat*, and OpenFGA a *condition*. Bob may use Device C, but only from the office network. The tuple can fix some of the condition's parameters when it is written, such as the office's address range. The check supplies the rest, such as the caller's IP. If the check leaves one out, SpiceDB does not guess. It answers *conditional* and names the missing fields. The store holds a condition on the context, and the context still comes with the request.

Of the five, ReBAC is the only model whose facts need a different data model. ACLs and capability lists are lists, RBAC is two tables, and ABAC is attributes on records. ReBAC is a graph, and its checks are graph queries.

### Rules: a policy is a view

Every model so far has two kinds of state. *Facts* are stored: ACL entries, role assignments, tuples, attributes. *Rules* derive the matrix from them: the join in RBAC, the rewrites in ReBAC, the predicate in ABAC. Datalog draws the same line, between stored facts and the rules that derive new ones, and so does SQL, between tables and views. A policy is a view definition. It says which rows of `Allowed` exist, given the facts.

Here is the rule from the ABAC figure, in Rego, the language of OPA:

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

Facts and rules say what `f` is. A separate question is who may change it. Granting access is a write, so the question is who may make that write, and the schemas above say nothing about it. There are four common answers:

```text
DAC                   the owner
MAC                   a security officer; owners cannot override
administrative roles  admins, scoped by the admin roles they hold
object capability     the holder, passing on at most what it holds
```

Any schema can pair with any of these. RBAC says nothing about who assigns roles. [ARBAC97][arbac97] answered that separately, with administrative roles that govern the others: RBAC applied to its own writes. And [Osborn, Sandhu and Munawer][rbac-dac-mac] showed that RBAC can be configured to enforce DAC or MAC. So DAC and MAC are not the first rungs of a ladder that climbs to RBAC and ABAC. They answer a different question.

The answers split on one property: whether a grant can create authority. A capability holder passes on at most what it holds, so authority shrinks along every edge. An administrator grants authority they do not hold themselves. Part 4 depends on keeping the two apart.

Once cells can be edited, the question you most want to ask is whether a permission can ever reach a subject, through any sequence of legal edits. Harrison, Ruzzo and Ullman proved in 1976 that this is undecidable in general. That is why every practical model restricts which edits are legal: take-grant, typed matrices, and the bounded schemes real engines ship. The [capabilities article](/programming/capabilities.html) comes back to this question, because it is the one capabilities answer worst.

## Materialization: where the boundary falls

The view, `Allowed`, can be stored in full, stored in part, or computed on every check. That choice sets where the write path ends and the read path begins. It moves the cost, never the answer. The two ends fail in opposite ways:

- **Precompute on write.** A check is a lookup. But every change has to reach every row derived from it, and a row that misses the change is a stale grant.
- **Compute on read.** A change is one write. But every check pays for the derivation, and depends on whoever holds the facts.

Three things decide where a real system lands:

- **The schema does not fix it.** The Facts sections ran along this line, from ACL to ABAC, but any schema's view can be stored, and how it is stored decides how a change reaches it:
  - *Maintained.* Updated on every write. Zanzibar's Leopard index keeps nested group membership current as tuples change, because walking deep groups on every check is slow.
  - *Snapshot.* Computed once and kept. Windows expands a user's groups into an access token at logon, so a group change waits for the next logon.
  - *Cache.* Computed on the first check and kept until it expires. Even an ABAC decision can be cached this way, and a change then waits out the expiry.
- **Context caps it.** A cell that depends on context cannot be stored as allow or deny, because the context arrives with the request. What can be stored is the condition left once the facts are filled in. OPA's partial evaluation produces exactly that, and SpiceDB's `LookupResources` marks such results as conditional.
- **A stored view can leave the store.** The Windows token is a snapshot that rides with every process the user starts. Revoking access then means reaching every copy. That is the subject of [Part 3](/programming/carriers.html).

## The read path

### Queries

The check is one query: is this row in `Allowed`? Every model answers it. Two more queries matter as much in practice: *what can Alice reach?* and *who can reach File A?* Review, audit and revocation all ask them.

Which of them is cheap depends on the key the facts are stored under. An ACL answers *who can reach File A* with one read, and *what can Alice reach* only by visiting every object. A capability list is the reverse. It is the same asymmetry the Writers section found for edits, now on the read side.

RBAC answers both through its join. ReBAC answers the check by walking the graph, and needs a reverse index for the rest: SpiceDB's `LookupResources` and OpenFGA's `ListObjects` exist for that. ABAC is the hard case. The predicate has to be tried against every resource, unless the engine can turn it into a filter the database runs. OPA's partial evaluation does exactly that: it compiles the policy into query conditions, which turns the policy back into what the Rules section said it was, a view.

[Part 3](/programming/carriers.html) leans on these queries. They are the questions a central store can answer and a capability cannot.

### Freshness

A lookup is not automatically current. The store that answers a check is usually a replica, and a replica can lag behind the write that revoked access.

Zanzibar's paper calls the result the *new enemy problem*. Alice removes Bob from a document's ACL, and then new content is added to the document. If the check on that content reads a replica that has not yet seen the removal, Bob sees content written after he lost access. Zanzibar's fix is the *zookie*. When content changes, the client asks Zanzibar for a zookie and stores it with the content. Later checks on that content pass the zookie, and Zanzibar evaluates them at a snapshot at least as fresh as the one it names. Databases call this guarantee *causal consistency*: a check may not see a world older than the write it depends on.

Freshness is a guarantee you ask for, not a property of looking things up. It also qualifies [Part 3](/programming/carriers.html#fresh-or-frozen)'s trade between a fresh lookup and a frozen copy: the lookup is only as fresh as the replica it reads.

Where the evaluator runs — inside the application, as a library, or as a service — is the last choice on the read path. It mostly decides latency and what fails when the evaluator is down.

## Stateful checks

Everything so far keeps the two paths apart. Writers change facts and rules, and a check only reads them. Asking `f` never changes the next answer.

Some policies need it to. The oldest is the [Chinese Wall][brewer-nash] of Brewer and Nash, from 1989, written for consultants who serve competing clients. Files are grouped by company, and companies by conflict of interest. Alice may read any bank's files until she reads one. From then on, every other bank's files are denied. The matrix changed, and no administrator wrote the change. The check did. A stateful firewall works the same way: packets write its connection table, not an administrator. The family has a name, *history-based access control*, from [Edjlali, Acharya and Chaudhary][history-based-access-control]'s 1998 work on mobile code. [Usage control][ucon-abc] made it a property of the model in 2004 and called it *mutability*: using an object can update the attributes the next decision reads.

In database terms, the check now writes. The store gains a new table: an append-only log of what the enforcer saw, one row per request. Monitoring theory calls this log a *trace*, and policies that read it *trace-based*. The check returns the row it appends along with its answer, and the next check reads the log:

```text
stateless:  f(subject, action, resource, context) → decision
stateful:   f(subject, action, resource, context) → (decision, update)
```

The first line is the special case where nothing is appended. [Schneider][enforceable-security-policies] gave the general case its theory in 2000. A monitor that watches each step of a program and can stop it is a *security automaton*. Its input is the trace, and the policies it can enforce are *safety properties* of the execution: a bad thing never happens. An ACL is an automaton with one state.

AI agents made this mainstream, because one tool call rarely says what an agent is doing. The attacker who [splits one intent across several requests](/programming/authority-enforcement.html#who-is-the-attacker) defeats any check that judges one request at a time. Once the log exists, the rest is ordinary database work:

- **Policies are temporal queries over the log.** [Dogwood][dogwood] adds temporal operators to Cedar: `formerly within 1h`, `count_within`, `sum_within`. "Sell shares only if an approval for these shares came back in the last hour" is a query over the log, run at check time. The operators come from [metric first-order temporal logic][mfotl], the specification language of runtime monitoring.
- **Time is `now()`.** `within 1h` is `WHERE ts > now() - 1h`, and an expiring grant is `WHERE expires_at > now()`. So the clock can move the answer with no write at all: same log, same request, a new answer. [TRBAC][trbac] did this for RBAC in 2000, with roles that turn on and off on a schedule. `now()` has to come from the enforcer's own clock, never from an hour the caller reports.
- **Query the log, or maintain a view of it.** This is the [materialization](#materialization-where-the-boundary-falls) trade again. Dogwood keeps the raw log and queries it per check, so a rule added next week applies to everything already recorded. [Omnigent][omnigent] folds each event into state as it arrives: a policy is a handler that takes "the old state and the new event" and returns a new state and a decision. That is Schneider's automaton, written as code. Checks are cheap, but you have to decide in advance what to remember.
- **The view definition can change per task.** [Conseca][conseca] has a model write a policy for each task from trusted input only. An action must pass both that policy and the standing ones.

The check is also a new writer, and the most trustworthy one in the system. The log records what the enforcer saw happen, not what anyone claims. That is why it is a table and not more context: context comes from the caller, and the caller cannot forge the log, as long as the enforcer runs outside its reach. A log kept in the agent's own harness falls with the harness: [Part 2](/programming/authority-enforcement.html#who-is-the-attacker)'s rung 2.

![The check written as f(subject, action, resource, context) → (decision, update), with an arrow from each part to the systems that make it move: per-task policy for f, information flow control for the request, temporal and attribute-based access control for context, and history-based access control for the update](/assets/authorization/contextual-policies.svg)

The lifetimes nest. A request sits inside a task, and a task inside a session. The policy changes per task, the log grows with each request, and the clock runs under all of them. One check reads a slice of each:

![A timeline with four lanes: the session's log grows by one row per request, the policy changes when a new task starts, requests arrive as ticks, and the clock runs underneath. One check reads the log so far, the current task's policy, its own request, and a one-hour window of the clock.](/assets/authorization/check-lifetimes.svg)

"Intent-based policy" is a name for what all of these try to approximate. Intent itself is not an input. No check can read it, and every system here guesses at it from what it can read.

Schneider's theory also marks where this stops. A trace monitor sees which calls happened. It does not see which value flowed into which argument. That is information flow, and it is not a property of a single trace. [Clarkson and Schneider][hyperproperties] call it a *hyperproperty*: a property of sets of traces, which no monitor watching one execution can check. A prompt injection can be a sequence of perfectly legal calls.

Distributed databases hit the same wall. Alice reads a match's final score from one replica and tells Bob. Bob's replica has not caught up, so when he looks, the match is still on. The database broke none of its rules. The dependency ran through a channel it never saw: Alice talking to Bob. Both fields answer in the same two ways. The first assumes every later operation may depend on every earlier one. Databases call this *linearizability*: the system acts as if there were one copy of the data, so nobody sees an older state than someone before them. Its security twin is [Biba][biba]'s *low-water mark*: once an agent reads untrusted text, everything it does next counts as untrusted. The second tracks only the real dependencies. Causal tokens like the [zookie](#freshness) do this, and so do fine-grained labels. They cost less, but they see only what flows through the system. An LLM is exactly such a hidden channel, inside your own system. Nothing records which input shaped which output.

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
| Dogwood, Omnigent | a log of the session's requests | temporal queries over the log | Dogwood keeps the log and queries it per check; Omnigent folds it into state per request | the enforcer, on every request |
| KeyKOS, EROS, seL4, Fuchsia, Cap'n Proto, WASI Preview 2 | references held by each process | none | stored as the references themselves | the holder |

The last row is a different matrix, and [Part 4](/programming/capabilities.html) is about it.

Everything in this article decides at the resource. The evaluator looks up what was written and computes `f`. The [next article](/programming/authority-enforcement.html) asks what makes that answer bind on the system where the effect happens. [Part 3](/programming/carriers.html) then asks what changes when the request brings a copy of the decision with it.

## References

1. [The State of the Union of Authorization][state-union-authorization] — the landscape diagram
2. [Protection][protection] — Lampson, 1974; the access matrix
3. [Type Enforcement][type-enforcement] — why the MAC/RBAC relationship is not a simple ladder
4. [The Ultimate Guide to Choosing the Right Authorization Language][ultimate-guide-choosing-right] — XACML versus Rego
5. [Zanzibar: Google's Consistent, Global Authorization System][zanzibar-google-s-consistent] — relationship-based authorization, the Leopard index, and zookies against the new enemy problem
6. [AuthZEN][authzen] — standardizing the decision-point interface; its [information model][authzen-spec] is where the subject/action/resource/context request is defined
7. [Designing Data-Intensive Applications][ddia] — Kleppmann; facts and derived views, and the boundary between the write path and the read path
8. [OPA policy language][opa-policy-language] — Rego and its Datalog lineage
9. [Postgres row security policies][postgres-row-security] — `CREATE POLICY`, a view the database applies to every query
10. [The Chinese Wall Security Policy][brewer-nash] — Brewer and Nash, 1989; access that depends on what you accessed before
11. [Enforceable Security Policies][enforceable-security-policies] — Schneider, 2000; security automata, and why a monitor enforces only safety properties
12. [Introducing Dogwood][dogwood] — Cedar with temporal operators over the log of tool calls
13. [Contextual policies in Omnigent][omnigent] — policies as handlers over session state
14. [Contextual Agent Security: A Policy for Every Purpose][conseca] — Tsai and Bagdasarian, HotOS 2025; a policy written per task
15. [History-based Access Control for Mobile Code][history-based-access-control] — Edjlali, Acharya, Chaudhary, CCS 1998; the name for the family
16. [The UCON<sub>ABC</sub> Usage Control Model][ucon-abc] — Park and Sandhu, 2004; mutable attributes, updated by use
17. [TRBAC: A Temporal Role-Based Access Control Model][trbac] — Bertino, Bonatti, Ferrari, 2000; roles enabled and disabled on a schedule
18. [Monitoring Metric First-Order Temporal Properties][mfotl] — Basin, Klaedtke, Müller, Zălinescu, JACM 2015; the logic under Dogwood's operators
19. [Hyperproperties][hyperproperties] — Clarkson and Schneider, 2010; why information flow is not a property of one trace
20. [Biba Model][biba] — Biba, 1977; integrity labels, and the low-water mark for subjects that read less-trusted data
21. [The ARBAC97 Model for Role-Based Administration of Roles][arbac97] — Sandhu, Bhamidipati, Munawer, TISSEC 1999; who may assign roles, answered with roles
22. [Configuring Role-Based Access Control to Enforce Mandatory and Discretionary Access Control Policies][rbac-dac-mac] — Osborn, Sandhu, Munawer, TISSEC 2000; RBAC as either DAC or MAC

[arbac97]: https://doi.org/10.1145/300830.300839 "The ARBAC97 model for role-based administration of roles"
[authorization-terminology-mess]: https://idpro.org/authorization-terminology-is-a-mess-lets-fix-it/ "Authorization Terminology Is a Mess. Let's Fix It."
[authzen-spec]: https://openid.net/specs/authorization-api-1_0.html#name-information-model "Authorization API 1.0: information model - OpenID Foundation"
[authzen]: https://openid.net/wg/authzen/ "AuthZEN - OpenID Foundation working group"
[biba]: https://en.wikipedia.org/wiki/Biba_Model "Biba Model"
[brewer-nash]: https://en.wikipedia.org/wiki/Brewer_and_Nash_model "Brewer and Nash model"
[conseca]: https://arxiv.org/abs/2501.17070 "Contextual Agent Security: A Policy for Every Purpose"
[ddia]: https://dataintensive.net/ "Designing Data-Intensive Applications"
[dogwood]: https://aws.amazon.com/blogs/opensource/introducing-dogwood-runtime-verification-for-ai-agents/ "Introducing Dogwood: runtime verification for AI agents"
[enforceable-security-policies]: https://dl.acm.org/doi/10.1145/353323.353382 "Enforceable Security Policies"
[history-based-access-control]: https://www.cse.buffalo.edu/cadi/papers/1998/1998_3.pdf "History-based Access Control for Mobile Code"
[hyperproperties]: https://content.iospress.com/articles/journal-of-computer-security/jcs393 "Hyperproperties"
[mfotl]: https://doi.org/10.1145/2699444 "Monitoring Metric First-Order Temporal Properties"
[omnigent]: https://www.databricks.com/blog/contextual-policies-omnigent-using-session-state-better-govern-ai-agents "Contextual policies in Omnigent: using session state to better govern AI agents"
[opa-policy-language]: https://www.openpolicyagent.org/docs/latest/policy-language/ "Policy Language - Open Policy Agent"
[postgres-row-security]: https://www.postgresql.org/docs/current/ddl-rowsecurity.html "PostgreSQL: Row Security Policies"
[protection]: https://www.microsoft.com/en-us/research/publication/protection/ "Protection"
[rbac-dac-mac]: https://doi.org/10.1145/354876.354878 "Configuring role-based access control to enforce mandatory and discretionary access control policies"
[rfc4949]: https://datatracker.ietf.org/doc/html/rfc4949 "RFC 4949: Internet Security Glossary, Version 2"
[state-union-authorization]: https://idpro.org/the-state-of-the-union-of-authorization/ "The State of the Union of Authorization"
[trbac]: https://www.cerias.purdue.edu/apps/reports_and_papers/view/3971 "TRBAC: A Temporal Role-Based Access Control Model"
[type-enforcement]: https://en.wikipedia.org/wiki/Type_enforcement "Type Enforcement"
[ucon-abc]: https://www.profsandhu.com/journals/tissec/ucon-abc.pdf "The UCON ABC Usage Control Model"
[ultimate-guide-choosing-right]: https://axiomatics.com/wp-content/uploads/2024/10/the-ultimate-guide-to-choosing-the-right-authorization-language-whitepaper-axiomatics-10-16-2024.pdf "The Ultimate Guide to Choosing the Right Authorization Language"
[zanzibar-google-s-consistent]: https://research.google/pubs/pub48190/ "Zanzibar: Google's Consistent, Global Authorization System"

## Footnotes <!-- omit in toc -->

[^authzen-shape]: This signature doesn't generalize all authorization models by coincidence; it is also the signature that the industry converged on and is in the process of standardizing via [AuthZEN][authzen], the OpenID Foundation's decision-point protocol. It deliberately says nothing about how the answer is reached. It standardizes only the shape of the question, which is a strong signal that the shape is the settled part.

[^planes]: Networking has names for these two paths: the write path is a control plane, and the read path a data plane. A router computes routes ahead of time and installs them in a forwarding table, so each packet costs one lookup. [Materialization](#materialization-where-the-boundary-falls) is the same choice.

[^access-profile]: [RFC 4949][rfc4949], the Internet Security Glossary, has a name for this row that keeps it away from the word capability: defining the access control matrix, it says "each row is equivalent to an *access profile* for the subject." The glossary does not actually recommend the term — `access profile` is marked "O", meaning non-Internet origin and not for use in Internet documents, and its entry reads only "synonym for capability list." `capability list` is the entry it recommends. The distinction RFC 4949 does draw is the one worth holding on to: a *capability list* enumerates what a subject may reach, while a *capability token* is an unforgeable object whose possession is itself the proof. Part 4 lives in the gap between those two. I keep "capability list" here, which also matches the Linux sense of the word — `CAP_NET_ADMIN` and friends are a per-process list of permitted operations, a row and not a token.
