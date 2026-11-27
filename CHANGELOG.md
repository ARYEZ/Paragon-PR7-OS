# Changelog

## 0.2.1

What a desktop needs beyond Plasma, in a new package (paragon-pr7os-system) that the updater brings to installed
machines too: open PR7-OS Update, or wait for the notification.

- **Names on the network**: every PR7-OS machine answers as `<its name>.local` (avahi), so `ssh you@outpost.local`
  works from Windows without looking up the address. The SSH server itself stays your choice
  (`sudo apt install openssh-server`).
- **Printing**: CUPS and Plasma's Printers page; network printers are found by themselves.
- **Security fixes by themselves**: Debian's security and stable fixes install quietly once a day (unattended-upgrades,
  Debian's own rules: no new versions). PR7-OS's own updates wait for it if it's busy.
- **Command-line basics**: curl, wget, git, unzip, htop.
- **Firewall on**: incoming connections blocked except SSH (port 22) and KDE Connect; names on the network and printers
  still work. Set up once: change it in System Settings > Firewall and updates leave it as you set it.
- **Flatpak with Flathub in Discover**: apps Debian doesn't carry, one click away.
- **Games**: Vulkan drivers and GameMode; "Get Steam" in the menu installs Steam from Flathub (its own 32-bit libraries,
  nothing added to Debian) and starts it afterwards. NVIDIA cards need NVIDIA's driver from Debian's non-free section.
- **Paragon account picture**: the gradient 7 instead of Debian's swirl on the lock screen, for accounts that still had
  Debian's (a picture you chose is never touched).
- From the next version on, updates are published without a new ISO (they come out in minutes instead of an hour);
  x.y.0 versions still come with one, booted and checked.

## 0.2.0

**Updates come to you.** Once a day PR7-OS checks for a new release and says so; "PR7-OS Update" (in the menu, or
from the notification) shows what's new, asks for your password once and installs it. Only what changed is
downloaded, and every package is checked against the release's checksums first. Debian's own updates keep coming
through Discover as before.

- **Already installed PR7-OS 0.1.x?** Get the updater once, in a terminal (Konsole or PR7-TM):

      python3 -c "import urllib.request; urllib.request.urlretrieve('https://github.com/ARYEZ/Paragon-PR7-OS/releases/latest/download/paragon-pr7os-updates.deb', '/tmp/pr7os-updates.deb')"
      sudo apt install /tmp/pr7os-updates.deb
      pr7os-update

  then UPDATE, and log out and back in. From then on, updates arrive by themselves. (PR7-OS has no wget: Python is
  always there. Over SSH, with no screen for the window, run `sudo /usr/libexec/paragon/pr7os-update-helper` instead
  of `pr7os-update`.)
- The lock screen in the login screen's look, for real this time: 0.1.1's showed KDE's built-in emergency lock screen on
  KDE's purple wallpaper (Plasma's password block imports an old QtQuick version that rejected the gradient). Its
  wallpaper is now Paragon's too.
- PR7-OS is now built from its own Debian packages (paragon-pr7os-look, -apps, -python, -updates): the ISO and the
  updates install the same files. When Debian updates Plasma, the look is applied to the new version by itself; if a
  future Plasma isn't recognised, the lock screen keeps Plasma's own design rather than breaking.

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
