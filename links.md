---
layout: page
title: Links
permalink: /links/
---

This page contains articles that have shaped my thinking and that I frequently find myself going back to or sending people to. It is 100% shamelessly inspired by matklad's [similar page](https://matklad.github.io/links.html), and should be considered as an extension of it.

## Meta Links

Meta links point to other similar aggregate lists of interesting articles, typically of a specific topic.

**Matklad's Links**
<br>&nbsp;&nbsp;&nbsp;&nbsp;
[https://matklad.github.io/links.html](https://matklad.github.io/links.html)
<br>&nbsp;&nbsp;&nbsp;&nbsp;
The list this page is an extension of, mostly on programming languages, compilers, and how to write software that stays simple.

**Vigorous Public Debates in Academic Computer Science**
<br>&nbsp;&nbsp;&nbsp;&nbsp; 
[https://blog.regehr.org/archives/1430](https://blog.regehr.org/archives/1430)
<br>&nbsp;&nbsp;&nbsp;&nbsp;
A catalog of famous disagreements between accomplished computer scientists. Valuable because it shows how much of the field has no obvious objective truth, and how experts argue when there isn't one.

**What every computer science major should know**
<br>&nbsp;&nbsp;&nbsp;&nbsp;
[https://matt.might.net/articles/what-cs-majors-should-know/](https://matt.might.net/articles/what-cs-majors-should-know/)
<br>&nbsp;&nbsp;&nbsp;&nbsp;
A checklist of what a CS education should actually leave you with, topic by topic, with recommended resources for each.

**Ted Kaminski's Book (and his entire blog)**
<br>&nbsp;&nbsp;&nbsp;&nbsp;
[https://www.tedinski.com/book/](https://www.tedinski.com/book/)
<br>&nbsp;&nbsp;&nbsp;&nbsp;
A long series of short essays building up a coherent theory of software design: how to decompose systems, and which abstractions survive contact with change. Hard to pick favorites — read the whole thing.

## Normal Links

**Russ Cox's Memory Models Series**
<br>&nbsp;&nbsp;&nbsp;&nbsp;
[https://research.swtch.com/mm](https://research.swtch.com/mm)
<br>&nbsp;&nbsp;&nbsp;&nbsp;
What it actually means for a language to have a memory (aka consistency) model: which reorderings hardware and compilers are allowed to perform, and why "don't write data races" is a definition rather than advice.

**Computer Networks: A Systems Approach**
<br>&nbsp;&nbsp;&nbsp;&nbsp;
[https://book.systemsapproach.org/index.html](https://book.systemsapproach.org/index.html)
<br>&nbsp;&nbsp;&nbsp;&nbsp;
A free networking textbook that builds the internet up from the problem each layer exists to solve, instead of cataloging protocols.

**Fragile narrow laggy asynchronous mismatched pipes kill productivity**
<br>&nbsp;&nbsp;&nbsp;&nbsp;
[https://thume.ca/2020/05/17/pipes-kill-productivity/](https://thume.ca/2020/05/17/pipes-kill-productivity/)
<br>&nbsp;&nbsp;&nbsp;&nbsp;
Splitting a system across a network forces you to solve seven hard problems at once — fragility, bandwidth, latency, asynchrony, protocol mismatch, security, serialization. So try really hard not to distribute anything you don't have to.

**Scalability! But at what COST?** (McSherry, Isard, Murray)
<br>&nbsp;&nbsp;&nbsp;&nbsp;
[https://www.usenix.org/system/files/conference/hotos15/hotos15-paper-mcsherry.pdf](https://www.usenix.org/system/files/conference/hotos15/hotos15-paper-mcsherry.pdf)
<br>&nbsp;&nbsp;&nbsp;&nbsp;
Defines COST — the Configuration that Outperforms a Single Thread — and shows that many published distributed systems never beat a competent single-threaded implementation on any number of cores. Scaling well and going fast are different things, and papers usually only measure the first.

**Data, objects, and being railroaded into misdesign** / **The Expression Problem** (Ted Kaminski)
<br>&nbsp;&nbsp;&nbsp;&nbsp;
[https://www.tedinski.com/2018/01/23/data-objects-and-being-railroaded-into-misdesign.html](https://www.tedinski.com/2018/01/23/data-objects-and-being-railroaded-into-misdesign.html)
<br>&nbsp;&nbsp;&nbsp;&nbsp;
[https://www.tedinski.com/2018/02/27/the-expression-problem.html](https://www.tedinski.com/2018/02/27/the-expression-problem.html)
<br>&nbsp;&nbsp;&nbsp;&nbsp;
Data and objects are duals: data is transparent and open to new operations, objects are opaque and open to new implementations. Languages railroad you into one of them, and the second post explains why the tradeoff can't be escaped without giving up comprehensibility.

**Data on the Outside vs. Data on the Inside** (Pat Helland)
<br>&nbsp;&nbsp;&nbsp;&nbsp;
[https://queue.acm.org/detail.cfm?id=3415014](https://queue.acm.org/detail.cfm?id=3415014)
<br>&nbsp;&nbsp;&nbsp;&nbsp;
Data inside a database is mutable, current, and transactionally consistent; data outside it — messages, documents, events — is immutable, versioned, and always from the past. Treating the two as the same thing is the root of a lot of distributed systems pain.

**The Value of Values** / **Are We There Yet?** (Rich Hickey)
<br>&nbsp;&nbsp;&nbsp;&nbsp;
[https://github.com/matthiasn/talk-transcripts/blob/master/Hickey_Rich/ValueOfValues.md](https://github.com/matthiasn/talk-transcripts/blob/master/Hickey_Rich/ValueOfValues.md)
<br>&nbsp;&nbsp;&nbsp;&nbsp;
[https://github.com/matthiasn/talk-transcripts/blob/master/Hickey_Rich/AreWeThereYet.md](https://github.com/matthiasn/talk-transcripts/blob/master/Hickey_Rich/AreWeThereYet.md)
<br>&nbsp;&nbsp;&nbsp;&nbsp;
Place-oriented programming, where new information overwrites old in place, is a holdover from when memory was scarce. Objects conflate identity, state, and time; separating them — an identity being a series of immutable values observed over time — is what makes concurrent programs tractable.

**The Expression Problem and its solutions** (Eli Bendersky)
<br>&nbsp;&nbsp;&nbsp;&nbsp;
[https://eli.thegreenplace.net/2016/the-expression-problem-and-its-solutions/](https://eli.thegreenplace.net/2016/the-expression-problem-and-its-solutions/)
<br>&nbsp;&nbsp;&nbsp;&nbsp;
The implementation side of the expression problem: adding new types is easy in OO and adding new operations is easy in FP, each painful in the other. A tour of the mechanisms that try to get both, including double dispatch and the visitor pattern.

**Bit Twiddling Hacks** (Sean Eron Anderson)
<br>&nbsp;&nbsp;&nbsp;&nbsp;
[https://graphics.stanford.edu/~seander/bithacks.html](https://graphics.stanford.edu/~seander/bithacks.html)
<br>&nbsp;&nbsp;&nbsp;&nbsp;
The classic catalog of branchless bit manipulation tricks: counting set bits, reversing bits, computing sign or absolute value without branches, rounding to powers of two.
