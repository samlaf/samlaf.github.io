---
title:  "Authorization"
category: programming
date: 2026-08-31
---

This is the intro to a short series on authorization — not a survey of policy engines, but the structure underneath them: where authority is written down, who is allowed to change it, what makes any of it binding, and what breaks when the thing you are constraining decides at runtime what it wants to do.

## One picture, four boxes

Almost every authorization product ships some version of this diagram. It comes from XACML, and the four-letter names are ugly, but the decomposition is the best map of the territory anyone has drawn.

![image](/assets/authorization/xacml-architecture.png)

Alice wants to view record #123. Four distinct things have to happen, and each one is a separate engineering problem:

- **PEP**, policy enforcement point. Sits in the path of the effect. Alice's request physically goes through it, and it does what the decision says.
- **PDP**, policy decision point. Evaluates policy against facts and returns allow or deny. It need not sit in the path at all.
- **PAP**, policy administration point. Where policy is authored, and — more interestingly — who is allowed to author it.
- **PIP**, policy information point. Where the facts come from. Group membership, ACL entries, security labels, attributes.

The PAP/PIP split is the one worth dwelling on, because it is the code/data split. The PDP is a pure function; everything mutable lives in the PIP. A Linux ACL is PIP data. The kernel's permission check is a stateless PDP reading it. "Change the policy" almost always means "write to the PIP," and that is why the question of *who may write there* turns out to organize the whole field.

Strip the boxes away and the PDP computes the same function in every system ever built:

```text
f(subject, action, resource, context) → allow | deny
```

That shape is settled. Everything else on the diagram is not.

## What each box costs you

The series is, more or less, one article per box.

**The PIP is never written down.** `f` is astronomically large and changes constantly, so nobody stores it. Every authorization model — ACLs, capability lists, roles, graphs, attribute policies — is a compression scheme for producing its answers without materializing it. Each makes one set of questions cheap and another expensive, and the expensive ones are what eventually break your architecture.

**The PAP is where the models actually differ.** Not in what they can express — in who may change it and where they go to do it. DAC and MAC are answers to that question, not rungs of a ladder. Most systems answer it with "someone with administrative standing," supplied from outside the model entirely, which is to say they do not answer it.

**Capabilities collapse the PIP into the request.** The diagram assumes arrow 4: the PDP looks Alice up. A capability system has nothing to look up, because Alice arrives holding the authority itself. Designation and permission become the same act. That single change is what makes the confused deputy structural rather than a bug.

**Only the PEP has to be unavoidable.** The PDP must be *correct*; the PEP must be *non-bypassable*. Different properties, different techniques, and conflating them is how you end up with an authorization system that is beautifully expressive and trivially routed around. This is Anderson's reference monitor, and every enforcement failure in the series is one of its properties not holding.

And then the thing the diagram does not draw. It shows one arrow from Alice to the green box, through the PEP. The entire discipline is about the arrows that are *not* drawn — the paths to the resource that never pass the enforcement point. Whether the picture is complete depends on who Alice is and what she is able to try, which is a threat model, not an architecture. So the series opens with a prologue on the adversary, and ends with the case where Alice is an LLM: a subject whose intent is not fixed at request time, and whose requests may have been authored by whoever last wrote into her context.

## The articles

- **[Prologue: Who is the adversary](/programming/who-is-the-adversary.html)** — five positions the attacker has occupied, from a stranger at the gate to the data your delegate reads. Why identity stopped being the useful thing to key on, and where to find a technical threat model.
- **[Part 1: Authorization models](/programming/authorization-models.html)** — the PIP and the PAP. The access matrix and its two projections, why DAC and MAC are answers to the mutation question rather than rungs of a ladder, and the five separable concerns that most authorization arguments confuse for one.
- **[Part 2: Capabilities](/programming/capabilities.html)** — authority you hold, not authority you are. Four things get called capabilities; only one of them makes designation and authority the same act, which is why the confused deputy is structural. Ends with the three classic objections and which of them survive.
- **[Part 3: How authority is enforced](/programming/authority-enforcement.html)** — the PEP. The reference monitor and its three properties, unnameability versus adjudication as the two enforcement strategies, why Linux is a toolkit rather than a primitive, and what can change between the check and the use.
- **[Part 4: LLM sandboxing](/programming/llm-sandbox.html)** — the gateway, correct and unavoidable. A system that has the substrate and threw the property away: the runtime–gateway contract, the landscape scored against it, and a recommended architecture.
