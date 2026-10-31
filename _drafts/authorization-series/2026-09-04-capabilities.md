---
title:  "Capabilities: authority you hold, not authority you are"
series: "Authorization, Part 4"
series_url: "/programming/authorization-series-intro.html"
category: programming
date:   2026-09-04
---

> This is Part 4 of a four-part [series on authorization](/programming/authorization-series-intro.html).
>
> - **[Part 1: Authorization is a database problem](/programming/authorization-models.html)** — what every system computes, and who may change it.
> - **[Part 2: How authority is enforced](/programming/authority-enforcement.html)** — what makes any of it binding.
> - **[Part 3: Carriers](/programming/carriers.html)** — decisions that travel with the request.
> - **Part 4: Capabilities** — authority you hold, not authority you are.

- [Squaring the matrix](#squaring-the-matrix)
- [Keys and object capabilities](#keys-and-object-capabilities)
  - [Two bindings collapse the stages](#two-bindings-collapse-the-stages)
  - [Where the authority lives](#where-the-authority-lives)
- [Designation is authority](#designation-is-authority)
  - [The confused deputy is structural](#the-confused-deputy-is-structural)
  - [Cannot, not do not](#cannot-not-do-not)
  - [Service chaining](#service-chaining)
  - [Expressible versus unrepresentable](#expressible-versus-unrepresentable)
- [The three objections](#the-three-objections)
  - [Revocation needs composability](#revocation-needs-composability)
  - [Propagation runs only along reach](#propagation-runs-only-along-reach)
  - [Review is the real trade](#review-is-the-real-trade)
- [Where the property can be bought](#where-the-property-can-be-bought)
- [Conclusion: one argument in four parts](#conclusion-one-argument-in-four-parts)
- [References](#references)

The [series intro](/programming/authorization-series-intro.html#from-a-chain-to-a-grid) follows a request through four stages: designate, reach, authenticate and decide. The industry has spent twenty years on the last two, and they are genuinely good now. [Part 2](/programming/authority-enforcement.html#which-stage-do-you-cut) treated designate and reach as stages an enforcer can cut. [Part 3](/programming/carriers.html#from-one-stage-to-several) ended on a line from bearer tokens to object capabilities. This article is about its last two steps: artifacts that carry several stages at once. That is where the only structural difference between capabilities and everything else lives.

It is also about a word that has been ruined by overuse. "Capability" names several distinct things. The arguments people have about capabilities are usually arguments about different ones, and most of the famous objections are true of one and false of another.

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

ACLs and capability lists are the special case where the entity set splits into two disjoint halves, so the bottom-left block is empty and you may as well draw the matrix rectangular. Nothing is lost by squaring it, and three things become expressible that Part 1's models could not reach.

**Mediation.** Bob is a row and a column. `Alice → Bob → X` is two cells, not one, and the difference between them is the entire value of a proxy.

**Communication as an access decision.** A cell `(Alice, Bob)` is a subject reaching a subject. Whether Alice may *talk to* Bob is now the same kind of question as whether Alice may read a file. In a rectangular matrix there is nowhere to ask it, which is why every model in Part 1 treats connectivity as someone else's problem: the network's, the linker's, the runtime's.

**A mutation rule written in the matrix's own terms.** Every model in Part 1 needs an outside notion of who may edit: an owner, an administrator, a lattice, a policy document. A square matrix can state its own rule. *Alice may write into Bob's row only if her own row already reaches both Bob and the thing she is granting.* Authority moves only along edges that already exist.

That last one is this whole article compressed into a sentence. It is also why the entity set has to be allowed to grow: attenuation means minting a new proxy, which is a new row and a new column appearing at runtime.

## Keys and object capabilities

Miller, Yee and Shapiro's [Capability Myths Demolished][capability-myths-demolished] is the paper that sorts the word out. It defines four models. Next to the ACL baseline, two of them matter here:

- **Keys** (the paper's Model 3) are unforgeable, copyable tokens. You can hand one to anyone you like. This is what the key metaphor describes, and what most people picture when they hear "capability."
- **Object capabilities** (Model 4) are unforgeable references. Naming an object and holding authority over it are one thing, and you can pass one only to someone you can already reach. This is what every major capability system actually implements.

The paper separates the models with six tests. Four of them carry the rest of this article, and each is a claim about how the grid's stages relate. One stage needs a name first. *Acquire* is the written half of designate: how the subject came to hold a name at all. New names arrive only over channels the subject can already reach, so one arrow runs from reach back to acquire. Miller's phrase for it is "only connectivity begets connectivity," and the rest of this article calls it the loop.

| | The test | On the grid | ACLs | keys | ocaps |
|---|---|---|---|---|---|
| **A** | Does designating a resource always convey its authority? | one artifact carries designate and decide | no | no | yes |
| **D** | Must subjects select which authority to use? | decide reads what the invocation carries, not who the subject is | no | yes | yes |
| **E** | Are resources also subjects? | whatever you reach can itself acquire and pass on names | unspecified | no | yes |
| **F** | Must X already reach Y to pass Y an authority? | acquire runs only along reach: the loop | unspecified | no | yes |

**Property A: no designation without authority.** Saying *which* object and saying *that you may use it* are the same act. Keys fail this, and the failure is easy to miss: you can hold a key without knowing which door it opens, and you can point at a door without holding its key. Designator and authority travel separately, and something has to recombine them.

**Property D: no ambient authority.** You must select the authority you exercise. Unix fails this: `open()` takes a path and no credential, and the call simply succeeds or fails. Miller's image for ambient authority is a world of doors and no keys, where a door opens if it deems you worthy.

**Property E: composability.** Resources are also subjects. Without it you cannot build a revocable forwarder, because a forwarder is a resource that is also a subject.

**Property F: access-controlled delegation channels.** To hand Bob a capability you must already hold a capability to Bob. This is the loop stated as a test, and it is the property everything else in this article eventually reduces to.

E and F are the [square matrix](#squaring-the-matrix), arriving as tests. **E is the squaring itself**: one entity set on both axes, so a thing can be a row and a column at once. **F is the mutation rule** the square matrix can state about itself.

Two things fall out immediately. Confinement fails for keys because F fails: if you can hand a key to anyone you can talk to, and you can talk to anyone, authority leaks wherever it likes. Revocation fails for keys because E fails: no composability, no forwarder to sever. So the two most famous objections to capabilities are *true statements about the key model*, and the key model is the one everyone has in their head.

[Part 3](/programming/carriers.html#policy-and-mechanism) drew it. The third panel of its door picture, the capability token, is a key ring. A key ring gets D right, because you must select a key, and gets A, E and F wrong. So the key metaphor teaches the correct lesson about ambient authority and the wrong lesson about confinement and revocation. It is a good picture of why capabilities are fast and offline, and a bad picture of what makes them safe.

Read on the grid, a capability is not a kind of token. It is what you get when one artifact designates, reaches and decides, and can be acquired only through another. Object capabilities are the only model that insists on all of it.

### Two bindings collapse the stages

That collapse is not one thing. Two separate bindings produce it.

- **Name to route.** A *local* name, such as an FD index, a C-list slot or a heap pointer, means something only as an entry in a table the enforcer owns. The entry is the route, so designate and reach become one. A *global* name, such as a path, a URL or an IP address, can be uttered by anyone, and whether it gets anywhere is a separate question. What makes a name local is who resolves it, not what it looks like: an opaque string is local if only one enforcer's table resolves it and the holder can reach no other resolver.
- **Name to permission.** The rights sit in the table entry, or a secret or signature sits in the string. Either way, designate and decide become one.

The two are independent, so all four combinations exist:

![A two-by-two grid. Columns: global name, where reach is separate, and local name, where the name is the route. Rows: authority checked separately, and name bound to authority. Top left: ACLs and keys (pathname plus ACL, OAuth, SPKI), split by Property D. Top right: unforgeable references with an ambient decision (Java reference plus SecurityManager), which Joe-E removes. Bottom left: a bound name on an open channel (share link, presigned S3 URL, Waterken), where A holds and F fails. Bottom right: object capabilities (FD under Capsicum, WASI handle, CHERI), where A, D and F hold if no channel is global.](/assets/authorization/two-bindings.svg)

ACLs and keys share the top left, and object capabilities sit bottom right. The other two corners are the instructive ones. A share link joins name and authority, but the open internet delivers a global name wherever it goes. Java references cannot be forged, but stack inspection decides against the caller's principal, and [Joe-E][joe-e-security-oriented] is what removing that looks like.

The column decides acquire. A global name can be guessed, listed or leaked, so it can arrive from anywhere. A local name can arrive only through a channel already held, provided no channel is global. Property F needs the right-hand column, and it needs the column clean. A mutable static is a channel every object can reach. In [Duffy][objects-as-secure-capabilities]'s words, "mutable statics are really just a form of ambient authority." Midori banned them, and they are the second thing Joe-E removes from Java.

[Part 2](/programming/authority-enforcement.html#one-enforcer-several-stages) draws the same split from the enforcer's side, as separate enforcers against one enforcer that spans the stages. The two views agree because a local name is one that a single enforcer resolves, routes and checks.

### Where the authority lives

The two columns also answer where the authority lives. A global name with the authority inside it is a carrier from [Part 3](/programming/carriers.html): the Carried row of the grid, and the key model. A local name is an index into a per-subject table that one monitor owns: the Written row, and the object-capability model.

![Two panels. Keys: Alice copies a token to Bob, who copies it on to a contractor and a paste site; passing is copying bytes over any channel, revoking means reaching every copy, and Property F fails. Object capabilities: Alice and Bob each hold only an index, and passing fd 3 to Bob makes the enforcer write a new entry in Bob's table; it can refuse the pass, revoking deletes the entry, and Property F holds.](/assets/authorization/where-authority-lives.svg)

The placement predicts the properties. Put the authority in a carrier, and F fails and revocation turns into debt: the two famous failures of keys. Put it in a table the enforcer owns, and both come back. Because the enforcer writes the recipient's entry, it can refuse a pass, and seL4 can revoke along the derivation tree.

Three systems show where the line falls.

**Unix file descriptors** are nearly object capabilities. A pathname is plain data: it names a slot in a global namespace, anyone can utter one, and uttering it conveys nothing. The descriptor `open` returns is a handle in a small per-process table that earlier authorization decisions populated. You cannot guess one, and holding it is the whole of your permission to act. But the channel that carries a descriptor between processes is a Unix socket, reached by pathname and governed by an ACL. So confining descriptor propagation depends on the ACL system rather than on the capability system. F fails at the seam.

**SPKI certificates** are keys, although every one is bound to a public key. A key-bound token stops a stranger from using a stolen copy, but the holder can still pass the authority on, by handing over the token and signing for the recipient, or by acting as a proxy. Binding a carrier to a key does not move it across the line. SPKI matters more than it looks, because it is the shape most distributed "capability" systems take.

**Cap'n Proto** sits on both sides. Over a live connection, each side keeps a table of imported and exported references, and a reference on the wire is an index into the peer's table: an object capability, with the connection as the channel F needs. A reference that must outlive the connection, or reach a party you are not connected to, has to be written out as a string. Cap'n Proto calls that a SturdyRef, E calls its secret a Swiss number, and Waterken makes it an HTTPS URL. The string carries the authority, so it is a carrier, and the capability has dropped to a key.

> **A carried token is what a capability becomes when it has to leave the enforcer's table.**

## Designation is authority

Property A has a second name, from a completely different tradition. Alan Karp, who built E-speak at HP and spent fifteen years arguing about this, states the same thing as a claim about *requests*:

> The root cause of the problem is that the authentication presented with the request is necessarily independent of the request, which means the authentication necessarily represents all the permissions assigned to me.

That is Property A read from the wire rather than from the object graph. A credential that arrives alongside a request, rather than inside it, cannot be specific to the request. It therefore carries everything its holder has. This is why Karp puts identity, roles and attributes in one family, NBAC, from [Part 3](/programming/carriers.html#where-and-when). All three answer "who is asking," and the answer is independent of what is being asked. ZBAC presents an authorization with the request instead.

Miller describes an object graph; Karp describes a protocol. They are making the same claim, and this section uses both.

### The confused deputy is structural

Norm Hardy's [The Confused Deputy][confused-deputy] is the canonical failure. A compiler holds write access to a billing file. A user invokes it and names the billing file as the destination for debugging output. The compiler overwrites the billing data, because it *can*, and because the request named a path rather than carrying a reference.

![Two panels. Left: the user passes the path /sys/BILL to the compiler, the kernel checks whether the compiler may write BILL, says yes, and BILL is overwritten. Right: Alice holds read on in.c, write on out.o and read on BILL; she passes the compiler one handle per argument, the compiler writes out.o through the handle it was given, and an attempt to pass write on BILL fails at the source.](/assets/authorization/confused-deputy.svg)

The usual reading is that the compiler was careless. Miller's reading is sharper:

> The problem is not caused by the compiler using access that it should not have. The problem is that it exercises its authority to write to BILL for the wrong purpose.

And the reason it cannot tell is Property D. If you cannot identify which authority you are using, you cannot associate a purpose with it. With keys you could label each one on receipt: *this one is for billing, that one came from the user*. But labelling is impossible when keys appear on the ring without your knowledge, which is what ambient authority is.

Karp's version, on the right, adds the cure. Alice passes one handle per argument. She holds only read on the billing file, so an attempt to pass write on it fails at the source. The attack does not get as far as the deputy.

An AI agent is Hardy's compiler with more inputs. Prompt injection is the same failure: the attacker supplies the designator, and the agent supplies the authority.

There is a nice piece of historical irony here: the web copy of Saltzer and Schroeder everyone links to was put online by Norm Hardy.

### Cannot, not do not

Karp is careful about a distinction that is easy to blur. He does not claim ACL systems *do not* support the kinds of sharing we need. He claims they *cannot*, and the argument is short enough to check.

The authentication accompanying a request is independent of the request. So the access decision allows the request if *any* of the requester's permissions matches it. So there is no place to attach a specific right to a specific argument.

His example is `cp File1 File2`. Get the arguments backwards and you destroy File1, and no ACL, role, attribute or relationship graph can save you, because the mechanism has nowhere to write down "this argument carries read and that one carries write." Pass open handles instead and the wrong order simply fails: the process tries to write to something it opened read-only.

The same structure explains malware. Every program you run authenticates as you, so every program you run holds everything you hold.

### Service chaining

The same bug appears whenever a request crosses more than one service. Alice invokes Bob's backup service, passing a reference to the source. Bob implements his backup using Carol's copy service, which takes an input and an output.

![Under NBAC, Bob can present his own credentials to Carol (a confused deputy: Alice gets back data she may not read), Alice's credentials (Bob may do anything at Carol's that Alice may), or both (the union, worse than either). Under ZBAC, Alice hands Bob read on the source, and Bob hands Carol that handle plus write on his backup store: exactly what the job needs, revocable when it completes.](/assets/authorization/service-chaining.svg)

Under NBAC, every answer to "whose credentials does Bob present?" is wrong. Karp's summary is that "in many cases, neither nor both is correct." A Navy evaluation of exactly this architecture resolved it two ways: declare the middle service fully trusted, or reduce it to a router that only forwards user-signed requests. Both define the problem away, and both break down the moment a partner organization is involved.

Under ZBAC there is no question of credentials. Bob passes on the handle Alice gave him, plus his own output handle, and Carol ends with exactly what the job needs.

AI agents calling tools that call other agents are this problem with different nouns.

### Expressible versus unrepresentable

ACLs can be patched against the confused deputy. Label the data, make every endorsement explicit, and propagate the original caller's identity into the request context so the deputy can say on whose behalf it acts. The check now has enough information to be right.

That patch makes the correct answer **expressible**. AWS's `sts:ExternalId` and `aws:SourceArn`, propagated caller identity and request-context claims all exist so a deputy *can* be right. It still has to ask. Object capabilities make the incorrect answer **unrepresentable**. Lacking authority means lacking a name. In Midori, a program without the capability "can't even attempt the operation," and the attempt was often caught at compile time.

The difference shows up precisely when the deputy is careless, and Hardy's compiler was careless rather than malicious. Nobody attacked it. Someone wrote it without considering the question. ACL-plus-context is exactly as reliable as the deputy's diligence, and diligence does not survive scale.

The capability claim needs its own limit, though, and Miller is explicit about it. A program holding two references can still use the wrong one. Unifying designation and authority removes *ambient* authority, not *excess* authority. It does not make the deputy careful; it shrinks the set of things carelessness can reach. [Midori][objects-as-secure-capabilities] hit this twice. Components accumulated "big bags" of capabilities because threading them individually was tedious. That is least authority losing to ergonomics rather than to theory. And a holder could downcast a `File` to the `CloudFile` behind it and "do things I didn't intend." A narrower type is not a narrower authority, so attenuation has to be a new wrapper object, not a cast.

It is a real finding about program internals, and it should not be generalized to users. At the user level the ergonomics have been solved and demonstrated. CapDesk turned acts of designation into acts of authorization: drag a file's icon onto an editor and the system starts the editor holding exactly that file. Polaris did it for Windows XP applications. Karp's team hid it so thoroughly in a file-sharing tool that a user asked them how to turn security on.

The systems that shipped capability ideas took the same lesson. Capsicum, `openat` everywhere, WASI preopens, seccomp, SPIFFE's short-lived scoped SVIDs and macaroon caveats do not improve how a resource is designated. All of them reduce what the process holds.

## The three objections

Saltzer and Schroeder saw the problem in 1975 and argued against capabilities: gently, and at the end of a section, but unmistakably. [The Protection of Information in Computer Systems][protection-information-computer-systems] raises three objections:

1. **Revocation.** You cannot un-give a reference.
2. **Propagation control.** Alice can pass it to anyone, and you cannot see or stop it.
3. **Review and audit.** You cannot answer "who holds authority over X?" by inspecting X.

Their conclusion is one of the most consequential recommendations in the field:

> The most effective way of preserving some of the useful properties of capabilities is to limit their free copyability to the bottom most implementation layer of a computer system… The authorizations implemented by the capability system are then systematically maintained as an image of some higher level authorization description, usually some kind of an access control list system.

Capabilities as a fast bottom layer, governed by an ACL system above. That design won completely. Unix, Windows, POSIX: file descriptors underneath, mode bits and ACLs on top. The entire identity-management industry is downstream of this paragraph.

The first two objections are the ones [keys fail](#keys-and-object-capabilities): revocation needs E, and propagation control needs F. They survive fifty years of rebuttal because the key metaphor is the one everyone reasons with, and in the key metaphor they are correct. The third is a real trade.

Each side can patch its weak spots. The ACL side's patch, caller context against the confused deputy, is [above](#expressible-versus-unrepresentable). The capability side's patches follow, one per objection. Only the revocation patch is specific to keys: a key system rebuilds the ACL's central table, and an object-capability system does not need to.

### Revocation needs composability

The standard answer is Redell's indirection: interpose a forwarder you can sever. It is described in Saltzer and Schroeder's own paper, and it is the seed of what later became the [membrane pattern](/programming/authority-enforcement.html#membranes-subtraction-plus-mediation).

It works for object capabilities and not for keys because of Property E. A forwarder has to be a resource that is also a subject. Where resources and subjects are separate type categories, with doors on one side and keys on the other, there is nowhere to put one. In Midori the forwarder is an ordinary object: "I can give you my own subclass of a Clock that delegates to the real one," and the subclass can refuse calls later.

So a key system patches revocation differently. The token no longer grants access directly; it points at something that can be invalidated. But that something lives in a table mapping tokens to validity, and a table is a registry. You have rebuilt the ACL's central lookup with an extra hop. Expiry is the same move: you need a clock authority and a check on use. A forwarder holds state too, but only its creator owns it, and nobody else has to consult it.

### Propagation runs only along reach

Property F answers the second objection directly: you can pass a capability only to someone you can already reach. Propagation is not uncontrolled. It is controlled by connectivity, in the same mechanism that controls access.

Within those channels, delegation is cheap. [Part 3](/programming/carriers.html#three-kinds-of-delegation) separated three kinds of delegation. Only the third, authority delegation, hands over one specific power and nothing else, and it is the kind capabilities are built for. Where the stages are separate, even that happens twice. Alice tells Bob a path, and then someone edits the ACL. She sends him a URL, and then an authorization server issues him a token. The name and the permission travel separately and something has to recombine them, which is Property A failing at delegation time.

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

That is the whole operation. No store, no round trip, nobody else informed. Attenuation then chains:

```text
Alice   read + write, all of repo
    ↓
Bob     read only
    ↓
Agent   read only, subdirectory Y, expires in 10 minutes
```

Each step hands on strictly less. Nobody consults a policy engine, and nobody can hand on more than they hold. That is a structural guarantee rather than a rule someone enforces.

The capability side's patch for propagation is policy-based issuance: "only managers get this capability." That requires an identity system that knows who is a manager.

The standard objection is that easy delegation means losing control. Karp's answer is worth quoting because it is an empirical claim, not a philosophical one:

> The fact is that any control that you might think you had is an illusion. People will find workarounds, and those workarounds usually violate the assumptions behind your security architecture, resulting in worse security.

Make delegation hard and people share credentials. You blocked the transfer of a little authority and got the transfer of all of it, with the audit trail destroyed on the way out.

### Review is the real trade

The third objection deserves more care, because the ACL's answer to it is weaker than it looks.

Alice wants Bob to watch a document in a SharePoint area. Under an ACL she asks Carol, the owner, to add Bob. Now consider what got recorded. The audit log says *Carol* created Bob's access. Nothing anywhere says Alice asked for it.

Then Alice wants it undone. Should Carol honor the request? There is no metadata naming Alice as the delegator, and even if there were, Dave might have granted Bob the same access for his own reasons. Remove it and Dave's work breaks.

Under ZBAC the delegation chain carries responsibility. It is the record that says Alice is answerable for Bob's access, it is the metadata that decides whether Alice may revoke, and revoking one authorization disturbs no other. This is Karp's sixth aspect of sharing, and it is the physical-world property we take entirely for granted:

> If Marc finds a new scratch on his car, he knows to ask me to pay for the repair. It's up to me to collect from my neighbor.

So capabilities do not lose accountability. They lose *global* review, which is a different thing. The capability side's patch for global review is to track holders, and a list of principals and their permissions is an ACL. [Part 3](/programming/carriers.html#local-authority-versus-global-knowledge) weighs that trade from the administrator's side.

The ACL's global review has a limit of its own. A relationship store like [Zanzibar][zanzibar-google-s-consistent] answers the review question directly, and its tuple graph is a complete picture of policy. But policy binds only where the code consults the decision point. The service still holds ambient credentials to the database. A code path that opens a connection directly, a deserialization bug or a compromised dependency appears nowhere in the graph, and the graph stops none of them. The audit is complete over the state you **intended**, not the state a compromised process can **reach**.

Object capabilities invert this exactly. There is no global view. But what you can see is reachability itself, and reachability is the thing that constrains a compromised component. A reference arrives in exactly four ways: initial conditions, creation, endowment or introduction. So acquire is a closed list. Midori made the first of those an artifact you can read, a [manifest][objects-as-secure-capabilities] consulted at load time. That bounds how the graph can evolve, which makes a component's authority analyzable from its boundary.

A Wasm component's import list is the concrete version. It enumerates, statically and exhaustively, everything the component can reach, exhaustive by construction rather than by policy discipline. As audit surfaces go, that is a good one, arguably better than a tuple query. It answers a different question, though: "what can this component do?" rather than "who can touch this resource?" Auditors want the second.

## Where the property can be bought

Everything above reduces to Property F, and Property F has a precondition that nobody states plainly.

> **To pass a capability only to someone you can already reach, something must be able to deny communication.**

On the grid, that is the loop. The arrow from reach back to acquire constrains anything only if reach can be refused, and reach can be refused only where names are local, where the name is the route. Refusing reach is the enforcer's job from [Part 2](/programming/authority-enforcement.html#non-bypassability-is-a-property-of-reach). Capabilities do not replace that enforcer. They depend on it.

That is not a design preference. It is an infrastructure requirement, and it explains every data point in this article at once:

| System | What controls communication | Result |
|---|---|---|
| seL4 | the kernel mediates all IPC | object capabilities |
| a language heap | references are the only way to reach | object capabilities |
| Cap'n Proto vats | the overlay controls who can address whom | object capabilities |
| Cloudflare workerd | the runtime mediates every binding | object capabilities |
| Unix file descriptors | passed over sockets, reached by path and guarded by ACLs | nearly |
| chroot | names removed, but authority still ambient | not a capability system |
| physical keys | nothing: the world is a universal channel | keys |
| the open internet | nothing: IP is a universal channel | keys |

**Every object-capability system that has ever worked is inside something that mediates communication.** A kernel, a language runtime, a VM boundary, an RPC overlay. That is not an implementation accident. It is Property F being purchasable only where connectivity is already controlled.

Which settles the question of capabilities on the internet, and the answer is not the one the maximalists give, nor the one the skeptics give.

The internet is *covered* in capabilities. Pre-signed S3 URLs, "anyone with this link can edit", GitHub fine-grained tokens, SPIFFE SVIDs, macaroons, biscuits. A Bitcoin private key is a bearer capability to spend a UTXO, works globally, and requires no relationship with anyone. The share link may be the most successful sharing mechanism ever deployed, it crosses every organizational boundary there is, and it is a capability.

Every one of them fails F. Most are keys outright: the token travels apart from the URL it is for. The rest, such as share links and pre-signed URLs, join name and authority and still cannot stop the name from travelling. Either way, the confinement myth comes true, because it was always a claim about F.

The obstacle is not that you fail to own both endpoints; HTTP and TLS do not require that either. It is that the internet's product *is* universal connectivity. Any host may address any other host, so nothing can deny communication, so F is unavailable in principle rather than in practice. Unguessable URLs, as in Waterken, approximate it, but that is F-by-obscurity rather than F-by-construction. Anyone who learns the string may use it, and nothing prevents the holder from publishing it.

So: use object capabilities inside your boundaries, expect keys across them, and know which one you are in. Where you control the substrate, such as a kernel, a runtime, a sandbox or an RPC fabric you designed, the property is nearly free and you should take it. Where you do not, macaroons and their relatives are keys done about as well as keys can be done: attenuable without a round trip, caveats travelling with the artifact, verifiable by a server that has never heard of you.

A service mesh shows what "an RPC fabric you designed" takes. Its sidecar already spans reach, authenticate and decide, but the workload still calls services by DNS name, and the sidecar decides by the pod's identity. To get object capabilities, the workload holds references its sidecar handed it, over Cap'n Proto or as opaque handles only that sidecar resolves, and no route bypasses the sidecar. workerd is built this way: a Worker reaches other services only through the bindings it was given.

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
8. [Objects as Secure Capabilities][objects-as-secure-capabilities] — Duffy on Midori; the capability oracle at `main`, mutable statics as ambient authority, revocation by wrapping, downcasting, and where it fell short
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
