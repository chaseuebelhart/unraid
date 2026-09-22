# unraid-vm

Boot Unraid in a KVM/libvirt VM using a *BIOS-bootable* “USB” disk image built from an extracted Unraid distribution.

This repo’s main entrypoint is:
- [unraid-vm-lab.sh](unraid-vm-lab.sh)

It automates:
- Building a bootable Unraid “USB” image (raw) using Syslinux
- Creating two additional VM disks (array + cache)
- Creating a libvirt VM and exposing the console over VNC on `127.0.0.1`

## What This Script Actually Does

### 1) Builds a bootable “USB” image
The script creates a raw disk image (default 1024MB), then:
- Creates an MBR partition table with a single FAT32 partition
- Formats the partition as FAT32 (label `UNRAID`)
- Copies Unraid boot files onto it (including required `*.sha256` files)
- Installs Syslinux to the FAT32 partition and writes a Syslinux MBR to the disk

Why this matters:
- SeaBIOS expects a real MBR + partition layout to boot reliably.
- Unraid’s boot process validates `bzimage.sha256`/etc; missing checksum files halts boot.

### 2) Avoids Syslinux “COM32” boot errors
If Syslinux core and its `menu.c32` (and friends) don’t match, you’ll see errors like:
- `Failed to load COM32 file menu.c32`

To prevent this, after copying the Unraid `syslinux/` directory, the script overwrites these modules with the host’s matching Syslinux BIOS modules (Ubuntu path):
- `/usr/lib/syslinux/modules/bios/menu.c32`
- `/usr/lib/syslinux/modules/bios/vesamenu.c32`
- `/usr/lib/syslinux/modules/bios/libcom32.c32`
- `/usr/lib/syslinux/modules/bios/libutil.c32`
- `/usr/lib/syslinux/modules/bios/ldlinux.c32`

### 3) Uses the system libvirt daemon
This script forces `qemu:///system` so your VM and images live in the normal system libvirt instance and can access `/var/lib/libvirt/images/...`.

If you accidentally use `qemu:///session`, you can hit:
- `Permission denied` accessing `/var/lib/libvirt/images/...`

### 4) Creates the VM
The VM is created with `virt-install` and:
- Boot disk attached as `bus=usb` (so Unraid recognizes it as a “flash” style device)
- Array + cache disks as SATA
- NAT networking via libvirt `default` network (good for Wi‑Fi)
- VNC bound to `127.0.0.1`

## Requirements

You need an extracted Unraid distribution directory containing at least:
- `bzimage`, `bzroot`, `bzmodules`, `bzfirmware`
- `bzimage.sha256`, `bzroot.sha256`, `bzmodules.sha256`, `bzfirmware.sha256`
- `bzroot-gui` + `bzroot-gui.sha256` (optional, for GUI mode)
- `syslinux/` directory from the Unraid distribution

On Ubuntu, the script attempts to install dependencies:
- `qemu-kvm`, `libvirt-daemon-system`, `libvirt-clients`, `virtinst`
- `dosfstools`, `syslinux`, `syslinux-utils`

## Usage

### Create/recreate the VM

```bash
./unraid-vm-lab.sh \
  --src /home/chase/projects/homelab/unraid-vm/unraid-extracted \
  --imagedir /var/lib/libvirt/images/unraid-lab \
  --net default \
  --name unraid-test
```

### (Recommended) Passthrough a real USB stick for licensing identity

If you plugged in a USB stick and want Unraid to see a *real* USB device identity (more reliable for registration/licensing), pass it through by vendor:product ID:

1) Find the VID:PID

```bash
lsusb
```

Example (Verbatim STORE N GO): `18a5:0250`

2) Start the VM with passthrough enabled

```bash
./unraid-vm-lab.sh \
  --src /home/chase/projects/homelab/unraid-vm/unraid-extracted \
  --imagedir /var/lib/libvirt/images/unraid-lab \
  --net default \
  --name unraid-test \
  --host-usb 18a5:0250
```

Notes:
- If your desktop auto-mounts the USB stick, unmount it before starting the VM.
- This does not attempt to bypass licensing; it just passes the physical device through.

### Boot Unraid *from* the physical USB stick (so Unraid uses its identity)

If you want Unraid to treat the physical USB stick as the actual boot flash (so Tools → Registration reflects the real device), you must:

1) Write the Unraid boot files onto the physical stick (this **erases it**)
2) Boot the VM from the passed-through stick (no virtual `*-usb.img`)

Example for the Verbatim stick:

```bash
# WARNING: this erases /dev/sda
./unraid-vm-lab.sh \
  --destroy --name unraid-test

./unraid-vm-lab.sh \
  --src /home/chase/projects/homelab/unraid-vm/unraid-extracted \
  --imagedir /var/lib/libvirt/images/unraid-lab \
  --net default \
  --name unraid-test \
  --flash-dev /dev/sda \
  --host-usb 18a5:0250
```

You will be prompted to type `ERASE` unless you pass `--yes-wipe`.

### Connect with Remmina (VNC)
Get the VNC display:

```bash
sudo virsh --connect qemu:///system vncdisplay unraid-test
```

If it shows `127.0.0.1:0`, connect to `127.0.0.1:5900`.

### Find the Unraid IP (NAT)

```bash
sudo virsh --connect qemu:///system net-dhcp-leases default
```

Then open:

```text
http://192.168.122.X/
```

### Destroy / clean everything

```bash
./unraid-vm-lab.sh --destroy --name unraid-test
```

### Start the VM later (no rebuild)

Once the VM is created, you do *not* need to rebuild images every time.

Option A (script):

```bash
./unraid-vm-lab.sh --name unraid-test --start
```

Option B (direct libvirt):

```bash
sudo virsh --connect qemu:///system start unraid-test
sudo virsh --connect qemu:///system vncdisplay unraid-test
```

## Common Issues & Fixes

### `bzimage.sha256 not present` during boot
Cause: checksum files weren’t present on the boot device.
Fix: this script copies `*.sha256` alongside the `bz*` files.

### `Failed to load COM32 file menu.c32`
Cause: Syslinux core/modules mismatch.
Fix: script overwrites the `syslinux/*.c32` modules with host Syslinux BIOS modules.

### `Permission denied` for `/var/lib/libvirt/images/...`
Cause: using the per-user libvirt connection.
Fix: script uses `qemu:///system` and runs `virt-install`/`virsh` with `sudo` when needed.

### Unraid web UI says “Cannot access your USB Flash boot device”
Cause: Unraid expects a USB flash boot device and can be picky about how it’s presented.
Fix (in this script): attach boot disk as USB (`bus=usb`).

If licensing/registration still complains, see the licensing section below.

## Licensing & USB GUID (Important)

Unraid licenses are tied to a unique identifier (commonly referred to as the USB flash GUID/device identity).

### Should you use a real USB flash drive?
If you want a stable, supportable identity for licensing/registration, **yes**—using a real USB stick and passing it through to the VM is the most reliable approach.

Typical setup:
- Plug in a dedicated USB flash drive
- Attach/pass it through to the VM via libvirt/virt-manager

This way, Unraid sees an actual USB device identity that stays consistent.

### Can you “programmatically reuse the same USB GUID” in a VM?
There are ways to make a *virtual device identity* stable (e.g., stable USB device serials), but **attempting to spoof or replicate a specific USB GUID/device identity to reuse a license** may violate Unraid’s license terms.

What I can help with (legit):
- Passing through a real USB device to the VM
- Making your VM configuration stable/reproducible
- Troubleshooting when Unraid can’t read the boot device

What I won’t help with:
- Bypassing or defeating Unraid’s licensing checks
- Spoofing/copying another device’s GUID to avoid purchasing a license

## Notes

- This is a lab/learning setup. For production, Unraid is typically installed on a real USB stick and run on bare metal.
- If you want this script to automatically passthrough a real USB device (vendor/product), say so and we can add an explicit, opt-in flag like `--usb-host 1234:abcd`.
