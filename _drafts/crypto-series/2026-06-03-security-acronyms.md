---
title:  "A Taxonomy of Security Taxonomies"
category: programming
date: 2026-06-03
---

The sentence that organizes the zoo is:

> For each **property/concern**, in each **data state**, against each **threat**, choose a **function/capability**, define the **policy**, enforce it with **mechanisms**, wrapped by **technical / process / human controls**.

That sentence is intentionally not a one-dimensional stack. It has four orthogonal axes:

1. **Concern** — what's at stake? Each concern has a *property* (its defender-side name — confidentiality, integrity, …) and a *threat* (its attacker-side name — disclosure, tampering, …): one thread seen from the two sides.
2. **Data state** — where is the information: at rest, in transit, or in use / processing?
3. **Layer** — *how abstract* is the control: capability → policy → mechanism, the realization stack.
4. **Control modality** — *what material* is the control: technology, process/practice, human/education.

McCumber's cube is the ancestor of this picture: CIA × {storage, transmission, processing} × {technology, policy/practices, people}. The tweak here is to split two *orthogonal* things McCumber's third axis bundles together. **Technology / process / people** is the *modality* — what **material** a control is made of. **Capability → policy → mechanism** is the *layer* — how **abstract** a control is, from the function you reach for down to the engine that enforces it. These are perpendicular: every control has both an altitude and a material, so the same three layers recur in each modality (a reference monitor is `(mechanism, tech)`; a four-eyes deploy checklist is `(mechanism, process)`; a written classification standard is `(policy, process)`). The collision to watch is the word *policy*: McCumber's "policy/practices" is a modality (organizational practice), while the "policy" layer here is a decision rule such as "subject S may perform action A on object O under context C."

Within that larger grid, the realization stack is a means-ends chain: a **mechanism** upholds a **policy model** that realizes a **capability** — and the top of that chain *delivers the property*, the concern's defender-side name. So the property is not a fourth layer; it's where the stack meets the concern axis. The other pieces are frames around it: the **threat** is the same concern's attacker-side name (the property mirrored), build principles constrain every layer, modality says what material the control is, and risk/governance decides what's worth doing at all.

So AAA isn't a rival to CIA — it's the *realization stack below* it (the capabilities that deliver the properties). Bell–LaPadula isn't a rival to AAA — it's a level below *that* (the rule-set that realizes a capability). And the reference monitor that checks each access is a level below *that* again (the engine that enforces the rules). Sort every acronym by **which question it answers** and the zoo collapses into a grid with an attacker-side mirror and a governance wrapper. The map:

**The concern, then the stack** — the top two rows are the concern's two faces (what's at stake); the bottom three are the realization stack (how you deliver it), descending from the function you reach for to the machine that enforces it:

| | The question it answers | Examples |
|---|---|---|
| *concern — WHAT'S AT STAKE* | | |
| **Property** · defender's name | What must hold — what counts as a violation? | CIA · Parkerian hexad · 5 Pillars · Pentagon of Trust · McCumber |
| **Threat** · attacker's name | What does the adversary make happen instead? | STRIDE · LINDDUN |
| **↳ formalized** | …stated precisely enough to *prove*? | safety/liveness · hyperproperties · noninterference · IND-CPA / EUF-CMA |
| *layer — THE REALIZATION STACK* | | |
| **Capability / function** · *what?* | What function delivers the property? | AAA · IAAA · Lampson's Gold Standard |
| **Policy model** · *which?* | Which rules apply? (the *spec*) | Bell–LaPadula · Biba · Clark–Wilson · Chinese Wall · MAC/DAC/RBAC/ABAC |
| **Enforcement mechanism** · *how?* | How are the rules enforced at runtime? (the *implementation*) | reference monitor · PEP/PDP · MMU & page bits · TPM/enclaves · sandboxes (seccomp/eBPF) · **the crypto itself** |

A note on what's *not* in the stack. The property and threat above aren't stack levels — they're the concern's two faces, the *what* the stack serves. State and modality are cross-cutting axes, not levels. Three more things sit *around* the grid, and this article only sketches them: **build principles** — how to build any layer *well* (Kerckhoffs, least privilege, Zero Trust); the **attacker's mirror** — the whole grid read from the other side (STRIDE is just the property axis inverted, which the concern grid below makes explicit); and the **governance / risk loop** — deciding what's even worth defending (risk scoring, NIST CSF, OODA). Privacy keeps its own property-sets (FIPPs, Contextual Integrity, Pfitzmann–Hansen) for what content-encryption can't state — but its core concern, *unlinkability*, is already a row below.

## The concern axis

The stack above is only the **layer** axis — *how abstract* (capability → policy → enforcement). Cutting across it is the **concern** axis: *what the thing is about*. Borrow the software word from *separation of concerns*: a concern is a subject-matter thread that runs vertically through every level, wearing a different name at each one. So every named term is really a **cell in a grid = (concern × state × layer × modality)**; the 2-D slice below holds state and modality implicit and shows just **concern × layer**. The two leftmost columns are the concern's two faces (*what's at stake* — defender's property, attacker's threat); the rest is the realization stack, which OS design reads as an interrogative ladder *what → which → how*:

| Concern | Property · *defender* | Threat · *attacker* | Capability · *what?* | Policy · *which?* | Enforcement · *how?* |
|---|---|---|---|---|---|
| **Secrecy** — keep content unseen | confidentiality | disclosure | encryption / read-control | classification labels · BLP no-read-up | AEAD · read-ACL |
| **Unlinkability** — who talks to whom? | anonymity / unlinkability | linking / profiling | metadata minimization | data-minimization · k-anonymity | mixnets · onion routing · padding |
| **Undetectability** — is there even a message? | undetectability / unobservability | detection / traffic analysis | traffic hiding | cover-traffic rate · stego capacity | steganography · spread-spectrum · constant-rate cover traffic |
| **Correctness** — keep content unaltered | integrity | tampering | integrity protection / write-control | Biba · Clark–Wilson | MAC · signature · write-ACL |
| **Origin** — who sent it? | authenticity | spoofing | authentication | which CAs/keys to trust | signature · cert-chain check |
| **Attribution** — who did it? | accountability / non-repudiation | repudiation | auditing | what-to-log · retention | logging · **signatures** · tamper-evident trail |
| **Uptime** — is it reachable? | availability | denial of service | rate-limit / admission control | quotas · QoS thresholds | replicas · load balancers · SYN cookies |

**Policy vs. mechanism.** [OSTEP](https://pages.cs.wisc.edu/~remzi/OSTEP/) names the bottom two stack levels for OS design — **policy = *which*** ("which process should run?") and **mechanism = *how*** ("how does a context switch work?") — and separating them is a modularity win: change the *which* without rethinking the *how*. **Capability = *what*** sits one level up (what *kind* of function you reach for: authentication? authorization? auditing?), and the **property** the stack delivers is the *why* it exists at all. The same swap-one-without-the-other modularity holds at every adjacent pair.

One asymmetry worth flagging: *policy* is the only **multi-W** level. Capability is just *what*, mechanism just *how* — but a policy is a predicate over an access *event*, so it pins down the full situational 5-W: **who** (subject) may take **what** action on **which** object, **where/when** (context). "Which" is just the headline; **ABAC** parameterizes all of them explicitly. This is also *why* XACML grows a fourth component — the Policy *Information* Point (PIP) — whose only job is to fetch those who/which/where attributes for the decision; see the enforcement-mechanism section.

The first three rows are one *hiding* family, split first into **data vs. metadata**: **secrecy** hides the *content* (the data), while **unlinkability** and **undetectability** hide the *metadata* (the envelope) — the *who-talks-to-whom* relationships and the *existence/volume* of traffic respectively. (That's exactly the capstone's "Leaky" split — "who talks to whom" vs. "when, how often, how much.") (Pfitzmann–Hansen's privacy vocabulary all lives in this corner: *anonymity* = unlinkability of a subject to its messages; *pseudonymity* = the mechanism that dials linkability between full anonymity and full identifiability — and, via digital pseudonyms, the bridge to **attribution**; *unobservability* = undetectability + anonymity.) Then come **correctness**; the identity concerns **origin** and **attribution**; and **uptime**, the availability leg (governance/ops, not crypto). Note what is *not* a row: **access control**. It looks like a concern — "who may touch it?" — but it has no goal of its own, which is the tell. It's the **non-crypto enforcement route** for secrecy (gate reads) and correctness (gate writes), the dual of crypto: authorization → RBAC/BLP/ABAC → reference monitor is that route's capability/policy/enforcement. The crypto-vs-access duality across the storage/transmission/processing states is *the cube*; the read/write split is what makes both confidentiality (encrypt, or gate reads) and integrity (verify, or gate writes) dual. One note on *slicing* the concern axis: Parker's *possession* and *utility* aren't new concerns — they're finer slices of **secrecy** and **uptime** (lose the sealed encrypted drive → secrecy intact, possession gone), the concern-granularity debate again.

This is the resolution to "wait, isn't *authentication* a property?": **a property is just the concern's defender-side name** — its *what-must-hold* face. "Authenticity" and "authentication" don't overlap as a property and a capability; they're the *same concern* (origin), one its property, the other the capability that delivers it. English reuses the root because it nominalizes the verb (*authenticate* → *authenticity*); loose mnemonics then grab whichever form fits their acronym, which is why the Pentagon of Trust drops the *capability* verb *authentication* into a *property* set. (Note the asymmetry: the *access* concern has no clean property at all — authorization's goal is just the confidentiality + integrity it enforces, which is why it keeps getting treated as its own axis.)

Two payoffs, once the grid is visible:

- **The property-set wars are a fight about one axis only.** CIA vs. Parkerian hexad vs. Samonas's "strikes back" is entirely about *how finely to slice the concern axis* — Parker splits confidentiality into secrecy + possession, Samonas says three broad concerns suffice. None of it touches the layer axis. "How many concerns?" and "how many abstraction levels?" are independent questions, routinely conflated.
- **STRIDE is the concern axis, mirrored.** Spoofing ↔ origin, Tampering ↔ integrity, Repudiation ↔ attribution, Information-disclosure ↔ secrecy, DoS ↔ uptime, Elevation ↔ access. That's *why* it's the cleanest property-dual — it's just the concerns enumerated from the attacker's side. It's literally the **threat** column of the grid above.

With the axes in play, the rest of this file walks the grid top-to-bottom — first the **properties** (the concern, defender-side), then each level of the **realization stack** (capability → policy → mechanism) — then the frames around it. The state and modality axes are cross-cuts rather than sections you want to expand into a full 3×N×M matrix every time.

## The data-state axis: storage / transmission / processing

McCumber's second axis asks *where the information is when protected*:

- **Storage / at rest** — disks, databases, object stores, backups, cold archives. Typical threats: stolen media, leaked database snapshots, cloud-admin access, ransomware, rollback to stale state.
- **Transmission / in transit** — bytes moving between endpoints. Typical threats: eavesdropping, tampering, replay, downgrade, man-in-the-middle, misbinding a key to the wrong name.
- **Processing / in use** — plaintext while a CPU, process, enclave, database engine, or AI agent operates on it. Typical threats: malicious process, compromised OS, hostile hypervisor, side channels, prompt injection, supply-chain code executing with legitimate credentials.

The same concern changes shape by state. Confidentiality in transit is usually a secure channel; confidentiality at rest is envelope encryption or read-control; confidentiality in use is isolation, minimization, or confidential computing. Integrity in transit is AEAD/MACs; integrity at rest is signatures, hashes, append-only logs, or write-control; integrity in use is process isolation, measured boot, sandboxing, and verified code.

## The control-modality axis: technology / process / humans

McCumber's third axis is best read as **control modality** — the kind of control you deploy:

- **Technology** — ciphers, protocols, HSMs, reference monitors, MMUs, sandboxes, scanners, logs.
- **Policy / practice / process** — standards, procedures, approvals, runbooks, key-rotation schedules, incident-response playbooks, data-classification rules.
- **Humans / education / culture** — training, review habits, phishing resistance, admin discipline, incentives, separation of duties in the organizational sense.

This is not the same as the **policy level** in the realization stack. The policy level is a decision rule ("who may do what to which object under which context?"). McCumber's policy/practices axis is broader organizational machinery. A KMS decrypt rule is policy-level; the quarterly key-rotation runbook and the training that tells engineers when to use it are process/human controls around that rule — and the rule itself can be enforced in any modality, which is exactly why *policy* lives on a different axis from *process*.

## Properties — the concern, defender-side: *what counts as a violation?*

The "what are we protecting" property sets — the concern's defender-side face; **STRIDE/LINDDUN mirror each into its attacker-side threat**. Every level of the realization stack below exists to deliver one of these.

- **CIA triad** — Confidentiality, Integrity, Availability. Sometimes written **AIC** to avoid the agency collision.
- **Parkerian hexad** (Donn Parker, 1998) — CIA + Possession/Control, Authenticity, Utility. The additions exist precisely because CIA conflates things: "possession" splits the *control* of data from its *disclosure* (you can lose a sealed encrypted drive — confidentiality intact, possession lost), and "utility" covers data that's available but useless (lost the key).
- **Five Pillars of Information Assurance** (US DoD / IATF) — CIA + Authentication + Non-repudiation. Often mnemonic'd as **CIANA** or **IAS-5**. (Note the category slip baked into the mnemonic: Authentication is a *capability* — it's listed as a peer property here only because the pillar set is loose.)
- **Pentagon of Trust** — the Schneier link. Piscitello's proposal to extend the traditional four-property model (Authentication, Authorization, Availability, Authenticity) by prepending **admissibility** — asserting the trustworthiness of the endpoint device before accepting a keystroke. The comment thread correctly collapses this to **remote attestation** — i.e. the whole TDX/DCAP world. The recurring objection there (admissibility ⊆ authentication, since a system has an identity too) is the same argument you'd make for mutual attestation / MAGE.
- **McCumber Cube** (1991) — 3D model: CIA × {storage, transmission, processing} × {policy/practices, education/people, technology}. The ancestor of the model here: property × data-state × control-modality. The important cleanup is that McCumber's third axis is **modality**, not the defender-stack's layer axis — "policy/practices" there means organizational controls, not just formal access rules.

The recurring pattern across these property sets — hexad, Pentagon of Trust, Five Pillars — is people bolting properties onto CIA because CIA feels too coarse. The Samonas counter-argument (see "Where crypto sits") is that they're all subsumable back into CIA *if you read the three words broadly enough* — which is true at the cost of precision.

### Formalized: *how do we state the property precisely enough to prove it?*

Same question, but rigorous. You reach here when the informal sets can't even *state* the property — exactly the BigDipper censorship-resistance situation.

- **Safety & Liveness** (Lamport; topologically characterized by Alpern–Schneider) — "bad thing never happens" / "good thing eventually happens."
- **Hyperproperties** (Clarkson & Schneider — Fred B. Schneider, the *-der*, not Bruce Schneier) — sets of trace-sets; needed because confidentiality (noninterference, observational determinism, generalized non-interference) isn't a property of individual traces. The right home for censorship-resistance-as-hyperproperty.
- **Noninterference** (Goguen–Meseguer, 1982) — the original info-flow security definition.
- **Crypto security notions** — IND-CPA / IND-CCA, EUF-CMA, semantic security, UC (universal composability). Different genre (game/simulation-based) but the same "name the exact property" instinct.

## Capabilities (functions): *which capabilities deliver the goals?*

The next three sections walk the **realization stack** — capability → policy → mechanism — that delivers each property.

Not properties — the *functions* you need to achieve them, and not yet the rules or the code that do so. This is where the "is admissibility a property or a capability?" debates actually live. (Beware the word *mechanism* here: in the classic "separation of policy and mechanism" sense it means the runtime enforcement *engine* — the enforcement-mechanism level below — not this abstract-capability level. That collision is exactly why this level is named *capability*, not *mechanism*.)

- **Lampson's Gold Standard** — **Au**thentication, **Au**thorization, **Au**diting. The pun is that "Au" is gold's symbol. Lampson's framing is broader than the networking sense.
- **AAA** (RADIUS / TACACS+ / Diameter) — Authentication, Authorization, Accounting. Same triad, ops flavor.
- **IAAA** (CISSP canon) — Identification, Authentication, Authorization, Accountability. Splits "claim identity" from "prove it," which the Schneier thread also nitpicks.

## Policy models: *what are the rules? (the spec)*

The formal rule-sets that say what's allowed — the *specification*, not yet the code that enforces it. Each is pinned to a property it realizes a capability for: Bell–LaPadula → confidentiality, Biba → integrity, and so on. (BLP isn't hand-waving — it's a state machine with a proved Basic Security Theorem, a genuine formal spec.)

- **Bell–LaPadula** (confidentiality: no-read-up, no-write-down), **Biba** (integrity: the dual), **Clark–Wilson** (integrity via well-formed transactions + separation of duty), **Brewer–Nash / Chinese Wall** (dynamic conflict-of-interest), plus **HRU**, **Take-Grant**, **Graham–Denning**, **Lipner**, and the **MAC/DAC/RBAC/ABAC** policy families.

## Enforcement mechanisms: *how are the rules enforced at runtime? (the implementation)*

The engine that actually upholds the policy on every access — the *implementation* the spec compiles down to. The boundary between this level and the policy level is the classic **"separation of policy and mechanism"** (Hydra, Brinch Hansen, X11's "mechanism, not policy"): keep the enforcement engine policy-agnostic so you can swap rules without rewriting the enforcer.

- **Reference monitor** (Anderson, 1972) — the abstract "check every access" enforcer the whole field was named around; must be tamper-proof, always-invoked, and small enough to verify.
- **PEP / PDP / PAP / PIP** (XACML's "four horsemen") — the access-control split into a *policy enforcement point* (the gate that intercepts each request), a *policy decision point* (evaluates the policy rules → permit/deny), a *policy administration point* (authors and stores them), and a *policy information point* (fetches the extra attributes the PDP needs — subject, resource, environment). That last one is the runtime embodiment of "policy is multi-W" — it gathers the *who/which/where* of the access so the PDP can decide.
- **Hardware enforcers** — MMU & page-protection bits, TPMs, secure enclaves, the UEFI/secure-boot chain.
- **OS/runtime sandboxes** — seccomp, eBPF, kernel capabilities, namespaces, hypervisor isolation.
- **The crypto itself** — AEAD, signatures, MACs. This is the level cryptography lives on: it *enforces* confidentiality and integrity directly, often with no separate policy model at all (see below).

## Where crypto sits in all this

Crypto is an **enforcement-mechanism family** that directly realizes two broad CIA goals: confidentiality (encryption) and integrity (MAC/signature, with authenticity and non-repudiation as integrity-of-*origin* sub-flavors — the MAC-vs-signature split). It also supports privacy/unlinkability in more specialized constructions. Tellingly, it often *skips* the policy level at the data-object boundary — you don't need Bell–LaPadula to get confidentiality out of AES; the cipher *is* the enforcement, and its implicit policy is "key-holders can decrypt, non-key-holders cannot." But real systems immediately reintroduce policy one step up: who receives the key, which public keys/roots are trusted, who may call KMS `Decrypt`, when keys expire, what measurements attestable code must have.

The useful compression is therefore **not** "all capabilities are crypto or access control." That is Samonas-style semantic inflation: true only if you stretch the words until they stop telling you what to build. The precise version is narrower and more valuable: for **confidentiality and integrity of data objects**, the two dominant enforcement routes are **self-protecting data** (crypto: encrypt/MAC/sign/commit the bytes) and **mediated access** (access control: reference monitors, ACL/RBAC/ABAC, MMUs, database guards, KMS policies). Same goal, different path down the stack: confidentiality via access control descends goal → capability (authorization) → policy (BLP/RBAC/ABAC) → enforcement (reference monitor), whereas confidentiality via crypto can shortcut straight from goal to enforcement (AEAD) and then pushes policy to key distribution and key use.

But the full capability layer is larger: authentication, authorization, auditing/accounting, attestation, key management, monitoring/detection, rate limiting, redundancy, backup/recovery, and incident response do not collapse cleanly into two buckets. Many *use* crypto or access control as mechanisms; they are not themselves just crypto/access control. This is also where one goal fans out into *several* capabilities — the [availability appendix](/programming/availability.html) works the `uptime` cell out in full: a single goal splitting into rate-limiting, redundancy, backup/recovery, and incident response, each with its own policy and mechanism level. Crypto provides none of availability, the authorization policy itself (the policy level), the build principles, or the governance loop — this is the series' "two arms" framing, and the capstone's list of what-a-secure-channel-doesn't-give-you is just the enumeration of the layers and frames crypto leaves untouched.

At the *concern* level, that single integrity arm fans out across the grid via the **MAC→signature escalation**: a symmetric MAC suffices for **correctness** and for **origin** between two parties, but the moment a *third party* must be convinced — **attribution / non-repudiation** — only an asymmetric **signature** works (a shared-key MAC is repudiable by construction, which is exactly why Signal authenticates with MACs *for* deniability). So crypto's enforcement column actually covers **secrecy, correctness, origin, and attribution** — the whole integrity family — not just the two data concerns. It even reaches **unlinkability**, but only partway: content-encryption hides *what* you send, never *who-talks-to-whom* (the capstone's "Leaky" gap), so anonymity needs a mixing/topology layer — though *privacy-enhancing cryptography* (mixnets, onion routing, ring/blind signatures, ZK proofs, PIR) pushes crypto deep into that concern too. The only cells crypto can't touch are **access** (policy + reference monitor) and **uptime** (it only *subtracts* from availability).

This also dissolves the **Samonas "CIA strikes back"** question (*The CIA Strikes Back*, Samonas & Coss 2014). Their claim — that the eight historical additions (authenticity, non-repudiation, correctness, responsibility, integrity-of-people, trust, ethicality, identity management) all subsume back into CIA — is purely a **property-level** argument, and they win it only by reading C/I/A *etymologically/semantically* (confidentiality from *confidere*, "to have full trust"). The tell is their own Table 3: six of the eight route into **Integrity**, because they're using "integrity" in the organizational sense (wholeness, coherence, ethicality of people), not crypto's tamper-evidence sense. So:

- **Narrow / crypto-integrity** = "these bytes weren't altered; this came from the key-holder." Crisp, mechanism-defining. The series' reduction lives here and is *mechanically* true.
- **Sponge / governance-integrity** = "the organization and its people are trustworthy and coherent." Absorbs almost anything — which is how Samonas reaches total subsumption, at the cost of the word telling you what to build.

Verdict: **teeth for governance taxonomy** (CIA-broadly-read genuinely is the durable north star, and the additions were largely a narrowing-then-recovery cycle — their Table 2 runs 1970s CIA → +Au,nR → +CSpec → +RITE,Idn → 2020s back to CIA), **trying too hard for mechanism precision** (the subsumption is semantic inflation, and it never grapples with the cases that genuinely escape CIA: availability's own irreducible leg, privacy/metadata, and the hyperproperty expressiveness gap). They even concede the placements are "highly debatable" and "for illustrative purposes."

## Throughline

The property sets (CIA → hexad → Five Pillars → Pentagon of Trust) all answer "what counts as a violation"; STRIDE/LINDDUN invert each property into an attacker action; the formal layer (safety/liveness, hyperproperties) is what you reach for when the informal sets can't even *state* the property — exactly the BigDipper censorship-resistance situation; and the whole defender/attacker pair runs inside a risk-and-ops loop that decides what's worth defending. The Parkerian additions and the "admissibility" debate are both symptoms of the *property* being too coarse — just at the data layer vs. the endpoint layer respectively — and Samonas is the argument that you should fix that by reading the property *richer*, not by adding levels. The cleaner fix, for an engineering audience, is the opposite: keep each level's vocabulary crisp and notice that the acronyms were never competing — they were answering different questions.
