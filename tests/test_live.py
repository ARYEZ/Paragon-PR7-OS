"""The ISO's build: live-build's configuration, the hooks, the live boot menus, the boot test's eyes."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / "live"
sys.path.insert(0, str(ROOT / "tools"))


def test_hooks_and_scripts_are_executable_shell():
    for f in list((LIVE / "config/hooks/normal").glob("*.hook.*")) + [LIVE / "build.sh"] + list((LIVE / "auto").iterdir()):
        assert os.access(f, os.X_OK), f.name
        assert f.read_text().startswith("#!/bin/"), f.name
        assert subprocess.run(["bash", "-n", str(f)]).returncode == 0, f.name      # syntax


def test_package_list():
    names = [l.strip() for l in (LIVE / "config/package-lists/paragon.list.chroot").read_text().splitlines()
             if l.strip() and not l.startswith("#")]
    assert len(names) == len(set(names))
    for must in ("kde-plasma-desktop", "sddm", "plymouth", "calamares", "python3-venv", "7zip", "handbrake-cli",
                 "restic", "grub-efi-amd64", "shim-signed", "libxcb-cursor0", "libpulse0"):
        assert must in names, must


def test_live_boot_parameters():
    cfg = (LIVE / "auto/config").read_text()
    assert "--distribution trixie" in cfg and "username=paragon" in cfg and "quiet splash" in cfg
    assert "--debian-installer none" in cfg


def test_hooks_use_what_the_image_has():
    look = (LIVE / "config/hooks/normal/0200-paragon-look.hook.chroot").read_text()
    assert "setup_look.py configure --strict" in look
    setup = (ROOT / "pr7os/static/setup_look.py").read_text()
    assert 'SHARE / "plasma-colors"' in setup and '"plymouth-set-default-theme", "paragon"' in setup
    assert 'SHARE / "grub-fonts.py"' in setup and "lockscreen.py" in setup
    system = (LIVE / "config/hooks/normal/0300-paragon-system.hook.chroot").read_text()
    assert "branding: paragon" in system and "update-initramfs" in system


@pytest.mark.skipif(not shutil.which("grub-mkfont"), reason="grub-mkfont (grub-common) isn't installed")
def test_live_boot_menus_are_themed(built, tmp_path):
    import live_bootloader
    root, _ = built
    b = tmp_path / "bootloaders"
    (b / "grub-pc").mkdir(parents=True)
    (b / "isolinux").mkdir()
    (b / "grub-pc/config.cfg").write_text("set default=0\n")
    (b / "grub-pc/grub.cfg").write_text('menuentry "Live system (amd64)" {\n}\n')
    (b / "isolinux/stdmenu.cfg").write_text("menu color sel * #ffffffff #76a1d0ff *\n")
    (b / "isolinux/splash.svg.in").write_text("<svg/>")
    live_bootloader.main(str(b), str(root))
    theme = (b / "grub-pc/live-theme/theme.txt").read_text()
    fonts = sorted(p.name for p in (b / "grub-pc/live-theme").glob("*.pf2"))
    assert len(fonts) == 6 and "Inter SemiBold" in theme                    # SemiBold kept a name of its own
    assert all(f"loadfont /boot/grub/live-theme/{f}" in (b / "grub-pc/theme.cfg").read_text() for f in fonts)
    assert "Paragon PR7-OS live" in (b / "grub-pc/grub.cfg").read_text()
    assert "set timeout=5" in (b / "grub-pc/config.cfg").read_text()
    menu = (b / "isolinux/stdmenu.cfg").read_text()
    assert "76a1d0" not in menu and "#ffe8303a" in menu                      # Debian's blue out, the family red in
    assert (b / "isolinux/splash.png").exists() and not (b / "isolinux/splash.svg.in").exists()


def test_the_boot_test_knows_the_boot_menu():
    pytest.importorskip("PIL")
    from PIL import Image
    import boot_test
    mock = ROOT / "docs/mockup"
    assert boot_test.has_band(Image.open(mock / "boot_menu.png").convert("RGB"))
    assert not boot_test.has_band(Image.open(mock / "boot_splash.png").convert("RGB"))
    assert not boot_test.has_band(Image.open(mock / "login.png").convert("RGB"))


def test_first_boot_findings_stay_fixed():
    build = (LIVE / "build.sh").read_text()
    assert "cp -a /usr/share/live/build/bootloaders/. config/bootloaders/" in build    # contents, not the folder
    assert "the live boot menu isn't themed" in build
    system = (LIVE / "config/hooks/normal/0300-paragon-system.hook.chroot").read_text()
    assert "apt-get purge -y plasma-welcome" in system and "Install Paragon PR7-OS" in system


def test_second_boot_findings_stay_fixed(built):
    root, _ = built
    theme = (root / "usr/share/grub/themes/paragon/theme.txt").read_text()
    menu = theme[theme.index("+ boot_menu"):theme.index("}")]
    assert "top = 35%" in menu and "left = 29%" in menu           # proportions: the picture scales with the screen
    assert "top = 73%" in theme and "top = 78%" in theme             # the hint and the countdown don't overlap
    assert "/sddm/faces/" in (root / "usr/share/sddm/themes/paragon/Main.qml").read_text()
    menus = (LIVE / "config/hooks/normal/0400-paragon-menus.hook.binary").read_text()
    assert "Paragon PR7-OS (safe graphics)" in menus


def test_the_boot_test_tells_screens_apart():
    """Locked = far from the desktop (> 12); unlocked = the desktop again (< 8)."""
    pytest.importorskip("PIL")
    from PIL import Image
    import boot_test
    mock = ROOT / "docs/mockup"
    desk = Image.open(mock / "desktop_obsidian.png").convert("RGB")
    login = Image.open(mock / "login.png").convert("RGB")
    assert boot_test.difference(desk, desk) == 0
    assert boot_test.difference(desk, login) > 12
