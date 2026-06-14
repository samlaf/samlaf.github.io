# The Shapes of I/O

Once you stop asking whether something is “a file” or “a socket,” you can ask a better question:

> What semantic protocol does this resource expose?

A regular file, a TCP socket, a Kafka topic, a timerfd, a database table, and a WebRTC media track are all things you can do I/O with. Some may even be represented by file descriptors. But they do not have the same semantics.

The mistake is to confuse the handle, the transport, and the protocol.

A file descriptor is a handle. A syscall, shared memory queue, or network connection is a transport. The semantic protocol is what the operations *mean*.

A storage write may travel through a syscall, `io_uring`, PCIe, Ethernet, RDMA, or a database connection. It is still storage-shaped if the operation promises durable, addressable state. A video stream and a log stream may both “stream,” but one cares about timely playback while the other cares about durable replay.

The transport carries the operation. The semantic protocol gives the operation meaning.

## Local handles and semantic resource managers

A local handle is a mechanism. It gives a process a secure way to refer to something and ask for operations on it. It does not, by itself, explain what the thing *means*.

A socket fd is a good example. To the local kernel, it is an endpoint with buffers, readiness, addresses, options, and packet or stream state. To the application, the bytes may be HTTP, SQL, Raft, WebRTC, SSH, or a game protocol. The fd is the local mechanism; the application protocol is the semantic layer.

This is a useful way to think about kernels in general. Kernels are best at providing mechanisms: isolation, scheduling, address spaces, descriptors, IPC, page mappings, device submission queues, and permission checks. Rich semantics and policy often live in resource managers above that mechanism.

In a monolithic Unix kernel, many resource managers live inside the kernel: filesystems, networking, device drivers, pipes, terminals. In a microkernel, more of those managers move to user space. In distributed systems, the resource manager may be an entire service or cluster: a database, object store, message log, scheduler, service mesh, or orchestrator.

This is why local endpoint handles and remote services should not be confused. An fd may point to a local timer backed by a nearby chip, a socket connected to a remote RPC endpoint, or a file cached from a distributed filesystem. The handle gives local authority and mechanics. The I/O shape describes the semantic contract: timer events, byte streams, durable storage, RPC, pub-sub, queries, media frames, and so on.

Unix put one especially important semantic resource manager in the kernel: the filesystem. The kernel understands directories, inodes, permissions, metadata, mounts, page cache, and storage-backed byte arrays. But most other semantic domains — databases, queues, logs, RPC services, media streams, collaborative documents — live above the kernel, even when they ultimately store bytes in files.

SQLite is a nice example. To the kernel, a SQLite database is a regular file operated on with `open`, `pread`, `pwrite`, `fsync`, and locks. To the application, it is tables, indexes, B-trees, transactions, constraints, SQL, and a write-ahead log. The kernel provides storage-shaped mechanisms. The database library provides database-shaped semantics.

## Storage is not just communication

One tempting conclusion is: if storage writes ultimately travel over PCIe, Ethernet, or some queue, maybe storage is just communication.

At the implementation layer, that is true. A modern SSD is basically a small computer behind a port. It has firmware, queues, DMA, caches, scheduling, error correction, and internal state. NVMe especially looks like message passing: the host submits commands to queues, rings doorbells, and receives completions.

A disk can be viewed as a remote service.

But it is a remote service with a storage contract.

The important question is not merely “did bytes get sent?” The important questions are:

```txt
Can I read the data later?
Where is it addressed?
Is it durable after acknowledgment?
What ordering is guaranteed?
Can writes be torn?
Can I flush?
Can I snapshot?
Can I replay?
Can I query?
What happens after failure?
```

Those are storage semantics. They are not captured by the transport layer.

Likewise, a network protocol can be used for storage. NFS, S3, iSCSI, NVMe-over-TCP, and database protocols all carry storage operations over communication transports. But the fact that they ride over a network does not make their semantics the same as a chat message, a video call, or a TCP byte stream.

Storage is about state over time. Communication is about interaction over time. They overlap, but they are not the same.

## Random-access storage

The classic file-shaped interface is random-access storage:

```txt
read_at(offset, length)
write_at(offset, bytes)
truncate
sync
```

Examples include regular files, block devices, object-storage range reads, and database pages.

The key idea is stable addressability. You write bytes at some location and expect to read them later. Durability, ordering, truncation, metadata, and failure behavior matter.

This is the colloquial meaning of “file”: persistent storage with a name and, usually, seekable contents.

## Byte streams

A byte stream has a simpler shape:

```txt
read next bytes
write next bytes
```

Examples include TCP, pipes, terminals, serial ports, and TLS streams.

This is ordered communication without inherent message boundaries. It is also the part of the Unix file abstraction that generalizes best. Programs can read from stdin and write to stdout because many things can be treated as byte streams.

But a byte stream is not the same as random-access storage. There is no stable offset to seek to. Once bytes pass by, they are gone unless something else stores them.

## Datagram or message transport

A message-oriented interface looks like:

```txt
send message
receive message
```

Examples include UDP, Unix datagram sockets, packet sockets, and Netlink-style channels.

Here message boundaries are part of the protocol. Delivery may be lossy, unordered, duplicated, filtered, or multiplexed. That is a different shape from both files and byte streams.

This is why saying “sockets are byte streams” is too broad. TCP sockets are byte streams. UDP sockets are datagram endpoints. Both are socket-shaped and fd-shaped, but their data shapes are different.

## Append-only logs

An append-only log has operations like:

```txt
append(record)
read_from(offset)
commit(offset)
replay(offset)
```

Examples include Kafka topics, journals, write-ahead logs, and event stores.

This is storage-like because records may be durable and replayable. It is communication-like because producers and consumers interact over time. It is not quite a file, not quite a socket, and not quite a database table.

The important semantic unit is the record, not the byte offset. The important semantic promise is that old records can be found again.

## Queues

A queue has operations like:

```txt
enqueue(message)
dequeue()
ack()
nack()
```

Examples include POSIX message queues, AMQP-style queues, work queues, and job queues.

A queue is close to a log, but the consumption semantics differ. Reading from a log usually leaves the log intact and advances a consumer offset. Reading from a queue often claims, removes, leases, or acknowledges a message. The important questions are: who owns the next item, can it be delivered twice, what happens after a crash, and when is work considered complete?

## RPC and command invocation

An RPC-shaped interface looks like:

```txt
operation(args) -> result
```

Examples include HTTP APIs, gRPC, Wasm imports, syscalls, `ioctl`, Plan 9 control files, stored procedures, and driver commands.

This is where resource-specific actions become explicit — or get smuggled through generic mechanisms.

Control is not a separate transport. It is a role an operation can play. A control operation may ride over RPC, a datagram socket, a byte stream, a syscall, an `ioctl`, or a string written to a file.

For example:

```txt
TCP data plane:     send and receive bytes
TCP control plane:  connect, bind, listen, accept, setsockopt

serial data plane:  read and write bytes
serial control:     set baud rate, parity, flow control

file data plane:    read and write contents
file control:       truncate, fsync, lock, chmod
```

The control operation belongs to the semantic protocol. The transport is merely how it gets there.

## Query

A query-shaped interface supports operations like:

```txt
filter
project
join
aggregate
search
```

Examples include SQL, Datalog, GraphQL-like APIs, search indexes, and system introspection tables.

Query is excellent for discovery and observability. It is a good way to ask questions like:

```txt
all running jobs owned by this user
all files modified by this workflow
all processes consuming more than X memory
all resources reachable by this service
```

A hierarchical namespace is a poor fit for those questions. A query over indexed state is often better.

But query is dangerous as an unrestricted authority boundary. Exposing arbitrary SQL as the system interface is like exposing a production database directly to the internet: powerful, flexible, and probably not what you want across a trust boundary.

A safer design uses query internally, or through scoped views, while exposing narrower authority-bearing operations externally.

## Pub-sub and event streams

A pub-sub interface looks like:

```txt
subscribe(filter)
publish(event)
receive matching events
```

Examples include inotify, fanotify, database changefeeds, DOM events, message buses, gossip topics, and signals, loosely.

This shape is about future events and fanout. It is not just reading bytes. The important questions are: what events can occur, who receives them, can they be missed, are they ordered, and how are subscriptions scoped?

## Shared or mapped memory

A shared-memory interface looks like:

```txt
map region
load/store directly
synchronize separately
```

Examples include `mmap`, shared memory, GPU buffers, RDMA regions, ring buffers, and `io_uring` queues.

This deserves its own category because after setup, the interface is not `read` or `write`. It is memory access plus synchronization. The hard parts are visibility, ordering, ownership, cache coherence, and lifetime.

## Real-time media

A real-time media interface looks like:

```txt
send timestamped frame
receive timestamped frame
play at the right time
```

Examples include RTP, WebRTC media tracks, audio devices, video capture, and game networking.

This is communication-shaped, but not simply byte-stream-shaped. Timing, jitter, latency, and loss tolerance are part of the semantics. A late video frame may be worse than a missing one. That is very different from a file write or a database transaction.

## Peer-to-peer overlays

Peer-to-peer protocols are usually not one data shape. They are overlays that combine several shapes.

A P2P system may have:

```txt
peer discovery
request/response
pub-sub or gossip
content-addressed block exchange
replicated logs
streams between peers
```

Examples include BitTorrent, IPFS/libp2p, Ethereum devp2p, Nostr relays, Matrix federation, and many blockchain gossip networks.

BitTorrent is partly a query/discovery protocol, partly a block-exchange protocol, and partly a swarm coordination protocol. IPFS has content-addressed block retrieval, DHT queries, pub-sub, and streams. A blockchain P2P network often has gossip for new transactions and blocks, request/response for missing data, and sometimes a durable log at the application layer.

So “P2P” is less a semantic protocol than a deployment topology. It says who talks to whom and how authority/discovery are distributed. The I/O shapes inside it may be datagrams, streams, RPC, query, pub-sub, logs, or storage.

## File vs socket is too small a vocabulary

The classic distinction says:

```txt
file   = storage
socket = communication
```

That is useful, but too coarse.

A file may be random-access storage, an append-only log, a directory namespace, a memory-mapped region, or a control file.

A socket may carry a byte stream, datagrams, RPC, events, kernel control messages, or storage operations.

A queue may be communication in one context and durable storage in another.

A peer-to-peer protocol may combine discovery, query, pub-sub, block exchange, streams, and logs under one networking stack.

A database may be storage, query engine, transaction manager, event source, and RPC endpoint all at once.

A video stream and a log stream may both be streams, but one is optimized for timely playback and the other for durable later inspection.

A disk may be attached locally over PCIe or remotely over Ethernet, but the semantic contract is still storage.

So “file vs socket” separates two historical object families. It does not describe the full design space.

The better question is:

> What resource do I hold, what protocol does it speak, and how are operations transported to it?

## Why this matters for security

This decomposition is not just pedantry. It matters for security.

If discovery, authority, and operations are all collapsed into one string, the result is powerful but dangerous.

A shell command can do this:

```txt
rm /some/path
```

A SQL query can do this:

```sql
DELETE FROM objects WHERE owner = 'alice';
```

A Plan 9-style control file might do this:

```txt
write ctl "connect 2048"
```

A String OS fantasy might do this:

```txt
the_syscall("kill pid 1234")
```

These interfaces are flexible because they encode names, operations, and arguments into dynamic strings. But that also makes them hard to constrain. The authority boundary has to parse and understand the command language.

This is the same reason we usually do not expose raw SQL directly to the internet. We put a REST, RPC, stored-procedure, or application-specific API in front of it.

Not because SQL is bad. Because SQL is too powerful to be the default public authority boundary.

The same lesson applies to operating systems. A queryable OS substrate might be excellent for discovery, observability, scheduling, debugging, and auditing. But mutation should usually happen through narrower, intention-revealing operations and explicit capabilities.

Good interfaces separate how you find things, what you are allowed to use, what operations you can perform, and how those operations are transported.

Bad interfaces collapse all of that into:

```txt
do whatever this string says
```

## Conclusion

The point is not to create a perfect taxonomy. The point is to avoid being trapped by historical names.

“File” and “socket” are useful words, but they are not enough. Modern systems are full of resources that are storage-like, stream-like, queue-like, query-like, memory-like, event-like, and media-like, often all at once.

A better vocabulary asks what semantic protocol the resource exposes. Only then should we ask what handle represents it and what transport carries its operations.

# References

- https://book.systemsapproach.org/e2e.html
- https://www.inngest.com/blog/queues-are-no-longer-the-right-abstraction
- https://jack-vanlightly.com/blog/2018/5/20/event-driven-architectures-the-queue-vs-the-log