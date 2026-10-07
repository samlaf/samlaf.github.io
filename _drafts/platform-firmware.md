# Platform firmware: what the buses can't say

Talking to a device is three separate problems, and each one has its own machinery.

1. **Data plane.** Moving bytes once you have a device: memory read and write TLPs, NVMe submission and completion queues, virtqueues.
2. **In-band control plane.** Finding and configuring devices using the device transport itself: config read and write TLPs, enumeration, BAR sizing, bridge programming. It rides the same wires as the data.
3. **Out-of-band platform plane.** Telling the OS what the buses cannot say about themselves: ACPI and devicetree tables in memory, plus platform firmware code (AML, UEFI runtime services, SMM). None of it travels over the device transport.

The first two are covered in [Interconnects are networks](/programming/interconnects-are-networks.html). This article is about the third.

```
                     ┌─────────────────────────────────────────┐
                     │                OS kernel                │
                     └────┬───────────────┬───────────────┬────┘
                          │               │               │
        (1) data plane    │   (2) in-band │               │  (3) out-of-band
        MemRd / MemWr     │   control     │               │  platform plane
        NVMe SQ / CQ      │   CfgRd/CfgWr │               │  ACPI / DT tables
        virtqueues        │   enumeration │               │  AML, UEFI RT, SMM
                          │               │               │
                     ┌────▼───────────────▼────┐   ┌──────▼──────────────┐
                     │    device transport     │   │  platform firmware  │
                     │ PCIe, SAS, TCP, virtio  │   │  (not on any bus)   │
                     └─────────────────────────┘   └─────────────────────┘
```

The planes are ordered by how you meet them when you read about devices, not by when they run. At boot they run in reverse: firmware builds the platform description, the OS uses it to find the buses, enumeration finds the devices, and only then does a single byte of data move. The first section covers that boot sequence so the rest of the article can assume it.

## How the machine boots, and who runs what

UEFI is the firmware that boots the machine; ACPI is the data format that firmware uses to describe the hardware to the OS. UEFI builds the ACPI tables and hands them over, then mostly disappears. The OS keeps using ACPI for the rest of its life.

### The boot handoff (x86, UEFI)

![Boot handoff: security coprocessor, UEFI firmware, OS loader, kernel, and what firmware leaves behind](/assets/firmware/boot-handoff.png)

- **SEC** sets up a stack in cache-as-RAM. **PEI** trains DRAM (often through Intel FSP or AMD AGESA). **DXE** loads drivers, enumerates PCI, installs protocols, and builds the ACPI tables. **BDS** picks a boot target from the `Boot####` NVRAM variables.
- The OS loader is an ordinary PE/COFF EFI application. It reads files and allocates memory through **boot services**, which vanish at `ExitBootServices()`.
- The kernel finds the ACPI root pointer (RSDP) in the **EFI configuration table** under `EFI_ACPI_20_TABLE_GUID`. Legacy BIOS systems made it scan `0xE0000–0xFFFFF` for the `"RSD PTR "` signature instead.
- Arm follows the same shape: BootROM → TF-A BL1/BL2 → BL31 (stays resident at EL3, serving PSCI) → BL33 normal-world firmware (U-Boot or EDK2) → OS loader.

The right-hand box is the problem Bryan Cantrill describes as "setting the machine backward": firmware builds and tears down a whole running system, then makes the machine look unbooted for the OS. The ACPI tables are the written record of what it did and what it left behind.

### What still runs after boot

Three kinds of code reach the hardware once the OS is up, and only one of them is written by the OS vendor. Below the OS sit two more that the OS cannot see at all.

![Runtime paths: drivers, AML and UEFI runtime services reaching hardware, with SMM and management cores below](/assets/firmware/after-boot.png)

### AML methods vs UEFI runtime services

Both are firmware-authored code that runs when the OS asks. AML is bytecode the OS interprets; runtime services are native code the OS jumps into.

|  | AML methods | UEFI runtime services |
| --- | --- | --- |
| Form | ACPI bytecode in the DSDT/SSDTs, run by the kernel's interpreter (ACPICA) | Native machine code in `EfiRuntimeServicesCode` memory, called through the EFI System Table |
| API shape | Named objects on devices (`\_SB.PCI0.GPP0._PS3`), meanings set by the ACPI spec | A small fixed function table |
| Scope | Per-device control: `_STA`, `_CRS`, `_PS0`/`_PS3`, `_OSC`, `_PRW`, GPE handlers, `Notify` | Variables, RTC, `ResetSystem`, `UpdateCapsule`, `SetVirtualAddressMap` |
| Who initiates | The OS, or a hardware event (SCI/GPE) whose handler the OS runs | Only the OS, by calling it |
| OS control | Mediated: touches only declared regions; the OS can trace, veto, decompile or override it | Opaque: full kernel privilege, can do anything the kernel can |

AML abstracts board-specific hardware sequences ("to power this slot down, toggle these GPIOs, then wait"). Runtime services abstract resources the firmware wants to keep owning, mainly the NVRAM variable store in SPI flash, which holds `BootOrder` and the Secure Boot keys. On x86 a `SetVariable` write usually traps into SMM so ring 0 cannot write flash directly.

Linux contains runtime services by running them in a separate `efi_mm` page table on a dedicated workqueue, mapping them RO/NX where firmware publishes `EFI_MEMORY_ATTRIBUTES_TABLE`, and offering `efi=noruntime`. For AML the equivalent levers are interpreter policy such as `acpi_osi=` and table overrides from the initrd.

**Confidential VMs change this picture.** A TDX guest has no SMM, so the bottom-left box disappears. TDVF (the TD firmware) builds the ACPI tables from what the VMM supplies, and those tables are measured into RTMR0. The guest still runs vendor-authored AML, but it can attest exactly which AML it ran.

## What the buses can't say about themselves

Self-enumerating buses (PCIe, USB) describe everything *below* their root. Something else has to describe the root itself and everything that isn't on such a bus. On servers and PCs that is ACPI; on embedded Arm and RISC-V it is usually devicetree.

- **Where the PCIe tree starts.** The ECAM base address, the bus-number range, and the memory and IO windows the host bridge decodes. ACPI: the `MCFG` table plus the host bridge's `_CRS`. Devicetree: a `pci@…` node with `reg`, `bus-range` and `ranges`.
- **How legacy interrupts route.** INTx pins to interrupt-controller inputs. ACPI: `_PRT`. Devicetree: `interrupt-map`.
- **Everything not on an enumerable bus.** CPUs, the interrupt controller, timers, the memory map, IOMMUs, NUMA topology, and on SoCs most peripherals, which sit at fixed MMIO addresses with nothing to probe. ACPI: `MADT`, `GTDT`, `IORT`/`DMAR`, `SRAT`, and device objects in the DSDT. Devicetree: a node per device, matched to a driver by its `compatible` string.

The layering, then:

```
  Plane 3   ACPI / devicetree  ──►  "ECAM is at 0xE000_0000, buses 0–255,
            (tables in RAM,          interrupt controller is at …, UART at …"
             built by firmware)
                 │
                 ▼
  Plane 2   enumeration        ──►  walks config space from that root,
            (CfgRd / CfgWr)          sizes BARs, programs bridges
                 │
                 ▼
  Plane 1   data path          ──►  MemRd / MemWr to the assigned BARs,
            (MemRd / MemWr)          queues, doorbells, MSI-X
```

### Device firmware vs platform firmware

"Firmware" means two different things, and only one of them belongs to this plane.

- **Device firmware** runs *on the device*, on its own microcontroller: an NVMe SSD's flash translation layer, a NIC's offload engine, a GPU's GSP, the MCU in a USB keyboard. Almost every device has it. The OS never runs or sees it; it sees only the device's interface (registers behind BARs, NVMe queues, USB descriptors) and reaches that interface over the transport. Sometimes the kernel driver loads the firmware at probe time, which is what the `linux-firmware` blobs for `iwlwifi` or `amdgpu` are.
- **Platform firmware** runs *on the host*: UEFI, AML, SMM handlers, and on their own cores the PSP or CSME. It drives no particular device; it describes and manages the machine as a whole. This is Plane 3.

The transport is neither. It is the wire and protocol a driver uses to reach a device's interface, with device firmware hiding behind that interface the way an AWS Nitro card hides the EBS storage network behind an NVMe device.

So each device has three independent properties: who *discovers* it (the bus itself, Plane 2, or the platform description, Plane 3), who *drives* it (a kernel driver, in both cases), and what *runs on it* (its own firmware, opaque to the OS). Whether that driver is upstream in Linux is a separate question again.

### Discoverable vs described, not on-board vs external

The in-band/out-of-band split follows the bus, not the device's location. On-die coprocessors are often dressed up as PCI devices and enumerate normally; an on-board touchpad needs ACPI because I2C has no discovery mechanism.

| Device | Where it lives | How the OS finds it |
| --- | --- | --- |
| External USB keyboard | External | In-band: USB enumeration |
| Onboard NIC, NVMe SSD | Board | In-band: PCIe enumeration |
| Intel iGPU, AMD PSP (`ccp`), Intel CSME (`mei`) | CPU die | In-band: they appear as PCI devices (the iGPU is `00:02.0`) |
| Monitor | External | In-band via the GPU: EDID read over DDC |
| Laptop I2C touchpad | Board | Out-of-band: an ACPI device node names the I2C bus, address and interrupt GPIO |
| Laptop battery, lid, power button | Board | Out-of-band: ACPI, usually through the embedded controller |
| Interrupt controller, timers | CPU die | Out-of-band: ACPI `MADT`/`GTDT` or devicetree |

Describing a device out-of-band doesn't replace its driver. For the touchpad, ACPI says where it is, and the ordinary `i2c-hid` driver does the rest.

### Why a laptop battery can't enumerate itself

In-band discovery needs two things from a bus: a way to address every possible slot, and a standard place where each device reports its identity. PCIe has both (walk every bus/device/function, read the vendor ID at offset 0). USB has both (a new device answers at address 0 and hands over descriptors). The buses a laptop battery hangs off have neither:

```
CPU ──eSPI/LPC──► embedded controller (EC) ──SMBus──► battery pack
                  IO ports 0x62 / 0x66              (fuel-gauge chip)
                  vendor-specific register map
```

- **The embedded controller** is a small microcontroller, descended from the PC keyboard controller, that handles the battery, fans, keyboard matrix, lid and power button. The OS reaches it through two legacy IO ports, and behind them is a register map each vendor invents. There is no ID register and no descriptor.
- **SMBus and I2C** have no enumeration: devices sit at fixed 7-bit addresses with no standard ID, and blind probing can misconfigure or brick parts, so OSes don't scan them.
- **The lid switch and power button** are often just wires into GPIO pins. A wire can't describe itself.

This is where ACPI's executable description earns its keep. The ACPI spec defines a standard battery interface, `_BIX` for static information and `_BST` for current status, and each vendor's AML implements those methods by reading its own EC registers. Linux's one generic ACPI battery driver calls `_BST` and gets the same answer format on every laptop. The AML is a per-board driver shim that ships with the hardware.

None of this is a law of nature, just the plumbing chosen. A USB UPS enumerates in-band as a HID Power Device and reports battery state through standard HID reports, with no ACPI involved. Chromebooks use a documented EC protocol (`cros_ec`) with an upstream driver: the EC still has to be *located* via ACPI or devicetree, but after that nothing vendor-opaque is needed.

### ACPI vs devicetree: executable vs pure data

A devicetree is a static description. You write it as `.dts` source, compile it with `dtc` into a `.dtb` blob, and the bootloader hands the blob to the kernel:

```dts
uart0: serial@9000000 {
    compatible = "arm,pl011", "arm,primecell";
    reg = <0x0 0x9000000 0x0 0x1000>;          // MMIO base + size
    interrupts = <GIC_SPI 1 IRQ_TYPE_LEVEL_HIGH>;
    clocks = <&apb_pclk>;
};
```

ACPI describes the same things but also ships **executable code**: AML methods such as `_PS3` (power off), `_STA` (present?) and `_OSC` (capability negotiation), plus handlers for hardware events. Firmware can hide a board-specific sequence ("toggle these GPIOs in this order") behind a standard method name. On a devicetree system that knowledge has to live in kernel drivers instead, and runtime power control goes through firmware calls such as PSCI or SCMI over SMC.

Arm uses both, and pairs them with UEFI as independent choices:

- **SBBR (SystemReady SR)**, for servers: UEFI plus ACPI, so a generic distro kernel boots unmodified, as on x86.
- **EBBR**, for embedded: a UEFI subset plus devicetree. U-Boot implements enough of the UEFI API for a normal EFI loader, and publishes the DTB through the EFI configuration table.

The classic ACPI layering diagram (OS → ACPI driver and AML interpreter → ACPI BIOS, tables and registers → hardware) is broadly right, with two caveats. The "BIOS interface" arrow suggests the OS calls into firmware to do ACPI work; it doesn't. It interprets AML, and the AML touches hardware directly through `OperationRegion`s. And "ACPI registers" are optional now: hardware-reduced ACPI, used on Arm servers and many modern x86 SoCs, drops the fixed-hardware registers entirely.

### Virtio: one transport, three ways to be found

Virtio's virtqueues are the same on every platform, but a guest can find a virtio device three ways, and they split cleanly along the planes:

| Surfacing | How the guest finds it | Plane doing the discovery |
| --- | --- | --- |
| virtio-pci | Ordinary PCI enumeration (vendor ID `0x1AF4`) | Plane 2 |
| virtio-mmio | A DT node, an ACPI device, or a kernel argument like `virtio_mmio.device=` | Plane 3 |
| virtio-ccw | s390 channel subsystem | Its own channel I/O model |

virtio-mmio is simpler and cheaper for a VMM to emulate than a PCI bus, which is why minimal VMMs like Firecracker use it. The price is that it isn't discoverable, so the VMM must describe it out-of-band. On x86, Firecracker does this by appending `virtio_mmio.device=` arguments to the kernel command line.

### Runtime: the platform plane doesn't stop at boot

Planes 1 and 2 are OS code talking to hardware. Plane 3 keeps running vendor code after boot: AML interpreted by the OS, UEFI runtime services called by it, and SMM handlers that preempt it unseen (see the after-boot diagram above). AML is also often a trampoline into SMM: a method declares an `OperationRegion` over the SMI command port (commonly `0xB2`), writes a value, and the CPU drops into ring −2.

Historically ACPI was a move *toward* the OS. Its predecessor, APM, had the BIOS run power management itself, often from SMM, behind the OS's back. ACPI's central idea is OSPM, OS-directed power management. But what it moved to the OS was *execution*, not *knowledge*. The OS runs the vendor's code without understanding it.

## The stable interface, and its critic

Every layer of the device stack has the same winning move: define a stable interface, then swap the implementation freely behind it. NVMe hides whether the transport is PCIe, TCP or a Nitro card. PCIe's config space hides that the "bus" is a packet network. ACPI is the same move one level down: a stable description interface, so one kernel can boot on thousands of boards it has never seen.

Bryan Cantrill's critique ([OSFC 2022 talk](https://speakerdeck.com/bcantrill/i-have-come-to-bury-the-bios-not-to-open-it-the-need-for-holistic-systems), [Chips and Cheese interview](https://chipsandcheese.com/p/an-interview-with-oxides-bryan-cantrill)) is aimed exactly at that move at the platform layer. A stable boundary with proprietary code on the far side lets vendors leave complicated SoCs undocumented, so the firmware implementation becomes the documentation. AML is that idea taken literally: vendor knowledge compiled into bytecode. The `_OSI("Windows 20xx")` query, where firmware branches on which OS it thinks it is running under and Linux answers by claiming to be Windows, shows the boundary hardening into a compatibility contract.

Oxide's answer is to remove the boundary: a co-designed OS (Helios) that performs platform initialization itself, never pseudo-resets the machine to hand state to a later stage through an interface like ACPI, and treats any entry into SMM as a panic. The cost is one Cantrill accepts openly: the OS must become SoC-specific. That works when you ship one sled design and your own OS. It doesn't work for a distro that has to boot every laptop, which is the market ACPI and devicetree exist to serve.

So the stable-interface pattern that wins everywhere else in the stack is contested at exactly one layer: the one where the interface separates the OS from the vendor who built the machine.

## References

- [UEFI and ACPI specifications (UEFI Forum)](https://uefi.org/specifications)
- [Devicetree specification](https://www.devicetree.org/specifications/)
- [Linux kernel ACPI firmware guide](https://docs.kernel.org/firmware-guide/acpi/index.html)
- [Why do we need AML? (Stack Overflow)](https://stackoverflow.com/questions/43088172/why-do-we-need-aml-acpi-machine-language)
- [I have come to bury the BIOS, not to open it (Bryan Cantrill, OSFC 2022)](https://speakerdeck.com/bcantrill/i-have-come-to-bury-the-bios-not-to-open-it-the-need-for-holistic-systems)
- [An interview with Oxide's Bryan Cantrill (Chips and Cheese)](https://chipsandcheese.com/p/an-interview-with-oxides-bryan-cantrill)
