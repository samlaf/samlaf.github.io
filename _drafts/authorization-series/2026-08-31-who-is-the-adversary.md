---
title:  "Who is the adversary?"
series: "Authorization, Prologue"
series_url: "/programming/authorization-series-intro.html"
category: programming
date: 2026-08-31
---

> This is the prologue to a five-part [series on authorization](/programming/authorization-series-intro.html).
>
> 0. **Prologue: Who is the adversary** — five positions the attacker has occupied, and why identity stopped being the useful thing to key on.
> 1. **[Authorization models](/programming/authorization-models.html)** — what every system computes, and who may change it.
> 2. **[Capabilities](/programming/capabilities.html)** — authority you hold, not authority you are.
> 3. **[How authority is enforced](/programming/authority-enforcement.html)** — what makes any of it binding.
> 4. **[LLM sandboxing](/programming/llm-sandbox.html)** — the gateway, correct and unavoidable.

- [1 · Outside the boundary](#1--outside-the-boundary)
- [2 · A subject you enrolled](#2--a-subject-you-enrolled)
- [3 · Code running as you](#3--code-running-as-you)
- [4 · A delegate you authorized](#4--a-delegate-you-authorized)
- [5 · The data the delegate reads](#5--the-data-the-delegate-reads)
- [Aside — three rungs and two side doors](#aside--three-rungs-and-two-side-doors)
- [What is actually being protected](#what-is-actually-being-protected)
- [Where to get a technical threat model](#where-to-get-a-technical-threat-model)

Every mechanism in this series exists to stop someone. A list at a resource, a reference in a subject's hand, a monitor in the path — each is a claim about *someone*: non-bypassable by whom, unnameable to whom, correct against what. Change the adversary and the same mechanism goes from sufficient to decorative without a line of it changing.

So it is worth asking where the adversary sits before describing what stops them. Over fifty years the answer has moved five times, always inward, and always because the previous position got closed. As in the [crypto series prologue](/programming/threat-model.html), it helps to separate the **threat**, the **theory** that modelled it, and the **implementation** that eventually shipped — because here too, every one of these was modelled long before anything defeated it, and two of them have not been defeated yet.

## 1 · Outside the boundary

**Threat.** Someone with no credentials is trying to get some. They are not a user of your system and the whole question is whether they become one.

**Theory and implementation.** This is the position most people still picture when they hear "access control," and it is the one where authorization does the least work. The interesting engineering is all authentication — passwords, then certificates, then the long arc to passkeys that the [crypto series](/programming/authentication.html) traces. Authorization's contribution is a list, checked once the gate has already decided who is knocking.

**Why it moved.** Authentication became infrastructure. Not perfect, but good enough that attacking the gate stopped being the cheapest route in. The cheapest route is to already be inside.

## 2 · A subject you enrolled

**Threat.** A legitimate account holder, hostile. They authenticate correctly every time, because the credential is theirs.

**Theory.** This is the position the foundational theory was built for, and it got extraordinary attention in about six years. Lampson's access matrix (1971) gave the field the object it still reasons with. Graham and Denning (1972) worked out its protection rules. Bell and LaPadula (1973) formalized what a military confinement policy even means. Harrison, Ruzzo and Ullman (1976) proved that in the general case you cannot decide whether a given permission will ever leak to a given subject — the safety problem is undecidable, which is why every tractable model since is a deliberate restriction of the general one. And Lampson's confinement problem (1973) asked the question the rest of the series keeps returning to: can a program you run on someone else's behalf be stopped from leaking what it sees?

**Implementation.** Unix file permissions, then decades later the mandatory-access-control systems that actually implemented Bell and LaPadula. [Part 1](/programming/authorization-models.html) is largely an account of this position's machinery.

**Why it moved.** It didn't get solved so much as outgrown. Keying on identity works here — the subject is a person, the person has intent, and holding them to a policy is coherent. The trouble starts when the thing taking the action is not the person.

## 3 · Code running as you

**Threat.** A program, carrying your full authority because it inherited it by running as you. It need not be malicious. It only needs to be talked into using a power it holds for a purpose it was not asked for.

**Theory.** Saltzer and Schroeder named the cure in 1975: every program should run with the least authority its job requires. Hardy named the disease in 1988, after watching a compiler be persuaded to overwrite a billing file it was merely *able* to reach — the confused deputy. Note the thirteen-year gap, and note which came first. The capability tradition had the structural answer even earlier: Dennis and Van Horn (1966), then KeyKOS and the systems [Part 2](/programming/capabilities.html) is about, all of which make designating a thing and holding authority over it the same act, so that there is no name an attacker can utter to borrow a power they were never given.

**Implementation.** Essentially none, on the platform where it mattered most. The desktop operating system shipped position-two controls into a position-three world and still does: every program you launch holds everything you can do. Mobile platforms bought some of it back with per-app permissions and per-app storage, twenty years late and only for one class of software.

**Why it didn't move.** This one never closed. It accumulated. Positions four and five are both built on top of an unfixed position three, which is why the confused deputy keeps reappearing in each of them wearing new clothes.

## 4 · A delegate you authorized

**Threat.** Software acting for you, on purpose, with authority you deliberately handed it — and exercising that authority for something you did not intend. An OAuth client, a service account, a CI job, an integration. Nothing is stolen and nobody is impersonated.

**Theory and implementation.** This is the position where the industry did real work, because delegation became the normal way software is composed and the bill arrived quickly. OAuth 1.0 (2007) and 2.0 (2012) made third-party delegation routine; scopes, audiences and short expiry made it survivable; macaroons (2014) showed that a credential can carry its own attenuation so that a delegate can hand on strictly less than it holds. [Part 2](/programming/capabilities.html) is mostly about how well that worked and where it stopped short.

**Why it moved.** It didn't, entirely — this is a live position. But it rests on an assumption that held until recently: the delegate's *plan* is fixed. You grant a CI job the authority its pipeline needs because you can read the pipeline. When the plan stops being knowable in advance, the scoping story stops working.

## 5 · The data the delegate reads

**Threat.** The delegate's intent is assembled at runtime out of documents, pages, issues, and tool output — any of which an attacker may have written. There is no subject to blame, no credential was stolen, and the agent is behaving exactly as designed. It read something and did what it said.

**Theory.** Greshake and co-authors gave it a name in 2023, indirect prompt injection, and the literature since has been enormous. But the shape is Hardy's, thirty-five years on. The injected text supplies a designator — a path, a URL, a repository. The agent's ambient authority supplies the rest. It is a confused deputy whose confusion is now the normal operating mode rather than a bug, because reading untrusted input and acting on it *is* the product.

**Implementation.** Open. [Part 4](/programming/llm-sandbox.html) is an argument that the cure is the old one — take away the ambient authority, so that the injected designator names nothing worth having — and an account of how far you can actually get.

## Aside — three rungs and two side doors

One distinction is worth carrying through the rest of the series, because it decides what any given mechanism is worth.

Three of these adversaries form a ladder, by how much of the machine they own. An attacker who controls only the *input* a program reads is the weakest; they need the program's own code to stay honest, and they defeat anything that relies on that program correctly telling a request it should honour from one it should not. An attacker running *arbitrary code* in the workload is stronger; they defeat every cooperative convention — proxy environment variables, tool APIs, library-level policy — while in-kernel mediation still holds. An attacker who owns the *kernel* is stronger still; every control enforced inside that machine fails at once, and every fact it reports becomes a claim rather than evidence.

Two more sit off the ladder and combine with any rung of it. One splits an action across several channels that are each individually permitted, which defeats a monitor that adjudicates one effect at a time without defeating any single check. The other targets the policy itself — the matchers, the callbacks, the config — which arrives through the same supply chain as everything else.

So adversary strength is a partial order, not a line. A threat table with a single column is quietly mixing two questions, and "this is sandboxed" is not an answer until it says which of these it was measured against.

## What is actually being protected

One more framing before the series proper, because it changes what a boundary has to cover.

In most security writing the asset is data. Here it is not. The asset is **the authority to cause an effect** — a repository that can be force-pushed, a credential that can be spent, a table that can be dropped, a package that can be published. Confidentiality is one effect among these, not the organizing one.

The practical difference is in what you end up enumerating. Inventory data and you protect stores. Inventory effects and you enumerate the paths by which the workload can cause each one — which is the only inventory that can tell you whether a monitor sits in all of them. [Part 3](/programming/authority-enforcement.html) builds directly on that.

## Where to get a technical threat model

This prologue is a lens, not a checklist. It says where the adversary sits and why the series is organized the way it is. It does not enumerate threat categories, score mechanisms, or give you a coverage matrix, and for real deployment work you want all three. Three documents do that job well:

- **[The Agent Sandbox Taxonomy](https://github.com/kajogo777/the-agent-sandbox-taxonomy)** decomposes agent sandboxing into seven defense layers and seven threat categories, scores each mechanism on strength, granularity and portability, and publishes fingerprints for a couple of dozen products. Its strength ladder — cooperative, software-enforced, kernel-enforced, structural — is the same distinction [Part 4](/programming/llm-sandbox.html) arrives at independently, which is some evidence that the distinction is real.
- **[OWASP's Top 10 for LLM Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/)** and the **[Agentic AI Threats and Mitigations](https://genai.owasp.org/resource/agentic-ai-threats-and-mitigations/)** work from the Agentic Security Initiative are the standards-body enumeration, and the right thing to audit a deployment against.
- **[MITRE ATLAS](https://atlas.mitre.org/)** supplies tactics, techniques and real case studies in the ATT&CK idiom, for anyone who already thinks in that vocabulary.

One place I read the taxonomy differently, since it bears on the whole series. AST rules prompt injection, hallucination and misalignment out of scope as *vectors* rather than threats, on the grounds that a sandbox governs what an agent can do rather than what it chooses to do, and that choosing is an alignment problem. The first half is right and the framing is useful. But the conclusion I draw is the opposite one: injection is a confused deputy, which is an authorization failure with a fifty-year-old structural cure, and treating it as somebody else's department is how it keeps getting answered with better judgment instead of less authority. Position three in this article is the argument, and [Part 4](/programming/llm-sandbox.html) is the case.
