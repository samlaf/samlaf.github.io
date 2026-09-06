# Follow-up to the tiny-kvm-vmm article

The first article was about the smallest example that can execute guest code inside a VM:handles, memory, cpu, run.

## Where this series goes

Every VMM is defined by what it declines to implement. Firecracker boots in a fraction of the time QEMU does because it has no BIOS, almost no legacy devices, and — until recently — no PCI bus. Each part of this series takes one thing the skeleton above does badly or not at all, and follows it down.

1. **The tiny VMM.** (already published)
2. **The vCPU thread model.** `KVM_RUN` is not a function call, it is a thread's entire life. One thread per vCPU, blocking in the kernel until an exit. How you kick a vCPU out of the guest with a signal, what `MP_STATE` is for, and how INIT/SIPI brings up the second processor. Every single-vCPU tutorial hides all of this.
3. **Memory.** The `kvm-hello-world` mode ladder, then EPT and two-dimensional page walks, why an address with no memory slot is what produces an MMIO exit, and dirty logging as the road to live migration.
4. **I/O, all the way down.** One `out` per character costs a VM exit. This is the rabbit hole: port I/O, MMIO, virtqueues, `ioeventfd`, vhost moving the device out of your process entirely, then VFIO, real DMA, and vDPA.
5. **What KVM already does for you.** The in-kernel irqchip, the PIT, interrupt injection and `irqfd`. The half of the loop the skeleton above never touches: everything here is host to guest.
6. **Booting Linux.** bzImage, the boot protocol, `boot_params`, E820, initramfs. See [4] and [5]

Parts 4 and 5 lean on each other. The fast I/O path is fast precisely because your VMM is not in it, and the reason it can step out is `irqfd`.

## Memory

**`dpw/kvm-hello-world`** runs the same payload four times, in four processor modes: `run_real_mode`, `run_protected_mode`, `run_paged_32bit_mode`, `run_long_mode`. ([GitHub][2])

That ladder is the whole point. Real mode needs almost nothing. Protected mode needs a GDT. Paged 32-bit mode needs `CR3` and a page directory, with `CR4_PSE` for a single 4MB page. Long mode needs `EFER_LME | EFER_LMA` and a real hierarchy: PML4 at `0x2000`, PDPT at `0x3000`, PD at `0x4000`. Two megabytes of guest RAM total. Each rung adds exactly one idea, and you can diff the setup functions against each other to see what that idea cost.

# References

1. [dpw/kvm-hello-world][1]
2. [Building a hypervisor, 2: Booting Linux][4]
3. [kvmtool][5]
4. [rust-vmm][6]
5. [Virtio on Linux - The Linux Kernel documentation][7]
6. [Firecracker design document][8]
7. [virtio-mmio specification enhancement - LWN.net][9]
8.  [Managing Interrupts in Virtio-PCI][10]

[1]: https://github.com/dpw/kvm-hello-world "dpw/kvm-hello-world"
[4]: https://iovec.net/2024-05-06 "Building a hypervisor, 2: Booting Linux"
[5]: https://github.com/kvmtool/kvmtool "kvmtool"
[6]: https://github.com/rust-vmm "rust-vmm"
[7]: https://docs.kernel.org/driver-api/virtio/virtio.html "Virtio on Linux — The Linux Kernel documentation"
[8]: https://github.com/firecracker-microvm/firecracker/blob/main/docs/design.md "Firecracker design document"
[9]: https://lwn.net/Articles/812055/ "virtio mmio specification enhancement - LWN.net"
[10]: https://michael2012z.medium.com/managing-interrupt-in-virtio-pci-bfe585117b49 "Managing Interrupt in Virtio-PCI"
[11]: https://airbus-seclab.github.io/qemu_blog/ "QEMU Blog - Airbus SECLab"
