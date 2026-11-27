# Changelog

## 0.1.1

- The lock screen (Meta+L, or after a while idle) in the login screen's look: the large clock and the date in capitals,
  the gradient ring around your picture, the dark password field with the family gradient under it, the gradient
  unlock key. Plasma's own lock screen does the unlocking; only its look changes.
- No kernel warnings flashing past during boot (such as Intel SGX's "disabled by BIOS", which is harmless): the boot
  options add loglevel=3, which still shows real errors. An installed 0.1.0 gets it by adding loglevel=3 to
  GRUB_CMDLINE_LINUX_DEFAULT in /etc/default/grub and running sudo update-grub.

## 0.1.0

The first Paragon PR7-OS: **Debian 13 with KDE Plasma in the Paragon look**, as a live ISO you can try from a USB stick
and install with "Install Paragon PR7-OS" on its desktop.

- The look from power-on: the PR7-OS boot menu, the boot splash, the login screen, the desktop (OBSIDIAN wallpaper,
  the dark floating panel with the 7 start button, Paragon window title bars), Inter everywhere, the family's colours
  only. System Settings > Global Theme switches between Paragon Obsidian and Paragon Aurora.
- 19 Paragon apps in the menu: Files (PR7-E), Text (PR7-W), Terminal (PR7-TM), Media (PR7-M), Images (PR7-P),
  PDF (PR7-R), Archives (PR7-Z), Transfers (PR7-F), Passwords (PR7-PM), Video (PR7-HB), Tags (PR7-L), Backups (PR7-BK),
  Sync (PR7-FS), Disk usage (PR7-DU), Hardware (PR7-HW), System (PR7-SM), Database (PR7-DB), Hex (PR7-HX),
  Compare (PR7-WM). Folders, images, PDFs, media, text and archives open in them.
- Live session: user "paragon", password "live".
- Not yet: PR7-CB, PR7-LN, PR7-Q and PR7-IS (they need Linux work for global keys, Wayland screenshots and search);
  the lock screen is still KDE's own design.

## 0.0.1

- First build: Debian 13 with KDE Plasma in the Paragon look (OBSIDIAN and AURORA global themes, window decoration,
  wallpaper, login screen, boot splash, boot menu, installer branding) and 19 Paragon apps. Development build: CI builds
  and boot-tests the ISO, nothing is published yet.
