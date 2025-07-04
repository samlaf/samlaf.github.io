---
title:  "Config As DSL Code: are we there yet?"
category: programming
date:   2025-07-04
---

The 12 factor app approach has taught a generation of programmers to maintain [strict separation of config from code](https://12factor.net/config). Twenty odd years later, it's not unusual to see teams pushing codes via CICD pipelines, yet hot reload their config files in production. Yet, config related bugs are still the [most important source of production large-scale bugs](https://danluu.com/postmortem-lessons/), which is why some people argue that config should be treated as code.

[![image](https://hackmd.io/_uploads/r1ibBSg9Jg.png)](https://x.com/mipsytipsy/status/1184673208491864064)

In this article we plan to explore some of the reasoning behind this, and explore alternative approaches that keep the config as data. The past few years have seen a surge in config DSLs, which we will explore in the [DSL Config Pendulum](#dsl-config-pendulum) section. While many different approaches have been proposed, we will argue that CUE might be the Rust of config languages.

## Config Complexity Clock

As a system grows, typically so does its configuration: see google chrome's [1400 CLI flags](https://peter.sh/experiments/chromium-command-line-switches/). The [Configuration Complexity Clock](https://mikehadlow.blogspot.com/2012/05/configuration-complexity-clock.html) is a famous narration of this phenomenon.

![image](https://hackmd.io/_uploads/HkKvQpzmgg.png)

In my experience, projects typically progress in the following manner (rules engines are not a thing in 2025):
1. Magic numbers in code
2. Magic numbers become named consts
3. Consts turned into configurable variables, ingested via flags, env-vars, or a flat config-file
4. Config values grouped into categories using key prefixes
5. Flat config turned to JSON for hierarchical namespacing
6. JSON converted to proper hierarchical config format ([YAML, TOML, HCL](https://www.youtube.com/watch?v=PJyQRWDMlKs)) as some dev gets tired of not having comments (JSON is a data transport format; not a config language)

Most projects would be better off stopping the pendulum at this 6 o'clock position, and spend their time on more meaningful and useful things. However, every team contains an overzealous teammate who doesn't have anything better to do during weekends than to typify his project's config for UlTiMaTe SaFeTy. Upon facing the 1K LoC PR on Monday morning, his project lead turns to the [grug brain manifesto](https://grugbrain.dev/) for advice and a quick rebuttal, but to his dismay realizes grug completely forgot to advise against the config complexity demon spirit. He is, begrudgingly, forced to accept the PR. And thus typically describes how most projects eventually do enter the DSL config pendulum, which we describe below. Most get forever stuck in this phase, oscillating between extremely complex solutions that each have trade-offs, with neither having yet matured to a scale of industry wide adoption.

## DSL Config Pendulum

> If the devil hides in the details, then make sure to have as few details as possible.

![image](https://hackmd.io/_uploads/SkzFA6fQgx.png)

The config pendulum swings back and forth, in a never ending smooth perpetual motion, driven by the incessant dissatisfaction of programmers, and the search for a tool to solve all DevOps issues. One example progression would evolve as:

<ol start="7">
<li>read Borg paper, listen to <a href="https://signalsandthreads.com/building-a-functional-email-server/">signals and threads</a>, move config to same language as code</li>
<li>read Google SRE book's <a href="https://sre.google/workbook/configuration-specifics/#pitfall-5-using-an-existing-general-purpose-scripting-language-like-python-ruby-or-lua">pitfall #5</a>, realize Turing-completeness is bad, move to Starlark (to remain in imperative language)</li>
<li>miss having types, move to <a href="https://www.kcl-lang.io/docs/user_docs/getting-started/intro#vs-starlark">KCL</a></li>
<li>get bitten by inheritance; gives up on types and tries the SRE book's suggestion to use Jsonnet</li>
<li>gets hurt by runtime misconfiguration bugs, realizes doesn't have Google level of tooling and testing, move to typed <a href="https://github.com/tweag/nickel/blob/master/RATIONALE.md#jsonnet-vs-nickel">nickel</a></li>
<li>want dependent types to encode security guarantees between code and config, move to Dhall</li>
<li>realize a very small subset of dependent types (lattices containing both values and types) might be the holy grail, move to CUE</li>
<li>miss programming language level of tooling, return to 7</li>
</ol>

## Configuration Data vs Configuration Language

The goal of this article is not to go into deep detail about any of the complex languages listed above, but rather to help the reader develop a framework for realizing how closely related each of them are, and how they are trying to solve a similar problem.

Following the SRE book's [configuration design](https://sre.google/workbook/configuration-design/) chapter, a system is composed of:
1. **code**, which is parameterized by
2. **configuration data**, and processes
3. **user data** (input -> output)

![image](https://hackmd.io/_uploads/BypGnemmgg.png)

The config DSL languages above are all "configuration languages", which can effectively be thought of as different ways to (safely!) generate configuration data (JSON, YAML, etc.), which itself is ingested by the code using a simple parser.

The need for this separation between the Configuration Language and the Configuration Data is explained in the [Configuration Design](https://sre.google/workbook/configuration-design/) chapter of the SRE book:
> To answer the age-old question of whether configuration is code or data, our experience has shown that having both code and data, but separating the two, is optimal. The system infrastructure should operate on plain static data, which can be in formats like Protocol Buffers, YAML, or JSON. This choice does not imply that the user needs to actually interact with pure data. Users can interact with a higher-level interface that generates this data. This data format can, however, be used by APIs that allow further stacking of systems and automation.

## Configuration Language vs Code Language

The first thought of smart developers after realizing that a Configuration Language is needed to generate configuration data, is to reuse the same programming language they use to write their code. This is in fact what Jane Street did by rewriting their [functional email server](https://signalsandthreads.com/building-a-functional-email-server) config in OCaml. The [Borg, Omega, and Kubernetes](https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/44843.pdf) paper similarly argues that:

> [...] configuration management systems tend to invent a domain-specific configuration language that (eventually) becomes Turing complete, starting from the desire to perform computation on the data in the configuration (e.g., to adjust the amount of memory to give a server as a function of the number of shards in the service). The result is the kind of inscrutable “configuration is code” that people were trying to avoid by eliminating hard-coded parameters in the application’s source code. It doesn’t reduce operational complexity or make the configurations easier to debug or change; it just moves the computations from a real programming language to a domain-specific one, which typically has weaker development tools such as debuggers and unit test frameworks. We believe the most effective approach is to accept this need, embrace the inevitability of programmatic configuration, and maintain a clean separation between computation and data.

This represents option 7 in the pendulum. However, many authors of that paper have moved on from that perspective, and swung back to the config DSL approach, for 2 reasons:

### 1. Too powerful

Power might seem like a good thing, but more power comes at the cost of [fewer properties](https://www.tedinski.com/2018/01/30/the-one-ring-problem-abstraction-and-power.html), which means possibly nondeterministic, hard to reason about and debug code.

Some argue that anyways [Every simple (config) language will eventually end up Turing Complete](https://solutionspace.blog/2021/12/04/every-simple-language-will-eventually-end-up-turing-complete/), but Turing Completeness is the [wrong property](https://www.haskellforall.com/2020/01/why-dhall-advertises-absence-of-turing.html).

In fact, the author even accepts that:
> This is not a universal strategy of course. SQL may be a valid counterexample. Well, SQL with recursive common table expressions is actually Turing complete, so it should probably be counted as an instance of the law I propose. Nevertheless, SQL really benefits from the ability to run static analysis so there would be value in sacrificing expressivity.

### 2. Readability

Marcel van Lohuizen, who was on the initial Borg team, created GCL, and more recently CUE, argues using the below diagram for why full-fledged programming languages shouldn't be used to generate configuration data:

![image](https://hackmd.io/_uploads/Byma4HxcJe.png)

## JSON with functions and types

Apart from Starlark, which is quite different from the other languages, most of the config DSLs can be thought of as [JSON with functions](https://nix.dev/tutorials/nix-language.html#attribute-set), and some with types.

## CUE: A Different Approach

CUE represents a fundamentally different approach to configuration management. Rather than being a traditional programming language or a simple data format, CUE is a constraint-based language where types and values exist in the same mathematical lattice.

The key insight behind CUE is that configuration should be about declaring constraints and relationships, not imperative computation. In CUE, you define what valid configurations look like, and the language ensures your actual configuration data satisfies those constraints.

This approach addresses several fundamental problems with traditional config approaches:

**Type Safety**: Unlike YAML or JSON, CUE catches type errors and constraint violations at validation time, not at runtime when your service fails to start.

**Composability**: CUE's lattice-based model allows you to safely merge and compose configurations from multiple sources without conflicts or ambiguity.

**Gradual Typing**: You can start with loose constraints and gradually tighten them as your understanding of the system evolves, without breaking existing configurations.

The creator's [main value proposition](https://github.com/cue-lang/cue/discussions/669#discussioncomment-959886) is that CUE formalizes safe [config data composition](https://github.com/cue-lang/cue/discussions/669#discussioncomment-13273463) - something that's been done ad-hoc in YAML templating and JSON merging for years, but never with mathematical rigor.

![image](https://hackmd.io/_uploads/S1uCNQ7Xex.png)



## Conclusion

TODO

## Appendix: Config Language DSL for Other Systems

Surprisingly, the debate between full-fledged PL vs DSL appears in all stages of application management:
1. Infra deployment (IaC): pulumi vs terraform HCL
2. System Package Manager (find dependencies): nix vs ??
    - language package managers tend to only use simple data directly in the form of package:version key:value pairs + SAT solver
3. Build System: make vs bazel (no full-blown PL in this category??)
4. CICD/Integration-Testing: dagger vs GHA / kurtosis
5. App deployment: k8s yaml, kustomize, jsonnet (no full-blown PL in this category??)
6. App config itself (this article)
7. Orchestration: Workflow (code) vs AWS Step (json data)

<!-- Commented out because although interesting, it diverts from the main goal of the article,
and it's also not so clear anymore that kurtosis is describing something wrong... it just doesn't fall
in the same category of application configuration language. Its a CICD/dag defining language, similar
to dagger (see CICD category in "One Config Language: Many Systems" section above) -->

<!-- ### Kurtosis uses Starlark for Imperative CICD plans (similar to Dagger)

TODO: describe how kurtosis' [reasoning for using starlark](https://docs.kurtosis.com/advanced-concepts/why-kurtosis-starlark/) doesn't make sense, because unlike bazel, which uses starlark as its ONLY config language. kurtosis doesn't actually use starlark as a config language. It uses it as a programming language, which uses yaml for its config language. They also link to this [tektoncd answer](https://github.com/tektoncd/experimental/issues/185#issuecomment-535338943) which mentions using starlark to generate yaml, which is yet another way of using starlark which is completely different from what kurtosis is doing (they don't generate yaml which is consumed by k8s, they directly call dockerd/k8s-server).

test/cicd case is the most important. docker/docker-compose is prob not flexible enough (??? still don't have a CLEAR reason why), and k8s/control-plane based systems are too slow/inflexible. A cicd test needs to imperatively cause certain changes to happen, in a CAUSAL graph. That would be hard to reproduce with k8s/helm. One would need to anyways have all the different end-states as yaml files, and then apply them one after the other. But because the controllers work asynchronously, one would need to poll the state after every apply before sending the next state request (I think kurtosis prob does something like this when using k8s backend??).

So instead, kurtosis uses Starlark to DEFINE PLANS (!!!) imperatively. One can view the starlark code as parameterized plans (parameterized by the yaml input file). This makes it very easy to create a bunch of test scenarios.

Note that there is always an imperative aspect to every declarative model: https://itnext.io/configuration-editing-is-imperative-fa9db379fbe4. Kurtosis decides to define the plan imperatively, instead of only creating end-states imperatively and letting a control-plane create the plane to resolve the diff. -->


## References

- [https://www.youtube.com/watch?v=PJyQRWDMlKs](https://www.youtube.com/watch?v=PJyQRWDMlKs)
- [https://sre.google/workbook/configuration-design](https://sre.google/workbook/configuration-design)
- [https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/44843.pdf](https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/44843.pdf)
- [https://www.domenkozar.com/2014/03/11/why-puppet-chef-ansible-arent-good-enough-and-we-can-do-better](https://www.domenkozar.com/2014/03/11/why-puppet-chef-ansible-arent-good-enough-and-we-can-do-better)
- [https://www.usenix.org/legacy/events/lisa2002/tech/full_papers/hart/hart_html](https://www.usenix.org/legacy/events/lisa2002/tech/full_papers/hart/hart_html)
- [https://github.com/tweag/nickel?tab=readme-ov-file#comparison](https://github.com/tweag/nickel?tab=readme-ov-file#comparison)
- [https://news.ycombinator.com/item?id=27511514](https://news.ycombinator.com/item?id=27511514)
