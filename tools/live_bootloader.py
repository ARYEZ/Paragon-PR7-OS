#!/usr/bin/env python3
"""Theme the live ISO's own boot menus (run in the build container, after live-build's defaults are copied in).

    python3 tools/live_bootloader.py LIVE_CONFIG_BOOTLOADERS ROOT

GRUB (UEFI, and BIOS where live-build uses it): the installed system's boot menu theme, the menu entries named for
PR7-OS, a 5 s timeout. isolinux (BIOS): the family's colours instead of Debian's blue, the boot menu picture.
ROOT is the generated image tree (python -m pr7os.assets ROOT). Standard library + Pillow (python3-pil) only.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path


def theme_grub(grub: Path, root: Path) -> None:
    src = root / "usr/share/grub/themes/paragon"
    live_theme = grub / "live-theme"
    live_theme.mkdir(parents=True, exist_ok=True)
    for f in src.iterdir():
        if f.suffix in (".png", ".txt"):
            shutil.copy2(f, live_theme / f.name)
    subprocess.run([sys.executable, str(root / "usr/share/paragon/grub-fonts.py"), str(live_theme),
                    str(root / "usr/share/fonts/truetype/paragon-inter")], check=True)
    shutil.copy2(src / "background.png", grub / "splash.png")
    fonts = "\n".join(f"loadfont /boot/grub/live-theme/{f.name}" for f in sorted(live_theme.glob("*.pf2")))
    (grub / "theme.cfg").write_text(
        "# Paragon PR7-OS boot menu\nset color_normal=light-gray/black\nset color_highlight=white/black\n"
        f"insmod png\n{fonts}\nset theme=/boot/grub/live-theme/theme.txt\n", encoding="utf-8")
    for cfg in grub.glob("*.cfg"):
        text = cfg.read_text(encoding="utf-8")
        new = text.replace("Live system", "Paragon PR7-OS live").replace("Debian GNU/Linux", "Paragon PR7-OS")
        if cfg.name == "config.cfg" and "set timeout" not in new:
            new += "\nset timeout=5\n"
        if new != text:
            cfg.write_text(new, encoding="utf-8")


def theme_isolinux(iso: Path, root: Path) -> None:
    from PIL import Image
    img = Image.open(root / "usr/share/grub/themes/paragon/background.png").convert("RGB")
    # isolinux's menu is 640x480: the mark's part of the boot menu picture, scaled
    w, h = img.size
    img.crop(((w - h * 4 // 3) // 2, 0, (w + h * 4 // 3) // 2, h)).resize((640, 480)).save(iso / "splash.png")
    for svg in iso.glob("splash.svg*"):
        svg.unlink()
    menu = iso / "stdmenu.cfg"
    if menu.exists():
        text = re.sub(r"^menu color .*\n?", "", menu.read_text(encoding="utf-8"), flags=re.M)
        text += ("menu color screen * #ffe8e8ea #00000000 none\n"
                 "menu color border * #00000000 #00000000 none\n"
                 "menu color title * #ffe8e8ea #00000000 none\n"
                 "menu color unsel * #ffc9c5c8 #00000000 none\n"
                 "menu color sel * #ffffffff #ffe8303a none\n"
                 "menu color hotsel * #ffffffff #ffe8303a none\n"
                 "menu color hotkey * #ffff7a1a #00000000 none\n"
                 "menu color tabmsg * #ff8a8a92 #00000000 none\n"
                 "menu color timeout_msg * #ff8a8a92 #00000000 none\n"
                 "menu color timeout * #ffff7a1a #00000000 none\n"
                 "menu color help * #ff8a8a92 #00000000 none\n")
        menu.write_text(text, encoding="utf-8")
    for cfg in iso.glob("*.cfg"):
        text = cfg.read_text(encoding="utf-8")
        new = text.replace("Live system", "Paragon PR7-OS live")
        if new != text:
            cfg.write_text(new, encoding="utf-8")


def main(bootloaders: str, root: str) -> int:
    b, r = Path(bootloaders), Path(root)
    if (b / "grub-pc").is_dir():
        theme_grub(b / "grub-pc", r)
    if (b / "isolinux").is_dir():
        theme_isolinux(b / "isolinux", r)
    print("live boot menus themed:", ", ".join(d.name for d in b.iterdir() if d.is_dir()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(*sys.argv[1:3]))
