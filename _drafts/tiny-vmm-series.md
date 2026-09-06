# Follow-up to the tiny-kvm-vmm article

The first article was about the smallest example that can execute guest code inside a VM:handles, memory, cpu, run.

## Where this series goes

Every VMM is defined by what it declines to implement. Firecracker boots in a fraction of the time QEMU does because it has no BIOS, almost no legacy devices, and — until recently — no PCI bus. Each part of this series takes one thing the skeleton above does badly or not at all, and follows it down.

1. **The tiny VMM.** (already published)
2. **The vCPU thread model.** `KVM_RUN` is not a function call, it is a thread's entire life. One thread per vCPU, blocking in the kernel until an exit. How you kick a vCPU out of the guest with a signal, what `MP_STATE` is for, and how INIT/SIPI brings up the second processor. Every single-vCPU tutorial hides all of this.
3. **Memory.** The `kvm-hello-world` mode ladder, then EPT and two-dimensional page walks, why an address with no memory slot is what produces an MMIO exit, and dirty logging as the road to live migration.
4. **Interrupts.** The half of the loop the skeleton never touches — everything here is host to guest. Inject one by hand with `KVM_INTERRUPT`, then hand the entire job to KVM: the in-kernel irqchip, the PIT, the LAPIC and IOAPIC, and the GSI routing table everything else later plugs into. This is the part where you delete your own code.
5. **I/O, all the way down.** One `out` per character costs a VM exit. This is the rabbit hole: port I/O, MMIO, virtqueues, `ioeventfd` and `irqfd` as a matched pair, vhost moving the device out of your process entirely, then VFIO, real DMA, and vDPA.
6. **Booting Linux.** bzImage, the boot protocol, `boot_params`, E820, initramfs. See [4] and [5]

## Memory

**`dpw/kvm-hello-world`** runs the same payload four times, in four processor modes: `run_real_mode`, `run_protected_mode`, `run_paged_32bit_mode`, `run_long_mode`. ([GitHub][2])

Then the second half of part 3: the memory-slot state table from part 1 gets
built out. `KVM_MEM_READONLY` as ROM, `userfaultfd` as post-copy migration,
`KVM_MEM_LOG_DIRTY_PAGES` and `KVM_GET_DIRTY_LOG` as pre-copy, the dirty ring,
and `guest_memfd` as the point where the host loses read access entirely. The
through-line: by default KVM handles a memory fault and never tells you, and
every one of these is an explicit request to be told.

That ladder is the whole point. Real mode needs almost nothing. Protected mode needs a GDT. Paged 32-bit mode needs `CR3` and a page directory, with `CR4_PSE` for a single 4MB page. Long mode needs `EFER_LME | EFER_LMA` and a real hierarchy: PML4 at `0x2000`, PDPT at `0x3000`, PD at `0x4000`. Two megabytes of guest RAM total. Each rung adds exactly one idea, and you can diff the setup functions against each other to see what that idea cost.

## Interrupts

Part 4 comes first because `irqfd` injects through the in-kernel GSI routing
table, and `KVM_CREATE_IRQCHIP` is what creates it. By the end of part 4 you
know memory and interrupts — which is what a virtqueue is: a structure in
shared memory plus a way to ring a bell. Part 5 is where they meet.

## Memory

**`dpw/kvm-hello-world`** runs the same payload four times, in four processor modes: `run_real_mode`, `run_protected_mode`, `run_paged_32bit_mode`, `run_long_mode`. ([GitHub][2])

Then the second half of part 3: the memory-slot state table from part 1 gets
built out. `KVM_MEM_READONLY` as ROM, `userfaultfd` as post-copy migration,
`KVM_MEM_LOG_DIRTY_PAGES` and `KVM_GET_DIRTY_LOG` as pre-copy, the dirty ring,
and `guest_memfd` as the point where the host loses read access entirely. The
through-line: by default KVM handles a memory fault and never tells you, and
every one of these is an explicit request to be told.

That ladder is the whole point. Real mode needs almost nothing. Protected mode needs a GDT. Paged 32-bit mode needs `CR3` and a page directory, with `CR4_PSE` for a single 4MB page. Long mode needs `EFER_LME | EFER_LMA` and a real hierarchy: PML4 at `0x2000`, PDPT at `0x3000`, PD at `0x4000`. Two megabytes of guest RAM total. Each rung adds exactly one idea, and you can diff the setup functions against each other to see what that idea cost.

## Interrupts

The interrupt article comes before the I/O article because it is a prerequisite,
not a companion. The fast I/O path is fast precisely because your VMM is not in
it, and the mechanism that lets it step out is `irqfd` — which injects through
the in-kernel GSI routing table that `KVM_CREATE_IRQCHIP` sets up. Part 4
introduces `irqfd` as a way to deliver an interrupt. Part 5 uses it as one half
of a notification pair. Reversed, part 5 would have to explain its own
foundation in a footnote.

By the end of part 4 you know how memory works and how interrupts work, which
is exactly what a virtqueue is: a data structure in shared memory plus a way to
ring a bell. Part 5 is where the two meet.

## I/O

The arc is "stop using exits to move data." The frame that makes it land is
control plane versus data plane: exits are how you say *look now*, and shared
memory is where the bytes actually are.

The virtio fast path is a loop with two bells, and no data crosses either one:

| Bell                                                    | Naive                                        | Fast                                                                                         |
| ------------------------------------------------------- | -------------------------------------------- | -------------------------------------------------------------------------------------------- |
| **kick** (guest → host) — "descriptors are in the ring" | MMIO write → `KVM_EXIT_MMIO` → your run loop | `ioeventfd`: KVM signals an eventfd and re-enters the guest, with no exit to userspace       |
| **call** (host → guest) — "done, check the used ring"   | your VMM calls `KVM_IRQ_LINE`                | `irqfd`: anything that can write an eventfd triggers injection, through part 4's GSI routing |

Everything else in the article is a move on that board. **vhost** hands both
eventfds to a kernel thread, which then knows only three things: the guest
memory mapping, a kick eventfd and a call eventfd ([Hajnoczi][12]) — your VMM
is out of the data path entirely. **VFIO** deletes both bells, because the
device DMAs into guest RAM itself and raises a real MSI; with posted interrupts
the hardware delivers it to a running vCPU with no exit at all.

Two details worth keeping: `KVM_IOEVENTFD_FLAG_DATAMATCH` fires only on a
specific written value, and `KVM_IRQFD_FLAG_RESAMPLE` plus a resamplefd handles
level-triggered interrupts, where the kernel needs to know when the guest
finished with one. ([Kernel.org][13])

# References

1. [dpw/kvm-hello-world][1]
2. [Building a hypervisor, 2: Booting Linux][4]
3. [kvmtool][5]
4. [rust-vmm][6]
5. [Virtio on Linux - The Linux Kernel documentation][7]
6. [Firecracker design document][8]
7. [virtio-mmio specification enhancement - LWN.net][9]
8.  [Managing Interrupts in Virtio-PCI][10]
9. [QEMU Blog - Airbus SECLab][11]
10. [QEMU Internals: vhost architecture - Stefan Hajnoczi][12]
11. [The Definitive KVM API Documentation][13]

[1]: https://github.com/dpw/kvm-hello-world "dpw/kvm-hello-world"
[4]: https://iovec.net/2024-05-06 "Building a hypervisor, 2: Booting Linux"
[5]: https://github.com/kvmtool/kvmtool "kvmtool"
[6]: https://github.com/rust-vmm "rust-vmm"
[7]: https://docs.kernel.org/driver-api/virtio/virtio.html "Virtio on Linux — The Linux Kernel documentation"
[8]: https://github.com/firecracker-microvm/firecracker/blob/main/docs/design.md "Firecracker design document"
[9]: https://lwn.net/Articles/812055/ "virtio mmio specification enhancement - LWN.net"
[10]: https://michael2012z.medium.com/managing-interrupt-in-virtio-pci-bfe585117b49 "Managing Interrupt in Virtio-PCI"
[11]: https://airbus-seclab.github.io/qemu_blog/ "QEMU Blog - Airbus SECLab"
[12]: http://blog.vmsplice.net/2011/09/qemu-internals-vhost-architecture.html "QEMU Internals: vhost architecture - Stefan Hajnoczi"
[13]: https://www.kernel.org/doc/html/latest/virt/kvm/api.html "The Definitive KVM (Kernel-based Virtual Machine) API Documentation"
