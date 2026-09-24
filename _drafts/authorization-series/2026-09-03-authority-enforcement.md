---
title:  "How authority is enforced: reference monitors and sandboxes"
series: "Authorization, Part 3"
series_url: "/programming/authorization-series-intro.html"
category: programming
date:   2026-09-03
---

> This is Part 3 of a five-part [series on authorization](/programming/authorization-series-intro.html).
>
> 0. **[Prologue: Who is the adversary](/programming/who-is-the-adversary.html)** — five positions the attacker has occupied, and why identity stopped being the useful thing to key on.
> 1. **[Authorization models](/programming/authorization-models.html)** — what every system computes, and who may change it.
> 2. **[Capabilities](/programming/capabilities.html)** — authority you hold, not authority you are.
> 3. **How authority is enforced** — what makes any of it binding.
> 4. **[LLM sandboxing](/programming/llm-sandbox.html)** — the gateway, correct and unavoidable.

- [The unit of analysis is the external effect](#the-unit-of-analysis-is-the-external-effect)
- [The reference monitor](#the-reference-monitor)
  - [Decomposing the monitor](#decomposing-the-monitor)
- [Four axes, four enforcers](#four-axes-four-enforcers)
  - [Every axis has its own enforcer](#every-axis-has-its-own-enforcer)
  - [Which axis do you cut?](#which-axis-do-you-cut)
  - [Acquire closes the loop](#acquire-closes-the-loop)
  - [Membranes in the wild](#membranes-in-the-wild)
- [Non-bypassability is a property of reach](#non-bypassability-is-a-property-of-reach)
- [Three properties people conflate](#three-properties-people-conflate)
- [Linux is a toolkit, not a primitive](#linux-is-a-toolkit-not-a-primitive)
  - [Credentials: one axis, moving alone](#credentials-one-axis-moving-alone)
  - [LSMs: authorize on the resolved object](#lsms-authorize-on-the-resolved-object)
- [Editing the object side](#editing-the-object-side)
- [What can change between check and use](#what-can-change-between-check-and-use)
- [Same interface, different enforcers](#same-interface-different-enforcers)
- [Two systems that cut acquire by construction](#two-systems-that-cut-acquire-by-construction)
- [seL4 as the meeting point](#sel4-as-the-meeting-point)
- [The architecture is recursive](#the-architecture-is-recursive)
- [What this does not solve](#what-this-does-not-solve)
- [References](#references)

The first two articles ended with a description and no teeth. A capability graph bounds what a component can reach. An ACL says who may touch a resource. Neither does anything to a program that declines to participate.

Something has to make the description true. This article is about that something: what it must guarantee, where it sits, and what it can cut.

The spine comes from the first article: four questions every invocation answers on its way to an effect. How did it come to hold a name? What does the name denote? Can it get there? May it do this? Each question is an axis a sandbox can cut, and each has its own enforcer. Most confusion about sandboxes comes from comparing mechanisms that cut different axes.

None of this is a rival to the capabilities article. Something still has to guarantee that a holder cannot forge a reference. But most of the machinery below exists because most code does not cooperate. A capability system asks the program to accept references instead of opening paths. Namespaces, seccomp and LSMs ask the program for nothing, which is why you reach for them when you did not write the binary.

## The unit of analysis is the external effect

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

## The reference monitor

The foundational statement is fifty years old. In 1972 James Anderson led a study for the U.S. Air Force whose two volumes set the research agenda of computer security for two decades.

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

There is no escaping this. Every mechanism in the rest of this article is a reference monitor placed somewhere, and every failure is one of the three properties not holding. Microkernel design is precisely the project of making the reference monitor as small as possible so the third property becomes achievable.

The third requirement was close to aspirational when it was written. Anderson knew formal verification of a real system was out of reach with 1972 tooling. seL4's verification in 2009 is, in a meaningful sense, the first time anyone discharged it on a system meant for actual use. That is most of the reason the seL4 people are entitled to their swagger.

### Decomposing the monitor

"Reference monitor" names a function, not a component. In practice that function splits in two, and Part 4 leans on the split.

```text
request ──► PEP ──────► PDP
             ▲            │
             └────────────┘
                decision
```

- **PEP**, policy enforcement point. Sits in the path of the effect. Cannot be bypassed. Does what the decision says.
- **PDP**, policy decision point. Evaluates policy against facts and returns an answer. Need not be in the path at all.

The [series intro](/programming/authorization-series-intro.html) adds XACML's other two boxes: the PAP, where policy is authored, and the PIP, where facts come from. The distinction is logical. All four can be one kernel function, or four services in different datacenters. What matters is that only the PEP has to satisfy Anderson's first two properties. The PDP must be *correct*; the PEP must be *unavoidable*. Conflating them is how people end up with an authorization system that is beautifully expressive and trivially routed around.

The [Flask architecture][flask-security-architecture] is the cleanest instantiation, and the direct ancestor of SELinux. Flask separates **object managers**, which own resources and enforce decisions, from a **security server**, which evaluates policy. An object manager asks whether a subject may perform an operation on an object, caches the returned access vector, and — the part people forget — receives notifications when a policy change requires revoking what it cached.

That revocation channel is the honest cost of caching a decision. The [capabilities article](/programming/capabilities.html) ended with the pipeline

```text
policy → decision → materialized authority → capability
```

and noted that the interesting engineering is in the arrow. Flask is what the arrow looks like when someone builds it carefully: the cache makes enforcement fast, and the notification channel is what you owe in exchange.

## Four axes, four enforcers

Every mechanism in the rest of this article sits somewhere on one path. The [first article](/programming/authorization-models.html#four-questions-every-invocation-answers) split it into four questions, each an axis a sandbox can cut:

```text
ACQUIRE     how did it come to hold a name?
DESIGNATE   which object does the name denote?
REACH       can the invocation get there?
AUTHORIZE   may it do this?
```

The capabilities article asked which artifact carries each axis, and what changes when [one artifact carries them all](/programming/capabilities.html#two-bindings-collapse-the-axes). This one asks what makes each axis hold. Cut one, and the invocation fails in a way that tells you which:

| Cut | What the invocation sees | Example |
|---|---|---|
| acquire | nothing; there was never a name to try | no FD was passed; the URL cannot be guessed |
| designate | the name resolves to nothing, or to something else | `ENOENT` inside a chroot; `NXDOMAIN` |
| reach | the name resolves, and delivery fails | `ENETUNREACH` in an empty network namespace; a timeout |
| authorize | the request arrives, and the answer is no | `EACCES`; HTTP 403 |

Real designators are layered, and each layer answers both questions. A URL is a host, resolved by DNS and reached over IP, plus a path, resolved and reached inside the server.

### Every axis has its own enforcer

Enforcement is not a fifth step. Each axis has its own enforcer, and the word means something different on each: control over how names are obtained, the resolver, whatever can deny a path, the check. Five systems, by who enforces each axis:

| | Pathname + ACL | OAuth bearer token | Capability URL | Capsicum FD | Object capability |
|---|---|---|---|---|---|
| **Acquire** | nobody; strings are free | nobody for the URL; the authorization server for the token | unguessability | kernel | runtime or kernel |
| **Designate** | kernel path walk | DNS + the server's router | DNS + the server's router | kernel FD table | runtime or kernel |
| **Reach** | nobody; `open` is always callable | the network, limited only by firewalls | the network, limited only by firewalls | kernel FD table | runtime or kernel |
| **Authorize** | kernel ACL check | resource server | server checks the secret | kernel rights check | runtime or kernel |

The Capsicum column says "kernel" four times. The capability URL column names four parties, and one of them is nobody. Plain Unix descriptors differ from Capsicum only in the first row: the first descriptor comes from opening a path, on ambient authority, and `cap_enter()` removes that route.

On reach, what *provides* the path is rarely what *limits* it. The network carries a request to any URL; only a firewall, an egress proxy or a network namespace can refuse. On the open internet nothing refuses, which is what it means for reach to be ambient.

Separated axes mean several enforcers, often in different trust domains, and the classic bugs live in the gaps between them. The confused deputy is authorize enforced by the kernel and designate enforced by no one: Hardy's compiler was handed a pathname, and nothing tied that name to the authority of whoever supplied it. A check-then-use race is designate resolved twice while authorize is checked once. [Collapse](/programming/capabilities.html#two-bindings-collapse-the-axes) closes the gaps, because one component enforces every axis.

Anderson's three properties therefore apply per axis. A PEP that is always invoked on authorize does nothing about a name that resolves somewhere else, or a route that goes around it. And collapse does not make the reference enforce itself. Whoever owns the table does, which is why seL4, further down, is both the purest capability system in this article and the most thoroughly enforced.

### Which axis do you cut?

Almost every argument about sandboxing is an argument about which of two strategies is in use. They are cuts on different axes.

```text
UNNAMEABILITY                         ADJUDICATION

cut acquire, designate or reach       leave those open, cut authorize

the resource is absent from           the request is expressible,
the reachable universe                it arrives, and something
                                      judges it

"there is nothing to ask for"         "you asked; the answer is no"
```

These are functions, not technology categories, and most mechanisms cut exactly one axis:

| Mechanism | Axis it cuts | Seen from inside |
|---|---|---|
| WASI import not supplied, Capsicum `cap_enter()` | acquire | no name to try |
| `chroot`, mount namespace | designate | `ENOENT`, or a different file |
| network namespace, missing route | reach | `ENETUNREACH` |
| VM | designate and reach, for the whole host | host names mean nothing; no device |
| seccomp | reach, per kernel entry point | `EPERM`, `ENOSYS`, or the process dies |
| LSM, Landlock | authorize, on the resolved object | `EACCES` |
| `setpriv` credentials | authorize, on the subject side | `EACCES` |
| ACL at the resource, branch protection | authorize, on the object side | `EACCES`, HTTP 403 |

Seccomp is the one people misplace. It decides which kernel entry points a process can get to, and it never sees the object a call would resolve to.

The strongest designs cut two axes at once. The workload never acquires the real GitHub token. It holds a placeholder handle that reaches only a gateway, and the gateway authorizes only approved operations. That is *authority attenuation* — possession of a powerful resource replaced by permission to request a smaller set of effects — and Part 4 builds it.

### Acquire closes the loop

Both strategies try to make a subject's row in the [square matrix](/programming/authorization-models.html#capabilities-make-both-axes-the-same-set) small. They differ in which part of the picture they edit.

```text
subtraction    the row starts full and the columns get cut away
construction   the row starts empty and grows by reference-passing
```

Subtraction is an outside configurator removing names and routes before the process starts. Construction grows the row only through [Miller's][robust-composition] loop — new names arrive over channels already held — and no step can hand on more than it holds.

Subtraction cannot mediate. You can remove a column. There is no namespace operation for "Alice reaches X only through Bob," because the thing in the middle has to hold a row and be a column at once — [Property E](/programming/capabilities.html#the-six-properties) — and a namespace has visibility rather than entities.

> **Subtraction plus mediation is construction.**

The moment removal is not enough and you need to interpose, you introduce something that holds the real authority and speaks a protocol: a FUSE daemon, a proxy inside the network namespace, a broker. That thing is a membrane. Its clients acquire only what it hands them, over the one channel they have to it, so the loop holds again. You have rebuilt the capability system one resource class at a time.

Without the membrane, subtraction stays subtraction. `chroot` cuts designate for everything outside the jail and leaves every axis ambient inside it, which is why it is not a capability system. Unnameability becomes capability discipline only when the name you hold is the only way to reach the object, and the only way to get more names.

### Membranes in the wild

The pattern is old, and the systems that use it at scale describe themselves in exactly these terms.

**Chromium's broker.** Chromium's [sandbox][chromium-sandbox] splits the browser into a *broker* and its *targets*. A renderer target runs under a token that denies it almost everything: every group deny-only, no privileges, untrusted integrity, a job object, a desktop of its own. That is subtraction, cutting authorize for nearly every OS object. The broker is the browser process, "a privileged controller/supervisor of the activities of the sandboxed processes." It evaluates policy, and "the policy-allowed calls are then executed by the broker and the results returned to the target process via the same IPC." The design doc puts the acquire axis in plain words:

> The Chromium renderer runs with this token, which means that almost all resources that the renderer process uses have been acquired by the Browser and their handles duplicated into the renderer process.

The target acquires only what the broker hands it, over the one channel it has. That is construction, rebuilt on top of Windows. The doc is just as plain about where enforcement is *not*. The hooks that forward Win32 calls to the broker are for convenience: "The interception + IPC mechanism does not provide security; it is designed to provide compatibility when code inside the sandbox cannot be modified to cope with sandbox restrictions." The token is the cut. The hook is `HTTP_PROXY` at the Win32 layer.

**Google's safe proxies.** [*Building Secure and Reliable Systems*][bsrs-safe-proxies] describes the same shape for people. "Engineers are not able to run arbitrary commands directly on servers; they need to contact the Tool Proxy instead." That cuts reach. The proxy then authorizes each command against an access list, can require multi-party approval, rate-limits changes so a restart rolls out gradually, and logs every operation — adjudication, in the legible vocabulary of whole commands rather than packets. The chapter is candid about the cost, and lists among the downsides "a central machine that an adversary could take control of." That is the last question of this article, asked of a real system: what can the enforcer do if its policy is wrong?

Part 4's capability gateways are the same membrane, placed in front of an agent.

## Non-bypassability is a property of reach

Adjudication works only if the request cannot go around the enforcer. That is not a property of a policy language or a hook. It is a property of the topology: can the workload reach the protected resource by some other path?

Stated as a condition to satisfy:

> **For every effect the workload can attempt, either no path to the resource exists, or every path passes through a point that decides.**

The two disjuncts are the two strategies. The first involves no enforcement point at all: unnameability is not a check that reliably says no, it is the absence of anything to check. So "is there a PEP?" is never the interesting question. A PEP is always a PEP for some class of effect, and what you have to establish is that the union of them leaves no path uncovered.

The humble proxy shows it best. `HTTP_PROXY` is a cooperative convention. A workload that wants to ignore it simply ignores it, and no policy inside the proxy changes that. The same proxy becomes genuine enforcement when reach closes: force routing with nftables or TPROXY, or give the workload a network peer that is the proxy, with no NAT and no alternate route.

Same code, same policies, same expressivity. Enforcement in one deployment and decoration in the other. This is why arguing about policy languages before establishing the topology is almost always wasted effort.

## Three properties people conflate

Knowing which axis a mechanism cuts, and that nothing goes around it, still leaves mechanisms on the same axis far apart. An LSM and a host-side HTTP gateway both cut authorize. "Policy expressivity" is the usual word for how they differ, and it collapses three independent questions.

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

These vary independently. An LSM is structurally legible, weakly programmable, and trusted only as far as the guest kernel. A JavaScript callback in a host proxy is semantically legible, arbitrarily programmable, and survives a compromised guest. Neither dominates; they protect different boundaries.

Non-bypassability is none of the three. It belongs to reach, and the previous section already asked it.

## Linux is a toolkit, not a primitive

Linux has no single sandbox primitive. It has a collection of mechanisms, each cutting one axis for one class of kernel object, and every real sandbox is a composition of them.

![](/assets/authority-enforcement/linux-security-mechanisms.png)

The mechanism table above placed most of them. Namespaces cut designate or reach, one kernel subsystem at a time. Seccomp cuts reach to kernel entry points. Credentials and LSMs both cut authorize, from different ends, and deserve a closer look.

### Credentials: one axis, moving alone

`fork()`, `setuid()` and `exec()` are the oldest sandbox on the list, and [`setpriv`][setpriv] is where they become usable. One `exec` sets the uid and gid, clears supplementary groups, trims the inheritable, ambient and bounding capability sets, locks securebits, requests an LSM label, and sets `no_new_privs`: the whole credential tuple, chosen by the launcher rather than the program. Hand-rolling it is a bug farm of unchecked `setuid` returns, leftover groups, and bounding sets trimmed too late.

`no_new_privs` is the load-bearing bit. Without it the restriction is not monotonic — exec a setuid binary and the authority comes back — and an unprivileged process cannot install a seccomp filter at all. It is the precondition for every restriction a workload applies to itself.

Credentials are also the cleanest case of one axis moving alone. They are ambient authority and nothing else. Shrink them and every name still resolves — `open("/etc/shadow")` stays a perfectly expressible request — and only the answer changes. No namespace, no label, no hook, no unnameability. Authorize cut while acquire, designate and reach stay exactly as ambient as they were.

The vocabulary collides here, and the collision is worth naming. A Linux *ambient capability* is authority that survives `exec` with nobody designating anything, which is ambient authority in this series' sense. `--ambient-caps` is the knob that grants it, and `no_cap_ambient_raise` is the securebit that takes the knob away.

### LSMs: authorize on the resolved object

The LSM framework is Flask brought into Linux, and it sits at a specific and well-chosen place. Rather than interposing at syscall entry, the kernel first resolves user-supplied names and handles into internal objects, *then* calls the hook immediately before the security-relevant operation. The question it asks is explicit:

```text
May subject S perform operation OP on kernel object OBJ?
```

That is the difference from seccomp. Seccomp sits on reach and sees a syscall number and scalar arguments; it cannot dereference a pathname pointer or reason about the resolved inode. An LSM sits on authorize, after designate has run, and sees the object and the kernel context that produced it, whichever syscall got there.

Where the hook sits has a direct consequence for policy soundness. Path-based policy has to account for symlinks, hard links, rename, bind mounts, already-open handles, and the gap between a directory entry and an inode — every way designate can resolve one object under many names. Label-based policy attached to kernel objects sidesteps much of that aliasing, at the cost of policies that map less directly onto how people describe a workspace. Neither choice is free.

![](/assets/authority-enforcement/linux-security-frontends.png)

The same primitives wear different user-facing clothes, which is much of why the landscape looks more fragmented than it is. Read the credentials row twice. Every supervisor on the chart reimplements `setpriv`: the OCI `process` block is its flag list as JSON, systemd spells it `User=`, `CapabilityBoundingSet=`, `AmbientCapabilities=` and `NoNewPrivileges=`, and Chrome's zygote drops to an unprivileged uid and sets `no_new_privs` before installing its filter. No other row is driven by all of them.

## Editing the object side

Every Linux mechanism above edits the subject. The matrix has two projections, and the other one is just as mutable. `setfacl` on a file, `chcon` on its label, `GRANT` and `REVOKE` in a database, an ACE for a package SID on a Windows object, a bucket policy, a protected branch. None of it touches the workload. Its authority shrinks anyway.

Sandboxes almost never work this way. Confining a workload means denying everything except a few things, and on the object side "everything" is unbounded: a file created after you ran `setfacl` carries whatever the default gives it, and nothing covers objects that do not exist yet. Each edit is also global. Lock one workload out of `/etc/passwd` by editing `/etc/passwd` and you break every other reader, so the move is only safe once the workload holds a principal nobody else shares — a subject-side act. And object state is durable. Credentials cost nothing per `exec`; you cannot relabel a filesystem per tool call.

Two things the object side buys that nothing else does. An ACL hangs on the inode, so hard links, renames and bind mounts cannot walk around it. And it holds after a total escape. Branch protection refuses the force-push whether it came from the sandbox, from a process that broke out of it, or from a laptop in another country. Every other mechanism in this article stops working the moment its boundary fails. Policy at the resource has no boundary to fail.

One trap comes with it. Unix checks permission at `open`, so `chmod 000` does nothing to a descriptor somebody already holds. Object-side edits bind at the next resolution, never retroactively, which is the next section in miniature.

## What can change between check and use

Always invoked, tamperproof, verifiable. All three can hold and the monitor can still authorize the wrong thing, because none of them says the decision was still true when the effect happened. Separated axes resolve at separate moments, and almost nothing in an authorization question is supplied directly. The subject and the object arrive as *references*, and each resolves against state somebody else can modify.

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

**Object binding.** The classic case, and the reason the LSM hook sits where it does. A pathname gets resolved twice:

```text
t0   access("/tmp/foo")  →  inode A   → allowed
t1   open("/tmp/foo")    →  inode B
```

Check and use named the same string and reached different objects: designate ran twice, authorize ran once. A file descriptor closes this by resolving once and binding the result — `read(7)` cannot be redirected by renaming anything. That is what `openat`, `O_PATH` and Capsicum are for. It is designate and authorize collapsing, seen as a race.

**Subject binding.** The same indirection exists on the other side and gets far less attention. A pathname is an indirect reference to an object; an ambient credential is an indirect reference to authority, resolved at the moment of use. Check under one credential context and act under another — a dropped privilege, a changed EUID, a recycled thread pool — and you have the same bug with the roles swapped. Setting the credentials once, from outside, before the workload starts is what `setpriv` buys: the program never holds authority it would have had to remember to drop.

**Authorization state.** Neither binding has to move for the answer to change. Remove Alice from a group and every decision derived from that membership is stale, with the same subject and the same object throughout. This is not a race inside the monitor. It is the monitor's inputs having a lifetime, which is exactly why Flask needs a revocation channel: a cached access vector is a decision that outlived its premises.

**Environment.** Device posture, time of day, risk score. Same shape as the others, least often modelled, and the usual reason a "zero trust" deployment is less continuous than its diagram.

Re-evaluate on every operation and the inputs stay fresh, but every operation pays the resolution cost and re-opens all four races. Materialize the decision into a capability and the bindings freeze — that is the point of it — but a frozen binding is indistinguishable from a stale one once the source of truth moves.

```text
re-evaluate    fresh inputs, repeated resolution races
materialize    stable bindings, revocation debt
```

Neither end is safe on its own. A file descriptor eliminates the object-binding race and creates a revocation problem in the same stroke. That is not a defect in the mechanism. It is the trade that appears wherever a system caches a derived fact, and authorization gets no exemption from it.

## Same interface, different enforcers

Containers show the per-axis enforcers better than any argument. A "container" is defined by a contract — an image, a bundle, a lifecycle — and never by a mechanism.

![image](/assets/authority-enforcement/oci-stacks.png)

The contract fixes the names the workload sees: its paths, its ports, its process IDs. It says nothing about who enforces reach and authorize behind those names. The runtime decides that:

```text
container contract
       │
       ├── runc    → the host kernel: namespaces, cgroups, seccomp, LSM
       ├── runsc   → gVisor: a userspace kernel answers the syscalls
       └── kata    → a hypervisor, with a guest kernel inside a VM
```

![image](/assets/authority-enforcement/container-runtimes.png)

Same names, three different enforcers. Under runc, the workload talks straight to the host kernel, so a reachable kernel bug is an escape. Under gVisor, it talks to a userspace kernel, and the host kernel sees a much smaller surface. Under Kata, the hypervisor is what the workload must defeat. These are interchangeable to the consumer and not remotely comparable as boundaries. "We run it in a container" names the interface, not the enforcer.

This is the capabilities article's policy/mechanism separation one level down. The contract is what the workload may assume about its environment. The runtime is who makes it true. Keeping the seam there is what lets you change your mind about isolation strength without repackaging anything.

## Two systems that cut acquire by construction

**WebAssembly and WASI** are the cleanest modern instance of unnameability followed by adjudicated reintroduction. A Wasm module starts with linear memory and computation. It acquires no ambient filesystem, network, environment, or clock. Everything useful arrives as an import the host chose to supply.

```text
Wasm module
    → imported WASI operation
        → host runtime
            → selected filesystem, socket, clock, or service
```

There is no syscall instruction to perform, so reach to the host kernel does not exist. Unnameability comes free from the execution semantics rather than from a device model someone had to get right. The vocabulary is legible — `open-at` means far more than a block offset — and the import list is the local audit surface the capabilities article describes.

**Effect systems** reach the same shape from the language side. The type system records each effect a function may perform, and a handler supplies its interpretation:

```text
computation requests Network.send
    → handler may execute, deny, record, transform, or emulate it
```

That is the top of the programmability ladder, at the most semantic legibility available anywhere. But it is confinement only when the language and runtime together guarantee that every relevant effect is captured. Otherwise native code, FFI, `unsafe`, or a compromised runtime walks straight past the handler — Anderson's first property, restated for a compiler.

The transferable lesson is not "adopt an effect language". It is that interfaces get easier to govern when the effect is named at the level policy cares about. `publishArtifact` is a better policy event than a sequence of writes and HTTP requests, but only if the lower-level routes cannot reach the same outcome.

## seL4 as the meeting point

The capabilities article used seL4 to argue that the capability graph can *be* the authority, with no authoritative copy elsewhere. That was the representation half. Here is the enforcement half.

seL4 stores capabilities in kernel objects called CNodes. Userspace never touches a capability directly; it names a slot, and the kernel dereferences it. Designate, reach and authorize are one capability, and one kernel enforces all three. All authority — memory, execution, IPC endpoints, interrupts — is a capability, obtained by retyping untyped memory. There is no ambient authority anywhere in the system, including the ability to allocate.

That leaves acquire, and two mechanisms govern it.

**The grant right.** Holding a capability does not imply the ability to share it. Passing a capability over an endpoint requires the `grant` right on that endpoint. From the [seL4 retrospective][10-years-sel4]:

> Capabilities also cleanly solved another issue with original L4, that of limiting communication. The original model relied on an (inflexible) process hierarchy and redirection to a monitor process ("chief") to limit data flow. Capabilities provide a cleaner, simpler and low-overhead model: Having a privilege does not in itself imply the ability to share that privilege, an additional grant right is needed to pass on capabilities.

That is Saltzer and Schroeder's second objection, propagation control, answered structurally rather than by a registry.

**The capability derivation tree.** The kernel tracks which capabilities were derived from which, and `seL4_CNode_Revoke` removes all descendants of a capability in one operation. That answers the third objection too, without indirection and without a lookup table, because the kernel already holds the provenance.

And the kernel is the verified one. Every axis collapses into one component, and that component discharges Anderson's third property. That is what collapse buys at the enforcement layer: one monitor to verify, instead of four that must agree.

> **Capabilities describe authority structurally. A trusted, verified reference monitor makes that structure non-bypassable.**

Policy and mechanism stay separate. seL4 enforces whatever capability graph exists. Which graph *should* exist is a design question outside the kernel, usually settled in a static configuration before boot.

## The architecture is recursive

None of these are alternatives. A Wasm component runs inside a Linux guest constrained by an LSM. The guest presents an attenuated handle to a host broker. The broker uses a scoped OAuth token against a service whose own policy protects the resource.

At every boundary, ask the same questions, one per axis plus two more:

1. What computation is inside the boundary?
2. **Acquire.** Which names can it obtain, and from whom?
3. **Designate.** What do those names resolve to, and who resolves them?
4. **Reach.** Which paths leave the boundary, and does every one pass an enforcer?
5. **Authorize.** Who decides, in what vocabulary?
6. What is the enforcer's own maximum authority if its policy is wrong?

Question four is Anderson's first property. Question six is the one people skip, and it is the one that decides how bad your worst day is.

## What this does not solve

Everything above assumes the reference monitor is a thing you can point at. A kernel. A hypervisor. A runtime. One component, in one trust domain, sitting in one path.

Modern workloads do not have that shape. A single logical operation crosses a process, a machine, an API, a database, a cloud service, a user identity, and an organizational policy. There is no kernel spanning all of that.

The answer is not that the reference monitor becomes distributed. It is that it gets **relocated and replicated**: several monitors, each complete within its own boundary, each seeing a different vocabulary, each surviving a different failure. The guest kernel mediates guest objects. The host mediates external effects. The resource server enforces its own invariant. No single one of them is complete, and the composition has to be designed rather than assumed.

Which is exactly the problem LLM agents force you to confront, because an agent's authority is not known until it runs. That is Part 4.

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

[10-years-sel4]: https://microkerneldude.org/2019/08/06/10-years-sel4-still-the-best-still-getting-better "10 years seL4"
[apparmor-where-do-lsms]: https://apparmor.net/about/lsm_introduction/ "AppArmor — Where Do LSMs Fit?"
[bpf-lsm-programs]: https://docs.kernel.org/bpf/prog_lsm.html "BPF LSM programs"
[bsrs-safe-proxies]: https://google.github.io/building-secure-and-reliable-systems/raw/ch03.html "Building Secure and Reliable Systems, Chapter 3: Safe Proxies"
[chromium-sandbox]: https://chromium.googlesource.com/chromium/src/+/HEAD/docs/design/sandbox.md "Chromium sandbox design"
[linux-capabilities]: https://man7.org/linux/man-pages/man7/capabilities.7.html "capabilities"
[capsicum-practical-capabilities-unix]: https://www.usenix.org/conference/usenixsecurity10/capsicum-practical-capabilities-unix "Capsicum: Practical Capabilities for UNIX"
[computer-security-technology-planning]: https://csrc.nist.gov/csrc/media/publications/conference-paper/1998/10/08/proceedings-of-the-21st-nissc-1998/documents/early-cs-papers/ande72.pdf "Computer Security Technology Planning Study"
[lsm-development]: https://docs.kernel.org/security/lsm-development.html "LSM development"
[flask-security-architecture]: https://www.cs.cmu.edu/~dga/papers/flask-usenixsec99.pdf "The Flask Security Architecture"
[handling-algebraic-effects]: https://arxiv.org/abs/1312.1399 "Handling Algebraic Effects"
[joe-e-security-oriented]: https://www.cs.berkeley.edu/~daw/papers/joe-e-ndss10.pdf "Joe-E: A Security-Oriented Subset of Java"
[landlock]: https://docs.kernel.org/userspace-api/landlock.html "Landlock"
[linux-namespaces]: https://man7.org/linux/man-pages/man7/namespaces.7.html "Linux namespaces"
[linux-security-module-usage]: https://docs.kernel.org/admin-guide/LSM/index.html "Linux Security Module usage"
[linux-security-modules-general]: https://www.usenix.org/legacy/publications/library/proceedings/sec02/full_papers/wright/wright_html/ "Linux Security Modules: General Security Support for the Linux Kernel"
[robust-composition]: http://www.erights.org/talks/thesis/markm-thesis.pdf "Robust Composition"
[sel4-reference-manual]: https://sel4.systems/Info/Docs/seL4-manual-latest.pdf "seL4 reference manual"
[setpriv]: https://man7.org/linux/man-pages/man1/setpriv.1.html "`setpriv`"
[software-isolation-linux]: https://nikmav.blogspot.com/2015/06/software-isolation-in-linux_15.html "Software isolation in Linux"
[wasi-security-principles]: https://github.com/bytecodealliance/wasi.dev/blob/main/docs/security.md "WASI security principles"
[webassembly-component-model]: https://component-model.bytecodealliance.org/design/components.html "WebAssembly Component Model"
