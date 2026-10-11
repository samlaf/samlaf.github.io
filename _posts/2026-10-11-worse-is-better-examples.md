---
title:  "Worse is Better and Narrow Waists"
series: "Design Tradeoffs"
category: programming
---

- [Narrow Waists](#narrow-waists)
- [Unix vs. Lisp](#unix-vs-lisp)
- [JavaScript vs. Scheme, ES4, and Dart](#javascript-vs-scheme-es4-and-dart)
- [TCP/IP vs. RINA](#tcpip-vs-rina)
- [OAuth vs. SPKI, Macaroons, and Biscuit](#oauth-vs-spki-macaroons-and-biscuit)
- [LSP vs. Smalltalk](#lsp-vs-smalltalk)
- [References](#references)

Richard Gabriel's [The Rise of *Worse is Better*](https://www.dreamsongs.com/RiseOfWorseIsBetter.html) describes a pattern that keeps showing up in software: a simpler, less complete system often beats a more elegant and theoretically superior one, because it is easier to build, adopt, and evolve.

The key distinction is between two kinds of simplicity:
- **Simplicity of interface:** how clean, consistent, and complete is the abstraction exposed to users?
- **Simplicity of implementation:** how easy is the system itself to build, port, and maintain?

The worse-is-better philosophy picks the second when the two conflict:
> It is more important for the implementation to be simple than the interface.
> -- Richard Gabriel

This article is meant as a personal compendium of examples of this tradeoff that I have come across. Expect the list to grow over time. But first, a detour through narrow waists, because I think they are the same idea seen from another angle.


## Narrow Waists

A narrow waist is a single shared interface with many things on one side and many things on the other. IP sits between many link technologies and many applications. The Unix byte stream sits between many devices and many programs. Andy Chu at Oil Shell [puts it](https://www.oilshell.org/blog/2022/02/diagrams.html) this way:
> A narrow waist is concept, interface, or protocol that solves an interoperability problem. It avoids O(M × N) code explosions, letting us write O(M + N) amounts of code instead.

That explains why a waist exists. Why it should be *narrow* comes from David D. Clark's idea of a [spanning layer](https://en.wikipedia.org/wiki/Hourglass_model): a minimal common service that hides the differences below it and presents a uniform service above it. Micah Beck [formalized](https://arxiv.org/abs/1607.07183) the tradeoff. If a spanning layer's specification promises less (is logically weaker), then:
> a weaker layer specification has fewer applications but more implementations.

Here is where it gets confusing, because "simple interface" means two opposite things:
- In Gabriel's sense, a simple interface is *easy to use*: it hides the hard cases from the caller. That requires the system to promise more.
- In the narrow waist sense, a simple interface is *small and weak*: it promises very little. IP is best effort, a byte stream has no structure. That is easy to implement everywhere, and hard to use directly. The caller has to retry, reorder, parse, and interpret.

So a narrow waist is exactly Gabriel's worse-is-better choice. It is simple to implement, so it spreads everywhere, and the work of making it pleasant is pushed out to the edges. This is also the [end-to-end argument](https://web.mit.edu/Saltzer/www/publications/endtoend/endtoend.pdf): put function at the endpoints, and keep the shared middle minimal. swyx makes the link [explicitly](https://swyx.io/narrow-waists):
> Narrow waists often benefit from "Worse is Better" type software dynamics.

The losers in this story are not the waists with a "complex" interface. They are the Right Thing designs that tried to give everyone a rich, complete interface in the middle.

Winning has a price though. Once many independent parties implement a waist, nobody can change it. Moxie Marlinspike [makes this point](https://signal.org/blog/the-ecosystem-is-moving/) about federated protocols:
> once you federate your protocol, it becomes very difficult to make changes

> We got to HTTP version 1.1 in 1997, and have been stuck there until now. Likewise, SMTP, IRC, DNS, XMPP, are all similarly frozen in time circa the late 1990s.

swyx calls it a "deadlock dual network effect". The waist's warts are frozen in place, and the Right Thing never gets a second chance to replace it. Improvements can only be layered on top. Moxie's answer at Signal was to shrink the number of parties who have to agree on a change, which is another way of making the waist narrow.

So every example below answers the same question: what is the smallest sufficient contract to standardize, while leaving everything else free to evolve? I describe each one with the same four parts:
- **The waist:** what got standardized and won.
- **The Right Thing:** the richer design that lost.
- **Pushed to the edges:** the work the waist refused to do.
- **The price:** the warts that froze in place.

## Unix vs. Lisp

- **The waist:** a small system call interface, with files as plain byte streams.
- **The Right Thing:** Lisp machines and ITS, where the system takes on the hard cases for the caller.
- **Pushed to the edges:** retrying interrupted calls, parsing byte streams.
- **The price:** every caller in the world checks for `EINTR`.

This is Gabriel's original example. He contrasts the MIT/Stanford "Right Thing" philosophy with the New Jersey "Worse is Better" philosophy of Unix and C.

The story is about interrupted system calls (the "PC loser-ing problem"). The right thing is for the system to back out and resume the call so the caller never notices. Unix instead returns an error (`EINTR` today), and the caller has to check for it and retry. When the MIT guy complained, the New Jersey guy answered that the:
> right tradeoff has been selected in Unix -- namely, implementation simplicity was more important than interface simplicity.

Beck uses Unix as his second example of a spanning layer, next to IP. His case is `fork()`, which he calls "a logically much weaker operation" than the process creation calls of earlier systems. The child cannot be configured by the parent. It just inherits everything, and separate calls like `exec()` and `nice()` change it afterwards.

Unix's small, pragmatic core was easy to implement and port, and it spread everywhere. Gabriel's conclusion is that worse-is-better "has better survival characteristics than the-right-thing", and that "Unix and C are the ultimate computer viruses."

## JavaScript vs. Scheme, ES4, and Dart

- **The waist:** one small language that every browser runs.
- **The Right Thing:** Scheme, then ES4, then Dart.
- **Pushed to the edges:** libraries, polyfills, and languages that compile to JavaScript, like TypeScript.
- **The price:** `typeof null === "object"`, forever, because "Don't break the Web!"

JavaScript is the next virus after Unix and C, and it has a Lisp in its backstory too. Brendan Eich [writes](https://brendaneich.com/2008/04/popularity/):
> I was recruited to Netscape with the promise of "doing Scheme" in the browser.

Then came the constraints. Management wanted a language that would "look like Java", and Eich built the first prototype in ten days. What shipped was, in his own words, "a quickie love-child of C and Self". But the core was good:
> I'm happy that I chose Scheme-ish first-class functions and Self-ish (albeit singular) prototypes as the main ingredients.

`typeof null === "object"` is my favorite example of the implementation leaking into the interface, in true PC loser-ing fashion. From the [JavaScript HOPL paper](https://www.wirfs-brock.com/allen/jshopl.pdf):
> The runtime value of null was encoded with the same internal tag value used for object values and hence the implementation of the typeof operator returned "object" without needing any extra special-case logic.

Once JavaScript was in every browser, its warts could never be fixed. The Right Thing was attempted anyway. ES4 was a major redesign with classes, packages, namespaces, and optional types. It split the standards committee for over a year and was abandoned in 2008. Eich's [Harmony announcement](https://esdiscuss.org/topic/ecmascript-harmony):
> Some ES4 proposals have been deemed unsound for the Web, and are off the table for good: packages, namespaces and early binding.

The committee went with the modest ES3.1 (renamed ES5) instead. Its fixes, such as strict mode, are opt-in so that old pages keep working. Fixing `typeof null` was considered and rejected for the same reason.

Google's [Dart](https://dart.dev/) tried a clean-slate replacement, with its own VM planned for Chrome. That plan was dropped in 2015. Meanwhile [TypeScript](https://www.typescriptlang.org/) won by layering optional types on top of JavaScript and compiling down to it. It made no attempt to replace the waist.

This is exactly the trajectory Gabriel predicted:
> It is important to remember that the initial virus has to be basically good. [...] the worse-is-better software first will gain acceptance, second will condition its users to expect less, and third will be improved to a point that is almost the right thing.

## TCP/IP vs. RINA

- **The waist:** IP, a best-effort packet delivery service.
- **The Right Thing:** John Day's RINA, where every layer is the same complete IPC facility.
- **Pushed to the edges:** reliability (TCP, QUIC), encryption, and stable node identity (overlays like Tailscale).
- **The price:** IPv6 has been "next" for decades, and NATs patch over the address shortage.

This is the canonical narrow waist. The [Systems Approach book](https://book.systemsapproach.org/e2e/trend.html) credits the minimal IP layer for the Internet's growth:
> by keeping the IP layer that everyone has to agree to minimal, a thousand flowers were allowed to bloom both above and below.

John Day's [Recursive InterNetwork Architecture (RINA)](https://en.wikipedia.org/wiki/Recursive_InterNetwork_Architecture) argues that the waist is not just narrow, but wrong. Networking is inter-process communication, and every layer should be an instance of the same general-purpose IPC facility, with common mechanisms for naming, routing, and resource management. It is a beautiful, uniform design.

TCP/IP, for example, doesn't separate a node's stable identity from its network location, which RINA gets right. Yet overlays such as [Tailscale](https://tailscale.com/blog/how-tailscale-works) recover that abstraction with virtual IP addresses, WireGuard, and endpoint discovery, without changing the underlying Internet. More generally, the narrow waist lets protocols like QUIC, WireGuard, and VXLAN evolve independently of each other.

The price is that the waist itself cannot move. Moxie again: the Internet has "been trying for the past 20 years to switch to a second production version of IP".

## OAuth vs. SPKI, Macaroons, and Biscuit

- **The waist:** who gets a token, how they get it, and how they present it.
- **The Right Thing:** OAuth 1.0's signed requests, and credentials with real delegation semantics like SPKI, Macaroons, and Biscuit.
- **Pushed to the edges:** what the token means, how policy is represented, attenuation, and delegation chains.
- **The price:** a framework so loose that it took a decade of extra specs to make it secure.

![](/assets/worse-is-better-examples/oauth-midwit.png)

OAuth 1.0 ([RFC 5849](https://datatracker.ietf.org/doc/html/rfc5849)) signed every request cryptographically, so security did not depend on the transport. The price was implementation complexity: the signature base string canonicalization is where everyone's implementation broke. OAuth 2.0 ([RFC 6749](https://datatracker.ietf.org/doc/html/rfc6749)) dropped request signing for bearer tokens, and handed confidentiality to TLS. Clients became much easier to write.

Eran Hammer, lead author of OAuth 1.0 and editor of OAuth 2.0, resigned and pulled his name from the spec. His rant, [*OAuth 2.0 and the Road to Hell*](https://gist.github.com/nckroy/dd2d4dfc86f7d13045ad715377b6a48f), is worth reading:
> I reached the conclusion that OAuth 2.0 is a bad protocol. WS-* bad.

> one of the compromises was to rename it from a protocol to a framework

The RFC itself [admits](https://datatracker.ietf.org/doc/html/rfc6749#section-1.8) as much:
> as a rich and highly extensible framework with many optional components, on its own, this specification is likely to produce a wide range of non-interoperable implementations.

But not being a full protocol is the point. SPKI, Macaroons, and Biscuit were carefully thought through as a whole. Their goal was to give authorization credentials beautiful delegation semantics. OAuth's goal was humbler: to standardize the messy interaction between browsers, users, apps, and APIs.

So OAuth standardized only three things:
- who gets a token,
- how they get it,
- and how they present it.

It left everything else to other systems:
- what authority actually means,
- how policy is represented,
- how authority can be attenuated,
- how delegation is chained,
- and how relationships are modeled.

That separation turned out to be incredibly deployable. The access token is opaque to the client, so its format and meaning are the resource server's business. It can be a random string looked up in a database, a JWT, a macaroon, or a biscuit. Policy can live in RBAC tables or in a Zanzibar-style relationship graph. OAuth doesn't care.

Seen this way, OAuth is the narrow waist of web authorization, the same way IP is the narrow waist of networking. SPKI, Macaroons, and Biscuit are closer to RINA: richer and more principled, and much less deployed.

The price is the one Hammer predicted:
> OAuth 2.0 at the hand of a developer with deep understanding of web security will likely result [in] a secure implementation. [...] 2.0 is likely to produce insecure implementations.

The next decade was spent standardizing back the constraints that 2.0 left out: [PKCE](https://datatracker.ietf.org/doc/html/rfc7636), [OpenID Connect](https://openid.net/specs/openid-connect-core-1_0.html), the [OAuth 2.0 Security BCP](https://datatracker.ietf.org/doc/html/rfc9700), and finally [OAuth 2.1](https://datatracker.ietf.org/doc/draft-ietf-oauth-v2-1/), which folds all of it into the baseline. Meanwhile [GNAP](https://datatracker.ietf.org/doc/html/rfc9635), the clean-slate "OAuth 3", is a finished standard that almost nobody runs.

## LSP vs. Smalltalk

- **The waist:** text documents addressed by line and column, and the editor's widgets (completions, hovers, diagnostics, edits).
- **The Right Thing:** a live programming system that understands the program's semantics, like Smalltalk and Newspeak; or richer protocols like the Dart Analysis Protocol.
- **Pushed to the edges:** each language's real semantics, inside its own language server.
- **The price:** columns counted in UTF-16 code units, and code that stays dead text in files.

The Language Server Protocol is the textbook M×N example: M editors and N languages need M×N plugins, or M+N with a shared protocol in the middle. matklad (author of rust-analyzer) argues in [*Why LSP?*](https://matklad.github.io/2022/04/25/why-lsp.html) that this explanation is wrong. The glue code was never the expensive part:
> To sum the above succinctly, the problem with decent IDE support was not of N * M, but rather of an inadequate equilibrium of a two-sided market.

> The total amount of work is almost irrelevant, the thing that matters is the amount of coordination to get things done.

That is Moxie's point again, from the other side. A waist that wins is hard to change because so many parties would have to agree. A missing waist is hard to create for the same reason.

What did LSP choose as its waist? Not a shared model of code. matklad again, in [*LSP could have been better*](https://matklad.github.io/2023/10/12/lsp-could-have-been-better.html), calls this choice genius:
> It just doesn't provide a semantic model of the code base. Instead, it is focused squarely on the presentation. No matter how different each programming language is, they all, in the end, use the same completion widget.

A common model of "files, variables, functions, classes" would be the Right Thing, and a treacherous one, because every language is weird in its own way. LSP standardizes what the completion popup shows, and leaves what the code *means* to each server. This is the same move as OAuth, which standardizes how a token moves, and leaves what it means to the resource server.

The `typeof null` of LSP is its position encoding. Columns are counted in UTF-16 code units, which is how JavaScript strings work, and LSP grew out of VS Code. matklad's verdict: "This is, like, 'no'." Version 3.17 of the [spec](https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/) lets clients and servers negotiate UTF-8 instead, but:
> To stay backwards compatible the only mandatory encoding is UTF-16

The Right Thing lost here too. matklad notes that the Dart Analysis Protocol "predates LSP and is technically superior in some aspects."

But the deeper waist is the one underneath LSP: source code as text files. Gilad Bracha has argued for years that this is the wrong abstraction. From [*Nail Files*](https://gbracha.blogspot.com/2010/02/nail-files.html):
> What I am saying is that your data - including but not limited to program code - should be viewed in a structured, searchable, semantically meaningful form. Not text files, not byte streams, but (collections of) objects.

Smalltalk did exactly that, decades before LSP. Its IDE worked on live objects, not text, and could change itself while running. Yet in [*Bits of History, Words of Advice*](https://gbracha.blogspot.com/2020/05/bits-of-history-words-of-advice.html), Bracha's own explanation of why Smalltalk lost reads like a list of narrow waists it refused to use:
> Source control. The lack of a conventional syntax meant that Smalltalk code could not be managed with conventional source control systems. [...] In general, saving Smalltalk code in something so mundane as a file was problematic.

> Smalltalk was never a programming language in the traditional sense. It was a holistically conceived programming system.

Holistically conceived is exactly what the Right Thing means. His summary of how it looked to a manager:
> Pay a lot of money to be locked in to slow software that exposes your IP, looks weird on screen and cannot interact well with anything else; it is much easier to maintain and develop though!

Bret Victor makes the same lament in [*The Future of Programming*](https://worrydream.com/dbx/). He gives the talk as if it were 1973, with an overhead projector, and "predicts" the ideas that were already around then: direct manipulation of data instead of coding, goals and constraints instead of procedures, spatial representations instead of a "text dump", and concurrency instead of sequential programs. Sketchpad, NLS, and Smalltalk had all of them. The text file won anyway, because every tool can read it: editors, `grep`, `diff`, `git`, and now LSP. He closes with:
> The most dangerous thought that you can have as a creative person is to think that you know what you're doing.

Bracha opens his Smalltalk post with an older, more resigned quote from Alan Perlis (1978), about trying to convince people to use the more elegant system:
> "Why do you jackasses use these inferior linguistic vehicles when we have something here that's so precious, so elegant, which gives me so much pleasure? How can you be so blind and so foolish?" That debate you'll never win, and I don't think you ought to try.

## References

Worse is better:
- [The Rise of *Worse is Better*](https://www.dreamsongs.com/RiseOfWorseIsBetter.html) — Richard Gabriel's original essay
- [Worse Is Better](https://www.dreamsongs.com/WorseIsBetter.html) — Gabriel's page collecting the essay and his later back-and-forth with himself

Narrow waists:
- [The Internet Was Designed With a Narrow Waist](https://www.oilshell.org/blog/2022/02/diagrams.html) — Andy Chu on narrow waists and O(M × N) vs. O(M + N)
- [Narrow Waists](https://swyx.io/narrow-waists) — swyx's examples, from shipping containers to x86
- [Hourglass model](https://en.wikipedia.org/wiki/Hourglass_model) — overview, including Clark's spanning layer
- [On the Hourglass Model](https://arxiv.org/abs/1607.07183) — Micah Beck's formalization and the deployment scalability tradeoff (Communications of the ACM, 2019)
- [End-to-End Arguments in System Design](https://web.mit.edu/Saltzer/www/publications/endtoend/endtoend.pdf) — Saltzer, Reed, and Clark
- [The Ecosystem is Moving](https://signal.org/blog/the-ecosystem-is-moving/) — Moxie Marlinspike on why federated protocols freeze

Unix and JavaScript:
- [Popularity](https://brendaneich.com/2008/04/popularity/) — Brendan Eich on Scheme, "look like Java", and JavaScript's origins
- [JavaScript: The First 20 Years](https://www.wirfs-brock.com/allen/jshopl.pdf) — Allen Wirfs-Brock and Brendan Eich's HOPL paper, covering the ten-day prototype, `typeof null`, "Don't break the Web", and the ES4 failure
- [ECMAScript Harmony](https://esdiscuss.org/topic/ecmascript-harmony) — Eich's 2008 announcement ending ES4

Networking:
- [Perspective: HTTP is the New Narrow Waist](https://book.systemsapproach.org/e2e/trend.html) — Peterson and Davie on IP as the narrow waist, and the waist moving to HTTP
- [Recursive InterNetwork Architecture](https://en.wikipedia.org/wiki/Recursive_InterNetwork_Architecture) — overview of RINA; the full argument is in John Day's book *Patterns in Network Architecture: A Return to Fundamentals*
- [How Tailscale works](https://tailscale.com/blog/how-tailscale-works) — recovering stable node identity as an overlay on top of IP

OAuth:
- [The OAuth 1.0 Protocol - RFC 5849](https://datatracker.ietf.org/doc/html/rfc5849)
- [The OAuth 2.0 Authorization Framework - RFC 6749](https://datatracker.ietf.org/doc/html/rfc6749)
- [OAuth 2.0 and the Road to Hell](https://gist.github.com/nckroy/dd2d4dfc86f7d13045ad715377b6a48f) — Eran Hammer's resignation post ([original](https://hueniverse.com/oauth-2-0-and-the-road-to-hell-8eec45921529))
- [Proof Key for Code Exchange - RFC 7636](https://datatracker.ietf.org/doc/html/rfc7636)
- [OpenID Connect Core 1.0](https://openid.net/specs/openid-connect-core-1_0.html)
- [Best Current Practice for OAuth 2.0 Security - RFC 9700](https://datatracker.ietf.org/doc/html/rfc9700)
- [The OAuth 2.1 Authorization Framework (draft)](https://datatracker.ietf.org/doc/draft-ietf-oauth-v2-1/)
- [Grant Negotiation and Authorization Protocol (GNAP) - RFC 9635](https://datatracker.ietf.org/doc/html/rfc9635)

Authorization credentials:
- [SPKI Certificate Theory - RFC 2693](https://datatracker.ietf.org/doc/html/rfc2693)
- [Macaroons: Cookies with Contextual Caveats](https://static.googleusercontent.com/media/research.google.com/en/us/pubs/archive/41892.pdf)
- [Biscuit](https://www.biscuitsec.org/)
- [API Tokens: A Tedious Survey](https://fly.io/blog/api-tokens-a-tedious-survey/) — Thomas Ptacek on token formats, from random strings to macaroons and biscuits

Programming environments:
- [Why LSP?](https://matklad.github.io/2022/04/25/why-lsp.html) — matklad on why the M×N story is wrong, and the two-sided market LSP actually fixed
- [LSP could have been better](https://matklad.github.io/2023/10/12/lsp-could-have-been-better.html) — matklad on LSP's presentation-level design, UTF-16 columns, and the Dart Analysis Protocol
- [Language Server Protocol Specification 3.17](https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/)
- [Nail Files](https://gbracha.blogspot.com/2010/02/nail-files.html) — Gilad Bracha against files as a representation of code
- [Bits of History, Words of Advice](https://gbracha.blogspot.com/2020/05/bits-of-history-words-of-advice.html) — Bracha on why Smalltalk didn't take over the world
- [Dynamic IDEs for Dynamic Languages!](https://gbracha.blogspot.com/2008/11/dynamic-ides-for-dynamic-languages.html) — Bracha on live IDEs that can change themselves while running
- [The Future of Programming](https://worrydream.com/dbx/) — Bret Victor's 2013 talk, with his references to Sketchpad, PLANNER, NLS, and Smalltalk
