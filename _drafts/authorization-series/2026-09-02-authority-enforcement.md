---
title:  "How authority is enforced: reference monitors and sandboxes"
series: "Authorization, Part 2"
series_url: "/programming/authorization-series-intro.html"
category: programming
date:   2026-09-02
---

> This is Part 2 of a four-part [series on authorization](/programming/authorization-series-intro.html).
>
> - **[Part 1: Authorization models](/programming/authorization-models.html)** — what every system computes, and who may change it.
> - **Part 2: How authority is enforced** — what makes any of it binding.
> - **[Part 3: Carriers](/programming/carriers.html)** — decisions that travel with the request.
> - **[Part 4: Capabilities](/programming/capabilities.html)** — authority you hold, not authority you are.

- [Who is the attacker](#who-is-the-attacker)
- [What is sandboxing](#what-is-sandboxing)
- [Theory](#theory)
  - [The reference monitor](#the-reference-monitor)
  - [Decide vs. enforce](#decide-vs-enforce)
  - [Along the path: four stages](#along-the-path-four-stages)
  - [Every stage has its own enforcer](#every-stage-has-its-own-enforcer)
  - [One enforcer, several stages](#one-enforcer-several-stages)
  - [Non-bypassability is a property of reach](#non-bypassability-is-a-property-of-reach)
  - [Which stage do you cut?](#which-stage-do-you-cut)
    - [Absence is a lookup that comes back empty](#absence-is-a-lookup-that-comes-back-empty)
  - [How to compare reference monitors](#how-to-compare-reference-monitors)
  - [What can change between check and use](#what-can-change-between-check-and-use)
  - [Composing reference monitors](#composing-reference-monitors)
- [Practice](#practice)
  - [Granularity, and the routes down](#granularity-and-the-routes-down)
  - [Built security-first: construction](#built-security-first-construction)
    - [seL4 as the meeting point](#sel4-as-the-meeting-point)
    - [WASI and effect systems](#wasi-and-effect-systems)
  - [Retrofitted onto ambient authority: subtraction](#retrofitted-onto-ambient-authority-subtraction)
    - [Linux is a toolkit, not a primitive](#linux-is-a-toolkit-not-a-primitive)
      - [Credentials: one stage, moving alone](#credentials-one-stage-moving-alone)
      - [LSMs: decide on the resolved object](#lsms-decide-on-the-resolved-object)
    - [Same interface, different enforcers](#same-interface-different-enforcers)
    - [Membranes: subtraction plus mediation](#membranes-subtraction-plus-mediation)
    - [Editing the object side](#editing-the-object-side)
  - [Composed: a Lambda function](#composed-a-lambda-function)
- [Conclusion: what this does not solve](#conclusion-what-this-does-not-solve)
- [References](#references)

[Part 1](/programming/authorization-models.html) read the decision as a database: stored facts, rules that derive a view, and checks that query it. A database enforces its own answers. It never returns a row nobody selected. An authorization answer is about an effect somewhere else, such as a file opened or a packet sent, and nothing in the store makes it hold. This article is about what does.

There are two ways. Something in the path of the effect applies the decision, or the path is not there at all. Either way, the claim is only as good as the attacker it holds against. So this article starts with the attacker, then with sandboxes, which use both ways.

## Who is the attacker

Every mechanism in this article exists to stop someone. A monitor in the path, a missing route, a filter on a syscall: each is a claim about an attacker. The same seccomp filter binds a program fed a hostile file, and means nothing to a kernel exploit. So "this is sandboxed" is not an answer until it says which attacker it was measured against.

Three attackers form a ladder, by how much of the machine they own:

1. **The attacker controls the input.** They write what the program reads: a file, a page, a request. The program's own code stays honest. This attacker defeats any check that relies on the program telling a request it should honor from one it should not.
2. **The attacker runs arbitrary code in the workload.** This defeats every cooperative convention: an `HTTP_PROXY` setting, a tool API, a policy a library enforces. Checks in the kernel still hold.
3. **The attacker owns the kernel.** Every check enforced inside that machine fails at once. Every fact the machine reports about itself becomes a claim rather than evidence.

Where a check runs sets the rung it survives. A check in the application falls at rung 2. A check in the guest kernel falls at rung 3. A check in the host, or at the resource server, survives all three.

Two more attackers sit off the ladder, and either one joins any rung of it:

- **Split the action.** The attacker spreads one intent across several requests, each allowed on its own. This defeats any monitor that judges one effect at a time, without defeating any single check. Only a monitor that remembers earlier requests can see it, and [Part 1](/programming/authorization-models.html#when-the-check-writes) covers those.
- **Edit the policy.** The attacker targets the policy itself: the matchers, the callbacks, the configuration. Policy arrives through the same supply chain as everything else.

So attacker strength is a partial order, not a line. A threat table with a single column mixes two questions. Rate each mechanism against the ladder, and you get the argument for stacking several: whatever falls at one rung needs something behind it that holds there.

## What is sandboxing

Sandboxing discussions usually start with the wrong noun. They ask whether untrusted code should run in a container, a microVM, gVisor, WASI, or a language runtime. Those choices answer *where computation happens*, not *what that computation can do*.

Start from the other end. What effects can the workload cause?

- Can it read host files?
- Can it mutate durable state?
- Can it reach the internet, localhost, or a metadata service?
- Can it exercise a credential?
- Can it publish an artifact that will execute later?
- Can it inspect or interfere with another workload?

Every one of these can be controlled at several points. A write to a repository might be prevented because the host path is absent, denied by an LSM, rejected by a filesystem provider, blocked by a tool hook, or refused by server-side branch protection. Those mechanisms are not interchangeable. They see different vocabularies and they live in different trust domains.

So a sandbox is best defined by what it constrains, not by how it is built:

> **A sandbox is an execution environment that restricts the effects a computation can have on the rest of the system.**

That definition is deliberately mechanism-free. It covers a VM, a seccomp filter, a WASI runtime, and a proxy, because all four exist to shrink the same set.

Note what that set holds. Most security writing treats data as the asset. Here the asset is **the authority to cause an effect**: a repository that can be force-pushed, a credential that can be spent, a table that can be dropped, a package that can be published. Reading a secret is one of these effects, not the one that organizes the rest.

That choice decides what you list. List data, and you protect stores. List effects, and you list every path by which the workload can cause each one. Only the second list can tell you whether an enforcer sits on all of them, which is the question [non-bypassability](#non-bypassability-is-a-property-of-reach) asks.

## Theory

### The reference monitor

The foundational statement is fifty years old. In 1972 James Anderson led a [study for the U.S. Air Force][computer-security-technology-planning] whose two volumes set the research agenda of computer security for two decades.

A reference monitor must be:

1. **Always invoked.** Every access goes through it. Usually called *complete mediation*.
2. **Tamperproof.** It is protected from modification by the subjects it controls.
3. **Verifiable.** Small and simple enough that its correctness can be analyzed, ideally formally.

```text
request
   ↓
Reference Monitor
   ↓
effect
```

There is no escaping this. Every mechanism in the rest of this article is a reference monitor placed somewhere, and every failure is one of the three properties not holding.

Anderson pictures one box on one path. Real systems break that box apart in two ways. The decision separates from its enforcement: a PEP applies what a PDP decides. And the path separates into stages, each with its own reference monitor, and Anderson's properties apply to every one of them. The next sections take the two splits in turn.

### Decide vs. enforce

"Reference monitor" names a function, not a component. In practice that function splits in two.

```text
request ──► PEP ──────► PDP
             ▲            │
             └────────────┘
                decision
```

- **PEP**, policy enforcement point. Sits in the path of the effect. Cannot be bypassed. Does what the decision says.
- **PDP**, policy decision point. Evaluates policy against facts and returns an answer. Need not be in the path at all.

The [series intro](/programming/authorization-series-intro.html) adds XACML's other two boxes: the PAP, where policy is authored, and the PIP, where facts come from. [Part 1](/programming/authorization-models.html) reads all four as a database. The distinction is logical. All four can be one kernel function, or four services in different datacenters. What matters is that only the PEP has to satisfy Anderson's first two properties. The PDP must be *correct*; the PEP must be *unavoidable*. Conflating them is how people end up with an authorization system that is beautifully expressive and trivially routed around.

The [Flask architecture][flask-security-architecture] is the cleanest instantiation, and the direct ancestor of SELinux. Flask separates **object managers**, which own resources and enforce decisions, from a **security server**, which evaluates policy. An object manager asks whether a subject may perform an operation on an object, caches the returned access vector, and — the part people forget — receives notifications when a policy change requires revoking what it cached.

That revocation channel is the honest cost of caching a decision. The cache makes enforcement fast, and the notification channel is what you owe in exchange. [Part 3](/programming/carriers.html#fresh-or-frozen) follows that trade through every kind of carrier.

### Along the path: four stages

Every mechanism in the rest of this article sits somewhere on one path. The [series intro](/programming/authorization-series-intro.html#from-a-chain-to-a-grid) splits that path into four stages: designate, reach, authenticate and decide. Designate has a written half, *acquire*: how the subject came to hold the name in the first place.

Each stage is a function, and each one can come back empty:

```text
designate      resolve(namespace, name)   → object  | ⊥
reach          route(source, address)     → path    | ⊥
authenticate   verify(claim, proof)       → subject | ⊥
decide         f(s, a, r, ctx)            → allow   | deny
```

A *namespace* here is what Saltzer calls a context: a set of bindings from names to objects. This series keeps the word *context* for the fourth argument of `f`.

Authenticate is the one stage this article leaves alone. What makes it binding is custody of a key, which is a question for cryptography rather than for a sandbox.

This article asks what makes each stage hold. [Part 4](/programming/capabilities.html#two-bindings-collapse-the-stages) asks the other question: which artifact carries each stage, and what changes when one artifact carries them all. Cut one, and the request fails in a way that tells you which:

| Cut | What the request sees | Example |
|---|---|---|
| acquire | nothing; there was never a name to try | no FD was passed; the URL cannot be guessed |
| designate | the name resolves to nothing, or to something else | `ENOENT` inside a chroot; `NXDOMAIN` |
| reach | the name resolves, and delivery fails | `ENETUNREACH` in an empty network namespace; a timeout |
| decide | the request arrives, and the answer is no | `EACCES`; HTTP 403 |

The object a name resolves to is often a lower-level name. DNS resolves a host to an IP address, and the address is what reach routes. [RFC 1498][rfc1498] chains these bindings: service to node, node to attachment point, attachment point to path. So designate and reach are one pair that repeats at every layer. A URL is a host, resolved by DNS and reached over IP, plus a path, resolved and reached again inside the server. Day's [RINA][networking-is-ipc-paper] goes further and repeats all four stages in every layer, each with its own enforcer. Each layer's reach calls designate in the layer below: to get a packet to the next hop, a layer asks the one below for a flow to that hop's name. The [series intro](/programming/authorization-series-intro.html#from-a-chain-to-a-grid) reads the grid this way.

### Every stage has its own enforcer

Enforcement is not a fifth stage. It is a row under every stage, and the enforcer means something different on each: control over how names are obtained, the resolver, whatever can deny a path, the check. The PEP is only the last of these. Five systems, by who enforces each stage:

| | Pathname + ACL | OAuth bearer token | Capability URL | Capsicum FD | Object capability |
|---|---|---|---|---|---|
| **Acquire** | nobody; strings are free | nobody for the URL; the authorization server for the token | unguessability | kernel | runtime or kernel |
| **Designate** | kernel path walk | DNS + the server's router | DNS + the server's router | kernel FD table | runtime or kernel |
| **Reach** | nobody; `open` is always callable | the network, limited only by firewalls | the network, limited only by firewalls | kernel FD table | runtime or kernel |
| **Decide** | kernel ACL check | resource server | server checks the secret | kernel rights check | runtime or kernel |

The Capsicum column says "kernel" four times. The capability URL column names four parties, and one of them is nobody. Plain Unix descriptors differ from Capsicum only in the first row: the first descriptor comes from opening a path, on ambient authority, and `cap_enter()` removes that route.

On reach, what *provides* the path is rarely what *limits* it. The network carries a request to any URL; only a firewall, an egress proxy or a network namespace can refuse. On the open internet nothing refuses, which is what it means for reach to be ambient.

Separated stages mean several enforcers, often in different trust domains, and the classic bugs live in the gaps between them. The confused deputy is decide enforced by the kernel and designate enforced by no one: Hardy's compiler was handed a pathname, and nothing tied that name to the authority of whoever supplied it. A check-then-use race is designate resolved twice while decide is checked once. A Capsicum descriptor closes the gaps, because one artifact carries every stage and one component enforces them all. [Part 4](/programming/capabilities.html#two-bindings-collapse-the-stages) calls that *collapse*.

Anderson's three properties therefore apply per stage. A PEP that is always invoked on decide does nothing about a name that resolves somewhere else, or a route that goes around it. And collapse does not make the reference enforce itself. Whoever owns the table does, which is why seL4, further down, is both the purest capability system in this article and the most thoroughly enforced.

### One enforcer, several stages

The table above counts enforcers per stage. One component can also enforce several stages. A service-mesh sidecar is the pod's only route out, because iptables sends every connection through it, so it enforces reach. It checks the peer's mTLS certificate, which is authenticate. And it evaluates an authorization policy, which is decide.

That gives a second axis. An artifact can carry one binding or several, and an enforcer can hold one stage or several:

| | separate enforcers | one enforcer, several stages |
|---|---|---|
| **separate bindings** | pathname + ACL; OAuth bearer token | service-mesh sidecar |
| **one artifact, several bindings** | share link; presigned URL | Capsicum FD; seL4; object capabilities |

The two corners off the diagonal show why both halves matter. A share link joins name and authority in one string, but DNS, the network and the server still enforce apart. Nothing enforces reach, so the link works for anyone who learns it. A sidecar closes the gaps between enforcers, but the workload still speaks global names and presents an ambient identity, so a confused deputy is still possible inside the policy the sidecar enforces. A collapsed artifact needs a collapsed enforcer behind it: a descriptor index means something only because one kernel owns the table it indexes. A gateway that starts from the sidecar's shape, but hands the workload handles instead of global names, moves to the bottom-right corner.

[Part 4](/programming/capabilities.html#two-bindings-collapse-the-stages) draws the same split from the artifact's side, as global names against local ones. The two views agree because a local name is one that a single enforcer resolves, routes and checks: the right-hand column there is the right-hand column here.

Collapse has a price. One enforcer across every stage leaves no gaps, and it leaves one thing to verify. That is the seL4 argument below. But one failure then opens every stage at once, and the enforcer's own authority is large. Separate enforcers in separate trust domains fail independently. The Lambda example at the end of this article relies on that: the IAM check at the resource holds even after a total escape from the guest.

### Non-bypassability is a property of reach

Applied per stage, Anderson's first property becomes a question about topology. A check that is always invoked on one path does nothing if the workload can reach the resource by another. No policy language or hook can settle that. Only the shape of reach can: is there some other path to the protected resource?

Stated as a condition to satisfy:

> **For every effect the workload can attempt, either no path to the resource exists, or every path passes through a point that decides.**

The condition has two ways to hold, and they are the two strategies of the next section. The first involves no enforcement point at all: a missing path is not a check that reliably says no, it is the absence of anything to check. So "is there a PEP?" is never the interesting question. A PEP is always a PEP for some class of effect, and what you have to establish is that the union of them leaves no path uncovered.

The humble proxy shows it best. `HTTP_PROXY` is a cooperative convention. A workload that wants to ignore it simply ignores it, and no policy inside the proxy changes that. The same proxy becomes genuine enforcement when reach closes: force routing with nftables or TPROXY, or give the workload a network peer that is the proxy, with no NAT and no alternate route.

Same code, same policies, same expressivity. Enforcement in one deployment and decoration in the other. This is why arguing about policy languages before establishing the topology is almost always wasted effort.

### Which stage do you cut?

Almost every argument about sandboxing is an argument about which half of that condition is in use. The two halves are two strategies:

```text
ABSENCE                               JUDGMENT

no path to the resource exists        every path passes a point
                                      that decides

the resource is absent from           the request is expressible,
the reachable universe                it arrives, and something
                                      judges it

"there is nothing to ask for"         "you asked; the answer is no"
```

They are not tied to stages. Each stage is one of the functions above, and each can be enforced either way, except decide, which is a judgment by definition:

| | absence | judgment |
|---|---|---|
| **designate** | `chroot`, mount namespace | a resolver that refuses names by policy |
| **reach** | no route; a VM with no device | firewall, seccomp, egress allowlist |
| **decide** | — | ACL, LSM, a PEP at the resource |

These are functions, not technology categories, and most mechanisms cut exactly one stage, by one strategy:

| Mechanism | Stage it cuts | Strategy | Seen from inside |
|---|---|---|---|
| WASI import not supplied, Capsicum `cap_enter()` | acquire | absence | no name to try |
| `chroot`, mount namespace | designate | absence | `ENOENT`, or a different file |
| network namespace, missing route | reach | absence | `ENETUNREACH` |
| VM | designate and reach, for the whole host | absence | host names mean nothing; no device |
| seccomp | reach, per kernel entry point | judgment | `EPERM`, `ENOSYS`, or the process dies |
| firewall, egress allowlist | reach, per destination | judgment | a refused or dropped connection |
| LSM, Landlock | decide, on the resolved object | judgment | `EACCES` |
| `setpriv` credentials | decide, on the subject side | judgment | `EACCES` |
| ACL at the resource, branch protection | decide, on the object side | judgment | `EACCES`, HTTP 403 |

Seccomp is the one people misplace, and they misplace it twice. It is a judge: the call is expressible, it arrives at a filter, and a policy says no. And it judges reach, not the object. It sees which kernel entry point a process is trying and the call's scalar arguments, never the object the call would resolve to. That is the difference from an LSM, which judges after designate has run.

#### Absence is a lookup that comes back empty

Formally, the two strategies are one. Every function above is a lookup, and absence is a lookup that returns ⊥. A `chroot` is a resolver with fewer bindings in its table. A network namespace with no route is a routing table that returns ⊥ for every destination. Even an ACL check fits: [Part 1](/programming/authorization-models.html#one-function-one-relation) asks "is this row present?", so a deny is a missing row.

What separates the strategies is whose table the lookup reads. Under absence, each subject has its own namespace, holding only the bindings it was granted, and ⊥ means the name means nothing here. Under judgment, everyone shares one namespace of global names, and a policy filters it: the name means something, and you may not use it. That is Part 4's split between local and global names, seen from the enforcer's side.

Three consequences follow, and they are why the distinction is worth keeping:

- **New objects.** A per-subject namespace binds only what someone put in it, so a file created tomorrow is absent by default. A filter over a shared namespace has to classify every new name, and a denylist misses the syscall added next year.
- **What leaks.** A no confirms that the object exists, and ⊥ says nothing. That is why GitHub answers 404, not 403, for a private repository you cannot see: a judge dressed as an absence. Seccomp can do the same by returning `ENOSYS`, so what the workload sees is not the test.
- **What can fail.** A judge runs policy code on every request, and that code can be wrong or broken. XACML even has a decision for it, *Indeterminate*, which [Part 1](/programming/authorization-models.html#policies-compose-and-the-rule-is-not-the-same-as-the-edit-right) covers. Absence is computed by the ordinary resolver, which has to work anyway. Its risk moves to setup: was the namespace built right?

The strongest designs cut two stages at once. The workload never acquires the real GitHub token. It holds a placeholder handle that reaches only a gateway, and the gateway authorizes only approved operations. That is *authority attenuation* — possession of a powerful resource replaced by permission to request a smaller set of effects.

### How to compare reference monitors

Knowing which stage a mechanism cuts, and that nothing goes around it, still leaves mechanisms on the same stage far apart. An LSM and a host-side HTTP gateway both cut decide. "Policy expressivity" is the usual word for how they differ, and it collapses three independent questions.

**1. Legibility — what vocabulary crosses the boundary?**

```text
more semantic
    agent intent and tool calls
    Git operations and SQL statements
    HTTP methods, paths, headers, bodies
    filesystem paths, inodes, operations
    IP addresses, ports, flows
    block offsets and Ethernet frames
more structural
```

**2. Programmability — what may policy do there?**

```text
fixed behavior
static allow/deny configuration
declarative subject × object relations
programmable decisions
stateful policy and external approval
transformation, emulation, resource synthesis
```

**3. Trust placement — who executes the decision?**

```text
application or harness
guest process
guest kernel
host process or host kernel
hypervisor
remote resource server
```

![image](/assets/authority-enforcement/legibility-vs-programmability.png)

These vary independently. An LSM is structurally legible, weakly programmable, and trusted only as far as the guest kernel. A JavaScript callback in a host proxy is semantically legible, arbitrarily programmable, and survives a compromised guest. Neither dominates; they protect different boundaries. Trust placement is also what sets the rung a monitor survives on the [attacker ladder](#who-is-the-attacker).

Non-bypassability is none of the three. It belongs to reach, and an earlier section already asked it.

### What can change between check and use

Always invoked, tamperproof, verifiable. All three can hold and the monitor can still authorize the wrong thing, because none of them says the decision was still true when the effect happened. Separated stages resolve at separate moments, and almost nothing in an authorization question is supplied directly. The subject and the object arrive as *references*, and each resolves against state somebody else can modify.

```text
subject reference ──resolve──► subject state ──┐
                                               │
object reference  ──resolve──► object state ───┤
                                               ├──► decision
policy store      ──query──────────────────────┤
                                               │
environment       ─────────────────────────────┘
```

Four inputs, four independent clocks. They are the four terms of the function [Part 1](/programming/authorization-models.html) started from — `f(subject, action, resource, context)` — and three of them arrive as references that resolve late. The action does not. It is supplied literally in the request, which makes it the only argument that cannot go stale, and the only one nobody writes a CVE about.

**Object binding.** The classic case, and the reason the LSM hook, below, sits where it does. A pathname gets resolved twice:

```text
t0   access("/tmp/foo")  →  inode A   → allowed
t1   open("/tmp/foo")    →  inode B
```

Check and use named the same string and reached different objects: designate ran twice, decide ran once. A file descriptor closes this by resolving once and binding the result — `read(7)` cannot be redirected by renaming anything. That is what `openat`, `O_PATH` and Capsicum are for. It is designate and authorize collapsing, seen as a race.

**Subject binding.** The same indirection exists on the other side and gets far less attention. A pathname is an indirect reference to an object; an ambient credential is an indirect reference to authority, resolved at the moment of use. Check under one credential context and act under another — a dropped privilege, a changed EUID, a recycled thread pool — and you have the same bug with the roles swapped. Setting the credentials once, from outside, before the workload starts is what `setpriv` buys: the program never holds authority it would have had to remember to drop.

**Authorization state.** Neither binding has to move for the answer to change. Remove Alice from a group and every decision derived from that membership is stale, with the same subject and the same object throughout. This is not a race inside the monitor. It is the monitor's inputs having a lifetime, which is exactly why Flask needs a revocation channel: a cached access vector is a decision that outlived its premises.

**Environment.** Device posture, time of day, risk score. Same shape as the others, least often modelled, and the usual reason a "zero trust" deployment is less continuous than its diagram.

**Approval.** A human approval is authorization state written for one request, and it has the tightest binding of all. It has to bind to exactly what the human saw: the action, the target, the arguments and the version of the object. If any of them changes before the effect, the [approval no longer applies][ai-engineer-security]. An approval bound only to the tool name is a check on one request and a use on another.

Re-evaluate on every operation and the inputs stay fresh, but every operation pays the resolution cost and re-opens all four races. Materialize the decision into a token, a descriptor or a capability, and the bindings freeze — that is the point of it — but a frozen binding is indistinguishable from a stale one once the source of truth moves.

```text
re-evaluate    fresh inputs, repeated resolution races
materialize    stable bindings, revocation debt
```

Neither end is safe on its own. A file descriptor eliminates the object-binding race and creates a revocation problem in the same stroke. That is not a defect in the mechanism. It is the trade that appears wherever a system caches a derived fact, and authorization gets no exemption from it. [Part 3](/programming/carriers.html) follows it once the copy leaves the machine.

### Composing reference monitors

The mechanisms above are not alternatives. A Wasm component runs inside a Linux guest constrained by an LSM. The guest presents an attenuated handle to a host broker. The broker uses a scoped OAuth token against a service whose own policy protects the resource.

At every boundary, ask the same questions, one per stage plus three more:

1. What computation is inside the boundary?
2. **Acquire.** Which names can it obtain, and from whom?
3. **Designate.** What do those names resolve to, and who resolves them?
4. **Reach.** Which paths leave the boundary, and does every one pass an enforcer?
5. **Decide.** Who decides, in what vocabulary?
6. What is the enforcer's own maximum authority if its policy is wrong?
7. Which inputs does this enforcer share with the others?

Question four is Anderson's first property. Question six is the one people skip, and it is the one that decides how bad your worst day is. Question seven decides whether stacking monitors buys anything. Monitors that trust the same claim fail together: a gateway, a sandbox and an audit system can [all trust the same wrong tenant ID][ai-engineer-security].

## Practice

### Granularity, and the routes down

There is a dimension the access matrix cannot see at all: how small is the thing that holds authority? Karp draws it as a ladder.

![image](/assets/authorization/pola-granularity.png)

*Finer-grained least authority is safer. Karp's ladder, with the systems that reached each rung. Each rung is a size of principal: the thing that holds authority.*

Keep that scale apart from a second one: how fine the *decision* is. A decision can be fine while the principal stays coarse. The [AuthZEN interop][authzen-interop] Todo scenario shows both on one request path:

![An API gateway and the Todo backend each call an AuthZEN PDP, at medium and fine granularity](/assets/authorization/authzen-interop-granularity.png)

*The AuthZEN interop Todo scenario, from [authzen-interop.net][authzen-interop].*

The API gateway asks its PDP about an HTTP method and a route. The middleware in the backend asks about a `can_*_todo` action on one todo, with the todo's owner as a property. The principal is the same user both times, the `sub` of the JWT. The second decision is finer because its PEP sits where the resource has a meaning: only the application knows that this route names this todo, owned by that user. Fine decisions need nothing more than a PEP in the right place and a PDP that can answer.

The ladder measures the other scale, and three routes lead down it. Conflating them causes real confusion, because sandboxes, containers, seccomp and LSMs plainly do get below the user, and none of them are capability systems.

**Subtraction from outside.** Someone authors a policy, in a global namespace, naming a subject. SELinux type enforcement is an access matrix whose subjects are types rather than users; a seccomp profile is a list keyed to a process; a container is a namespace configuration. These are the access matrix of [Part 1](/programming/authorization-models.html) with a finer principal. Authority inside the box remains completely ambient: within a container, `open("/etc/passwd")` still works by name and still succeeds because of who you are.

**Adjudication from inside.** The program asks a decision point itself, about a principal finer than the user: the module that is calling, the tool invocation, the request. Java's stack inspection did this inside one process, checking the protection domain of every caller on the stack before a sensitive operation. It holds as long as every path through the code asks.

**Construction from inside.** The reference *is* the grant. Nothing is authored, because a per-instance, per-argument, per-call grant is just the reference that was passed.

The first route costs a policy artifact per descent, written in a vocabulary the program does not itself use — paths, types, syscall numbers, labels. The cost grows as the box shrinks, which is why nobody writes a fresh seccomp profile per request. And it bottoms out: you cannot write an LSM policy about which objects inside a process may invoke which methods, because at that granularity the policy author would be rewriting the program. Every system on the bottom two rungs is a language or a runtime rather than a supervisor, and that is not a coincidence.

The two inside routes both need the program's cooperation. It has to call the decision point, or accept a reference instead of opening a path. They differ in what happens when it does not. A program that forgets to ask still holds the authority, so the check was advisory, and every code path that skips it reaches everything. A program that was never handed a reference has nothing to misuse. Adjudication makes the correct answer expressible, and construction makes the wrong one unrepresentable. [Part 4](/programming/capabilities.html#the-convergence-is-not-symmetric) comes back to that asymmetry.

Granularity is independent of the [grid's stages](/programming/authorization-series-intro.html#from-a-chain-to-a-grid), and the rest of the series keeps them apart. A container is fine-grained and fully ambient: the principal is small, and inside it every name still works because of who you are. `chroot` cuts designate while leaving decide ambient over everything still visible, so it narrows what can be named without joining any name to its authority.

Some systems were designed security-first, and those tend to start from capabilities: nothing is ambient, and authority grows only by passing references. Most systems were not. Linux, Windows and the internet all started from ambient authority, and sandboxing them means taking authority away from code that was written to assume it.

Both kinds of system try to make a subject's row in the access matrix small. They differ in which part of the picture they edit.

```text
subtraction    the row starts full and the columns get cut away
construction   the row starts empty and grows by reference-passing
```

Subtraction is an outside configurator removing names and routes before the process starts. Construction grows the row only through [Miller's][robust-composition] loop — new names arrive over channels already held — and no step can hand on more than it holds. The reason both exist is that construction asks the program to cooperate — to accept a reference instead of opening a path — and most programs were not written to. Subtraction asks the program for nothing, which is why it is what you reach for when you did not write the binary.

Each system below is a reference monitor broken apart in its own way. For each one, ask which stages it cuts, who enforces each stage, and where that enforcer's trust sits.

### Built security-first: construction

#### seL4 as the meeting point

seL4 makes two claims about capabilities. The first is about representation: the capability graph can *be* the authority, with no authoritative copy elsewhere, and [Part 3](/programming/carriers.html#local-authority-versus-global-knowledge) takes it up. The second is about enforcement, and it belongs here.

seL4 stores capabilities in kernel objects called CNodes. Userspace never touches a capability directly; it names a slot, and the kernel dereferences it. Designate, reach and decide are one capability, and one kernel enforces all three. All authority — memory, execution, IPC endpoints, interrupts — is a capability, obtained by retyping untyped memory. There is no ambient authority anywhere in the system, including the ability to allocate.

That leaves acquire, and two mechanisms govern it.

**The grant right.** Holding a capability does not imply the ability to share it. Passing a capability over an endpoint requires the `grant` right on that endpoint. From the [seL4 retrospective][10-years-sel4]:

> Capabilities also cleanly solved another issue with original L4, that of limiting communication. The original model relied on an (inflexible) process hierarchy and redirection to a monitor process ("chief") to limit data flow. Capabilities provide a cleaner, simpler and low-overhead model: Having a privilege does not in itself imply the ability to share that privilege, an additional grant right is needed to pass on capabilities.

Saltzer and Schroeder objected that nobody can control where a capability gets passed. The grant right answers that structurally, rather than with a registry. [Part 4](/programming/capabilities.html#the-three-objections) takes their objections in turn.

**The capability derivation tree.** The kernel tracks which capabilities were derived from which, and `seL4_CNode_Revoke` removes all descendants of a capability in one operation. That answers their objection about revocation, without indirection and without a lookup table, because the kernel already holds the provenance.

And the kernel is the verified one. Every stage collapses into one component, and that component discharges Anderson's third property. That is what collapse buys at the enforcement layer: one monitor to verify, instead of four that must agree.

Anderson's third property was close to aspirational when he wrote it. Formal verification of a real system was out of reach with 1972 tooling. Microkernel design is the project of shrinking the monitor until verification becomes achievable, and seL4's proof in 2009 was, in a meaningful sense, the first time anyone discharged the property on a system meant for actual use. That is most of the reason the seL4 people are entitled to their swagger.

> **Capabilities describe authority structurally. A trusted, verified reference monitor makes that structure non-bypassable.**

Policy and mechanism stay separate. seL4 enforces whatever capability graph exists. Which graph *should* exist is a design question outside the kernel, usually settled in a static configuration before boot.

#### WASI and effect systems

**WebAssembly and WASI** are the cleanest modern instance of absence followed by judged reintroduction. A Wasm module starts with linear memory and computation. It acquires no ambient filesystem, network, environment, or clock. Everything useful arrives as an import the host chose to supply.

```text
Wasm module
    → imported WASI operation
        → host runtime
            → selected filesystem, socket, clock, or service
```

There is no syscall instruction to perform, so reach to the host kernel does not exist. Absence comes free from the execution semantics rather than from a device model someone had to get right. The vocabulary is legible — `open-at` means far more than a block offset — and the import list is a local audit surface, which [Part 4](/programming/capabilities.html#complete-over-the-intended-state-not-the-reachable-state) weighs against a global one.

**Effect systems** reach the same shape from the language side. The type system records each effect a function may perform, and a handler supplies its interpretation:

```text
computation requests Network.send
    → handler may execute, deny, record, transform, or emulate it
```

That is the top of the programmability ladder, at the most semantic legibility available anywhere. But it is confinement only when the language and runtime together guarantee that every relevant effect is captured. Otherwise native code, FFI, `unsafe`, or a compromised runtime walks straight past the handler — Anderson's first property, restated for a compiler.

The transferable lesson is not "adopt an effect language". It is that interfaces get easier to govern when the effect is named at the level policy cares about. `publishArtifact` is a better policy event than a sequence of writes and HTTP requests, but only if the lower-level routes cannot reach the same outcome.

### Retrofitted onto ambient authority: subtraction

Everything else starts from ambient authority and takes it away, one stage at a time.

#### Linux is a toolkit, not a primitive

Linux has no single sandbox primitive. It has a collection of mechanisms, each cutting one stage for one class of kernel object, and every real sandbox is a composition of them.

![](/assets/authority-enforcement/linux-security-mechanisms.png)

The mechanism table above placed most of them. Namespaces cut designate or reach by absence, one kernel subsystem at a time. Seccomp cuts reach to kernel entry points by judgment. Credentials and LSMs both cut decide, from different ends, and deserve a closer look.

##### Credentials: one stage, moving alone

`fork()`, `setuid()` and `exec()` are the oldest sandbox on the list, and [`setpriv`][setpriv] is where they become usable. One `exec` sets the uid and gid, clears supplementary groups, trims the inheritable, ambient and bounding capability sets, locks securebits, requests an LSM label, and sets `no_new_privs`: the whole credential tuple, chosen by the launcher rather than the program. Hand-rolling it is a bug farm of unchecked `setuid` returns, leftover groups, and bounding sets trimmed too late.

`no_new_privs` is the load-bearing bit. Without it the restriction is not monotonic — exec a setuid binary and the authority comes back — and an unprivileged process cannot install a seccomp filter at all. It is the precondition for every restriction a workload applies to itself.

Credentials are also the cleanest case of one stage moving alone. They are ambient authority and nothing else. Shrink them and every name still resolves — `open("/etc/shadow")` stays a perfectly expressible request — and only the answer changes. No namespace, no label, no hook, no absence. Decide cut while acquire, designate and reach stay exactly as ambient as they were.

The vocabulary collides here, and the collision is worth naming. A Linux *ambient capability* is authority that survives `exec` with nobody designating anything, which is ambient authority in this series' sense. `--ambient-caps` is the knob that grants it, and `no_cap_ambient_raise` is the securebit that takes the knob away.

##### LSMs: decide on the resolved object

The LSM framework is Flask brought into Linux, and it sits at a specific and well-chosen place. Rather than interposing at syscall entry, the kernel first resolves user-supplied names and handles into internal objects, *then* calls the hook immediately before the security-relevant operation. The question it asks is explicit:

```text
May subject S perform operation OP on kernel object OBJ?
```

That is the difference from seccomp. Seccomp sits on reach and sees a syscall number and scalar arguments; it cannot dereference a pathname pointer or reason about the resolved inode. An LSM sits on decide, after designate has run, and sees the object and the kernel context that produced it, whichever syscall got there.

Where the hook sits has a direct consequence for policy soundness. Path-based policy has to account for symlinks, hard links, rename, bind mounts, already-open handles, and the gap between a directory entry and an inode — every way designate can resolve one object under many names. Label-based policy attached to kernel objects sidesteps much of that aliasing, at the cost of policies that map less directly onto how people describe a workspace. Neither choice is free.

![](/assets/authority-enforcement/linux-security-frontends.png)

The same primitives wear different user-facing clothes, which is much of why the landscape looks more fragmented than it is. Read the credentials row twice. Every supervisor on the chart reimplements `setpriv`: the OCI `process` block is its flag list as JSON, systemd spells it `User=`, `CapabilityBoundingSet=`, `AmbientCapabilities=` and `NoNewPrivileges=`, and Chrome's zygote drops to an unprivileged uid and sets `no_new_privs` before installing its filter. No other row is driven by all of them.

#### Same interface, different enforcers

Containers show the per-stage enforcers better than any argument. A "container" is defined by a contract — an image, a bundle, a lifecycle — and never by a mechanism.

![image](/assets/authority-enforcement/oci-stacks.png)

The contract fixes the names the workload sees: its paths, its ports, its process IDs. It says nothing about who enforces reach and decide behind those names. The runtime decides that:

```text
container contract
       │
       ├── runc    → the host kernel: namespaces, cgroups, seccomp, LSM
       ├── runsc   → gVisor: a userspace kernel answers the syscalls
       └── kata    → a hypervisor, with a guest kernel inside a VM
```

![image](/assets/authority-enforcement/container-runtimes.png)

Same names, three different enforcers. Under runc, the workload talks straight to the host kernel, so a reachable kernel bug is an escape. Under gVisor, it talks to a userspace kernel, and the host kernel sees a much smaller surface. Under Kata, the hypervisor is what the workload must defeat. These are interchangeable to the consumer and not remotely comparable as boundaries. "We run it in a container" names the interface, not the enforcer.

This is the separation of policy from mechanism, one level down. [Part 3](/programming/carriers.html#policy-and-mechanism) takes it up for carriers. The contract is what the workload may assume about its environment. The runtime is who makes it true. Keeping the seam there is what lets you change your mind about isolation strength without repackaging anything.

#### Membranes: subtraction plus mediation

Subtraction cannot mediate. You can remove a column. There is no namespace operation for "Alice reaches X only through Bob," because the thing in the middle has to hold a row and be a column at once, and a namespace has visibility rather than entities. [Part 4](/programming/capabilities.html#the-six-properties) calls this Property E: resources are also subjects.

> **Subtraction plus mediation is construction.**

The moment removal is not enough and you need to interpose, you introduce something that holds the real authority and speaks a protocol: a FUSE daemon, a proxy inside the network namespace, a broker. That thing is a membrane. Its clients acquire only what it hands them, over the one channel they have to it, so the loop holds again. You have rebuilt the capability system one resource class at a time.

Without the membrane, subtraction stays subtraction. `chroot` cuts designate for everything outside the jail and leaves every stage ambient inside it, which is why it is not a capability system. Absence becomes capability discipline only when the name you hold is the only way to reach the object, and the only way to get more names.

The membrane pattern is old, and the systems that use it at scale describe themselves in exactly these terms.

**Chromium's broker.** Chromium's [sandbox][chromium-sandbox] splits the browser into a *broker* and its *targets*. A renderer target runs under a token that denies it almost everything: every group deny-only, no privileges, untrusted integrity, a job object, a desktop of its own. That is subtraction, cutting decide for nearly every OS object. The broker is the browser process, "a privileged controller/supervisor of the activities of the sandboxed processes." It evaluates policy, and "the policy-allowed calls are then executed by the broker and the results returned to the target process via the same IPC." The design doc puts the acquire axis in plain words:

> The Chromium renderer runs with this token, which means that almost all resources that the renderer process uses have been acquired by the Browser and their handles duplicated into the renderer process.

The target acquires only what the broker hands it, over the one channel it has. That is construction, rebuilt on top of Windows. The doc is just as plain about where enforcement is *not*. The hooks that forward Win32 calls to the broker are for convenience: "The interception + IPC mechanism does not provide security; it is designed to provide compatibility when code inside the sandbox cannot be modified to cope with sandbox restrictions." The token is the cut. The hook is `HTTP_PROXY` at the Win32 layer.

**Google's safe proxies.** [*Building Secure and Reliable Systems*][bsrs-safe-proxies] describes the same shape for people. "Engineers are not able to run arbitrary commands directly on servers; they need to contact the Tool Proxy instead." That cuts reach. The proxy then authorizes each command against an access list, can require multi-party approval, rate-limits changes so a restart rolls out gradually, and logs every operation — judgment, in the legible vocabulary of whole commands rather than packets. The chapter is candid about the cost, and lists among the downsides "a central machine that an adversary could take control of." That is the last question of the composition checklist, asked of a real system: what can the enforcer do if its policy is wrong?

A capability gateway in front of an AI agent is the same membrane.

#### Editing the object side

Every mechanism above edits the subject. The matrix has two projections, and the other one is just as mutable. `setfacl` on a file, `chcon` on its label, `GRANT` and `REVOKE` in a database, an ACE for a package SID on a Windows object, a bucket policy, a protected branch. None of it touches the workload. Its authority shrinks anyway.

Sandboxes almost never work this way. Confining a workload means denying everything except a few things, and on the object side "everything" is unbounded: a file created after you ran `setfacl` carries whatever the default gives it, and nothing covers objects that do not exist yet. Each edit is also global. Lock one workload out of `/etc/passwd` by editing `/etc/passwd` and you break every other reader, so the move is only safe once the workload holds a principal nobody else shares — a subject-side act. And object state is durable. Credentials cost nothing per `exec`; you cannot relabel a filesystem per tool call.

Two things the object side buys that nothing else does. An ACL hangs on the inode, so hard links, renames and bind mounts cannot walk around it. And it holds after a total escape. Branch protection refuses the force-push whether it came from the sandbox, from a process that broke out of it, or from a laptop in another country. Every other mechanism in this article stops working the moment its boundary fails. Policy at the resource has no boundary to fail.

One trap comes with it. Unix checks permission at `open`, so `chmod 000` does nothing to a descriptor somebody already holds. Object-side edits bind at the next resolution, never retroactively, which is the check-and-use problem in miniature.

### Composed: a Lambda function

AWS Lambda runs each function inside a [Firecracker][firecracker-design] microVM. Follow one function's request to S3 and it crosses four reference monitors, each answering the composition checklist for its own boundary.

```text
function code
  └─ guest kernel          designate and decide, for guest objects
      └─ Firecracker       reach: the only way out is its device model
          └─ jailer        the enforcer's own authority, cut down
              └─ host kernel and KVM
signed API request ──────► IAM at the AWS service: decide, on the object side
```

**Inside the guest**, the function is ordinary Linux code with ambient authority over a machine that holds nothing else. The guest kernel designates and authorizes guest objects. Host names mean nothing there.

**At the VM boundary**, reach is the device model. Firecracker's design doc assumes that "all vCPU threads are considered to be running malicious code as soon as they have been started." The guest sees a handful of emulated devices: VirtIO net and block, a serial console, a partial keyboard controller. Network traffic leaves through a TAP device on the host, and block devices are backed by host files. Every path out passes through the Firecracker process.

**Question six, asked of the enforcer.** That process is itself a monitor whose own code might fail, so it gets confined too. The [jailer][firecracker-jailer] enters a new mount namespace, pivots into a chroot that holds little more than the Firecracker binary, `/dev/kvm` and `/dev/net/tun`, places the process in a cgroup, joins a network namespace, drops to an unprivileged uid and gid, and only then execs Firecracker. Firecracker loads seccomp filters on each thread before running any guest code. A guest that escapes into the VMM lands in a process that can reach almost nothing. That is the Linux subtraction toolkit — `setpriv`, namespaces, seccomp — applied to the enforcer rather than the workload.

**At the resource**, none of those layers holds the function's authority over the rest of AWS. Lambda puts the execution role's [temporary keys][lambda-envvars] in the function's environment, and each service authorizes the signed request against IAM policy. That is object-side judgment, in the vocabulary of API actions, and it holds even if every layer above it fails.

It is also the gap. The function *acquires* the real credential. Nothing between the function and S3 attenuates it, so whatever the role allows, a compromised function can do, from wherever the keys end up. A gateway closes that gap: the workload holds a handle, and the credential stays outside.

## Conclusion: what this does not solve

Everything above assumes the reference monitor is a thing you can point at. A kernel. A hypervisor. A runtime. One component, in one trust domain, sitting in one path.

Modern workloads do not have that shape. A single logical operation crosses a process, a machine, an API, a database, a cloud service, a user identity, and an organizational policy. There is no kernel spanning all of that.

The answer is not that the reference monitor becomes distributed. It is that it gets **relocated and replicated**: several monitors, each complete within its own boundary, each seeing a different vocabulary, each surviving a different failure. The guest kernel mediates guest objects. The host mediates external effects. The resource server enforces its own invariant. No single one of them is complete, and the composition has to be designed rather than assumed.

Between those monitors, decisions have to travel. A token issued in one domain is checked in another, long after it was issued. [Part 3](/programming/carriers.html) follows the decision on that trip.

## References

1. [Computer Security Technology Planning Study][computer-security-technology-planning] — Anderson, 1972; the reference monitor
2. [The Flask Security Architecture][flask-security-architecture] — object managers, security server, access-vector caching, revocation
3. [Robust Composition][robust-composition] — Miller's thesis; "only connectivity begets connectivity"
4. [Joe-E: A Security-Oriented Subset of Java][joe-e-security-oriented] — removing ambient authority from an unforgeable heap
5. [Linux Security Modules: General Security Support for the Linux Kernel][linux-security-modules-general] — the original LSM design
6. [Linux Security Module usage][linux-security-module-usage] and [LSM development][lsm-development]
7. [AppArmor — Where Do LSMs Fit?][apparmor-where-do-lsms] — syscall filtering versus DAC, MAC, and resolved-object hooks
8. [Landlock][landlock] — unprivileged monotonic self-restriction
9. [BPF LSM programs][bpf-lsm-programs]
10. [Linux namespaces][linux-namespaces] and [capabilities][linux-capabilities]
11. [`setpriv`][setpriv] — the credential tuple in one exec: uid, gid, the three capability sets, securebits, `no_new_privs`, LSM labels, Landlock and seccomp
12. [Software isolation in Linux][software-isolation-linux] — the mechanism inventory
13. [Capsicum: Practical Capabilities for UNIX][capsicum-practical-capabilities-unix]
14. [10 years seL4][10-years-sel4] — the grant right and what verification bought
15. [seL4 reference manual][sel4-reference-manual] — CNodes, untyped retyping, the capability derivation tree, `Revoke`
16. [WebAssembly Component Model][webassembly-component-model] and [WASI security principles][wasi-security-principles]
17. [Handling Algebraic Effects][handling-algebraic-effects] — effect handlers as programmable interpretations
18. [Chromium sandbox design][chromium-sandbox] — broker and target, restricted tokens, and interception as compatibility rather than security
19. [Building Secure and Reliable Systems, Chapter 3: Safe Proxies][bsrs-safe-proxies] — Warmuz, Oprea et al.; Google's Tool Proxy
20. [Firecracker design][firecracker-design] and [the jailer][firecracker-jailer] — the microVM threat model, the device model, and confining the VMM itself
21. [Lambda environment variables][lambda-envvars] — the execution role's keys, handed to the function
22. [AuthZEN Interop][authzen-interop] — the Todo scenario, with PEPs at the gateway and in the backend
23. [AI Engineer: AI security][ai-engineer-security] — trust boundaries for agents, approvals bound to exact actions, and controls that share failure modes
24. [AI Engineer: sandboxes and execution isolation][ai-engineer-sandboxes] — talks and historic papers, from namespaces and microVMs to agent sandbox fleets

[10-years-sel4]: https://microkerneldude.org/2019/08/06/10-years-sel4-still-the-best-still-getting-better "10 years seL4"
[ai-engineer-sandboxes]: https://ai.engineer/topics/sandboxes-and-execution-isolation "AI Engineer: sandboxes and execution isolation"
[ai-engineer-security]: https://ai.engineer/topics/ai-security "AI Engineer: AI security"
[apparmor-where-do-lsms]: https://apparmor.net/about/lsm_introduction/ "AppArmor — Where Do LSMs Fit?"
[bpf-lsm-programs]: https://docs.kernel.org/bpf/prog_lsm.html "BPF LSM programs"
[bsrs-safe-proxies]: https://google.github.io/building-secure-and-reliable-systems/raw/ch03.html "Building Secure and Reliable Systems, Chapter 3: Safe Proxies"
[chromium-sandbox]: https://chromium.googlesource.com/chromium/src/+/HEAD/docs/design/sandbox.md "Chromium sandbox design"
[linux-capabilities]: https://man7.org/linux/man-pages/man7/capabilities.7.html "capabilities"
[capsicum-practical-capabilities-unix]: https://www.usenix.org/conference/usenixsecurity10/capsicum-practical-capabilities-unix "Capsicum: Practical Capabilities for UNIX"
[computer-security-technology-planning]: https://csrc.nist.gov/csrc/media/publications/conference-paper/1998/10/08/proceedings-of-the-21st-nissc-1998/documents/early-cs-papers/ande72.pdf "Computer Security Technology Planning Study"
[lsm-development]: https://docs.kernel.org/security/lsm-development.html "LSM development"
[firecracker-design]: https://github.com/firecracker-microvm/firecracker/blob/main/docs/design.md "Firecracker design"
[firecracker-jailer]: https://github.com/firecracker-microvm/firecracker/blob/main/docs/jailer.md "Firecracker jailer"
[flask-security-architecture]: https://www.cs.cmu.edu/~dga/papers/flask-usenixsec99.pdf "The Flask Security Architecture"
[handling-algebraic-effects]: https://arxiv.org/abs/1312.1399 "Handling Algebraic Effects"
[joe-e-security-oriented]: https://www.cs.berkeley.edu/~daw/papers/joe-e-ndss10.pdf "Joe-E: A Security-Oriented Subset of Java"
[landlock]: https://docs.kernel.org/userspace-api/landlock.html "Landlock"
[lambda-envvars]: https://docs.aws.amazon.com/lambda/latest/dg/configuration-envvars.html#configuration-envvars-runtime "Lambda environment variables"
[linux-namespaces]: https://man7.org/linux/man-pages/man7/namespaces.7.html "Linux namespaces"
[linux-security-module-usage]: https://docs.kernel.org/admin-guide/LSM/index.html "Linux Security Module usage"
[linux-security-modules-general]: https://www.usenix.org/legacy/publications/library/proceedings/sec02/full_papers/wright/wright_html/ "Linux Security Modules: General Security Support for the Linux Kernel"
[robust-composition]: http://www.erights.org/talks/thesis/markm-thesis.pdf "Robust Composition"
[sel4-reference-manual]: https://sel4.systems/Info/Docs/seL4-manual-latest.pdf "seL4 reference manual"
[networking-is-ipc-paper]: https://www.cs.bu.edu/fac/matta/Papers/IPC-arch-rearch08.pdf "“Networking is IPC”: A Guiding Principle to a Better Internet"
[rfc1498]: https://www.rfc-editor.org/rfc/rfc1498.html "RFC 1498: On the Naming and Binding of Network Destinations"
[setpriv]: https://man7.org/linux/man-pages/man1/setpriv.1.html "`setpriv`"
[software-isolation-linux]: https://nikmav.blogspot.com/2015/06/software-isolation-in-linux_15.html "Software isolation in Linux"
[wasi-security-principles]: https://github.com/bytecodealliance/wasi.dev/blob/main/docs/security.md "WASI security principles"
[webassembly-component-model]: https://component-model.bytecodealliance.org/design/components.html "WebAssembly Component Model"
[authzen-interop]: https://authzen-interop.net/ "AuthZEN Interop"
