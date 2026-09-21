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
- [Unnameability versus adjudication](#unnameability-versus-adjudication)
  - [The layering leaks, and it should](#the-layering-leaks-and-it-should)
- [Three properties people conflate](#three-properties-people-conflate)
  - [Non-bypassability is none of the three](#non-bypassability-is-none-of-the-three)
- [Linux is a toolkit, not a primitive](#linux-is-a-toolkit-not-a-primitive)
- [Editing the object side](#editing-the-object-side)
- [What can change between check and use](#what-can-change-between-check-and-use)
- [Interface and mechanism are separable](#interface-and-mechanism-are-separable)
- [Two systems that got the shape right](#two-systems-that-got-the-shape-right)
- [seL4 as the meeting point](#sel4-as-the-meeting-point)
- [Runtime versus analysis time](#runtime-versus-analysis-time)
- [The architecture is recursive](#the-architecture-is-recursive)
- [What this does not solve](#what-this-does-not-solve)
- [References](#references)

The first two articles ended with a description and no teeth. A capability graph bounds what a component can reach. An ACL says who may touch a resource. Neither does anything to a program that declines to participate.

Something has to make the description true. This article is about that something: what it must guarantee, where people put it, and the two fundamentally different strategies it can use.

Worth saying up front how this relates to the last article, because the two are easy to read as rivals. They are not. Capabilities do not escape the reference monitor — seL4 is the most thoroughly enforced system in this article and it is also the purest capability system anyone has built. Something still has to guarantee that references are unforgeable, that a holder cannot fabricate one, that the handle table is not writable by the process it constrains.

What *is* true is that most of the machinery below exists because most code does not cooperate. A capability system asks the program to accept references instead of opening paths. Namespaces, seccomp and LSMs ask the program for nothing at all, which is why they are what you reach for when you did not write the binary. So: the theory here is universal, and the toolkit is what universality costs when you cannot change the code.

## The unit of analysis is the external effect

Sandboxing discussions usually start with the wrong noun. They ask whether untrusted code should run in a container, a microVM, gVisor, WASI, or a language runtime. Those choices matter, but they answer only *where computation happens*. They do not answer *what that computation can do*.

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

The foundational statement is fifty years old. James Anderson led a study for the U.S. Air Force in 1972 whose two volumes defined the research agenda of computer security for the next two decades. Most of what now feels like background furniture got its first rigorous statement there.

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

## Decomposing the monitor

"Reference monitor" names a function, not a component. In practice that function splits, and the split has a standard vocabulary worth fixing now because Part 4 leans on it.

```text
request ──► PEP ──────► PDP
             ▲            │
             └────────────┘
                decision
```

- **PEP**, policy enforcement point. Sits in the path of the effect. Cannot be bypassed. Does what the decision says.
- **PDP**, policy decision point. Evaluates policy against facts and returns an answer. Need not be in the path at all.

XACML's architecture adds two more, and the four-part vocabulary is the one most authorization products use:

```text
PAP   policy administration point   where policy is authored
PIP   policy information point      where facts come from
PDP   policy decision point         evaluates policy against facts
PEP   policy enforcement point      sits in the path, applies the answer
```

The distinction is logical. All four can be one kernel function, or four services in different datacenters. What matters is that only the PEP has to satisfy Anderson's first two properties. The PDP must be *correct*; the PEP must be *unavoidable*. Conflating them is how people end up with an authorization system that is beautifully expressive and trivially routed around.

The [Flask architecture][flask-security-architecture] is the cleanest instantiation, and the direct ancestor of SELinux. Flask separates **object managers**, which own resources and enforce decisions, from a **security server**, which evaluates policy. An object manager asks whether a subject may perform an operation on an object, caches the returned access vector, and — the part people forget — receives notifications when a policy change requires revoking what it cached.

That revocation channel is the honest cost of caching a decision. The [capabilities article](/programming/capabilities.html) ended with the pipeline

```text
policy → decision → materialized authority → capability
```

and noted that the interesting engineering is in the arrow. Flask is what the arrow looks like when someone builds it carefully: the cache makes enforcement fast, and the notification channel is what you owe in exchange.

## Unnameability versus adjudication

Underneath all of it are two strategies, and almost every argument about sandboxing is really an argument about which one is being used.

```text
UNNAMEABILITY                      ADJUDICATION

the resource is absent from        the request is expressible,
the reachable universe             and an enforcement point
                                   judges it

no route                           policy engine
no mount                           SELinux / AppArmor
no reference                       seccomp rule
API not imported                   ACL check

"there is nothing to ask for"      "you asked; the answer is no"
```

The cleanest way to say what separates them is in the [capabilities article](/programming/capabilities.html)'s vocabulary. A sandbox can take away ambient *designation*, ambient *authority*, or both. Remove designation and the resource is unnameable — there is no request to intercept, because there is nothing to ask for. Leave designation and remove authority, and the request stays expressible while something adjudicates it. In an object capability the two are fused, which is why an ocap system gets the first for free.

This is the third of the three axes that article set out, and it is genuinely independent of the other two:

```text
granularity   how small is the principal?              capabilities article
designation   selected and joined, or ambient?         capabilities article
enforcement   unnameability or adjudication?           here
```

Independent in both directions. A container is fine-grained, fully ambient, and mostly adjudicated. `chroot` buys unnameability while leaving designation ambient. An ACL check on a file descriptor is adjudication over a non-ambient designation. All the combinations exist, which is why none of the three substitutes for another.

These are functions, not technology categories. A mechanism may provide either or both. Namespaces alter the universe a process can name, one kernel-object class at a time. A VM does it for a whole machine. WASI does it by omitting APIs. Seccomp adjudicates entry to the syscall interface using syscall numbers and scalar arguments. LSMs adjudicate operations on resolved kernel objects.

The strongest designs compose them: make the raw authority **unnameable**, then expose a **restricted, adjudicated** capability in its place.

```text
real GitHub token
    absent from the workload entirely

placeholder handle
    visible to the workload
    usable only through the gateway
    valid only for approved operations
```

That is not layering one filter over another. It is *authority attenuation* — replacing possession of a powerful resource with permission to request a smaller set of effects. Which is the capabilities article's story, arriving from the enforcement side.

Unnameability only covers what is absent. A component holding two references can still use the wrong one, and that is excess authority rather than ambient authority. No amount of unnameability touches it.

That is the granularity axis, not the designation axis. Shrinking the box is a different project from controlling how authority enters it, and the extrinsic route — a policy, in a global namespace, naming a subject — is what every mechanism in this article does. It reaches the instance rung and stops, because below it the policy author would be rewriting the program. Least authority is a separate discipline from capability discipline, which is why the last of the six questions at the end of this article asks what an interpreter can do when its policy is wrong.

### The layering leaks, and it should

It is tempting to present this series as a clean stack: the first two articles are representation, this one is enforcement. That is mostly true and it is worth noticing exactly where it fails.

Object-capability reachability is both. It is a *representation* of authority — the graph says what exists — and simultaneously an *enforcement strategy*, because a component cannot invoke what it cannot name. There is no separate checking step to bypass. The unnameability column above is, read another way, just the capability model applied to whatever resource class you care about.

Which is also the limit of the analogy. Unnameability is the broader category. A mount namespace removes names while leaving ambient authority intact over everything still visible, so `chroot` is not a capability system. Designation and authority coincide only when the name you hold is the only way to reach the object.

The cleanest way to hold the pair is in the [square matrix](/programming/authorization-models.html#make-both-axes-the-same-set). Both approaches are trying to make the subject's row small, and they arrive from opposite directions:

```text
construction   the row starts empty and grows by reference-passing
subtraction    the row starts full and the columns get cut away
```

Same target, opposite mutation rules. Construction is edited by the holder, at runtime, monotonically downward, along edges that already exist. Subtraction is edited by an external configurator, before the process starts, from a global namespace, with no limit on what it may grant.

And subtraction cannot mediate. You can remove a column. There is no namespace operation for "Alice reaches X only through Bob," because the thing in the middle has to be an entity with a row *and* a column, and namespaces have visibility rather than entities.

Which produces the pattern worth carrying into the rest of this article:

> **Subtraction plus mediation is construction.**

The moment removal is not enough and you need to interpose, you introduce something that holds the real authority and speaks a protocol — a FUSE daemon, a proxy inside the network namespace, a broker. That thing is a membrane. You have rebuilt the capability system in a different vocabulary, one resource class at a time, and Part 4 is a long worked example of exactly that.

ACLs do not have this property. An ACL is purely a representation, and it is inert until some object manager consults it. That asymmetry is the single most useful thing to carry out of these two articles, and it explains why capabilities keep reappearing in both halves of the discussion while ACLs stay firmly in the first.

The confused deputy is that asymmetry in one example. Hardy's compiler is handed a pathname, and a pathname is a designator anyone can utter. The resulting check is an adjudication, and it can be made correct: propagate the caller's identity and the deputy has enough to decide. Hand the compiler a file descriptor instead and there is nothing to decide, because it never held a name for the billing file. Expressible versus unrepresentable is the same seam as adjudication versus unnameability, seen from the representation side.

## Three properties people conflate

"Policy expressivity" collapses three independent questions. Separating them makes most comparisons tractable.

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

### Non-bypassability is none of the three

It is a property of the **topology**, not of a policy language or a hook. The question is only ever: can the workload reach the protected resource by some other path?

Stated as a condition to satisfy:

> **For every effect the workload can attempt, either no path to the resource exists, or every path passes through a point that decides.**

The two disjuncts are the two strategies above, and the first one involves no enforcement point at all. Unnameability is not a check that reliably says no. It is the absence of anything to check. Which is also why "is there a PEP?" is never the interesting question — a PEP is always a PEP for some class of effect, and what you actually have to establish is that the union of them leaves no path uncovered.

The clearest illustration is the humble proxy. `HTTP_PROXY` is a cooperative convention. A workload that wants to ignore it simply ignores it, and no amount of policy sophistication inside the proxy changes that. The same proxy becomes genuine enforcement when the topology closes: force routing with nftables or TPROXY, or give the workload a network peer that is the proxy, with no NAT and no alternate route.

Same code, same policies, same expressivity. Enforcement in one deployment and decoration in the other. This is why arguing about policy languages before establishing the topology is almost always wasted effort.

## Linux is a toolkit, not a primitive

Linux has no single sandbox primitive. It has a collection of mechanisms, each controlling a different class of effect, and every real sandbox is a composition.

1. `fork()` + `setuid()` + `exec()` — memory isolation, though only in one direction
2. `chroot()` and mount namespaces — filesystem view
3. `seccomp()` — allow or deny syscalls by number and scalar arguments
4. `prctl()` — assorted process-level restrictions
5. Namespaces — virtualize a kernel subsystem at a time: PID, IPC, NET, MNT, UTS, user, cgroup, time
6. DAC and Linux capabilities — the traditional permission checks, and root split into pieces
7. LSMs — SELinux, AppArmor, Smack, TOMOYO, Landlock, BPF-LSM

![](/assets/authority-enforcement/linux-security-mechanisms.png)

Items 1 and 6 are one mechanism seen twice, and [`setpriv`][setpriv] is where it becomes usable. A single `exec` sets the uid and gid, clears supplementary groups, trims the inheritable, ambient and bounding capability sets, locks securebits, requests an LSM label, and sets `no_new_privs`. The whole credential tuple, chosen by the launcher rather than by the program. Hand-rolling it is a bug farm: unchecked `setuid` return values, supplementary groups left behind, a bounding set trimmed after the point where it would have mattered.

`no_new_privs` is the load-bearing bit. Without it the restriction is not monotonic — exec a setuid binary and the authority comes back — and an unprivileged process cannot install a seccomp filter at all. It is the precondition for everything further down the list that a workload applies to itself.

The LSM framework deserves the most attention, because it is Flask brought into Linux and it sits at a specific and well-chosen place. Rather than interposing at syscall entry, the kernel first resolves user-supplied names and handles into internal objects, *then* calls the hook immediately before the security-relevant operation. The question it asks is explicit:

```text
May subject S perform operation OP on kernel object OBJ?
```

This is exactly what separates an LSM from seccomp. Seccomp sees a syscall number and scalar arguments; it cannot dereference a pathname pointer or reason about the resolved inode. An LSM sees the object and the kernel context that produced it, no matter which syscall route got there.

That difference has a direct consequence for policy soundness. Path-based policy has to account for symlinks, hard links, rename, bind mounts, already-open handles, and the gap between a directory entry and an inode. Label-based policy attached to kernel objects sidesteps much of that aliasing, at the cost of policies that map less directly onto how people describe a workspace. Neither choice is free.

![](/assets/authority-enforcement/linux-security-frontends.png)

The same primitives wear different user-facing clothes, which is a large part of why the landscape looks more fragmented than it is.

The credentials row is the one to read twice. Every supervisor on that chart reimplements `setpriv` internally: the OCI `process` block is its flag list rendered as JSON, systemd spells it `User=`, `CapabilityBoundingSet=`, `AmbientCapabilities=` and `NoNewPrivileges=`, and Chrome's zygote drops to an unprivileged uid and sets `no_new_privs` before installing its filter. Nothing else on the chart is driven by all of them. Recent versions also grew `--landlock-access`, `--landlock-rule` and `--seccomp-filter`, which quietly moves the tool out of the single-primitive column.

It is also the cleanest case of the three axes moving one at a time. Credentials are ambient authority and nothing else. Shrink them and every name still resolves — `open("/etc/shadow")` stays a perfectly expressible request — only the answer changes. No namespace, no label, no hook, no unnameability. Authority subtracted while designation stays exactly as ambient as it was.

The vocabulary collides here, and the collision is worth naming. A Linux *ambient capability* is authority that survives `exec` with nobody designating anything, which is ambient authority in this series' sense. `--ambient-caps` is the knob that grants it, and `no_cap_ambient_raise` is the securebit that takes the knob away.

## Editing the object side

Every mechanism above changes the subject. The matrix has two projections, and the other one is just as mutable. `setfacl` on a file, `chcon` on its label, `GRANT` and `REVOKE` in a database, an ACE for a package SID on a Windows object, a bucket policy, a protected branch. None of it touches the workload. The authority shrinks anyway.

Sandboxes almost never work this way, and the reason is mutation locality. Confining a workload means denying everything except a few things. Stated on the object side, "everything" is unbounded, and it keeps growing while you work — a file created after you ran `setfacl` carries whatever the default gives it. Inherited ACEs and default ACLs cover a subtree. Nothing covers the objects that do not exist yet. One `setpriv` covers all of them.

Each edit is also global. Change the object and you change it for every subject that reaches it. Locking one workload out of `/etc/passwd` by editing `/etc/passwd` breaks every other reader, so the object-side move is only safe once the workload holds a principal nobody else shares — which is a subject-side act. The two are not alternatives. The second depends on the first.

And object state is durable where a process is not. Credentials cost nothing per `exec`. You cannot relabel a filesystem per tool call.

Two things the object side buys that nothing else does. An ACL hangs on the inode, so hard links, renames and bind mounts cannot walk around it, which is the aliasing soundness path-based policy has to work for. And it holds after a total escape. Branch protection refuses the force-push whether the push came from the sandbox, from a process that broke out of it, or from a laptop in another country. Every mechanism in this article stops working the moment its boundary fails. Policy at the resource has no boundary to fail.

One trap comes with it, and it is the next section wearing different clothes. Unix checks permission at `open`. `chmod 000` does nothing to a descriptor somebody already holds. Object-side edits bind at the next resolution and never retroactively.

## What can change between check and use

Always invoked, tamperproof, verifiable. All three can hold and the monitor can still authorize the wrong thing, because none of them says the decision was still true when the effect happened.

The reason is that almost nothing in an authorization question is supplied directly. The subject and the object arrive as *references*, and each one resolves against state somebody else can modify.

```text
subject reference ──resolve──► subject state ──┐
                                               │
object reference  ──resolve──► object state ───┤
                                               ├──► decision
policy store      ──query──────────────────────┤
                                               │
environment       ─────────────────────────────┘
```

Four inputs, four independent clocks. They are the four terms of the function [Part 1](/programming/authorization-models.html) started from — `f(subject, action, resource, context)` — and the useful observation is that three of them arrive as references that resolve late, while one does not. The action is supplied literally in the request. It is the only argument that cannot go stale, and correspondingly the only one nobody writes a CVE about.

**Object binding.** The classic case, and the reason the LSM hook sits where it does. A pathname gets resolved twice:

```text
t0   access("/tmp/foo")  →  inode A   → allowed
t1   open("/tmp/foo")    →  inode B
```

Check and use named the same string and reached different objects. A file descriptor closes this by resolving once and binding the result — `read(7)` cannot be redirected by renaming anything. That is what `openat`, `O_PATH` and Capsicum are for, and it is designation-equals-authority showing up as a race.

**Subject binding.** The same indirection exists on the other side and gets far less attention. Ambient credentials are a *reference to authority*, resolved at the moment of use. Check under one credential context and act under another — a dropped privilege, a changed EUID, a recycled thread pool — and you have the same bug with the axes swapped. Setting the credentials once, from outside, before the workload starts is what `setpriv` buys: the program never holds authority it would have had to remember to drop.

```text
pathname            indirect reference to an object
ambient credential  indirect reference to authority
```

Both resolve late. Both can resolve differently.

**Authorization state.** Neither binding has to move for the answer to change. Remove Alice from a group and every decision derived from that membership is stale, with the same subject and the same object throughout. This is not a race inside the monitor. It is the monitor's inputs having a lifetime, which is exactly why Flask needs a revocation channel: a cached access vector is a decision that outlived its premises.

**Environment.** Device posture, time of day, risk score. This is `f`'s context argument, and it is the one the access matrix had no axis for in the first place. Same shape as the others, least often modelled, and the usual reason a "zero trust" deployment is less continuous than its diagram.

Which makes the tension from the end of the capabilities article concrete. Re-evaluate on every operation and the inputs stay fresh, but every operation pays the resolution cost and re-opens all four races. Materialize the decision into a capability and the bindings freeze — that is the point of it — but a frozen binding is indistinguishable from a stale one once the source of truth moves.

```text
re-evaluate    fresh inputs, repeated resolution races
materialize    stable bindings, revocation debt
```

Neither end is safe on its own. A file descriptor eliminates the object-binding race and creates a revocation problem in the same stroke. That is not a defect in the mechanism. It is the trade that appears wherever a system caches a derived fact, and authorization gets no exemption from it.

## Interface and mechanism are separable

Containers make the point better than any argument could.

A "container" is defined by a contract — an image, a bundle, a lifecycle — and never by a mechanism.

![image](/assets/authority-enforcement/oci-stacks.png)

Behind the same OCI runtime interface you can put wildly different enforcement:

```text
container contract
       │
       ├── runc    → namespaces, cgroups, host kernel
       ├── runsc   → gVisor, a userspace kernel
       └── kata    → a full VM
```

![image](/assets/authority-enforcement/container-runtimes.png)

These are interchangeable to the consumer and not remotely comparable as boundaries. "We run it in a container" says nothing about the security properties. It says the workload was packaged a certain way.

This is the capabilities article's policy/mechanism separation showing up one level down. The interface is the policy — what the workload may assume about its environment. The runtime is the mechanism. Keeping the seam there is what lets you change your mind about isolation strength without repackaging anything.

## Two systems that got the shape right

**WebAssembly and WASI** are the cleanest modern instance of unnameability followed by adjudicated reintroduction. A Wasm module starts with linear memory and computation. It inherits no ambient filesystem, network, environment, or clock. Everything useful arrives as an import the host chose to supply.

```text
Wasm module
    → imported WASI operation
        → host runtime
            → selected filesystem, socket, clock, or service
```

The module cannot perform a host syscall behind the runtime's back, because there is no syscall instruction to perform. Its effect vocabulary is also legible: `open-at` or a typed component call carries far more meaning than a block offset. Unnameability comes free from the execution semantics rather than from a device model someone had to get right. The import list doubles as an audit surface: a static, exhaustive enumeration of what the component can reach, which is the local form of review the capabilities article argues capabilities keep.

**Effect systems** reach the same separation from the language side. Instead of letting a function perform hidden I/O, the type system records the effect, and a handler supplies its interpretation.

```text
computation requests Network.send
    → handler may execute, deny, record, transform, or emulate it
```

Note what the handler can do. It is not restricted to allow or deny — it can synthesize a result, maintain a budget, or delegate the decision elsewhere. That is the programmability axis, at the most semantic legibility available anywhere.

But a type-and-effect system is not automatically a security boundary. It may prove that *cooperative* source code declares its effects while native code, FFI, `unsafe`, or a compromised runtime walks straight past the handler. It becomes confinement only when the language and runtime together guarantee that every relevant effect is captured. Anderson's first property, restated for a compiler.

The transferable lesson is not "adopt an effect language". It is that interfaces get easier to govern when the effect is named at the level policy cares about. `publishArtifact` is a better policy event than a sequence of writes and HTTP requests — but only if the lower-level routes cannot reach the same outcome.

## seL4 as the meeting point

The capabilities article used seL4 to argue that capabilities are not always cached ACL decisions: in a separation kernel, the capability graph *is* the authority, with no authoritative copy elsewhere. That was a claim about representation. Here is the enforcement half.

seL4 stores capabilities in kernel objects called CNodes. Userspace never touches a capability directly; it names a slot, and the kernel dereferences it. All authority — memory, execution, IPC endpoints, interrupts — is a capability, obtained by retyping untyped memory. There is no ambient authority anywhere in the system, including the ability to allocate.

Two mechanisms make the graph governable rather than merely descriptive:

**The grant right.** Holding a capability does not imply the ability to share it. Passing a capability over an endpoint requires the `grant` right on that endpoint. From the [seL4 retrospective][10-years-sel4]:

> Capabilities also cleanly solved another issue with original L4, that of limiting communication. The original model relied on an (inflexible) process hierarchy and redirection to a monitor process ("chief") to limit data flow. Capabilities provide a cleaner, simpler and low-overhead model: Having a privilege does not in itself imply the ability to share that privilege, an additional grant right is needed to pass on capabilities.

That is Saltzer and Schroeder's second objection — propagation control — answered structurally rather than by a registry.

**The capability derivation tree.** The kernel tracks which capabilities were derived from which. `seL4_CNode_Revoke` removes all descendants of a capability in one operation. That is the third objection answered too, without indirection and without a lookup table, because the kernel already holds the provenance.

So seL4 is where the two articles meet:

> **Capabilities describe authority structurally. A trusted, verified reference monitor makes that structure non-bypassable.**

And the separation of policy from mechanism survives: seL4 enforces whatever capability graph exists. Deciding what graph *should* exist — which components get which endpoints — is a system-design question that lives entirely outside the kernel, usually in a static configuration produced before boot.

## Runtime versus analysis time

One last axis, because it explains why some security properties cannot be enforced by a monitor at all, however well placed.

There are three ways to establish that something cannot happen:

- **Runtime monitoring** enforces safety trace properties. Access control, type checks, assertions, capability discipline. It is your first line of defense and it is fundamentally limited to "is this single step okay?"
- **Static analysis** verifies hyperproperties by reasoning over all traces at once. Information-flow type systems, model checking, abstract interpretation. Strictly more powerful than monitoring for security properties, but incomplete, and limited to properties of the code.
- **Cryptographic enforcement** converts a hyperproperty into a trace property by making distinguishing information computationally unavailable, then enforces the result at runtime. It is the only mechanism that can enforce a hyperproperty *during* execution — at the cost of computational hardness assumptions the other two do not need.

The difference in one line each:

```text
"We proved no one can break in."     static analysis
"We're watching for break-ins."      runtime monitor
"There's nothing to steal."          capabilities
```

For trace properties, runtime monitoring is complete and static analysis is merely sound. For hyperproperties — non-interference, most confidentiality claims — static analysis can verify what monitoring cannot express. And capabilities sidestep the hierarchy entirely by operating at the level of system design rather than system verification. The attack does not get denied; it becomes incoherent.

This is why "add a check" is sometimes the wrong instinct. If the property you want is about what an observer can *infer*, no reference monitor will get you there.

## The architecture is recursive

None of these are alternatives. A Wasm component runs inside a Linux guest constrained by an LSM. The guest presents an attenuated handle to a host broker. The broker uses a scoped OAuth token against a service whose own policy protects the resource.

At every boundary, the same six questions:

1. What computation is inside the boundary?
2. What raw authority has been made unnameable?
3. What handle or request vocabulary crosses it?
4. Which trusted component interprets that vocabulary?
5. Can the requester bypass that interpreter?
6. What is the interpreter's maximum authority if its policy is wrong?

Question five is Anderson's first property. Question six is the one people skip, and it is the one that decides how bad your worst day is.

## What this does not solve

Everything above assumes the reference monitor is a thing you can point at. A kernel. A hypervisor. A runtime. One component, in one trust domain, sitting in one path.

Modern workloads do not have that shape. A single logical operation crosses a process, a machine, an API, a database, a cloud service, a user identity, and an organizational policy. There is no kernel spanning all of that.

The answer is not that the reference monitor becomes distributed. It is that it gets **relocated and replicated**: several monitors, each complete within its own boundary, each seeing a different vocabulary, each surviving a different failure. The guest kernel mediates guest objects. The host mediates external effects. The resource server enforces its own invariant. No single one of them is complete, and the composition has to be designed rather than assumed.

Which is exactly the problem LLM agents force you to confront, because an agent's authority is not known until it runs. That is Part 4.

## References

1. [Computer Security Technology Planning Study][computer-security-technology-planning] — Anderson, 1972; the reference monitor
2. [The Flask Security Architecture][flask-security-architecture] — object managers, security server, access-vector caching, revocation
3. [Linux Security Modules: General Security Support for the Linux Kernel][linux-security-modules-general] — the original LSM design
4. [Linux Security Module usage][linux-security-module-usage] and [LSM development][lsm-development]
5. [AppArmor — Where Do LSMs Fit?][apparmor-where-do-lsms] — syscall filtering versus DAC, MAC, and resolved-object hooks
6. [Landlock][landlock] — unprivileged monotonic self-restriction
7. [BPF LSM programs][bpf-lsm-programs]
8. [Linux namespaces][linux-namespaces] and [capabilities][linux-capabilities]
9. [`setpriv`][setpriv] — the credential tuple in one exec: uid, gid, the three capability sets, securebits, `no_new_privs`, LSM labels, Landlock and seccomp
10. [Software isolation in Linux][software-isolation-linux] — the mechanism inventory
11. [Capsicum: Practical Capabilities for UNIX][capsicum-practical-capabilities-unix]
12. [10 years seL4][10-years-sel4] — the grant right and what verification bought
13. [seL4 reference manual][sel4-reference-manual] — CNodes, untyped retyping, the capability derivation tree, `Revoke`
14. [WebAssembly Component Model][webassembly-component-model] and [WASI security principles][wasi-security-principles]
15. [Handling Algebraic Effects][handling-algebraic-effects] — effect handlers as programmable interpretations

[10-years-sel4]: https://microkerneldude.org/2019/08/06/10-years-sel4-still-the-best-still-getting-better "10 years seL4"
[apparmor-where-do-lsms]: https://apparmor.net/about/lsm_introduction/ "AppArmor — Where Do LSMs Fit?"
[bpf-lsm-programs]: https://docs.kernel.org/bpf/prog_lsm.html "BPF LSM programs"
[linux-capabilities]: https://man7.org/linux/man-pages/man7/capabilities.7.html "capabilities"
[capsicum-practical-capabilities-unix]: https://www.usenix.org/conference/usenixsecurity10/capsicum-practical-capabilities-unix "Capsicum: Practical Capabilities for UNIX"
[computer-security-technology-planning]: https://csrc.nist.gov/csrc/media/publications/conference-paper/1998/10/08/proceedings-of-the-21st-nissc-1998/documents/early-cs-papers/ande72.pdf "Computer Security Technology Planning Study"
[lsm-development]: https://docs.kernel.org/security/lsm-development.html "LSM development"
[flask-security-architecture]: https://www.cs.cmu.edu/~dga/papers/flask-usenixsec99.pdf "The Flask Security Architecture"
[handling-algebraic-effects]: https://arxiv.org/abs/1312.1399 "Handling Algebraic Effects"
[landlock]: https://docs.kernel.org/userspace-api/landlock.html "Landlock"
[linux-namespaces]: https://man7.org/linux/man-pages/man7/namespaces.7.html "Linux namespaces"
[linux-security-module-usage]: https://docs.kernel.org/admin-guide/LSM/index.html "Linux Security Module usage"
[linux-security-modules-general]: https://www.usenix.org/legacy/publications/library/proceedings/sec02/full_papers/wright/wright_html/ "Linux Security Modules: General Security Support for the Linux Kernel"
[sel4-reference-manual]: https://sel4.systems/Info/Docs/seL4-manual-latest.pdf "seL4 reference manual"
[setpriv]: https://man7.org/linux/man-pages/man1/setpriv.1.html "`setpriv`"
[software-isolation-linux]: https://nikmav.blogspot.com/2015/06/software-isolation-in-linux_15.html "Software isolation in Linux"
[wasi-security-principles]: https://github.com/bytecodealliance/wasi.dev/blob/main/docs/security.md "WASI security principles"
[webassembly-component-model]: https://component-model.bytecodealliance.org/design/components.html "WebAssembly Component Model"
