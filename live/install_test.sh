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
