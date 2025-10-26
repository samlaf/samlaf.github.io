---
title:  "Powers vs Properties: Examples Compendium"
category: programming
---

One of my favorite articles about programming philosophy is Ted Kaminski's [The one ring problem: abstraction and our quest for power](https://www.tedinski.com/2018/01/30/the-one-ring-problem-abstraction-and-power.html) where he describes how adding more power to languages (e.g. adding macros) always comes at the cost of (provable) properties.

![image](/assets/powers-vs-properties-examples/properties-vs-powers.png)

This article is meant as a personal compendium of various examples of this tradeoff that I have encountered during my career. Expect the list to grow over time.

# Normed Division Algebras

John Baez, in his article on [Octonions](https://people.sissa.it/~cecotti/octonions.pdf), describes this exact phenomena for the four normed division algebras, where increasing "power" comes with the loss of property:
- Real Numbers: complete ordered field
- Complex Numbers: algebraically complete, but not ordered
- Quaternions: noncommutative
- Octonions: nonassociative

# Compiler Intermediate Representations

When compiling high-level programming languages to low-level assembly languages, compilers typically go through a series of intermediate representations. Imperative languages use SSA based representations, while functional languages use lambda-calculus based representations such as System F.

![image](/assets/powers-vs-properties-examples/llvm-ir.png)

### Properties
Here are main properties that IRs lose as they go down from high-level programming languages to assembly languages:
- Type Information Loss: As code moves down the compilation chain, rich type systems (generics, algebraic data types) collapse into primitive types and memory addresses
- Control Flow Abstraction Loss: High-level constructs like exceptions, iterators, and closures get transformed into jumps, branches, and function pointers.
- Memory Management Semantics: Garbage collection, RAII, or other memory management paradigms get translated into explicit allocations and deallocations.
- Concurrency Models: High-level concurrency primitives (async/await, actors) translate to lower-level threading or event mechanisms.
- Liveness Analysis Challenges: register liveness information isn't inherently part of many IRs and must be recalculated at various compilation stages.


### IR Hierarchy

1. High-Level Language → Abstract Syntax Tree (AST)
    - Properties Preserved: Semantic meaning, Type information, Variable scope relationships, Control flow structure
    - Properties Lost: Comments and documentation, Specific syntax choices (coding style), Whitespace and formatting, Programmer intent beyond what's explicit in code


2. AST → High-Level IR (e.g., Rust's HIR, Swift's SIL)
    - Properties Preserved: Control flow structure, Type relationships, Function boundaries, Variable scope information
    - Properties Lost: Language-specific abstractions, Some type system nuances, Complex inheritance relationships, Syntactic sugar


3. High-Level IR → Mid-Level IR (e.g., LLVM IR, GIMPLE)
    - Properties Preserved: Basic control flow, Function boundaries, Core type information (simplified), Data flow relationships
    - Properties Lost:
        - High-level type system features (generics, traits)
        - Object-oriented relationships
        - Exception handling semantics (translated to control flow)
        - Abstract data types (transformed to primitives)

4. Mid-Level IR → Low-Level IR (e.g., RTL, LLVM MachineIR)
    - Properties Preserved: Basic operations, Simplified control flow, Memory access patterns, Data dependencies
    - Properties Lost: Hardware independence, Most remaining type information, Variable abstractions (everything becomes registers or memory), Some optimization opportunities tied to high-level semantics

5. Low-Level IR → Assembly Language
    - Properties Preserved: Machine operations, Memory addressing, Register allocation, Basic blocks structure
    - Properties Lost: Machine independence, Most optimization opportunities, Remaining abstract data types, Register allocation flexibility, Variable lifetime management

6. Assembly → Machine Code
    - Properties Preserved: Direct hardware operations, Memory layout
    - Properties Lost: Human readability, Symbolic references, Label names, Meaningful structure beyond instructions

### References
Leaving a list of references for those interested in digging into this topic further:
- [https://mitchellh.com/zig/astgen](https://mitchellh.com/zig/astgen)
- [https://cs.lmu.edu/~ray/notes/ir/](https://cs.lmu.edu/~ray/notes/ir/)
- [http://troubles.md/wasm-is-not-a-stack-machine/](http://troubles.md/wasm-is-not-a-stack-machine/)
- [https://queue.acm.org/detail.cfm?id=2544374](https://queue.acm.org/detail.cfm?id=2544374)
- [https://www.youtube.com/playlist?list=PLmYPUe8PWHKrc3arcxUPp2XosprqIb617](https://www.youtube.com/playlist?list=PLmYPUe8PWHKrc3arcxUPp2XosprqIb617)