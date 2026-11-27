#!/bin/bash
# Build the Paragon PR7-OS ISO. Runs as root in a Debian 13 container (CI: docker run --privileged debian:trixie),
# with the repository at /work and the generated tree at /work/build/root (pr7os.assets + pr7os.apps).
# PR7-OS goes into the ISO as its Debian packages (pr7os.packages), the same ones the update channel delivers: the
# packages land in /work/debs for the release.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends live-build debootstrap squashfs-tools xorriso mtools dosfstools \
    grub-common grub-efi-amd64-bin grub-pc-bin isolinux syslinux-common ca-certificates python3 python3-pil \
    python3-venv rsync cpio zstd xz-utils

# the packages (the venv at its final path, then the five .debs and the manifest)
bash /work/live/packages.sh

cd /work/live
lb clean --purge || true
rm -rf config/includes.chroot_after_packages config/bootloaders config/packages.chroot
./auto/config
mkdir -p config/packages.chroot
cp /work/debs/*.deb config/packages.chroot/
# the contents, not the folder: lb config makes config/bootloaders, and copying the folder into it puts live-build's
# files one level down, where nothing reads them (the first ISO booted with Debian's own menu)
mkdir -p config/bootloaders
cp -a /usr/share/live/build/bootloaders/. config/bootloaders/
python3 /work/tools/live_bootloader.py config/bootloaders /work/build/root
grep -q "Paragon PR7-OS" config/bootloaders/grub-pc/live-theme/theme.txt || { echo "the live boot menu isn't themed"; exit 1; }
ls config/bootloaders
lb build 2>&1 | tee build.log
ls -la ./*.iso
