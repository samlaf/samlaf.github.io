# Ring Buffers Design Space

Comparing the various families of ring buffers in the kernel

| | Ring shape | Completion | Addressing | Doorbell / suppression | Consumer & trust |
|---|---|---|---|---|---|
| **NIC desc ring** (ixgbe, e1000) | true ring of descriptors | in-place writeback, `DD` bit | DMA / IOVA | MMIO tail write; coalescing regs, NAPI | silicon; trusted (IOMMU retrofit) |
| **NVMe SQ/CQ** | paired rings, 64 B SQE / 16 B CQE | separate CQ, phase tag | DMA / IOVA, PRP or SGL | MMIO tail write; MSI-X coalescing | silicon; trusted |
| **virtio split** | 2 index rings + desc table (not a ring) | `used` ring, `(id, len)` | GPA (IOVA w/ vIOMMU) | MMIO notify → VM exit; `NO_NOTIFY`, `EVENT_IDX` | hypervisor; untrusted under TDX/SEV |
| **virtio packed** | one ring, descs in place | in-place, `AVAIL`/`USED` + wrap counter | GPA, or bounce buffer w/ `ACCESS_PLATFORM` | same as split | hypervisor or real HW (vDPA) |
| **Xen ring** | request + response ring pair | response ring | grant refs | event channel; `req_event` / `rsp_event` | peer domain; mutually untrusted |
| **io_uring** | index ring + inline 64 B SQEs | separate CQ, inline CQE | user VA, or index into registered buffers | `io_uring_enter`; `SQPOLL`, `IOPOLL` | kernel; trusted consumer, hostile producer |
| **AF_XDP** | 4 rings: fill, rx, tx, completion | completion ring | offset into registered UMEM | `sendto()` or busy-poll; `NEED_WAKEUP` | kernel; untrusted producer by design |
| **vhost** | virtio rings, host-side | virtio `used` | HVA via memory-region map | eventfd (kickfd / callfd) | kernel thread; trusted |
| **vhost-user / ublk** | virtio rings / `uring_cmd` | virtio `used` / CQE | shared mmap region | eventfd / io_uring | userspace daemon; roles inverted |
| **DPDK `rte_ring`** | pure ring of pointers | none — it's a queue, not a protocol | process VA in hugepages | none, spin | peer thread; same trust domain |

Three things I'd read off it.

The bottom-left corner of the table is where the ring stops being a device protocol and becomes just a queue — `rte_ring` has no completion concept at all, which is why it's the honest floor of the family.

The rows that arrived latest (io_uring, AF_XDP) are the ones using registered-region indices rather than raw addresses, and both were designed with an untrusted producer. That's not coincidence; it's the same pressure that Xen felt in 2004 and that TDX is now applying to virtio from the opposite direction.

And packed virtqueue is the row that migrates upward — it abandons virtio's own two-ring-of-indices design to land exactly on NVMe's phase-tag shape, because the consumer stopped being software.

## 5 axes comparison

**1. Is the descriptor array a ring, or is the ring an index into it?**

A NIC descriptor ring genuinely is a ring of descriptors: `head`/`tail` registers walk a circular array, slot *i* is both the request and (after writeback) the completion. NVMe is the same shape with SQ and CQ split apart. virtio split rings are the outlier — two rings of *indices* around a non-ring table — and this is precisely what packed virtqueues undid. A packed ring is one circular array of descriptors written in place, with a wrap counter plus `AVAIL`/`USED` flag bits telling you whose turn a slot is. That is NVMe's phase tag, and it exists because hardware implementers (vDPA, virtio NICs) wanted the shape silicon already knew how to build.

**2. Where does completion status land?**

- In-place writeback + status bit: e1000/ixgbe RX descriptors, where the device rewrites the descriptor and sets `DD`. One cache line total per packet, but you've destroyed your request.
- Phase/wrap bit in a separate ring: NVMe CQ, packed virtqueue. No consumer index to read back over PCIe.
- Separate ring with an index: virtio split `used`, Xen's response ring.
- Separate ring with an inline payload: io_uring CQ.

The Intel NIC style is the cheapest and the least expressive, which is fine when the only thing to report is "length and a few error flags."

**3. Address semantics.**

DMA rings carry bus addresses/IOVAs. virtio carries GPAs. io_uring carries user VAs. But there's a fourth model worth having in your head: **offsets into a pre-registered region**. AF_XDP descriptors are `(addr, len)` where `addr` is an offset into the UMEM the process registered up front; io_uring's `IORING_OP_READ_FIXED` and provided-buffer rings do the same with registered buffers; ublk does it with a preallocated area. That model exists because it makes validation O(1) and bounds-checkable, which is why it keeps reappearing wherever the producer isn't trusted. It's also the model TDX pushes virtio toward — SWIOTLB bounce buffers in shared pages are, functionally, a registered region the descriptors index into.

**4. Doorbell mechanism, and what it costs.**

| Design | Doorbell | Cost |
|---|---|---|
| NIC / NVMe | MMIO tail write | PCIe posted write |
| virtio (guest) | MMIO notify | VM exit (~1-2 µs) |
| vhost | eventfd write | syscall + wakeup |
| io_uring | `io_uring_enter` | syscall |
| AF_XDP | `sendto()` or busy-poll | syscall or none |
| DPDK / SPDK | none, pure poll | a burned core |

Every one of these has a suppression mechanism bolted on because the doorbell is the expensive part: `NO_NOTIFY`/`EVENT_IDX` in virtio, interrupt coalescing registers on NICs, `XDP_USE_NEED_WAKEUP` in AF_XDP, `SQPOLL` in io_uring, NAPI on the receive side generally. The convergence here is stronger than the convergence in the ring layouts.

**5. Who's on the other end, and do you trust them?**

This is the one that actually determines API shape, and it's the ordering I'd use:

- **Silicon** (NIC, NVMe): fixed-size descriptors, flat addressing, no faulting, no chained semantics beyond SG lists. Historically trusted; the IOMMU exists because that assumption was wrong.
- **A hypervisor pretending to be silicon** (virtio, and vDPA where it's silicon again): all of the above, plus feature negotiation, plus — under TDX/SEV — an explicitly untrusted consumer, which is what forces `ACCESS_PLATFORM` and the driver-hardening work.
- **A peer domain** (Xen ring): the direct ancestor. `xen/interface/io/ring.h` is a request/response ring pair with `req_event`/`rsp_event` fields and `RING_PUSH_REQUESTS_AND_CHECK_NOTIFY` — kick-with-suppression, verbatim, years before virtio. virtio's `EVENT_IDX` is that idea reimported. Both sides are guests, so both sides distrust each other, which is why Xen got there first.
- **The kernel** (io_uring): trusted consumer, hostile producer. Inline payloads, opcode namespace, references to kernel objects, faulting allowed.
- **A userspace daemon** (ublk, vhost-user, virtio-fs's FUSE-over-virtqueue): the roles invert — kernel produces, userspace consumes — and you inherit the untrusted-consumer problem from the CVM case even without a hypervisor.


## AF_XDP

The genuinely interesting family is AF_XDP — four rings (fill, rx, tx, completion) rather than two, because it separates "here are empty frames" from "here is data" on *both* directions. virtio-net fakes this with two virtqueues plus RX pre-posting; io_uring bolted it on later as provided-buffer rings. Four rings is arguably the honest factoring, and it's the one design in the list that was drawn with an untrusted producer, a registered region, and optional polling all in mind from the start.

## io_uring

Almost everything is inline in the ring itself:

![](/assets/networking-series/ring-buffers/io-uring.png)

The only real pointer chase is `addr` → user buffer, and the kernel resolves it by walking the submitting process's page tables — it can fault the page in if it isn't resident. The SQ ring of indices exists only so you can submit SQEs out of order; the common path is index `i` → `sqe[i]`.

## virtqueue

Note that the equivalent of the io_uring's SQE isn't in the ring at all — it's off in guest memory behind a descriptor:

![](/assets/networking-series/ring-buffers/virtqueue.png)
