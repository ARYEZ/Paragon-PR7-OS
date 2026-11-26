#!/usr/bin/env python3
"""Make the boot menu's fonts (GRUB .pf2 files) from Inter and write their real names into theme.txt.

    python3 grub-fonts.py THEME_DIR FONTS_DIR

GRUB finds a font by the exact name inside its .pf2 file, which grub-mkfont builds from the font's own tables; so
the names are read back from the files instead of guessed. Runs in the image's build (no Qt, Python's standard library).
"""
import struct
import subprocess
import sys
from pathlib import Path

# (font file, the name theme.txt asks for, sizes, family name given to grub-mkfont). grub-mkfont names SemiBold
# "Inter Regular" like the regular weight unless it gets a family name of its own; -n gives it one.
WANT = [("Inter-Regular.ttf", "Inter Regular", (12, 14, 16, 18), None),
        ("Inter-SemiBold.ttf", "Inter SemiBold", (12, 18), "Inter SemiBold")]


def pf2_name(path: Path) -> str:
    data = path.read_bytes()
    i = 0
    while i + 8 <= len(data):
        tag, size = data[i:i + 4], struct.unpack(">I", data[i + 4:i + 8])[0]
        if tag == b"NAME":
            return data[i + 8:i + 8 + size].rstrip(b"\0").decode("utf-8")
        if tag == b"DATA":
            break
        i += 8 + size
    raise ValueError(f"{path}: no NAME in the font")


def main(theme_dir: str, fonts_dir: str) -> int:
    theme, fonts = Path(theme_dir), Path(fonts_dir)
    names = {}
    for ttf, label, sizes, family in WANT:
        for size in sizes:
            out = theme / f"{label.lower().replace(' ', '-')}-{size}.pf2"
            cmd = ["grub-mkfont", "-s", str(size), "-o", str(out)] + (["-n", family] if family else []) + [str(fonts / ttf)]
            done = subprocess.run(cmd, capture_output=True, text=True)    # quiet: Inter's font features warn
            if done.returncode:
                sys.stderr.write(done.stderr)
                raise SystemExit(f"grub-mkfont failed for {ttf} {size}")
            names[f"{label} {size}"] = pf2_name(out)
    if len(set(names.values())) != len(names):
        raise SystemExit(f"two fonts share a name: {names}")
    txt = theme / "theme.txt"
    text = txt.read_text(encoding="utf-8")
    for wanted, real in names.items():
        text = text.replace(f'"{wanted}"', f'"{real}"')
    txt.write_text(text, encoding="utf-8")
    for wanted, real in names.items():
        print(f"{wanted} -> {real}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(*sys.argv[1:3]))
