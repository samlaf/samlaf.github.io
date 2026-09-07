---
title:  "Tiny KVM VMM"
category: programming
date:   2026-05-31
---

Pekka Enberg in [3] discusses the past and future of hypervisors. In particular, he breaks down the hypervisor as being a VMM and a device model.
That is a useful theoretical model to have in mind, but it doesn't line up very well with how hypervisors are implemented in practice,
where the kernel (KVM, Apple's Hypervisor.framework) and the user-space emulator (qemu, firecracker, etc) both implement parts of Pekka's VMM and device-model.

![VMM and device model responsibilities across userspace and the kernel.](/assets/tiny-kvm-vmm/vmm-vs-device-model.png)

## What KVM Is

KVM is the hardware path. The important conceptual point is that KVM is essentially an ioctl API over VMX/SVM and several file descriptor types: a system fd from `/dev/kvm`, a VM fd, vCPU fds, and sometimes device fds. ([Kernel.org][2])

![KVM system, VM, and vCPU file descriptors and their ioctl operations.](/assets/tiny-kvm-vmm/kvm-fds.png)

![How KVM register and memory configuration maps to kernel and hardware state.](/assets/tiny-kvm-vmm/kvm-regs-and-mem.png)

## Setting up

Four phases get you to the point where guest code can run: **handles**,
**memory**, **cpu**, **run**. The first three are setup, they are the same in
every example, and once you have written them you mostly stop thinking about
them.
Here they are, in full.

```c
#include <err.h>
#include <fcntl.h>
#include <linux/kvm.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <unistd.h>

/* The guest payload. This is the one thing every example below changes. */
static const uint8_t code[] = { /* ... */ };

int main(void)
{
    int kvm, vmfd, vcpufd, ret;
    uint8_t *mem;
    size_t mmap_size;
    struct kvm_run *run;
    struct kvm_sregs sregs;
    struct kvm_regs regs;

    /* 1. handles */
    kvm = open("/dev/kvm", O_RDWR | O_CLOEXEC);
    if (kvm == -1)
        err(1, "/dev/kvm");
    ret = ioctl(kvm, KVM_GET_API_VERSION, NULL);
    if (ret == -1)
        err(1, "KVM_GET_API_VERSION");
    if (ret != 12)
        errx(1, "KVM_GET_API_VERSION %d, expected 12", ret);

    vmfd = ioctl(kvm, KVM_CREATE_VM, (unsigned long)0);
    if (vmfd == -1)
        err(1, "KVM_CREATE_VM");

    /* 2. memory: one 4KB page at guest-physical 0x1000 */
    mem = mmap(NULL, 0x1000, PROT_READ | PROT_WRITE,
               MAP_SHARED | MAP_ANONYMOUS, -1, 0);
    if (!mem)
        err(1, "allocating guest memory");
    memcpy(mem, code, sizeof(code));

    struct kvm_userspace_memory_region region = {
        .slot            = 0,
        .guest_phys_addr = 0x1000,
        .memory_size     = 0x1000,
        .userspace_addr  = (uint64_t)mem,
    };
    ret = ioctl(vmfd, KVM_SET_USER_MEMORY_REGION, &region);
    if (ret == -1)
        err(1, "KVM_SET_USER_MEMORY_REGION");

    /* 3. cpu: create it, map the shared run page, set initial state */
    vcpufd = ioctl(vmfd, KVM_CREATE_VCPU, (unsigned long)0);
    if (vcpufd == -1)
        err(1, "KVM_CREATE_VCPU");

    ret = ioctl(kvm, KVM_GET_VCPU_MMAP_SIZE, NULL);
    if (ret == -1)
        err(1, "KVM_GET_VCPU_MMAP_SIZE");
    mmap_size = ret;
    if (mmap_size < sizeof(*run))
        errx(1, "KVM_GET_VCPU_MMAP_SIZE unexpectedly small");
    run = mmap(NULL, mmap_size, PROT_READ | PROT_WRITE, MAP_SHARED, vcpufd, 0);
    if (!run)
        err(1, "mmap vcpu");

    /* flatten cs so cs:ip addresses are just physical addresses */
    ret = ioctl(vcpufd, KVM_GET_SREGS, &sregs);
    if (ret == -1)
        err(1, "KVM_GET_SREGS");
    sregs.cs.base = 0;
    sregs.cs.selector = 0;
    ret = ioctl(vcpufd, KVM_SET_SREGS, &sregs);
    if (ret == -1)
        err(1, "KVM_SET_SREGS");

    memset(&regs, 0, sizeof(regs));
    regs.rip    = 0x1000;
    regs.rax    = 2;
    regs.rbx    = 2;
    regs.rflags = 0x2;
    ret = ioctl(vcpufd, KVM_SET_REGS, &regs);
    if (ret == -1)
        err(1, "KVM_SET_REGS");
```

Nothing forces the memory slot to come before the vCPU. Group them this way
anyway, because each phase then stands on its own and the shape matches the
object model. Filling guest RAM before registering the slot is fine too —
`KVM_SET_USER_MEMORY_REGION` only tells KVM which host pages back which
guest-physical range. The host mapping stays yours, and you can write to it
before, during, or after the guest runs.

Example 3 is the only one that adds anything here, and only a second memory
slot.
Everything else in this article happens after the brace above.

## Building it up

Most KVM tutorials open with a guest that immediately talks to a serial port,
which welds two separate ideas together: *the guest ran and I can observe it*,
and *I emulated a peripheral*. Those are worth pulling apart.

So we start with neither. Example 1 is a working VMM with no device model at
all, and every example after it is a diff against the one before, varying
exactly one thing.

| Example | Adds | Varies |
|---|---|---|
| 1 | `hlt`, host reads `rax` and guest RAM | — |
| 2 | a store to an unbacked address | the exit |
| 3 | an IVT, `sti`, and injection — by hand, then by KVM | the direction |
| 4 | the run loop in a thread, kicked by a signal | the execution model |

Examples 1 and 2 are about what makes the guest leave. Example 3 is about which
way traffic goes, and it gets built twice: once with your VMM doing the work,
once with `KVM_CREATE_IRQCHIP` doing it. Example 4 is about who runs the loop.

### Example 1: no devices at all

A guest can do useful work and hand back a result without any device model. All
that is left is phase 4 — the payload, the loop, and reading the answer back.
The scaffolding above is LWN's, with a different payload inside it.
([LWN.net][1])

The payload adds two numbers, stores the result, and stops:

```c
static const uint8_t code[] = {
    0x00, 0xd8,        /* add  %bl, %al       */
    0xa2, 0x00, 0x1f,  /* mov  %al, (0x1f00)  */
    0xf4,              /* hlt                 */
};
```

And phase 4 continues the same `main()`:

```c
    /* 4. run */
    for (;;) {
        ret = ioctl(vcpufd, KVM_RUN, NULL);
        if (ret == -1)
            err(1, "KVM_RUN");
        switch (run->exit_reason) {
        case KVM_EXIT_HLT:
            ret = ioctl(vcpufd, KVM_GET_REGS, &regs);
            if (ret == -1)
                err(1, "KVM_GET_REGS");
            printf("rax = %llu\n", (unsigned long long)regs.rax);
            printf("mem = %u\n", mem[0x1f00 - 0x1000]);
            return 0;
        case KVM_EXIT_FAIL_ENTRY:
            errx(1, "KVM_EXIT_FAIL_ENTRY: hardware_entry_failure_reason = 0x%llx",
                 (unsigned long long)run->fail_entry.hardware_entry_failure_reason);
        case KVM_EXIT_INTERNAL_ERROR:
            errx(1, "KVM_EXIT_INTERNAL_ERROR: suberror = 0x%x",
                 run->internal.suberror);
        default:
            errx(1, "exit_reason = 0x%x", run->exit_reason);
        }
    }
}
```

It prints `4` twice. The guest adds `rbx` to `rax`, stores the result at
`0x1f00`, and halts — and the host reads that result back two different ways.

There is no `switch` case for a device, because there is no device. The
`KVM_EXIT_HLT` arm is not a device model; it is the guest telling you it is
finished. This is the entire VMM with the device model deleted, and it still
does useful work.

Both channels it uses are worth naming, because the second one is easy to walk
straight past.

**Registers.** `KVM_GET_REGS` after the exit. Obvious, and limited to a few
dozen values.

**Guest memory.** `mem[0x1f00 - 0x1000]` — the store landed at guest-physical
`0x1f00`, which is inside the slot, so it was an ordinary write to RAM and the
guest never exited for it. That channel costs *no exits at all*. There is no
trap, no emulation, no round trip through your process. It is also live:
nothing here has to wait for `hlt`. Host and guest can read and write the same
page while the vCPU is running.

![Host mappings for guest RAM and the shared kvm_run page.](/assets/tiny-kvm-vmm/kvm-host-guest-mmap.png)

#### Coda: a slot can be backed by anything

`KVM_SET_USER_MEMORY_REGION` takes a `userspace_addr`. It is an ordinary host
virtual address, and KVM does not care where it came from. Anonymous memory is
just the easiest thing to hand it. Swap the `mmap` and the guest's RAM becomes
something else entirely:

```c
int fd = open("guest.img", O_RDWR);
mem = mmap(NULL, MEM_SIZE, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
```

Now guest-physical memory *is* a host file — writes by the guest land in it,
and the kernel's page cache does the work. Point it at a `memfd` or a POSIX
shared-memory object instead and another host process can map the same pages,
which is how a device backend running outside your VMM gets at guest buffers
without copying them. Josh Triplett's !!Con talk gives the short version of the
list: code loading, host files, in-memory data structures, host shared-memory
buffers. ([Triplett][4])

Keep `MAP_SHARED`. With `MAP_PRIVATE` you get copy-on-write, so the guest's
writes go to a private copy and nobody else ever sees them.

This is worth pausing on, because it is the thing the rest of this article is
implicitly working around. Examples 2 and 3 are about *exits* — the guest stops,
you do something, the guest resumes. Exits are a control plane, and every one
of them costs a round trip. Shared memory is a data plane, and it costs
nothing. Fast virtual I/O is almost entirely the art of moving bytes on the
second one while using the first only to ring a bell.

A virtqueue is exactly this: descriptors and rings sitting in guest RAM that
the VMM reads directly, with an MMIO write used only to say *look now*. The
bytes never travel through an exit.

### Example 2: an address that isn't there

Change one byte. The store target goes from `0x1f00` to `0x8000`:

```c
    0xa2, 0x00, 0x80,  /* mov  %al, (0x8000)  */
```

Nothing else changes. Same instruction, same operand size, same one byte of
data. But `0x8000` is not covered by any memory slot, so instead of a write to
RAM you get:

```c
case KVM_EXIT_MMIO:
    printf("MMIO %s addr 0x%llx len %u data 0x%02x\n",
           run->mmio.is_write ? "write" : "read",
           (unsigned long long)run->mmio.phys_addr,
           run->mmio.len, run->mmio.data[0]);
    break;
```

That is the entire lesson of memory-mapped I/O, and it is a two-character diff.
A device is not a kind of hardware here. It is an address you declined to back
with RAM. KVM has already emulated the instruction and advanced `rip`, so you
handle the exit and continue — there is nothing to fix up.

It is tempting to read `KVM_EXIT_MMIO` as *the page wasn't there*. It isn't.
It means *no memory slot covers this address at all*, which is a much stronger
statement than a page being absent right now.

Consider what happens when a slot does cover the address but the host page has
been swapped out. The guest touches it, the EPT walk fails, and the CPU exits
into KVM. KVM looks the address up, finds a slot, and so treats it as memory:
it takes an ordinary host page fault on the matching host virtual address, the
host's memory management swaps the page back in, KVM installs the mapping and
re-enters the guest. Your VMM sleeps through all of it. No exit is delivered,
no case in your `switch` runs, and nothing in your program ever learns that a
disk was involved.

So a guest-physical address has more than two states, and which one it is
decides who wakes up:

| What covers the address | What the guest sees | Who handles it |
|---|---|---|
| nothing | `KVM_EXIT_MMIO` | your VMM |
| a slot, page resident | a normal load or store | nobody — there is no exit |
| a slot, page swapped out | a normal load or store, eventually | KVM and the host kernel, invisibly |
| a slot with `KVM_MEM_READONLY` | reads normal, writes trap | your VMM, on writes only |
| a slot registered with `userfaultfd` | the vCPU thread blocks | your VMM, out of band |
| a slot with `KVM_MEM_LOG_DIRTY_PAGES` | a normal store, recorded | KVM; you read the bitmap later |

The last three are the interesting ones, because they are how a VMM buys back
the control it does not get by default.

`KVM_MEM_READONLY` gives you ROM: reads run at memory speed, and writes come
back as `KVM_EXIT_MMIO` with `is_write` set. ([Kernel.org][2])

`userfaultfd` is the one that matches the intuition that a fault could mean
*fetch this page from somewhere*. Register the guest's memory with it, and when
the guest touches a page you have not filled in, the host blocks the vCPU
thread and sends your VMM a `UFFD_EVENT_PAGEFAULT` on a side channel. You
supply the page with `UFFDIO_COPY` and the guest resumes. That is how post-copy
live migration works: the guest starts running on the destination host before
its memory has finished arriving, and pages are pulled across the network on
demand. ([Kernel.org][7])

`KVM_MEM_LOG_DIRTY_PAGES` is the other half of migration. KVM write-protects
the slot and records which pages get dirtied, and you collect them later with
`KVM_GET_DIRTY_LOG`. Again, no per-write exit — the tracking happens underneath
you.

The pattern is the same one example 3 will show for interrupts. By default the
kernel handles it and you are not told. Every mechanism here is an explicit
request to be told, paid for in exits.

#### Coda: the other door

x86 has a second address space, reachable only by `in` and `out`. Swap the
store for a write to port `0x3f8` and you have a serial console — this is the
version LWN's article builds. ([LWN.net][1])

```c
    0xba, 0xf8, 0x03,  /* mov  $0x3f8, %dx  */
    0xee,              /* out  %al, (%dx)   */
```

Same byte, same effect, different exit — `KVM_EXIT_IO` instead of
`KVM_EXIT_MMIO`, with `run->io.port` and `run->io.data_offset` in place of
`run->mmio.phys_addr` and `run->mmio.data`. The `case` body that services it is
a complete device model: a write-only 16550 UART, in one line.

```c
case KVM_EXIT_IO:
    if (run->io.direction == KVM_EXIT_IO_OUT && run->io.size == 1 &&
        run->io.port == 0x3f8 && run->io.count == 1)
        putchar(*(((char *)run) + run->io.data_offset));
    else
        errx(1, "unhandled KVM_EXIT_IO");
    break;
```

Everything above the `switch` is the VMM. Every `case` body is the device
model. The split in the diagram at the top of this article is not
architectural — it is a line number.

{% include tiny-kvm-vmm/kvmtest-stepper.html %}

It is tempting to file port I/O under obsolete x86 trivia. Two things argue
against that. The device is not obsolete at all: a 16550 at `0x3f8` is how
essentially every microVM still gets its console, and it is the only output you
have before virtio comes up. And the legacy door is the *cheaper* one. For an
MMIO exit, KVM has to run its instruction emulator over the faulting
instruction to recover the address, the width, the direction and the register,
because a store can be any of dozens of encodings and the hardware exit
information alone does not say which. `in` and `out` carry all of that in the
opcode, so the fields arrive already decoded, straight out of the VMCS. ([ACRN][5])

The mechanism really is x86-only, though — arm64 has `KVM_EXIT_MMIO` and no
`KVM_EXIT_IO` whatsoever. ([Kernel.org][2])

### Example 3: the other direction

Everything so far is guest to host. The guest hits something, you wake up, you
service it. Nothing in the program has ever *reached into* a running guest.

Example 1 mapped its code at `0x1000` and left physical zero unbacked. That was
not arbitrary. In real mode the interrupt vector table lives at zero — four
bytes per vector, a 16-bit offset then a 16-bit segment — and putting guest
code there would have landed on top of it. This is the example that finally
wants an IVT, so it needs a second slot.

```c
uint8_t *ivt = mmap(NULL, 0x1000, PROT_READ | PROT_WRITE,
                    MAP_SHARED | MAP_ANONYMOUS, -1, 0);
struct kvm_userspace_memory_region ivt_region = {
    .slot            = 1,
    .guest_phys_addr = 0x0,
    .memory_size     = 0x1000,
    .userspace_addr  = (uint64_t)ivt,
};
ioctl(vmfd, KVM_SET_USER_MEMORY_REGION, &ivt_region);

/* vector 0x20 -> 0000:1010 */
ivt[0x20 * 4 + 0] = 0x10;
ivt[0x20 * 4 + 1] = 0x10;
ivt[0x20 * 4 + 2] = 0x00;
ivt[0x20 * 4 + 3] = 0x00;
```

The guest enables interrupts and halts. The handler writes a byte to the MMIO
address from example 2, so you can see it run:

```c
const uint8_t code[] = {
    /* 0x1000 */ 0xfb,              /* sti                */
    /* 0x1001 */ 0xf4,              /* hlt                */
    /* 0x1002 */ 0xb0, 'D',         /* mov  $'D', %al     */
    /* 0x1004 */ 0xa2, 0x00, 0x80,  /* mov  %al, (0x8000) */
    /* 0x1007 */ 0xf4,              /* hlt                */
    /* 0x1008 */ 0x90, 0x90, 0x90, 0x90, 0x90, 0x90, 0x90, 0x90,
    /* 0x1010 */ 0xb0, 'I',         /* mov  $'I', %al     */
    /* 0x1012 */ 0xa2, 0x00, 0x80,  /* mov  %al, (0x8000) */
    /* 0x1015 */ 0xcf,              /* iret               */
};
```

Now the host injects. Because this program never calls `KVM_CREATE_IRQCHIP`,
the PIC lives in userspace, which is exactly when `KVM_INTERRUPT` is available
— it returns `-ENXIO` if the PIC is in the kernel. You ask KVM to tell you when
the guest can accept a vector, and then you hand one over:

```c
run->request_interrupt_window = 1;

/* ... inside the loop, after KVM_RUN ... */
case KVM_EXIT_IRQ_WINDOW_OPEN: {
    struct kvm_interrupt irq = { .irq = 0x20 };
    ioctl(vcpufd, KVM_INTERRUPT, &irq);
    run->request_interrupt_window = 0;
    break;
}
```

Expected output is `I` then `D`: the handler runs, `iret` returns to the
instruction after `hlt`, and the guest finishes.

One thing this example exposes that the others do not. A real-mode interrupt
pushes flags, `cs` and `ip` — six bytes — and the program has no stack at all,
because nothing before now ever needed one. So you must also set
`regs.rsp = 0x1000`, which grows down through the IVT page, comfortably above
the 1KB the vector table itself occupies.

Notice what you did *not* write here. Nothing in this example emulates a CPU.
Reading the IVT, pushing flags and `cs` and `ip`, vectoring to `0x1010` — that
is all done by the hardware, driven by KVM. And nothing here emulates an
interrupt controller either, because there isn't one. On real hardware a device
raises a line into a PIC, and the PIC decides which vector the CPU should take.
`KVM_INTERRUPT` skips that entire layer and hands the CPU a vector directly.

So this is not a device model. It is a back door, and it is only open
because of something the program never did.

#### The same example, delegated

Ask KVM for an interrupt controller and it will keep one for you:

```c
ioctl(vmfd, KVM_CREATE_IRQCHIP);
```

That single call creates a virtual IOAPIC, a virtual PIC — two 8259s, nested,
as on a real PC — and arranges for every vCPU to have a local APIC.
([Kernel.org][2]) It has to happen before `KVM_CREATE_VCPU`, so this is a
decision you make during setup, in phases 1 through 3, before anything runs.

Three things change, and each one is a piece of work moving across the
kernel boundary.

**You stop naming vectors.** `KVM_INTERRUPT` takes a vector: you decided
`0x20`. Its in-kernel counterpart takes a GSI — a *line*:

```c
struct kvm_irq_level irq = { .irq = 0, .level = 1 };
ioctl(vmfd, KVM_IRQ_LINE, &irq);
irq.level = 0;
ioctl(vmfd, KVM_IRQ_LINE, &irq);
```

You say a wire went high and then low. Which vector that becomes, whether it is
masked, how it ranks against other pending interrupts, and what happens at EOI
are now the in-kernel PIC's problem. That is the difference between asserting a
vector and having an interrupt controller.

**The handshake goes away.** No `request_interrupt_window`, no
`KVM_EXIT_IRQ_WINDOW_OPEN`, no waiting to be told the guest is ready. KVM
already knows.

**And `KVM_EXIT_HLT` stops happening at all.** With an in-kernel local APIC,
`hlt` is handled inside the kernel: the vCPU blocks there and the irqchip wakes
it when a line goes high. Your process is not involved. Both earlier examples
end on `KVM_EXIT_HLT`, so turning on the irqchip would quietly delete the exit this
whole article has been built around — which is the real reason it comes last.
(There is a modern opt-out, `KVM_X86_USERSPACE_EXIT_HLT`, if you want the exit
back anyway. ([LWN.net][6]))

The guest side moves too. A guest using the in-kernel PIC programs it the
normal way, with `out` to ports `0x20` and `0x21`. Those writes are serviced in
the kernel and never surface in your run loop — the same instruction that
produced a `KVM_EXIT_IO` in example 2's coda now produces no exit whatsoever.
Whether your process wakes up is decided by one ioctl at setup time.

That is the diagram at the top of this article, in code. `KVM_INTERRUPT` and
the hand-built IVT are the left column: work your VMM does. `KVM_CREATE_IRQCHIP`
moves that work into the right column, into the kernel, where the guest can use
it without ever waking you. Neither version is more correct. The first shows you
what an interrupt costs; the second is what you ship.

### Example 4: who calls `KVM_RUN`?

Example 3 injected an interrupt from inside the run loop, between exits. Real
devices do not work that way. A timer fires, a packet lands, a block request
completes — and none of them are politely waiting for the vCPU to exit first.
So: who calls `KVM_INTERRUPT`, and how do they reach a vCPU that is blocked
inside `KVM_RUN`?

Give the vCPU its own thread and make the guest never leave:

```c
const uint8_t code[] = {
    0xeb, 0xfe,        /* jmp . */
};
```

That guest spins forever. It executes no I/O, halts on nothing, and will never
produce an exit on its own. The only way out is from the outside:

```c
static void kick(int sig) { (void)sig; }

static void *vcpu_thread(void *arg)
{
    for (;;) {
        if (ioctl(vcpufd, KVM_RUN, 0) == -1) {
            if (errno == EINTR) {
                printf("kicked out of the guest\n");
                continue;
            }
            err(1, "KVM_RUN");
        }
        /* ... the switch from the earlier examples ... */
    }
}

int main(void)
{
    /* ... setup as before ... */
    struct sigaction sa = { .sa_handler = kick };
    sigaction(SIGUSR1, &sa, NULL);       /* deliberately no SA_RESTART */

    pthread_t tid;
    pthread_create(&tid, NULL, vcpu_thread, NULL);

    sleep(1);
    pthread_kill(tid, SIGUSR1);
    /* ... */
}
```

The missing `SA_RESTART` is the whole trick. With it, the kernel restarts the
interrupted `ioctl` and the vCPU dives straight back into the guest as if
nothing happened. Without it, `KVM_RUN` returns `-EINTR` and the thread is
yours again. `SIG_IGN` will not do either — the signal has to be delivered to a
handler to break the call.

That is the vCPU thread model in miniature: `KVM_RUN` is not a function call,
it is a thread's entire life, and a signal is the doorbell.

> A note on trust. The instruction encodings above are machine-checked — I
> assembled every one of them and diffed the bytes — and the ioctl sequences come
> from the KVM API documentation. But none of it has been *run*: I wrote this on
> a Mac, which has no `/dev/kvm`. The interrupt handshake in example 3 is the part I
> would put on a Linux box first.

## References

1. [Using the KVM API - LWN.net][1]
2. [The Definitive KVM API Documentation][2]
3. [The Evolution and Future of Hypervisors - Pekka Enberg][3]
4. [!!Con 2019 - Build your own virtual machine with /dev/kvm and Rust! by Josh Triplett][4]
5. [I/O Emulation High-Level Design - Project ACRN][5]
6. [KVM: x86: Allow userspace exit on HLT and MWAIT - LWN.net][6]
7. [Userfaultfd - The Linux Kernel documentation][7]

[1]: https://lwn.net/Articles/658511 "Using the KVM API - LWN.net"
[2]: https://www.kernel.org/doc/html/latest/virt/kvm/api.html "The Definitive KVM (Kernel-based Virtual Machine) API Documentation"
[3]: https://medium.com/@penberg/the-evolution-and-future-of-hypervisors-999f568f9a5d "The Evolution and Future of Hypervisors - Pekka Enberg"
[4]: https://www.youtube.com/watch?v=A_diEEpAfpM "!!Con 2019 - Build your own virtual machine with /dev/kvm and Rust! by Josh Triplett"
[5]: https://projectacrn.github.io/2.5/developer-guides/hld/hv-io-emulation.html "I/O Emulation High-Level Design - Project ACRN"
[6]: https://lwn.net/Articles/944862/ "KVM: x86: Allow userspace exit on HLT and MWAIT - LWN.net"
[7]: https://www.kernel.org/doc/html/latest/admin-guide/mm/userfaultfd.html "Userfaultfd - The Linux Kernel documentation" 
