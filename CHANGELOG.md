# Changelog

## 0.6.0

A new ISO with 0.5.1 (DRIVERS) and 0.5.2 (an encrypted disk by default), and a boot test that now also checks:
- **the encrypted disk's question**: asked from the initramfs as cryptsetup asks it, typed into, the dots shown and the
  answer passed on;
- **Welcome, pressed for real** (`pr7os-welcome --press KEY` clicks a key as the mouse does): FONT -> Inter (your
  account's fonts change and an app started afterwards no longer gets Bebas Neue), BACK UP TO A DRIVE (PR7-BK opens
  the home backup), SSH -> TURN ON (Plasma's password dialog, the password, Debian's SSH server installed and running),
  DRIVERS (this machine's graphics card read through lspci);
- **sleep and wake**: the PC suspends (S3), wakes to the lock screen, unlocks, and Print still opens PR7-Q, the PR7-IS
  service still runs and apps still start.

## 0.5.2

- **An encrypted disk by default** (the installer, from the next ISO): "Encrypt system" is ticked from the start, with
  LUKS2 (Argon2id: far harder to guess than LUKS1's), a small /boot that isn't encrypted and the system in one
  encrypted partition. The password is asked once, by the boot splash, in the family look; nothing on the plain /boot
  can unlock the disk (Calamares writes no key file there). The ISO now carries cryptsetup-initramfs, which unlocks it.
- **The splash can ask**: its words (an encrypted disk's question, the dots as you type, boot messages) need Plymouth's
  text plugin and the font inside the initramfs: paragon-pr7os-look now depends on plymouth-label and copies Bebas
  Neue and fontconfig's settings in. Until now the question would have been invisible.
- The ISO's boot test asks that question from the initramfs, as cryptsetup does, types into it, and checks the dots
  showed and the answer arrived.
- 0.5.1's notes corrected: the ISO already has the common firmware; DRIVERS adds the rest.

## 0.5.1

- **DRIVERS in Welcome**: firmware for any PC (Wi-Fi, Bluetooth, sound, graphics, and the processor's microcode with
  its security fixes; the ISO has the common ones, this adds Atheros, Broadcom and MediaTek Wi-Fi, Bluetooth and sound), and on a PC with an NVIDIA card the NVIDIA driver: the package Debian's
  own nvidia-detect names for that card (a card Debian 13 has no driver for is said plainly, nothing is installed),
  built for your kernel, with modesetting and video memory kept over sleep (Plasma on Wayland needs both). With Secure
  Boot on, the driver's signing key is queued and Welcome shows a one-time password: at the next start, a blue screen
  asks for it once (Enroll MOK, Continue, Yes, the password, Reboot). Turns on Debian's contrib, non-free and
  non-free-firmware areas first (only on Debian's own sources).
- CI installs the packages into a clean Debian 13 and runs the drivers helper there for an RTX 4070: the real
  nvidia-detect chooses, apt resolves every firmware and driver package.

## 0.5.0

A new ISO with everything since 0.4.0, booted and checked in CI like every x.y.0:
- Go back to the release before (PR7-OS Update), with a Timeshift snapshot before every update (0.4.1).
- Welcome's FONT (Bebas Neue or Inter for your account) and PR7-AR (startup items) and PR7-UN (uninstaller) on
  PR7-OS (0.4.2).
- Welcome's BACKUPS: your home folder every night to a drive, with PR7-BK 0.2.0 (0.4.3).
The boot test now also starts PR7-AR and PR7-UN in the session.

## 0.4.3

- **Backups out of the box**: Welcome has a BACKUPS card. BACK UP TO A DRIVE opens PR7-BK (0.2.0) with your home folder
  already chosen, every night at 03:00, caches and the Trash left out; you pick the drive and the password. The
  schedule is a systemd user timer, so a backup missed while the PC was off runs when it's next on.

## 0.4.2

- **PR7-AR Startup** and **PR7-UN Uninstaller** join PR7-OS (both now run on Linux): every Paragon app is here but PR7-U
  (it installs Windows setups; PR7-OS Update does that job here). PR7-AR shows what starts with the system and with you
  (autostart entries, systemd services and timers, cron, modules) and switches each off its own way; PR7-UN uninstalls
  apt and Flatpak programs, asks apt first what a removal would take with it, and cleans up the leftovers.
- **A font switch in Paragon Welcome**: Bebas Neue (PR7-OS's) or Inter, for your account: Plasma's fonts, every Paragon
  app, Welcome and PR7-OS Update. Sign out and back in to see it everywhere. The login screen and the boot stay in Bebas
  Neue (they're every account's).

## 0.4.1

- **Undo an update.** PR7-OS Update has GO BACK: it installs the release before the one you have again (its own
  packages, checked against its manifest, as an update is), and the newer one isn't offered by the daily check until
  something newer still comes out. Over SSH: `sudo /usr/libexec/paragon/pr7os-update-helper previous`.
- **A snapshot before every update.** Each update (and each going back) starts with a Timeshift snapshot of the system
  (your home folder is left out: that's PR7-BK's job). Snapshots share what didn't change, so after the first one
  they're small; PR7-OS keeps its three newest and never touches snapshots of your own. Timeshift (in the menu) restores
  one if anything else ever goes wrong. No snapshot is taken with less than 5 GB free; the update goes ahead anyway.

## 0.4.0

- **Bebas Neue everywhere**: Plasma's fonts, the login and lock screens, the boot splash and boot menu, the installer,
  Welcome, the updater and every Paragon app (through its launcher; the Windows apps keep Inter). The login password
  field keeps Inter, terminals and monospaced text keep their fixed-width font. Bebas Neue has capitals only and one
  weight.
- **PR7-IS Search** (Ctrl+Alt+Space; its index service starts at sign-in, kept up to date by Linux's change notices),
  **PR7-LN Launcher** (Alt+Space; Plasma's KRunner keeps Alt+F2 and the Search key) and **PR7-CB Clipboard** (Ctrl+`;
  Plasma's Klipper feeds its history; choose a clip, then Ctrl+V) join PR7-OS: every Paragon app that works on Linux is
  here now.
- **One finish for the whole desktop**: OBSIDIAN / AURORA in any Paragon app switches Plasma's global theme too, and
  picking a Paragon theme in System Settings switches the apps.
- **Paragon Welcome** at sign-in (until you switch it off): the finish, the keys, SSH on / off, printers, Steam, updates.
- **Print belongs to PR7-Q**: Spectacle (still installed, still in the menu) no longer takes the Print keys.
- Links between the apps work on PR7-OS (Edit in PR7-W, Open in PR7-E ...): the apps find each other's launchers.
- The boot test checks more for real: no Spectacle on Print, Alt+Space opens PR7-LN, PR7-IS's service runs, and every
  app's window is photographed in an awake session (a locked or blank screen no longer counts).

## 0.3.0

A new ISO with everything since 0.2.0 (the update channel, names on the network, printing, security updates, the
firewall, Flatpak and Flathub, games, the Paragon account picture, PR7-Q Screenshots), checked in a real Plasma
session before it was published:
- the boot test now presses Print and sees PR7-Q answer through Plasma's shortcut, and starts every Paragon app in the
  live session and photographs its window (`apps.png` in this release);
- installed machines get the same through PR7-OS Update (nothing new to install since 0.2.3 apart from the version).

## 0.2.3

- **PR7-Q Screenshots joins PR7-OS** (PR7-Q 0.4.0, which now runs on Plasma's Wayland desktop): Print captures a
  region, Shift+Print the last region, Alt+Print a window (Plasma's dialog: pick the window), Ctrl+Print the full
  screen; then PR7-Q's after-capture menu and editor, as on Windows. It starts at sign-in in the panel's tray (switch
  that off in its Preferences). The first capture may ask once whether PR7-Q may take screenshots: allow it.
- PR7-PM 0.2.4 (from the previous update): copied passwords stay out of Plasma's clipboard history; locking the screen
  locks PR7-PM.

## 0.2.2

- **0.2.1's additions now actually install.** The updater only installed the four packages it knew by name, so the
  new paragon-pr7os-system (names on the network, printing, security updates, the firewall, Flatpak, Vulkan) was
  skipped. It now installs every PR7-OS package the release lists. Already on 0.2.1? Run the update twice this once
  (`sudo /usr/libexec/paragon/pr7os-update-helper` over SSH, or UPDATE in PR7-OS Update): the first run brings the
  fixed updater, the second the rest.
- When an update includes the updater itself, its new copy now looks again in the same run, so a fix like this one
  won't need a second run in future.

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
