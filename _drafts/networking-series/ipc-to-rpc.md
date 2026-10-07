# From IPC to RPC

An IPC flow moves messages. It doesn't know what they mean, which ones belong together, or what the other side did with them. RPC is the layer that knows. In the [Part 1 table](/programming/networking-is-ipc.html), it is the two middle columns, message types and request/response IDs, plus everything that depends on them.

This article is about what that layer adds, and why the same additions show up at every scope, down to the queues between a CPU and an SSD.

## What a request/reply protocol adds

Take any flow that delivers whole messages in order. To turn it into RPC you need:

1. **Framing**, if the flow is a byte stream. TCP and pipes give you bytes, so the RPC layer adds a length prefix or a delimiter. A flow with its own framing, like `SOCK_SEQPACKET` or SCTP, saves this step.
2. **Message types.** Something in each message says which operation it is, so the receiver can dispatch it: a method name, an opcode, a procedure number.
3. **Serialization.** An agreed encoding for the arguments and results: Protocol Buffers, Cap'n Proto, XDR, JSON.
4. **Request IDs.** Each request carries an ID, and its reply carries the same one. This is the column that turns messaging into RPC.
5. **Cancellation and deadlines.** A way to say "stop working on request 17", and a time after which nobody wants the answer.
6. **Failure semantics.** A rule for what the caller may conclude when no reply comes.

The first three are about one message. The last three are about the relationship between two, and they all hang on the request ID.

### Request IDs make concurrency possible

A function call doesn't need a request ID, because the stack frame is one: the reply goes back to whoever is waiting on that frame. A flow has no stack. If a client sends two requests on one flow and replies come back in a different order, the ID is the only way to tell which is which.

With IDs, one flow can carry many outstanding calls, and the server can finish them in any order. Without them, a client either waits for each reply before sending the next request, or opens one flow per outstanding call. HTTP/1.1 is the cautionary example. It has no request IDs, so pipelined replies must come back in request order, and one slow response blocks every one behind it. Browsers opened six connections per host instead. HTTP/2 added stream IDs, and gRPC rides on them.

### Cancellation is addressed by request ID

Once requests have IDs, cancelling one is a message naming its ID. The same design appears at every scope:

| Protocol | Request ID | Cancel |
| --- | --- | --- |
| HTTP/2, gRPC | stream ID | `RST_STREAM` |
| 9P | tag | `Tflush` |
| io_uring | `user_data` | `IORING_OP_ASYNC_CANCEL` |
| NVMe | command identifier | `Abort` admin command |

A cancel is a request in its own right, and it races with the reply it cancels. Every one of these protocols has to say what happens when the reply arrives first. 9P's answer is the cleanest. The client may not reuse the old tag until `Rflush` arrives. If the original reply arrives first, the client must honor it as if the request had never been flushed.

## Every completion queue is an RPC protocol

That NVMe and io_uring appear in the table above is not a stretch. A submission queue and a completion queue are a request/reply protocol over shared memory:

- **The submission entry is the request.** It has an opcode, which is the message type, and an ID: NVMe's command identifier, io_uring's `user_data`, a virtqueue's descriptor index.
- **The completion entry is the reply.** It carries the same ID back, and a status.
- **Completions come back out of order.** That is the whole point of the ID. An SSD finishes reads in whatever order its flash allows, and the driver matches each completion to its waiter by ID.

The [ring buffers article](/programming/ring-buffers.html) compares these queues as data structures. Read as protocols, they are RPC with the network removed. The hypercall row of the Part 1 table is the limit case: the leaf number is the message type, the registers are the framing, and the call is synchronous, so the vCPU itself is the request ID, as the stack frame is for a function call.

## What the caller may conclude

A local call either returns or it doesn't, and if it doesn't, the whole process is gone. A remote call can fail in a third way: the request or the reply is lost, and the caller can't tell which. Did the server execute it?

Birrell and Nelson's [*Implementing Remote Procedure Calls*](https://dl.acm.org/doi/10.1145/2080.357392) (1984) gave the classic answer. If the call returns, the procedure ran exactly once. If it fails, it ran at most once. Their implementation got there with call IDs: the server remembers the last ID it saw from each caller, and drops a retransmitted request instead of executing it twice.

That is the end-to-end argument again, applied to RPC. A reliable flow below doesn't help. TCP guarantees the bytes arrived in order while the connection lasts. When the connection breaks with a request in flight, TCP can't tell you whether the server ran it, because the answer lives in the server's application state, not in TCP's. Only the ends can settle it:

- **At-least-once:** retry until a reply comes back. Safe only for idempotent operations.
- **At-most-once:** the server remembers request IDs and drops duplicates, so a retry never runs twice. This is Birrell and Nelson's design.
- **Exactly-once, in effect:** at-most-once plus retries, with the ID kept long enough to cover every retry. Stripe's `Idempotency-Key` header is this, done by hand on top of HTTP.

All three depend on an ID that outlives the flow. That is why the "session resume" column of the Part 1 table matters to RPC. If request IDs are scoped to a connection, a reconnect loses them, and every in-flight call becomes a question nobody can answer. QUIC's connection IDs, mosh's state sync and Kafka's offsets each keep that state alive across a broken flow, at their own layer.

### Remote is not local

Waldo, Wyant, Wollrath and Kendall's [*A Note on Distributed Computing*](https://scholar.harvard.edu/files/waldo/files/waldo-94.pdf) (1994) is the standing warning against hiding all of this. RPC systems were sold on making a remote call look like a local one. The note argues that four differences can't be hidden: latency, memory access, partial failure and concurrency. An interface designed as if they didn't exist breaks when they do.

The table is a map of how much each row hides. A function call has nothing to hide. Every row below it makes some of the four visible, and an RPC layer that pretends otherwise is filling a dash with a promise it can't keep. I made a related argument about multiprocessors in [an earlier post](/programming/multiprocessors-are-distributed-systems.html): partial failure is what makes a system distributed, and once you have it, no layer can make it go away.

## Where RPC ends

RPC names operations. The layer above it in the [series map](/programming/networking-series-intro.html) names objects: the things the operations act on. Two designs sit right at that seam.

### Cap'n Proto: references in the protocol

Cap'n Proto's RPC protocol, descended from the E language's CapTP, lets a message carry a reference to a remote object. The receiver can call methods on it, and pass it on. Two things follow:

- **Promise pipelining.** A call returns a promise for its result, and the caller can call a method on that promise before it resolves. The server receives both calls together and runs the second on the result of the first. A chain of dependent calls costs one round trip instead of one per call.
- **Capabilities in the protocol.** A reference is the only way to reach an object, and you only hold references you were given. Authority travels with the reference. The [authorization series](/programming/capabilities.html) covers why that makes designation and authority the same act.

At this point the flow carries an object graph, not just messages. That is the "distributed object" layer of the map, the one CORBA aimed at with less success.

### CDAP: one application protocol for everything

RINA goes the other way and fixes the operations. Its management functions, routing, enrollment and flow allocation among them, share a single application protocol, CDAP, the Common Distributed Application Protocol. It has a handful of operations on remote objects: create, delete, read, write, start and stop. Everything else is a schema: which objects exist in the layer's resource information base, and what each operation does to them.

Day's bet is that this is enough for every application: a small fixed set of verbs, over a named tree of objects. It isn't a new idea. REST is the same bet over HTTP, with resources and methods. 9P is the same bet over files, with walk, open, read and write, which is why virtio-fs and 9p fill so many columns of the Part 1 table. The [everything is a file](/programming/everything-is-a-file.html) post argued about exactly this tradeoff: a uniform data plane composes well, and the control plane never fits inside it.

## Up the stack

Once there are objects and operations on them, the next question is which histories of those operations are legal. Can a reader see a write before it's acknowledged? Can two clients disagree about the order of two writes? That is the consistency layer of the map, and the replication protocols that implement it. It is where this series stops. The protocols up there, Raft, Paxos, atomic broadcast, all sit on the RPC described here, and all fill its last dash themselves: deciding what happened when the reply never came.

## References

- A. Birrell, B. Nelson, [Implementing Remote Procedure Calls](https://dl.acm.org/doi/10.1145/2080.357392), ACM TOCS, 1984.
- J. Waldo, G. Wyant, A. Wollrath, S. Kendall, [A Note on Distributed Computing](https://scholar.harvard.edu/files/waldo/files/waldo-94.pdf), Sun Microsystems Laboratories, 1994.
- J. Saltzer, D. Reed, D. Clark, [End-to-end arguments in system design](https://web.mit.edu/Saltzer/www/publications/endtoend/endtoend.pdf), ACM TOCS, 1984.
- [Cap'n Proto RPC protocol](https://capnproto.org/rpc.html), including promise pipelining.
- [9P2000 manual: flush](https://9fans.github.io/plan9port/man/man9/flush.html).
- E. Grasa et al., [Recursive InterNetwork Architecture, Investigating RINA as an Alternative to TCP/IP (IRATI)](https://www.riverpublishers.com/pdf/ebook/chapter/RP_9788793519114C16.pdf), River Publishers, 2017. CDAP and the resource information base.
