---
title:  "Authorization"
category: programming
date: 2026-08-31
---

Despite security and authorization having been essential parts of computer science and programming for decades, the field is constantly reinventing itself and still evolving rapidly:

![](/assets/authorization/auth-timeline.png)

Practice is fragmented, but the abstractions underneath are converging. And with LLM agents now running inside our software, we need to understand how authorization decisions are made and enforced in systems that change while they run.

Most writing on authorization covers one step: the decision itself. It starts from the function every system computes,

```text
f(subject, action, resource, context) → allow | deny
```

and compares ways to compute it: ACL, RBAC, ReBAC, ABAC. But a request can be stopped long before anything decides. A name can resolve to nothing. A packet can have no route. We try to take a holistic view of authorization, including sandboxing, networking, enforcement, caching and bearer tokens, and even capabilities.

This series follows the path of a request: the subject is authenticated, a decision is made, and the decision is enforced on the way to the object/resource. NIST's [ABAC guide][nist-sp-800-162] calls this the *trust chain*:

![NIST SP 800-162, Figure 8: the ABAC trust chain](/assets/authorization/nist-abac-trust-chain.png)

The horizontal spine is the request path, with the vertical "bones" above each stage representing information that was written ahead of time, without which the object cannot successfully be reached: a credential issued, an identity provisioned, an attribute assigned, a rule managed.

This is a great starting point, but it is ABAC-focused. To take a more holistic systems perspective, we make a few modifications to reach the grid below that acts as our series roadmap:

1. We see networking not only as information needed for authentication, but also as a stage the request passes through, which can itself be a source of implicit authorization (e.g., dropping the request). **Reach** more broadly includes all the various boundaries the request must cross, including local gates such as an IPC endpoint, a syscall, or a VM exit.
2. Similarly, before a request can be made at all, a name that **designates** an object first has to be resolved: the kernel walks a path, DNS maps a host, a table maps a file descriptor to an open file.
3. Finally, similar to the ABAC bones, we breakdown each stage temporally:
   - **Written:** what the stage rests on, such as namespace bindings, routes, or facts and rules. It is written before any request.
   - **Carried:** a copy of written state that the request brings along, such as a session cookie or a token.
   - **Reference monitors:** what the request meets, and what can stop it. Either the lookup comes back empty (*absence*), or a policy says no (*judgment*).
   - **Looked up:** what the monitor fetches when the request did not bring enough.

![Series roadmap: the grid of four stages and four rows, with each cell tagged by the article that covers it](/assets/authorization/series-roadmap.svg)

## How the series walks the grid

Each article takes one part of the grid[^other-maps]:

- **[Part 1: Authorization models](/programming/authorization-models.html)** reads the Decide column as a database. Facts and rules are written, and every check is a query against the view they define. ACL, RBAC, ReBAC and ABAC are different schemas for the same facts, and DAC and MAC are answers to a different question: who may change them.
- **[Part 2: How authority is enforced](/programming/authority-enforcement.html)** takes the reference monitor row. A database answer binds nothing on its own: something in the path of the effect has to apply it, or the path must not exist. Each stage has its own enforcer, and sandboxes are built from both strategies.
- **[Part 3: Carriers](/programming/carriers.html)** takes the Carried row. A token is a copy of a decision that travels with the request, so the check does not have to go back to the store. Every copy is a cache, and taking it back means reaching every copy.
- **[Part 4: Capabilities](/programming/capabilities.html)** follows the artifacts that span several columns. When one reference names the object, routes to it and carries the permission, designate, reach and decide become one act. "May Alice do this?" turns into "can Alice reach this?"

[authorization-terminology-mess]: https://idpro.org/authorization-terminology-is-a-mess-lets-fix-it/ "Authorization Terminology Is a Mess. Let's Fix It."
[authzen-api]: https://openid.net/specs/authorization-api-1_0.html "Authorization API 1.0 - OpenID Foundation"
[from-abac-zbac-evolution]: https://shiftleft.com/mirrors/www.hpl.hp.com/techreports/2009/HPL-2009-30.pdf "From ABAC to ZBAC: The Evolution of Access Control Models"
[networking-is-ipc-paper]: https://www.cs.bu.edu/fac/matta/Papers/IPC-arch-rearch08.pdf "“Networking is IPC”: A Guiding Principle to a Better Internet"
[nist-sp-800-162]: https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-162.pdf "NIST SP 800-162: Guide to Attribute Based Access Control (ABAC) Definition and Considerations"
[rfc1498]: https://www.rfc-editor.org/rfc/rfc1498.html "RFC 1498: On the Naming and Binding of Network Destinations"
[state-union-authorization]: https://idpro.org/the-state-of-the-union-of-authorization/ "The State of the Union of Authorization"

## Footnotes <!-- omit in toc -->

[^other-maps]: This diagram is the most general model of security that I have ever come across. It is broader and we will leave certain topics such as authentication and cryptography to separate series. Nonetheless, keeping this diagram in head while thinking about any security related topic, including authorization, has been incredibly useful to me, which is why I am sharing it here. Every other map or taxonomy that I have ever come across fits inside it, often inside a single column. Working out where each of these lands is left as an insightful exercise:

    - [XACML's four boxes](/programming/authority-enforcement.html#decide-vs-enforce): the PEP, PDP, PAP and PIP, as NIST draws them for ABAC.
    - [IDPro's six axes][authorization-terminology-mess]: a shared vocabulary for comparing authorization systems.
    - [Karp's four steps][from-abac-zbac-evolution]: identification, authentication, authorization and access decision.
    - [RINA's DIF][networking-is-ipc-paper]: a network layer with its own directory, enrollment, routing and flow allocation.
