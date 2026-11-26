#!/bin/bash
# Build the Paragon PR7-OS ISO. Runs as root in a Debian 13 container (CI: docker run --privileged debian:trixie),
# with the repository at /work and the generated image tree at /work/build/root (pr7os.assets + pr7os.apps).
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends live-build debootstrap squashfs-tools xorriso mtools dosfstools \
    grub-common grub-efi-amd64-bin grub-pc-bin isolinux syslinux-common ca-certificates python3 python3-pil rsync \
    cpio zstd xz-utils
cd /work/live
lb clean --purge || true
rm -rf config/includes.chroot_after_packages config/bootloaders
./auto/config
mkdir -p config/includes.chroot_after_packages
rsync -a /work/build/root/ config/includes.chroot_after_packages/
cp -a /usr/share/live/build/bootloaders config/bootloaders
python3 /work/tools/live_bootloader.py config/bootloaders /work/build/root
lb build 2>&1 | tee build.log
ls -la ./*.iso
