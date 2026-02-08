---
title:  "Solidity Types Layout Cheat Sheet"
category: blockchain
---

One unusual thing about programming in Solidity to target the EVM, as opposed to other programming languages targeting any other platform,
is that a type doesn't only dictate the data's memory layout; it also dictates how the data is encoded in calldata and how it is stored in storage.
Typically, persistence format is done via custom (de)serialization, and on-the-wire formats are handled by IDLs.

| data        | solidity                     | other languages/platforms       |
| ----------- | ---------------------------- | ------------------------------- |
| on-the-wire | abi-encoded[**](#abi-vs-idl) | IDL layout                      |
| in-use      | memory layout                | language memory layout          |
| at-rest     | storage layout (packed)      | serialization lib memory layout |

In order to write gas-efficient programs, it is important for solidity programmers to understand the 3 different layouts that their types can be represented in:
1. ABI-encoded calldata
   1. always 32-byte padded (no packing)
   2. big-endian
   3. dynamic types use offset pointers
   4. function selector (4 bytes) at start
2. Memory
   1. always 32-byte padded (no packing)
   2. big-endian for numeric types (including address == uint160)
   3. bytes1..bytes31 which are left-aligned (right-padded with zeros)
3. Storage
   1. types <32 bytes can be packed into the same 32-byte slot
   2. packed right to left (this one trips people up!!)
   3. dynamic types (arrays + mappings) use keccak256 hash of their slot as their storage location

![image](/assets/solidity-types-layout/data-layout-cheat-sheet.png)



## ABI vs IDL

Solidity's "ABI" is a misnomer — it's really an IDL/message serialization format. A traditional [ABI](https://en.wikipedia.org/wiki/Application_binary_interface) specifies function calling conventions:
- Which registers hold which arguments
- Stack frame layout and calling conventions
- How return values are delivered

This is about INTRA-process function calls — caller and callee share an address space and execution context.
EVM [CALLs](https://www.evm.codes/?fork=osaka#f1), on the other hand, are about INTER-process message passing — caller and callee are separate contracts with separate storage, and the EVM mediates with a raw byte buffer (calldata). The receiving contract's dispatcher reads 4 bytes (selector), then deserializes the rest. This is structurally identical to:
- Protobuf/gRPC service definitions
- Solana's IDL
- COM/CORBA IDLs
- JSON-RPC schemas

Solidity's "real" ABI is for internal/private function calls within a single contract (shared address space). When one internal function calls another, the compiler decides how to pass arguments — on the EVM stack, via memory, or by pointing to a storage slot. That's the actual "binary interface" in the traditional sense. But this is entirely a compiler implementation detail, undocumented and subject to change between solc versions.

The name "ABI" was likely chosen in reference to in traditional programming, shared libraries are called across compilation unit boundaries, somewhat analogous to cross-contract calls. But the key difference is that traditional cross-library calls still happen in-process with shared memory and registers, while EVM external calls are mediated through serialized byte buffers — which makes it fundamentally a serialization/deserialization protocol, not a calling convention.

# References

- [https://docs.soliditylang.org/en/develop/internals/layout_in_memory.html](https://docs.soliditylang.org/en/develop/internals/layout_in_memory.html)
- [https://docs.soliditylang.org/en/develop/internals/layout_in_storage.html](https://docs.soliditylang.org/en/develop/internals/layout_in_storage.html)
- [https://docs.soliditylang.org/en/develop/abi-spec.html](https://docs.soliditylang.org/en/develop/abi-spec.html)
- [https://rareskills.io/post/evm-solidity-storage-layout](https://rareskills.io/post/evm-solidity-storage-layout)


<!-- Link to excalidraw, in case I ever lose access to seismic's workspace where its hosted. -->
<!-- https://app.excalidraw.com/s/7UT6xpZZbal/5ITjNUDPjTO -->
<!-- Also saved the excalidraw file locally under /assets/solidity-types-layout/excalidraw.json -->
