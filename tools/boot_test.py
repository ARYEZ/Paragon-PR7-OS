"""Boot the PR7-OS ISO in QEMU (CI, with KVM) and take screenshots of what a person sees.

    python tools/boot_test.py ISO OUT_DIR

Run 1, UEFI from the ISO (as on a PC): the boot menu, the splash, the desktop the live session logs into by itself.
Run 2, the ISO's own kernel with live-config's "noautologin": the login screen, then the live password ("live") typed
in and the desktop again. OUT_DIR gets boot_menu.png, splash.png, desktop.png, login.png, desktop_after_login.png,
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
                "-monitor", f"unix:{self.sock},server,nowait"]
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


def has_band(img: Image.Image) -> bool:
    """The boot menu's selected entry: a wide run of the family's red / orange across the middle of the screen."""
    small = img.resize((192, 108))
    hits = 0
    for y in range(30, 70):
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
    last = None
    try:
        while m.elapsed() < 420:
            img = m.shot()
            t = m.elapsed()
            frames.append((t, "UEFI", img))
            if menu is None and has_band(img):
                menu = img
                img.save(out / "boot_menu.png")
                result.append(f"boot menu at {t:.0f} s")
            elif menu is not None and splash is None and t > 20 and not has_band(img) and brightness(img) > 3:
                splash = img
                img.save(out / "splash.png")
                result.append(f"splash at {t:.0f} s")
            last = img
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
    append = ("boot=live components quiet splash username=paragon hostname=pr7os locales=en_US.UTF-8 "
              "keyboard-layouts=us live-config.noautologin console=ttyS0,115200 console=tty0")
    m = Machine(["-kernel", str(work / "vmlinuz"), "-initrd", str(work / "initrd.img"), "-append", append,
                 "-cdrom", iso], work, "login")
    login_ok = False
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
    finally:
        m.stop()
    for log in work.glob("*-serial.log"):
        shutil.copy(log, out / log.name)
    timeline(frames, out / "timeline.png")
    (out / "result.txt").write_text("\n".join(result) + "\n")
    print("\n".join(result))
    return 0 if desktop_ok and login_ok else 1


if __name__ == "__main__":
    raise SystemExit(main(*sys.argv[1:3]))
