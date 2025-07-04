---
title:  Config As DSL Code: are we there yet?
category: programming
date:   2025-07-04
---

# Config As DSL Code: are we there yet?

[![image](https://hackmd.io/_uploads/r1ibBSg9Jg.png)](https://x.com/mipsytipsy/status/1184673208491864064)

The 12 factor app approach has taught a generation of programmers to maintain [strict separation of config from code](https://12factor.net/config). It even further prescribed apps to keep their config as simple env var key-value pairs!

That approach might have worked for simple heroku web-apps of the day, but single namespaced flat config file is clearly not the right way to manage large scale systems.

We're in 2025, and misconfiguration is still the [largest source of production large-scale bugs](https://danluu.com/postmortem-lessons/). Rust is the future of safe programming, so clearly there's a way to do similar with config languages... right?

## Config Complexity Clock

As a system grows, typically so does its configuration: see google chrome's [1400 CLI flags](https://peter.sh/experiments/chromium-command-line-switches/). Most seasoned devops engineers are likely familiar with the [configuration complexity clock](https://mikehadlow.blogspot.com/2012/05/configuration-complexity-clock.html); if not by name then definitely by concept.

![image](https://hackmd.io/_uploads/HkKvQpzmgg.png)

In my experience, projects typically progress in the following manner (rules engine are not a thing in 2025):
1. magic numbers in code
2. magic numbers become named consts
3. consts turned into configurable variables, ingested via flags, env-vars, or a flat config-file
4. config values grouped into categories using key prefixes
5. flat config turned to json for hierarchical namespacing
6. json converted to proper hierarchical config format ([yaml, toml, hcl](https://www.youtube.com/watch?v=PJyQRWDMlKs)) as some dev gets tired of not having comments (json is a data transport format; not a config language)

Most projects would be better off stopping the pendulum at this 6 o'clock position, and spend their time on more meaningful and useful things. However, every team contains a mid-curved smarty pants engineer who doesn't have anything better to do during weekends than to typify his project's config for UlTiMaTe SaFeTy. Upon facing the 1K LoC PR on monday morning, his project lead turns to the [grug brain manifesto](https://grugbrain.dev/) for advise and a quick rebuttal, but to his big dismay realizes grug completely forgot to advise against the config complexity demon spirit. He is, begrudgingly, forced to accept the PR. And thus typically describes how most projects eventually do enter the DSL config pendulum, which we describe below. Most get forever stuck in this phase, oscillating between extremely complex solutions that each have tradeoffs, with neither having yet matured to a scale of industry wide adoption.

## DSL Config Pendulum

> If the devil is in the details, then make sure to have as few details as possible.

![image](https://hackmd.io/_uploads/SkzFA6fQgx.png)

The config pendulum swings back and forth, in a never ending smooth perpetual motion, driven by the incessant unpleasedness of programmers, and the search for a tool to solve all devops issues. One example progression would evolve as:

7. read borg paper, listen to [signals and threads](https://signalsandthreads.com/building-a-functional-email-server/), move config to same language as code
8. read google SRE book's [pitfall #5](https://sre.google/workbook/configuration-specifics/#pitfall-5-using-an-existing-general-purpose-scripting-language-like-python-ruby-or-lua), realize turing-completeness is bad, move to starlark (to remain in imperative language)
9. miss having types, move to [KCL](https://www.kcl-lang.io/docs/user_docs/getting-started/intro#vs-starlark)
10. get bitten by inheritance; gives up on types and tries the SRE book's suggestion to use Jsonnet
12. gets hurt by runtime misconfiguration bugs, realizes doesn't have google level of tooling and testing, move to typed [nickel](https://github.com/tweag/nickel/blob/master/RATIONALE.md#jsonnet-vs-nickel)
13. want dependent types to encode security guarantees between code and config, move to dhall
14. realize a very small subset of dependent types (lattices containing both values and types) might be the holy grail, move to CUE
15. miss programming language level of tooling, return to 7

## Configuration Data vs Configuration Language

The goal of this article is not to go into deep detail about any of the complex languages listed above, but rather to help the reader develop a framework for realizing how closely related each of them are, and how they are trying to solve a similar problem.

Following the SRE book's [configuration design](https://sre.google/workbook/configuration-design/) chapter, a system is composed of:
1. **code**, which is parameterized by
2. **configuration data**, and processes
3. **user data** (input -> output)

![image](https://hackmd.io/_uploads/BypGnemmgg.png)

The languages above are all "configuration languages", which can effectively be thought of as different ways to (safely!) generate configuration data (json, yaml, )

The "Borg, Omega, and Kubernetes" paper also argues
> [...] configuration management systems tend to invent a domain-specific configuration language that (eventually) becomes Turing complete, starting from the desire to perform computation on the data in the configuration (e.g., to adjust the amount of memory to give a server as a function of the number of shards in the service). The result is the kind of inscrutable “configuration is code” that people were trying to avoid by eliminating hard-coded parameters in the application’s source code. It doesn’t reduce operational complexity or make the configurations easier to debug or change; it just moves the computations from a real programming language to a domain-specific one, which typically has weaker development tools such as debuggers and unit test frameworks. We believe the most effective approach is to accept this need, embrace the inevitability of programmatic configuration, and maintain a clean separation between computation and data.

The above quote describes option 7 in the pendulum. However, many authors of that paper have moved on from that perspective, and swung back to the config DSL approach. Marcel van Lohuizen, who was on the initial Bord team, created GCL, and more recently CUE, argues using the below diagram for why full fledged programming languages shouldn't be used to generate configuration data:
![image](https://hackmd.io/_uploads/Byma4HxcJe.png)

## Cue

Cue's main value proposition is outlined by its creator in [this answer](https://github.com/cue-lang/cue/discussions/669#discussioncomment-959886).

TLDR is that Cue is a logic constraint-based language, where constraints are types and are in the same lattice as values. Its the formalization of safe [config data composition](https://github.com/cue-lang/cue/discussions/669#discussioncomment-13273463).

![image](https://hackmd.io/_uploads/S1uCNQ7Xex.png)



## Conclusion

TODO

## Appendix

Here we explore in more details some niche topics.

### Kurtosis

TODO: describe how kurtosis' [reasoning for using starlark](https://docs.kurtosis.com/advanced-concepts/why-kurtosis-starlark/) doesn't make sense, because unlike bazel, which uses starlark as its ONLY config language. kurtosis doesn't actually use starlark as a config language. It uses it as a programming language, which uses yaml for its config language. They also link to this [tektoncd answer](https://github.com/tektoncd/experimental/issues/185#issuecomment-535338943) which mentions using starlark to generate yaml, which is yet another way of using starlark which is completely different from what kurtosis is doing (they don't generate yaml which is consumed by k8s, they directly call dockerd/k8s-server).

test/cicd case is the most important. docker/docker-compose is prob not flexible enough (??? still don't have a CLEAR reason why), and k8s/control-plane based systems are too slow/inflexible. A cicd test needs to imperatively cause certain changes to happen, in a CAUSAL graph. That would be hard to reproduce with k8s/helm. One would need to anyways have all the different end-states as yaml files, and then apply them one after the other. But because the controllers work asynchronously, one would need to poll the state after every apply before sending the next state request (I think kurtosis prob does something like this when using k8s backend??).

So instead, kurtosis uses Starlark to DEFINE PLANS (!!!) imperatively. One can view the starlark code as parameterized plans (parameterized by the yaml input file). This makes it very easy to create a bunch of test scenarios.


Note that there is always an imperative aspect to every declarative model: https://itnext.io/configuration-editing-is-imperative-fa9db379fbe4. Kurtosis decides to define the plan imperatively, instead of only creating end-states imperatively and letting a control-plane create the plane to resolve the diff.


### Turing Incompleteness

Often touted as a benefit, famous examples are:
- Starlark
- CUE
- Dhall (though see [this](https://www.haskellforall.com/2020/01/why-dhall-advertises-absence-of-turing.html) for why turing incompleteness is not restrictive enough)

TODO: compare this to [every simple (config) language will eventually end up turing complete](https://solutionspace.blog/2021/12/04/every-simple-language-will-eventually-end-up-turing-complete/).

### One Config Language: Many Systems

Surprisingly, the same typed "json with functions" DSLs can be used for different stages of application management:
1. Infra deployment (IaC): terraform HCL
2. System Package Manager (find dependencies): nix
    - language package managers tend to use simple package:version key:value pairs + SAT solver
3. Build System (make, bazel)
4. CICD/Integration-Testing: GHA, dagger, kurtosis
5. App deployment (k8s yaml, kustomize, jsonnet, etc)
6. App config itself (this article)
7. Orchestration: Workflow (code) vs AWS Step (json data)


### Nix is also declarative

> Rather than having specific builtin language constructs for these notions, the language of Nix expressions is a simple functional language for computing with sets of attributes.
https://edolstra.github.io/pubs/nspfssd-lisa2004-final.pdf

This was the theory in the original Nix paper. However in practice nowadays, what we see is (from this [article](https://www.haskellforall.com/2022/03/the-hard-part-of-type-checking-nix.html))
![image](https://hackmd.io/_uploads/BkRlbYzoJg.png)


## References

- https://www.youtube.com/watch?v=PJyQRWDMlKs
- https://sre.google/workbook/configuration-design/
- https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/44843.pdf
- https://www.domenkozar.com/2014/03/11/why-puppet-chef-ansible-arent-good-enough-and-we-can-do-better/
- https://www.usenix.org/legacy/events/lisa2002/tech/full_papers/hart/hart_html/
- https://github.com/tweag/nickel?tab=readme-ov-file#comparison
- https://news.ycombinator.com/item?id=27511514
