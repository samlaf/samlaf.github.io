---
title:  "Authorization"
category: programming
date: 2026-08-31
---

This is the intro to a short series on authorization — not a survey of policy engines, but the structure underneath them: where authority is written down, who is allowed to change it, what makes any of it binding, and what breaks when the thing you are constraining decides at runtime what it wants to do.

## One picture, four boxes

Almost every authorization product ships some version of this diagram. The four boxes come from XACML, and the four-letter names are ugly, but the decomposition is the best map of the territory anyone has drawn. This version is Figure 5 of [NIST SP 800-162][nist-sp-800-162], the NIST guide to attribute-based access control:

![PEP, PDP, PAP and PIP, with the policy repository, the attribute repository and environment conditions](/assets/authorization/nist-abac-functional-points.png)

A subject wants to act on an object. Four distinct things have to happen, and each one is a separate engineering problem:

- **PEP**, policy enforcement point. Sits in the path of the effect. The subject's request physically goes through it on its way to the object, and it does what the decision says.
- **PDP**, policy decision point. Evaluates policy against facts and returns a decision. It need not sit in the path at all.
- **PAP**, policy administration point. Where policy is authored, and — more interestingly — who is allowed to author it. It writes to the policy repository.
- **PIP**, policy information point. Where the facts come from. It draws on two kinds: attributes that someone assigned and stored, such as group membership, ACL entries and security labels; and *environment conditions*, which nobody assigns and which are measured at decision time, such as the time, the location or the threat level.

The policy repository and the attribute repository are the split worth dwelling on, because it is the code/data split. The policy repository holds rules; the attribute repository holds facts; the PDP is a pure function of both. The split is clean in ABAC, the model the figure was drawn for, and it blurs everywhere else. A Linux ACL entry is a rule and a fact at once: it says who may do what, and it is stored on the file like any other attribute. In ReBAC the schema is policy and the relationship tuples are data, yet writing a tuple is how you grant access. Either way, "change the policy" almost always means "write to a repository," and that is why the question of *who may write there* turns out to organize the whole field.

Strip the boxes away and the PDP computes the same function in every system ever built:

```text
f(subject, action, resource, context) → allow | deny
```

Stored attributes describe the subject and the resource. The environment conditions are the context.

### What the figure leaves out

XACML's own [data-flow model][xacml-core] has a fifth box, the *context handler*. It translates the PEP's native request into XACML's canonical form, and it fetches attributes from the PIP on the PDP's behalf. NIST calls it "an optional additional component," and most deployments fold it away: the translation moves into the PEP, and the attribute fetching into the PDP. XACML also lets a decision carry *obligations*, duties such as "log this access" or "redact these fields." Conforming PEPs are "required to deny access unless they understand and can discharge all of the `<Obligations>` elements." The figure draws neither.

Of all the arrows in the figure, one has a standard today: PEP to PDP. [AuthZEN][authzen-api], the OpenID Foundation's Authorization API, defines that exchange and nothing else. The PDP's "policy language, architecture, and state management" are out of scope, and the terms PAP and PIP never appear. AuthZEN also lets the PEP push attributes itself, instead of having the PDP pull them from a PIP: "Many authorization systems are stateless, and expect the PEP to pass in all relevant attributes." Its decision is a boolean, plus an optional `context` that may carry obligations. Where XACML requires a deny, AuthZEN says only that a PEP that does not understand the context "MAY choose to reject the decision."

That is the state of the field in one line: the shape of `f` is settled, and everything else on the diagram is not.

## Six columns over the boxes

The boxes name the parts. IDPro's [Authorization Terminology Is a Mess: Let's Fix It][authorization-terminology-mess] turns them into questions you can ask of any system:

![Authorization Terminology](/assets/authorization/authorization-terminology.png)

Each column asks about one part of the figure:

| column | question | part |
| --- | --- | --- |
| Administration | who sets the rules? | PAP |
| Model | what is the logic? | policy repository: what the rules mean |
| Policy | what is the format? | policy repository: how the rules are written |
| Information | what is the data source? | PIP |
| Decision | where is it computed? | PDP |
| Enforcement | where is it enforced? | PEP |

The Model column lists ACL, RBAC, ABAC and ReBAC, and no capabilities. The nearest cell is Token Claims, under Information, and even that is not quite it. Part 3 explains why.

## From a chain to a grid

The four boxes describe one stage of a request: the decision. NIST draws the whole path of a request in a second figure, which it calls a *trust chain*:

![NIST SP 800-162, Figure 8: the ABAC trust chain](/assets/authorization/nist-abac-trust-chain.png)

Read it as a spine with bones. The spine runs left to right, and it is what happens during one request: the subject authenticates, a decision is made, and the decision is enforced on the way to the object. The bones are what each stage rests on, and almost all of them were written earlier, by someone: a credential issued, an identity provisioned, an attribute assigned, a rule managed. The effect at the end is only as trustworthy as every bone behind it. That is why NIST calls it a chain.

Karp's four steps of access control split across the two halves. [Karp][from-abac-zbac-evolution] names them identification, authentication, authorization and access decision. Two of them are writes, made before any request: identification provisions an identity, and authorization grants a permission. The other two happen on the spine, at request time.

The chain leaves out two stages. It assumes the subject can already name the object and get a request to it, and neither is free. First a name has to resolve to an object: the kernel walks a path, DNS maps a host, a table maps a file descriptor to an open file. Call that **designate**. Then the request has to be carried to whatever serves the object: a syscall boundary, a route, an IPC endpoint. Call that **reach**. NIST has one bone for all of this, "Network Access," and it feeds authentication rather than standing on the spine.

Put designate and reach on the spine, and enforcement stops being a stage. NIST's "Access Control Enforcement" box is the PEP: the gate that applies a decision. That is the **narrow** sense of a reference monitor. But a `chroot` enforces too, and so does an empty network namespace. The name resolves to nothing, or the packet has no route, and nothing was ever decided. Designate and reach have enforcers of their own. So enforcement is not a stage after the decision. It is a row under every stage, and Anderson's three properties — always invoked, tamperproof, verifiable — apply to whatever carries out each one. That is the **broad** sense of a reference monitor. The series needs both.

The result is a grid. Here it is as a map of this series, with each cell tagged by the article that covers it:

![Series roadmap: the grid of four stages and three rows, with each cell tagged by the article that covers it](/assets/authorization/series-roadmap.svg)

The columns are the stages of a request: designate, reach, authenticate, decide. The rows are:

- **Written:** what the stage rests on, and who may write it.
- **Request:** what the stage computes while the request is in flight.
- **Enforced:** what makes the stage binding.

Two regions sit outside the cells. **Carriers** are copies of something written that travel with the request, so the stage does not have to look it up: a certificate, a session cookie, a scoped token, a capability. **Bindings** are artifacts that serve several stages at once. A capability designates, reaches and decides in one object.

Everything earlier in this intro lands on the grid. The four boxes are the Decide column: the PAP and the attribute authorities write it, the PIP and the PDP evaluate it, and the PEP enforces it. IDPro's six columns describe that same column. Karp's four steps take four cells.

### Three series, one grid

This series is one of three that share the grid. A series on applied cryptography covers proof of possession and custody, under the Authenticate column, and the machinery below the grid. A series on identity covers most of the Written row: how names get bound to keys, and to places. This series covers the rest: the Decide column, the Enforced row, the carriers of decisions, and bindings. The other two series come later. Until then, the grey cells mark their ground.

The grid does not draw the adversary. The whole discipline is about the paths it does not show: the ones that reach the object without passing an enforcer. Whether a cell holds depends on who the subject is and what it can try, which is a threat model, not an architecture. So the series opens with a prologue on the adversary. It ends with the case where the subject is an LLM: a subject whose intent is not fixed at request time, and whose requests may have been written by whoever last wrote into its context window.

## The articles

- **[Prologue: Who is the adversary](/programming/who-is-the-adversary.html)** — five positions the attacker has occupied, from a stranger at the gate to the data your delegate reads. Why identity stopped being the useful thing to key on, and where to find a technical threat model.
- **[Part 1: Authorization models](/programming/authorization-models.html)** — the Written and Request rows of the Decide column: what the repositories hold, and who may write to them. The access matrix and its two projections, and why DAC and MAC are answers to the mutation question rather than rungs of a ladder.
- **[Part 2: Carriers](/programming/carriers.html)** — copies of a decision that travel with the request. How much of the decision rides along, Karp's where and when, bearer tokens and the registries they grow, OAuth, and the trade between a fresh lookup and a frozen copy.
- **[Part 3: Capabilities](/programming/capabilities.html)** — the Bindings region: authority you hold, not authority you are. The four boxes assume the PDP looks the subject up; a capability has nothing to look up, because the subject arrives holding the authority. Why the access matrix has to be square to describe that. Four things get called capabilities; only one of them makes designation and authority the same act, which is why the confused deputy is structural. Then the three classic objections, and where the property can be bought.
- **[Part 4: How authority is enforced](/programming/authority-enforcement.html)** — the Enforced row. The reference monitor in both senses, and its three properties. Each stage has its own enforcer, and unnameability versus adjudication is a choice of which stage to cut. Then granularity and the routes down it, why Linux is a toolkit rather than a primitive, and what can change between the check and the use.
- **[Part 5: LLM sandboxing](/programming/llm-sandbox.html)** — every region at once: the gateway, correct and unavoidable. A system that has the substrate and threw the property away: the runtime–gateway contract, the landscape scored against it, and a recommended architecture.

[authorization-terminology-mess]: https://idpro.org/authorization-terminology-is-a-mess-lets-fix-it/ "Authorization Terminology Is a Mess. Let's Fix It."
[authzen-api]: https://openid.net/specs/authorization-api-1_0.html "Authorization API 1.0 - OpenID Foundation"
[from-abac-zbac-evolution]: https://shiftleft.com/mirrors/www.hpl.hp.com/techreports/2009/HPL-2009-30.pdf "From ABAC to ZBAC: The Evolution of Access Control Models"
[nist-sp-800-162]: https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-162.pdf "NIST SP 800-162: Guide to Attribute Based Access Control (ABAC) Definition and Considerations"
[xacml-core]: https://docs.oasis-open.org/xacml/3.0/xacml-3.0-core-spec-os-en.html "eXtensible Access Control Markup Language (XACML) Version 3.0"
