---
title:  The Unbeknownst Pervasiveness of Immutability
category: programming
---


Do you think about immutability on a daily basis while coding? I certainly don't. Yet, you are very likely making use of it in one form or another: rust's let, git, lsm-based dbs, consensus append-only logs, frontend frameworks, etc. Immutability is literally everywhere, sometimes hiding behind synonyms like persistent (data-structures), copy-on-write, and content-based.

Unfortunately, immutability tends to be predominently associated with functional programming and those pesky "persistent data-structures" that have a bad rep in industry.

![image](/assets/unbeknownst-pervasiveness-of-immutability/persistent-datastructure.png)

The theoretically minded will keep challenging that bad rep on hackernews, pointing to some Rich Hickey talk touting the benefits of immutability in [Clojure and Datomic](https://www.infoq.com/interviews/hickey-datomic-functional/), to some John Hughes [article](https://www.cs.kent.ac.uk/people/staff/dat/miranda/whyfp90.pdf), or to a Joe Armstrong quote about the benefits of [immutability in Erlang](https://iamstarkov.com/why-immutability-matters/).

But the practically minded programmer who wants to get shit done, fast, will have no-doubt already prepared his [Chris Lattner quote](https://www.youtube.com/watch?v=8nyg_IXfnvs) as a response: "Functional programming, strictly defined, is dumb."

This debate is certainly interesting, but is missing the forest for the trees. Immutability is a much broader concept, which has pervaded modern day computer systems. The goal of this article is not to advocate for the unreasonable effectiveness of immutable data structures, but rather to open peoples' eyes to the unbeknownst pervasiveness of immutability as a concept, and to its multiple shapes and forms.


## Memory + CPU

| Category             | Mutable              | Immutable                             |
| -------------------- | -------------------- | ------------------------------------- |
| Data Structures      | Arrays, dictionaries | Persistent data structures            |
| Programming Language | Imperative (C, Java) | Functional (Haskell, Clojure, Unison) |

After learning basic data structures in University, programmers tend to get drawn into one of two worlds: functional/pure or performance/impure. The theoretically minded will sooner or later stumble upon Chris Okasaki's 1996 somewhat arcane thesis [Purely Functional Data Structure](https://en.wikipedia.org/wiki/Purely_functional_data_structure). Unfortunately, those kinds of data structures, despite being beautiful and helping prevent bugs, are not performant, as Chris Lattner [reminds us](https://www.youtube.com/watch?v=8nyg_IXfnvs). That is because they don't take into consideration how the underlying hardware works, and fail to make use of cache locality. The more performance oriented programmers will instead delve into the lock free data structures like rings buffers, timing wheels, etc. Interestingly however, there are data structures that fall in both camps! [Hash array mapped tries](https://en.wikipedia.org/wiki/Hash_array_mapped_trie) are an example of this, which have been implemented in Clojure and Scala.

More generally, not many people have the privilege of using functional languages at work. The world was taken by storm by OOP languages, which take the opposite viewpoint and use objects that are mutated in-place. Nonetheless, slowly but surely, imperative languages are [making a comeback](https://www.youtube.com/watch?v=vQPHtAxOZZw) in the form of languages such as golang, rust, and zig. And these languages, lo and behold, are filled with functional features! Go is the big laggard in this category, but even it introduced so-called "interior" functional iterators in [v1.23](https://www.gingerbill.org/article/2024/06/17/go-iterator-design/). Zig [has ADTs](https://ziglang.org/documentation/master/#Tagged-union), and Rust is extremely functional: its variables are [immutable by default](https://doc.rust-lang.org/book/ch03-01-variables-and-mutability.html), its traits are basically haskell [typeclasses](https://web.engr.oregonstate.edu/~walkiner/teaching/cs583-sp21/files/Wadler-TypeClasses.pdf), and even [effect systems](https://blog.yoshuawuyts.com/extending-rusts-effect-system/) are slowly making their way into the language.

[Unison](https://www.unison-lang.org/) is a new programming language in a class of its own. It's main new [big idea](https://www.unison-lang.org/docs/the-big-idea/) is that Unison code itself is immutable and content-addressed!

## Single-Node Storage

| Category     | Mutable                     | Immutable                         |
| ------------ | --------------------------- | --------------------------------- |
| File Systems | Traditional (ext4, NTFS)    | Copy-on-write (ZFS, Btrfs)        |
| Database     | B+ tree (MySQL, PostgreSQL) | LSM (RocksDB), MVCC (CockroachDB) |
| Data Storage | CRUD operations             | Event sourcing, append-only logs  |

File systems is one place where the two most popular linux distros, ubuntu and debian, are stuck in the past. ext4 is clearly an improvement over its ext predecessors, but better modern alternatives like zfs and btrfs (literally better fs) have existed for just as long, with much less usage. These filesystems, just like macos' proprietary APFS, make extensive use of "immutable" features like copy-on-write and snapshots. They are worth reading about, and are easy to try thanks to [docker support](https://docs.docker.com/engine/storage/drivers/btrfs-driver/).

In the world of databases, append-only [LSM](https://en.wikipedia.org/wiki/Log-structured_merge-tree)-based architectures have for a long-time now surpassed in popularity their mutable B+tree alternative for write-intensive workloads, despite a very vocal minority such as LMDB author claiming LSMs are still [worse at everything](https://news.ycombinator.com/item?id=10450246).

And more generally in the world of storage, many modern backends have also replaced, or at least augmented, their traditional CRUD db with an event-sourced, append-only queue-based asynchronous system: SAGA, Kafka, and the Lambda architecture are some buzzwords worth googling here.

## Distributed Storage

| Category            | Mutable                            | Immutable                                 |
| ------------------- | ---------------------------------- | ----------------------------------------- |
| Distributed Storage | Distributed databases with updates | Mutable Value Chains                      |
| Content Delivery    | Origin servers                     | Content-addressed storage (IPFS)          |
| Consensus Protocols | Paxos with state modification      | Raft/PBFT/Blockchain (append-only ledger) |

The fancy-sounding examples from this section are actually nothing new, and are essentially just additions on top of the basic concept of content-addressed storage: store values with key=hash(value). At the end of the day, the fancy BFT/CFT consensus protocols are just working on top of a hash chain ("block"chain), which works similarly to [git](#VCS--Package-Management--Build-Systems).

It is important to note that immutability here is the property of the underlying storage model. One can still create mutable views on top of the immutable storage by creating [mutable value chains](https://joearms.github.io/published/2015-06-19-Mutable-Value_Chains.html)!

As Joe Armstrong put it in this [blog post](https://joearms.github.io/published/2015-03-12-The_web_of_names.html):
> Today we have a web of names. Things like http://some.name.of.a.server.someplace/some.name.of.a.file . But we don't have either a web of hashes or a web of UUIDs.
>
> I think we need all three:
> - The web of names is convenient and easy to use
> - The web of UUIDs allows us to track content that changes with time
> - The web of hashes (SHA1) allows total precision in managing content


## Infra / DevOps

| Category           | Mutable                                    | Immutable                                       |
| ------------------ | ------------------------------------------ | ----------------------------------------------- |
| Deployment         | In-place updates                           | Blue-green deployments                          |
| Configuration      | Config files modified in place             | Versioned configs, environment variables        |
| Cloud Architecture | VMs with configuration management ("pets") | Containers, immutable infrastructure ("cattle") |
| Cluster Management | Mutable cluster state                      | CRDTs, replicated logs (Kafka)                  |

Perhaps surprisingly, immutability is a lot more present in infra than one might think. It [became a thing](https://martinfowler.com/bliki/ImmutableServer.html) before k8s was a thing and people were managing servers; the google SRE book [mentions it](https://sre.google/workbook/configuration-specifics/), as do many other [great](https://www.digitalocean.com/community/tutorials/what-is-immutable-infrastructure) [resources](https://www.hashicorp.com/en/resources/what-is-mutable-vs-immutable-infrastructure).

For a simple example, blue-green deployments are used to achieve zero-downtime deployments. Their main idea, when you squint a little, is the same as that of persistent data structures pictured at the very top of this article! An entirely new separate backend is (immutably) deployed, and a load-balancer is able to quickly switch back and forth between the two versions deployed, rolling back to the previous version if a bug/reversion was found in the new release.
![image](/assets/unbeknownst-pervasiveness-of-immutability/blue-green-deployment.png)

Modern tooling like Kubernetes has made these deployments even easier, by moving from vms to containers. This great [talk](https://www.youtube.com/watch?v=-daSI6fGQFA) speed-runs the history of containers and explains how containers are the new vm, and how k8s is leading this movement from mutable pet-like infra to immutable cattle-like containers that are spun up and thrown away.

## Web Related

| Category         | Mutable                            | Immutable                        |
| ---------------- | ---------------------------------- | -------------------------------- |
| UI Frameworks    | Direct DOM manipulation            | Virtual DOM (React)              |
| State Management | Direct state mutation              | Redux, Elm architecture          |
| API Design       | Mutable endpoints                  | Versioned, immutable APIs        |
| Web Architecture | Server-rendered with session state | JAMstack, static site generation |

I don't know enough about web technologies to make a coherent paragraph explaining the above table, and prefer to not let an LLM generate it for me, so will leave this section for the reader's imagination to complete.

## Operating Systems

| Category          | Mutable                   | Immutable                     |
| ----------------- | ------------------------- | ----------------------------- |
| Operating Systems | Traditional Linux distros | NixOS, CoreOS                 |
| System Updates    | In-place upgrades         | Atomic updates (ostree, snap) |
| Kernel Management | Kernel module loading     | Unikernels                    |

An OS' main purpose is to manage a piece of hardware which is only useful because of its mutability. One might thus think that dealing with mutable data structures is inevitable for os developers. That is partly true, yet many functional techniques leveraging immutability have made their ways into real OSes (meaning not only toy Haskell OSes that use monads like [HalVM](https://github.com/GaloisInc/HaLVM)).

[NixOS](https://nixos.org/) leverages the Nix package manager and build system's immutable store to manage an entire linux distro. NixOS is known to have a notoriously steep learning curve, and many fail to learn it properly; but those that do, apparently, never come back. See the [nix][nix] section for full details.

NixOS manages the entire system configuration declaratively and represents a complete paradigm shift in system management. OSTree and Snap, on the other hand, are more incremental improvements on traditional models, but still represent functional/immutable ways of dealing with OS system updates (OSTree) and application packaging (Snap).

The above were all distro examples, but even kernel developers have now seen immutable approaches taking over their world. [Unikernels](http://unikernel.org/) were introduced in 2014 as a futher improvement on current techniques in [immutable infra][immutable-infra]. as a means to reduce the footprint of OSes on cloud VMs; unikernel application are compiled statically with only the parts of the kernel that they need (eg. tcp stack) and can be popped directly on top of a hypervisor. They can hence be much smaller than docker containers, which means safer and faster. MirageOS is the most well known Unikernel example, but there are [many others](https://github.com/cetic/unikernels) nowadays.

## Data Processing

| Category          | Mutable               | Immutable                       |
| ----------------- | --------------------- | ------------------------------- |
| Processing Model  | Imperative processing | Functional reactive programming |
| Stream Processing | Stateful processors   | Stateless mappers/reducers      |
| Analytics         | OLAP databases        | Data lakes, immutable analytics |


Functional reactive programming introduced in functional languages like haskell has already made its way into [frontend frameworks](#Web-Related) like redux and elm, which speaks to its usefulness. I don't have much more to add here.

On the other hand, OLAP databases have mostly always been about periodically taking an entire companies' recent data from its multiple databases and dumping it to some structured database (or nowadays also unstructured "data lakes") to then run expensive queries over them. Those databases are mostly append-only, with queries representing views over them.

## Security Models

| Category         | Mutable             | Immutable                           |
| ---------------- | ------------------- | ----------------------------------- |
| Access Control   | Dynamic permissions | Capability-based security           |
| System Integrity | Runtime protection  | Verified boot, measured boot        |
| Audit Trails     | Mutable logs        | Append-only audit logs, blockchains |

Immutable append-only audit logs are the third pillar in Butler Lampson's [Security Gold Standard](https://www.usenix.org/legacy/event/sec05/tech/lampson.pdf#page=9.00), accompanying the better known authn/authz duo.

Although capabilities are often seen as the dual to the more common and traditional access control list (ACL) based security model, thanks to Butler Lampson's [matrix](https://en.wikipedia.org/wiki/Access_control_matrix) view, this perspective hides the immutable benefits of capabilities.

![image](/assets/unbeknownst-pervasiveness-of-immutability/capabilities-vs-acl.png)

Instead of having a system administrator mutate a global ACL, capabilities are "local" access rights, represented as immutable tokens that grant permissions. Once issued, a capability can't be modified—it can only be used as-is, revoked entirely, or in some systems, attenuated (creating a more restricted capability from an existing one).

Most systems exemplifying the use of capabilities tend to be esoteric and less well known, such as Tahoe-LAFS, KeyKOS, or the [Pony](https://tutorial.ponylang.io/reference-capabilities/index.html) programming languages. However, some modern well-known systems do also make use of capabilities: [WASI](https://github.com/WebAssembly/WASI/blob/main/docs/Capabilities.md), the [cosmos-sdk](https://docs.cosmos.network/v0.46/modules/capability/), and chromium.

## Software Design Patterns

| Category          | Mutable            | Immutable                       |
| ----------------- | ------------------ | ------------------------------- |
| Design Pattern    | Observer pattern   | Pub/sub with immutable messages |
| Error Handling    | Exception throwing | Railway-oriented programming    |
| Concurrency Model | Locks and mutexes  | Actor model, CSP                |


Including this section is definitely a bit of a stretch, but I think it still deserves to be here for completeness sake. I had never heard of [Railway-oriented programming](https://fsharpforfunandprofit.com/rop/), but it sounded too cool to not be added to my reading list.

As for concurrency models, any half-serious distributed systems programmer knows that [threads are a bad idea](https://web.stanford.edu/~ouster/cgi-bin/papers/threads.pdf). There are many different ways to circumvent shared state and mutexes: event-based systems (eg. node.js), rust's [borrow-checker](https://blog.rust-lang.org/2015/04/10/Fearless-Concurrency.html), actor-based systems (erlang processes being the most famous of the [4 different categories](https://tvcutsem.github.io/2016/12/actor-taxonomy)), and communicating sequential processes (CSP) based languages like go (although channels and actors are [very closely related](https://arxiv.org/abs/1611.06276)). All of these are related to immutability in some shape or form.

## VCS + Package Management + Build Systems

| Category                     | Mutable                       | Immutable                         |
| ---------------------------- | ----------------------------- | --------------------------------- |
| Version Control System (VCS) | CVS, SVN (modifiable history) | Git (immutable commits)           |
| System Package Management    | RPM, APT, Brew                | Nix, Guix                         |
| Build Systems                | Make (incremental builds)     | Bazel, Buck (reproducible builds) |

I haven't been programming for long enough to have used a VCS system other than git, so won't be able to speak about previous systems. Git's hash-chain is the very basis of gitops, which has revolutionized devops. One cannot rewrite history using `rebase -i` without changing the hash of the commit. When used as a package manager (hello submodules), this immutability prevents [supply-chain attacks](https://snyk.io/blog/npm-security-preventing-supply-chain-attacks/) like those that happen on mutable package managers such as npm.

![image](/assets/unbeknownst-pervasiveness-of-immutability/git-tree.png)


System package managers like apt and brew are another pile of mutable spaghetti. Brew install, brew install, brew install, 3 years later your system has turned into an irreproducible mess, and when forced to use the new shiny m3 laptop your company has provided for you, you cry just thinking of having to reproduce your environment. This moment is when you swear to never again use brew, discover about Eelco Dolstra and his PhD thesis [The Purely Functional Software Deployment Model](https://edolstra.github.io/pubs/phd-thesis.pdf). After 3 months of blood, sweat, and tears, you finally understand the distinction between Nix the language, nix the package manager, and nix the OS; not to mention nixpkgs and nixOps. At this point you wonder whether you shouldn't have just saved some effort, kept typing `brew install` a few more hundred times, and spent the rest with your family. But you can't stop running into [very](https://antithesis.com/blog/madness/) freaking [freaking](https://mitchellh.com/writing/nix-with-dockerfiles) [smart](https://jvns.ca/blog/2023/02/28/some-notes-on-using-nix/) [people](https://shopify.engineering/what-is-nix) who use and write about Nix, so there must be something there!

That little something, hiding behind all the complexity, is an [immutable store](https://nix.dev/manual/nix/2.24/store/)! There is obviously a lot more to Nix than its store, but that is its essence, as the picture below describes.

![image](/assets/unbeknownst-pervasiveness-of-immutability/nix-store.png)
<!-- image from https://youtu.be/RVYqsOky6g4?si=dgMxGtqW2YVvD3hI&t=1284 -->

The last developer tool used on a daily basis is the build system. Most people are familiar and probably use Makefiles. Make builds are are not reproducible because they depend on the current filesystem state. They also determine whether to rebuild or not by comparing file timestamps, which are... mutable: `touch -d "2025-01-15 15:30:00" file`.

Modern build systems like Bazel and Buck, first of all, use the Starlark language, which is a deterministic subset of Python that [favours immutable data structures](https://bazel.build/rules/language). Furthermore, they make use of [content-addressable storage][content-addressable-storage] to determine whether dependencies have truly changed, instead of just relying on mutable (and often incorrect!) timestamps. More importantly, they provide [reproducible builds](https://en.wikipedia.org/wiki/Reproducible_builds).

## Conclusion

![image](/assets/unbeknownst-pervasiveness-of-immutability/theyre-the-same-meme.png)




[immutable-infra]: #Infra--DevOps
[nix]: #VCS--Package-Management--Build-Systems
[content-addressable-storage]: #Distributed-Storage