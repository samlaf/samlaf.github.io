---
title:  "Anti-Modularity in Software Systems"
category: programming
---

If you ask programmers whether modularity is good, you'll likely only hear "yes" answers. However, there are many places where anti-modularity is explicitly chosen, and the goal of this article is just to list the few interesting anti-modular use cases that I have come across over the years.

The keyword I use throughout the article is GLOBAL, since using anti-modular techniques often means the programmer has to think through global program properties, which is sometimes deemed an acceptable tradeoff.

## What is Modularity?

Before looking at anti-modularity, let's first tackle what modularity means.

> Modularity is the degree to which a system's components may be separated and recombined, often with the benefit of flexibility and variety in use. The concept of modularity is used primarily to reduce complexity by breaking a system into varying degrees of interdependence and independence across and "hide the complexity of each part behind an abstraction and interface".
> -- Wikipedia


So modularity is about breaking up programs into "modules" and recombining them flexibly. I won't go into very much more detail, but strongly recommend reading Tedinski's [Breaking systems into modules](https://www.tedinski.com/2018/08/14/modularity.html), as well as Parnas' original article [On the Criteria To Be Used in Decomposing Systems into Modules](https://wstomv.win.tue.nl/edu/2ip30/references/criteria_for_modularization.pdf).

## Manual Memory Management

As matklad [writes](https://matklad.github.io/2023/03/26/zig-and-rust.html):
> To be a bit snarky, while Rust “is not for lone genius hackers”, Zig … kinda is. On more peaceable terms, while Rust is a language for building modular software, Zig is in some sense **anti-modular**.
> 
> It’s appropriate to quote Bryan Cantrill here:
> > I can write C that frees memory properly…that basically doesn’t suffer from memory corruption…I can do that, because I’m controlling heaven and earth in my software. It makes it very hard to compose software. Because even if you and I both know how to write memory safe C, it’s very hard for us to have an interface boundary where we can agree about who does what.
> 
> That’s the core of what Rust is doing: it provides you with a language to precisely express the contracts between components, such that components can be integrated in a machine-checkable way.
> 
> Zig doesn’t do that. It isn’t even memory safe.

So rust is more modular than other system programming languages that do manual memory management (c and zig) because its compiler is checking the GLOBAL safety of your programs for you.

## Haskell/Rust Typeclasses vs OCaml Modules

Functional programmers will spend a lot of effort arguing that FP is the best, [most modular](https://www.cs.kent.ac.uk/people/staff/dat/miranda/whyfp90.pdf), most effective programming technique, with their [monads and effects](https://just-bottom.blogspot.com/2010/04/programming-with-effects-story-so-far.html) being the perfect **compositional** syntax to combine their parts. And they might have a point, since modules are useless if they can't effectively and flexibly be recomposed.

However, Bob Harper [argues](https://existentialtype.wordpress.com/2011/04/16/modules-matter-most/) that Haskell's typeclasses (and Rust traits which are very similar) are in fact... anti-modular. For those who don't have a PhD in PL, Bob Harper is very hard to read. Jimmy Koppel wrote an extended explainer [for the masses](https://www.pathsensitive.com/2023/03/modules-matter-most-for-masses.html). 

And others have expressed similar ideas. Here is rust creator Graydon Hoare in his article [The Rust I Wanted Had No Future](https://graydon2.dreamwidth.org/307291.html):
> I generally don't like traits / typeclasses. To my eyes they're too type-directed, too **GLOBAL**, too much like programming and debugging a distributed set of invisible inference rules, and produce too much coupling between libraries in terms of what is or isn't allowed to maintain coherence. I wanted (and got part way into building) a first class module system in the ML tradition. Many team members objected because these systems are more verbose, often painfully so, and I lost the argument. But I still don't like the result, and I would probably have backed the experiment out "if I'd been BDFL".

Leo White, who works on the Compiler team at Jane Street (famous OCaml shop), argues similarly on Ron Minsky's podcast Signals And Threads:
> Operator overloading, is a mechanism that gives you ad-hoc polymorphism. So, I would say that type classes were a major breakthrough in ad-hoc polymorphism, and they’re still kind of the gold standard to measure your ad-hoc polymorphism features against, but it’s a very kind of, **anti-modular** feature. So, let’s say, you want an addition function and so you define an addition type class, and then you decide that you want it to work on integers, so you have to, somewhere in your program, write “this is how addition works on integers,” and the important thing there is that it really has to be, just in the entire program, for type class to work, there has to be just one place where you’ve written, this is how addition works on integers.
> 
> And so, if you have one library that’s written an addition instance over here, and another one that written another addition instance, you will not be able to link them together. And it’s kind of **anti-modular**, because you don’t notice this problem until you get to link time. Like you try to link them together and it says, “Oh, no, those two bits have to live in separate worlds. They can’t combine like this. You have kind of **broken some of the compositionality** of your language.”

## Types and Compilation Units

Gilad Bracha succinctly [summarizes](https://gbracha.blogspot.com/2011/06/types-are-anti-modular.html) his position:
> Types are inherently non-local - they describe data that flows across module boundaries. The absence of types won’t buy you modularity on its own though. Far from it. But types and typechecking act as an inhibitor - a **countervailing force to modularity**.

His argument is related to modular compilation units:
> The specific point I was discussing when I made this comment was the distinction between separate compilation and independent compilation. Separate compilation allows you to compile parts of a program separately from other parts. I would say it was a necessary, but not sufficient, requirement for modularity.

Funnily enough, even OCaml, with its "perfect" modules (see section above), still falls pray to this critique:
> The situation is better if the language supports separate signature declarations (like Modula-3 or **ML**) - but you still have to have these around before you compile.
> [...]
> The problem is that inference only works well within a module (if that). If you rely on inference at module boundaries, your module leaks implementation information. Why? Because if you infer types from your implementation, those types may vary when you modify your implementation. That is why, even in **ML**, signatures are declared explicitly.

## Protocol Design

Vitalik talks about [encapsulated vs systemic complexity in protocol design](https://vitalik.eth.limo/general/2022/02/28/complexity.html) and gives many examples where some complexity can be completely black-boxed and presented as a simple API with certain properties. This kind of modularity greatly helps reduce the search space when creating new protocols.

He gives an example that is very dear to my heart, having worked on optimistic BFT protocols at Eigenlayer. Cryptography vs cryptoeconomics:
> But while ZK-SNARKs are complex, their complexity is encapsulated complexity. The relatively light complexity of fraud proofs, on the other hand, is systemic. [...] For these reasons, even from a complexity perspective purely cryptographic solutions based on ZK-SNARKs are likely to be long-run safer: ZK-SNARKs have are more complicated parts that some people have to think about, but they have fewer dangling caveats that everyone has to think about.

The so-called blockchain [modular thesis](https://www.galaxy.com/insights/research/making-sense-of-blockchain-modularity), in my opinion doesn't scale for this very reason. Stripe completely hides the complexity of payment processing behind a simple REST API. BFT "layers", on the other hand, cannot do so, and force anyone integrating with them to understand their entire system in order to guarantee byzantine resistance. That is, byzantine resistance using optimistic/fraud proof based methods, require GLOBAL thinking.

## Optimization

This one is not so much about modularity but more so about GLOBAL vs LOCAL optimization, which seemed related enough to include.

Dynamic programming's "optimal substructure" property effectively allows breaking a global search problem into "modular" subproblems.

Most search problems don't have this kind of nice "modular" structure however. Nonconvex optimization, for example, is NP-hard. Nevertheless, interestingly, we can [very often](https://www.youtube.com/watch?v=OiOrJbUtvCc) apply heuristic/greedy algorithms to get very reasonable solutions.

That is, we can do well without searching the entire GLOBAL space.