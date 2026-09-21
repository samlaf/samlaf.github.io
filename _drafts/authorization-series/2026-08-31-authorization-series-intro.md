---
title:  "Authorization"
category: programming
date: 2026-08-31
---

This is the intro to a short series on authorization — not a survey of policy engines, but the structure underneath them: where authority is written down, who is allowed to change it, what makes any of it binding, and what breaks when the thing you are constraining decides at runtime what it wants to do.

## Three questions, not one

Strip away the storage and every authorization system evaluates the same function:

```text
f(subject, action, resource, context) → allow | deny
```

That shape is the settled part. The industry converged on it and then standardized it. What is not settled is everything around it, and it splits into three questions that get collapsed into one constantly.

1. **Representation.** Where does the answer live before anyone asks? A list at each resource, a set of references held by each subject, a role table, a graph, a policy document. Nobody stores `f` — it is astronomically large and it changes constantly — so every model is a scheme for producing its answers without writing it down. Each makes a different set of questions cheap and a different set expensive, and the expensive ones are what eventually break your architecture.
2. **Mutation.** Who may change the answer, and where do they go to do it? The models differ more on this than on anything else, and almost nobody sorts them by it. Most answers amount to "someone with administrative standing," supplied from outside the model entirely.
3. **Enforcement.** What stops a program from ignoring the description? A representation is a description. A program that does not participate is not violating the model — it is operating outside it. Something has to guarantee that every attempt to cause an effect actually meets the check.

Those three sort into the two halves people usually mean by *policy* and *mechanism*. Representation and mutation are the policy half — what the rules are and who edits them. Enforcement is the mechanism half. Both are answers, and an answer is only as good as the question it was measured against: every claim in this series — non-bypassable, unnameable, correct — is a claim about one specific adversary, and the same mechanism goes from sufficient to decorative when that adversary changes. So the series opens with a prologue on who the adversary is, and where they have sat over the last fifty years.

## The articles

- **[Prologue: Who is the adversary](/programming/who-is-the-adversary.html)** — five positions the attacker has occupied, from a stranger at the gate to the data your delegate reads. Why identity stopped being the useful thing to key on, and where to find a technical threat model.
- **[Part 1: Authorization models](/programming/authorization-models.html)** — what every system computes, and who may change it. The access matrix and its two projections, why DAC and MAC are answers to the mutation question rather than rungs of a ladder, and the five separable concerns that most authorization arguments confuse for one.
- **[Part 2: Capabilities](/programming/capabilities.html)** — authority you hold, not authority you are. Four things get called capabilities; only one of them makes designation and authority the same act, which is why the confused deputy is structural rather than a bug. Ends with the three classic objections and which of them survive.
- **[Part 3: How authority is enforced](/programming/authority-enforcement.html)** — what makes any of it binding. The reference monitor and its three properties, unnameability versus adjudication as the two enforcement strategies, why Linux is a toolkit rather than a primitive, and what can change between the check and the use.
- **[Part 4: LLM sandboxing](/programming/llm-sandbox.html)** — the gateway, correct and unavoidable. The whole series pointed at a system that has the substrate and threw the property away: the runtime–gateway contract, the landscape scored against it, and a recommended architecture.
