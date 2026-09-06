---
title:  "Tiny KVM VMM"
category: programming
date:   2026-05-31
---

Pekka Enberg in [3] discusses the past and future of hypervisors. In particular, he breaks down the hypervisor as being a VMM and a device model.
That is a useful theoretical model to have in mind, but it doesn't line up very well with how hypervisors are implemented in practice,
where the kernel (KVM, Apple's Hypervisor.framework) and the user-space emulator (qemu, firecracker, etc) both implement parts of Pekka's VMM and device-model.

![](/assets/tiny-kvm-vmm/vmm-vs-device-model.png)

## What KVM Is

KVM is the hardware path. The important conceptual point is that KVM is essentially an ioctl API over VMX/SVM and several file descriptor types: a system fd from `/dev/kvm`, a VM fd, vCPU fds, and sometimes device fds. ([Kernel.org][3])

![](/assets/tiny-kvm-vmm/kvm-fds.png)

![](/assets/tiny-kvm-vmm/kvm-regs-and-mem.png)

The core structure you want to internalize is:

```c
/* 1. handles */
kvmfd = open("/dev/kvm", O_RDWR);
vmfd  = ioctl(kvmfd, KVM_CREATE_VM, 0);

/* 2. memory: allocate, fill, then register */
mem = mmap(NULL, MEM_SIZE, PROT_READ|PROT_WRITE,
           MAP_ANONYMOUS|MAP_SHARED, -1, 0);
memcpy(mem + GUEST_ENTRY, guest_code, sizeof guest_code);
ioctl(vmfd, KVM_SET_USER_MEMORY_REGION, &region);

/* 3. cpu: create, map the shared run page, set state */
vcpufd = ioctl(vmfd, KVM_CREATE_VCPU, 0);
run    = mmap(NULL, ioctl(kvmfd, KVM_GET_VCPU_MMAP_SIZE, 0),
              PROT_READ|PROT_WRITE, MAP_SHARED, vcpufd, 0);
ioctl(vcpufd, KVM_GET_SREGS, &sregs);   /* flatten cs */
ioctl(vcpufd, KVM_SET_SREGS, &sregs);
ioctl(vcpufd, KVM_SET_REGS, &regs);     /* rip, rflags */

/* 4. run + handle exits */
for (;;) {
    ioctl(vcpufd, KVM_RUN, 0);
    switch (run->exit_reason) {
    case KVM_EXIT_HLT:
    case KVM_EXIT_IO:
    case KVM_EXIT_MMIO:
    }
}
```

Four phases: handles, memory, cpu, run. Nothing forces the memory slot to come
before the vCPU — group them this way anyway, because each phase then stands on
its own and the shape matches the object model below. Filling guest RAM before
registering the slot is fine too. `KVM_SET_USER_MEMORY_REGION` only tells KVM
which host pages back which guest-physical range; the host mapping stays yours,
and you can write to it before, during, or after the guest runs.


## The first program: LWN's "Using the KVM API"

Start with **LWN’s “Using the KVM API”**. It walks through setting up a VM directly without QEMU, runs a tiny 16-bit x86 guest, prints via an emulated serial port, and exits via `hlt`. ([LWN.net][1])

From https://lwn.net/Articles/658512/, with one comment of mine added:
```c
int main(void)
{
    int kvm, vmfd, vcpufd, ret;
    const uint8_t code[] = {
        0xba, 0xf8, 0x03, /* mov $0x3f8, %dx */
        0x00, 0xd8,       /* add %bl, %al */
        0x04, '0',        /* add $'0', %al */
        0xee,             /* out %al, (%dx) */
        0xb0, '\n',       /* mov $'\n', %al */
        0xee,             /* out %al, (%dx) */
        0xf4,             /* hlt */
    };
    uint8_t *mem;
    struct kvm_sregs sregs;
    size_t mmap_size;
    struct kvm_run *run;

    kvm = open("/dev/kvm", O_RDWR | O_CLOEXEC);
    if (kvm == -1)
        err(1, "/dev/kvm");

    /* Make sure we have the stable version of the API */
    ret = ioctl(kvm, KVM_GET_API_VERSION, NULL);
    if (ret == -1)
        err(1, "KVM_GET_API_VERSION");
    if (ret != 12)
        errx(1, "KVM_GET_API_VERSION %d, expected 12", ret);

    vmfd = ioctl(kvm, KVM_CREATE_VM, (unsigned long)0);
    if (vmfd == -1)
        err(1, "KVM_CREATE_VM");

    /* Allocate one aligned page of guest memory to hold the code. */
    mem = mmap(NULL, 0x1000, PROT_READ | PROT_WRITE, MAP_SHARED | MAP_ANONYMOUS, -1, 0);
    if (!mem)
        err(1, "allocating guest memory");
    memcpy(mem, code, sizeof(code));

    /* Map it to the second page frame (to avoid the real-mode IDT at 0). */
    struct kvm_userspace_memory_region region = {
        .slot = 0,
        .guest_phys_addr = 0x1000,
        .memory_size = 0x1000,
        .userspace_addr = (uint64_t)mem,
    };
    ret = ioctl(vmfd, KVM_SET_USER_MEMORY_REGION, &region);
    if (ret == -1)
        err(1, "KVM_SET_USER_MEMORY_REGION");

    vcpufd = ioctl(vmfd, KVM_CREATE_VCPU, (unsigned long)0);
    if (vcpufd == -1)
        err(1, "KVM_CREATE_VCPU");

    /* Map the shared kvm_run structure and following data. */
    ret = ioctl(kvm, KVM_GET_VCPU_MMAP_SIZE, NULL);
    if (ret == -1)
        err(1, "KVM_GET_VCPU_MMAP_SIZE");
    mmap_size = ret;
    if (mmap_size < sizeof(*run))
        errx(1, "KVM_GET_VCPU_MMAP_SIZE unexpectedly small");
    run = mmap(NULL, mmap_size, PROT_READ | PROT_WRITE, MAP_SHARED, vcpufd, 0);
    if (!run)
        err(1, "mmap vcpu");

    /* Initialize CS to point at 0, via a read-modify-write of sregs. */
    ret = ioctl(vcpufd, KVM_GET_SREGS, &sregs);
    if (ret == -1)
        err(1, "KVM_GET_SREGS");
    sregs.cs.base = 0;
    sregs.cs.selector = 0;
    ret = ioctl(vcpufd, KVM_SET_SREGS, &sregs);
    if (ret == -1)
        err(1, "KVM_SET_SREGS");

    /* Initialize registers: instruction pointer for our code, addends, and
     * initial flags required by x86 architecture. */
    struct kvm_regs regs = {
        .rip = 0x1000,
        .rax = 2,
        .rbx = 2,
        .rflags = 0x2,
    };
    ret = ioctl(vcpufd, KVM_SET_REGS, &regs);
    if (ret == -1)
        err(1, "KVM_SET_REGS");

    /* Repeatedly run code and handle VM exits. */
    while (1) {
        ret = ioctl(vcpufd, KVM_RUN, NULL);
        if (ret == -1)
            err(1, "KVM_RUN");
        switch (run->exit_reason) {
        case KVM_EXIT_HLT:
            puts("KVM_EXIT_HLT");
            return 0;
        case KVM_EXIT_IO:
            /* This case body is the entire device model: a write-only 16550
             * UART at COM1 (0x3f8). Everything above the switch is the VMM. */
            if (run->io.direction == KVM_EXIT_IO_OUT && run->io.size == 1 && run->io.port == 0x3f8 && run->io.count == 1)
                putchar(*(((char *)run) + run->io.data_offset));
            else
                errx(1, "unhandled KVM_EXIT_IO");
            break;
        case KVM_EXIT_FAIL_ENTRY:
            errx(1, "KVM_EXIT_FAIL_ENTRY: hardware_entry_failure_reason = 0x%llx",
                 (unsigned long long)run->fail_entry.hardware_entry_failure_reason);
        case KVM_EXIT_INTERNAL_ERROR:
            errx(1, "KVM_EXIT_INTERNAL_ERROR: suberror = 0x%x", run->internal.suberror);
        default:
            errx(1, "exit_reason = 0x%x", run->exit_reason);
        }
    }
}
```

![](/assets/tiny-kvm-vmm/kvm-host-guest-mmap.png)

{% include tiny-kvm-vmm/kvmtest-stepper.html %}



## References

1. [Using the KVM API - LWN.net][1]
2. [The Definitive KVM API Documentation][2]
3. [The Evolution and Future of Hypervisors - Pekka Enberg][3]

[1]: https://lwn.net/Articles/658511 "Using the KVM API - LWN.net"
[2]: https://www.kernel.org/doc/html/latest/virt/kvm/api.html "The Definitive KVM (Kernel-based Virtual Machine) API Documentation"
[3]: https://medium.com/@penberg/the-evolution-and-future-of-hypervisors-999f568f9a5d "The Evolution and Future of Hypervisors - Pekka Enberg"
