#!/bin/bash
# Every release: the five packages installed into a clean Debian 13 with apt, as the updater installs them (their
# dependencies from Debian, Plasma included), then what they set up is checked. This is what catches a dependency
# Debian 13 doesn't have or a file another package owns, without building the ISO.
#   docker run --rm -v "$PWD:/work" debian:trixie bash /work/live/install_test.sh
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq /work/debs/*.deb > /tmp/install.log 2>&1 || { tail -n 80 /tmp/install.log; exit 1; }
tail -n 5 /tmp/install.log
fail() { echo "FAILED: $*"; exit 1; }
for pkg in look apps python updates system; do
    dpkg-query -W -f '${db:Status-Status}' "paragon-pr7os-$pkg" | grep -qx installed || fail "paragon-pr7os-$pkg isn't installed"
done
echo "five packages installed"
# the look's postinst ran: the system's name, the lock screen, new accounts' picture
grep -q '^NAME="Paragon PR7-OS"' /usr/lib/os-release || fail "os-release isn't Paragon's"
grep -q ParagonClock /usr/share/plasma/shells/org.kde.plasma.desktop/contents/lockscreen/LockScreenUi.qml \
    || fail "the lock screen wasn't restyled"
[ "$(readlink /etc/skel/.face.icon)" = /usr/share/paragon/face.png ] || fail "new accounts don't get Paragon's picture"
! ls -a /etc/skel | grep -q paragon-orig || fail "Debian's set-aside pictures are in /etc/skel (new accounts copy them)"
[ -d /usr/share/plasma/desktoptheme/paragon ] || fail "no Paragon Plasma style"
echo "look set up"
# the system package's postinst: the firewall marked on, Flathub a source
grep -q '^ENABLED=yes' /etc/ufw/ufw.conf || fail "the firewall isn't marked on"
flatpak remotes --system | grep -q '^flathub' || fail "Flathub isn't a Flatpak source"
echo "firewall and Flathub set up"
# every app imports in the environment the python package brought
for app in /opt/paragon/apps/paragon-pr7-*; do
    pkg=$(basename "$app" | sed 's/paragon-pr7-/pr7/')
    PYTHONPATH="$app" /opt/paragon/venv/bin/python -c "import $pkg" || fail "$pkg doesn't import"
done
echo "every app imports"
# Welcome's DRIVERS, for real in Debian 13 except the card (this container has none: an lspci stand-in reports an RTX
# 4070) and the big installs (apt-get -s: every package name and dependency resolved, nothing downloaded): Debian's
# areas turned on in its own sources file, the real nvidia-detect asked about the card, firmware and driver resolved.
mkdir -p /tmp/fakebin
cat > /tmp/fakebin/lspci <<'PCI'
#!/bin/sh
printf '01:00.0 VGA compatible controller [0300]: NVIDIA Corporation AD104 [GeForce RTX 4070] [10de:2786] (rev a1)\n\tKernel driver in use: nouveau\n'
PCI
chmod +x /tmp/fakebin/lspci
PATH="/tmp/fakebin:$PATH" PR7OS_SIMULATE=1 /usr/libexec/paragon/pr7os-drivers-helper install > /tmp/drivers.log 2>&1 \
    || { tail -n 60 /tmp/drivers.log; fail "the drivers helper stopped"; }
grep -E '^(STEP|DONE|ERROR)' /tmp/drivers.log
grep -q 'non-free-firmware' /etc/apt/sources.list.d/debian.sources || fail "Debian's non-free areas weren't turned on"
tail -n 1 /tmp/drivers.log | grep -qx 'DONE nvidia-driver (simulated)' || fail "nvidia-driver wasn't the driver chosen"
grep -q '^Inst firmware-iwlwifi' /tmp/drivers.log || fail "the Wi-Fi firmware wasn't going to be installed"
grep -q '^Inst nvidia-kernel-dkms' /tmp/drivers.log || fail "the driver's kernel module wasn't going to be built"
echo "drivers helper: firmware and nvidia-driver resolve in Debian 13"
# Welcome's REMOTE DESKTOP: the firewall's 3389 rules are home-only
# A rule for some networks only makes ufw test the kernel's firewall first (initcaps); this unprivileged container may
# not touch it ("Permission denied (you must be root)"), a real PC and the ISO's build can. That one reason is
# accepted here (the setup tries again on the next update, and the ISO's boot test reads the three rules in a real
# PR7-OS); anything else fails.
if [ -f /var/lib/paragon/remote-desktop-allowed ]; then
    echo "remote desktop: firewall rule added"
elif grep 'PR7-OS remote desktop' /tmp/install.log | grep -q 'initcaps'; then
    echo "remote desktop: firewall rule left for a real kernel (this container may not test it)"
else
    grep 'PR7-OS ' /tmp/install.log || true
    fail "the remote desktop firewall rule wasn't added"
fi
# Remote desktop through xrdp: the server, its X server and Plasma's X11 session (xrdp's sessions are X11), and the
# session xrdp starts (Debian's Xsession runs x-session-manager)
for pkg in xrdp xorgxrdp kwin-x11 xserver-xorg-input-libinput; do
    dpkg-query -W -f '${db:Status-Status}' "$pkg" | grep -qx installed || fail "$pkg isn't installed"
done
command -v startplasma-x11 >/dev/null || fail "Plasma's X11 session (startplasma-x11) isn't there"
echo "xrdp's session manager: $(readlink -f /etc/alternatives/x-session-manager)"
echo "remote desktop: xrdp, xorgxrdp, Plasma on X11 installed"
# Steam's NVIDIA libraries: the service is on at every start (it does nothing here: no NVIDIA driver running)
[ -L /etc/systemd/system/multi-user.target.wants/pr7os-remote-awake.service ] || fail "pr7os-remote-awake isn't enabled"
[ -L /etc/systemd/system/multi-user.target.wants/pr7os-remote-desktop-firewall.service ] \
    || fail "pr7os-remote-desktop-firewall isn't enabled"
systemctl is-enabled pr7os-flatpak-gl.service 2>/dev/null | grep -qx enabled \
    || [ -L /etc/systemd/system/multi-user.target.wants/pr7os-flatpak-gl.service ] || fail "pr7os-flatpak-gl isn't enabled"
/usr/libexec/paragon/pr7os-flatpak-gl | grep -q "no NVIDIA driver running" || fail "pr7os-flatpak-gl didn't run"
echo "Flatpak NVIDIA service: enabled, runs"
