---
title:  "Multiplexing, from first principles: floors, carving, and height"
category: programming
---

Multiplexing means sharing one resource among many users. Time-division multiplexing (TDM) is still everywhere, in Wi-Fi, 5G, Bluetooth, and your OS scheduler, but rarely in its textbook "fixed slot per user" form. Modern systems combine several kinds of sharing at once. This article sorts all of them into a single picture.

## The big picture

A communication channel offers three nested things to share:

1. **Floors**: independent physical channels, meaning spatial modes × polarizations.
2. **Carving**: each floor is a time × frequency plane with about **2WT degrees of freedom** (bandwidth W, duration T), which can be divided among users in many ways.
3. **Height**: the power poured onto each patch of a floor, which sets how many bits that patch carries: **log₂(1 + SNR)**.

Capacity ≈ floors × 2WT × log₂(1 + SNR).

Two more things cut across all three levels: the **allocation policy** (who decides who gets what: static assignment, a scheduler, contention, or a shared queue) and the **logical layers** stacked on top (identifiers, overcommit).

## Level 1: floors

A **mode** is a field pattern that passes through the channel without mixing with the others, so each one can carry its own signal. In MIMO the modes are the SVD of the channel matrix H = UΣVᴴ. The transmitter drives pattern vᵢ, the receiver listens with uᵢ, and σᵢ is that mode's strength. The number of strong singular values is the number of usable floors, at most min(N, M) for N transmit and M receive antennas. **Polarization** doubles every spatial mode, because the electromagnetic field is a vector with two orthogonal orientations.

![Level 1: spatial modes from the SVD of H, each split into two polarizations](/assets/multiplexing/level1-floors.svg)

How many floors physics allows comes down to diffraction. A wave of wavelength **λ** leaving an aperture of size D spreads at about λ/D, so over a distance **R** it makes a spot of size λR/D. The number of distinguishable spots, the Fresnel number, is:

> modes per transverse axis ≈ D_tx · D_rx / (λR), and the total is roughly that squared

Some consequences:

- **Lasers** have tiny λ, so even 10 cm optics over 1 km give about 40 modes.
- **Wi-Fi** in pure line of sight gets only one usable mode, because its Fresnel number is far below one. Its 4×4 MIMO works only because walls scatter the signal, turning the room into a large virtual aperture.
- **Satellites** use spot beams to separate *different users on the ground*, not to give one link several streams.
- **Wires** carry as many floors as they have guided modes. Single-mode fiber gives 2 (two polarizations), multi-core fiber gives 2 per core, and twisted pair, coax, and multimode fiber are usually run as one floor each. A multi-pair cable is a multi-floor channel, which is why DSL vectoring and Gigabit Ethernet need MIMO-style crosstalk cancellation.

## Level 2: carving a floor

Time, frequency, and code are not separate dimensions. They are different **bases for the same 2WT plane**. TDMA, FDMA, OFDMA, and CDMA all divide the same pie and differ only in engineering trade-offs. CDMA gives each user an orthogonal "texture" spread over the whole floor. OTFS (delay-Doppler) is yet another basis.

![Level 2: one floor carved by TDMA, FDMA, OFDMA, and CDMA](/assets/multiplexing/level2-carving.svg)

## Level 3: height (power)

Each patch carries log₂(1 + P/N) bits, so **every extra bit costs a little more power than all the previous bits combined**: N for the first bit, then +2N, +4N, +8N.

- **NOMA** gives different steps of this staircase to different users and separates them with successive interference cancellation.
- **Higher-order QAM** is the same staircase for one user; 16-QAM is two QPSK constellations superimposed.
- **Water-filling** decides how to spread a fixed power budget. Each tile's or mode's noise floor is N/|h|² (or N/σᵢ²), set by levels 1 and 2. Pour power up to a common level μ, and tiles whose floor sits above μ get nothing.

![Level 3: the power staircase and water-filling](/assets/multiplexing/level3-power.svg)

## Who decides: allocation policy

Every level can be allocated in four ways:

- **Static** assignment is deterministic but wastes idle capacity.
- **Scheduled** allocation grants resources before anyone transmits. It's efficient but needs a coordinator.
- **Contention** needs no coordination: conflicts are resolved by collision and retry, which collapses under load (slotted ALOHA peaks around 37% utilization).
- **Queued** (statistical) allocation gives nobody a slice. Everyone shares one queue, and buffers absorb the bursts.

| Level | Static | Scheduled | Contention | Queued (statistical) |
|---|---|---|---|---|
| **Floors** | Cell reuse plans, CPU pinning, fixed MIG slices | MU-MIMO user grouping, beam scheduling, thread placement | Wi-Fi 6 spatial reuse, work stealing | One work queue feeding many cores (thread pools), load balancer feeding a server pool |
| **Carving: time** | T1/E1, GSM slots, TSN, ARINC 653 | LTE/5G scheduler, OS scheduler | ALOHA, CSMA/CA, spinlocks, CAS retry | Packet switching (router and switch egress queues), NVMe and io_uring submission queues |
| **Carving: frequency** | Broadcast licenses, fixed DWDM grid | OFDMA resource blocks, CBRS spectrum access | Wi-Fi channel selection, listen-before-talk | — |
| **Carving: code** | GPS Gold codes | UMTS OVSF code allocation | LTE random-access preambles | — |
| **Height** | Fixed transmit power | Water-filling, link adaptation, turbo budgets | Uncoordinated power control between cells | — |
| **Naming** | Static IPs, VLAN IDs, SR-IOV VFs | DHCP, page-frame allocator | IPv6 duplicate address detection, UUIDs | — |

The empty cells in the last column are informative: queuing is a time-domain policy. You can buffer packets until the link frees up, but you can't buffer a frequency band or a code.

Packet switching is the best-known queued design. [Packets and circuits](/programming/packets-and-circuits.html#the-statistical-multiplexing-bet) covers what its statistical multiplexing buys, and what it costs.

## The full taxonomy

| Level | Dimension | What it is | Comms examples | Systems / compute analogues |
|---|---|---|---|---|
| **1. Floors** | Spatial modes | Singular vectors of H; count ≈ aperture²/(λR)² or number of guided modes | MIMO, separate wires, fiber cores, LoS-MIMO backhaul | Cores, sockets, GPU SMs and MIG, NUMA nodes, sharding |
| | Polarization | Two field orientations per spatial mode | Dual-pol coherent optics, satellite, microwave backhaul | No clean analogue |
| | Multi-user spatial reuse | Different receivers in different places | Spot beams, cellular reuse, MU-MIMO | Spreading work across racks or regions |
| **2. Carving** | Time | Slices along time | TDMA, TDD, CSMA/CA | CPU time-slicing, locks |
| | Frequency / wavelength | Slices along frequency | FDMA, WDM, OFDM | Loosely, SMT issue slots |
| | Time × frequency tiles | Both at once | OFDMA | Packing work into core × time slots |
| | Code / other bases | Orthogonal textures, delay-Doppler | CDMA, GPS, OTFS | None (compute isn't a linear medium) |
| **3. Height** | Power allocation | log₂(1 + SNR) bits per degree of freedom | Water-filling, QAM order selection | DVFS and turbo budgets (roughly cubic cost) |
| | Power-domain separation | Users on different steps of the staircase | NOMA, hierarchical modulation | — |
| **Cross-cutting** | Allocation policy | Static, scheduled, contention, or queued | See matrix above | See matrix above |
| | Naming | Identifiers layered on top | VLANs, MPLS, ports, QUIC streams | Virtual memory, SR-IOV VFs, ASIDs |
| | Overcommit | Promising more than exists | Oversubscribed uplinks | Memory and CPU overcommit |

Compute lacks most of level 2 because it isn't a linear medium. Two radio signals add and can be separated again by projection, while two programs on one ALU cannot. That leaves compute with time-sharing, physical partitioning, and naming.

## Takeaways

- Every sharing scheme answers three questions: **which floor**, **which patch of that floor**, and **how much power on it**. Allocation policy and naming sit on top.
- Carving a floor never creates capacity; only **more floors** (aperture relative to λR, or scattering) or **more bandwidth** do. Power helps only logarithmically.
- **Optics wins on raw capacity** for both reasons: carrier frequencies around 193 THz give enormous bandwidth, and tiny λ gives many modes per aperture. Fiber turns that into tens of Tb/s per fiber pair. **Radio wins on reach**: it bends, penetrates, and needs no pointing.
