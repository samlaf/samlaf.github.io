---
title:  "Hyperproperties"
series: "Keys, names and authority, Epilogue"
series_url: "/programming/keys-names-authority.html"
category: programming
date: 2026-06-03 12:00:00
---

> This is the epilogue to three series: [applied cryptography](/programming/crypto-series-intro.html), [identity](/programming/identity-series-intro.html) and [authorization](/programming/authorization-series-intro.html). The [prologue](/programming/threat-model.html) asked where the adversary lives. This one asks what kind of guarantee can stop them. The [map](/programming/keys-names-authority.html) shows how the series fit together.

- [Two doors](#two-doors)
- [One run, or several](#one-run-or-several)
- [Why a monitor cannot see a flow](#why-a-monitor-cannot-see-a-flow)
- [The context window](#the-context-window)
- [Where type systems land](#where-type-systems-land)
- [CIA is not a classification](#cia-is-not-a-classification)
- [Back to the three series](#back-to-the-three-series)

Every check in the three series looks at one event. A signature verifies or it does not. A token is valid or it is not. A reference monitor lets this call through or stops it. Each check judges one thing that happened, in one run of one program.

Some guarantees cannot be stated that way. Take "the report does not reveal the salary file." The report might contain a number that happens to match a salary. Whether it *reveals* one depends on what the report would have said if the salary had been different. That is a claim about two runs, not one.

[Clarkson and Schneider][hyperproperties] named such guarantees *hyperproperties*. The name comes with a map. Almost everything in the three series sits in one corner of it, and the prologue's last adversary, the data an agent reads, sits in another.

## Two doors

![Three panels, each a process that reads a secret file and a public forecast and sends two messages on a public network. With access control only, both doors allow the requests and the secret leaks. With coarse information flow control, the process takes the secret label and both messages are blocked. With fine information flow control, each value carries its own label, so only the report built from the secret is blocked.](/assets/series/hyperproperties/two-doors.svg)

A process reads a secret file and sends messages on a public network. Access control asks the same question at each door: who is asking? May this process read the file? May it send on the network? Both answers can be yes, and the secret still walks out. Neither question looked at what the message was made of.

Information flow control (IFC) asks a different question at the exit: what is this output made of? [Sabelfeld and Myers][sabelfeld-myers] open their survey of the field with this split. Access control governs *release*: whether a request may happen. IFC governs *propagation*: where information may go once it has been released.

There are two ways to answer IFC's question.

**Coarse: the process takes the label.** Weissman's ADEPT-50 (1969) gave each job a [high-water mark][high-water-mark]: the highest classification it had opened so far, which also labelled what it wrote. [Bell and LaPadula][blp] (1973) made the same move a rule. A process may not write below its own level, because it may be carrying anything it has read. [Biba][biba] (1977) turned it around for integrity: a process that reads less-trusted data drops to that level, a *low-water mark*. A sandbox with no network gets the same effect by absence, because there is no exit to check. [KeyKOS and EROS][eros-confinement] built confinement from capabilities this way: a confined program starts with no reference that leads out. All of these block the leak, and all of them over-block. Once a process has read one secret, nothing it says counts as public.

**Fine: each value carries its label.** [Denning's lattice model][denning] (1976) gave labels a join: a value computed from two inputs carries both of their labels. [Denning and Denning][denning-certification] (1977) checked programs for bad flows at compile time. [Jif][jif] made that a type system for Java, [SCIF][scif] does it for smart contracts, and [CaMeL][camel] does it for LLM agents. Only what the secret shaped is stopped.

Swap "secret" for "untrusted" and the network for a tool call, and the same picture shows integrity. A prompt injection enters by the door and is judged at the call.

## One run, or several

A *trace* is one run of a system: the sequence of states or events it goes through. A *trace property* is a rule that each run satisfies or breaks on its own. "Every file this process read was allowed by the ACL" is one. To check it, you look at one run.

[Alpern and Schneider][defining-liveness] (1985) split trace properties in two. A *safety* property says a bad thing never happens. Any violation shows up in a finite part of the run, so a monitor can stop the run at that point. A *liveness* property says a good thing eventually happens. No finite part of a run can prove it broken, because the good thing may still come. [Schneider][enforceable-security-policies] later proved that a monitor watching one run can enforce only safety properties. [Part 1](/programming/authorization-models.html#when-the-check-writes) of the authorization series builds on that result.

A *hyperproperty* is a rule about sets of runs. The classic one is *noninterference*, from [Goguen and Meseguer][goguen-meseguer] (1982). In its usual form for programs, it says that any two runs that agree on public inputs also agree on public outputs. No single run can break it. A run that sends "42" is fine, unless another run with the same public inputs and a different secret sends "41". [Terauchi and Aiken][terauchi-aiken] call this *2-safety*: a violation is a pair of finite runs. That also says how to check it. Run two copies of the program side by side and feed them different secrets. Noninterference becomes an ordinary safety property of the pair, a trick [Barthe, D'Argenio and Rezk][self-composition] named *self-composition*.

Put the two splits together and you get Clarkson and Schneider's grid:

| | Safety: a finite run shows the violation | Liveness: no finite run shows it |
| --- | --- | --- |
| **Trace property:** judged on one run | access control; type safety; "no token is spent twice"; the Chinese Wall | termination; "every request is eventually answered" |
| **Hyperproperty:** judged on sets of runs | noninterference; confused-deputy freedom; reentrancy security | generalized noninterference: whatever an observer sees, every secret is still possible |

Every trace property is also a hyperproperty: "every run in the set satisfies it." So the grid is not two separate worlds. The top row is the part of the space where one run is enough to judge.

## Why a monitor cannot see a flow

![Two runs of an agent asked to send meeting notes to Bob. In both, every tool call is allowed. In the second, an email tells the agent to send them to Carol, and it does. Only comparing the runs shows that the recipient changed with untrusted input. Below, information flow control labels the chosen address with the email it was chosen by, and the rule at the tool call blocks it.](/assets/series/hyperproperties/trace-vs-flow.svg)

A reference monitor sees one run. It sees `send_email(to=carol@corp)`, checks it against policy, and lets it through: Carol is a colleague, and her address came back from the calendar. In a second run, with a clean inbox, the agent sends to Bob. Each run passes on its own. The attack exists only between them: the recipient changed when only untrusted input changed. No monitor on one run can see that.

There are two ways around it.

**Check every pair of runs before running.** A type system or static analysis can prove noninterference for all runs at once. That is what Denning and Denning's certification, Jif and SCIF do. The price is annotations, and a program the analysis can follow.

**Make the flow visible inside one run.** Carry labels at runtime, and join them whenever values combine. The monitor at the tool call can then see, in this run, that `to` carries the email's label. Labels turn the hyperproperty back into a trace property, over a richer state. The price is precision. A runtime tracker sees the branch that ran, not the one that did not. In `if secret: send(x)`, the runs that do *not* send leak the secret too. Trackers handle this with a label on the program counter: anything done inside a branch on a secret carries the secret's label.

Distributed databases face the same choice. [Part 1](/programming/authorization-models.html#when-the-check-writes) of the authorization series compares the two: linearizability assumes every later operation may depend on every earlier one, the way a high-water mark does, while causal tokens track only the real dependencies, the way fine labels do. Both fine-grained answers share a blind spot. They see only the dependencies that flow through the system.

## The context window

![Three columns. A program keeps code, data and authority in separate places, so input can fill a hole in a query but never become an instruction. An LLM agent reads its system prompt, the user's request, tool output and an attacker's email as one token stream, and acts with ambient authority. Two fixes split it again: capabilities narrow the authority any call can use, and information flow control labels each part of the stream with its source.](/assets/series/hyperproperties/one-stream.svg)

A program keeps instructions and data apart. A parameterized query fixes the structure of the query first, and input can only fill its holes. Authority sits somewhere else again, in handles the process holds rather than in any text it reads.

An LLM merges the first two. The system prompt, the user's request and an attacker's email arrive as one stream of tokens, and the model decides which of them count as instructions. It is also the worst case for fine labels. Nothing tracks which input tokens shaped which output token, so the only honest label for an output is "everything in the context." That leaves the coarse options: Biba's low-water mark, or Willison's [lethal trifecta][lethal-trifecta] as a rule. Or it means moving the split outside the model. CaMeL's privileged model writes the plan from the user's request alone. A quarantined model with no tools turns untrusted text into values. An interpreter carries a label on each value, up to the tool call.

Capabilities do a different job. They are access control: they bound what any call can reach, whoever asked for it. A task that holds only a handle to mail Bob cannot mail Carol. But within what the task allows, they cannot see a flow. An injection can still make the agent tell Bob the meeting moved. [Part 4](/programming/capabilities.html#prompt-injection-is-a-confused-deputy) of the authorization series argues that the stronger version, designator and authority as one object, is still open for agents, because a model designates with text.

The two compose. Capabilities bound what the agent can reach. Labels decide whose words chose each call. CaMeL uses both.

## Where type systems land

A type system checks a program before it runs, and type systems split along the same line.

- **Affine types**, as in Rust, let each value be used at most once. No double free, no use after move. These are safety trace properties.
- **Linear and session types**, as in Move, Nomos and Obsidian, stop assets from being copied or dropped, and make parties follow a protocol in order. "Total supply is conserved" holds run by run. These are richer trace properties.
- **Integrity labels**, as in SCIF, give noninterference, freedom from confused deputies, and security against reentrancy. These are 2-safety hyperproperties.

The two families check different cells of the grid, and neither covers the other. The [Dexible][dexible] exploit shows the gap. In February 2023, users had approved Dexible's contract to move their tokens. Its `selfSwap` function let the caller name the router to call, and nothing checked the router. The attacker named token contracts instead, and called `transferFrom` on every account that had approved Dexible. About $2 million moved. No token was created or destroyed, and every transfer was covered by an approval. A linear type system has nothing to say about it. It is Hardy's [confused deputy][confused-deputy] again: the attacker supplied the designator, and the contract supplied the authority. An integrity label does catch it. The router address came from an untrusted caller, so it may not choose the target of a trusted call.

Laid out by class, following SCIF's own framing:

| Class | Property | What it says |
| --- | --- | --- |
| Trace property | Access control | Only callers with enough integrity may invoke a method |
| Trace property | Type safety | No type confusion at call boundaries |
| Trace property | Lock discipline | Locks are held around trusted operations |
| Trace property | Failure handling | Every exception is handled, or the transaction rolls back |
| 2-safety | Noninterference (integrity) | Two runs that differ only in untrusted inputs have the same trusted outputs |
| 2-safety | Confused-deputy freedom | Whatever an attacker's callback does, the contract's trusted state changes the same way |
| 2-safety | [Reentrancy security][reentrancy] | A reentrant call during an inconsistent state cannot change the trusted outcome |
| 2-safety, with exceptions | Endorsed noninterference | Noninterference, except at explicit endorsement points |
| Outside SCIF | Availability | Transactions eventually complete, and assets are never frozen for good |
| Outside SCIF | Ordering fairness | The outcome does not depend on how an adversary orders transactions |
| Outside SCIF | Confidentiality of state | Values stay hidden from the public |

None of the four trace properties rules out what happened to Dexible. The 2-safety rows do, but strict noninterference is too strict for real code: a user's chosen amount is untrusted input, and it has to matter. *Endorsement* marks the few places where untrusted input may affect trusted state, so an auditor reads those and nothing else. CaMeL's user confirmations play the same role.

The last three rows are out of reach of labels, for three different reasons. Availability is liveness. Ordering fairness is a hyperproperty whose adversary is the scheduler: it never touches a value, only the order, so there is nothing to label. And confidentiality on a public chain is out of reach because every node replays every run. Computing on secrets there takes cryptography or trusted hardware.

## CIA is not a classification

Security is usually sorted into confidentiality, integrity and availability. That sorting names *what* is protected. The grid names the *shape* of the rule. The two are independent:

- "Only Alice may read the salary file" is confidentiality, and a safety trace property.
- "The report does not depend on the salary file" is confidentiality, and a 2-safety hyperproperty.
- "Every request gets a reply within five seconds" is availability, and a safety property: a missed deadline shows up in a finite run.
- "Every request is eventually answered" is availability, and a liveness property.
- "The mean response time over all runs is under a second" is availability, and a hyperproperty. No single run decides it, and no finite set of runs can break it, since a new batch of fast runs can always pull the mean back down. Clarkson and Schneider call that *hyperliveness*.

Clarkson and Schneider draw the whole space in one figure:

![Clarkson and Schneider's classification of security policies: hyperproperties split into hypersafety on the left, with k-safety and lifted safety properties nested inside it, and hyperliveness on the right, with lifted liveness properties and possibilistic information flow inside it. Example policies sit in each region.](/assets/series/hyperproperties/classification.png)
*Figure 1 of [Hyperproperties][hyperproperties], Clarkson and Schneider.*

HP is every hyperproperty. The left circle, SHP, is hypersafety. Inside it, KSHP(2) is 2-safety, and inside that, KSHP(1) is the ordinary safety properties, lifted. Access control (AC) and "no network write after a file read" (NRW) sit there. 2-safety holds observational determinism (OD) and two forms of noninterference (GMNI, TIRNI). The outer ring holds secret sharing (SecS), a bound on leaked bits (QL<sub>k</sub>), and perfect indistinguishability of an encryption scheme (PI). The right circle, LHP, is hyperliveness. It holds the ordinary liveness properties, such as guaranteed service (GS), and the possibilistic flow policies, such as generalized noninterference (GNI). Mean response time (RT) and channel capacity (CC<sub>k</sub>) sit there too. A few policies are in neither circle, such as probabilistic noninterference (PNI). Every hyperproperty is the intersection of one hypersafety property and one hyperliveness property, just as every trace property is the intersection of a safety property and a liveness property.

Now read the labels against CIA. Confidentiality lands on both sides: OD on the left, GNI on the right. Availability lands in three regions: the five-second deadline above is plain safety, GS is plain liveness, and RT is hyperliveness. The figure has no region for any of the three letters. Clarkson and Schneider conclude:

> The classification of security requirements as confidentiality, integrity, and availability therefore would seem to be orthogonal to hypersafety and hyperliveness. Hypersafety and hyperliveness have the advantages of being formalized and providing an orthogonal basis for constructing security policies. In contrast, there is no formalization that simultaneously characterizes confidentiality, integrity, and availability, nor are confidentiality, integrity, and availability orthogonal.

Their footnote makes the second point concrete: "the requirement that a principal be unable to read a value could be interpreted as confidentiality or unavailability of that value."

## Back to the three series

Each series lands on the grid.

- **Authorization** is almost entirely trace properties. A reference monitor judges one request, and Schneider's result says it can enforce only safety. Part 1's [checks that write](/programming/authorization-models.html#when-the-check-writes) add history, but a history is still one run. Capabilities too: "no reference, no access" is judged run by run. Confinement reaches a hyperproperty only by absence, by leaving no way out.
- **Identity** is trace properties as well. A binding is a fact about one run: this key belonged to this name when the check ran.
- **Applied cryptography** is the exception. Its definitions compare worlds. [IND-CPA](/programming/crypto-primitives.html) asks whether an attacker can tell an encryption of one message from an encryption of another. Clarkson and Schneider place perfect indistinguishability in hypersafety, the PI in their figure, and note that IND-CPA and IND-CCA can be written as hyperproperties the same way. Encryption is how you get a hyperproperty when the adversary sees every run. It makes the public output independent of the secret.

The prologue's positions line up the same way. The wire, the binding and the gate are stated in cryptographic or trace terms. A hostile insider is judged request by request. Positions five and seven are the ones that need hyperproperties.

The 1970s met this in position five. A Trojan horse running as a cleared user could read secrets and write them down, and Bell and LaPadula's rules exist to stop it. They settled for coarse labels, and coarse labels were tolerable, because a military process rarely needed to mix levels. An agent's whole job is to read untrusted text and act on it. A coarse label taints everything it does. That is why the data the delegate reads is the open frontier: the checks we are good at have the wrong shape for it, and the checks with the right shape stop at the model.

## References <!-- omit in toc -->

1. [Hyperproperties - Clarkson and Schneider][hyperproperties]
2. [Language-Based Information-Flow Security - Sabelfeld and Myers][sabelfeld-myers]
3. [High-water mark (computer security) - Wikipedia][high-water-mark]
4. [Bell–LaPadula Model - Wikipedia][blp]
5. [Biba Model - Wikipedia][biba]
6. [Verifying the EROS Confinement Mechanism - Shapiro and Weber][eros-confinement]
7. [A Lattice Model of Secure Information Flow - Denning][denning]
8. [Certification of Programs for Secure Information Flow - Denning and Denning][denning-certification]
9. [Jif: Java + information flow][jif]
10. [SCIF: Smart Contract Information Flow][scif]
11. [A Language for Smart Contracts with Secure Control Flow - Yao, Ni, Myers and Cecchetti][scif-paper]
12. [Compositional Security for Reentrant Applications - Cecchetti, Yao, Ni and Myers][reentrancy]
13. [Defeating Prompt Injections by Design - Debenedetti et al.][camel]
14. [Defining Liveness - Alpern and Schneider][defining-liveness]
15. [Enforceable Security Policies - Schneider][enforceable-security-policies]
16. [Security Policies and Security Models - Goguen and Meseguer][goguen-meseguer]
17. [Secure Information Flow as a Safety Problem - Terauchi and Aiken][terauchi-aiken]
18. [Secure Information Flow by Self-Composition - Barthe, D'Argenio and Rezk][self-composition]
19. [The lethal trifecta for AI agents - Simon Willison][lethal-trifecta]
20. [The Confused Deputy - Norm Hardy][confused-deputy]
21. [Dexible aggregator hacked for $2M via selfSwap function - Cointelegraph][dexible]

[hyperproperties]: https://www.cs.cornell.edu/fbs/publications/Hyperproperties.pdf "Hyperproperties - Clarkson and Schneider"
[sabelfeld-myers]: https://www.cs.cornell.edu/andru/papers/jsac/sm-jsac03.pdf "Language-Based Information-Flow Security - Sabelfeld and Myers"
[high-water-mark]: https://en.wikipedia.org/wiki/High-water_mark_(computer_security) "High-water mark (computer security) - Wikipedia"
[blp]: https://en.wikipedia.org/wiki/Bell%E2%80%93LaPadula_model "Bell–LaPadula model - Wikipedia"
[biba]: https://en.wikipedia.org/wiki/Biba_Model "Biba Model - Wikipedia"
[eros-confinement]: https://doi.org/10.1109/SECPRI.2000.848454 "Verifying the EROS Confinement Mechanism - Shapiro and Weber"
[denning]: https://doi.org/10.1145/360051.360056 "A Lattice Model of Secure Information Flow - Denning"
[denning-certification]: https://doi.org/10.1145/359636.359712 "Certification of Programs for Secure Information Flow - Denning and Denning"
[jif]: https://www.cs.cornell.edu/jif/ "Jif: Java + information flow"
[scif]: https://www.cs.cornell.edu/projects/scif "SCIF: Smart Contract Information Flow"
[scif-paper]: https://arxiv.org/abs/2407.01204 "A Language for Smart Contracts with Secure Control Flow"
[reentrancy]: https://www.cs.cornell.edu/andru/papers/oakland21 "Compositional Security for Reentrant Applications"
[camel]: https://arxiv.org/abs/2503.18813 "Defeating Prompt Injections by Design"
[defining-liveness]: https://doi.org/10.1016/0020-0190(85)90056-0 "Defining Liveness - Alpern and Schneider"
[enforceable-security-policies]: https://dl.acm.org/doi/10.1145/353323.353382 "Enforceable Security Policies - Schneider"
[goguen-meseguer]: https://doi.org/10.1109/SP.1982.10014 "Security Policies and Security Models - Goguen and Meseguer"
[terauchi-aiken]: https://doi.org/10.1007/11547662_24 "Secure Information Flow as a Safety Problem - Terauchi and Aiken"
[self-composition]: https://doi.org/10.1109/CSFW.2004.1310735 "Secure Information Flow by Self-Composition - Barthe, D'Argenio and Rezk"
[lethal-trifecta]: https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/ "The lethal trifecta for AI agents: private data, untrusted content, and external communication"
[confused-deputy]: https://www.cs.utexas.edu/~witchel/S25-380L/papers/hardy88confused.pdf "The Confused Deputy - Norm Hardy"
[dexible]: https://cointelegraph.com/news/dexibleapp-aggregator-hacked-for-2m-via-selfswap-function "Dexible aggregator hacked for $2M via selfSwap function - Cointelegraph"
