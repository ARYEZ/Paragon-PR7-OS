# Changelog

## 0.13.1

- No changes for installed PCs (the same packages as 0.12.1). The version moves past 0.13.0 so that later pushes are
  package-only releases: an x.y.0 version builds an ISO on every push, and ISOs are made only when asked for.

## 0.13.0

A new ISO with the login screen's input driver (0.12.1), remote desktop through xrdp, the network made the PC's on
TURN ON, and awake while connected. Its boot test checks the live user signs in at the login screen again, and the RDP
login, Welcome's keys, sleep / wake and every app as before.

## 0.12.1

- **The login screen's keyboard and mouse**: the login screen (SDDM) runs on an X server, and that server had no input
  driver ("No input driver specified, ignoring this device" for the keyboard, the mouse and the tablet): the login
  screen ignored them, so nobody could sign in at the PC itself. 0.12.0's boot test found it (its saved X server log).
  The system package now depends on xserver-xorg-input-libinput, and the ISO carries it.

## 0.12.0

A new ISO with remote desktop through xrdp, the network made the PC's on TURN ON, and awake while connected (0.10.1,
0.11.1). 0.11.0's boot test proved remote desktop (TURN ON from Welcome, then a real RDP client logged in as a user of
its own and got a Plasma session), but the live user's own login never happened: the password typed at the login
screen didn't reach it (no attempt in SDDM's log), as if the key presses were lost. The test now checks the login took
(SDDM's LoginSucceeded or a logind session), tries once more if it didn't, and keeps SDDM's and the X server's logs.

## 0.11.1

- **Remote desktop works signed out**: Plasma keeps a network for the account that set it up (the Wi-Fi password in its
  wallet), so a signed-out PC dropped off the network and Windows couldn't reach it. Welcome's REMOTE DESKTOP TURN ON
  now makes each active network the PC's (every account, and the login screen): a Wi-Fi password kept in your wallet is
  stored for the system instead (NetworkManager's own root-only file), and the card says which networks changed.
- **Awake while you're connected**: pr7os-remote-awake.service keeps the PC from sleeping while anyone is connected over
  SSH (port 22) or remote desktop (3389), and lets go when the last connection closes. Typing in an SSH session or a
  remote desktop doesn't count as using the PC, so Plasma put it to sleep mid-session.

## 0.11.0

A new ISO with remote desktop through xrdp (0.10.1). Its boot test turns REMOTE DESKTOP on from Welcome (Plasma's
password dialog), then a real RDP client (FreeRDP, on the test machine, through the virtual network: a home network to
the firewall) logs in to it as a user of its own, and a Plasma session must start for that user.

## 0.10.1

- **Remote desktop through xrdp**: Plasma's KRdp sent a video stream (H.264) that both of Microsoft's clients refused
  (Remote Desktop Connection: protocol error 0xd06; Windows App: "Invalid packet format"), at 4K and at 1080p alike.
  PR7-OS now uses xrdp, the remote desktop server Windows' own client works with: Welcome's REMOTE DESKTOP card turns
  it on and off (your password once); Windows logs in with your PR7-OS user name and password and gets a Plasma
  session of its own, so sign out on the PC first (one account can't run two desktops at once). Turning it on stops
  KRdp for your account (both want port 3389). The firewall still lets 3389 in from home networks only.
- Welcome's `--press` takes "CARD/KEY" (SSH and REMOTE DESKTOP both have TURN ON).

## 0.10.0

A new ISO with everything since 0.5.0 (DRIVERS, an encrypted disk by default, remote desktop from Windows, Steam's
NVIDIA libraries, updates that always go forward, pr7os-update over SSH). 0.9.0's boot test found why the encrypted
disk's question showed in text: the startup image had everything (Plymouth running, the theme, its plugins, Bebas
Neue, the graphics device), but the test's own serial console (console=ttyS0, for its log) makes Plymouth fall back to
text unless the kernel line also says `plymouth.ignore-serial-consoles`. A PC has no serial console; the test now says
so. The question being asked and its answer arriving are required for the ISO; its themed look is reported, not
required (the owner's choice).

## 0.9.0

A new ISO. 0.8.0's boot test passed everything (remote desktop's rules included) except the encrypted disk's
question in the theme: it was asked, typed into and answered, but in Plymouth's text mode. This ISO's boot test
records what the splash has at that moment (theme, plugins, fonts, graphics devices) to find out why.

## 0.8.1

0.8.0's packages, without waiting for its ISO (its boot test passed everything but one: see 0.9.0):
- `plymouth.use-simpledrm` on the kernel line (installed systems' GRUB);
- pr7os-remote-desktop-firewall.service: remote desktop's three home-network rules at start-up (0.8.0's boot test:
  all three in, the port from nowhere else).

## 0.8.0

A new ISO (0.7.0's boot test found two more things, now fixed; everything else it checked passed: SSH from Welcome,
sleep and wake with the lock screen, Print, PR7-IS and the apps after waking):
- **The encrypted disk's question in the theme**: Plymouth ignores the firmware's framebuffer (simpledrm) unless the
  kernel line says `plymouth.use-simpledrm`, and waits for a real graphics driver, which isn't in the initramfs
  (NVIDIA's included): so it asked in plain text. PR7-OS's kernel line (installed systems' GRUB, the ISO's menu) now
  has it: the splash, and the question with its dots, from the first moment.
- **Remote desktop's firewall rules at start-up**: built into the ISO, only the first of the three home-network rules
  went in. pr7os-remote-desktop-firewall.service adds them at start-up on the running system, until all three are in
  (then never again); ufw's own message goes to its log.

## 0.7.1

- **pr7os-update over SSH**: with no screen (an SSH session) it no longer tries to open its window (Qt aborted: "could
  not connect to display"); it runs the update in the terminal instead: your password, then each step.
  `pr7os-update --back` goes back to the release before, the window's GO BACK.

## 0.7.0

A new ISO with everything since 0.5.0: DRIVERS (0.5.1), an encrypted disk by default with the splash asking for its
password (0.5.2), remote desktop from Windows (0.6.1), Steam's NVIDIA libraries (0.6.2), updates that always go
forward (0.6.3). Its boot test checks the encrypted disk's question, Welcome's keys (FONT, BACKUPS, SSH, REMOTE
DESKTOP, DRIVERS) and sleep / wake. 0.6.0's run showed the machine, not PR7-OS, in the way, so the login run now boots:
- with UEFI firmware, as a real PC: its framebuffer is there from the first moment, so Plymouth draws the unlock
  question in the theme (under BIOS it asked in text until the graphics driver loaded: the question and the five
  stars showed, the dots in the family orange didn't);
- with QEMU's standard graphics: the virtio graphics driver doesn't survive sleep (KWin: "Pageflip timed out! This is
  a bug in the virtio_gpu kernel driver"), so the screen stayed dark after waking, though the lock screen asked for
  and took the password;
- and Welcome is started as Plasma starts an app (the user's own service manager): started from the guest agent it
  belonged to a system service, polkit found no password agent for it, and SSH's TURN ON got no password dialog.

## 0.6.3

- **Updates always go forward**: PR7-OS Update took GitHub's "latest" release, which is only the last one published;
  a release with an ISO takes an hour to build and could be published after a newer one, and every PC would then have
  been "updated" back to it. The updater now takes the highest version that carries packages, an update never
  installs an older version than the one you have (going back is GO BACK's job alone), and CI marks a release "latest"
  only when nothing newer is out.

## 0.6.2

- **Steam's games on the NVIDIA driver**: Flatpak apps (Steam from Flathub) don't use the system's NVIDIA libraries but a
  Flathub extension built for the exact driver version; without it games fall back to slow software rendering.
  pr7os-flatpak-gl.service runs at every start and, once per driver version, has Flatpak install the matching one:
  after the restart that follows DRIVERS, and again whenever Debian updates the driver. It does nothing without the
  NVIDIA driver running or without Flatpak runtimes, and tries again at the next start when offline.

## 0.6.1

- **Remote desktop from Windows**: Plasma's own RDP server (KRdp) is installed, and Welcome has a REMOTE DESKTOP card:
  SET UP opens its settings (choose a user name and password, switch it on), and the card then says what to type in
  Windows' Remote Desktop Connection (this PC's name.local, and its home-network address). Nothing to install on
  Windows. The firewall lets port 3389 in from home networks only (10.x, 172.16-31.x, 192.168.x), never from the
  internet, where RDP is a favourite target; added once on its own, so installed PCs get it too and keep your changes.
- CI checks KRdp installs in a clean Debian 13; the boot test presses SET UP and checks the firewall's three rules.

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
