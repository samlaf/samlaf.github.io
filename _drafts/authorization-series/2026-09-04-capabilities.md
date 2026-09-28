---
title:  "Capabilities: authority you hold, not authority you are"
series: "Authorization, Part 4"
series_url: "/programming/authorization-series-intro.html"
category: programming
date:   2026-09-04
---

> This is Part 4 of a four-part [series on authorization](/programming/authorization-series-intro.html).
>
> - **[Part 1: Authorization models](/programming/authorization-models.html)** — what every system computes, and who may change it.
> - **[Part 2: How authority is enforced](/programming/authority-enforcement.html)** — what makes any of it binding.
> - **[Part 3: Carriers](/programming/carriers.html)** — decisions that travel with the request.
> - **Part 4: Capabilities** — authority you hold, not authority you are.

- [Squaring the matrix](#squaring-the-matrix)
- [Four things get called capabilities](#four-things-get-called-capabilities)
  - [The six properties](#the-six-properties)
  - [Where the real systems land](#where-the-real-systems-land)
  - [The key metaphor](#the-key-metaphor)
- [Capabilities on the grid](#capabilities-on-the-grid)
  - [The properties, read on the grid](#the-properties-read-on-the-grid)
  - [Two bindings collapse the stages](#two-bindings-collapse-the-stages)
  - [Where the authority lives](#where-the-authority-lives)
- [Designation and authority](#designation-and-authority)
  - [The confused deputy is structural](#the-confused-deputy-is-structural)
  - [Cannot, not do not](#cannot-not-do-not)
- [Delegation](#delegation)
  - [Service chaining](#service-chaining)
  - [The control you think you have](#the-control-you-think-you-have)
- [The three objections](#the-three-objections)
  - [Revocation needs composability](#revocation-needs-composability)
  - [Accountability is the one ACLs lose](#accountability-is-the-one-acls-lose)
  - [The patches converge](#the-patches-converge)
  - [The convergence is not symmetric](#the-convergence-is-not-symmetric)
  - [Complete over the intended state, not the reachable state](#complete-over-the-intended-state-not-the-reachable-state)
- [Where the property can be bought](#where-the-property-can-be-bought)
- [Conclusion: one argument in four parts](#conclusion-one-argument-in-four-parts)
- [References](#references)

The [series intro](/programming/authorization-series-intro.html#from-a-chain-to-a-grid) follows a request through four stages: designate, reach, authenticate and decide. The industry has spent twenty years on the last two, and they are genuinely good now. Designate and reach, the stages that carry names and requests, are rarely treated as authorization at all. [Part 2](/programming/authority-enforcement.html#which-stage-do-you-cut) treated them as stages an enforcer can cut. This article treats them as stages an artifact can carry. Its subject is the carrier that serves several stages at once. That is where the only structural difference between capabilities and everything else lives.

[Part 3](/programming/carriers.html#from-one-stage-to-several) ended on a line from bearer tokens to object capabilities, and this article is about its last two steps. It is also about a word that has been ruined by overuse. "Capability" names at least four distinct things, the arguments people have about capabilities are usually arguments about different ones, and most of the famous objections are true of some and false of others.

## Squaring the matrix

[Part 1](/programming/authorization-models.html#one-function-one-relation)'s access matrix assumes something it never argues for: that the world divides cleanly into subjects who act and resources that are acted upon. Alice is a row. File A is a column. Nothing is both.

That assumption is what makes mediation inexpressible. If Alice holds a reference to Bob, and Bob holds a reference to X, the matrix wants to record `Alice: rw X`. That is wrong. Bob is in the middle, and Bob can refuse, revoke, log, or forward only a subset. To write it down you would need Bob to be a row *and* a column at once, and in a rectangular matrix he cannot be.

So drop the assumption. Let both axes range over the same set of entities, and read a cell as *which of Y's operations may X invoke*:

```text
          Alice    Bob    File A    Logger
Alice        —     call     rw         —
Bob          —       —      r        write
File A       —       —       —         —
Logger       —       —       —         —
```

Everything still works. ACLs and capability lists are the special case where the entity set partitions into two disjoint halves, so the bottom-left block is empty by construction and you may as well draw the matrix rectangular. Nothing is lost by squaring it; things become expressible that were not.

Three of them, and each is a rung Part 1's models could not reach.

**Mediation.** Bob is a row and a column. `Alice → Bob → X` is two cells, not one, and the difference between them is the entire value of a proxy.

**Communication as an access decision.** A cell `(Alice, Bob)` is a subject reaching a subject. Whether Alice may *talk to* Bob is now the same kind of question as whether Alice may read a file, answered by the same mechanism. In a rectangular matrix there is nowhere to ask it, which is why every model in Part 1 treats connectivity as someone else's problem — the network's, the linker's, the runtime's.

**A mutation rule written in the matrix's own terms.** Every model in Part 1 needs an outside notion of who may edit: an owner, an administrator, a lattice, a policy document. A square matrix can state its own rule. *Alice may write into Bob's row only if her own row already reaches both Bob and the thing she is granting.* Authority moves only along edges that already exist.

That last one is this whole article compressed into a sentence, and it is why the entity set also has to be allowed to grow: attenuation means minting a new proxy, which is a new row and a new column appearing at runtime.

## Four things get called capabilities

Miller, Yee and Shapiro's [Capability Myths Demolished][capability-myths-demolished] is the paper that sorts this out, and its central move is to define four models rather than two.

```text
Model 1   ACLs as columns
          authority stored at the resource; the subject presents a name

Model 2   capabilities as rows
          a row of the access matrix, held by the kernel on the subject's
          behalf; what a C-list is

Model 3   capabilities as keys
          unforgeable, copyable tokens; hand one to anyone you like;
          what the key metaphor describes

Model 4   object capabilities
          unforgeable references; designation and authority are one thing;
          you can only pass one to someone you can already reach
```

Model 1 is what you run. Model 4 is what every major capability system actually implements. Models 2 and 3 are how capabilities get *explained* — as a naive reading of Lampson's matrix, and as the key metaphor — and both explanations are wrong in ways that generate the standard objections.

### The six properties

The paper separates the models with six tests. This table is the densest thing in this series and it is worth reading slowly.

| | | M1 ACLs | M2 rows | M3 keys | M4 ocaps |
|---|---|---|---|---|---|
| **A** | Does designating a resource always convey its authority? | no *(impossible)* | unspecified | **no** | yes |
| **B** | Can subjects create new subjects? | no *(in practice)* | yes | yes | yes |
| **C** | Is the power to edit authorities aggregated by subject? | no *(in practice)* | yes | yes | yes |
| **D** | Must subjects select which authority to use? | no | **no** | yes | yes |
| **E** | Are resources also subjects? | unspecified | unspecified | **no** | yes |
| **F** | Must X already reach Y to pass Y an authority? | unspecified | unspecified | **no** | yes |

Four of these deserve names you will use again.

**Property A — no designation without authority.** Saying *which* object and saying *that you may use it* are the same act. The key model fails this, and the failure is easy to miss: you can hold a key without knowing which door it opens, and you can point at a door without holding its key. Designator and authority travel separately and something has to recombine them.

**Property D — no ambient authority.** You must select the authority you exercise. Unix fails this: `open()` takes a path and no credential, and the call simply succeeds or fails. Miller's image for ambient authority is a world of doors and no keys, where a door opens if it deems you worthy.

**Property E — composability.** Resources are also subjects. Without it you cannot build a revocable forwarder, because a forwarder is a resource that is also a subject.

**Property F — access-controlled delegation channels.** To hand Bob a capability you must already hold a capability to Bob. This is Miller's **"only connectivity begets connectivity"** stated as a test, and it is the property everything else in this article eventually reduces to.

E and F are the [square matrix](#squaring-the-matrix), arriving as tests. **E is the squaring itself** — one entity set on both axes, so a thing can be a row and a column at once. **F is the mutation rule the square matrix can state about itself** — you may write into Bob's row only if your own row already reaches both Bob and the authority you are handing over. Everything else in the table is a consequence of being able to say those two things.

Two things fall out immediately. Confinement fails in Model 3 precisely because F fails — if you can hand a key to anyone you can talk to, and you can talk to anyone, authority leaks wherever it likes. Revocation fails in Model 3 precisely because E fails — no composability, no forwarder to sever. So the two most famous objections to capabilities are *true statements about the key model*, which is the model everyone has in their head.

### Where the real systems land

The models are not academic. Three worked examples:

**Unix file descriptors** are nearly Model 4 and fall short on exactly one property. The difference from a pathname is visible in the types. A pathname is plain data: it names a slot in a global namespace, anyone can utter one, and uttering it conveys nothing. The descriptor `open` returns is a handle in a small per-process table that previous authorization decisions populated. You cannot guess one, and holding it is the whole of your permission to act. A descriptor is unforgeable, designation and authority coincide, and you must select one to act. But the channel that carries a descriptor between processes is a Unix socket, and that socket is governed by an ACL. So confining descriptor propagation depends on the ACL system rather than on the capability system. F fails at the seam.

**POSIX capabilities** fit Model 2 on every property above and still cannot support least privilege, because the set of resources is finite and fixed. Miller adds a seventh test for this — **Property G, dynamic resource creation** — and notes that no model limited to a static set of resources can have enough expressive detail to describe least authority on a live system.

**SPKI certificates** are Model 3. They designate a resource separately from conveying authority, and propagation is unrestricted: the holder may hand a copy to anyone.

That last one matters more than it looks, because SPKI is the shape most distributed "capability" systems take.

### The key metaphor

[Part 3](/programming/carriers.html#policy-and-mechanism) draws three ways to open a door: a physical key, a card checked against a central list, and a capability token. The third panel is the picture everyone draws, and it is Model 3. Worth being explicit, because the metaphor is doing quiet damage. A key ring gets Property D right — you must select a key — and gets A, E and F wrong. You can hold a key without knowing its door. A key is not itself a lock. And you may hand a copy to anyone you can physically reach, which in the physical world is anyone at all.

So the key metaphor teaches the correct lesson about ambient authority and the wrong lesson about confinement and revocation. It is a good picture of why capabilities are fast and offline, and a bad picture of what makes them safe.

## Capabilities on the grid

The [series intro](/programming/authorization-series-intro.html#from-a-chain-to-a-grid) follows one request through four stages: designate, reach, authenticate, decide. *Acquire* is the written half of designate: how the subject came to hold a name at all. One arrow matters more than the others here. It runs from reach back to acquire, because new names arrive only over channels the subject can already reach. Miller's phrase for it is "only connectivity begets connectivity," and the rest of this article calls it the loop. The six properties are tests on those stages.

### The properties, read on the grid

Each of Miller's properties is a claim about how the stages relate:

| | The test | On the grid |
|---|---|---|
| **A** | no designation without authority | one artifact carries designate and decide |
| **D** | no ambient authority | decide reads what the invocation carries, not who the subject is |
| **E** | resources are also subjects | whatever you reach can itself acquire and pass on names |
| **F** | you must reach Bob to pass Bob a capability | acquire runs only along reach: the loop |
| **G** | resources can be created | creating an object is one way to acquire a name |

Read this way, a capability is not a kind of token. It is what you get when one artifact designates, reaches and decides, and can be acquired only through another. Model 4 is the only model that insists on all of it.

### Two bindings collapse the stages

That collapse is not one thing. Two separate bindings produce it.

- **Name to route.** A *local* name — an FD index, a C-list slot, a heap pointer — means something only as an entry in a table the enforcer owns. The entry is the route, so designate and reach become one. A *global* name — a path, a URL, an IP address — can be uttered by anyone, and whether it gets anywhere is a separate question. What makes a name local is who resolves it, not what it looks like: an opaque string is local if only one enforcer's table resolves it and the holder can reach no other resolver.
- **Name to permission.** The rights sit in the table entry, or a secret or signature sits in the string. Either way, designate and decide become one.

The two are independent, so all four combinations exist:

```text
                        global name                 local name
                        reach is separate           the name is the route

authority checked       pathname + ACL              Java reference +
separately              OAuth (URL + token)         SecurityManager
                        SPKI

name bound to           share link                  FD under Capsicum,
authority               presigned S3 URL            WASI handle, CHERI,
                        Waterken                    object capability

                        bound in the string         bound in the entry
                                                    the name indexes
```

Models 1 and 3 both sit top left: the name is global and the authority travels apart from it. Property D splits them. Model 1's authority is ambient; Model 3's is a key you must select. Model 4 is bottom right.

The other two corners are the instructive ones. The bottom left satisfies A and still fails F. A share link joins name and authority, but a global name can travel to anyone, and the open internet delivers it wherever it goes. The top right is an unforgeable heap with ambient authority on top: Java references cannot be forged, but stack inspection makes the decision against the caller's principal. [Joe-E][joe-e-security-oriented] is what removing that looks like.

The column decides acquire. A global name can be guessed, listed or leaked, so it can arrive from anywhere. A local name can arrive only through a channel already held — provided no channel is global. Property F needs the right-hand column, and it needs the column clean: Java's mutable statics are a channel every object can reach, which is the second thing Joe-E removes.

[Part 2](/programming/authority-enforcement.html#one-enforcer-several-stages) draws the same split from the enforcer's side, as separate enforcers against one enforcer that spans the stages. The two views agree because a local name is one that a single enforcer resolves, routes and checks. The right-hand column here is the right-hand column there.

The worked examples above fall out directly. Unix descriptors sit bottom right, and fail F only because the socket that carries one is reached by pathname, a global name, and guarded by an ACL. SPKI sits top left.

### Where the authority lives

The table's two columns answer one question: where does the authority live? A global name with the authority inside it is a carrier from [Part 3](/programming/carriers.html): the authority travels in the artifact. A local name is an index into a table the reference monitor owns, and the authority never leaves that table. On the grid, the first is the Carried row. The second is the Written row, a per-subject namespace, judged by one monitor that spans the stages.

| | authority lives in the artifact | authority lives in a table the enforcer owns |
|---|---|---|
| on the grid | Carried | Written: a per-subject namespace |
| the holder presents | the authority itself | an index into the table |
| model | 3: keys | 4: object capabilities |
| Property F | fails: a copy can travel over any channel | holds: passing one goes through the enforcer |
| revocation | reach every copy | the table's owner revokes |
| examples | presigned URL, share link, macaroon, SPKI certificate | FD, seL4 capability, a reference in a memory-safe heap |

The placement predicts the table of properties. Put the authority in a carrier, and F fails and revocation turns into debt: the two famous failures of Model 3. Put it in a table the enforcer owns, and both come back. Passing a descriptor is not copying a token. The kernel writes a new entry into the recipient's table, which is why it can refuse the pass, and why seL4 can revoke along the derivation tree.

Binding a carrier to a key does not move it across. A key-bound token stops a stranger from using a stolen copy, but the holder can still pass the authority on, by handing over the token and signing for the recipient, or by acting as a proxy. That is why SPKI is Model 3, although every SPKI certificate is bound to a key.

Across machines, the line falls where the connection ends. Over a live Cap'n Proto connection, each side keeps a table of imported and exported references, and a reference on the wire is an index into the peer's table: Model 4, with the connection as the channel F needs. A reference that must outlive the connection, or reach a party you are not connected to, has to be written out as a string. Cap'n Proto calls that a SturdyRef, E calls its secret a Swiss number, and Waterken makes it an HTTPS URL. The string carries the authority, so it is a carrier, and the capability has dropped to Model 3.

> **A carried token is what a capability becomes when it has to leave the enforcer's table.**

## Designation and authority

Property A has a second name, from a completely different tradition. Alan Karp, who built E-speak at HP and spent fifteen years arguing about this, states the same thing as a claim about *requests*:

> The root cause of the problem is that the authentication presented with the request is necessarily independent of the request, which means the authentication necessarily represents all the permissions assigned to me.

That is Property A read from the wire rather than from the object graph. A credential that arrives alongside a request, rather than inside it, cannot be specific to the request. It therefore carries everything its holder has.

This is why Karp puts identity, roles and attributes in one family, NBAC, from [Part 3](/programming/carriers.html#where-and-when). All three answer "who is asking," and the answer is independent of what is being asked. ZBAC presents an authorization with the request instead.

The two vocabularies are worth holding at once. Miller is describing an object graph; Karp is describing a protocol. They are making the same claim.

### The confused deputy is structural

Norm Hardy's [The Confused Deputy][confused-deputy] is the canonical failure. A compiler holds write access to a billing file. A user invokes it and names the billing file as the destination for debugging output. The compiler overwrites the billing data, because it *can*, and because the request named a path rather than carrying a reference.

The usual reading is that the compiler was careless. Miller's reading is sharper:

> The problem is not caused by the compiler using access that it should not have. The problem is that it exercises its authority to write to BILL for the wrong purpose.

And the reason it cannot tell is Property D. If you cannot identify which authority you are using, you cannot associate a purpose with it. With keys you could label each one on receipt — *this one is for billing, that one came from the user* — but labelling is impossible when keys appear on the ring without your knowledge. Which is what ambient authority is.

Karp's version adds the cure. Alice invokes the compiler and delegates read on the input and write on the output. She only holds read on the billing file, so an attempt to delegate write to it fails at the source. The attack does not get as far as the deputy.

There is a nice piece of historical irony here: the web copy of Saltzer and Schroeder everyone links to was put online by Norm Hardy.

### Cannot, not do not

Karp is careful about a distinction that is easy to blur. He does not claim ACL systems *do not* support the kinds of sharing we need. He claims they *cannot*, and the argument is short enough to check.

The authentication accompanying a request is independent of the request. So the access decision allows the request if *any* of the requester's permissions matches it. So there is no place to attach a specific right to a specific argument.

His example is `cp File1 File2`. Get the arguments backwards and you destroy File1, and no ACL, role, attribute or relationship graph can save you, because the mechanism has nowhere to write down "this argument carries read and that one carries write." Pass open handles instead and the wrong order simply fails: the process tries to write to something it opened read-only.

The same structure explains malware. Every program you run authenticates as you, so every program you run holds everything you hold.

## Delegation

[Part 3](/programming/carriers.html#three-kinds-of-delegation) separated three kinds of delegation. Only the third, authority delegation, hands over one specific power and nothing else, and it is the kind capabilities are built for.

Where the stages are separate, even that happens twice. Alice tells Bob a path, and then someone edits the ACL. She sends him a URL, and then an authorization server issues him a token. The name and the permission travel separately and something has to recombine them, which is Property A failing at delegation time.

The mechanics differ sharply. Under central policy:

```text
Alice grants Bob access to X
        ↓
record an authorization fact in the store
        ↓
Bob's next request is evaluated against the new fact
```

Under capabilities:

```text
Alice ─── cap(X) ───► Bob
```

That is the whole operation. No store, no round trip, nobody else informed.

Attenuation then chains:

```text
Alice   read + write, all of repo
    ↓
Bob     read only
    ↓
Agent   read only, subdirectory Y, expires in 10 minutes
```

Each step hands on strictly less. Nobody consults a policy engine, and nobody can hand on more than they hold — a structural guarantee rather than a rule someone enforces.

### Service chaining

The three kinds of delegation stay abstract until a request crosses more than one service, so here is the case that does the damage.

Alice invokes Bob's backup service, passing a reference to the service that will supply the data. Bob implements his backup using Carol's copy service, which takes an input reference and an output reference.

Under NBAC, whose credentials does Bob present to Carol?

**His own.** Then Alice can name a service Carol may use and Alice may not, and the result comes back to Alice. Alice has mounted a confused deputy attack on Carol.

**Alice's.** Then Bob can take any action at Carol's service that Alice is permitted, whether or not Alice wanted it. Provider chaining — passing both sets of attributes — is worse than either, because it grants the union.

Karp's summary is that "in many cases, neither nor both is correct." A Navy evaluation of exactly this architecture resolved it two ways: declare the middle service fully trusted, or reduce it to a router that only forwards user-signed requests. Both define the problem away, and both break down the moment a partner organization is involved.

Under ZBAC there is no question of credentials. Alice delegates the input capability to Bob. Bob delegates it onward to Carol along with the output capability. Carol ends with exactly what the job needs, and it can be revoked when the job completes.

AI agents calling tools that call other agents are this problem with different nouns.

### The control you think you have

The standard objection to all of this is that easy delegation means losing control. Karp's answer is worth quoting because it is an empirical claim, not a philosophical one:

> The fact is that any control that you might think you had is an illusion. People will find workarounds, and those workarounds usually violate the assumptions behind your security architecture, resulting in worse security.

Make delegation hard and people share credentials. You blocked the transfer of a little authority and got the transfer of all of it, with the audit trail destroyed on the way out.

## The three objections

Saltzer and Schroeder saw the problem in 1975 and argued against capabilities — gently, and at the end of a section, but unmistakably. [The Protection of Information in Computer Systems][protection-information-computer-systems] raises three:

1. **Revocation.** You cannot un-give a reference.
2. **Propagation control.** Alice can pass it to anyone, and you cannot see or stop it.
3. **Review and audit.** You cannot answer "who holds authority over X?" by inspecting X.

Their conclusion is one of the most consequential recommendations in the field:

> The most effective way of preserving some of the useful properties of capabilities is to limit their free copyability to the bottom most implementation layer of a computer system… The authorizations implemented by the capability system are then systematically maintained as an image of some higher level authorization description, usually some kind of an access control list system.

Capabilities as a fast bottom layer, governed by an ACL system above. That design won completely. Unix, Windows, POSIX — file descriptors underneath, mode bits and ACLs on top. The entire identity-management industry is downstream of this paragraph.

Here is what the four-model table does to it. Objections one and two are **true of Model 3 and false of Model 4**. Propagation is uncontrollable exactly when Property F is missing; revocation is impossible exactly when Property E is missing. The objections survive fifty years of rebuttal because the key metaphor is the one everyone reasons with, and in the key metaphor they are correct.

### Revocation needs composability

The standard answer is Redell's indirection: interpose a forwarder you can sever. It is described in Saltzer and Schroeder's own paper, and it is the seed of what later became the [membrane pattern](/programming/authority-enforcement.html#membranes-subtraction-plus-mediation).

The reason it works in Model 4 and not in Model 3 is Property E. A forwarder has to be a resource that is also a subject. Where resources and subjects are separate type categories — where you have doors on one side and keys on the other — there is nowhere to put one.

### Accountability is the one ACLs lose

The third objection deserves more care, because the ACL's answer to it is weaker than it looks.

Alice wants Bob to watch a document in a SharePoint area. Under an ACL she asks Carol, the owner, to add Bob. Now consider what got recorded. The audit log says *Carol* created Bob's access. Nothing anywhere says Alice asked for it.

Then Alice wants it undone. Should Carol honor the request? There is no metadata naming Alice as the delegator, and even if there were, Dave might have granted Bob the same access for his own reasons. Remove it and Dave's work breaks.

Under ZBAC the delegation chain carries responsibility. It is the record that says Alice is answerable for Bob's access, it is the metadata that decides whether Alice may revoke, and revoking one authorization disturbs no other. This is Karp's sixth aspect of sharing, and it is the physical-world property we take entirely for granted:

> If Marc finds a new scratch on his car, he knows to ask me to pay for the repair. It's up to me to collect from my neighbor.

So capabilities do not lose accountability. They lose *global* review, which is a different thing. [Part 3](/programming/carriers.html#local-authority-versus-global-knowledge) weighs that trade from the administrator's side.

### The patches converge

Each side's fix for its own weakness imports the other side's core mechanism.

![image](/assets/authorization/acl-vs-ocaps.png)

**Capabilities adding revocation.** Introduce indirection: the token no longer grants access directly, it points at something that can be invalidated. But that something lives in a table mapping tokens to validity, and a table is a registry. You have rebuilt the ACL's central lookup with an extra hop. Expiry is the same move — you need a clock authority and a check on use.

**Capabilities adding global audit.** Answering "who holds what?" across a whole system requires tracking holders. That is a list of principals and their permissions.

**Capabilities adding policy-based issuance.** "Only managers get this capability" requires an identity system that knows who is a manager.

**ACLs adding confused-deputy protection.** Label the data, make every endorsement explicit, propagate the original caller's identity into the request context so the deputy can say on whose behalf it acts. The check now has enough information to be right.

### The convergence is not symmetric

The three capability-side patches import machinery: a registry, a list, an identity system. Each works whether or not the capability holder cooperates. The ACL-side patch imports a discipline. It works only if the deputy uses it.

That gap has a clean statement. ACL-plus-context makes the correct answer **expressible** — AWS's `sts:ExternalId` and `aws:SourceArn`, propagated caller identity, request-context claims all exist so a deputy *can* be right. It still has to ask. Object capabilities make the incorrect answer **unrepresentable**. Lacking authority means lacking a name, so there is no wrong question available.

The difference shows up precisely when the deputy is careless, and Hardy's compiler was careless rather than malicious. Nobody attacked it. Someone wrote it without considering the question. ACL-plus-context is exactly as reliable as the deputy's diligence, and diligence does not survive scale.

The capability claim needs its own limit, though, and Miller is explicit about it. A program holding two references can still use the wrong one. Unifying designation and authority removes *ambient* authority, not *excess* authority. It does not make the deputy careful; it shrinks the set of things carelessness can reach. Midori hit this directly: components accumulated "big bags" of capabilities because threading them individually was tedious, which is least authority losing to ergonomics rather than to theory.

That is a real finding about program internals, and it should not be generalized to users. At the user level the ergonomics have been solved and demonstrated. CapDesk turned acts of designation into acts of authorization — drag a file's icon onto an editor and the system starts the editor holding exactly that file. Polaris did it for Windows XP applications. Karp's team hid it so thoroughly in a file-sharing tool that a user asked them how to turn security on.

Which also explains what the systems that shipped this actually did. Capsicum, `openat` everywhere, WASI preopens, seccomp, SPIFFE's short-lived scoped SVIDs, macaroon caveats — none of them improve how a resource is designated. All of them reduce what the process holds. That is the attenuation chain arriving as fifteen years of engineering practice rather than as a diagram.

### Complete over the intended state, not the reachable state

A relationship store like [Zanzibar][zanzibar-google-s-consistent] answers the review question directly, and its tuple graph is a complete picture of policy. But policy binds only where the code consults the decision point. The service still holds ambient credentials to the database. A code path that opens a connection directly, a deserialization bug, a compromised dependency — none of those appear in the graph, and none are stopped by it. The audit is complete over the state you **intended**, not the state a compromised process can **reach**.

Object capabilities invert this exactly. There is no global view. But what you can see is reachability itself, and reachability is the thing that constrains a compromised component.

So capability auditability is not zero. It is local rather than global, and "only connectivity begets connectivity" is the load-bearing claim. A reference arrives in exactly four ways — initial conditions, creation, endowment, or introduction — so acquire is a closed list. Midori made the first of those an artifact you can read — a manifest, consulted at load time. That bounds how the graph can evolve, which makes a component's authority analyzable from its boundary.

A Wasm component's import list is the concrete version. It enumerates, statically and exhaustively, everything the component can reach — exhaustive by construction rather than by policy discipline. As audit surfaces go, that is a good one, arguably better than a tuple query.

It answers a different question, though. "What can this component do?" rather than "who can touch this resource?" Auditors want the second.

## Where the property can be bought

Everything above reduces to Property F, and Property F has a precondition that nobody states plainly.

> **To pass a capability only to someone you can already reach, something must be able to deny communication.**

On the grid, that is the loop. The arrow from reach back to acquire constrains anything only if reach can be refused, and reach can be refused only where names are local — where the name is the route. Refusing reach is the enforcer's job from [Part 2](/programming/authority-enforcement.html#non-bypassability-is-a-property-of-reach). Capabilities do not replace that enforcer. They depend on it.

That is not a design preference. It is an infrastructure requirement, and it explains every data point in this article at once:

```text
seL4                 the kernel mediates all IPC              Model 4
a language heap      references are the only way to reach     Model 4
Cap'n Proto vats     the overlay controls who can address whom Model 4
Cloudflare workerd   the runtime mediates every binding       Model 4

Unix file descriptors passed over ACL-controlled sockets      nearly
chroot                names removed, authority still ambient  not a capability system
physical keys         the world is a universal channel        Model 3
the open internet     IP is a universal channel               Model 3
```

**Every object-capability system that has ever worked is inside something that mediates communication.** A kernel, a language runtime, a VM boundary, an RPC overlay. That is not an implementation accident. It is Property F being purchasable only where connectivity is already controlled.

Which settles the question of capabilities on the internet, and the answer is not the one the maximalists give, nor the one the skeptics give.

The internet is *covered* in capabilities. Pre-signed S3 URLs, "anyone with this link can edit", GitHub fine-grained tokens, SPIFFE SVIDs, macaroons, biscuits. A Bitcoin private key is a bearer capability to spend a UTXO, works globally, and requires no relationship with anyone. The share link may be the most successful sharing mechanism ever deployed, it crosses every organizational boundary there is, and it is a capability.

Every one of them fails F. Most are Model 3 outright: the token travels apart from the URL it is for. The rest — share links, pre-signed URLs — sit in the bottom-left corner of the table above, with name and authority joined, and still cannot stop the name from travelling. Either way, the confinement myth comes true, because it was always a claim about F.

The obstacle is not that you fail to own both endpoints — HTTP and TLS do not require that either. It is that the internet's product *is* universal connectivity. Any host may address any other host, so nothing can deny communication, so F is unavailable in principle rather than in practice. You can approximate it with unguessable designators and confidentiality — Waterken did exactly this, with object capabilities as HTTPS URLs — but that is F-by-obscurity rather than F-by-construction. Anyone who learns the string may use it, and nothing prevents the holder from publishing it.

So: use Model 4 inside your boundaries, expect Model 3 across them, and know which one you are in. Where you control the substrate — a kernel, a runtime, a sandbox, an RPC fabric you designed — the property is nearly free and you should take it. Where you do not, macaroons and their relatives are Model 3 done about as well as Model 3 can be done: attenuable without a round trip, caveats travelling with the artifact, verifiable by a server that has never heard of you.

A service mesh shows what "an RPC fabric you designed" takes. Its sidecar already spans reach, authenticate and decide, but the workload still calls services by DNS name, and the sidecar decides by the pod's identity. To reach Model 4, the workload holds references its sidecar handed it, over Cap'n Proto or as opaque handles only that sidecar resolves, and no route bypasses the sidecar. workerd is built this way: a Worker reaches other services only through the bindings it was given.

The gap in between is a missing standard rather than a law of nature, and Karp has been asking for it since 2009:

> There is no standard for chained, attenuated delegation, which is an opportunity for an IEEE standards group. […] We must start on these standards before the IoT world becomes embedded in our lives. If we don't, we'll end up with walled gardens, an AOL of Things.

## Conclusion: one argument in four parts

The four articles were one argument. Authority has to be *represented* somewhere, and the choice between a list at the resource and a reference in the subject's hand decides which questions stay cheap. That is [Part 1](/programming/authorization-models.html). A representation of either kind is inert until something *enforces* it: a reference monitor on every stage, working by absence or by judgment. That is [Part 2](/programming/authority-enforcement.html). A decision can *travel* with the request, and every copy is a debt that someone must be able to call back. That is [Part 3](/programming/carriers.html).

This article took the strong version of the third step, designation and authority as one thing, and found a precondition: a substrate that can deny communication. That brings the argument back to Part 2, because denying communication is a reference monitor's job on reach. Capabilities do not replace enforcement. They are what enforcement makes possible.

## References

1. [Capability Myths Demolished][capability-myths-demolished] — Miller, Yee, Shapiro; the four models and the six properties
2. [Robust Composition][robust-composition] — Miller's thesis; ambient versus excess authority, and "only connectivity begets connectivity"
3. [From ABAC to ZBAC: The Evolution of Access Control Models][from-abac-zbac-evolution] — Karp, Haury, Davis; service chaining, and why a credential sent alongside a request carries everything its holder has
4. [Access Control for IoT: A Position Paper][access-control-iot-position] — Karp; the six aspects of sharing, and why delegation control is an illusion
5. [The Confused Deputy][confused-deputy] — Hardy, 1988
6. [The Protection of Information in Computer Systems][protection-information-computer-systems] — Saltzer and Schroeder; the three objections and the recommendation that shaped every mainstream OS
7. [Macaroons: Cookies with Contextual Caveats][macaroons-cookies-with-contextual] — attenuable bearer capabilities
8. [Objects as Secure Capabilities][objects-as-secure-capabilities] — Duffy on Midori; the capability oracle at `main`, no mutable statics, and where it fell short
9. [Capsicum: Practical Capabilities for UNIX][capsicum-practical-capabilities-unix] — ambient authority removed from a real Unix
10. [E and CapDesk: POLA for the Distributed Desktop][e-capdesk-pola-distributed] — Stiegler and Miller; designation as authorization in a user interface
11. [Joe-E: A Security-Oriented Subset of Java][joe-e-security-oriented] — Mettler, Wagner, Close; object references as capabilities, enforced by a verifier
12. [Waterken][waterken] — object capabilities as HTTPS URLs
13. [Zanzibar: Google's Consistent, Global Authorization System][zanzibar-google-s-consistent] — relationship-based authorization and reverse indexability

[access-control-iot-position]: https://alanhkarp.com/publications/Access-Control-for-IoT.pdf "Access Control for IoT: A Position Paper"
[capability-myths-demolished]: https://cgi.cse.unsw.edu.au/~cs9242/20/papers/Miller_YS_03.pdf "Capability Myths Demolished"
[capsicum-practical-capabilities-unix]: https://www.usenix.org/conference/usenixsecurity10/capsicum-practical-capabilities-unix "Capsicum: Practical Capabilities for UNIX"
[confused-deputy]: https://www.cs.utexas.edu/~witchel/S25-380L/papers/hardy88confused.pdf "The Confused Deputy"
[e-capdesk-pola-distributed]: https://web.archive.org/web/2020/http://www.combex.com/tech/edesk.html "E and CapDesk: POLA for the Distributed Desktop"
[from-abac-zbac-evolution]: https://shiftleft.com/mirrors/www.hpl.hp.com/techreports/2009/HPL-2009-30.pdf "From ABAC to ZBAC: The Evolution of Access Control Models"
[joe-e-security-oriented]: https://www.cs.berkeley.edu/~daw/papers/joe-e-ndss10.pdf "Joe-E: A Security-Oriented Subset of Java"
[macaroons-cookies-with-contextual]: https://static.googleusercontent.com/media/research.google.com/en/us/pubs/archive/41892.pdf "Macaroons: Cookies with Contextual Caveats"
[objects-as-secure-capabilities]: https://joeduffyblog.com/2015/11/10/objects-as-secure-capabilities/ "Objects as Secure Capabilities"
[protection-information-computer-systems]: https://www.cs.virginia.edu/~evans/cs551/saltzer/ "The Protection of Information in Computer Systems"
[robust-composition]: http://www.erights.org/talks/thesis/markm-thesis.pdf "Robust Composition"
[waterken]: http://waterken.sourceforge.net/ "Waterken"
[zanzibar-google-s-consistent]: https://research.google/pubs/pub48190/ "Zanzibar: Google's Consistent, Global Authorization System"
