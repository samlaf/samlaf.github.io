# Interconnects are networks

Talking to a device is two problems on the same wires, and each one has its own machinery. Most writing about storage and interconnects covers only the first.

1. **Data plane.** Moving bytes once you have a device: memory read and write TLPs, NVMe submission and completion queues, virtqueues.
2. **In-band control plane.** Finding and configuring devices using the device transport itself: config read and write TLPs, enumeration, BAR sizing, bridge programming. It rides the same wires as the data.

A third problem, telling the OS what the buses cannot say about themselves, is solved by platform firmware off the wires entirely. It has [its own article](/programming/platform-firmware.html).

This article argues that both planes are networking. The buses became packet networks, they perform the same functions as Ethernet and TCP, and they face the same question of where reliability belongs.

## The data plane: a command set over a transport

Once the OS has a device, moving data through it is a four-layer stack, from "what the user wants" at the top down to wires at the bottom.

```
┌──────────────────────────────────────────────────────────────┐
│  Layer 4 — OS BLOCK LAYER                                    │
│  read()/write() on /dev/sda, /dev/nvme0n1, etc.              │
└──────────────────────────────────────────────────────────────┘
                              │
┌──────────────────────────────────────────────────────────────┐
│  Layer 3 — COMMAND SET  (the "verbs" the device understands) │
│                                                              │
│    ┌────────┐         ┌────────┐         ┌────────┐          │
│    │  SCSI  │         │  NVMe  │         │  ATA   │          │
│    └────────┘         └────────┘         └────────┘          │
└──────────────────────────────────────────────────────────────┘
                              │
┌──────────────────────────────────────────────────────────────┐
│  Layer 2 — TRANSPORT  (encapsulation, framing, flow control) │
│                                                              │
│   SCSI rides on:         NVMe rides on:      ATA rides on:   │
│   • Parallel SCSI        • PCIe (native)     • SATA          │
│   • SAS                  • RDMA  ┐           • PATA (legacy) │
│   • Fibre Channel (FCP)  • TCP   │ NVMe-oF                   │
│   • iSCSI (TCP/IP)       • FC    ┘                           │
│   • USB Mass Storage                                         │
│   • SRP (over RDMA)                                          │
│   • FCoE (over Ethernet)                                     │
└──────────────────────────────────────────────────────────────┘
                              │
┌──────────────────────────────────────────────────────────────┐
│  Layer 1 — PHYSICAL                                          │
│  Copper pairs, fiber optic, PCIe lanes, USB wires, RF, etc.  │
└──────────────────────────────────────────────────────────────┘
```

Concrete real-world mappings make it less abstract:

| Real-world setup | Command | Transport | Physical |
| --- | --- | --- | --- |
| Laptop SATA SSD (drive POV) | ATA | SATA | SATA cable |
| Same drive (as the OS sees it) | SCSI | (SAT) → SATA | SATA cable |
| Consumer/server NVMe SSD | NVMe | PCIe | PCIe lanes |
| AWS EBS volume on a Nitro instance | NVMe | PCIe (to the Nitro card) | PCIe lanes |
| NVMe/TCP storage array | NVMe | TCP | Ethernet |
| Old enterprise SAN | SCSI | Fibre Channel | Fiber optic |
| iSCSI SAN | SCSI | TCP/IP | Ethernet |
| USB thumb drive | SCSI | USB-MS (BOT) | USB cable |
| Modern USB-C SSD enclosure | SCSI | UAS over USB | USB-C cable |
| HBA + SAS expander shelf | SCSI | SAS | SAS cabling |
| InfiniBand storage array | SCSI | SRP over RDMA | IB cables |
| Modern IB storage array | NVMe | NVMe-oF/RDMA | IB cables |

The EBS row is the stack's main thesis in miniature. The guest sees an ordinary NVMe device on PCIe. Behind it, the Nitro card carries the request over AWS's internal network to the storage fleet. The guest-facing interface stays fixed while the transport behind the card is swapped out entirely.

**Two wrinkles worth knowing about the diagram:**

*Translation layers exist between command sets.* SAT (SCSI/ATA Translation) is the big one. SATA drives natively speak ATA, but the OS block layer historically grew up on SCSI, so almost every OS presents SATA drives as if they were SCSI. In Linux this is `libata`. The drive gets a `READ(10)` SCSI CDB, the kernel or HBA rewrites it as `READ DMA EXT` ATA, the drive responds in ATA, and the response is rewritten back into SCSI shape going up. From userspace it looks like SCSI all the way down, which is why a SATA drive shows up as `/dev/sda` (the `s` is for SCSI).

*Some "transports" are themselves stacks.* iSCSI is SCSI over TCP over IP over Ethernet: three layers of network protocol acting as one logical transport. FCoE is SCSI over FCP over Ethernet (no IP). NVMe-oF/TCP is NVMe over TCP over IP. The diagram flattens these, but you can slot in a "Layer 1.5 — network stack" between transport and physical whenever the transport is networked.

### Three interconnect models (why networking won)

![Diagram: shared vs switched vs networked interconnects](/assets/networking-series/devices/three-interconnected-models.png)

See [Shared, switched, or networked? The uncharted future of on-chip buses](https://www.eetimes.com/shared-switched-or-networked-the-uncharted-future-of-on-chip-buses/) (EE Times).

This article ran in September 2002, two months after PCI-SIG released the PCIe 1.0 spec. The off-chip world had just committed to switched point-to-point links, and the on-chip world was standing at the identical fork in the road.

The physics driving it is the same physics that capped parallel PCI. The article opens with multiple peripherals on a bus causing electrical loading that limits attainable clock rates: the multi-drop load problem that birthed the PCI-PCI bridge. Its first workaround is LSI's customers using segmented buses with bridges between segments, tuning each subsystem separately, at the cost of latency between segments and heavy up-front partitioning. That is the PCI bridge hierarchy (see the control plane below) reinvented on silicon. Same primitive, same tradeoff.

The escalation ladder matches too. The article lays out three strategies: widen the bus, speed up the bus, or give every master its own point-to-point connection, which yields a switched architecture. Strategies 1 and 2 are what PCI did (32→64 bit, 33→66 MHz, then PCI-X at 133 MHz) until it hit the wall; strategy 3 is PCIe. The on-chip instances, ARM's multi-layer AHB interconnect matrix with per-slave arbitration and MIPS's SoC-It five-by-five crossbar, are functionally a PCIe switch. Masters get dedicated paths, contention moves from "arbitrate for the wire" to "arbitrate at the destination port", and concurrent transfers become possible because there is no longer one shared medium.

The most prescient part is the last section. Sonics' SiliconBackplane put a network "agent" next to each IP core, speaking OCP to the core and a packetized protocol between agents, borrowing the networking insight that standard protocol stacks decouple the interconnect from the devices. That is a network-on-chip in 2002, before the term was mainstream, and NoC is what won. Every serious SoC today (AMD Infinity Fabric, Arm CMN mesh, Intel's ring and mesh, Apple's fabric, every NVIDIA GPU's crossbar) is packets over point-to-point links with routers.

The decoupling argument is the thread running through this whole article. OCP's pitch (the core publishes requests, the interconnect figures out delivery) is the move PCIe made with config space, aimed at a different consumer. PCIe decoupled *software* from the interconnect: it kept the 1992 bus/bridge/tree fiction stable so drivers and enumeration code never noticed the fabric change from shared wires to a packet network. OCP and AXI decoupled *IP blocks* from the interconnect: keep the socket stable so the fabric can be a crossbar today and a mesh tomorrow. In both cases the winner wasn't just "switch beats bus" but "define a stable interface, then swap the transport freely behind it."

The same design shows up at every scale: on-chip NoCs, die-to-die links (UCIe, which carries PCIe and CXL protocol over chiplet links), board-level PCIe, rack-level NVLink and CXL fabrics, datacenter Ethernet and InfiniBand. Shared buses are extinct at every layer; everything is packets over two-party links. The one thing that *didn't* converge is the software model, which is why "bus 4" still shows up in `lspci` a quarter century later. That software model is the control plane, below.

### PCIe layering

```
════ PCIe Transaction Layer (TLPs: MemRd, MemWr, CfgRd/Wr, Cpl) ════
════ PCIe Data Link Layer (DLLPs: seq#, LCRC, ACK/NAK, credits) ════
════ PCIe Physical Layer (lanes, 128b/130b, Start/End framing)  ════
```

Data-plane traffic is `MemRd`, `MemWr` and their completions. Config TLPs travel through exactly the same three layers, which is what makes the control plane in-band.

### PCIe vs Ethernet

```
  PCIe stack                            Internet / Ethernet stack
  ──────────────────────────            ──────────────────────────

┌──────────────────────────┐          ┌──────────────────────────┐
│ Software / Requester     │  ◄────►  │ Application (HTTP, SSH)  │
│ NVMe/SCSI/GPU driver     │          │                          │
│ builds the request       │          │                          │
└────────────┬─────────────┘          └────────────┬─────────────┘
             │ payload                             │ payload
             ▼                                     ▼
┌──────────────────────────┐          ┌──────────────────────────┐
│ Transaction Layer (TLP)  │  ◄────►  │ Transport (TCP)          │
│  adds: Header, Data,     │          │  adds: TCP header,       │
│        ECRC              │          │        checksum          │
│  end-to-end integrity    │          │  end-to-end reliability  │
│  credit-based flow ctrl  │          │  windowed flow ctrl      │
└────────────┬─────────────┘          └────────────┬─────────────┘
             │                                     │
             │ (no separate network                ▼
             │  layer: the TLP header    ┌──────────────────────────┐
             │  carries routing inline:  │ Network (IP)             │
             │  address, ID, or implicit)│  adds: IP header         │
             │                           │  addressing/routing      │
             │                           └────────────┬─────────────┘
             ▼                                        ▼
┌──────────────────────────┐          ┌──────────────────────────┐
│ Data Link Layer (DLLP)   │  ◄────►  │ Data Link (Ethernet MAC) │
│  adds: Sequence #, LCRC  │          │  adds: MAC header, FCS   │
│  hop-by-hop reliability  │          │  hop-by-hop framing      │
│  ACK/NAK + replay buffer │          │  (no retry — drops)      │
└────────────┬─────────────┘          └────────────┬─────────────┘
             ▼                                     ▼
┌──────────────────────────┐          ┌──────────────────────────┐
│ Physical Layer           │  ◄────►  │ Physical (Ethernet PHY)  │
│  adds: Start, End frame  │          │  adds: preamble, SFD     │
│  128b/130b encoding      │          │  64b/66b, PAM-4          │
│  lane training (LTSSM)   │          │  auto-negotiation        │
│  differential signaling  │          │  differential signaling  │
└──────────────────────────┘          └──────────────────────────┘
```

One correction to the naive mapping: PCIe's reliability actually comes from the data link layer's hop-by-hop ACK/NAK replay, which does not drop TLPs on a healthy link. ECRC is an optional end-to-end *integrity* check, not a retransmission mechanism like TCP's.

### Where reliability lives

That correction is the interesting part. PCIe and Ethernet make opposite choices about the same function. Ethernet drops a corrupt frame and leaves recovery to TCP at the two ends. PCIe retries every TLP at every hop from a replay buffer, and almost never loses one.

Ethernet's choice is the textbook one. Saltzer, Reed and Clark's [end-to-end argument](https://en.wikipedia.org/wiki/End-to-end_principle) (1981, revised 1984) says a function such as reliable delivery "can completely and correctly be implemented only with the knowledge and help of the application standing at the endpoints." (Same Saltzer as [RFC 1498](https://www.rfc-editor.org/info/rfc1498/).) Their example is careful file transfer. Per-hop checks can't catch a bit flipped in a router's memory, or a bug in the file system that wrote the file. The only complete check is a checksum over the whole file, compared by the two ends. Every check below that is a performance enhancement, worth adding only when it pays for itself.

PCIe doesn't violate the argument. It takes the performance-enhancement clause, priced for a link. The argument is economic: on a large network whose loss rate varies, reliability in the middle costs more than retransmission at the ends. A PCIe link is the opposite case. It is centimeters long and nearly lossless, and its latency budget is in nanoseconds. Replaying a TLP from the neighbor's buffer is cheap. Letting the loss surface at the NVMe driver costs a command timeout, 30 seconds by default on Linux. So the link retries, and the ends still check:

- **ECRC**, when enabled, covers a TLP across switches, including a switch's internal buffers, which LCRC never sees.
- **NVMe command timeouts** and the block layer's retries catch commands that never complete.
- **File system checksums** (ZFS, btrfs) are the careful file transfer, verbatim. They catch what every hop below missed, including the drive's own firmware.

RINA reads the same facts differently. In RINA every layer runs the same error and flow control protocol (EFCP, based on Richard Watson's delta-t work), with policies chosen for that layer's scope. Matta's group at Boston University spell out its structure in [Declarative Transport](https://www.cs.bu.edu/fac/matta/Papers/hotnets7-paper40.pdf), subtitled "No more transport protocols to design, only policies to specify." EFCP splits in two. The data transfer protocol (DTP) holds what must travel with the data: delimiting, fragmentation, sequence numbers, addresses, checksums. The data transfer control protocol (DTCP) holds the loosely coupled mechanisms: acknowledgement, retransmission, flow control and congestion control, each one switched on and tuned by policy. Whether a flow has a DTCP at all is itself a policy. Without one, each PDU is sent once, at whatever rate the layer below allows. PCIe's data link layer and TCP are then one function at two scopes. A link-scope layer uses aggressive local retry because loss is rare and retry is cheap. An internet-scope layer retransmits from the ends because the middle is large and varies. The end-to-end argument still holds inside each layer, where "end" means the ends of that layer. What RINA drops is the Internet's fixed placement, where only TCP may retransmit and every layer below must not. The IRATI team make this concrete: their VM-to-VM tests use a flow with flow control but no retransmission control. TCP/IP has no transport with that combination, since UDP has neither and TCP has both.

### Virtio

Virtio is a transport, not a command set. It belongs on Layer 2 alongside PCIe, SAS and TCP, but it is a virtual transport. It defines an efficient way for a guest VM to move command and data buffers to and from a host, hypervisor or device emulator when there is no real link in the middle, just a software boundary.

```
┌──────────────────────────────────────────────────────────────┐
│  Layer 4 — OS BLOCK LAYER (in the GUEST)                     │
│  read()/write() on /dev/vda                                  │
└──────────────────────────────────────────────────────────────┘
                              │
┌──────────────────────────────────────────────────────────────┐
│  Layer 3 — COMMAND SET                                       │
│  virtio-blk's own tiny command set, OR virtio-scsi (= SCSI), │
│  OR (newer) NVMe-over-virtio                                 │
└──────────────────────────────────────────────────────────────┘
                              │
┌──────────────────────────────────────────────────────────────┐
│  Layer 2 — TRANSPORT                                         │
│  virtio's virtqueues (descriptor rings in shared memory)     │
│   ─ surfaced to the guest as either:                         │
│       • virtio-pci  (a fake PCIe device)                     │
│       • virtio-mmio (a fake MMIO device, common on ARM/RISCV)│
│       • virtio-ccw  (on s390)                                │
└──────────────────────────────────────────────────────────────┘
                              │
┌──────────────────────────────────────────────────────────────┐
│  Layer 1 — "PHYSICAL"                                        │
│  Not physical at all — shared memory between guest and host  │
│  + a notification mechanism (vmexit, ioeventfd, MSI)         │
└──────────────────────────────────────────────────────────────┘
```

The three surfacings differ mostly in the control plane, not the data plane: the virtqueues are the same, but how the guest *finds* the device is completely different. Only virtio-pci is found in-band; the others are the platform firmware's problem.

virtio-net shows what happens when the transport is dressed up as the wrong thing. It presents a full Ethernet NIC to the guest, with a MAC address, an MTU, TSO and checksum offload, although nothing between guest and host is Ethernet. The IRATI project built the alternative: a shim DIF for hypervisors that exposes the shared-memory channel directly as a RINA layer. An application whose peer is on the host uses that layer with nothing above it, because it is the lowest layer whose scope covers the peer. In their host-to-VM test the unoptimized prototype beat both an emulated e1000 and virtio-net. VM-to-VM, through a normal layer stacked on two shims, virtio-net came out slightly ahead. vsock is Linux's own answer to the same mismatch: sockets addressed by context ID and port, with no Ethernet in between.

### The same functions at every scope

The PCIe vs Ethernet diagram lines up layers, and the layers don't match: PCIe has no network layer, and Ethernet has no retry. Lining up functions works better. The IRATI chapter lists what every RINA IPC process does:

- **Data transfer:** delimiting, addressing, sequencing, relaying, multiplexing, lifetime termination, error check, encryption.
- **Data transfer control:** flow control and retransmission control.
- **Layer management:** enrollment, routing, flow allocation, namespace management, resource allocation, security management.

PCIe and the Internet stack against that list:

| Function | PCIe | Ethernet + IP + TCP |
| --- | --- | --- |
| delimiting | TLP, framed by Start and End symbols | Ethernet frame; TCP has none, it is a byte stream |
| addressing | memory address, or bus/device/function ID | MAC, IP address, port |
| relaying | switches route TLPs by address or ID | Ethernet switches, IP routers |
| multiplexing | traffic classes onto virtual channels | ports onto IP, protocols onto Ethernet by EtherType |
| lifetime termination | none needed: a tree has no loops | IP TTL |
| sequencing, loss detection | sequence numbers, per hop | TCP sequence numbers, end to end |
| retransmission control | ACK/NAK and replay, per hop | TCP, end to end |
| flow control | credits, per hop | TCP window, end to end; PAUSE frames, per hop |
| error check | LCRC per hop; ECRC end to end, optional | FCS per hop; TCP checksum end to end |
| encryption | IDE, optional | MACsec, IPsec, TLS |
| enrollment | enumeration assigns bus numbers and BAR addresses | DHCP, ARP |

Every row is filled on both sides. What changes is the scope each function runs at and the policy it uses. That is the IRATI chapter's claim about layers: they aren't units of modularity but "distributed resource allocators", performing the same functions over different ranges of bandwidth, QoS and scale.

[Part 1](/programming/networking-is-ipc.html) does the same exercise for every boundary a message can cross, from a function call to a broker. Its table has no group for the host ↔ device boundary. From this article, that group would read:

| | Reliable ordered | Framing | Msg types | Req/resp IDs | Mux + flow ctl | Session resume | Crypto | Peer identity |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **PCIe** (TLPs) | per hop | TLP | TLP type | tag | VCs, credits | — | IDE opt | BDF; SPDM opt |
| **NVMe** (over PCIe) | inherits | 64 B SQE | opcode | command ID | per queue | — | — | inherits |

## The control plane rides the same wires

PCI is self-enumerating: the OS can discover every device on the bus by reading the bus itself. The discovery and configuration traffic uses the same transport as the data, just different TLP types.

### Config space and how the CPU reaches it

Every PCI function has a config space: 256 bytes on PCI, 4 KiB on PCIe. It holds the vendor and device IDs, the class code, the header type, the BARs (Base Address Registers), and capability lists for things like MSI-X and power management.

On PCIe the CPU reaches config space through **ECAM** (Enhanced Configuration Access Mechanism). ECAM is a window of physical address space where each function's config space sits at a fixed offset:

```
ECAM address = ECAM_base + (bus << 20) + (device << 15) + (function << 12) + register

  CPU load/store          root complex               link(s)               device
  to ECAM address  ───►  turns it into a     ───►  CfgRd0 / CfgWr0   ───►  function's
                         config TLP                (Type 0: this bus)      config space
                                                   CfgRd1 / CfgWr1
                                                   (Type 1: forwarded by
                                                    bridges downstream)
```

A config access is an ordinary load or store from the CPU's point of view. The root complex turns it into a config TLP, routed by bus/device/function ID rather than by address. Bridges forward Type 1 requests downstream and convert them to Type 0 when they reach the target bus.

### Enumeration: walking the tree

The OS (or firmware, earlier) finds devices with a depth-first walk:

```
scan(bus):
  for dev in 0..31, fn in 0..7:
    vendor = cfg_read(bus, dev, fn, 0x00)
    if vendor == 0xFFFF: continue              # nothing there
    if header_type == 0:                       # endpoint
      size BARs, assign addresses
    if header_type == 1:                       # PCI-PCI bridge
      primary = bus
      secondary = next_free_bus++
      subordinate = 0xFF                       # temporary: route everything below
      scan(secondary)
      subordinate = highest bus number found below
      program memory / IO windows to cover the children's BARs
```

Three mechanisms carry the whole control plane:

- **BAR sizing.** Write all ones to a BAR, read it back, and the bits the device kept at zero give the size: size = \~(readback & mask) + 1. The OS then writes the address it chose. From then on, the device's registers answer `MemRd`/`MemWr` at that address, which is the hand-off to the data plane.
- **Bridge programming.** Each bridge's primary, secondary and subordinate bus numbers tell it which Type 1 config requests to forward. Its memory and IO windows tell it which memory TLPs to forward downstream. The tree of bus numbers is a routing table.
- **Interrupts as memory writes.** With MSI and MSI-X, the OS programs a target address and data value into the device's capability structure. Raising an interrupt is then just a `MemWr` TLP to that address. It is a control signal carried entirely on the data path.

One thing enumeration cannot do is start itself. The walk needs to know where ECAM lives, which bus numbers exist below the host bridge, and which memory windows the root complex decodes. Config space can't tell you where config space is. That answer comes from platform firmware, through ACPI or devicetree, which is [its own article](/programming/platform-firmware.html).

### From PCI to PCIe

PCIe kept this software model verbatim so that 1990s enumeration code would still work, but replaced the physical layer entirely. A PCIe "bus" behind a downstream port is a point-to-point link with exactly one device on it (device 0), and a switch's internal "bus 4" has no wires at all. Both are just numbers written into Type 1 headers so the tree-walking algorithm above has something to walk.

Because a PCIe link is point-to-point, the bus behind any downstream port can only ever contain device 0 (one device, possibly multi-function). So the tree behind a switch always looks like: bridge → single-device bus → bridge or endpoint. The one place a "bus" can still hold multiple devices is a switch's internal virtual bus (devices 1–4 on bus 4 in the diagram), which is exactly the one bus that doesn't physically exist. The only populated buses left in PCIe are the fake ones; every real link is a bus of one.

![Diagram: PCIe switched network vs software bus model](/assets/networking-series/devices/switch.png)

This is where the two planes meet. The electrical and protocol reality is a switched network of two-party links. The software model is a 1992 shared-bus tree. Neither describes the other honestly, so the spec builds a translation layer: virtual bridges and virtual buses dress the switched network up as a bus hierarchy for config space. Five "devices" on a "bus" is the costume, not the machine.

The crisp summary: buses are gone from the hardware, and links are gone from the software model. "Point-to-point" describes the hardware; "bus 4" describes the fiction. Switches live exactly at the seam, being a packet router in reality and a bag of bridges in config space.

![Diagram: PCI config space](/assets/networking-series/devices/pci-config-space.png)

## References

- [Comparing virtio, NVMe, and io\_uring queue designs](https://blog.vmsplice.net/2022/06/comparing-virtio-nvme-and-iouring-queue.html)
- [Virtio devices and drivers overview (Red Hat)](https://www.redhat.com/en/blog/virtio-devices-and-drivers-overview-headjack-and-phone)
- [Shared, switched, or networked? The uncharted future of on-chip buses (EE Times)](https://www.eetimes.com/shared-switched-or-networked-the-uncharted-future-of-on-chip-buses/)
- [PCI Express TLP primer (Xillybus)](https://xillybus.com/tutorials/pci-express-tlp-pcie-primer-tutorial-guide-1)
- [PCIe part 1 (ctf.re)](https://ctf.re/windows/kernel/pcie/tutorial/2023/02/14/pcie-part-1/)
- [PCI Express primer 1: overview and physical layer (Simon Southwell)](https://www.linkedin.com/pulse/pci-express-primer-1-overview-physical-layer-simon-southwell)
- [Video](https://www.youtube.com/watch?v=3ic61kJNEQ0)
- [Linux kernel PCI documentation](https://docs.kernel.org/PCI/index.html)
- J. Saltzer, D. Reed, D. Clark, [End-to-end arguments in system design](https://web.mit.edu/Saltzer/www/publications/endtoend/endtoend.pdf), ACM TOCS, 1984. Summary: [End-to-end principle (Wikipedia)](https://en.wikipedia.org/wiki/End-to-end_principle).
- E. Grasa et al., [Recursive InterNetwork Architecture, Investigating RINA as an Alternative to TCP/IP (IRATI)](https://www.riverpublishers.com/pdf/ebook/chapter/RP_9788793519114C16.pdf), River Publishers, 2017.
- J. Day, I. Matta, K. Mattar, "Networking is IPC: a guiding principle to a better Internet", CoNEXT 2008.
- [Declarative Transport: No more transport protocols to design, only policies to specify](https://www.cs.bu.edu/fac/matta/Papers/hotnets7-paper40.pdf), Boston University, HotNets-VII submission, 2008.
