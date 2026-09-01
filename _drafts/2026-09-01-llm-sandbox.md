---
title:  "LLM Sandbox = Compute Isolation + Authority Mediation"
category: programming
date:   2026-09-01
---

- [Act I — Containing Computation Is Not Containing Authority](#act-i--containing-computation-is-not-containing-authority)
  - [The unit of analysis is the external effect](#the-unit-of-analysis-is-the-external-effect)
  - [Two coupled subsystems](#two-coupled-subsystems)
    - [1. The compute sandbox](#1-the-compute-sandbox)
    - [2. The capability gateway](#2-the-capability-gateway)
  - [The runtime–gateway contract](#the-runtimegateway-contract)
  - [The residual interface](#the-residual-interface)
  - [Three independent properties of enforcement](#three-independent-properties-of-enforcement)
    - [1. Legibility: what vocabulary crosses the boundary?](#1-legibility-what-vocabulary-crosses-the-boundary)
    - [2. Programmability: what may policy do there?](#2-programmability-what-may-policy-do-there)
    - [3. Trust placement: who executes the decision?](#3-trust-placement-who-executes-the-decision)
    - [JavaScript gateways versus declarative LSMs](#javascript-gateways-versus-declarative-lsms)
  - [Filesystem mediation is a resource service](#filesystem-mediation-is-a-resource-service)
    - [The path-policy soundness trap](#the-path-policy-soundness-trap)
  - [Protocol gateways can see what kernels cannot](#protocol-gateways-can-see-what-kernels-cannot)
  - [Secret possession is not authority containment](#secret-possession-is-not-authority-containment)
  - [Threat model by enforcement plane](#threat-model-by-enforcement-plane)
  - [Cost and compatibility](#cost-and-compatibility)
  - [A complete enforcement stack](#a-complete-enforcement-stack)
  - [Replaceable runtimes, stable authority boundary](#replaceable-runtimes-stable-authority-boundary)
  - [Recommended architecture](#recommended-architecture)
- [Act II — Architectures, Models, and Authority Artifacts](#act-ii--architectures-models-and-authority-artifacts)
  - [Object capabilities: the authority model](#object-capabilities-the-authority-model)
  - [WebAssembly and WASI: imported effects](#webassembly-and-wasi-imported-effects)
  - [Effect systems: making effects explicit](#effect-systems-making-effects-explicit)
  - [Macaroons and JWTs: reifying an authorization grant](#macaroons-and-jwts-reifying-an-authorization-grant)
  - [Flask and LSMs: the reference-monitor architecture](#flask-and-lsms-the-reference-monitor-architecture)
  - [Proxies are one transport for a gateway](#proxies-are-one-transport-for-a-gateway)
  - [The architecture is recursive](#the-architecture-is-recursive)
- [Act III — Agents Turn Authority into a Runtime Protocol](#act-iii--agents-turn-authority-into-a-runtime-protocol)
  - [1. Data becomes executable](#1-data-becomes-executable)
  - [2. There is a semantic governance plane](#2-there-is-a-semantic-governance-plane)
  - [3. Authority is temporal](#3-authority-is-temporal)
  - [4. Policy cannot be completely enumerated in advance](#4-policy-cannot-be-completely-enumerated-in-advance)
  - [5. The confined workload is also a delegate](#5-the-confined-workload-is-also-a-delegate)
  - [Agent-specific threats](#agent-specific-threats)
    - [Inference-endpoint exfiltration](#inference-endpoint-exfiltration)
  - [Harness placement and the trust split](#harness-placement-and-the-trust-split)
  - [Conclusion](#conclusion)
- [References](#references)
  - [Primary implementation sources](#primary-implementation-sources)
  - [Kernel security mechanisms](#kernel-security-mechanisms)
  - [Capability and authority foundations](#capability-and-authority-foundations)
  - [WebAssembly and effect systems](#webassembly-and-effect-systems)
  - [Agent frameworks and research](#agent-frameworks-and-research)
  - [Landscape and performance](#landscape-and-performance)


## Compute containment and capability gateways for untrusted agents

Sandboxing discussions usually begin with the wrong noun. They ask whether untrusted code should run in a container, a microVM, gVisor, WASI, or a language runtime. Those choices matter, but they answer only **where computation happens**. They do not answer **what authority that computation can exercise**.

A process inside a perfectly isolated VM can still exfiltrate source code through an allowed API, mutate a host-mounted repository, publish a poisoned artifact, spend cloud credentials, or invoke a token's full administrative authority. Compute isolation protects the host kernel and memory. It does not, by itself, protect resources deliberately exposed to the workload.

A complete design therefore consists of two coupled systems:

> **A replaceable compute sandbox connected to a non-bypassable, host-trusted capability gateway.**

The compute sandbox removes ambient access to the host. The capability gateway selectively reintroduces useful authority as narrow, adjudicated operations: read this workspace, call this API method, publish this artifact, connect using this database role. Raw credentials and host resources remain outside the guest.

The word *coupled* is doing important work. A proxy is not enforcement if the workload can route around it. A VM does not contain authority if it directly mounts host state or receives durable credentials. The runtime must guarantee that every external effect crosses the gateway; the gateway must guarantee that every effect is evaluated under a host-authenticated sandbox identity.

This article develops that model in three acts. **Act I** derives the architecture: compute containment, capability mediation, and the contract joining them. **Act II** separates three kinds of precedent: enforcement architectures such as Flask, LSMs, WebAssembly, and host brokers; authority models such as object capabilities and effect systems; and artifacts such as JWTs and macaroons that carry a grant forward for later verification. **Act III** describes the delta introduced by agents: data that behaves like instructions, authority acquired dynamically, semantic tool calls, prompt injection, and capabilities that should expire when a subgoal ends.

Most writing on "AI sandboxing" is really writing on sandboxing, with agents supplying the motivation. The useful distinction is not that agents make isolation necessary. It is that agents turn authority into a continuously negotiated runtime protocol.

![sandboxing-taxonomy](/assets/llm-sandbox/confinement-hierarchy.png)


# Act I — Containing Computation Is Not Containing Authority

## The unit of analysis is the external effect

VM versus container is not the right first debate. The first question is what effects the workload can cause:

- Can it read host files?
- Can it mutate durable state?
- Can it contact the internet, localhost, or a metadata service?
- Can it exercise an API credential?
- Can it publish an artifact that will execute later?
- Can it signal, inspect, or interfere with another workload?

The same effect can be controlled at several points. A write to a repository might be prevented because the host path is absent, denied by a guest LSM, rejected by a host VFS provider, blocked by a tool hook, or refused by server-side branch protection. These mechanisms are not interchangeable. They see different vocabularies and live in different trust domains.

Two strategies recur across all of them:

- **Unnameability** — the raw resource is absent from the reachable universe, so no direct request is possible. Mount, PID, IPC, and network namespaces do this per kernel-object class; a VM does it for the host machine; WASI does it by omitting APIs; a capability-safe interface does it by withholding ambient names.
- **Adjudication** — the request is expressible, but an enforcement point judges it. Seccomp filters syscalls; LSMs judge kernel-object operations; a VFS provider judges filesystem requests; an egress gateway judges HTTP or SQL; a tool hook judges agent actions.

These are functions, not mutually exclusive technology categories. A mechanism may provide either or both. Namespaces primarily alter the resource universe a process can name. Seccomp adjudicates entry to the syscall interface using syscall numbers and scalar arguments. LSMs adjudicate operations on resolved kernel objects using subject, object, operation, and kernel context. WASI combines a restricted execution universe with explicitly imported authority.

The strongest systems compose the two. They make the **raw authority unnameable** and expose only a **restricted, adjudicated capability**.

For a credential:

```text
real GitHub token
    absent from guest memory

placeholder handle
    visible to guest
    usable only through the gateway
    valid only for approved GitHub operations
```

For a filesystem:

```text
host home directory
    absent from guest mount table

/workspace
    visible through a host VFS service
    selected reads and writes allowed
    persistence explicitly controlled
```

This is more than layering one filter over another. It is **authority attenuation**: replacing possession of a powerful resource with permission to request a smaller set of effects.

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

## Three independent properties of enforcement

The phrase *policy expressivity* commonly collapses three independent questions.

### 1. Legibility: what vocabulary crosses the boundary?

```text
more semantic
    agent intent and tool calls
    Git operations and SQL statements
    HTTP methods, paths, headers, and bodies
    filesystem paths, inodes, and operations
    IP addresses, ports, and flows
    block offsets and Ethernet frames
more structural
```

### 2. Programmability: what may policy do there?

```text
fixed behavior
static allow/deny configuration
declarative subject × object relations
programmable decisions
stateful policy and external approval
transformation, emulation, and resource synthesis
```

### 3. Trust placement: who executes the decision?

```text
agent harness
guest process
guest kernel
host process or host kernel
hypervisor
remote resource server
```

![image](/assets/llm-sandbox/legibility-vs-programmability.png)

Non-bypassability is related but different. It is not a property of a policy language or hook. It is a property of the complete topology: can the workload reach the protected resource through some other path?

This makes several comparisons clearer.

### JavaScript gateways versus declarative LSMs

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

## Threat model by enforcement plane

The earlier two-column model—unnameability versus adjudication—hides trust placement. In particular, "malicious code defeats adjudication" is true of in-guest adjudication but false of a host gateway designed to distrust the guest kernel.

| Threat | Compute boundary | Guest LSM | Capability gateway | Semantic governance | Upstream controls |
| --- | --- | --- | --- | --- | --- |
| **G1** Confused or buggy destructive process | Contains guest damage; snapshots roll it back | Restricts processes internally | Protects host and durable effects | Catches obvious actions | Limited |
| **G2** Actively malicious code or compromised guest kernel | Protects host kernel and memory | Defeated with the guest kernel | Still protects external authority | Arbitrary code can bypass its harness | Protects the remote resource |
| **G3** Persistence into later execution | Makes local guest state disposable | Restricts dangerous guest writes | Controls host VFS writes and publication | Sees hooks, CI edits, and similar intent | Branch, signing, and deployment policy |
| **G4** Exfiltration through an allowed host | Little once a route is deliberately granted | Limited | Constrains request semantics and credential use | May recognize suspicious intent | Least-privilege API and token scope |
| **G5** Lateral movement to localhost, RFC1918, or metadata | Removes raw host routes | Restricts guest sockets | Rejects internal destinations and rebinding | Secondary | Network-side controls |
| **G6** Resource exhaustion | CPU, memory, and device ceilings | Weak | Request, bandwidth, and parser-work quotas | Weak | Rate limits |
| **G7** Microarchitectural side channels | Limited; requires scheduling/hardware measures | None | None | None | Confidential computing may change host trust |

The table exposes the central division:

> **The compute boundary contains execution. The capability gateway contains authority.**

Neither dominates, and a failure in their contract can invalidate both.

## Cost and compatibility

Strength comparisons omit the variable that determines what people actually run. Cold starts span orders of magnitude, as does per-instance memory. Snapshot capability matters as much as nominal isolation: disk snapshots give rollback, while memory snapshots enable fork-from-snapshot and a different workload architecture.

Mediation has its own tax. Every filesystem operation becoming a host RPC is fine for source files and potentially ruinous for large builds. A useful layout keeps toolchains, dependency caches, object files, and scratch data on a guest-local block device while exposing only source, selected outputs, and publication operations through the semantic gateway.

The stronger version is not to mount the host repository at all. Clone it inside the guest, work locally, and publish changes through a controlled Git or artifact capability. This deliberately trades filesystem legibility for absence. It is often both faster and safer.

The dominant failure mode of a strong sandbox is that users disable it. A boundary that survives normal tests, local sockets, language servers, package managers, and caches is more valuable than a theoretically stronger profile that daily work routes around.

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

## Replaceable runtimes, stable authority boundary

The capability-gateway abstraction makes the compute layer replaceable, but not irrelevant. A coding workload wants a rich, relatively long-lived environment with fast filesystem access, package caches, test servers, and an explicit publication path. A recursive-inference workload may want many cheap, ephemeral, forkable environments where memory-snapshot cloning matters more than a sophisticated workspace VFS.

The same gateway concepts can serve both while the runtime optimization differs. Do not make one sandbox implementation serve every workload, and do not couple external authority to one runtime forever.

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


# Act II — Architectures, Models, and Authority Artifacts

The split between computation and authority is not peculiar to Gondolin, proxies, or agents. It recurs whenever a system prevents a component from directly naming or exercising ambient authority, then reintroduces selected effects through a controlled interface.

The recurring shape is:

```text
restricted computation
    → presents an explicit handle or request
        → trusted interpreter checks context and policy
            → external effect occurs
```

The resemblance is real, but the entries below are not peers. Some are complete enforcement architectures, some are abstract models for reasoning about authority, and some are portable artifacts produced by an authorization decision. Treating all of them as alternative “systems” hides more than it reveals.

| Thing | What kind of thing is it? | What it contributes to this article |
| --- | --- | --- |
| **Gondolin** | Concrete cross-boundary enforcement architecture | VM containment plus host VFS and network authority mediation |
| **Wasm/WASI** | Execution model and host-interface architecture | A restricted computation universe with explicitly imported effects |
| **Flask / LSM** | Reference-monitor architecture and kernel enforcement framework | Policy decision separated from complete mediation of kernel-object operations |
| **Object capabilities** | Authority model and family of system designs | Authority represented by possession of an unforgeable reference rather than an ambient name |
| **Effect systems and handlers** | Programming-language model, sometimes enforced by a runtime | Effects made explicit and interpreted at a semantic interface |
| **Macaroons, JWTs, and OAuth tokens** | Serialized authorization artifacts | A previous grant or set of claims carried forward for later verification |

This distinction matters. Gondolin, Flask, and WASI describe where enforcement occurs and why requests cannot bypass it. Object-capability theory describes what it means to possess authority. A JWT or macaroon is neither a sandbox nor a reference monitor; it is evidence or a portable capability presented to one.

## Object capabilities: the authority model

Object-capability theory gives the cleanest conceptual statement of the model. An unforgeable reference both designates an object and conveys permission to invoke its interface. Code that lacks the reference lacks the corresponding authority; there is no separate global namespace from which it can recover the object by guessing a name. Actual object-capability systems embody this model, but the model itself is the important contribution here.

The interface can expose less authority than the underlying resource:

```text
repository administrator token
    → capability: openPullRequest(repository = X)

database owner credential
    → capability: query(view = analytics, budget = 1000 rows)

host directory
    → capability: readTree(root = /workspace/src)
```

This is the conceptual core of a capability gateway. The gateway retains a powerful resource and gives the workload a reference to an attenuated operation. A Gondolin proxy token, VFS mount, synthetic file, or publication handle can all be understood this way, provided they are unforgeable, scoped, and bound to the sandbox identity.

Capability terminology also corrects a common intuition about secrets. A secret byte string is not the important resource; the important resource is the authority a service grants to its presenter. Preventing extraction is valuable, but it is not enough. A deputy that will apply a hidden root token to any attacker-chosen request has protected the bytes and exposed the authority. The interface must attenuate use, not merely hide representation.

## WebAssembly and WASI: imported effects

WebAssembly provides the closest structural parallel to the complete architecture. A Wasm module begins with linear memory and computation. It does not inherit a POSIX process's ambient filesystem, network, environment, or clock. Useful interaction arrives through imports supplied by the host.

Under the WASI component model, resources such as files, streams, sockets, and clocks appear through typed interfaces and handles. The host runtime decides which implementations and resources to supply. The module can request only effects expressible through that interface, and the host remains responsible for interpreting them.

```text
Wasm module
    → imported WASI operation
        → host runtime
            → selected filesystem, socket, clock, or service
```

This is unnameability followed by adjudicated reintroduction. The module cannot perform an ordinary host syscall behind the runtime's back. Its effect vocabulary is also legible: `open-at`, a stream write, or a typed component call is more meaningful than a block offset or Ethernet frame.

Wasm therefore suggests a useful description of Gondolin's ambition:

> **Provide a WASI-like authority shape for unmodified Linux software: preserve a normal Linux environment inside the VM while replacing ambient external authority with host-mediated capabilities.**

The analogy has limits. A general Linux guest contains a kernel, arbitrary native binaries, conventional sockets, and a much larger local namespace. Gondolin must construct non-bypassability through VM devices and host networking, while Wasm obtains much of it from the execution semantics. In exchange, the VM runs software that was never designed for a capability-oriented ABI.

## Effect systems: making effects explicit

Effect systems approach the same separation from programming-language semantics. Instead of allowing a function to perform hidden I/O, state mutation, exceptions, or nondeterminism, the language records or represents those effects. An effect handler supplies their interpretation.

```text
computation requests Network.send
    → handler may execute, deny, record, transform, or emulate it
```

This resembles a programmable gateway in two ways. First, effects cross an explicit semantic interface. Second, the interpreter may do more than return allow or deny: it can synthesize a result, redirect state, maintain a budget, or delegate the decision.

But a type-and-effect system is not automatically a security boundary. It may prove that cooperative source code declares its effects without preventing native code, foreign-function interfaces, unsafe operations, or a compromised runtime from bypassing the handler. It becomes a confinement mechanism only when the language and runtime guarantee that all relevant external effects are captured.

The lesson for sandbox design is broader than adopting an effect language. Interfaces become easier to govern when the effect is named at the level at which policy cares. `publishArtifact` is a better policy event than a sequence of file writes and HTTP requests—but only if lower-level routes cannot bypass it.

## Macaroons and JWTs: reifying an authorization grant

Macaroons, JWTs, and OAuth access tokens solve a different problem from the systems above. They serialize the result or inputs of an authorization process so that a later request need not return to the original decision-maker and reconstruct the decision from scratch. In that sense they are a cacheable, portable reification of authority.

The analogy to a cached policy decision is useful but not exact. A verifier still checks cryptographic validity, issuer, audience, expiry, and often current resource state or revocation data. A JWT may contain claims from which the resource server makes a fresh decision rather than an already-final allow result. A macaroon goes further toward a reified capability: a holder can attenuate it by adding caveats such as repository, method, time, request budget, or required third-party discharge without learning or reissuing the root key.

```text
may access GitHub
    only repository X
    only pull-request operations
    before 17:00
    for sandbox Y
```

The resource server verifies those caveats before honoring the request. This fits naturally inside a gateway: a controller makes a grant for a subgoal, encodes it in a macaroon, and the guest later presents that artifact to the gateway or upstream service. The token carries authority across time or process boundaries; the verifier remains the enforcement point.

A macaroon does not itself isolate computation, retain some separate root credential, or remove alternate network paths. It is an authority artifact, not a sandbox or system decomposition. Its value here is to demonstrate that attenuation, delegation, context, and expiry can be properties of a reified grant rather than one global process profile.

JWTs and OAuth access tokens offer a useful contrast. They commonly encode subject, audience, expiry, and scopes, but are often bearer credentials: whoever extracts the token can exercise their authority wherever the resource server accepts them. A short-lived, audience-restricted JWT is much safer than a durable administrator token, yet giving it to the guest still transfers possession of the reified grant.

A host-only token behind an opaque guest handle separates possession from use:

```text
guest holds opaque handle
    → gateway validates sandbox, destination, method, and policy
        → gateway presents real token to the resource server
```

The strongest construction often combines both approaches: narrowly scoped and short-lived upstream credentials limit the gateway's maximum authority, while a non-exportable gateway handle further limits what the guest can ask it to do.

## Flask and LSMs: the reference-monitor architecture

The Flask architecture gives the clearest theoretical bridge between kernel access control and a host resource gateway. Flask separates **object managers**, which own resources and enforce decisions, from a **security server**, which evaluates policy. An object manager asks whether a subject may perform an operation on an object, caches the returned access vector, and receives notifications when policy changes require revocation.

The architecture depends on reference-monitor properties: security-relevant requests must encounter the enforcement mechanism, the mechanism must be isolated from the subjects it controls, and its implementation must be amenable to assurance. These are the same requirements this article has called completeness, trust placement, and non-bypassability.

LSM brought this pattern into Linux at the kernel-object boundary. Rather than interposing only at syscall entry, the kernel first resolves user-supplied names and handles into internal objects, then invokes an LSM hook immediately before a security-relevant operation. The resulting question is explicit authority mediation:

```text
May subject S perform operation OP on kernel object OBJ?
```

This distinguishes LSMs from seccomp. Seccomp mediates the syscall interface using syscall numbers and scalar arguments; it normally cannot dereference a pathname pointer or reason about the resolved inode. An LSM sees the kernel object and relevant kernel context, regardless of which syscall route produced it.

The correspondence to a host capability gateway is structural:

| Reference-monitor concept | Guest LSM | Host capability gateway |
| --- | --- | --- |
| Subject | Guest process, credentials, or security label | Host-authenticated VM or sandbox identity |
| Object | Inode, socket, task, IPC object | Host file, API account, credential, database, publication target |
| Operation | Open, execute, connect, signal, mount | Read path, issue HTTP request, sign, query, publish |
| Object manager / enforcer | Kernel subsystem plus LSM hook | VFS provider, protocol broker, or resource service |
| Policy decision | AppArmor, SELinux, Landlock, or BPF-LSM logic | Host declarative rules, JavaScript callback, or policy service |

The difference is trust placement. An in-guest LSM assumes the guest kernel remains the reference monitor. Gondolin places mediation of selected external objects in a host process that treats the entire guest—including its kernel—as one untrusted subject.

Capsicum, namespaces, and syscall brokers instantiate adjacent pieces of the pattern. Namespaces and capability mode remove ambient names; seccomp restricts the operation vocabulary; LSMs insert policy into the kernel-object access path. They often provide stronger coverage and weaker application semantics than a host gateway.

An LSM can reliably see a process attempting to open an inode, send a signal, or bind a port. It generally cannot tell whether a sequence of those operations means “publish a release approved for this task.” Conversely, a tool hook or HTTP gateway may understand that meaning but cover fewer ways of producing the underlying effect.

This is why an in-guest LSM is a complement rather than an alternative to Gondolin's host gateway:

- The guest LSM compartments processes and kernel objects while the guest kernel remains trustworthy.
- The VM contains a compromised guest kernel relative to the host.
- The host gateway controls external resources and credentials even if the entire guest is one adversarial principal.
- The upstream resource server enforces the final invariant in its own domain.

Each layer interprets effects at a different vocabulary and survives a different failure.

## Proxies are one transport for a gateway

Iron Proxy and Gondolin's network mediation are topologically forward proxies: they stand between an outbound client and destination servers. Their unusual property is not the direction of forwarding but the security relationship. The client is adversarial, the proxy holds authority the client does not possess, and policy determines whether and how each request is made.

That makes them **adversarial-client forward proxies functioning as capability gateways**. The forward/reverse distinction remains useful for network placement, but it does not generalize to files, databases, signing keys, or publication handles. “Capability gateway” names the security role; “forward proxy” names one implementation shape.

The distinction also exposes the contract again. An `HTTP_PROXY` variable is merely a cooperative convention. A capability gateway becomes enforcement only when the runtime removes every alternate route to the protected destination. Iron Proxy can be combined with forced routing such as nftables or TPROXY. Gondolin can make the relationship tighter by withholding ordinary NAT and making the host network backend the guest's only peer.

## The architecture is recursive

These examples can be nested rather than chosen exclusively. A Wasm component may run inside a Linux guest constrained by an LSM. The guest may present an attenuated capability to a host gateway. The gateway may use a narrowly scoped OAuth token to call a service whose own authorization policy protects the final resource.

At every boundary, ask the same questions:

1. What computation is inside the boundary?
2. What raw authority has been made unnameable?
3. What handle or request vocabulary crosses the boundary?
4. Which trusted component interprets it?
5. Can the requester bypass that interpreter?
6. What is the interpreter's maximum authority if its policy fails?

This recursive view prevents a false choice between capabilities, language effects, kernel security, VM isolation, and proxies. They are placements of the same basic pattern at different semantic levels and trust boundaries.


# Act III — Agents Turn Authority into a Runtime Protocol

Everything above applies to arbitrary untrusted code. Agents introduce several structural changes.

## 1. Data becomes executable

Generic sandboxing assumes that code is untrusted and data is inert. An LLM weakens that distinction: any README, issue, webpage, source comment, tool output, or retrieved document may change subsequent behavior.

Compute containment and capability mediation primarily govern outbound effects. They do not decide whether an inbound sentence is an instruction. Prompt injection rides through the same channels the agent legitimately needs.

The practical answer is not an "input sandbox." It is to assume intent can be corrupted and ensure that resulting effects still encounter narrow capabilities, trusted enforcement, and upstream policy.

## 2. There is a semantic governance plane

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

## 3. Authority is temporal

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

## 4. Policy cannot be completely enumerated in advance

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

## 5. The confined workload is also a delegate

Traditional confinement limits software you want to do as little as possible. An agent is valuable precisely because it can act broadly on a user's behalf.

The core tension is not merely least privilege. It is **useful delegation without ambient authority**.

Act II supplied the underlying object-capability model: do not hand a delegate a global name and durable credential. Hand it a reference to a narrower operation, with contextual caveats, and retain the ability to revoke or decline each invocation. Agents make that old design problem continuous. They form new subgoals, encounter new resources, and request new authority throughout a run, so capability issuance becomes part of the runtime protocol rather than a one-time launch configuration.

## Agent-specific threats

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

## Conclusion

The framing trap is to see a weak mechanism and immediately replace it with a stronger boundary. Often the actual failure is that policy lived at the wrong semantic level, in the wrong trust domain, or on a path the workload could bypass.

A VM protects the host kernel but cannot decide whether a GitHub API operation is justified. An HTTP proxy can understand that operation but is optional if raw egress remains. A guest LSM can separate processes but falls with the guest kernel. A tool hook can understand intent but arbitrary code can route below it. Branch protection is authoritative but sees only the final Git operation.

The argument has three layers. First, containing execution and containing authority are different jobs joined by a non-bypassable contract. Second, that architecture has precedents at several conceptual levels: Flask and LSMs supply the reference-monitor pattern, Wasm imports and protocol brokers provide concrete mediated interfaces, object capabilities provide a model of authority, and tokens can reify grants for later use. Third, agents make the composition dynamic because their useful authority changes with the plan and because untrusted data can influence which capabilities they request.

The architecture is therefore not a single best sandbox. It is a composition:

> **A replaceable compute sandbox connected to a non-bypassable, host-trusted capability gateway, reinforced by guest-internal policy, semantic action governance, and resource-owner controls.**

The compute sandbox determines which universe the workload inhabits. The capability gateway determines which external authority that universe may exercise. The contract between them is the boundary.


# References

## Primary implementation sources

- [Gondolin — security design](https://earendil-works.github.io/gondolin/security/) — threat model, host trust boundary, network mediation, secret substitution, filesystem confinement, and explicit limitations
- [Gondolin — architecture](https://earendil-works.github.io/gondolin/architecture/) — VM lifecycle, `vm.exec` over virtio-serial, `sandboxd`, VFS RPC, and host/guest component placement
- [Gondolin — VFS providers](https://earendil-works.github.io/gondolin/vfs/) — programmable resource providers, real-filesystem hardening, read-only and shadow layers, and provider composition
- [Gondolin — QEMU backend](https://earendil-works.github.io/gondolin/qemu/) — minimal device model and the decision to keep the host as the guest's network peer
- [Iron Proxy](https://github.com/paradigmxyz/iron-proxy) — untrusted-client forward proxy, default-deny egress, proxy-token secret substitution, request transforms, auditing, and routing requirements
- [Lima — filesystem mounts](https://lima-vm.io/docs/config/mount/) — reverse-SSHFS, 9p, virtiofs, and mount behavior across VM drivers

## Kernel security mechanisms

- [Linux Security Module usage](https://docs.kernel.org/admin-guide/LSM/index.html) — the LSM framework, major and minor LSMs, stacking, and active-module inspection
- [Linux Security Module development](https://docs.kernel.org/security/lsm-development.html) — kernel hooks exposed to security modules
- [Linux Security Modules: General Security Support for the Linux Kernel](https://www.usenix.org/legacy/publications/library/proceedings/sec02/full_papers/wright/wright_html/) — original LSM design, including race-free mediation of subject–operation–kernel-object requests
- [The Flask Security Architecture](https://www.cs.cmu.edu/~dga/papers/flask-usenixsec99.pdf) — separation of object managers and security decisions, access-vector caching, policy flexibility, and revocation
- [AppArmor — Where Do LSMs Fit?](https://apparmor.net/about/lsm_introduction/) — comparison of syscall filtering, DAC, MAC, and resolved-object LSM hooks
- [Landlock: unprivileged access control](https://docs.kernel.org/userspace-api/landlock.html) — monotonic self-restriction over filesystem, network, and limited IPC scope
- [Linux capabilities](https://man7.org/linux/man-pages/man7/capabilities.7.html) — split-up root privileges, capability sets, file capabilities, and user-namespace interactions
- [Linux namespaces](https://man7.org/linux/man-pages/man7/namespaces.7.html) — resource virtualization across mount, PID, network, IPC, user, UTS, cgroup, and time namespaces
- [BPF LSM programs](https://docs.kernel.org/bpf/prog_lsm.html) — programmable eBPF policy attached to LSM hooks
- [Capsicum: Practical Capabilities for UNIX](https://www.usenix.org/conference/usenixsecurity10/capsicum-practical-capabilities-unix) — capability mode and application compartmentalization in a conventional UNIX environment

## Capability and authority foundations

- [Capability Myths Demolished](https://cgi.cse.unsw.edu.au/~cs9242/20/papers/Miller_YS_03.pdf) — capability-system terminology, authority, designation, confinement, and common misconceptions
- [The Confused Deputy](https://www.cs.utexas.edu/~witchel/S25-380L/papers/hardy88confused.pdf) — the classic description of a program misusing authority on behalf of an untrusted requester
- [Macaroons: Cookies with Contextual Caveats for Decentralized Authorization in the Cloud](https://static.googleusercontent.com/media/research.google.com/en/us/pubs/archive/41892.pdf) — attenuable bearer capabilities with contextual caveats
- [JSON Web Token (JWT), RFC 7519](https://www.rfc-editor.org/rfc/rfc7519.html) — signed claims, audiences, expiry, and bearer-token representation
- [OAuth 2.0 Authorization Framework, RFC 6749](https://www.rfc-editor.org/rfc/rfc6749.html) — delegated access tokens, scopes, resource servers, and bearer-token deployment

## WebAssembly and effect systems

- [WebAssembly Component Model — Components](https://component-model.bytecodealliance.org/design/components.html) — typed imports, exports, composition, and interface-only component interaction
- [WASI security principles](https://github.com/bytecodealliance/wasi.dev/blob/main/docs/security.md) — capability-oriented host access and the security model for WASI interfaces
- [Handling Algebraic Effects](https://arxiv.org/abs/1312.1399) — effect handlers as programmable interpretations of explicitly invoked effects

## Agent frameworks and research

- [The Agent Sandbox Taxonomy](https://github.com/kajogo777/the-agent-sandbox-taxonomy) — defense layers, threats, strength, granularity, and action governance
- [Lingering Authority: Revocable Resource-and-Effect Capabilities for Coding Agents](https://arxiv.org/abs/2606.22504) — epoch-bound capability handles and the request–grant–invoke lifecycle
- [Recursive Language Models](https://alexzhang13.github.io/blog/2025/rlm/) — context as a live variable and recursive partition-and-map workloads
- [Inspect](https://inspect.aisi.org.uk/) — an agent/evaluation harness with model and tool semantics

## Landscape and performance

- [AI agent sandbox technologies: a 2026 comparison](https://grigio.org/ai-agent-sandbox-technologies-a-complete-2026-comparison/) — startup, memory, eBPF network mediation, and confidential-computing comparisons
- [Best microVM sandboxes for AI code execution](https://modal.com/resources/best-microvm-sandboxes-ai-code-execution) — vendor-authored comparison including filesystem, directory, and memory snapshot capabilities
- [List of coding agent sandboxes](https://gist.github.com/wincent/2752d8d97727577050c043e4ff9e386e) — curated index of OS primitives, application kernels, microVM runtimes, and local CLI sandboxes
