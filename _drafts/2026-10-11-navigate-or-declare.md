---
title:  "Navigate or declare"
series: "Design Tradeoffs"
category: programming
---

<!-- OUTLINE. Headings and notes only; prose to come. -->

Every system that holds things has to answer one question: how does a caller find the thing it wants? It can walk the system's structure, one step at a time. Or it can say what it wants and let the system find the way. Charles Bachman called the first style *the programmer as navigator*. Edgar Codd built the relational model to get rid of it. Networks, filesystems and memory managers have had the same argument, mostly without noticing that databases already had it.

The answer is a tradeoff, not progress. Exposing structure makes a system fast, simple and predictable. Hiding it lets the system change underneath its callers, but someone has to do the finding: a resolver, an optimizer, a router. The indirection never disappears. You only choose who carries it.

- [Two questions about every name](#two-questions-about-every-name)
- [Bachman and Codd](#bachman-and-codd)
- [The same split elsewhere](#the-same-split-elsewhere)
- [Structure pays: the swing back](#structure-pays-the-swing-back)
- [What the name binds to](#what-the-name-binds-to)
- [Which side each field chose](#which-side-each-field-chose)
- [References](#references)

## Two questions about every name

- **How does the caller reach the object?** Navigate: the caller follows the structure. Declare: the caller names the object, and the system finds the way.
- **What is the name bound to?** A location, a thing whose content changes, or one exact value.
- Frame both with Saltzer: an address is the name of whatever an object is bound to. Link to [Naming and binding](/programming/naming-and-binding.html).
- Saltzer's network paper brought the binding concept over from operating systems, where he had worked it out in *Naming and Binding of Objects* (1978). This article follows the idea back out of networking.

## Bachman and Codd

- Bachman, Integrated Data Store and CODASYL. His 1973 Turing lecture, *The Programmer as Navigator*: a program walks from record to record along owner–member sets.
- Codd, 1970, section 1.2: the three kinds of data dependence programs should be free of. **Ordering**, **indexing**, **access path**. The goal: change how data is stored without changing what programs mean.
- The 1974 "Great Debate" between the two, at the ACM SIGFIDET workshop in Ann Arbor (SIGFIDET became SIGMOD a year later).
- What Codd actually won: independence *at the query interface*. The database still navigates inside: B-trees, hash indexes, join orders. Navigation didn't vanish. It moved behind the interface, into the optimizer.

## The same split elsewhere

| Domain | Navigate (caller follows the structure) | Declare (system finds the way) |
| --- | --- | --- |
| Email | UUCP bang paths: `host1!host2!user` | `user@domain`, resolved through DNS MX records |
| Telephone | Old phone numbers encoded the exchange | Number portability: a database lookup on every call |
| Web | URL: host plus path | DOIs and the Handle System; persistent IDs exist because links rot |
| Web APIs | REST links you follow, hop by hop | GraphQL: describe the shape you want |
| Filesystems | Pathnames, one directory at a time | BeOS BFS queries, Spotlight, WinFS (cancelled in 2006) |
| Filesystems | Symlinks: one name bound to another, resolved late | NFS file handles, `open_by_handle_at`: they survive a rename |
| Databases | IMS, CODASYL | Relational, SQL |
| Graph DBs | Gremlin traversals | Cypher patterns |
| ORMs | `order.customer.address`, and the N+1 query problem | One join, planned by the database |
| Memory | Raw pointers | Classic Mac OS Handles, ECS entity IDs, virtual memory |

One short subsection per domain, each with its strongest example:

### Networks: from bang paths to MX records

- A bang path is a route the sender spells out. `user@domain` names the destination, and DNS finds the way.
- IP itself isn't navigational: routers pick the path. Source routing was the navigational option, and it was dropped.
- Link to [Naming and binding](/programming/naming-and-binding.html#saltzers-own-examples): ARPANET's "the load balancer was a human" is the cost of naming the wrong level.

### Filesystems: pathnames and handles

- A pathname is navigation: a sequence of lookups, one directory at a time. A file descriptor is the result, resolved once. Link to [Everything is a file, §2](/programming/everything-is-a-file.html#2-resolve-once-use-by-handle).
- The declarative filesystem keeps being tried: BeOS BFS with indexed attributes and live queries, WinFS, Spotlight. Seltzer and Murphy, *Hierarchical File Systems are Dead* (HotOS 2009).
- Search got bolted on beside the hierarchy instead of replacing it. Why? Humans browse; programs need stable paths.
- Link to *The Shapes of I/O* on query as an interface. <!-- TODO: link once published -->

### Memory: pointers and handles

- A raw pointer is a location. If the object moves, every copy of the pointer breaks.
- Classic Mac OS Handles: a pointer to a pointer, so the Memory Manager could move blocks to compact the heap. Codd's data independence, for RAM.
- ECS entity IDs and generational indices: the same move in game engines.
- Virtual memory is the general case: the page table is the binding.

### APIs and ORMs

- REST hypermedia: follow links. GraphQL: declare the shape.
- ORMs put a navigational interface over a declarative engine. `order.customer.address` is Bachman's navigation, and the N+1 query problem is what it costs.

## Structure pays: the swing back

The evidence that this is a tradeoff: each field moved toward declaration, then partly back.

- **DynamoDB single-table design.** AWS's own advice: "you shouldn't start designing your schema for DynamoDB until you know the questions it will need to answer", and keep "as few tables as possible". Bachman's approach, back for scale.
- **Segment routing (SRv6) and SCION.** The path is written into the packet. SCION does it on purpose, so the sender can choose and check its path. Link to [Future internets](/programming/future-internets.html).
- **SQL index hints.** An escape hatch back to navigation when the optimizer picks a bad plan.
- **NDN's hierarchical names.** Routers keep tables small only because names group by prefix.
- **DHTs.** Keys are flat hashes, but Kademlia puts a distance metric (XOR) on the key space so lookups can be routed.
- **IP addresses themselves.** Prefixes encode topology so routers can aggregate. Ethernet's flat MACs can't be aggregated, which is why L2 networks flood and don't scale.
- **Day's position, stated carefully.** RINA keeps addresses location-dependent inside each layer, where routing needs structure. It hides them above, where applications ask for names. Structure where it pays, independence where it doesn't. Link to [The Internet as DIFs](/programming/internet-as-difs.html#saltzers-levels-inside-one-dif).

## What the name binds to

The second question. Joe Armstrong asked for three webs:

| Armstrong's web | The name binds to | Can the binding change? |
| --- | --- | --- |
| names (`http://host/path`) | a location | yes, and it can break |
| UUIDs | one thing whose content changes over time | the content changes, the name doesn't |
| hashes (`sha1://…`) | one exact value | never |

- A hash name is the far end of location independence. It says nothing about where, so any copy will do. The client checks the data itself, so it doesn't need to trust the server.
- Package managers use all three in one file:

```
package.json     "left-pad": "^1.3.0"           a name: mutable, resolved at install time
lockfile         resolved: https://…/1.3.0.tgz  a location
                 integrity: sha512-…            a hash: checked against the content
```

- A mutable name over an immutable one, every time: Docker tag and digest, Git ref and commit, IPNS name and IPFS CID, magnet link and BitTorrent infohash.
- Variations: Nix store paths hash the build's *inputs*, not its output (content-addressed derivations are still experimental; fetchers have always been content-addressed). Unison names are labels on hashes of code. Venti is Plan 9's content-addressed block store. Subresource Integrity puts a location and a hash in one reference.
- **The costs.**
  - Content can't change in place, so every system above adds a mutable name on top. Identity Part 6 says it: "Self-certification does not remove the binding problem. It moves it to the layer above." Link to [Binding without a CA](/programming/binding-without-a-ca.html#self-certifying-names).
  - Deletion is hard.
  - You're stuck with your hash function. Git has supported SHA-256 repositories since 2020, but interoperation with SHA-1 repositories is still unfinished. <!-- TODO: recheck Git 3.0 status before publishing -->
- Link to [The Unbeknownst Pervasiveness of Immutability](/programming/unbeknownst-pervasiveness-of-immutability.html) rather than repeat its examples.
- NDN sits on both axes: names are hierarchical (declare, with structure kept for routing), and the producer's signature binds name to content.

## Which side each field chose

| Field | Structure hidden at | Structure exposed at | Why |
| --- | --- | --- | --- |
| Databases | the query interface | NoSQL key design | the optimizer can be trusted with one machine's data; at scale, latency must be predictable |
| The Internet | service names (DNS) | the forwarding interface (prefixes) | routers need to aggregate |
| Filesystems | handles, for programs | pathnames, for people | people browse |
| Content-addressed systems | location, entirely | the mutable name layered on top | content that never changes can't model things that do |

- Close: the indirection never disappears. You choose who carries it: the caller, a resolver, or a layer above.
- Tie to [Worse is Better](/programming/worse-is-better-examples.html): exposing structure is the simple-implementation choice. Codd took the other side and won at the query interface. IP took the simple side and won at the forwarding interface.

## References

- C. Bachman, *The Programmer as Navigator*, Turing Award lecture, CACM, 1973.
- E. F. Codd, *A Relational Model of Data for Large Shared Data Banks*, CACM, 1970.
- J. Saltzer, *Naming and Binding of Objects*, in *Operating Systems: An Advanced Course*, LNCS 60, Springer, 1978.
- J. Saltzer, [RFC 1498, *On the Naming and Binding of Network Destinations*](https://www.rfc-editor.org/info/rfc1498/), 1993 (first published 1982).
- M. Seltzer, N. Murphy, *Hierarchical File Systems are Dead*, HotOS XII, 2009.
- J. Armstrong, [The web of names, hashes and UUIDs](https://joearms.github.io/published/2015-03-12-The_web_of_names.html), 2015.
- S. Quinlan, S. Dorward, *Venti: a new approach to archival storage*, FAST, 2002.
