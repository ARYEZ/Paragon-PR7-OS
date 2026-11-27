#!/usr/bin/python3
"""The installer's disk settings for PR7-OS (run by the ISO's hook 0300 on Debian's own partition.conf).

Debian's Calamares can already encrypt the disk ("Encrypt system"); these settings make it PR7-OS's way:
- the box is ticked from the start (preCheckEncryption): an encrypted disk unless you untick it;
- LUKS2 (luksGeneration), whose key derivation (Argon2id) resists password guessing far better than LUKS1's;
- a small /boot that isn't encrypted (partitionLayout, noEncrypt) and the system in one encrypted partition: GRUB
  then reads /boot without a password, and the initramfs asks for it once, through the boot splash, in the family
  look (GRUB could only ask in plain text, and only for LUKS1). Calamares then writes no key file into /boot
  (luksbootkeyfile skips it when /boot isn't encrypted), so nothing on the plain partition unlocks the disk.

Only these keys change; everything else stays as Debian set it."""
import re
import sys

SETTINGS = {"enableLuksAutomatedPartitioning": "true", "preCheckEncryption": "true", "luksGeneration": "luks2"}
COMMENT = "# Paragon PR7-OS: an encrypted disk by default, unlocked through the boot splash"
LAYOUT = """partitionLayout:
    - name: "boot"
      filesystem: "ext4"
      noEncrypt: true
      mountPoint: "/boot"
      size: 1G
    - name: "root"
      filesystem: "unknown"
      mountPoint: "/"
      size: 100%
"""


def patch(text: str) -> str:
    out, in_layout = [], False
    for line in text.splitlines():
        if in_layout:
            if not line.strip() or line[:1] in (" ", "\t", "-"):
                continue                                  # the old layout's entries
            in_layout = False
        if re.match(r"^partitionLayout\s*:", line):
            in_layout = True
            continue
        m = re.match(r"^(\w+)\s*:", line)
        if m and m.group(1) in SETTINGS:
            continue
        if line == COMMENT:
            continue
        out.append(line)
    body = "\n".join(out).rstrip("\n")
    ours = "\n".join(f"{k}: {v}" for k, v in SETTINGS.items())
    return f"{body}\n\n{COMMENT}\n{ours}\n{LAYOUT}"


def main(argv: list[str]) -> int:
    path = argv[0] if argv else "/etc/calamares/modules/partition.conf"
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except FileNotFoundError:
        text = ""
    new = patch(text)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(new)
    print(new)                                            # into the ISO build's log
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
