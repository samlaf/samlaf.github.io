---
title:  "Authorization"
category: programming
date: 2026-08-31
---

Despite security and authorization having been parts of computer science and programming for decades, the field is still [evolving rapidly][state-union-authorization]:

![](/assets/authorization/auth-timeline.png)

While still being quite fragmented in practice, there is a growing understanding of the underlying principles that govern how authority is represented and managed, and we are starting to see a convergence on the fundamental abstractions that underlie all models. Furthermore, with LLMs and agents now being ubiquitous in software systems, there is a pressing need to understand and formalize how authorization decisions are made and enforced in these dynamic environments.

The goal of this series is to take a holistic view on the mechanisms underlying authorization:

1. **Deciding is a database problem.** Facts are stored, rules derive a view from them, and every check is a query against that view.
2. **Enforcing makes the answer bind.** Either something in the path judges the request, or the path is not there at all. Sandboxes use both.
3. **Carriers bring the answer to the enforcer.** A token is a copy of a decision that travels with the request, so the check does not have to go back to the database.
4. **Capabilities join the two ways of enforcing.** If the only names you hold are the ones you were given, what you can reach is what you may do.

## Deciding is a database problem

Many people present authorization in its very circumscribed functional form, as the decision that every system must compute for each request:

```text
f(subject, action, resource, context) → allow | deny
```

Indeed, all authorization models such as ACL, RBAC, ReBAC, and ABAC can be understood as different ways to represent and compute this function.

XACML first expanded this pure function into a system. This is how NIST draws it, in [SP 800-162][nist-sp-800-162]:

![PEP, PDP, PAP and PIP, with the policy repository, the attribute repository and environment conditions](/assets/authorization/nist-abac-functional-points.png)

XACML was specialized to ABAC systems, but [AuthZEN][authzen-api], the OpenID Foundation's Authorization API, recently generalized and standardized the PEP<>PDP interface to work with all authorization models.

The main point is that we can think of the PDP (Policy Decision Point) as a database system that answers the authorization query from above. From this perspective, we are able to bring to this problem 40+ years of database expertise that has been developed. An ACL stores the rows of `Allowed` directly. RBAC stores two tables and joins them. ReBAC stores a graph and walks it. ABAC stores attributes and evaluates a predicate over them. We expand on all of these with concrete examples in [Part 1](/programming/authorization-models.html).

## A database answer binds nothing

A database enforces its own answers. It never returns a row nobody selected. Postgres row-level security is the rare case where an authorization decision works the same way: the database adds the policy to every query on the table, so deciding and enforcing are one act.

Everywhere else, the decision is about an effect on another system: a file opened, a packet sent, a payment made. Something in the path of that effect has to apply the answer. That is the PEP. It is one kind of *reference monitor*, and Anderson gave every reference monitor three properties: always invoked, tamperproof and verifiable. The PDP has to be correct. The PEP has to be unavoidable.

The PEP also has to know who is asking. `f` takes a subject, and the database cannot pick one for itself. So every request carries something that ties it to a subject: a header, a signature, or the channel it arrived on. Checking that claim is authentication. It has its own column on the grid below, and the series on identity and applied cryptography cover it.

## Every stage can stop a request

Deciding is not the only place to stop a request. A request has to get to the decision first, and it passes two stages on the way. First a name has to resolve to an object: the kernel walks a path, DNS maps a host, a table maps a file descriptor to an open file. Call that **designate**. Then the request has to be carried to whatever serves the object: a syscall boundary, a route, an IPC endpoint. Call that **reach**.

Each stage is a function, and each one can come back empty:

```text
designate      resolve(namespace, name)   → object  | ⊥
reach          route(source, address)     → path    | ⊥
authenticate   verify(claim, proof)       → subject | ⊥
decide         f(s, a, r, ctx)            → allow   | deny
```

So there are two ways to stop a request, at any stage. Under **absence**, the lookup comes back empty and nothing is ever decided. Under **judgment**, the request arrives and a policy says no. Sandboxes use both:

- A `chroot` or a mount namespace changes what a path resolves to. The file the workload asks for is not there.
- A network namespace with no route removes reach. The name resolves, and the packet goes nowhere.
- A VM does both for the whole host. Host paths mean nothing inside the guest, and there is no device to reach the host through.
- Seccomp judges reach. The call is expressible, and a filter refuses it before the kernel ever looks at the object.

The first three are absences, and the last is a judgment. Most arguments about sandboxing are about which of the two is in use, and on which stage.

The two need each other. A PEP is unavoidable only if there is no other path around it, and whether there is depends on the shape of reach, not on any policy. An `HTTP_PROXY` setting is a request the workload can ignore. The same proxy becomes a real PEP once the network gives the workload no other route.

So each stage has its own reference monitor, and Anderson's properties apply to each one. [Part 2](/programming/authority-enforcement.html) covers them, from Linux namespaces to VMs to seL4.

## Carriers bring the answer to the enforcer

The PEP needs the decision, but the database may be far away. So the request brings something along. At the least, it brings who is asking. It can bring much more. The Windows logon token is RBAC, joined at logon and carried by every process the user starts. An OAuth access token carries a scoped decision on the web. Each one is a copy of something written, riding with the request so the check does not have to go back to the store. Call it a **carrier**.

The identity carrier is required. Every carrier beyond it is a cache, and it has the cost of one. Checks are fast, and they work without the store. But once the copy leaves, revoking it means reaching every copy. [Part 3](/programming/carriers.html) follows that trade.

## Capabilities: authority becomes reachability

Push the carrier far enough and it stops being a copy. A capability has nothing to look up: the subject arrives holding the authority. It needs no authentication either, because there is no subject to look up. An object capability goes further. The reference that names the object is also the route to it and the permission to use it, so designate, reach and decide become one act.

That is where the two ways of enforcing meet. Under object capabilities, every name a program holds was given to it, and everything it was not given is absent. The question "may Alice do this?" turns into "can Alice reach this?", which is a question about who holds references to what. That is not a faster way to consult the database. It is a different database, and the access matrix has to be [square](/programming/capabilities.html#squaring-the-matrix) to describe it. [Part 4](/programming/capabilities.html) makes that case.

## From a chain to a grid

The four boxes cover one stage of a request: the decision. NIST draws the whole path in a second figure, which it calls a *trust chain*:

![NIST SP 800-162, Figure 8: the ABAC trust chain](/assets/authorization/nist-abac-trust-chain.png)

Read it as a spine with bones. The spine runs left to right, and it is what happens during one request: the subject authenticates, a decision is made, and the decision is enforced on the way to the object. The bones are what each stage rests on, and someone wrote almost all of them earlier: a credential issued, an identity provisioned, an attribute assigned, a rule managed. The effect at the end is only as trustworthy as every bone behind it. That is why NIST calls it a chain.

The bones are the write path, and the spine is the read path. So the database picture is not special to the decision. Every stage rests on something written, and computes something at request time. NIST gives designate and reach a single bone, "Network Access," which feeds authentication rather than standing on the spine. Put them on the spine, add a row for the copies that travel with the request and a row for each stage's enforcer, and the chain becomes a grid. Here it is as a map of this series, with each cell tagged by the article that covers it:

![Series roadmap: the grid of four stages and four rows, with each cell tagged by the article that covers it](/assets/authorization/series-roadmap.svg)

The columns are the stages of a request: designate, reach, authenticate, decide. Each one is labelled with the function it computes. The rows run in time order:

- **Written:** what the stage rests on, and who may write it. This is the write path, and it happens before any request.
- **Carried:** a copy of the written state that the holder brings with the request: a certificate or a session cookie for authenticate, a scoped token for decide. It is minted at issue time, still before the request. A carrier can also serve several stages at once. A capability designates, reaches and decides in one object.
- **Reference monitors:** what the request meets first, and what makes the stage binding, by absence or by judgment. Under designate, that is who controls the namespace. Under reach, it is that no path goes around the enforcer. Under decide, it is the PEP.
- **Looked up:** what the reference monitor fetches when the request did not carry enough. This is the read path: resolution, routing, the PDP's query.

Carried and Looked up are the two ways a reference monitor gets written state. A carrier is fast and frozen. A lookup is fresh, and it has to go all the way back to the store. That is the trade [Part 3](/programming/carriers.html#fresh-or-frozen) is about.

The Decide column reads top to bottom as one check. Facts and rules are written, and a token may be minted from them. The PEP receives the request, and asks the PDP only if the token is not enough. Its Written and Looked up cells are the database of [Part 1](/programming/authorization-models.html), and its reference monitor is the PEP.

Other maps of authorization land on the grid too. The XACML boxes are the Decide column: the PAP and the attribute authorities write it, the PIP and the PDP evaluate it, and the PEP enforces it. [IDPro's six axes][authorization-terminology-mess] also fit inside that one column, which is why they have no place for sandboxes or capabilities. And [Karp's][from-abac-zbac-evolution] four steps of access control take four cells. Identification and authorization are writes, made before any request: one provisions an identity, the other grants a permission. Authentication and the access decision happen at request time.

## The articles

- **[Prologue: Who is the adversary](/programming/who-is-the-adversary.html)** — five positions the attacker has occupied, from a stranger at the gate to the data your delegate reads. Why identity stopped being the useful thing to key on, and where to find a technical threat model.
- **[Part 1: Authorization models](/programming/authorization-models.html)** — the Decide column read as a data system: stored facts, the rules that derive a view from them, and who may write either. Where the view is computed, which questions it answers cheaply, and how fresh its answers are. Along the way, why DAC and MAC are answers to the mutation question rather than rungs of a ladder.
- **[Part 2: How authority is enforced](/programming/authority-enforcement.html)** — the reference monitor row, and Anderson's three properties. Each stage has its own enforcer, one enforcer can hold several stages, and each stage is enforced by absence or by judgment. Then granularity and the routes down it, why Linux is a toolkit rather than a primitive, and what can change between the check and the use.
- **[Part 3: Carriers](/programming/carriers.html)** — copies of a decision that travel with the request. How much of the decision rides along, Karp's where and when, bearer tokens and the registries they grow, OAuth, and the trade between a fresh lookup and a frozen copy.
- **[Part 4: Capabilities](/programming/capabilities.html)** — the carrier that serves several stages at once: authority you hold, not authority you are. The four boxes assume the PDP looks the subject up; a capability has nothing to look up, because the subject arrives holding the authority. Why the access matrix has to be square to describe that. Four things get called capabilities; only one of them makes designation and authority the same act, which is why the confused deputy is structural. Then the three classic objections, and where the property can be bought.

[authorization-terminology-mess]: https://idpro.org/authorization-terminology-is-a-mess-lets-fix-it/ "Authorization Terminology Is a Mess. Let's Fix It."
[authzen-api]: https://openid.net/specs/authorization-api-1_0.html "Authorization API 1.0 - OpenID Foundation"
[from-abac-zbac-evolution]: https://shiftleft.com/mirrors/www.hpl.hp.com/techreports/2009/HPL-2009-30.pdf "From ABAC to ZBAC: The Evolution of Access Control Models"
[nist-sp-800-162]: https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-162.pdf "NIST SP 800-162: Guide to Attribute Based Access Control (ABAC) Definition and Considerations"
[state-union-authorization]: https://idpro.org/the-state-of-the-union-of-authorization/ "The State of the Union of Authorization"
