#!/usr/bin/env bash
# unraid-vm-lab.sh
#
# Creates an Unraid test VM on Ubuntu using KVM/libvirt with:
# - A BIOS-bootable "USB" disk image (raw) built from Unraid ZIP contents
#   (writes Syslinux MBR + installs syslinux bootloader + copies Unraid files)
# - Virtual array + cache disks (qcow2)
# - NAT networking via libvirt "default" network (works on Wi-Fi)
# - VNC console bound to 127.0.0.1
# - Debug logs + readable output
#
# Key design:
# - WORKDIR is for logs/temp mounts and must be user-writable (default: ~/unraid-lab)
# - IMAGEDIR is for VM disk images and must be readable by libvirt-qemu
#   (default: /var/lib/libvirt/images/unraid-lab)
#
# REQUIREMENTS:
# - Unraid files in UNRAID_SRC_DIR:
#   bzimage bzroot bzmodules bzfirmware syslinux/ (folder)
# - Ubuntu packages:
#   qemu-kvm libvirt-daemon-system libvirt-clients virtinst dosfstools syslinux syslinux-utils
#
# Usage:
#   chmod +x unraid-vm-lab.sh
#   ./unraid-vm-lab.sh --src ~/projects/unraid-vm/unraid-extracted --net default
#   ./unraid-vm-lab.sh --src ~/projects/unraid-vm/unraid-extracted --imagedir /var/lib/libvirt/images/unraid-lab --net default
#
# Destroy:
#   ./unraid-vm-lab.sh --destroy --name unraid-test
#
set -Eeuo pipefail

########################################
# Defaults (override via flags/env)
########################################
VM_NAME="${VM_NAME:-unraid-test}"

# Use the system libvirt daemon by default.
# If you accidentally use a per-user session (qemu:///session), it won't have access
# to /var/lib/libvirt/images and you'll hit "Permission denied" when starting pools.
LIBVIRT_URI="${LIBVIRT_URI:-qemu:///system}"

# Optional: passthrough a real USB device into the VM (recommended for stable Unraid licensing identity).
# Format: VID:PID (hex), e.g. 18a5:0250
HOST_USB_ID="${HOST_USB_ID:-}"

# Optional: install Unraid boot to a physical USB block device and boot VM from it.
# Example: /dev/sda (THIS WILL ERASE IT)
FLASH_DEV="${FLASH_DEV:-}"
WIPE_YES=0

# Logs/temp files (must be writable by your user)
WORKDIR="${WORKDIR:-$HOME/unraid-lab}"

# VM images (must be readable by libvirt-qemu; default is libvirt's images dir)
IMAGEDIR="${IMAGEDIR:-/var/lib/libvirt/images/unraid-lab}"

# IMPORTANT: this must contain Unraid bz* AND syslinux/ from the ZIP extraction
UNRAID_SRC_DIR="${UNRAID_SRC_DIR:-$HOME/unraid-vm}"   # must contain bz* and syslinux/

RAM_MB="${RAM_MB:-4096}"
VCPUS="${VCPUS:-2}"

USB_SIZE_MB="${USB_SIZE_MB:-1024}"                    # "USB" image size
ARRAY_SIZE_GB="${ARRAY_SIZE_GB:-50}"
CACHE_SIZE_GB="${CACHE_SIZE_GB:-20}"
DISK_FMT="${DISK_FMT:-qcow2}"                         # qcow2 recommended for lab
OS_VARIANT="${OS_VARIANT:-generic}"                   # generic is fine

# VNC UI by default
GRAPHICS="${GRAPHICS:-vnc}"                           # vnc or none
VNC_LISTEN="${VNC_LISTEN:-127.0.0.1}"                 # bind VNC locally by default
CONSOLE="${CONSOLE:-pty}"                             # for serial console if headless

# Networking defaults:
# - NAT via libvirt network "default" (works everywhere, including Wi-Fi)
NET_MODE="${NET_MODE:-network}"                       # "network" (NAT) or "bridge" (LAN bridge)
NET_NAME="${NET_NAME:-default}"                       # for NET_MODE=network
BRIDGE_NAME="${BRIDGE_NAME:-br0}"                     # for NET_MODE=bridge (must exist)

DESTROY_ONLY=0
NO_INSTALL=0
START_ONLY=0

########################################
# Logging (in WORKDIR; user-writable)
########################################
mkdir -p "$WORKDIR"
LOGFILE="$WORKDIR/${VM_NAME}.log"
touch "$LOGFILE"

ts() { date +"%Y-%m-%d %H:%M:%S"; }

log()  { echo -e "[$(ts)] $*" | tee -a "$LOGFILE" >&2; }
info() { log "ℹ️  $*"; }
ok()   { log "✅ $*"; }
warn() { log "⚠️  $*"; }
err()  { log "❌ $*"; }

virsh_cmd() {
  sudo_wrap virsh --connect "$LIBVIRT_URI" "$@"
}

run() {
  info "RUN: $*"
  ( "$@" ) 2>&1 | tee -a "$LOGFILE"
}

die() { err "$*"; exit 1; }

########################################
# Helpers
########################################
need_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1"
}

sudo_wrap() {
  if [[ $EUID -ne 0 ]]; then
    sudo "$@"
  else
    "$@"
  fi
}

usage() {
  cat <<EOF
Unraid VM Lab Setup Script (BIOS boot via Syslinux)

Flags:
  --name NAME            VM name (default: $VM_NAME)
  --src DIR              Directory containing Unraid bz* and syslinux/ (default: $UNRAID_SRC_DIR)
  --workdir DIR          Logs/temp dir (user-writable) (default: $WORKDIR)
  --imagedir DIR         VM images dir (libvirt-qemu readable) (default: $IMAGEDIR)

  --ram MB               RAM in MB (default: $RAM_MB)
  --vcpus N              vCPU count (default: $VCPUS)
  --array GB             Array disk size in GB (default: $ARRAY_SIZE_GB)
  --cache GB             Cache disk size in GB (default: $CACHE_SIZE_GB)

  --net NAME             libvirt NAT network name (sets NET_MODE=network) (default: $NET_NAME)
  --bridge BR0           Bridge interface (sets NET_MODE=bridge) (default: $BRIDGE_NAME)

  --graphics vnc|none     VNC console or headless (default: $GRAPHICS)
  --vnc-listen IP         VNC bind address (default: $VNC_LISTEN)

  --host-usb VID:PID       Passthrough a physical USB device to the VM (e.g. 18a5:0250)
  --flash-dev /dev/sdX      Install Unraid boot to a physical USB block device (ERASES IT)
  --yes-wipe               Skip confirmation prompt for --flash-dev (DANGEROUS)

  --destroy              Destroy VM + delete artifacts (uses --name)
  --no-install           Create images but do NOT create VM
  --start                Start existing VM only (no rebuild)

Examples:
  ./unraid-vm-lab.sh --src ~/projects/unraid-vm/unraid-extracted --net default
  ./unraid-vm-lab.sh --destroy --name unraid-test
EOF
}

########################################
# Arg parsing
########################################
while [[ $# -gt 0 ]]; do
  case "$1" in
    --name) VM_NAME="$2"; shift 2 ;;
    --src) UNRAID_SRC_DIR="$2"; shift 2 ;;
    --workdir) WORKDIR="$2"; shift 2 ;;
    --imagedir) IMAGEDIR="$2"; shift 2 ;;

    --ram) RAM_MB="$2"; shift 2 ;;
    --vcpus) VCPUS="$2"; shift 2 ;;
    --array) ARRAY_SIZE_GB="$2"; shift 2 ;;
    --cache) CACHE_SIZE_GB="$2"; shift 2 ;;

    --net) NET_MODE="network"; NET_NAME="$2"; shift 2 ;;
    --bridge) NET_MODE="bridge"; BRIDGE_NAME="$2"; shift 2 ;;

    --graphics) GRAPHICS="$2"; shift 2 ;;
    --vnc-listen) VNC_LISTEN="$2"; shift 2 ;;

    --host-usb) HOST_USB_ID="$2"; shift 2 ;;
    --flash-dev) FLASH_DEV="$2"; shift 2 ;;
    --yes-wipe) WIPE_YES=1; shift ;;

    --destroy) DESTROY_ONLY=1; shift ;;
    --no-install) NO_INSTALL=1; shift ;;
    --start) START_ONLY=1; shift ;;

    -h|--help) usage; exit 0 ;;
    *) die "Unknown arg: $1 (use --help)" ;;
  esac
done

# Re-derive logging after args are applied
mkdir -p "$WORKDIR"
LOGFILE="$WORKDIR/${VM_NAME}.log"
touch "$LOGFILE" || die "Cannot write log to $LOGFILE. Choose a user-writable --workdir."

# Image paths live in IMAGEDIR
USB_IMG="$IMAGEDIR/${VM_NAME}-usb.img"
ARRAY_IMG="$IMAGEDIR/${VM_NAME}-array.${DISK_FMT}"
CACHE_IMG="$IMAGEDIR/${VM_NAME}-cache.${DISK_FMT}"

# Temp mount dir lives in WORKDIR
MNT_DIR="$WORKDIR/mnt-usb"

########################################
# Destroy path
########################################
destroy_vm() {
  info "Destroy requested for VM '$VM_NAME'"

  if virsh_cmd dominfo "$VM_NAME" >/dev/null 2>&1; then
    info "VM exists. Attempting shutdown..."
    virsh_cmd shutdown "$VM_NAME" >/dev/null 2>&1 || true
    sleep 2
    if virsh_cmd domstate "$VM_NAME" 2>/dev/null | grep -qi running; then
      warn "VM still running; forcing destroy..."
      virsh_cmd destroy "$VM_NAME" >/dev/null 2>&1 || true
    fi

    info "Undefining VM (and NVRAM if present)..."
    virsh_cmd undefine "$VM_NAME" --nvram >/dev/null 2>&1 || \
      virsh_cmd undefine "$VM_NAME" >/dev/null 2>&1 || true
    ok "VM undefined."
  else
    warn "VM '$VM_NAME' not found in libvirt."
  fi

  info "Deleting images from IMAGEDIR ($IMAGEDIR):"
  sudo_wrap rm -f "$USB_IMG" "$ARRAY_IMG" "$CACHE_IMG" || true

  info "Cleaning temp mount dir:"
  sudo_wrap umount "$MNT_DIR" >/dev/null 2>&1 || true
  rm -rf "$MNT_DIR" || true

  ok "Cleanup complete."
}

if [[ $DESTROY_ONLY -eq 1 ]]; then
  need_cmd virsh
  destroy_vm
  exit 0
fi

########################################
# Validate environment
########################################
info "Logging to: $LOGFILE"
info "VM_NAME=$VM_NAME"
info "WORKDIR=$WORKDIR"
info "IMAGEDIR=$IMAGEDIR"
info "UNRAID_SRC_DIR=$UNRAID_SRC_DIR"
info "RAM_MB=$RAM_MB VCPUS=$VCPUS"
info "ARRAY_SIZE_GB=$ARRAY_SIZE_GB CACHE_SIZE_GB=$CACHE_SIZE_GB"
info "NET_MODE=$NET_MODE NET_NAME=$NET_NAME BRIDGE_NAME=${BRIDGE_NAME:-<none>}"
info "GRAPHICS=$GRAPHICS VNC_LISTEN=$VNC_LISTEN"
info "LIBVIRT_URI=$LIBVIRT_URI"

need_cmd bash
need_cmd qemu-img
need_cmd mkfs.vfat
need_cmd virt-install
need_cmd virsh
need_cmd truncate
need_cmd awk
need_cmd grep
need_cmd ip
need_cmd mount
need_cmd umount
need_cmd dd
need_cmd syslinux
need_cmd losetup
need_cmd sfdisk
need_cmd partprobe

validate_host_usb_id() {
  [[ -n "${HOST_USB_ID:-}" ]] || return 0
  if [[ ! "$HOST_USB_ID" =~ ^[0-9a-fA-F]{4}:[0-9a-fA-F]{4}$ ]]; then
    die "--host-usb must be VID:PID hex (e.g. 18a5:0250). Got: '$HOST_USB_ID'"
  fi
}

validate_flash_dev() {
  [[ -n "${FLASH_DEV:-}" ]] || return 0
  [[ -b "$FLASH_DEV" ]] || die "--flash-dev must be a block device path (e.g. /dev/sda). Got: '$FLASH_DEV'"

  # Refuse partition paths like /dev/sda1
  if [[ "$FLASH_DEV" =~ [0-9]+$ ]]; then
    die "--flash-dev must be the whole-disk device (e.g. /dev/sda), not a partition (e.g. /dev/sda1)."
  fi

  # Best-effort safety check: must be removable OR USB transport.
  local name
  name="$(basename "$FLASH_DEV")"
  local tran rm
  tran="$(lsblk -dn -o TRAN "$FLASH_DEV" 2>/dev/null || true)"
  rm="$(cat "/sys/block/${name}/removable" 2>/dev/null || echo 0)"
  if [[ "$tran" != "usb" && "$rm" != "1" ]]; then
    die "Refusing to write to '$FLASH_DEV' (TRAN='$tran', removable='$rm'). Use a removable USB drive."
  fi
}

confirm_wipe() {
  [[ -n "${FLASH_DEV:-}" ]] || return 0
  if [[ $WIPE_YES -eq 1 ]]; then
    warn "--yes-wipe set; proceeding to ERASE $FLASH_DEV"
    return 0
  fi

  err "About to ERASE and repartition: $FLASH_DEV"
  err "ALL DATA ON THIS DEVICE WILL BE LOST."
  read -r -p "Type ERASE to continue: " ans
  [[ "$ans" == "ERASE" ]] || die "Aborted."
}

install_unraid_to_physical_usb() {
  [[ -n "${FLASH_DEV:-}" ]] || return 0

  info "Installing Unraid boot onto physical USB device: $FLASH_DEV"
  validate_flash_dev
  confirm_wipe

  # Unmount any existing partitions on the device
  sudo_wrap umount "${FLASH_DEV}"* >/dev/null 2>&1 || true

  # Partition: one FAT32 LBA partition starting at 1MiB
  sudo_wrap sfdisk "$FLASH_DEV" >/dev/null <<'SFDISK'
label: dos
unit: sectors

start=2048, type=c, bootable
SFDISK

  sudo_wrap partprobe "$FLASH_DEV" >/dev/null 2>&1 || true
  sleep 0.2

  local part="${FLASH_DEV}1"
  [[ -b "$part" ]] || die "Expected partition not found: $part"

  sudo_wrap mkfs.vfat -F 32 -n UNRAID "$part"

  mkdir -p "$MNT_DIR"
  sudo_wrap umount "$MNT_DIR" >/dev/null 2>&1 || true
  sudo_wrap mount "$part" "$MNT_DIR"

  info "Copying Unraid boot files to physical USB..."
  for f in \
    bzimage bzimage.sha256 \
    bzroot bzroot.sha256 \
    bzmodules bzmodules.sha256 \
    bzfirmware bzfirmware.sha256
  do
    [[ -f "$UNRAID_SRC_DIR/$f" ]] && sudo_wrap cp "$UNRAID_SRC_DIR/$f" "$MNT_DIR/"
  done

  for f in bzroot-gui bzroot-gui.sha256; do
    [[ -f "$UNRAID_SRC_DIR/$f" ]] && sudo_wrap cp "$UNRAID_SRC_DIR/$f" "$MNT_DIR/"
  done

  if [[ -d "$UNRAID_SRC_DIR/config" ]]; then
    sudo_wrap mkdir -p "$MNT_DIR/config"
    sudo_wrap cp -r "$UNRAID_SRC_DIR/config/." "$MNT_DIR/config/"
  fi

  sudo_wrap mkdir -p "$MNT_DIR/syslinux"
  sudo_wrap cp -r "$UNRAID_SRC_DIR/syslinux/." "$MNT_DIR/syslinux/"

  # Overwrite COM32 modules with host-matching versions.
  local sys_mod_dir="/usr/lib/syslinux/modules/bios"
  if [[ -d "$sys_mod_dir" ]]; then
    for f in menu.c32 vesamenu.c32 libcom32.c32 libutil.c32 ldlinux.c32; do
      [[ -f "$sys_mod_dir/$f" ]] && sudo_wrap cp "$sys_mod_dir/$f" "$MNT_DIR/syslinux/$f"
    done
  fi

  sudo_wrap sync
  sudo_wrap umount "$MNT_DIR"

  # Install syslinux to the partition and write Syslinux MBR to the disk.
  sudo_wrap syslinux --directory syslinux --install "$part"

  local mbr_bin="/usr/lib/syslinux/mbr/mbr.bin"
  [[ -f "$mbr_bin" ]] || die "Syslinux MBR not found at $mbr_bin"
  sudo_wrap dd if="$mbr_bin" of="$FLASH_DEV" bs=440 count=1 conv=notrunc status=none

  ok "Physical USB is now Unraid-bootable: $FLASH_DEV"
}

attach_host_usb() {
  [[ -n "${HOST_USB_ID:-}" ]] || return 0

  local vid="${HOST_USB_ID%%:*}"
  local pid="${HOST_USB_ID##*:}"
  local xml="$WORKDIR/${VM_NAME}-host-usb.xml"

  info "Attaching physical USB device to VM: ${vid}:${pid}"
  cat > "$xml" <<EOF
<hostdev mode='subsystem' type='usb' managed='yes'>
  <source>
    <vendor id='0x${vid}'/>
    <product id='0x${pid}'/>
  </source>
  <boot order='1'/>
</hostdev>
EOF

  # Attach live (if running) and persistently.
  if virsh_cmd attach-device "$VM_NAME" "$xml" --live >/dev/null 2>&1; then
    ok "USB passthrough attached live (${vid}:${pid})."
  else
    warn "USB passthrough live-attach failed (${vid}:${pid}). Will still try to persist it."
  fi

  if virsh_cmd attach-device "$VM_NAME" "$xml" --config >/dev/null 2>&1; then
    ok "USB passthrough persisted in VM config (${vid}:${pid})."
  else
    warn "USB passthrough config-attach failed (${vid}:${pid})."
  fi
}

if ! egrep -q '(vmx|svm)' /proc/cpuinfo; then
  warn "No vmx/svm flags detected. VM may be slow if virtualization disabled in BIOS."
fi

########################################
# Install packages (best-effort)
########################################
install_deps() {
  info "Ensuring KVM/libvirt tools are installed..."
  if command -v apt-get >/dev/null 2>&1; then
    sudo_wrap apt-get update -y 2>&1 | tee -a "$LOGFILE" || true
    sudo_wrap apt-get install -y \
      qemu-kvm libvirt-daemon-system libvirt-clients virtinst \
      bridge-utils dosfstools syslinux syslinux-utils 2>&1 | tee -a "$LOGFILE" || true
    sudo_wrap systemctl enable --now libvirtd 2>&1 | tee -a "$LOGFILE" || true
    ok "Dependency install attempt complete (check log if anything failed)."
  else
    warn "apt-get not found; skipping dependency install."
  fi
}

install_deps

validate_host_usb_id
validate_flash_dev

########################################
# Validate Unraid files exist
########################################
require_unraid_files() {
  local missing=0
  for f in bzimage bzroot bzmodules bzfirmware; do
    if [[ ! -f "$UNRAID_SRC_DIR/$f" ]]; then
      err "Missing: $UNRAID_SRC_DIR/$f"
      missing=1
    fi
  done

  if [[ ! -d "$UNRAID_SRC_DIR/syslinux" ]]; then
    err "Missing: $UNRAID_SRC_DIR/syslinux/ directory (needed for syslinux.cfg + menu.c32)"
    missing=1
  fi

  [[ $missing -eq 0 ]] || die "Unraid boot files missing. Use the extracted ZIP folder containing bz* + syslinux/."
  ok "Found required Unraid files in $UNRAID_SRC_DIR"
}

require_unraid_files

########################################
# Ensure IMAGEDIR exists & is libvirt-qemu readable
########################################
prepare_imagedir() {
  info "Preparing IMAGEDIR: $IMAGEDIR"
  sudo_wrap mkdir -p "$IMAGEDIR"

  # Ensure directory is searchable by libvirt-qemu
  sudo_wrap chown libvirt-qemu:kvm "$IMAGEDIR" || true
  sudo_wrap chmod 750 "$IMAGEDIR" || true

  ok "IMAGEDIR ready."
}

########################################
# Create BOOTABLE USB image (raw) + FAT32 + Syslinux MBR + syslinux --install
########################################
create_usb_image() {
  info "Creating BOOTABLE Unraid USB image: $USB_IMG ($USB_SIZE_MB MB)"

  sudo_wrap rm -f "$USB_IMG"

  # Create raw disk
  sudo_wrap truncate -s "${USB_SIZE_MB}M" "$USB_IMG"

  # We create a real MBR partition table + FAT32 partition so SeaBIOS boots reliably.
  # (Formatting the whole disk image as FAT would overwrite the MBR.)
  local mbr_bin="/usr/lib/syslinux/mbr/mbr.bin"
  [[ -f "$mbr_bin" ]] || die "Syslinux MBR not found at $mbr_bin (install: sudo apt install syslinux syslinux-utils)"

  local loopdev=""
  local partdev=""
  mkdir -p "$MNT_DIR"
  sudo_wrap umount "$MNT_DIR" >/dev/null 2>&1 || true

  cleanup_usb_image() {
    sudo_wrap umount "$MNT_DIR" >/dev/null 2>&1 || true
    if [[ -n "${loopdev:-}" ]]; then
      sudo_wrap losetup -d "$loopdev" >/dev/null 2>&1 || true
    fi
  }
  trap cleanup_usb_image RETURN

  # Create a loop device with partition scanning enabled
  loopdev=$(sudo_wrap losetup --find --show --partscan "$USB_IMG")
  partdev="${loopdev}p1"

  # One FAT32 LBA partition starting at 1MiB
  sudo_wrap sfdisk "$loopdev" >/dev/null <<'SFDISK'
label: dos
unit: sectors

start=2048, type=c, bootable
SFDISK

  # Ensure kernel sees ${loopdev}p1
  if [[ ! -b "$partdev" ]]; then
    sudo_wrap partprobe "$loopdev" >/dev/null 2>&1 || true
    sleep 0.2
  fi
  [[ -b "$partdev" ]] || die "Partition device not found after sfdisk: $partdev"

  # Create FAT32 filesystem with label on the partition
  sudo_wrap mkfs.vfat -F 32 -n UNRAID "$partdev"

  sudo_wrap mount "$partdev" "$MNT_DIR"

  info "Copying Unraid boot files..."
  # Unraid expects both the images and their accompanying .sha256 files.
  # Missing checksums will halt boot with a prompt to reboot.
  for f in \
    bzimage bzimage.sha256 \
    bzroot bzroot.sha256 \
    bzmodules bzmodules.sha256 \
    bzfirmware bzfirmware.sha256
  do
    [[ -f "$UNRAID_SRC_DIR/$f" ]] && sudo_wrap cp "$UNRAID_SRC_DIR/$f" "$MNT_DIR/"
  done

  # GUI mode needs bzroot-gui (if present in the extracted distribution)
  for f in bzroot-gui bzroot-gui.sha256; do
    [[ -f "$UNRAID_SRC_DIR/$f" ]] && sudo_wrap cp "$UNRAID_SRC_DIR/$f" "$MNT_DIR/"
  done

  # Persisted config directory (identity/network settings). Safe to include for VMs too.
  if [[ -d "$UNRAID_SRC_DIR/config" ]]; then
    sudo_wrap mkdir -p "$MNT_DIR/config"
    sudo_wrap cp -r "$UNRAID_SRC_DIR/config/." "$MNT_DIR/config/"
  fi

  # Copy full syslinux folder from Unraid ZIP (contains syslinux.cfg, menu.c32, etc.)
  sudo_wrap mkdir -p "$MNT_DIR/syslinux"
  # Avoid -a: vfat doesn't support ownership/perms and cp will error under set -e.
  sudo_wrap cp -r "$UNRAID_SRC_DIR/syslinux/." "$MNT_DIR/syslinux/"

  # IMPORTANT: Syslinux COM32 modules must match the Syslinux core version.
  # Unraid's shipped menu.c32 can be incompatible with the distro syslinux we install,
  # leading to: "Failed to load COM32 file menu.c32".
  # Use the host's BIOS modules to match the installed syslinux.
  local sys_mod_dir="/usr/lib/syslinux/modules/bios"
  if [[ -d "$sys_mod_dir" ]]; then
    for f in menu.c32 vesamenu.c32 libcom32.c32 libutil.c32 ldlinux.c32; do
      if [[ -f "$sys_mod_dir/$f" ]]; then
        sudo_wrap cp "$sys_mod_dir/$f" "$MNT_DIR/syslinux/$f"
      fi
    done
  else
    warn "Syslinux BIOS module dir not found at $sys_mod_dir; leaving Unraid-provided COM32 modules in place."
  fi

  sudo_wrap sync
  sudo_wrap umount "$MNT_DIR"

  # Install syslinux bootloader into the FAT32 partition.
  # Unraid keeps its config at /syslinux/syslinux.cfg, so point syslinux at that directory.
  sudo_wrap syslinux --directory syslinux --install "$partdev"

  # Write a proper Syslinux MBR (critical for SeaBIOS boot)
  sudo_wrap dd if="$mbr_bin" of="$loopdev" bs=440 count=1 conv=notrunc status=none

  # Detach loop device cleanly
  sudo_wrap losetup -d "$loopdev"
  loopdev=""

  # Permissions for libvirt
  sudo_wrap chown libvirt-qemu:kvm "$USB_IMG"
  sudo_wrap chmod 640 "$USB_IMG"

  ok "USB image is BIOS-bootable (Syslinux installed)."
}

########################################
# Create virtual disks
########################################
create_disks() {
  info "Creating array disk: $ARRAY_IMG (${ARRAY_SIZE_GB}G)"
  sudo_wrap rm -f "$ARRAY_IMG"
  sudo_wrap qemu-img create -f "$DISK_FMT" "$ARRAY_IMG" "${ARRAY_SIZE_GB}G" | tee -a "$LOGFILE"

  info "Creating cache disk: $CACHE_IMG (${CACHE_SIZE_GB}G)"
  sudo_wrap rm -f "$CACHE_IMG"
  sudo_wrap qemu-img create -f "$DISK_FMT" "$CACHE_IMG" "${CACHE_SIZE_GB}G" | tee -a "$LOGFILE"

  # Ownership readable by libvirt-qemu
  sudo_wrap chown libvirt-qemu:kvm "$ARRAY_IMG" "$CACHE_IMG"
  sudo_wrap chmod 640 "$ARRAY_IMG" "$CACHE_IMG"

  ok "Disks created."
}

########################################
# VM lifecycle helpers
########################################
vm_exists() { virsh_cmd dominfo "$VM_NAME" >/dev/null 2>&1; }

delete_existing_vm() {
  if vm_exists; then
    warn "VM '$VM_NAME' already exists. Replacing VM definition."
    virsh_cmd shutdown "$VM_NAME" >/dev/null 2>&1 || true
    sleep 2
    virsh_cmd destroy "$VM_NAME" >/dev/null 2>&1 || true
    virsh_cmd undefine "$VM_NAME" --nvram >/dev/null 2>&1 || \
      virsh_cmd undefine "$VM_NAME" >/dev/null 2>&1 || true
  fi
}

check_bridge_exists() {
  if [[ "$NET_MODE" == "bridge" ]]; then
    if ! ip link show "$BRIDGE_NAME" >/dev/null 2>&1; then
      die "Bridge '$BRIDGE_NAME' not found. Use NAT mode: --net default (recommended on Wi-Fi) or create a bridge on wired Ethernet."
    fi
  fi
}

virt_install_vm() {
  local netarg=()
  if [[ "$NET_MODE" == "bridge" ]]; then
    netarg=(--network "bridge=${BRIDGE_NAME},model=virtio")
  else
    netarg=(--network "network=${NET_NAME},model=virtio")
  fi

  local gfxarg=()
  if [[ "$GRAPHICS" == "none" ]]; then
    gfxarg=(--graphics none --console "$CONSOLE")
  else
    gfxarg=(--graphics "vnc,listen=${VNC_LISTEN}")
  fi

  info "Creating VM with virt-install..."
  info "RUN: virt-install --connect $LIBVIRT_URI (see log for full args)"
  sudo_wrap virt-install \
    --connect "$LIBVIRT_URI" \
    --name "$VM_NAME" \
    --memory "$RAM_MB" \
    --vcpus "$VCPUS" \
    --cpu host-passthrough \
    --os-variant "$OS_VARIANT" \
    --boot hd,menu=on \
    --disk "path=${USB_IMG},format=raw,bus=usb" \
    --disk "path=${ARRAY_IMG},format=${DISK_FMT},bus=sata" \
    --disk "path=${CACHE_IMG},format=${DISK_FMT},bus=sata" \
    "${netarg[@]}" \
    "${gfxarg[@]}" \
    --noautoconsole \
    --autostart 2>&1 | tee -a "$LOGFILE"

  ok "VM created."

  # Optional: passthrough a real USB device for stable Unraid flash identity/licensing.
  attach_host_usb
}

virt_install_vm_boot_from_host_usb() {
  local netarg=()
  if [[ "$NET_MODE" == "bridge" ]]; then
    netarg=(--network "bridge=${BRIDGE_NAME},model=virtio")
  else
    netarg=(--network "network=${NET_NAME},model=virtio")
  fi

  local gfxarg=()
  if [[ "$GRAPHICS" == "none" ]]; then
    gfxarg=(--graphics none --console "$CONSOLE")
  else
    gfxarg=(--graphics "vnc,listen=${VNC_LISTEN}")
  fi

  info "Creating VM (boot from physical USB passthrough)..."
  info "RUN: virt-install --connect $LIBVIRT_URI (see log for full args)"

  sudo_wrap virt-install \
    --connect "$LIBVIRT_URI" \
    --name "$VM_NAME" \
    --memory "$RAM_MB" \
    --vcpus "$VCPUS" \
    --cpu host-passthrough \
    --os-variant "$OS_VARIANT" \
    --boot menu=on \
    --controller type=usb,model=qemu-xhci \
    --disk "path=${ARRAY_IMG},format=${DISK_FMT},bus=sata" \
    --disk "path=${CACHE_IMG},format=${DISK_FMT},bus=sata" \
    "${netarg[@]}" \
    "${gfxarg[@]}" \
    --noautoconsole \
    --autostart 2>&1 | tee -a "$LOGFILE"

  ok "VM created."

  # Attach the real USB stick and reboot to ensure it's present at boot.
  attach_host_usb
  virsh_cmd reboot "$VM_NAME" >/dev/null 2>&1 || true
}

########################################
# Post info: VNC + IP hints
########################################
show_post_info() {
  info "VM status:"
  virsh_cmd domstate "$VM_NAME" 2>&1 | tee -a "$LOGFILE" || true

  if [[ "$GRAPHICS" != "none" ]]; then
    local disp=""
    disp="$(virsh_cmd vncdisplay "$VM_NAME" 2>/dev/null || true)"
    if [[ -n "$disp" ]]; then
      ok "VNC display for '$VM_NAME': $disp"
      info "If using a VNC viewer: display :0 => port 5900, :1 => port 5901, etc. Bound to ${VNC_LISTEN}."
    else
      warn "Could not determine VNC display yet. Try: virsh vncdisplay $VM_NAME"
    fi
  fi

  info "Waiting briefly for DHCP (15s) then attempting to detect IP..."
  sleep 15

  local ip=""
  ip="$(virsh_cmd domifaddr "$VM_NAME" 2>/dev/null | awk '/ipv4/ {print $4}' | head -n1 | cut -d/ -f1 || true)"

  if [[ -z "$ip" ]]; then
    warn "Could not detect guest IP via virsh domifaddr (common without qemu-guest-agent)."

    if [[ "$NET_MODE" == "network" && "$NET_NAME" == "default" ]]; then
      info "Try DHCP leases on libvirt default network:"
      virsh_cmd net-dhcp-leases default 2>&1 | tee -a "$LOGFILE" || true
      info "Unraid will usually be on 192.168.122.0/24 in NAT mode."
    else
      info "If bridged, check your router DHCP leases for a new device."
    fi
  else
    ok "Detected IP: $ip"
    info "Open Unraid Web UI: http://${ip}"
  fi

  info "Log file: $LOGFILE"
}

########################################
# Main
########################################
main() {
  if [[ $START_ONLY -eq 1 ]]; then
    info "--start set; starting existing VM only (no rebuild)."
    if ! vm_exists; then
      die "VM '$VM_NAME' not found in libvirt ($LIBVIRT_URI). Create it first (omit --start)."
    fi
    virsh_cmd start "$VM_NAME" >/dev/null 2>&1 || true
    show_post_info
    exit 0
  fi

  check_bridge_exists
  prepare_imagedir
  # If FLASH_DEV is set, we install Unraid to the physical stick and boot from passthrough.
  if [[ -n "${FLASH_DEV:-}" ]]; then
    install_unraid_to_physical_usb
  else
    create_usb_image
  fi
  create_disks

  if [[ $NO_INSTALL -eq 1 ]]; then
    ok "--no-install set; created images but did not create VM."
    info "Artifacts:"
    echo "  USB:   $USB_IMG" | tee -a "$LOGFILE" >&2
    echo "  Array: $ARRAY_IMG" | tee -a "$LOGFILE" >&2
    echo "  Cache: $CACHE_IMG" | tee -a "$LOGFILE" >&2
    exit 0
  fi

  delete_existing_vm
  if [[ -n "${FLASH_DEV:-}" ]]; then
    [[ -n "${HOST_USB_ID:-}" ]] || die "When using --flash-dev, also pass --host-usb VID:PID to attach the stick to the VM."
    virt_install_vm_boot_from_host_usb
  else
    virt_install_vm
  fi
  show_post_info
}

main
