---
title:  "LLM sandboxing: making the gateway correct and unavoidable"
series: "Authorization, Part 4"
series_url: "/programming/authorization-series-intro.html"
category: programming
date:   2026-09-04
---

> This is Part 4 of a five-part [series on authorization](/programming/authorization-series-intro.html).
>
> 0. **[Prologue: Who is the adversary](/programming/who-is-the-adversary.html)** — five positions the attacker has occupied, and why identity stopped being the useful thing to key on.
> 1. **[Authorization models](/programming/authorization-models.html)** — what every system computes, and who may change it.
> 2. **[Capabilities](/programming/capabilities.html)** — authority you hold, not authority you are.
> 3. **[How authority is enforced](/programming/authority-enforcement.html)** — what makes any of it binding.
> 4. **LLM sandboxing** — the gateway, correct and unavoidable.

- [Part 0 — Why agents break the assumptions](#part-0--why-agents-break-the-assumptions)
  - [Data becomes executable](#data-becomes-executable)
  - [The confined workload is also a delegate](#the-confined-workload-is-also-a-delegate)
  - [Policy cannot be enumerated in advance](#policy-cannot-be-enumerated-in-advance)
  - [The tool call is a semantic chokepoint](#the-tool-call-is-a-semantic-chokepoint)
  - [The shape of the answer](#the-shape-of-the-answer)
- [Part I — DECIDE](#part-i--decide)
  - [The decision point, with a task in it](#the-decision-point-with-a-task-in-it)
  - [AuthZEN: standardizing the seam](#authzen-standardizing-the-seam)
- [Part II — DELEGATE](#part-ii--delegate)
  - [From decision to capability](#from-decision-to-capability)
  - [Authority is temporal](#authority-is-temporal)
  - [Why not just call the PDP on everything, forever](#why-not-just-call-the-pdp-on-everything-forever)
  - [How far up does the property survive](#how-far-up-does-the-property-survive)
- [Part III — EXERCISE](#part-iii--exercise)
  - [Two coupled subsystems](#two-coupled-subsystems)
    - [1. The compute sandbox](#1-the-compute-sandbox)
    - [2. The capability gateway](#2-the-capability-gateway)
  - [The runtime–gateway contract](#the-runtimegateway-contract)
  - [The residual interface](#the-residual-interface)
  - [Programmable gateways versus declarative LSMs](#programmable-gateways-versus-declarative-lsms)
  - [Filesystem mediation is a resource service](#filesystem-mediation-is-a-resource-service)
    - [The path-policy soundness trap](#the-path-policy-soundness-trap)
  - [Protocol gateways can see what kernels cannot](#protocol-gateways-can-see-what-kernels-cannot)
  - [Secret possession is not authority containment](#secret-possession-is-not-authority-containment)
  - [Threat model by enforcement plane](#threat-model-by-enforcement-plane)
  - [A complete enforcement stack](#a-complete-enforcement-stack)
  - [Cost and compatibility](#cost-and-compatibility)
  - [Replaceable runtimes, stable authority boundary](#replaceable-runtimes-stable-authority-boundary)
  - [The landscape, scored against the contract](#the-landscape-scored-against-the-contract)
  - [Recommended architecture](#recommended-architecture)
- [Part IV — What is left over](#part-iv--what-is-left-over)
  - [Agent-specific threats](#agent-specific-threats)
    - [Inference-endpoint exfiltration](#inference-endpoint-exfiltration)
  - [Harness placement and the trust split](#harness-placement-and-the-trust-split)
  - [The seam nobody has named](#the-seam-nobody-has-named)
  - [Conclusion](#conclusion)
- [References](#references)
  - [Primary implementation sources](#primary-implementation-sources)
  - [Policy and decision](#policy-and-decision)
  - [Foundations](#foundations)
  - [Agent frameworks and research](#agent-frameworks-and-research)
  - [Landscape and performance](#landscape-and-performance)

Sandboxing discussions usually begin with the wrong noun. They ask whether untrusted code should run in a container, a microVM, gVisor, WASI, or a language runtime. Those choices matter, but they answer only **where computation happens**. They do not answer **what authority that computation can exercise**.

A process inside a perfectly isolated VM can still exfiltrate source code through an allowed API, mutate a host-mounted repository, publish a poisoned artifact, spend cloud credentials, or invoke a token's full administrative authority. Compute isolation protects the host kernel and memory. It does not, by itself, protect resources deliberately exposed to the workload.

A complete design therefore consists of two coupled systems:

> **A replaceable compute sandbox connected to a non-bypassable, host-trusted capability gateway.**

The compute sandbox removes ambient access to the host. The capability gateway selectively reintroduces useful authority as narrow, adjudicated operations: read this workspace, call this API method, publish this artifact, connect using this database role. Raw credentials and host resources remain outside the guest.

The word *coupled* is doing the work. A proxy is not enforcement if the workload can route around it. A VM does not contain authority if it directly mounts host state or receives durable credentials. These are not two systems cooperating: they are one reference monitor whose two required properties are supplied by different technologies. The gateway is the decision point and must be **correct** — right policy, right answer, real credential held outside the guest. The sandbox decides nothing and must make the gateway **unavoidable**, which is a claim about topology rather than about policy. That is the [enforcement article](/programming/authority-enforcement.html)'s PEP/PDP split, with the enforcement point's non-bypassability delegated to whatever substrate you chose. Drop either half and you do not have a weaker sandbox. You have no reference monitor at all.

The condition to aim at is easier to state than to satisfy:

> **For every effect the workload can attempt, either no path to the resource exists, or every path passes through a point that decides.**

Two disjuncts, and they correspond to the two things a sandbox can take away. Strip ambient *designation* and the resource becomes unnameable — there is no request to intercept, because there is nothing to ask for. Strip ambient *authority* and leave designation intact, and the request stays expressible while something adjudicates it. Every mechanism in this article is one of those two moves applied to one class of effect, and the engineering claim is never that a decision point exists. It is that the union of them leaves no path uncovered.

The first three articles supply that vocabulary: how authority is represented, what the capability property actually is and where it can be bought, then what makes a limit real. This article is what happens when you point both at a program whose authority is not known until it runs.

![sandboxing-taxonomy](/assets/llm-sandbox/confinement-hierarchy.png)

# Part 0 — Why agents break the assumptions

Most writing on "AI sandboxing" is really writing on sandboxing, with agents supplying the motivation. That framing undersells the delta. Four assumptions that hold for ordinary untrusted code fail for agents, and each failure moves work from configuration time to runtime.

## Data becomes executable

Generic sandboxing assumes that code is untrusted and data is inert. An LLM weakens that distinction: any README, issue, webpage, source comment, tool output, or retrieved document may change subsequent behavior.

Compute containment and capability mediation primarily govern outbound effects. They do not decide whether an inbound sentence is an instruction. Prompt injection rides through the same channels the agent legitimately needs.

The practical answer is not an "input sandbox." It is to assume intent can be corrupted and ensure that resulting effects still encounter narrow capabilities, trusted enforcement, and upstream policy.

There is an older name for this failure, and using it changes what you look for. **Prompt injection is a confused deputy attack.** Injected text utters a designator — a path, a URL, a repository, a tool name. The agent's ambient authority supplies the rest. The agent is Hardy's compiler: not malicious, not compromised, simply unable to tell which of its powers a given request was entitled to invoke, because the request carried a name and the authority came from somewhere else.

That reframing is useful because the confused deputy has a known cure and it is not "be more careful." You cannot fix the model's judgment, and every mitigation that depends on the agent correctly distinguishing instruction from data is ACL-plus-context — the correct answer is expressible, and the deputy still has to ask. What you can do is shrink the set of designators that mean anything. If the agent holds a reference to one file rather than a `read_file` tool plus a path argument, the injected instruction has nothing to designate.

## The confined workload is also a delegate

Traditional confinement limits software you want to do as little as possible. An agent is valuable precisely because it can act broadly on a user's behalf.

The core tension is not merely least privilege. It is **useful delegation without ambient authority**.

The [capabilities article](/programming/capabilities.html) supplied the underlying object-capability model: do not hand a delegate a global name and durable credential. Hand it a reference to a narrower operation, with contextual caveats, and retain the ability to revoke or decline each invocation. Agents make that old design problem continuous. They form new subgoals, encounter new resources, and request new authority throughout a run, so capability issuance becomes part of the runtime protocol rather than a one-time launch configuration.

## Policy cannot be enumerated in advance

You can audit a binary and write an AppArmor or SELinux profile. You cannot fully enumerate an agent's future plan, because discovering the plan is the workload.

The design target changes from "configure the correct static profile" to:

```text
deny by default
make requests legible
make grants cheap
scope each grant narrowly
make expiry automatic
make denial recoverable
```

Most sandbox abandonment happens at this allow-loop. If granting a legitimate exception is slow, opaque, or breaks the agent irrecoverably, users widen the static envelope until little protection remains.

## The tool call is a semantic chokepoint

Generic workloads rarely expose a semantic chokepoint above syscalls. Agents do: the tool call.

A tool hook can understand:

```text
force-push main
publish package
modify CI workflow
open pull request
send message
deploy service
```

That vocabulary is enormously useful, but tool governance is not a containment boundary. Arbitrary code can bypass the tool API and use lower-level filesystem or network operations. Its proper role is semantic governance:

```text
tool hook proposes or rejects intent early
capability gateway authorizes the resulting external effect
remote resource server enforces its own invariant
```

For a protected branch, a `PreToolUse` hook can reject `git push --force`; an HTTP/Git-aware gateway can restrict `git-receive-pack`; GitHub branch protection can refuse the update at the authoritative resource. The layers improve explanation, containment, and final correctness respectively.

## The shape of the answer

Take those four together and the architecture writes itself as three phases. Each one is a question the previous three articles prepared:

```text
DECIDE      What authority should exist for this task?
            Policy, evaluated at runtime, because it cannot
            be enumerated in advance.
                    ↓
DELEGATE    Give the agent that authority and nothing else.
            Materialized, attenuated, scoped, expiring —
            the capability story.
                    ↓
EXERCISE    Ensure every effect stays inside it.
            Complete mediation in a trust domain the agent
            cannot reach — the reference monitor.
```

Mapped onto components:

```text
policy / PDP
     ↓
delegated authority
     ↓
agent
     ↓
sandbox / PEP
```

A fifth consequence falls out of the first four rather than standing beside them: authority becomes temporal. An agent's justified authority changes turn by turn, so a grant is a thing that should end. That belongs under DELEGATE, and it is where Part II goes.

Most of this article is about EXERCISE. Not because the first two phases are easy, but because they are largely the enterprise authorization problem with a new subject, while EXERCISE is where the engineering is unfamiliar and where the interesting failures are.

# Part I — DECIDE

## The decision point, with a task in it

The enforcement article established the decomposition: a PEP sits in the path and cannot be bypassed, a PDP evaluates policy and need not be in the path at all. Nothing about that changes for agents. What changes is what the PDP can be asked.

A traditional PDP answers a question about a subject and a resource. An agent PDP has more to work with, and needs it:

```text
user            who delegated this run, and what may they do at all
agent           which agent, which version, which trust tier
action          the operation actually requested
resource        the object it targets
task            the stated purpose of the run
context         time, epoch, prior actions this run, budget consumed
relationships   org structure, ownership, project membership
risk            reversibility, blast radius, whether a human is watching
```

The `task` and `context` rows are the new ones, and they are why a static profile cannot do this job. "May this agent push to `main`" has no answer. "May this agent, acting for this user, push to `main` in a run whose stated task is fixing a test, at minute forty of that run, having already been denied twice" has one.

The cost is that the PDP now depends on facts the agent itself supplied. A stated task is an assertion by a component that may be under an attacker's influence. Treat it as an input that can *narrow* a decision and never as one that can widen it: a task claim is evidence for denial, not a grant. The authority ceiling has to come from facts the host knows independently — which user launched this run, which sandbox identity is on the channel, which grants were issued.

## AuthZEN: standardizing the seam

Here is the practical problem. An agent deployment has an unusual number of enforcement points, and they are all different: a filesystem provider, an HTTP gateway, an MCP broker, a database proxy, a tool hook, a CI check. Left alone, each grows its own policy configuration format, and the organization ends up with six half-policies and no way to reason about their union.

[AuthZEN](https://openid.net/wg/authzen/), from the OpenID Foundation, standardizes the wire contract between PEP and PDP. It is explicitly **not** a policy language. It says nothing about how a decision is reached. It standardizes the shape of the question and the shape of the answer:

```text
Subject    who is asking          { type, id, properties }
Action     what they want to do   { name, properties }
Resource   what they want it on   { type, id, properties }
Context    everything else        { ... }

        ──► decision: true | false, plus optional context
```

That is `f(subject, action, resource, context)` from the [first article](/programming/authorization-models.html), promoted from a way of describing what every model computes into a wire format anything can speak.

The four-part request is the whole idea, and its value is compositional. Any enforcement point that can normalize its native effect into S/A/R/C can be governed by any decision engine that speaks the protocol:

```text
                   ┌── local Cedar
PEP ──AuthZEN──►   ├── local Rego / OPA
                   ├── a Zanzibar-style relationship service
                   └── the corporate authorization system
```

Swap the engine without touching the enforcement points. Add an enforcement point without touching the engine. This is the policy/mechanism seam from the capabilities article, standardized as a protocol.

Two honest caveats. First, AuthZEN is a moving specification — the evaluation API is the stable core, with batch evaluation and search endpoints at varying maturity, so check the current draft before building against details. Second, and more important: a standard request shape does nothing for non-bypassability. The enforcement article's point stands unchanged. A beautifully normalized S/A/R/C request from a PEP the workload can route around is decoration. The protocol standardizes the question; the topology decides whether the question gets asked.

# Part II — DELEGATE

## From decision to capability

The [capabilities article](/programming/capabilities.html) ended with a one-directional pipeline and the note that the interesting engineering is in the arrow:

```text
global, queryable policy
        ↓
authorization decision
        ↓
materialized authority
        ↓
capability
```

For agents, that arrow is where the design happens. A PDP returns a boolean. What you do with it determines everything about the system's behaviour under load, under partition, and under compromise.

Consume it and discard it, and you have a pure adjudication architecture: every effect is a fresh round trip, policy is always current, and the PDP is in the critical path of everything. Materialize it, and the decision becomes a thing the agent holds — which is exactly a capability, now produced by a policy engine rather than handed over by a person.

The crucial detail is *who* holds it. The materialized capability lives on the host:

```text
PDP decision
     ↓
host mints a lease
     - bound to sandbox identity
     - scoped to operation and resource
     - epoch, budget, expiry
     ↓
guest receives an opaque handle
```

The guest holds a name for the lease. The host holds the lease. This is unnameability applied to the grant itself, and it is what separates possession from use: stealing the handle gets you nothing you could not already ask the gateway to do.

Worth naming what that is. A handle table the host owns, holding entries the guest can only reference by index, where the reference both designates the operation and conveys the right to invoke it, and where the guest can only pass a handle to something it already reaches through the gateway — that is an object-capability system. Model 4, in the capabilities article's terms, built from scratch for the host–guest boundary. The interesting question for the rest of this article is how far up the stack that property survives.

The macaroon variant makes the same binding structural rather than remembered. Instead of an opaque string whose meaning lives in gateway state, the handle *is* an attenuated grant carrying its own caveats — host, method, path, validity window — verified cryptographically before any real credential is substituted. A stolen handle is then worth exactly what its caveats already permitted. The constraint travels with the artifact instead of living in a table somewhere.

## Authority is temporal

A traditional sandbox grants a static envelope for a process lifetime. That works when a program's needs are known and auditable in advance.

An agent discovers needs turn by turn:

```text
observe
    → form subgoal
    → request authority
    → receive scoped capability
    → invoke through gateway
    → audit result
    → revoke when subgoal closes
```

A static agent profile is necessarily the union of everything the agent might eventually need. It is over-granted by construction. A capability justified for one subgoal often lingers for the rest of the run.

This is where the gateway becomes more than a credential proxy. It is the natural home for epoch-bound handles, one-shot operations, per-turn budgets, repository-specific grants, read and write phases, human approval, and revocation. The gateway turns authority from configuration into a protocol.

## Why not just call the PDP on everything, forever

Because the two ends of that arrow have opposite failure modes, and you have to choose where to sit.

```text
freshness                      local execution
    ▲                                ▲
    │                                │
online policy              materialized capability

every effect revalidated   decision cached in a handle
revocation is immediate    revocation needs a channel
PDP outage stops work      works while the PDP is down
every effect is a round trip   effects are local and fast
central visibility of use  attenuated delegation is free
```

This is Lampson's split from the capabilities article, wearing operational clothes. The PDP is excellent at the administrative and query questions — who can do this, what can this user reach, revoke everything derived from that grant. The capability is excellent at the execution question — may the holder of this do this, right now, with no network.

Agents want both, badly. They make many effects per second, so round-tripping everything is unaffordable. They also change what they are doing constantly, so a long-lived grant is over-broad within minutes.

The resolution is not novel, and the enforcement article already showed it: Flask solved this in 1999. Cache the decision where enforcement happens, and pair the cache with a revocation channel so a policy change invalidates what was cached. An access vector cache plus a notification is structurally the same thing as a host-held lease plus an epoch bump. The agent case differs only in that the invalidating event is usually the agent's own subgoal closing rather than an administrator editing policy.

## How far up does the property survive

The capabilities article ends on a precondition. Object capabilities need Property F — you can only pass a capability to someone you can already reach — and Property F requires a substrate that can deny communication. That is why every object-capability system that has ever worked lives inside a kernel, a language runtime, an RPC overlay, or a VM boundary, and why the open internet is a Model 3 world.

An agent sandbox has that substrate. The host controls every channel the guest has; that is the definition of the sandbox. So this is one of the rare places where the property is nearly free, and it is worth walking the layers to see where it is taken and where it is thrown away.

```text
host ↔ guest handle table       Model 4 already, as above
gateway ↔ your own services     free choice, usually not taken
agent ↔ subagent                Model 1 today
agent ↔ tools (MCP)             Model 1 today
agent ↔ the world (git, curl)   Model 3, permanently, and correctly
```

**The bottom row is not a failure.** The agent runs `git push`, `curl`, `npm install`, `psql`, and you cannot hand `git` an object reference. Object capabilities require both ends of an interface to speak the model, and the premise of the whole design is that one end is the existing tool ecosystem. So legacy egress gets adjudication forever, and macaroons are the right credential there precisely because they are Model 3 done as well as Model 3 can be done: attenuable without a round trip, caveats travelling with the artifact, verifiable by a resource server that has never heard of your gateway.

**The middle two rows are the interesting ones,** because they carry no legacy constraint at all. Nobody is locked in. They were designed recently, by people who could have chosen either way.

A tool call is `{"name": "read_file", "arguments": {"path": "/etc/passwd"}}`. The tool name is a string in a global namespace, the argument is a designator anyone can utter, and the authority to act comes from the connection's ambient grant. That is Model 1 — an ACL, keyed by session, consulted by name — and it is the exact shape that makes prompt injection work. The injected sentence supplies a designator; the session supplies the authority.

Subagent spawning has the same shape and a more obvious fix. A parent holding repository write should be able to spawn a child holding read on one subdirectory, by wrapping the reference it already holds, with no policy round trip and no way to hand on more than it has. That is the attenuation chain, and it is the one place in this architecture where it is unarguably the right answer.

**Going further is possible and someone should.** Cap'n Proto is the obvious vehicle for the rows you own, and Cloudflare's `workerd` is the existence proof: untrusted third-party code holding capability bindings to storage and to other workers rather than credentials for them, at scale. Three costs to weigh before committing. Three-party handoff — passing agent C a capability you got from agent B without proxying through B — is specified but, at the time of writing, unimplemented in the C++ runtime, so multi-agent topologies proxy through the introducer. Persistence is application-implemented, so epoch-bound revocable leases are still yours to build. And every service you want to reach this way needs a capability-shaped interface, which for services you own is a weekend and for the open world is a facade per service, forever.

That last cost is the honest reason nobody has done it, and it is also why the line in the table above sits where it does. Take the property where you control the substrate. Expect Model 3 where you do not.

# Part III — EXERCISE

Everything so far decided what authority should exist and handed it over. None of it constrains a program that declines to use the handle.

This is the part that makes the rest true.

## Two coupled subsystems

### 1. The compute sandbox

The compute sandbox owns execution:

- VM or container lifecycle
- Guest image and boot path
- CPU and memory boundaries
- Local disks and snapshots
- PID, IPC, network, mount, and user isolation
- Device exposure
- Command execution and console access
- Guest-local seccomp, capabilities, namespaces, and LSM policy

Its job is to ensure that untrusted computation cannot directly reach the host or invent an unmediated route to external resources.

Possible implementations include QEMU/KVM microVMs, Firecracker, cloud-hypervisor, gVisor, hardened containers, WASI runtimes, or specialized application kernels. They differ dramatically in residual interface, startup cost, compatibility, and the consequences of a kernel compromise. They can nevertheless implement the same side of the contract.

### 2. The capability gateway

The capability gateway owns external effects:

- Network destination policy
- Protocol-aware request policy
- Credential storage and late injection
- Filesystem and persistence mediation
- Database roles and query restrictions
- SSH and source-control operations
- Artifact publication
- Rate limits, budgets, expiry, revocation, and approval
- Structured auditing

The gateway is not merely a firewall. It is a **programmable authority broker**. The guest receives a name, placeholder, or restricted handle. The host retains the actual file, token, socket, key, database credential, or durable resource and decides how each attempted use maps to a real effect.

Notice the shape of what that is. The sandbox half is pure subtraction — no route, no mount, no credential — and subtraction alone would leave a workload that can do nothing useful. So the gateway adds the one thing subtraction cannot express: an entity in the middle that holds the real authority and speaks a protocol. The enforcement article's rule applies exactly. Subtraction plus mediation is construction, and this table is a capability system being rebuilt one resource class at a time.

Gondolin currently combines a microVM runtime with two important gateway families. Its host-side VFS providers serve selected filesystem operations, while its host network stack terminates and replays mediated HTTP/TLS traffic, applies destination and request hooks, and substitutes real secrets for guest-visible placeholders. Iron Proxy isolates the latter idea as an egress product: untrusted workloads receive proxy tokens, real credentials remain at the proxy, and an ordered transform pipeline applies default-deny routing, secret substitution, auditing, and protocol-specific policy.

The abstraction generalizes:

| Host-held authority | Guest-visible capability | Gateway action |
| --- | --- | --- |
| API token | Placeholder token | Inject into an approved request |
| Host directory | Virtual mount | Execute approved VFS operations |
| Internal network route | Synthetic destination | Connect to an approved service |
| SSH private key | Restricted SSH request | Authenticate and perform an approved operation |
| Database credential | Broker session | Authenticate, select a role, and constrain queries |
| Durable deployment state | Publication handle | Validate and commit an approved artifact |

Two rows of that table sit at different rungs, and the difference is worth naming because it is where the gateway's own confused deputy lives.

The broker session is Model 4. The guest holds a handle to a thing with operations on it, and there is no designator to supply.

The placeholder token is Model 3. The guest holds an opaque string, chooses a destination, and the gateway matches that destination against policy and substitutes real authority. Designator and authority arrive by separate paths and the gateway recombines them — which is the precise configuration Miller warns produces confused deputies. Any route by which an agent gets an attacker-chosen request to match an approved destination converts the gateway's authority into the agent's: an open redirect on an allowed host, a request-splitting bug, an allowed API that proxies a URL parameter.

The contract below names this (credentials inserted only into approved destinations and fields), and that mitigation is real. It is also exactly ACL-plus-context: the correct answer is expressible and the gateway still has to ask, on every request, forever. A handle to *writer on repository X* has no wrong question available. Where you can afford the facade, prefer the broker-session shape; where you cannot, know that the placeholder row is the one carrying the residual risk.

## The runtime–gateway contract

A VM and a proxy are not independently sufficient. Their composition is the boundary.

The system should maintain an invariant of the form:

> Every effect on an external resource is either impossible or passes through the gateway under a host-authenticated sandbox identity.

The runtime side of the contract must guarantee:

1. No generic NAT, bridged interface, or alternate egress bypasses the gateway.
2. No host filesystem is directly exposed outside explicitly mediated providers.
3. Real credentials do not enter guest environment variables, memory, disks, metadata, or snapshots.
4. Control channels cannot be repurposed into generic tunnels.
5. Gateway failure is fail-closed.
6. Every VM has a host-known, nonforgeable identity.
7. Guest-local storage is ephemeral unless it crosses an explicit publication boundary.
8. CPU, memory, I/O, and gateway-work amplification have enforceable limits.

The gateway side must guarantee:

1. Policy is keyed to the host-known sandbox identity, not a guest-asserted UID.
2. Credentials are inserted as late as possible and only into approved destinations and fields.
3. DNS answers, resolved IPs, redirects, methods, paths, and relevant content are revalidated.
4. Raw-protocol escape hatches are explicit and narrower than the normal mediated path.
5. Authority can be scoped, expired, budgeted, and revoked.
6. Requests, transformations, and decisions are auditable.
7. Responses are part of the threat model: an allowed server must not trivially reflect an injected secret back to the guest.

This contract matters more than packaging. Runtime and gateway can be one project, separate libraries, separate host processes, or a local runtime connected to a remote service. The security property is that the gateway is **unavoidable**.

An `HTTP_PROXY` environment variable is not such a property. A malicious workload can ignore it. DNS redirection alone is not such a property if direct IP egress still exists. Iron Proxy explicitly recommends kernel routing enforcement such as nftables or TPROXY for stronger deployments. Gondolin obtains a tighter composition by withholding generic NAT: the host network backend is the guest's network peer, so unauthorized traffic never becomes an ordinary host connection.

## The residual interface

The thing to examine after constructing the boundary is the **residual interface**: what remains reachable, and at what semantic level?

![residual interface](/assets/llm-sandbox/vm-vs-container.png)

A raw VM's residual interface is mostly structural: block devices, Ethernet frames, virtio queues, boot state, and device models. Policy applied there can usually speak only in structural terms. But that is a property of the exposed device set, not an intrinsic limitation of VMs. Attach a programmable VFS or protocol gateway and semantic operations cross the VM boundary deliberately.

It is tempting to say a container's residual interface is a strict superset of a VM's. That is false. A VM introduces attack surfaces that a container does not have: KVM or HVF ioctls, a VMM, device models, firmware, boot code, and, in systems like Gondolin, host processes parsing hostile filesystem RPC and network protocols. A container under a small seccomp profile with empty namespaces is different in kind, not merely wider.

The honest claim is empirical: for workloads requiring a general-purpose Linux syscall API, a hardware VM usually gives a cleaner boundary against guest-kernel compromise, and hypervisor escapes are rarer than ordinary kernel privilege escalations. That conclusion does not make the VMM free.

Two caveats survive:

- **Granularity runs the other way.** Namespaces are selectively composable: share PID but not network, network but not mounts. A VM is comparatively all-or-nothing per machine. Containers are more expressive within the unnameability layer even when they provide a weaker kernel boundary.
- **Configuration dominates the label.** A VM with the host home directory mounted read-write and unrestricted NAT may expose more useful authority than a carefully restricted container. Hole-punching is the actual variable.

A third tier changes *who* the adversary is rather than which resources are reachable: confidential-computing systems such as Intel TDX, AMD SEV-SNP, and SGX attempt to remove parts of the host operator from the trusted computing base. That is a distinct problem from protecting a trusted host against an untrusted guest.

## Programmable gateways versus declarative LSMs

JavaScript is computationally more expressive than an SELinux or AppArmor policy language. A host callback can maintain counters, consult a database, ask a human, call another policy service, transform a request, synthesize a file, or redirect writes into memory.

But computational expressivity is not security coverage. A callback can decide only from the facts delivered to it. A Gondolin HTTP hook may understand hostname, resolved IP, method, path, headers, body, and redirects, yet know nothing trustworthy about which guest process originated the request. A VFS provider may see rich file operations while having no visibility into guest `ptrace`, signals, capabilities, IPC, or access to the guest's internal root disk.

An LSM has the opposite shape. SELinux, AppArmor, Smack, TOMOYO, and Landlock hook kernel access-control points across processes, files, sockets, IPC, capabilities, mounts, and other object classes. Their conventional policies are less computationally open-ended but broader and more uniform inside the kernel. BPF LSM occupies another point: programmable eBPF code attached to LSM hooks, with kernel context and verifier-imposed constraints.

| Property | Host capability gateway | Declarative guest LSM | BPF LSM |
| --- | --- | --- | --- |
| Principal | Usually the entire VM | Guest process/domain/profile | Guest task plus hook context |
| Vocabulary | Mediated protocols and resources | Kernel subjects, objects, and operations | Selected kernel-hook context |
| Computation | Arbitrary userspace code and external state | Mostly static/declarative relations | Verified programs and maps |
| Result | Allow, deny, transform, emulate, synthesize | Allow, deny, audit, transition, label | Usually deny/audit plus programmable logic |
| Coverage | Only gateway-backed effects | Broad guest-kernel coverage | Hooks actually instrumented |
| Survives hostile guest kernel | Yes, absent VM/gateway escape | No | No |

The right conclusion is not that one policy language dominates. It is that they protect different trust boundaries. A guest LSM is excellent for separating `agent_t`, `compiler_t`, and `test_t` while the guest kernel remains trustworthy. The host gateway protects host resources and external authority even if that guest kernel is compromised.

If the guest kernel is in the adversary set, the host cannot rely on guest-supplied process identity. A malicious kernel can claim that a request came from UID 200 or `credential_helper_t`. The host gateway must treat the VM and its authenticated transport as the security principal. If two workloads need genuinely different external authority, place them behind different nonforgeable host channels—often different VMs.

## Filesystem mediation is a resource service

Gondolin's VFS is not simply "SELinux written in JavaScript." It is a programmable resource server:

```text
guest filesystem operation
    → sandboxfs/FUSE
    → virtio-serial RPC
    → host provider
    → memory, real filesystem, overlay, or synthetic resource
```

A provider can deny access, return `ENOENT`, redirect writes into a memory layer, synthesize content, maintain quotas, or expose a database as files. Conventional LSMs normally adjudicate access to resources implemented elsewhere; a VFS provider implements the resource itself.

Lima and Gondolin occupy a comparable legibility level but do not literally use the same host protocol. Lima's virtiofs path carries the FUSE protocol over virtio. Gondolin's guest `sandboxfs` translates filesystem operations into Gondolin's own `fs_request` RPC over virtio-serial. Both make filesystem operations legible at the host boundary; Gondolin intentionally exposes programmable providers.

### The path-policy soundness trap

"Deny writes under `.git/hooks`" reads like a few lines. It is a few lines to write and many to make correct.

Path policy must account for symlinks, hard links, rename, bind aliases, already-open handles, and the distinction between a directory entry and an inode. Current Gondolin documentation says `RealFSProvider` blocks symlink traversal escaping the exposed host directory, rejects dangling symlinks for follow-style operations, and offers realpath consultation for shadow policies. That resolves an earlier documentation gap, but it does not make every possible provider composition or aliasing rule automatically sound.

Label-based LSMs such as SELinux avoid some pathname aliasing problems by attaching policy to kernel objects. AppArmor and path-oriented gateways trade some of that object stability for policies that map more directly onto how developers describe a workspace. Neither choice removes the need for careful semantics around creation, linking, rename, and publication.

## Protocol gateways can see what kernels cannot

A guest LSM observing a TLS connection normally sees something like:

```text
connect 140.82.x.x:443
send encrypted bytes
```

A host gateway that terminates TLS can see:

```text
POST api.github.com/repos/acme/project/git/refs
Authorization: placeholder-7f91
body: { ... }
```

It can therefore apply host, IP, method, path, header, body, redirect, and resource-specific policy. It can replace a placeholder with a real credential only after the request has been approved. It can also implement protocol-specific authority: a PostgreSQL gateway may assign a fixed role and reject role-changing SQL; a Git gateway may distinguish fetching from updating a protected ref.

This semantic advantage has a cost. TLS termination expands the trusted userspace parser surface, breaks certificate pinning and end-to-end authenticity inside the guest, and requires compatibility decisions for HTTP versions, QUIC, SSH, raw TCP, WebSockets, gRPC, and other protocols. Mediation relocates the compatibility tax; it does not abolish it.

## Secret possession is not authority containment

Suppose the host owns a token that can create releases, delete branches, and modify repository settings. Giving the guest a placeholder instead of the token establishes **non-extractability**: compromise of the guest does not reveal the reusable credential bytes.

It does not automatically establish **constrained use**. If the gateway allows arbitrary requests to `api.github.com`, the guest may exercise the token's full authority through the gateway without ever learning it.

The proxy is therefore a classic potential confused deputy: it possesses authority on behalf of an untrusted requester and must know *which use* of that authority is justified. Good policies constrain destination, method, path, request fields, repository, branch, amount, rate, time, and sandbox identity. Stronger systems bind a grant to an explicit request–grant–invoke lifecycle.

The placeholder is itself a capability. It may be worthless outside the gateway but valuable to anyone who can still reach that gateway. It should be bound to a sandbox identity, authenticated channel, session, expiry, scope, and budget rather than treated as harmless merely because it is not the upstream bearer secret.

agent-creds shows one way to make that binding structural. Its guest-visible handle is a macaroon rather than an opaque string, so the constraints travel with the artifact instead of living only in gateway-side state: caveats naming host, method, path glob, and validity window are verified cryptographically before the vault will substitute a real credential. A stolen handle is then worth only what its caveats already permitted. This does not dissolve the confused-deputy problem — a caveat set wide enough to cover an agent's entire run recreates it — but it changes the question from *what does the gateway remember about this token* to *what does this token say about itself*.

## Threat model by enforcement plane

The unnameability/adjudication split from the enforcement article hides trust placement. In particular, "malicious code defeats adjudication" is true of in-guest adjudication but false of a host gateway designed to distrust the guest kernel.

Making that precise means asking two questions instead of one: *which adversary* is a plane rated against, and *which harm* is it meant to prevent. Collapsing them into a single list is how sandboxes end up compared on a number nobody can define. The [prologue](/programming/who-is-the-adversary.html) supplies the first axis — three rungs, by how much of the machine the attacker owns, plus two that sit off the ladder and combine with any rung.

Rated against the rungs, the planes sort cleanly, and the sort is the entire argument for composing them:

| Enforcement plane | Attacker controls the input | Attacker runs code | Attacker owns the guest kernel |
| --- | --- | --- | --- |
| Tool-call policy | Holds, bounded by policy completeness | Falls — code routes below the tool API | Falls |
| Guest resource universe | Holds | Holds | Falls |
| Guest syscall mediation | Holds | Holds | Falls |
| Guest object mediation | Holds | Holds | Falls |
| VM boundary | Holds | Holds | Holds, absent a VMM escape |
| Host capability gateway | Holds | Holds | Holds |
| Upstream resource policy | Holds | Holds | Holds |

Read down the third column and the recommended architecture writes itself. Everything above the VM boundary is defense in depth; everything at or below it is what you are actually relying on once the guest is fully lost. Read across the first row and you get the honest limit of semantic governance: it is the most legible plane and the first one to go.

The two off-ladder adversaries cut across every row rather than appearing in one. An attacker who splits a single intent across several individually-permitted requests defeats all seven equally, because every one of them adjudicates one effect at a time. An attacker who can edit the policy artifacts defeats whichever plane reads them — which is the sharpest argument for buying non-bypassability with topology rather than with rules.

The second axis is harm, and it is what the planes are *for*:

| Harm | Compute boundary | Guest LSM | Capability gateway | Semantic governance | Upstream controls |
| --- | --- | --- | --- | --- | --- |
| **H1** Destruction of local or durable state | Contains guest damage; snapshots roll it back | Restricts processes internally | Protects host and durable effects | Catches obvious actions | Branch protection, backups, deletion policy |
| **H2** Persistence into later execution | Makes local guest state disposable | Restricts dangerous guest writes | Controls host VFS writes and publication | Sees hooks, CI edits, and similar intent | Signing, branch rules, deployment gates |
| **H3** Exfiltration through an allowed path | Little once a route is deliberately granted | Limited | Constrains request semantics and credential use | May recognize suspicious intent | Least-privilege API and token scope |
| **H4** Lateral movement to localhost, RFC1918, or metadata | Removes raw host routes | Restricts guest sockets | Rejects internal destinations and rebinding | Secondary | Network-side controls |
| **H5** Resource exhaustion | CPU, memory, and device ceilings | Weak | Request, bandwidth, and parser-work quotas | Weak | Rate limits |
| **H6** Microarchitectural side channels | Limited; requires scheduling or hardware measures | None | None | None | Confidential computing may change host trust |

Together the two tables expose the central division:

> **The compute boundary contains execution. The capability gateway contains authority.**

Neither dominates, and a failure in their contract can invalidate both.

## A complete enforcement stack

The strongest design combines several enforcement planes because each answers a different question. Consider an agent attempting to push a commit to GitHub:

| Enforcement plane | Question it can answer | Security role | Trust limit |
| --- | --- | --- | --- |
| **Tool-call policy** | “May the agent request `git push` for this task?” | Judges semantic intent before execution and can request approval or a temporary grant | Arbitrary code can bypass the tool interface |
| **Guest resource universe** | “Which mounts, processes, networks, users, and IPC objects can this process name?” | Namespaces, mount topology, and omitted resources remove ambient reachability | A compromised guest kernel can reconstruct or bypass these views |
| **Guest syscall mediation** | “May this process invoke `execve`, `socket`, or `mount` with these scalar arguments?” | Seccomp reduces the available syscall interface and kernel attack surface | It lacks resolved-object context; a compromised guest kernel can disable it |
| **Guest object mediation** | “May this subject execute this file, connect this socket, or signal this task?” | DAC, Linux capabilities, and LSMs authorize operations on resolved kernel objects | A compromised guest kernel can disable or bypass the checks |
| **VM boundary** | “Can any code in this guest directly access the host?” | Contains the entire guest, including a hostile root process or compromised guest kernel | A hypervisor, VMM, or device-model escape crosses the boundary |
| **Host capability gateway** | “May this VM perform this exact GitHub operation, and should a credential be injected?” | Retains the real credential and attenuates it to approved destinations and operations | A gateway flaw or alternate route can expose the brokered authority |
| **Upstream resource policy** | “May this GitHub identity update this repository and branch?” | Enforces the final invariant where the resource is actually owned | A broad token, weak branch rule, or upstream authorization error defeats it |

These are not five interchangeable sandboxes, nor are they simply five filters placed in one process. The VM encloses the untrusted compute. The gateway sits outside that enclosure and is the VM's only route to protected external resources. GitHub then applies its own policy at the destination:

```text
┌──────────────────────── VM boundary ────────────────────────┐
│                                                             │
│  agent intent                                               │
│      ↓ tool-call policy                                     │
│  guest process                                              │
│      ↓ namespace and mount view                             │
│      ↓ seccomp syscall mediation                            │
│      ↓ DAC / capabilities / LSM object mediation            │
│  guest kernel                                               │
│                                                             │
└───────────────────┬─────────────────────────────────────────┘
                    │ exclusive mediated channel
                    ↓
             host capability gateway
             - authenticates the VM
             - authorizes the exact request
             - injects a scoped credential
                    │
                    ↓
             GitHub resource policy
             - repository permissions
             - branch protection
             - token scope
```

The composition matters because the failures differ. If malicious code bypasses the tool API and runs Git directly, its namespace still determines what it can reach, seccomp still constrains which kernel entry points it can use, and the LSM still adjudicates operations on resolved objects. If it compromises the guest kernel, all three guest controls should be treated as lost. The VM still protects the host, and the hostile guest still cannot obtain the real GitHub token or open an alternate network route; it can only ask the host gateway to perform an operation. If the gateway mistakenly permits a request, GitHub's own branch and identity policy remains the final backstop.

No layer makes the others redundant. Semantic governance understands *why* an action is being attempted. Namespaces shape the guest's visible universe. Seccomp mediates the syscall vocabulary. LSMs and ordinary kernel access controls mediate resolved objects. The VM establishes the host trust boundary. The capability gateway controls external authority. The resource owner decides the final state transition. The theoretically strongest architecture composes all of them.

Read that table against the first two articles and the series closes on itself. The guest resource universe is unnameability. Syscall and object mediation are adjudication. The VM is a trust boundary, not a policy. The gateway is a PEP holding a materialized capability. The upstream resource policy is the ACL that was always there, doing the administrative job capabilities are bad at. Every row is one of the two strategies, placed in one of the trust domains, speaking at one of the legibility levels.

## Cost and compatibility

Strength comparisons omit the variable that determines what people actually run. Cold starts span orders of magnitude, as does per-instance memory. Snapshot capability matters as much as nominal isolation: disk snapshots give rollback, while memory snapshots enable fork-from-snapshot and a different workload architecture.

Mediation has its own tax. Every filesystem operation becoming a host RPC is fine for source files and potentially ruinous for large builds. A useful layout keeps toolchains, dependency caches, object files, and scratch data on a guest-local block device while exposing only source, selected outputs, and publication operations through the semantic gateway.

The stronger version is not to mount the host repository at all. Clone it inside the guest, work locally, and publish changes through a controlled Git or artifact capability. This deliberately trades filesystem legibility for absence. It is often both faster and safer.

The dominant failure mode of a strong sandbox is that users disable it. A boundary that survives normal tests, local sockets, language servers, package managers, and caches is more valuable than a theoretically stronger profile that daily work routes around.

## Replaceable runtimes, stable authority boundary

The capability-gateway abstraction makes the compute layer replaceable, but not irrelevant. A coding workload wants a rich, relatively long-lived environment with fast filesystem access, package caches, test servers, and an explicit publication path. A recursive-inference workload may want many cheap, ephemeral, forkable environments where memory-snapshot cloning matters more than a sophisticated workspace VFS.

The same gateway concepts can serve both while the runtime optimization differs. Do not make one sandbox implementation serve every workload, and do not couple external authority to one runtime forever.

## The landscape, scored against the contract

Gondolin is one point in this space. Five others make the axes visible.

| System | Compute boundary | What makes the gateway unavoidable | Filesystem mediation | Credentials | Gateway principal |
| --- | --- | --- | --- | --- | --- |
| **landrun** | Landlock on the host kernel | No gateway | Allow/deny on real host paths | Denied paths, or nothing | — |
| **Codex CLI** | Seatbelt; Landlock, seccomp, and namespaces on Linux | No gateway; network is on or off | Allow/deny on real host paths | None | — |
| **Claude Code** (`sandbox-runtime`) | Seatbelt; bubblewrap; a restricted token in a job object on Windows | Network namespace removed; one permitted loopback port; a WFP block keyed to the sandbox account's SID | Allow/deny on real host paths, with deny-then-allow reads | Optional injection when TLS is terminated | The sandbox instance |
| **nono** | Landlock plus seccomp on the host kernel | seccomp user notification on `connect()`, checking the resolved destination | Allow/deny on real host paths | Phantom token, reverse-proxy injection | The command invocation |
| **Gondolin** | QEMU/KVM microVM | The host stack is the guest's only network peer | Programmable VFS providers over virtio-serial RPC | Placeholder substitution in mediated traffic | The VM |
| **Iron Proxy, agent-creds** | None of its own | Whatever routes the caller: nftables, TPROXY, a network namespace | — | Proxy tokens; macaroon caveats | The client |

Five things fall out of that table.

**The two jobs vary independently.** The first two rows are compute without a gateway. The last row is a gateway without compute. Nothing about a row's first column predicts its third or fifth. This is the article's thesis in tabular form: the interesting quantity is the composition, and most systems ship only one half of it.

**Non-bypassability comes in four strengths.** An environment variable a program may ignore. A syscall filter that inspects each destination. An absent route, where the only descriptor reaching outside is a bind-mounted Unix socket and a program that ignores `HTTP_PROXY` does not escape but simply fails to connect. And a route that was never built, where the host is the peer and NAT does not exist. The last two differ from the second in failure mode: a filter has to be right about every destination, while absence has nothing to be right about. That is the enforcement article's unnameability, applied at the network layer, and it is usually the cheaper of the two to implement.

**Principal granularity runs opposite to compute strength.** A microVM gateway sees one principal, because the VM boundary destroys the process identities behind it. A host-kernel sandbox shares a kernel with its supervisor, so the supervisor can attribute a request to an exact command using facts the kernel vouches for: process ancestry, a per-command cgroup, a POSIX session id. nono brokers each tool invocation separately for this reason. Buying the stronger compute boundary costs the finer principal, and a guest that re-exports its own process identities is supplying evidence, not authority.

**Mediation depth is its own ladder.** Domain allowlist, then a re-check of the resolved address, then request-level policy on method and path, then credential substitution, then protocol-specific authority. Every system here does the first two. Most stop there and say so plainly: filtering which hosts a workload may reach is not inspecting what it does there.

**Only the microVM mediates the filesystem semantically.** Every host-kernel sandbox in the table allows or denies operations on real host paths. None can transform, shadow, redirect, or synthesize, because a kernel access-control hook answers yes or no and then gets out of the way. An RPC boundary is what turns the filesystem into a resource service.

One entry also qualifies a claim made above. The enforcement-stack table lists "arbitrary code can bypass the tool interface" as the limit of tool-call policy. nono narrows that: its shims sit on `PATH` while Landlock denies execute on the real binaries, so `git` resolves to the broker and `/usr/bin/git` returns `EACCES`. The tool call becomes a kernel-enforced chokepoint rather than a cooperative one, and each invocation gets a fresh sandbox built from its own policy. A build tool and a deployment tool stop sharing authority merely because the same agent called both.

The practical reading is to choose the compute layer from the threat model and the gateway from the set of effects, and to let neither choice decide the other.

## Recommended architecture

For a high-assurance untrusted workload, the target stack is:

1. **Server-side least authority.** Use branch protection, narrowly scoped tokens, repository roles, deployment environments, database roles, and resource-owner policy.
2. **A hardware VM boundary when the guest kernel is in the adversary set.** Keep the base image immutable and guest-local work disposable.
3. **A non-bypassable host capability gateway.** No raw NAT, direct host mounts, or real credentials. Mediate filesystem publication, HTTP/TLS, SSH, databases, and other necessary effects through explicit protocols.
4. **Guest-internal defense in depth.** Use an LSM, capabilities, namespaces, seccomp, and cgroups to separate processes and services while the guest kernel remains intact.
5. **Semantic action governance where available.** Reject obviously dangerous intent, negotiate temporary grants, and explain denials.
6. **Revocation and usable exception handling.** Bind grants to sandbox identity, operation, epoch, budget, and expiry. Make the allow-loop cheap enough that users do not replace it with `*`.

An implementation might separate into:

```text
sandbox-runtime
    lifecycle, images, snapshots, execution
    exclusive routes to gateway channels

capability-gateway
    identity, policy, secrets, request transforms
    HTTP/TLS, SSH, Git, SQL, audit, approval

workspace-service
    VFS providers, overlays, durable publication

policy-control-plane
    declarative matchers, programmable extensions
    grants, expiry, revocation, audit schema
```

They need not be separate deployments. They should be separate architectural interfaces joined by an explicit security contract.

# Part IV — What is left over

## Agent-specific threats

The table below is the same two axes applied to what is specific about agents. A1 is the input-controlling adversary from the prologue, arriving through a channel the agent needs open; the rest are harms peculiar to a delegate whose plan is discovered at runtime.

| Threat | Compute boundary | Guest LSM | Capability gateway | Semantic governance | Upstream controls |
| --- | --- | --- | --- | --- | --- |
| **A1** Prompt injection acting through opened channels | Does not recognize corrupted intent | Does not understand prompt semantics | Constrains resulting filesystem, network, and credential effects | Dominant early semantic signal | Final invariant |
| **A2** Exfiltration through the inference endpoint | Keeps raw host secrets absent | Can restrict which files processes read | Mediates model traffic but cannot reliably distinguish legitimate context from stolen proprietary text | Controls context-building tools and may track provenance | Provider policy and data handling |
| **A3** Lingering authority after a subgoal ends | Static boundary does not solve it | Static profiles usually do not solve it | Epochs, expiry, budgets, and revocation | Knows when the plan changes | Short-lived and scoped upstream credentials |
| **A4** Confused-deputy use of brokered credentials | None | Limited | Must bind grants to exact operations and sandbox identity | Supplies justification and intent | Token scopes and server authorization |

### Inference-endpoint exfiltration

A2 deserves special care. A coding agent reads source, places it in model context, and POSTs that context to an allowlisted inference provider. Content inspection cannot reliably separate normal operation from exfiltration because legitimate model traffic is full of file contents.

One control does bite cleanly: **a secret that never enters the guest namespace cannot enter the model context**. This is unnameability applied to credentials. The credential gateway allows legitimate use without disclosure.

Proprietary source is harder because the agent must often read it to work. Possible mitigations—context provenance, per-file policies, local models, DLP, approval, response auditing—are partial and workload-specific. The architecture should state this limitation rather than pretending an inference-host allowlist solves it.

## Harness placement and the trust split

![harness placement](/assets/llm-sandbox/vm-with-virtio.png)

A programmable sandbox has enforcement without model semantics. An evaluation or agent harness has model semantics without necessarily controlling arbitrary code.

![composition](/assets/llm-sandbox/vm-with-gondolin.png)

Running the harness inside the guest can improve compatibility and observability: transcripts, token accounting, model substitution, and tool semantics remain near the agent. Its API calls then traverse the host gateway, where enforcement remains outside the untrusted domain.

The general principle is:

> **Observability may live with the workload; enforcement must live in the trusted domain appropriate to the threat.**

If the guest kernel itself is untrusted, guest transcripts and process identities are evidence, not authority. The host may record them, but must enforce using facts it knows independently: the VM channel, resolved destination, parsed request, exposed VFS object, and gateway policy.

The cost is real. The guest trusts a MITM CA for mediated TLS, so end-to-end TLS authenticity no longer terminates at the original application. Certificate pinning may fail. The gateway becomes a trusted parser of hostile HTTP, TLS, Git, SQL, or other protocols. Semantic visibility is purchased by expanding the host-side trusted computing base.

## The seam nobody has named

Read the landscape table again and the common gap is not enforcement. Every system in it enforces something real, and the strongest of them enforce at a boundary a hostile guest kernel cannot reach. What none of them has is a decision point separable from the enforcement point.

```text
guest agent
    ↓
host PEP
 ├─ filesystem
 ├─ network
 ├─ secrets
 └─ external services
```

Gondolin is the clearest case because it has the most policy to misplace. Its rules are declarative matchers and JavaScript callbacks, evaluated in the same process that enforces them. `sandbox-runtime` does the same thing with `filterRequest`. landrun and Codex have no policy layer to speak of, which is the same problem arrived at from the other side. In every case the arrangement is the one the enforcement article warned about conflating: a PEP with a PDP baked into it cannot be governed by anyone who does not own the sandbox.

That is the right starting place. It is simple, it is fast, and it couples nothing to an external service's availability. It stops being the right place the moment more than one team has to live with the answer.

One system in the table has started to move. nono's Tool Sandbox defines webhook approval backends against a documented request protocol, with a combinator for requiring several of them to agree — a remote decision point in everything but name, even while its own capability-expansion prompts still go to a terminal. It got there by the practical route, needing someone other than the person at the keyboard to approve a `kubectl` invocation, rather than by setting out to split a PDP from a PEP. The two paths arrive at the same seam.

Naming it is what keeps the architecture honest:

```text
native effect
    ↓
normalize to S / A / R / C
    ↓
AuthorizationProvider
    ├── local JS callback      (today)
    ├── local Cedar
    ├── local Rego
    └── remote AuthZEN PDP
```

Nothing about enforcement changes. The gateway still owns the resources, still holds the credentials, still sits in the only path. What changes is that the decision becomes a thing an organization can own, version, audit, and share across every sandbox it runs — rather than a callback living in one deployment's config.

And then the second half, which is where the capabilities article's pipeline finally lands somewhere real:

```text
PDP decision
    ↓
host-held lease
    - sandbox identity
    - operation and resource scope
    - epoch, budget, expiry
    ↓
opaque guest handle
```

That is the whole series in one diagram. Policy decides, a capability materializes, a reference monitor makes it stick.

## Conclusion

The framing trap is to see a weak mechanism and immediately replace it with a stronger boundary. Often the actual failure is that policy lived at the wrong semantic level, in the wrong trust domain, or on a path the workload could bypass.

A VM protects the host kernel but cannot decide whether a GitHub API operation is justified. An HTTP proxy can understand that operation but is optional if raw egress remains. A guest LSM can separate processes but falls with the guest kernel. A tool hook can understand intent but arbitrary code can route below it. Branch protection is authoritative but sees only the final Git operation.

The argument has three layers. First, containing execution and containing authority are different jobs joined by a non-bypassable contract. Second, neither job is new: the reference monitor, the PEP/PDP split, and the object-capability model were all worked out decades ago, and this architecture is those patterns placed at a new boundary. Third, agents make the composition dynamic, because their useful authority changes with the plan and because untrusted data can influence which capabilities they request.

The architecture is therefore not a single best sandbox. It is a composition:

> **A replaceable compute sandbox connected to a non-bypassable, host-trusted capability gateway, reinforced by guest-internal policy, semantic action governance, and resource-owner controls.**

The compute sandbox determines which universe the workload inhabits. The capability gateway determines which external authority that universe may exercise. The contract between them is the boundary.

The four articles were really one argument, arriving in four parts. Authority has to be *represented* somewhere, and the choice between a list at the resource and a reference in the subject's hand decides which questions stay cheap. The strong version of the second choice — designation and authority as one thing — has a precondition, which is a substrate that can deny communication. A representation of either kind is inert until something *enforces* it, and enforcement is a reference monitor placed in a trust domain, using unnameability or adjudication or both. And an agent is the case that will not let you separate those concerns in time, because it discovers what it needs while it runs.

There is one last thing worth saying plainly, because it is the part I did not expect to find. The capabilities article ends pessimistically: Model 4 is purchasable only where something mediates communication, the open internet mediates nothing, and so the deployed world is Model 3 and the old objections to capabilities remain true of everything anyone ships.

An agent sandbox is the exception. It mediates every channel the workload has, by construction, as its entire purpose. It is one of the few places where the property is available for free.

We built it at the boundary the host already controlled, and then shipped Model 1 everywhere above it — tools named by strings, authority supplied by the session, subagents inheriting the parent's whole grant. Prompt injection is the bill for that, and it is a fifty-year-old bug with a fifty-year-old cure.

Which is why agents are worth the attention even if you never build one. They take a design problem that was previously solvable at configuration time and force it to be solved at runtime, in the open, where the tradeoffs are visible — and where the consequences of getting the representation wrong show up within a week rather than within a decade.

# References

## Primary implementation sources

- [Gondolin — security design](https://earendil-works.github.io/gondolin/security/) — threat model, host trust boundary, network mediation, secret substitution, filesystem confinement, and explicit limitations
- [Gondolin — architecture](https://earendil-works.github.io/gondolin/architecture/) — VM lifecycle, `vm.exec` over virtio-serial, `sandboxd`, VFS RPC, and host/guest component placement
- [Gondolin — VFS providers](https://earendil-works.github.io/gondolin/vfs/) — programmable resource providers, real-filesystem hardening, read-only and shadow layers, and provider composition
- [Gondolin — QEMU backend](https://earendil-works.github.io/gondolin/qemu/) — minimal device model and the decision to keep the host as the guest's network peer
- [Iron Proxy](https://github.com/paradigmxyz/iron-proxy) — untrusted-client forward proxy, default-deny egress, proxy-token secret substitution, request transforms, auditing, and routing requirements
- [agent-creds](https://github.com/dtkav/agent-creds) — per-sandbox Envoy proxy and shared credential vault; the guest holds only a macaroon whose caveats are verified before the vault injects a bearer, Basic, OAuth2, or SigV4 credential, with network-namespace isolation supplying non-bypassability
- [sandbox-runtime](https://github.com/anthropic-experimental/sandbox-runtime) — the sandbox behind Claude Code's Bash tool: Seatbelt, bubblewrap with the network namespace removed and proxies reached over bind-mounted Unix sockets, a Windows WFP egress fence keyed to a separate account SID, resolved-address re-checking, and experimental TLS termination
- [Claude Code — sandboxing](https://code.claude.com/docs/en/sandboxing) — configuration surface and the violation reporting that turns a denial into something the model can act on
- [nono — security model](https://nono.sh/docs/cli/internals/security-model) — a capability model rather than a VM model, supervisor trust, and per-invocation command policy
- [nono — Landlock](https://nono.sh/docs/cli/internals/landlock) and [networking](https://nono.sh/docs/cli/features/networking) — ABI v1–v6 access rights, seccomp user notification on `connect()` and `openat`, and the `io_uring_setup` denial that closes the syscall-filter gap
- [landrun](https://github.com/Zouuup/landrun) — the minimal case: a Landlock wrapper with no gateway at all
- [Codex CLI — agent approvals and security](https://developers.openai.com/codex/agent-approvals-security) — Seatbelt and Landlock/seccomp profiles with network off by default
- [Using proxies to hide secrets from Claude Code](https://formal.ai/blog/using-proxies-claude-code/) — mitmproxy addons substituting a real API key for a dummy one, `NODE_EXTRA_CA_CERTS` to trust the intercepting CA, and separate proxy configuration for the harness process and its sandboxed subprocesses; forced by environment variable rather than by routing
- [Lima — filesystem mounts](https://lima-vm.io/docs/config/mount/) — reverse-SSHFS, 9p, virtiofs, and mount behavior across VM drivers

## Policy and decision

- [AuthZEN](https://openid.net/wg/authzen/) — OpenID Foundation working group standardizing the PEP/PDP contract; the Authorization API and its subject/action/resource/context request shape
- [Cedar](https://www.cedarpolicy.com/) and [OPA/Rego](https://www.openpolicyagent.org/docs/latest/policy-language/) — two policy languages that can sit behind an AuthZEN seam
- [Zanzibar: Google's Consistent, Global Authorization System](https://research.google/pubs/pub48190/) — relationship-based authorization and the reverse-indexability problem
- [The Flask Security Architecture](https://www.cs.cmu.edu/~dga/papers/flask-usenixsec99.pdf) — decision caching paired with a revocation channel, the 1999 answer to the freshness/locality tradeoff

## Foundations

The first two articles in this series cover these properly. Listed here because this article leans on them directly.

- [The Protection of Information in Computer Systems](https://www.cs.virginia.edu/~evans/cs551/saltzer/) — Saltzer and Schroeder's design principles, including complete mediation and least privilege
- [Capability Myths Demolished](https://cgi.cse.unsw.edu.au/~cs9242/20/papers/Miller_YS_03.pdf) — designation, authority, and confinement
- [The Confused Deputy](https://www.cs.utexas.edu/~witchel/S25-380L/papers/hardy88confused.pdf) — the failure mode every credential broker must avoid
- [Macaroons: Cookies with Contextual Caveats](https://static.googleusercontent.com/media/research.google.com/en/us/pubs/archive/41892.pdf) — attenuable grants that carry their own constraints
- [WASI security principles](https://github.com/bytecodealliance/wasi.dev/blob/main/docs/security.md) — capability-oriented host access
- [Landlock](https://docs.kernel.org/userspace-api/landlock.html) — unprivileged monotonic self-restriction

## Agent frameworks and research

- [The Agent Sandbox Taxonomy](https://github.com/kajogo777/the-agent-sandbox-taxonomy) — defense layers, threats, strength, granularity, and action governance
- [Lingering Authority: Revocable Resource-and-Effect Capabilities for Coding Agents](https://arxiv.org/abs/2606.22504) — epoch-bound capability handles and the request–grant–invoke lifecycle
- [Recursive Language Models](https://alexzhang13.github.io/blog/2025/rlm/) — context as a live variable and recursive partition-and-map workloads
- [Inspect](https://inspect.aisi.org.uk/) — an agent/evaluation harness with model and tool semantics

## Landscape and performance

- [AI agent sandbox technologies: a 2026 comparison](https://grigio.org/ai-agent-sandbox-technologies-a-complete-2026-comparison/) — startup, memory, eBPF network mediation, and confidential-computing comparisons
- [Best microVM sandboxes for AI code execution](https://modal.com/resources/best-microvm-sandboxes-ai-code-execution) — vendor-authored comparison including filesystem, directory, and memory snapshot capabilities
- [List of coding agent sandboxes](https://gist.github.com/wincent/2752d8d97727577050c043e4ff9e386e) — curated index of OS primitives, application kernels, microVM runtimes, and local CLI sandboxes
