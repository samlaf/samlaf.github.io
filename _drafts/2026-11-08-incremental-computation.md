---
title:  "Incremental computation"
category: programming
date:   2026-11-08
---

- [Redo only what changed](#redo-only-what-changed)
- [Push and pull](#push-and-pull)
- [Push is pull in continuation-passing style](#push-is-pull-in-continuation-passing-style)
- [Static and dynamic graphs](#static-and-dynamic-graphs)
- [Glitches](#glitches)
- [Where FRP fits](#where-frp-fits)
- [What databases add: changes you can add up](#what-databases-add-changes-you-can-add-up)
- [Full state or partial state](#full-state-or-partial-state)
- [The work moves to the write path](#the-work-moves-to-the-write-path)
- [The systems side by side](#the-systems-side-by-side)
- [References](#references)

## Redo only what changed

[Database caches](/programming/db-caches.html) ended on a mapping problem. A write changes rows, but a cache holds keys, and a key may be built from many rows. Something has to know which keys a row feeds. In the [Hacker News discussion][hn-meta-cache] of Meta's cache-invalidation post, commenters called this the hard part. Lu Pan, the post's author, replied that the problem is really "materialization/denormalization", and is "not even unique to cache": it shows up "even if it's a table on the same database".

Incremental computation is the general form of that problem. A program computes an output from inputs. When one input changes, redo only the work that depends on it. Make does this for files, a spreadsheet for cells, a UI framework for the screen, and a database for materialized views. [Rado Kirov's series][kirov-1] works through the problem from first principles, and this post follows its path, then turns to databases:

1. Push or pull: does a change announce itself, or does a reader ask?
2. Push is pull rewritten in continuation-passing style.
3. Static or dynamic graphs: is the dependency graph known before the program runs?
4. Glitches: what a reader sees while a change is still spreading.
5. What databases add: changes that can be added and subtracted.

## Push and pull

Kirov's test is the type signature. In a pull-based API, methods look like `(...): T`: you ask for a value and get it back. In a push-based API, they look like `((x: T) => ...): ...`: you hand over a function, and the system calls it when a value is ready.

- **Pull** is demand-driven. Nothing runs until someone reads the output. Then the system walks back through the inputs and recomputes what is out of date. Make works this way: you ask for a target. [Adapton][adapton] is the research system built around demand.
- **Push** is data-driven. A change to an input travels forward, and each node that depends on it runs again. Jane Street's [Incremental][js-incremental] works this way: you set inputs, call `stabilize`, and changes flow forward to the outputs.

Most real systems mix the two:

- **Signals.** The [TC39 Signals proposal][tc39-signals], like Solid and Preact, pushes a "dirty" mark forward on a write, and recomputes lazily on a read: "Computed Signals are lazy, i.e., pull-based".
- **Push-pull FRP.** [Elliott's 2009 paper][push-pull-frp] splits a behavior into a discrete part, "reactive values", and a continuous part, "time functions". Reactive values are evaluated by push, "leaving pull for time functions".
- **Noria and Readyset.** Writes push changes forward through the dataflow graph. A miss pulls a result back with an "upquery". [Database caches](/programming/db-caches.html#query-results-readyset) covers the cache side.

## Push is pull in continuation-passing style

The push signature `((x: T) => ...)` is a continuation: a function that stands for "the rest of the program". Rewrite a pull computation in continuation-passing style (CPS), so it calls the rest of the program with each value instead of returning it, and you get a push computation. Erik Meijer's duality between iterables and observables makes the same observation for collections. So CPS is the program transformation, and push-based reactivity is the runtime structure it produces.

This matters for incremental computation, because incrementality is about rerunning or skipping the rest of the computation when one input changes. CPS turns the rest of the computation into a value you can store, memoize, and call again.

Kirov's example computes `sqrt(x² + y²)` as four operations: `op1 = square(x)`, `op2 = square(y)`, `op3 = op1 + op2`, and `op4 = sqrt(op3)`. He rewrites it into a CPS-like form, and then memoizes each continuation. The naive version has a bug: "as soon as `op1` is the same as before we will skip to the end, ignoring any change to `op2`." The fix is to memoize `op3`'s two inputs together. A continuation captures the rest of the program, but a node with two inputs depends on both, and the memo must too.

The same idea runs through the research systems:

- **Self-adjusting computation.** In [Acar, Blelloch and Harper's adaptive functional programming][afp], reading a changeable value takes a closure: `read(m, fn v => ...)`. The runtime records each reader in a dynamic dependence graph. When `m` changes, change propagation re-runs just that reader, not the whole program. Jane Street's Incremental is [based on this work][js-incremental-blog].
- **Build systems.** [Build Systems à la Carte][bsalc] calls one of its schedulers "suspending": a task that needs a dependency pauses while the dependency builds. The paper notes that suspending "can be done with cheap green threads and blocking (the original approach of Shake) or using continuation-passing style [...] (what Shake currently does)."

## Static and dynamic graphs

In Incremental, `map` and `map2` connect a node to inputs fixed when you build the graph. `bind` is different. Whenever its input changes, it calls a function that returns a new node, "possibly with an arbitrary DAG below it". So a value can decide which part of the graph exists.

[Build Systems à la Carte][bsalc] names the same split. An applicative task declares its dependencies before it runs, so the graph is static, as in Make. A monadic task can read one value and then decide what to depend on next, so the graph is dynamic, as in Excel and Shake. A dynamic graph is more expressive, but the system learns the dependencies only by running the task. That makes it harder to stay minimal and rebuild nothing extra.

A SQL view sits on the static side: the dataflow graph is fixed when you create the view. Recursion is the exception that needs more machinery, and [the database section](#what-databases-add-changes-you-can-add-up) comes back to it.

## Glitches

Take Kirov's graph again. `op3` reads both `op1` and `op2`. Suppose `x` and `y` change together. A naive push runs `op1`, then `op3`, then `op4`, and only then `op2`, `op3`, and `op4` again. For a moment, `op4` holds a value computed from the new `x` and the old `y`, a state no input ever had. That transient value is a glitch. Kirov's push version notes that "the two input updates can arrive at different times", and keeps state in `op3` to cope.

Each family of systems fixes glitches its own way:

- **Heights.** Incremental gives each node a height greater than all its inputs, and `stabilize` visits nodes "in non-decreasing order of 'height'". A node runs only after every input has settled.
- **Lazy pulls.** Signals recompute on read, after the write has marked everything dirty. The TC39 proposal calls its computation "glitch-free".
- **Timestamps and frontiers.** Differential Dataflow labels every update with a logical time, and tracks the frontier: the times for which no more input can arrive. A reader can wait for the frontier to pass time *t*, and then see every view as of *t*. [Materialize][materialize-isolation] builds strict serializability on this. At database scale, that is glitch freedom.

Noria chose the other way. Its paper says an update "may appear in different views at different times," and calls eventual consistency "attractive for performance and scalability". Readyset inherits that choice.

## Where FRP fits

Functional reactive programming started as a semantics, not as an implementation technique. In [Elliott and Hudak's Fran][fran] (ICFP 1997), a behavior is a value that varies over continuous time, and an event is a stream of timestamped occurrences. That definition says nothing about recomputing less. Implementations use incremental techniques to make it efficient, as push-pull FRP does.

Libraries like RxJS are reactive streams, not FRP in Elliott's sense. Kirov's view is that "reactive programming with streams can solve many problems of which incremental computation is just one of," and that "incremental computation does not need the full power of Rxjs reactive primitives." Signals are the opposite case: a small API that does incremental computation and little else.

## What databases add: changes you can add up

General incremental systems detect change by comparing whole values. Incremental, by default, treats a node as changed "if its new value is not `phys_equal` to the previous value", and lets you set a custom cutoff. To skip work, the system recomputes a value and compares it with the old one.

View maintenance does better, because a database change has algebra. [DBSP][dbsp] (Budiu et al., VLDB 2023) makes this precise. Tables are Z-sets: each row carries an integer weight, positive for an insert and negative for a delete. Z-sets form a group, so changes can be added and subtracted. A stream of changes then has two operators:

- **Integrate (I)** sums a stream of changes into a stream of full tables.
- **Differentiate (D)** turns a stream of full tables back into a stream of changes.

The incremental version of a streaming query Q is Q<sup>Δ</sup> = D ∘ Q ∘ I: integrate the changes, run the query, and differentiate the result. Two theorems make this cheap:

- **Linear operators are their own incremental versions** (Q<sup>Δ</sup> = Q). Filter, projection, and union fall here. A change to the input maps straight to a change to the output.
- **Joins are bilinear,** and their change has three terms: Δ(a ⋈ b) = Δa ⋈ Δb + a ⋈ Δb + Δa ⋈ b, where a and b are the tables before the change.

`distinct` is the notable exception, and it needs its own rule. Recursion uses nested streams, where each value of the outer stream is itself a stream over loop iterations. Differential Dataflow uses nested timestamps for the same purpose, and that is how Materialize can maintain [`WITH MUTUALLY RECURSIVE`][materialize-recursive] queries.

This is why database view maintenance can be far cheaper than general memoization. For one input change, it never recomputes and compares the output. It computes the output change directly. [Cai et al.'s change structures][ilc] (PLDI 2014) carry the same idea to higher-order languages. DBSP's authors went on to build [Feldera][feldera].

## Full state or partial state

The two database engines also differ in how much of each result they keep.

- **Materialize keeps full state.** An index on a view holds the result for every key in memory, shared by every query in the cluster that uses it.
- **Noria keeps partial state.** A view keyed by `user_id` holds only the keys that have been read. A miss sends an upquery up the graph to compute that key. From then on, pushed changes keep it current, and it can be evicted later. Memory scales with the working set, not the whole result.

Partial state brings back the problems of a cache. Upqueries and pushed updates can race, and the Noria paper notes that "ordinary updates and upqueries can race," so correctness "requires careful attention to invariants." That race is the [fill race](/programming/db-caches.html#the-fill-race) inside a dataflow engine.

## The work moves to the write path

Incremental maintenance doesn't remove work. It moves work from reads to writes. A view over a join must, on every write, find each result the write affects: a join on the write path. In the [HN thread][hn-meta-cache], Pan pointed out that this fanout depends on the data, not the schema, so nothing bounds it. On an update-heavy workload, "you will spend more power on processing invalidation than serving user queries." Meta's TAO takes the other side of the trade, and [joins on the read path](/programming/db-caches.html#which-keys-a-write-touches) instead.

The same thread named two conditions for any engine that maintains derived results:

- **It must know the query.** A commenter put the appeal of Materialize and Readyset this way: "the invalidation pipeline is automatically derived from the query structure." Pan had made the same point earlier in the thread: if "anyone can cache anything without the invalidation pipeline knowing", the problem can't be solved.
- **It must compute against a snapshot.** An asynchronous pipeline that reads the database while it changes computes against "a moving data source". Each update must be computed as of the write's commit. Pan's example was Spanner's commit timestamps. Differential Dataflow's timestamps do the same job, and they are also what makes its reads [glitch-free](#glitches).

## The systems side by side

| System | Push or pull | Graph | How it avoids glitches | How it detects a change |
| --- | --- | --- | --- | --- |
| Make | Pull | Static | Builds in dependency order | File timestamps |
| Shake | Pull, suspending | Dynamic | Builds in dependency order | Verifying traces |
| Adapton | Pull | Dynamic | Recomputes on demand | Equality |
| Incremental | Push, on `stabilize` | Static with `map`, dynamic with `bind` | Heights | Cutoff, `phys_equal` by default |
| Signals | Push dirty marks, pull values | Dynamic, tracked on each run | Lazy recomputation | Equality |
| Noria, Readyset | Push writes, pull misses | Static per query | Doesn't: eventual consistency | Row deltas |
| Materialize | Push | Static, with loops for recursion | Timestamps and frontiers | Weighted deltas |
| DBSP, Feldera | Push | Static, nested streams for recursion | One step per input change | Z-set deltas |

## References

1. [Incremental Computation, part 1][kirov-1], [part 2][kirov-2], and [part 3][kirov-3] — Rado Kirov, 2020; push and pull, CPS, memoizing continuations
2. [Hacker News discussion of "Cache made consistent"][hn-meta-cache] — 2022; materialization as the hard part, joins on the write path, and computing against a snapshot
3. [Build Systems à la Carte][bsalc] — Mokhov, Mitchell, Peyton Jones, ICFP 2018; applicative and monadic tasks, and the suspending scheduler
4. [Adaptive Functional Programming][afp] — Acar, Blelloch, Harper, TOPLAS 2006; modifiables, readers, and change propagation
5. [Incremental][js-incremental] and [Introducing Incremental][js-incremental-blog] — Jane Street; heights, cutoffs, and `bind`
6. [Adapton][adapton] — Hammer et al., PLDI 2014; demand-driven incremental computation
7. [JavaScript Signals proposal][tc39-signals] — TC39; lazy, glitch-free computed signals
8. [Functional Reactive Animation][fran] — Elliott and Hudak, ICFP 1997; behaviors and events
9. [Push-Pull Functional Reactive Programming][push-pull-frp] — Elliott, Haskell Symposium 2009; push for reactive values, pull for time functions
10. [DBSP: Automatic Incremental View Maintenance for Rich Query Languages][dbsp] — Budiu, Chajed, McSherry, Ryzhyk, Tannen, VLDB 2023; Z-sets, integration, differentiation
11. [A Theory of Changes for Higher-Order Languages][ilc] — Cai, Giarrusso, Rendel, Ostermann, PLDI 2014; change structures
12. [Noria: dynamic, partially-stateful data-flow for high-performance web applications][noria] — Gjengset et al., OSDI 2018; partial state, upqueries, eventual consistency
13. [Isolation levels][materialize-isolation] and [Recursive CTEs][materialize-recursive] — Materialize docs
14. [Feldera][feldera] — an incremental query engine from the creators of DBSP

[kirov-1]: https://rkirov.github.io/posts/incremental_computation/ "Incremental Computation (part 1)"
[kirov-2]: https://rkirov.github.io/posts/incremental_computation_2 "Incremental Computation (part 2)"
[kirov-3]: https://rkirov.github.io/posts/incremental_computation_3 "Incremental Computation (part 3)"
[hn-meta-cache]: https://news.ycombinator.com/item?id=31671252 "Hacker News: Cache made consistent"
[bsalc]: https://www.microsoft.com/en-us/research/uploads/prod/2018/03/build-systems.pdf "Build Systems à la Carte"
[afp]: https://www.cs.cmu.edu/~rwh/papers/afp/toplas06.pdf "Adaptive Functional Programming"
[js-incremental]: https://github.com/janestreet/incremental "Incremental"
[js-incremental-blog]: https://blog.janestreet.com/introducing-incremental/ "Introducing Incremental"
[adapton]: http://adapton.org/ "Adapton"
[tc39-signals]: https://github.com/tc39/proposal-signals "JavaScript Signals standard proposal"
[fran]: http://conal.net/papers/icfp97/ "Functional Reactive Animation"
[push-pull-frp]: http://conal.net/papers/push-pull-frp/ "Push-Pull Functional Reactive Programming"
[dbsp]: https://www.vldb.org/pvldb/vol16/p1601-budiu.pdf "DBSP: Automatic Incremental View Maintenance for Rich Query Languages"
[ilc]: https://dl.acm.org/doi/10.1145/2594291.2594304 "A Theory of Changes for Higher-Order Languages"
[noria]: https://www.usenix.org/conference/osdi18/presentation/gjengset "Noria: dynamic, partially-stateful data-flow for high-performance web applications"
[materialize-isolation]: https://materialize.com/docs/get-started/isolation-level/ "Materialize: Isolation levels"
[materialize-recursive]: https://materialize.com/docs/sql/select/recursive-ctes/ "Materialize: Recursive CTEs"
[feldera]: https://www.feldera.com/ "Feldera"
