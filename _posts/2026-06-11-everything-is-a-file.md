---
title:  "Everything is an... unstructured byte stream?"
category: programming
date: 2026-06-11
---

[Everything is a file](https://en.wikipedia.org/wiki/Everything_is_a_file) is one of those Unix slogans that feels profound until you ask what it means.

Let's address the first point of confusion: the "file" the slogan is referring to is NOT the filesystem "text file" that the colloquial use of the word typically refers to.

The more you dig, the more completely unrelated meanings you will find: Does it mean everything has a filename? Does it mean everything is a file descriptor? Does it mean everything supports `read` and `write`? Does it mean everything is storage? Here's Linus [himself][linus-eiaf]:
> The UNIX philosophy is often quoted as "everything is a file", but that really means "everything is a stream of bytes".

> The whole point with "everything is a file" is not that you have some random filename (indeed, sockets and pipes show that "file" and "filename" have nothing to do with each other), but the fact that you can use common tools to operate on different things.

> The UNIX way is "everything is a file descriptor or a process", but that was never about namespaces.

Confused yet? Good, let's untangle this mess.

- [Three ideas hiding in one slogan](#three-ideas-hiding-in-one-slogan)
  - [1. Naming and creation](#1-naming-and-creation)
  - [2. Resolve once, use by handle](#2-resolve-once-use-by-handle)
  - [3. Unstructured Byte Stream Data Plane API](#3-unstructured-byte-stream-data-plane-api)
    - [**Data Plane is about Composition**](#data-plane-is-about-composition)
    - [**Control Plane Doesn't Fit in a Byte Stream**](#control-plane-doesnt-fit-in-a-byte-stream)
- [A better model](#a-better-model)
  - [The future is more structured, not less](#the-future-is-more-structured-not-less)
- [TLDR](#tldr)


## Three ideas hiding in one slogan

In the UNIX philosophy, “Everything is a file” is really [three separate meanings][sunfish-eiaf] wearing one trench coat:
- Everything has a name in a hierarchical namespace (Name)
- Everything is a file descriptor (Authoritative Handle)
- Everything is a byte sequence (API)

![](/assets/everything-is-a-file/fd-kernel-vfs-file.svg)

This picture highlights the polysemy. Sometimes file means the virtual FILE system pathname, sometimes the FILE descriptor, sometimes the `struct file` kernel object behind the descriptor, and sometimes the persistent physical FILE system on disk.

The important underlying idea is that an OS manages (and protects) resources: files, sockets, pipes, timers, event sources, processes, etc. User-space programs that want to interact with those resources thus need answers to three fundamental questions:
1. How do I name, find, or create a resource?
2. What do I possess that lets me use it?
3. What operations can I perform on it?

Unix's answer is (for most resources): namespace entries or creation syscalls, file descriptors, and a few simple byte-stream operations:
1. Name/create: `/dev/null`, `/proc/self/status`, `socket()`, `pipe()`, `timerfd_create()`
2. Hold: fd 0, 1, 2, 3, ...
3. Use: `read`, `write`, `poll`, `ioctl`, ...


### 1. Naming and creation

One interpretation of “everything is a file” is that system objects can be exposed, opened, or sometimes created through the filesystem namespace. This is the `/dev`, `/proc`, and `/sys` version of the slogan. A program can open `/dev/null`. A shell can `cat /proc/self/status`. A user can browse `/sys/class/net`.

This is the least important and generalizable aspect, but powerful where applicable because paths are easy for both humans and programs to work with. You can inspect the system with `ls`, `cat`, `grep`, `find`, and `watch`. You can script it with shell redirection. Every language knows how to open, read, and write files. Exposing a kernel object through VFS makes it available to all of that existing machinery.

But there is a cost. VFS works best when the object is naturally nameable, hierarchical, and inspectable as bytes or text. It works less well when the object has rich structured operations, ambiguous lifetime, high performance requirements, or security-sensitive mutations. Then the “file” becomes a small protocol endpoint wearing a pathname.

This is why Linus [strongly objected][linus-eiaf] to futexes being exposed as `/dev/futex` or `/proc/futex`:
> The whole point with "everything is a file" is not that you have some random filename (indeed, sockets and pipes show that "file" and "filename" have nothing to do with each other), but the fact that you can use common tools to operate on different things.

[Plan 9][plan9], built by Unix's own creators as a successor, took this to its logical conclusion — networking, the window system, even remote machines, all exposed as files over a single protocol ([9P][9p]) — but it ultimately failed, for [reasons we come back to](#the-future-is-more-structured-not-less).

### 2. Resolve once, use by handle

Regardless of which namespace you used to find or create your resource, the main UNIX philosophy, and the most important aspect of the slogan, is that that resource is resolved once, and turned into a handle that you can keep using without repeated lookups. That handle is the file descriptor.

> The UNIX way is "everything is a file descriptor or a process", but that was never about namespaces.

Strictly speaking, an fd is "just another name in another namespace": a small integer resolved by the process' fd table. The important difference is that the fd table is a small, explicit, kernel-mediated namespace populated by previous authorization decisions. A pathname is a plain-data reference into a much larger ambient/global namespace. `open` converts the latter into the former.

If I hand you the string `/tmp/foo`, I have given you a name to resolve. If I hand you an open file descriptor for `/tmp/foo`, I have given you a usable reference to a particular resource, with whatever permissions were checked at open time, which you won't have to race with other processes to access.

That resolved handle has several useful properties:
- **authority**:               possession usually implies permission to use it (similar but not equivalent to [capabilities][fd-capabilities] [[^1]])
- **lifetime**:                the resource stays referenced while the fd exists
- **race avoidance**:          no repeated path/PID lookup (source of [TOCTOU](https://cwe.mitre.org/data/definitions/367.html) bugs)
- **explicit delegation**:     pass the fd over a Unix socket
- **namespace independence**:  receiver need not share the original pathname namespace

A useful example of this name-versus-handle distinction is the recent [pidfd](https://lwn.net/Articles/794707/). A bare PID is a name in an ambient, global namespace: you re-resolve it on every syscall, and it can be guessed, reused, and raced — once a PID is recycled, you signal the wrong process. A pidfd is the handle version of the same reference: resolved once into a descriptor that points at one specific process object. It turns fragile process authority into possession of a stable handle you can use to send signals, wait for exit, and inspect status, with no re-lookup in between.

On Linux, the kernel-side [implementation][linux-vfs-file-object] of FDs is the `struct file` open-handle object; the process fd table maps small integers to these open file objects. The `struct file` holds the handle's state such as offset, flags, mode, and reference count and points to the backing resource. For ordinary files that leads to VFS dentries/inodes and filesystem state. For other fds it may lead to socket state, a pipe buffer, a timer, an epoll set, a process reference, or a synthetic/anonymous inode used to fit the object into VFS machinery.

Furthermore, the `struct file` contains a `file_operations` table which contains the API supported by that handle. It points to operations like `read`, `write`, `poll`, `mmap`, and `ioctl` to the resource-specific implementation underneath, which brings us to the third and most controversial aspect of the slogan.

### 3. Unstructured Byte Stream Data Plane API

The colloquial word “file” points us toward persistent, seekable storage, which implies a backing random-access array, with special syscalls like `pread`, `pwrite`, `fsync`, `truncate`, and metadata updates. This is already way too structured to fit other kernel resources like sockets, pipes, timers, and event sources.

This trick is to get rid of this structure, only restrict the "file" to being a [byte stream](https://blog.sunfishcode.online/is-everything-a-file#so-what-if) which we interact with through `read` and `write`.

> The UNIX philosophy is often quoted as "everything is a file", but that really means "everything is a stream of bytes".

This uniformity is genuinely [powerful](https://www.tedinski.com/2018/01/30/the-one-ring-problem-abstraction-and-power.html). Programs can read from stdin and write to stdout without caring much whether those streams are connected to a terminal, a file, a pipe, or a socket. Behind the scenes, the kernel is doing the hard work: on a regular file, `read` means something like “copy bytes from persistent storage at the current offset.” On a pipe, it means “receive the next bytes in a stream.” On a socket, it means “receive bytes from a connection.” On a timerfd, it means “consume timer expirations encoded as bytes.” On an inotify fd, it means “consume filesystem event records.” Shell pipelines then "just work" because byte streams compose.

#### **Data Plane is about Composition**

It's worth being precise about *what* is powerful here: the win is **composition** — independent tools chained through one uniform interface — not the unstructuredness of the bytes. The two are separable, and [Tedinski][tedinski-unix] argues we routinely conflate them. Structured pipelines compose just as freely, without forcing every stage to re-parse text.

The deeper issue is that an fd is really a *dynamic union type*. In C it is just an integer; the compiler has no idea whether it points at a file, pipe, socket, or timer, and the kernel decides at runtime whether `lseek(fd, …)` means anything. So the honest slogan is not

```txt
everything is a file
```

but something closer to

```txt
everything is a FilePipeDirectorySocketSerialPortTimerEventEpollPidInotifyTTY...
```

a uniform handle over a type resolved only at runtime, with an operation set that is only partially shared. Modern programming is moving the other way, toward typed and structured interfaces; the unstructured byte stream is just the lowest common denominator the kernel can hand to everyone, and even on the data plane, [structure wins](#the-future-is-more-structured-not-less). The control plane is where that dynamic type comes roaring back hardest.

#### **Control Plane Doesn't Fit in a Byte Stream**

This power on the data plane was quickly recognized, and extended to the control plane. User space programs can now read from any resource uniformly, but event loops broke since not all resources could be uniformly waited on. Over time Linux extended readiness/waitability via `poll`/`select`/`epoll` for more and more resource types, until now you can wait on regular files, sockets, pipes, timers, event sources, and even processes through pidfds.

Hence the generic core FD API we landed on is something like:

```txt
read/write:  byte stream data plane
poll/epoll:  readiness/waitability control plane
dup:         explicit handle passing
close:       release
```

But this is the extent of the uniformity, since resources ultimately expose very different control planes that can't fit in a single unified API:

```txt
regular file:  lseek, fsync, truncate, chmod, flock
socket:        bind, listen, accept, connect, setsockopt, shutdown
terminal:      termios, window size, job control
serial port:   baud rate, parity, flow control
timerfd:       timerfd_settime / timerfd_gettime
epoll:         epoll_ctl
inotify:       inotify_add_watch / inotify_rm_watch
block device:  flush, discard, geometry-ish controls
GPU buffer:    map, fence, submit command buffer
```

These are resource-specific control surfaces. We could expose all of these via VFS writes. As Linus [mentions][linus-eiaf], we could imagine replacing socket syscalls with something like:

```txt
open("/dev/socket")
write(fd, "connect stream 25")
```

This is equivalent, in some sense, to `socket()` plus `connect()`. However, his objection is that it moves the real operation into a string protocol. You still need to encode, parse, validate, and implement all the socket-specific details. Calling the transport `read` and `write` does not make the protocol simple.

Instead, Unix often puts them in side APIs like `ioctl`, `sysctl`, `fcntl`, `setsockopt`, `getsockopt`, `mmap`, `epoll_ctl`, or special-purpose syscalls. The generic interface never eliminates the specific protocol. It only chooses where to hide it.

The same limitation appears even when the thing you want to move *is* a descriptor itself! Writing the bytes `"3"` down a pipe only sends a number that means something in your fd table and nothing in the receiver's; passing the actual handle needs an out-of-band control channel, which Unix domain sockets carry as ancillary data (`SCM_RIGHTS`) so the kernel can install a fresh fd in the receiver pointing at the same open file object. Once again, the byte stream alone is not enough.

## A better model

Instead of asking whether something “is a file,” think about resources first and ask a few separate questions:

1. How is it named, found, or created? Maybe by pathname, PID, URL, DNS name, socket address, creation syscall, SQL query, service name, inherited handle, or linked import.
2. After that, how do I keep referring to it? Maybe by repeatedly using a name resolved in some namespace, or by converting it into a more local reference such as a file descriptor, capability, token, object reference, Mach port, Windows `HANDLE`, Wasm resource, or seL4 capability slot.
3. What protocol does it speak? Maybe random-access storage, byte stream, datagram messages, append-only log, RPC, query, pub-sub, shared memory, real-time media, or resource-specific control operations like `ioctl`, `fcntl`, and `setsockopt`. [[^2]]

These layers are easy to confuse because Unix connects them so smoothly behind shell commands. `cat /proc/self/status` looks like a single operation on a file, but it runs the whole pipeline: pass a pathname, resolve it with `open`, receive an fd, then repeatedly `read` bytes. But the moment the descriptor refers to a socket, pipe, timer, process, or event source, the layers come apart.

### The future is more structured, not less

If there's a direction of travel, it's toward *more* structure, not less. The interfaces that are actually getting better are the ones layering types, schemas, and explicit message formats on top of — or instead of — the raw byte stream:

- **Typed RPC**: gRPC/protobuf, Cap'n Proto, and Thrift replace "write a string, parse the reply" with a schema both ends agree on.
- **Structured submission**: `io_uring` swaps the per-syscall `read`/`write` dance for explicit submission and completion queues, and `netlink` long ago replaced socket `ioctl`s for network configuration with structured messages.
- **Object pipelines**: PowerShell and nushell pass typed records and tables between commands instead of re-parsing columnar text at every stage.
- **Typed component interfaces**: the WebAssembly Component Model and WASI describe imports and exports with an IDL (WIT) rather than a `void*` ABI.

In each case the byte stream didn't win; structure did.

And yet the pull of "everything is a file" never fully releases — people keep wanting to reinvent Plan 9. [omnifs][omnifs] is just the latest: project GitHub, DNS, and arXiv into a filesystem and `cat` your way around the cloud. It's a genuinely fun idea, and that's exactly why it recurs: paths and `cat` are a universal, beautifully composable interface.

But the critiques are old and still unanswered. Rich Hickey, in [Simple Made Easy][hickey-sme]:
> Are we all not glad we don't use the Unix method of communicating on the Web? Any arbitrary command string can be the argument list for your program, and any arbitrary set of characters can come out the other end. Let us all write parsers.

[Tedinski][tedinski-unix] makes the structural version of the same point: the slogan gets credit for the wrong thing. What actually makes Unix powerful is *composition*, not the filesystem metaphor, and unstructured text is a leaky universal interface — it's why `/sys` and `/proc` exist yet we still reach for tools like `lspci`, and why reading a few `/proc` fields in a row can hand you a snapshot that never existed (negative counters, over-100% usage). His prescription lands in the same place as Hickey's: structured, typed streams compose *better* than text, not worse.

So the honest synthesis is the three-question model. Keep the parts of the file idea that earned their keep — resolve once, hold a handle, let independent tools compose — but drop the pretense that the *protocol* wants to be an unstructured byte stream. The handle stays uniform; the thing it speaks is getting more typed, not less.

## TLDR

Three meanings hid in one slogan, and they deserve three different verdicts:

1. **Naming — not everything belongs in one namespace.** The filesystem is a great place to expose nameable, hierarchical, byte-inspectable things (`/proc`, `/sys`, `/dev`) and a bad place for everything else. A pathname is not free real estate; a rich, stateful, or security-sensitive resource just becomes a small protocol wearing a filename. Use VFS where it fits, and stop there.
2. **The handle — the file descriptor is the one idea worth keeping.** Resolve once, hold a reference, use it without looking it up again: that is the genuinely good part of the Unix philosophy, and everything else rides on it. It generalizes well beyond Unix — Mach ports, Windows `HANDLE`s, Wasm resources — and gets *better* when you push it further into [capabilities][fd-capabilities], where the handle itself carries unforgeable authority. If you keep one thing, keep this.
3. **The byte stream — a dumb outdated universal interface.** `read`/`write` over an unstructured stream is a reasonable default for *moving* bytes and useless the moment you need to *say something* about them. The control plane always comes roaring back as `ioctl`/`setsockopt`/special syscalls, or as a string protocol you have to parse. "Everything is a byte stream" is the part of the slogan to retire; the future is more structured, not less.

## References <!-- omit in toc -->

1. [Is everything a file? - sunfishcode][sunfish-eiaf]
2. [Case study: Unix philosophy - Tedinski][tedinski-unix]
3. [The everything-is-a-file principle - Linus Torvalds][linus-eiaf]
4. [Completing the pidfd API - LWN.net][pidfd-lwn]
5. [What is a pidfd? - Corsix][pidfd-corsix]
6. [The UNIX system call interface is inadequate - D. J. Bernstein][twofd-djb]
7. [The UNIX File Abstraction - OpenCSF][opencsf-unix-file]
8. [Problems in the Design of Unix - The Art of Unix Programming][taoup-unix-problems]
9. [Overview of the Linux Virtual File System - Linux kernel docs][linux-vfs-file-object]
10. [File descriptors as capabilities - Wikipedia][fd-capabilities]
11. [Plan 9 from Bell Labs][plan9]
12. [9P (protocol) - Wikipedia][9p]
13. [omnifs: open a path, read the world][omnifs]
14. [Simple Made Easy - Rich Hickey][hickey-sme]

[sunfish-eiaf]: https://blog.sunfishcode.online/is-everything-a-file/ "Is everything a file? - sunfishcode"
[tedinski-unix]: https://www.tedinski.com/2018/05/08/case-study-unix-philosophy.html "Case study: Unix philosophy - Tedinski"
[linus-eiaf]: https://yarchive.net/comp/linux/everything_is_file.html "The everything-is-a-file principle - Linus Torvalds"
[pidfd-lwn]: https://lwn.net/Articles/794707/ "Completing the pidfd API - LWN.net"
[pidfd-corsix]: https://www.corsix.org/content/what-is-a-pidfd "What is a pidfd? - Corsix"
[twofd-djb]: https://cr.yp.to/tcpip/twofd.html "The UNIX system call interface is inadequate - D. J. Bernstein"
[opencsf-unix-file]: https://w3.cs.jmu.edu/kirkpams/OpenCSF/Books/csf/html/UnixFile.html "The UNIX File Abstraction - OpenCSF"
[taoup-unix-problems]: http://www.catb.org/esr/writings/taoup/html/ch20s03.html "Problems in the Design of Unix - The Art of Unix Programming"
[linux-vfs-file-object]: https://docs.kernel.org/filesystems/vfs.html#the-file-object "Overview of the Linux Virtual File System - Linux kernel docs"
[fd-capabilities]: https://en.wikipedia.org/wiki/File_descriptor#File_descriptors_as_capabilities "File descriptors as capabilities - Wikipedia"
[plan9]: https://9p.io/plan9/ "Plan 9 from Bell Labs"
[9p]: https://en.wikipedia.org/wiki/9P_(protocol) "9P (protocol) - Wikipedia"
[omnifs]: https://github.com/0xff-ai/omnifs "omnifs: open a path, read the world"
[hickey-sme]: https://github.com/matthiasn/talk-transcripts/blob/master/Hickey_Rich/SimpleMadeEasy-mostly-text.md "Simple Made Easy - Rich Hickey"

## Footnotes <!-- omit in toc -->

[^1]: Capability-oriented microkernels like seL4 push the idea even further by exposing unforgeable capabilities stored in a process capability space. Those capabilities are fd-like in the important sense: they are local handles that carry authority. The kernel enforces possession and rights; the resource manager behind the handle may live in user space. In such a system, many resource managers that Unix puts in the kernel — filesystems, drivers, network services — move out of it: the filesystem server, not the kernel, understands what a “file” means, the driver server understands the device, and the network service understands the protocol stack.

[^2]: This whole model is local. A socket fd may connect to another machine, but the fd is still only the local endpoint as represented by this kernel. The protocol above it — HTTP, SQL, Raft, WebRTC, etc. — is not part of the fd abstraction. The kernel gives you a secure local mechanism for holding and operating on an endpoint; understanding what that endpoint *means* belongs to a higher semantic layer.
