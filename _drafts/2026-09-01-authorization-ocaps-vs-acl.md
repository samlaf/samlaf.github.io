---
title:  "Authorization: Capabilities vs ACLs"
category: programming
date:   2026-09-01
---

## Historical Perspective

![image](/assets/authorization-ocaps-vs-acl/auth-models.png)

https://idpro.org/the-state-of-the-union-of-authorization/

### Reference Monitor (Anderson Report)

This is the OG paper. It was a study Anderson led for the U.S. Air Force, and it's one of the foundational documents of computer security as a discipline. The two-volume report laid out a research agenda that basically defined the field for the next two decades — it's where a lot of concepts that now feel like background furniture got their first rigorous statement.

There is no way to escape having some reference monitor — that's just Anderson's 1972 observation about tamperproof, always-invoked, verifiable enforcement. Microkernel design is precisely the project of making the reference monitor as small as possible.

Reference Monitor is thus:
1. Complete mediation (sometimes "always invoked") — it must be impossible to bypass; every access goes through it.
2. Tamperproof — it must be protected from unauthorized modification.
3. Verifiable — it must be small and simple enough that its correctness can be analyzed, ideally formally.

### All the way back to S&S

https://www.cs.virginia.edu/~evans/cs551/saltzer/ 

S&S actually argue against capabilities, in a soft way, by the end of section II-B. They identify three problems: revocation, propagation control, and review/audit. Their conclusion is that capabilities are great as a fast bottom layer but should be governed by an ACL system above them: "the most effective way of preserving some of the useful properties of capabilities is to limit their free copyability to the bottom most implementation layer of a computer system… The authorizations implemented by the capability system are then systematically maintained as an image of some higher level authorization description, usually some kind of an access control list system." This recommendation is enormously consequential — it's basically the design philosophy that won. Unix, Windows, POSIX, every mainstream OS until very recently is built this way. The whole ACL/identity-management world that Samonas is operating inside is downstream of this choice.

The ocap pushback is essentially: S&S identified real problems but drew the wrong conclusion. Modern ocap work argues that revocation has good answers (Redell's indirection, which S&S themselves describe! — that's the seed of the membrane pattern), propagation can be controlled by being careful about what references you hand out, and audit is recoverable through other means. Meanwhile, ACL systems have the confused deputy problem and ambient authority pathologies that ocap proponents argue are worse than what they "fix." Norm Hardy's "The Confused Deputy" (1988) is the canonical statement of this critique — and notice that the web version of the S&S paper you linked was apparently created by Norm Hardy himself, which is a nice piece of historical irony.

### SeL4

From [here](https://microkerneldude.org/2019/08/06/10-years-sel4-still-the-best-still-getting-better):
"Capabilities also cleanly solved another issue with original L4, that of limiting communication. The original model relied on an (inflexible) process hierarchy and redirection to a monitor process (“chief”) to limit data flow. Capabilities provide a cleaner, simpler and low-overhead model: Having a privilege does not in itself imply the ability to share that privilege, an additional grant right is needed to pass on capabilities."

The "verifiable" requirement was considered almost aspirational in 1972 — Anderson knew formal verification of real systems was beyond reach with the tools of the day. The seL4 verification in 2009 is, in a real sense, the first time anyone fully discharged Anderson's third requirement on a system intended for actual use. That's part of why the seL4 people are entitled to a bit of swagger about it.

### Lampson's "caps are cached ACL decisions"

From [this](https://arxiv.org/pdf/2011.02455):
An authorization policy is a function permissions(agent, resource), usually thought of as amatrix and stored as a set of triples. A small policy can be centralized, but usually it’s stored
- at the resource, listing the agents with permissions for it in an access control list (ACL), or
- at the agent, listing the resources for which it has permissions in a capability list.

Only ACLs work for managing the policy, because the manager’s question is, “Who has access tothis resource?” It’s okay to make short-term copies of parts of it into capabilities (usually calledfile descriptors), which are faster to check. Stating the policy using named sets of both agents andresources makes the manager’s job feasible.

### TLDR ocap vs reference monitor

I think the cleanest way to hold both views is this: caps and ACLs are dual representations, but they make different things easy to reason about. ACLs make administrative questions easy ("who has access?"). Caps make confinement and propagation questions easy ("what can this subject ever reach?"). For a multi-user file server, the administrative question dominates and ACLs win. For a separation kernel running mutually-suspicious components where you want a formal bound on blast radius, the propagation question dominates and caps win.

seL4 is squarely in the second camp — it's not trying to be a Unix replacement, it's trying to be the substrate for systems where you need provable confinement. In that setting, Lampson's "caps are cached ACL decisions" framing genuinely undersells what's happening, because the static structure of the cap graph is the thing being reasoned about, not any individual access decision.

But I'd resist the maximalist cap position too. The cap community spent a long time pretending revocation and administration weren't problems, and they are. Lampson's corrective is healthy. The right reading is probably: ACLs are the right interface for humans managing policy; caps are the right interface for programs enforcing it; and which one you put at the core of your system depends on which question you most need to answer rigorously.

## SVO Framework

Traditional Models (DAC/MAC/RBAC)
- DAC: "WHO (specific subject identity) can do WHAT (verbs) to WHICH resources (objects)"
- MAC: "WHO (subject's clearance level) can do WHAT to WHICH (object's classification level)"
    - but systems like SELinux are more sophisticated on the WHO, and use the full `user:role:type:level` to write filtering policies
- RBAC: "WHICH ROLES (groups of subjects) can do WHAT to WHICH resources"

These are fundamentally about "WHO" the subject is, with increasingly sophisticated ways of grouping and categorizing subjects.

Advanced Attribute Models (ABAC)
- ABAC: "GIGANTIC LIST OF ATTRIBUTES DESCRIBING SOMEONE"-VO

Capabilities
- Mostly about shifting left the cost of computing the ABAC (afaiu... see below)
- Supports Delegation-Centric Access Control (DCAC?)


![image](/assets/authorization-ocaps-vs-acl/access-control-models.png)

### MAC

Relationship between MAC and ABAC/RBAC might not be as simple as outlined in the diagram:
> A security context in a domain is defined by a domain security policy. In the Linux security module (LSM) in SELinux, the security context is an extended attribute. Type enforcement implementation is a prerequisite for MAC, and a first step before multilevel security (MLS) or its replacement multi categories security (MCS). It is a complement of role-based access control (RBAC).
> -- From [Type Enforcement](https://en.wikipedia.org/wiki/Type_enforcement) article

### ABAC

XACML and OPA's Rego seem to be the 2 main approaches.

https://axiomatics.com/wp-content/uploads/2024/10/the-ultimate-guide-to-choosing-the-right-authorization-language-whitepaper-axiomatics-10-16-2024.pdf 

### Capabilities

Capabilities *can* be thought of as a kind of ABAC, where each capability is an attribute in some sense. Think of a jwt token being sent using an "attribute" (the `Authorization: Bearer` header) of each API request.

Capabilities are about shifting authorization decisions "left" (earlier in the process) and effectively "compiling" the authorization decision into an unforgeable token. RBAC/ABAC requires heavy process everytime a user tries to access something.
- "Compile-time" authorization: The hard work happens when issuing the capability
- "Run-time" is just verification: Just verify the capability is valid and hasn't been revoked
- Optimization through pre-authorization: The decision is made once, encoded in the token
- Decentralized verification: The resource only needs to verify the capability is valid

Real-World Examples of This Pattern

- AWS Pre-signed URLs: AWS does the complex policy evaluation once, then creates a URL that grants specific access for a limited time - no further policy evaluation needed when using it
- OAuth 2.0 tokens (JWT?): Authorization servers do the heavy policy work once, then issue a scoped token that services can validate without re-evaluating complex user permissions
- Kubernetes Service Account tokens: The auth decision is "compiled" into a JWT with specific permissions, allowing services to access specific resources without re-authenticating
- Macaroons: Google's capability tokens that contain "caveats" (restrictions) and can be attenuated further without going back to a central authority

## Separation of Policy from Mechanism

Somehow it feels to me like capabilities violate the policy/mechanism separation. See the wiki [paragraph about physical vs card keys](https://en.wikipedia.org/wiki/Separation_of_mechanism_and_policy#Rationale_and_implications). I extended it with what seems like capabilities (separate key for each door).

![image](/assets/authorization-ocaps-vs-acl/keys-vs-cards.png)

The Evolution of Access Control
1. Physical Key (Policy + Mechanism Fused)
- The key's shape IS the policy
- No separation - the mechanism (lock pins) and policy (who can enter) are literally the same thing
- Simple but inflexible: changing policy requires changing locks

1. Card Key with ACL (Separated Policy/Mechanism)
- Mechanism: Card reader verifies identity
- Policy: Database decides access rights
- Clean separation allows dynamic policy updates
But requires online checks and centralized infrastructure

1. Smart Card with JWT/Capabilities (Distributed Policy Enforcement)
- High-level policy: "Who gets tokens and when do they expire?"
- Low-level policy: Embedded in the token itself
- Mechanism: Just cryptographic verification

You're absolutely right - it's like we've come full circle! The capability token is similar to a physical key in that it carries its own authorization, but with crucial improvements:
- Physical Key:  Policy = Key Shape (permanent)
- Capability:    Policy = Token Claims (temporal, revocable, contextual)

Modern capability systems add a temporal dimension to policies:
- Expiration times (token valid until X)
- Contextual constraints (only valid from certain IPs)
- Revocation lists (even unexpired tokens can be blacklisted)
- Refresh mechanisms (get new tokens without re-authentication)

It's like having a physical key that:
- Dissolves after 1 hour
- Only works during business hours
- Can be remotely deactivated
- Morphs its shape based on what door you're at

This hybrid approach gives us the simplicity of physical keys (bearer model) with the flexibility of database-driven policies (dynamic, contextual, temporal controls).


Also see this:
![image](/assets/authorization-ocaps-vs-acl/mechanism-policy-separation.png)

## Bearer Assets vs Identity Checks


There's multiple ways to look at this:
- [Object Capabilities](https://en.wikipedia.org/wiki/Object-capability_model) vs [Reference Monitor](https://en.wikipedia.org/wiki/Reference_monitor)
- [Access Control Matrix](https://en.wikipedia.org/wiki/Access_control_matrix): Capabilities vs ACL
- push vs pull
- bearer assets vs registered assets
- DID vs ID Registry (India's aadhaar)
- IBE vs access control

### Posession is Authorization

No external registry or identity check mediates access.

- Physical tokens of value
    - Casino chips
    - Gift cards / prepaid debit cards
    - Subway tokens / transit cards (pre-account era)
    - Arcade tokens
    - Postage stamps (unused)
    - Gold, gems, and other commodity money — value is intrinsic to the object
    - Lottery tickets
    - Money orders (before cashing)
- Physical tokens of access
    - Keys (house, car, padlock) — whoever holds the key opens the door
    - Coat check tickets / claim tickets
    - Locker keys
    - Safe deposit box keys (partially — bank also checks identity, but the key is the irreplaceable half)
- Computing & security
    - Bearer tokens (OAuth 2.0) — literally named after this concept
    - API keys / secret keys
    - Session cookies — the browser "holds" the cookie, the server trusts the holder
    - Pre-signed URLs (AWS S3, etc.) — anyone with the URL gets access
    - Capability URLs (e.g., "anyone with this link can edit" in Google Docs)
    - Macaroons (decentralized authorization credentials you can attenuate and pass along)
    - One-time passwords / TOTP seeds — possession of the seed is the identity
    - SSH private keys
- Historical / cultural
    - Signet rings / royal seals — pressing the seal was proof of authority
    - Letters of credit (historically, often bearer-like)
    - Tally sticks — medieval bearer debt instruments

Almost nothing is purely bearer anymore. Even cash has serial numbers. Crypto has a public ledger (pseudonymous but not anonymous). Gift cards have activation systems. The trend across every domain is the same one the Wikipedia article describes for bearer shares — registries creep in because bearer systems make theft, fraud, and regulatory enforcement hard. The interesting question is where on the spectrum something sits, not whether it's binary.

### Pros and Cons

ACL / identity-based systems have: 
- auditability ("who can access X?" — read the list) 
- policy expression ("all managers get access" — one rule)
- revocation (edit the list)
- centralized governance

They suffer from confused deputy because authority is ambient — the deputy acts based on who it is, not on a scoped token for this specific action.

Capability / bearer systems have:
- confused deputy immunity (authority is per-token, no ambient power to misuse)
- privacy (no central registry)
- easy delegation (hand over the token)
- attenuability (create sub-capabilities with reduced scope)

They suffer from: no revocation (can't un-give a token), delegation indistinguishable from theft, no auditability (who holds what?).

### ACL and Tokens Convergence

Capabilities adding revocation → you introduce an indirection layer: the token doesn't grant access directly, it points to a reference that can be invalidated. But that reference lives somewhere — a table mapping tokens to validity status. That table is a registry. You've reinvented the ACL's central lookup, just with an extra hop. Expiring tokens are the same — you need a clock authority and a check-on-use mechanism, which is a registry check.

Capabilities adding auditability → you need to answer "who holds what?" which requires tracking token holders. That's literally a registry of principals and their permissions — an ACL.

ACLs adding confused deputy protection → SCIF's approach: label every piece of data with its trust level, make all endorsement explicit, add runtime type checks at boundaries. But this is essentially scoping authority to specific operations and trust levels — which is converging toward the capability idea that authority should be per-action, not ambient. You're still identity-based, but the effective authority at any call site is narrow and explicit.

![image](/assets/authorization-ocaps-vs-acl/acl-vs-ocaps.png)

The punchline is that the patches each side applies to fix its weaknesses import the core mechanism of the other side:

When ACLs add SCIF-style information flow control, they're effectively saying "authority at this call site is scoped to exactly what was explicitly endorsed" — which is converging toward the capability idea that authority should travel with the specific action, not float ambiguously around the deputy's identity.

When capabilities add revocation via indirection, they're building a lookup table that says "is this token still valid?" — which is a registry. Add auditability ("who holds what?") and you're maintaining a list of principals and their permissions. Add policy-based distribution ("only managers get this capability") and you need an identity system to decide who's a manager. You've rebuilt an ACL with extra steps.

### Runtime vs Analysis Time

three enforcement mechanisms:
- Runtime monitoring — enforces safety trace properties. Access control, type checks, assertions, capability discipline. This is your first line of defense but it's fundamentally limited to "is this single step okay?"
- Static analysis — verifies hyperproperties by reasoning over all traces at once. IFC type systems, model checking, abstract interpretation. More powerful than runtime monitoring for security properties, but incomplete and limited to properties of the code (can't reason about the adversary's computational power).
- Cryptographic enforcement (eg. bearer token) — converts hyperproperties into trace properties by making distinguishing information computationally unavailable, then enforces the resulting trace property at runtime. This is the only mechanism that can enforce hyperproperties during execution rather than before it. But it depends on computational hardness assumptions, which static analysis doesn't need.

It's the difference between:
- "We proved no one can break in" (type system — verified the hyperproperty)
- "We're watching for break-ins" (runtime monitor — can catch trace-level violations but can't verify the hyperproperty)
- "There's nothing to steal" (capabilities — restructured the system so the attack is incoherent)

For trace properties, runtime monitoring is complete (so more powerful) while static analysis is only sound. For hyperproperties, static analysis can verify things runtime monitoring fundamentally can't. And capabilities sidestep the whole hierarchy by operating at the level of system design rather than system verification.


## Linux Sandboxing

From https://nikmav.blogspot.com/2015/06/software-isolation-in-linux_15.html :
1. fork() + setuid() + exec(): memory isolation (parent memory protected from child ONLY!)
2. chroot(): filesystem isolation
3. seccomp(): white/blacklist syscalls
4. prctl(): memory isolation (from other processes)
5. SELinux: centralized-policy administrative MAC tool for protecting OS resources (files, other processes, pipes, network interfaces etc) - policy written in m4 language
6. Namespaces: virtualize entire kernel subsystems (PID, IPC, NS, NET, etc) - blacklist based

See also https://apparmor.net/about/lsm_introduction/
![](/assets/authorization-ocaps-vs-acl/linux-security-mechanisms.png)

And the different security primitives have different user-friendly frontends:
![](/assets/authorization-ocaps-vs-acl/linux-security-frontends.png)

## Containers

"container" is defined by the contract (an image, a bundle, a lifecycle), never by the mechanism.

![image](/assets/authorization-ocaps-vs-acl/oci-stacks.png)

runc (namespaces), runsc (a userspace kernel), and kata-runtime (a VM) are interchangeable behind container

![image](/assets/authorization-ocaps-vs-acl/container-runtimes.png)



## References

- https://insights.sei.cmu.edu/blog/zero-trust-adoption-managing-risk-with-cybersecurity-engineering-and-adaptive-risk-assessment/
- https://nvlpubs.nist.gov/nistpubs/specialpublications/NIST.SP.800-207.pdf
- https://www.latacora.com/blog/2019/07/24/how-not-to/
- https://www.usenix.org/legacy/event/sec10/tech/full_papers/Watson.pdf
- https://arxiv.org/pdf/2509.10727
- https://microkerneldude.org/2019/08/06/10-years-sel4-still-the-best-still-getting-better
- https://arxiv.org/pdf/2011.02455
- https://trustworthy.systems/publications/nicta_full_text/8988.pdf
- https://www.cs.virginia.edu/~evans/cs551/saltzer/
- https://dl.acm.org/doi/10.1145/353323.353382
