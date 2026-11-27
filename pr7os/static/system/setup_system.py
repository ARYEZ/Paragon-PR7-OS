#!/usr/bin/env python3
"""What the paragon-pr7os-system package does once its dependencies are in place (its postinst).

    python3 setup_system.py configure

- The firewall (ufw), once: incoming connections blocked except SSH (port 22, used only if you install an SSH server)
  and KDE Connect (1714-1764); ufw's own rules already let mDNS (avahi: name.local, network printers) through.
  Switched on at once on a running system; in the ISO's build it's marked on and starts at boot. Done only the
  first time (a marker in /var/lib/paragon): if you change or switch off the firewall later, updates leave it alone.
- Remote desktop (KRdp, Plasma's RDP server: Windows' Remote Desktop Connection), once, on its own marker so installed
  systems get it too: port 3389 from home networks only (10/8, 172.16/12, 192.168/16), never from the internet, which
  RDP is a favourite target on. Nothing listens there until you set it up (Welcome's REMOTE DESKTOP).
- pr7os-flatpak-gl.service enabled: at every start, Flatpak's NVIDIA libraries for the running driver (Steam's games).
- Flathub as a Flatpak source (so Discover offers its apps, Steam included), every time: `--if-not-exists` makes
  that a no-op once it's there; without a network it's tried again on the next update.
Standard library only (Debian's python3). PR7OS_ROOT, PR7OS_UFW and PR7OS_FLATPAK point the tests elsewhere.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

FLATHUB = "https://dl.flathub.org/repo/flathub.flatpakrepo"
RULES = [
    ["default", "deny", "incoming"],
    ["default", "allow", "outgoing"],
    ["allow", "22/tcp", "comment", "SSH"],
    ["allow", "1714:1764/tcp", "comment", "KDE Connect"],
    ["allow", "1714:1764/udp", "comment", "KDE Connect"],
]


def root() -> Path:
    return Path(os.environ.get("PR7OS_ROOT", "/"))


def tool(env: str, name: str) -> str | None:
    return os.environ.get(env) or shutil.which(name)


def running_system() -> bool:
    """Booted with systemd (an installed or live system), not the ISO's build chroot."""
    return (root() / "run/systemd/system").is_dir()


def firewall() -> str:
    marker = root() / "var/lib/paragon/firewall-configured"
    if marker.exists():
        return "left as you set it"
    ufw = tool("PR7OS_UFW", "ufw")
    if not ufw:
        return "ufw isn't installed"
    for rule in RULES:
        if subprocess.run([ufw, *rule], stdout=subprocess.DEVNULL).returncode:
            return f"ufw {' '.join(rule)} failed; tried again on the next update"
    conf = root() / "etc/ufw/ufw.conf"
    if conf.exists():
        text = conf.read_text(encoding="utf-8")
        text = re.sub(r"^ENABLED=.*$", "ENABLED=yes", text, flags=re.M) if "ENABLED=" in text else text + "ENABLED=yes\n"
        conf.write_text(text, encoding="utf-8")
    if running_system():
        subprocess.run([ufw, "--force", "enable"], stdout=subprocess.DEVNULL)
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("PR7-OS set up the firewall once; it's yours to change now.\n", encoding="utf-8")
    return "on"


HOME_NETWORKS = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]


def remote_desktop() -> str:
    marker = root() / "var/lib/paragon/remote-desktop-allowed"
    if marker.exists():
        return "left as you set it"
    ufw = tool("PR7OS_UFW", "ufw")
    if not ufw:
        return "ufw isn't installed"
    for net in HOME_NETWORKS:
        rule = ["allow", "from", net, "to", "any", "port", "3389", "proto", "tcp", "comment", "Remote desktop (home)"]
        done = subprocess.run([ufw, *rule], capture_output=True, text=True)
        if done.returncode:
            why = (done.stderr or done.stdout).strip()[-200:]
            return f"ufw {' '.join(rule)} failed ({why}); tried again on the next update"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("PR7-OS allowed remote desktop from home networks once; it's yours to change now.\n",
                      encoding="utf-8")
    return "allowed from home networks"


def flathub() -> str:
    flatpak = tool("PR7OS_FLATPAK", "flatpak")
    if not flatpak:
        return "flatpak isn't installed"
    done = subprocess.run([flatpak, "remote-add", "--system", "--if-not-exists", "flathub", FLATHUB],
                          stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    return "added" if done.returncode == 0 else f"not added yet ({done.stderr.strip()[:200]})"


def gl_service() -> str:
    """pr7os-flatpak-gl.service on at every start (it does nothing without the NVIDIA driver)."""
    systemctl = tool("PR7OS_SYSTEMCTL", "systemctl")
    if not systemctl:
        return "systemctl isn't there"
    done = subprocess.run([systemctl, "enable", "pr7os-flatpak-gl.service"], stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL)
    return "on at every start" if done.returncode == 0 else "not switched on (tried again on the next update)"


def main(argv: list[str]) -> int:
    if not argv or argv[0] != "configure":
        print(__doc__)
        return 2
    print(f"PR7-OS firewall: {firewall()}")
    print(f"PR7-OS remote desktop: {remote_desktop()}")
    print(f"PR7-OS Flathub: {flathub()}")
    print(f"PR7-OS Flatpak NVIDIA libraries: {gl_service()}")
    return 0                                    # never fail the package: each step is retried on the next update


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
