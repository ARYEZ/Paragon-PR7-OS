"""Boot the PR7-OS ISO in QEMU (CI, with KVM) and take screenshots of what a person sees.

    python tools/boot_test.py ISO OUT_DIR

Run 1, UEFI from the ISO (as on a PC): the boot menu, the splash, the desktop the live session logs into by itself.
Run 2, the ISO's own kernel with live-config's "noautologin": the login screen, then the live password ("live") typed
in and the desktop again, then Meta+L and unlocking with the password, then Print (PR7-Q, started at sign-in, through
Plasma's shortcut) and every Paragon app started in the real Plasma session (apps.png: each one's window). OUT_DIR gets boot_menu.png, splash.png,
desktop.png, login.png, desktop_after_login.png, lock_screen.png, unlocked.png,
timeline.png (every frame, small) and result.txt; the exit code is 1 when a desktop never appeared.
"""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from PIL import Image, ImageStat

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pr7os import apps as family_apps  # noqa: E402

OVMF_CODE = ["/usr/share/OVMF/OVMF_CODE_4M.fd", "/usr/share/OVMF/OVMF_CODE.fd", "/usr/share/ovmf/OVMF.fd"]
OVMF_VARS = ["/usr/share/OVMF/OVMF_VARS_4M.fd", "/usr/share/OVMF/OVMF_VARS.fd"]


def first(paths):
    return next((p for p in paths if os.path.exists(p)), None)


class Machine:
    def __init__(self, args: list[str], work: Path, name: str):
        self.work = work
        self.sock = work / f"{name}.sock"
        kvm = os.access("/dev/kvm", os.R_OK | os.W_OK)
        base = ["qemu-system-x86_64", "-machine", "q35", "-m", "6144", "-smp", "4",
                *(["-enable-kvm", "-cpu", "host"] if kvm else ["-accel", "tcg"]),
                "-vga", "virtio", "-display", "none", "-serial", f"file:{work / (name + '-serial.log')}",
                "-device", "qemu-xhci", "-device", "usb-tablet",
                "-netdev", "user,id=n", "-device", "virtio-net-pci,netdev=n",
                "-monitor", f"unix:{self.sock},server,nowait",
                # the QEMU guest agent (qemu-guest-agent is in the image): commands inside the machine, e.g. the journal
                "-device", "virtio-serial", "-chardev", f"socket,path={work / (name + '-qga.sock')},server=on,wait=off,id=qga0",
                "-device", "virtserialport,chardev=qga0,name=org.qemu.guest_agent.0"]
        self.qga_sock = work / (name + "-qga.sock")
        self.proc = subprocess.Popen(base + args)
        for _ in range(100):
            if self.sock.exists():
                break
            time.sleep(0.1)
        self.started = time.monotonic()

    def hmp(self, command: str) -> str:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.connect(str(self.sock))
            s.settimeout(10)
            out = b""
            while not out.endswith(b"(qemu) "):
                out += s.recv(4096)
            s.sendall(command.encode() + b"\n")
            out = b""
            while not out.endswith(b"(qemu) "):
                chunk = s.recv(4096)
                if not chunk:
                    break
                out += chunk
            return out.decode(errors="replace")

    def guest(self, path: str, args: list[str], timeout: float = 60) -> str:
        """Run a command inside the machine through the guest agent; its output ("" when the agent can't)."""
        import base64
        import json

        def call(s, msg):
            s.sendall(json.dumps(msg).encode() + b"\n")
            buf = b""
            while b"\n" not in buf:
                buf += s.recv(65536)
            return json.loads(buf.split(b"\n")[0])
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                s.connect(str(self.qga_sock))
                s.settimeout(timeout)
                call(s, {"execute": "guest-sync", "arguments": {"id": 7}})
                pid = call(s, {"execute": "guest-exec", "arguments": {"path": path, "arg": args,
                                                                      "capture-output": True}})["return"]["pid"]
                end = time.time() + timeout
                while time.time() < end:
                    st = call(s, {"execute": "guest-exec-status", "arguments": {"pid": pid}})["return"]
                    if st.get("exited"):
                        out = base64.b64decode(st.get("out-data", "")).decode(errors="replace")
                        err = base64.b64decode(st.get("err-data", "")).decode(errors="replace")
                        return out + err
                    time.sleep(1)
        except (OSError, KeyError, ValueError) as e:
            return f"(guest agent: {e})"
        return "(guest agent: timed out)"

    def shot(self) -> Image.Image:
        ppm = self.work / "frame.ppm"
        ppm.unlink(missing_ok=True)
        self.hmp(f"screendump {ppm}")
        for _ in range(50):
            if ppm.exists() and ppm.stat().st_size > 0:
                break
            time.sleep(0.1)
        time.sleep(0.2)
        img = Image.open(ppm)
        img.load()
        return img.convert("RGB")

    def keys(self, text: str):
        for ch in text:
            self.hmp(f"sendkey {ch}")
            time.sleep(0.08)

    def key(self, name: str):
        self.hmp(f"sendkey {name}")

    def elapsed(self) -> float:
        return time.monotonic() - self.started

    def stop(self):
        try:
            self.hmp("quit")
        except OSError:
            pass
        try:
            self.proc.wait(10)
        except subprocess.TimeoutExpired:
            self.proc.kill()


def brightness(img: Image.Image) -> float:
    return sum(ImageStat.Stat(img.convert("L")).mean)


def difference(a: Image.Image, b: Image.Image) -> float:
    """How different two screens are: the mean of every pixel's difference (0 = the same picture)."""
    from PIL import ImageChops
    small = (320, 200)
    return sum(ImageStat.Stat(ImageChops.difference(a.resize(small), b.resize(small))).mean) / 3


def has_band(img: Image.Image) -> bool:
    """The boot menu's selected entry: a wide run of the family's red / orange across the middle of the screen."""
    small = img.resize((192, 108))
    hits = 0
    for y in range(20, 92):
        run = sum(1 for x in range(40, 152) if (lambda p: p[0] > 190 and p[1] < 140 and p[2] < 90)(small.getpixel((x, y))))
        hits = max(hits, run)
    return hits > 60


def timeline(frames: list[tuple[float, str, Image.Image]], out: Path):
    cols, w, h = 6, 320, 180
    rows = (len(frames) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w, rows * (h + 18)), (6, 4, 7))
    from PIL import ImageDraw
    d = ImageDraw.Draw(sheet)
    for i, (t, run, img) in enumerate(frames):
        x, y = (i % cols) * w, (i // cols) * (h + 18)
        sheet.paste(img.resize((w, h)), (x, y))
        d.text((x + 4, y + h + 3), f"{run} {t:5.0f} s", fill=(232, 232, 234))
    sheet.save(out)


def contact_sheet(tiles: list[tuple[str, bool, Image.Image]], out: Path):
    """Every app's screenshot, small, with its name: started (white) or not (red)."""
    from PIL import ImageDraw
    cols, w, h = 4, 480, 300
    rows = max(1, (len(tiles) + cols - 1) // cols)
    sheet = Image.new("RGB", (cols * w, rows * (h + 22)), (6, 4, 7))
    d = ImageDraw.Draw(sheet)
    for i, (name, ok, img) in enumerate(tiles):
        x, y = (i % cols) * w, (i // cols) * (h + 22)
        sheet.paste(img.resize((w, h)), (x, y))
        d.text((x + 6, y + h + 4), f"{name}: {'started' if ok else 'DID NOT START'}",
               fill=(232, 232, 234) if ok else (255, 70, 70))
    sheet.save(out)


def in_session(m: Machine, command: str) -> str:
    """A command as the live user inside their Plasma session (Wayland, their session bus), not waited for."""
    env = ("XDG_RUNTIME_DIR=/run/user/$U WAYLAND_DISPLAY=wayland-0 DISPLAY=:0 "
           "DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$U/bus XDG_SESSION_TYPE=wayland XDG_CURRENT_DESKTOP=KDE")
    return m.guest("/bin/sh", ["-c", f"U=$(id -u paragon); runuser -u paragon -- env {env} setsid sh -c "
                                     f"'{command}' > /dev/null 2>&1 < /dev/null &"])


def main(iso: str, out_dir: str) -> int:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="pr7os-boot-"))
    frames: list[tuple[float, str, Image.Image]] = []
    result = []

    # ---- run 1: UEFI from the ISO
    code, vars_src = first(OVMF_CODE), first(OVMF_VARS)
    uefi = []
    if code:
        uefi = ["-drive", f"if=pflash,format=raw,readonly=on,file={code}"]
        if vars_src and "OVMF.fd" not in code:
            shutil.copy(vars_src, work / "vars.fd")
            uefi += ["-drive", f"if=pflash,format=raw,file={work / 'vars.fd'}"]
    m = Machine(uefi + ["-cdrom", iso, "-boot", "d"], work, "uefi")
    menu = splash = None
    menu_since = None
    last = None
    try:
        while m.elapsed() < 240:
            img = m.shot()
            t = m.elapsed()
            frames.append((t, "UEFI", img))
            if menu is not None and menu_since and t - menu_since > 15 and has_band(img):
                m.key("ret")                     # a menu with no timeout must not stall the test
                menu_since = None
            if menu is None and has_band(img):
                menu = img
                menu_since = t
                img.save(out / "boot_menu.png")
                result.append(f"boot menu at {t:.0f} s")
            elif menu is not None and splash is None and t > 20 and not has_band(img) and brightness(img) > 3:
                splash = img
                img.save(out / "splash.png")
                result.append(f"splash at {t:.0f} s")
            if brightness(img) > 20:
                last = img           # the last lit frame: an idle desktop locks and blanks after 5 minutes
            time.sleep(4 if t < 60 else 15)
    finally:
        m.stop()
    if last is not None:
        last.save(out / "desktop.png")
    desktop_ok = last is not None and brightness(last) > 20
    result.append(f"desktop: {'shown' if desktop_ok else 'NOT SHOWN'} (brightness {brightness(last) if last else 0:.0f})")

    # ---- run 2: straight to the login screen (the ISO's kernel, live-config's noautologin)
    for f in ("vmlinuz", "initrd.img"):
        subprocess.run(["xorriso", "-osirrox", "on", "-indev", iso, "-extract", f"/live/{f}", str(work / f)],
                       check=True, capture_output=True)
    append = ("boot=live components quiet splash loglevel=3 username=paragon user-fullname=Paragon hostname=pr7os locales=en_US.UTF-8 "
              "keyboard-layouts=us live-config.noautologin console=ttyS0,115200 console=tty0")
    m = Machine(["-kernel", str(work / "vmlinuz"), "-initrd", str(work / "initrd.img"), "-append", append,
                 "-cdrom", iso], work, "login")
    login_ok = lock_shown = unlocked = packaged = False
    firewall_on = flathub_listed = avahi_on = False
    print_ok = apps_ok = launcher_ok = is_running = False
    try:
        while m.elapsed() < 240:
            img = m.shot()
            frames.append((m.elapsed(), "LOGIN", img))
            time.sleep(15)
        img.save(out / "login.png")
        login_ok = brightness(img) > 20
        result.append(f"login screen: {'shown' if login_ok else 'NOT SHOWN'}")
        m.keys("live")
        m.key("ret")
        time.sleep(150)
        img = m.shot()
        frames.append((m.elapsed(), "LOGIN", img))
        img.save(out / "desktop_after_login.png")
        desktop = img
        # lock (Meta+L), see the lock screen, unlock with the password: a lock screen that can't unlock fails here
        m.key("meta_l-l")
        time.sleep(10)
        m.key("shift")                    # wakes the lock screen's controls
        time.sleep(3)
        locked = m.shot()
        frames.append((m.elapsed(), "LOCK", locked))
        locked.save(out / "lock_screen.png")
        m.keys("live")
        m.key("ret")
        time.sleep(15)
        back = m.shot()
        frames.append((m.elapsed(), "LOCK", back))
        back.save(out / "unlocked.png")
        lock_shown = difference(locked, desktop) > 12
        unlocked = difference(back, desktop) < 8
        pkgs = m.guest("/usr/bin/dpkg-query", ["-W", "-f", "${Package} ${Version}\n", "paragon-pr7os-*"])
        (out / "packages.txt").write_text(pkgs)
        packaged = all(f"paragon-pr7os-{p} " in pkgs for p in ("look", "apps", "python", "updates", "system"))
        result.append(f"PR7-OS packages: {'all five' if packaged else 'MISSING'}")
        system = m.guest("/bin/sh", ["-c",
            "ufw status verbose; echo @@PR7@@; flatpak remotes --system; echo @@PR7@@; "
            "systemctl is-active avahi-daemon cups; echo @@PR7@@; for u in /home/*; do ls -la \"$u\"/.face* 2>&1; done; ls -la /var/lib/AccountsService/icons "
            "2>&1; cat /var/lib/AccountsService/users/* 2>&1"])
        (out / "system.txt").write_text(system)
        firewall_on = "Status: active" in system and "22/tcp" in system
        flathub_listed = "\nflathub" in system or system.startswith("flathub")
        parts = system.split("@@PR7@@")                   # ufw draws its table with ------ lines
        avahi_on = len(parts) > 2 and parts[2].split()[:1] == ["active"]
        result.append(f"firewall: {'on' if firewall_on else 'OFF'}; Flathub: {'listed' if flathub_listed else 'MISSING'}; "
                      f"avahi: {'running' if avahi_on else 'NOT RUNNING'}")
        # PR7-Q: started at sign-in (its autostart entry); Print reaches it through Plasma's shortcut (kglobalaccel)
        q_running = "pr7q" in m.guest("/bin/sh", ["-c", "pgrep -af 'python -m pr7q' || true"])
        before = m.shot()
        m.key("print")
        time.sleep(8)
        after = m.shot()
        frames.append((m.elapsed(), "PRINT", after))
        after.save(out / "print.png")
        spectacle = m.guest("/bin/sh", ["-c", "pgrep -a spectacle || true"]).strip()
        print_ok = q_running and difference(after, before) > 4 and not spectacle   # PR7-Q answered, not Spectacle
        m.key("esc")
        time.sleep(2)
        m.key("esc")
        time.sleep(3)
        result.append(f"PR7-Q: {'running' if q_running else 'NOT RUNNING'}; Print: "
                      + ("SPECTACLE ANSWERED" if spectacle else "answered" if print_ok else "NOTHING HAPPENED"))
        m.guest("/bin/sh", ["-c", "pkill spectacle || true"])
        # PR7-LN: running from autostart; Alt+Space (a Plasma shortcut, taken from KRunner) opens its launcher
        ln_running = "pr7ln" in m.guest("/bin/sh", ["-c", "pgrep -af 'python -m pr7ln' || true"])
        before = m.shot()
        m.key("alt-spc")
        time.sleep(5)
        after = m.shot()
        frames.append((m.elapsed(), "ALT+SPACE", after))
        after.save(out / "launcher.png")
        launcher_ok = ln_running and difference(after, before) > 3
        m.key("esc")
        time.sleep(2)
        is_running = "pr7is" in m.guest("/bin/sh", ["-c", "pgrep -af 'python -m pr7is --index-service' || true"])
        result.append(f"PR7-LN: {'running' if ln_running else 'NOT RUNNING'}; Alt+Space: "
                      f"{'opened it' if launcher_ok else 'NOTHING HAPPENED'}; PR7-IS service: "
                      f"{'running' if is_running else 'NOT RUNNING'}")
        # every app in the real Plasma session: still running after a while, and a window on the screen
        base = m.shot()
        tiles, failed, notes = [], [], []
        for app in family_apps.APPS:
            if app.autostart == "--tray":          # already running in the tray (PR7-Q, PR7-LN): checked by their keys
                continue
            log = f"/tmp/{app.command}.log"
            m.key("shift")                         # a key now and then: an idle session locks after 5 minutes
            in_session(m, f"exec {app.command} > {log} 2>&1")
            time.sleep(14)
            m.key("shift")
            shot = m.shot()
            alive = app.package in m.guest("/bin/sh", ["-c", f"pgrep -af 'python -m {app.package}$' || true"])
            # its window on the screen: not the desktop as it was, not the lock screen, not a blanked display (near 0;
            # the apps' own OBSIDIAN windows are dark, ~10)
            ok = alive and difference(shot, base) > 3 and difference(shot, locked) > 8 and brightness(shot) > 3
            tiles.append((f"PR7-{app.letter} {app.name}", ok, shot))
            if not ok:
                failed.append(app.letter)
                notes.append(f"== PR7-{app.letter} (alive: {alive})\n" + m.guest("/bin/sh", ["-c", f"tail -n 30 {log}"]))
            m.guest("/bin/sh", ["-c", f"pkill -f 'python -m {app.package}$'; sleep 2; "
                                      f"pkill -9 -f 'python -m {app.package}$' || true"])
            time.sleep(3)
        contact_sheet(tiles, out / "apps.png")
        (out / "apps.txt").write_text("\n".join(notes) or "every app started\n")
        apps_ok = bool(tiles) and not failed
        result.append(f"apps: {len(tiles) - len(failed)} of {len(tiles)} started"
                      + (f" (not: {', '.join('PR7-' + f for f in failed)})" if failed else ""))
        (out / "journal.txt").write_text(m.guest("/usr/bin/journalctl", ["-b", "--no-pager", "-o", "short-monotonic"], 120))
        (out / "lockscreen-files.txt").write_text(m.guest("/bin/sh", ["-c",
            "ls -la /usr/share/plasma/shells/org.kde.plasma.desktop/contents/lockscreen/; "
            "dpkg-divert --list | grep paragon; cat /usr/share/plasma/shells/org.kde.plasma.desktop/contents/lockscreen/MainBlock.qml; "
            "find / -xdev -name UserDelegate.qml* 2>/dev/null; cat ~paragon/.config/kscreenlockerrc /etc/xdg/kscreenlockerrc 2>&1"]))
        result.append(f"lock screen: {'shown' if lock_shown else 'NOT SHOWN'}; "
                      f"unlocked: {'yes' if unlocked else 'NO'}")
    finally:
        m.stop()
    for log in work.glob("*-serial.log"):
        shutil.copy(log, out / log.name)
    timeline(frames, out / "timeline.png")
    (out / "result.txt").write_text("\n".join(result) + "\n")
    print("\n".join(result))
    return 0 if (desktop_ok and login_ok and lock_shown and unlocked and packaged and firewall_on
                  and flathub_listed and avahi_on and print_ok and apps_ok and launcher_ok and is_running) else 1


if __name__ == "__main__":
    raise SystemExit(main(*sys.argv[1:3]))
