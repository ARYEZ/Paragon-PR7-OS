# Paragon PR7-OS: notes for Claude

**Paragon PR7-OS** is the owner's own desktop: **Debian 13 (trixie) with KDE Plasma** in the Paragon family look
(OBSIDIAN and AURORA, the family's colours only, Inter, the PR7 mark), with the Paragon apps that work on Linux. It's
a live ISO with the Calamares installer. The owner writes Python; explain the why of changes.

## How it's built

- **Everything visual is generated** by `pr7os/assets.py` from the family theme (`pr7os/theme.py`, PR7-IS's, and
  `widgets.py` with the PR7-OS mark: PR7's geometry, O = PR7-Q's Q without the tail, S = PR7-IS's) into a tree laid out
  like the system (`python -m pr7os.assets ROOT`): Plasma colour schemes (every role filled: KDE's blues and greens never
  show), an Aurorae window decoration (gradient thread on the active window, gradient close key), the wallpaper (light
  = AURORA, `images_dark` = OBSIDIAN), two global themes (`org.paragon.pr7os.obsidian|aurora`: defaults, the floating
  panel's `layout.js`, KSplash), the panel colours (`/usr/share/paragon/plasma-colors`, put into a copy of Breeze Dark
  by a hook: the panel and launcher stay dark in both finishes, as menus and keys do), SDDM, Plymouth, GRUB, Calamares
  branding, `/etc/xdg` defaults (OBSIDIAN). Hand-written parts (QML, Plymouth script, Calamares, grub-fonts.py) are in
  `pr7os/static/` and carry no colours of their own beyond the family's.
- **The apps** (`pr7os/apps.py`): 20 apps copied from their repositories (checked out next to this one, or
  `PR7OS_FAMILY`) to `/opt/paragon/apps/<repo>/`, one venv `/opt/paragon/venv` built in the image from the merged
  requirements (PySide6 as Essentials + Addons + Pdf: no web engine), launchers `/usr/bin/pr7-<x>`, menu entries,
  icons, `/etc/xdg/mimeapps.list` (folders PR7-E, images PR7-P, PDF PR7-R, media PR7-M, text PR7-W, archives PR7-Z).
  Left out for now (`LEFT_OUT`): AR, UN, U (Windows-only), CB, LN, IS (global keys, Wayland, NTFS). `App.actions`
  (id, name, args, shortcut) become menu actions; with a shortcut the entry is also copied to /usr/share/kglobalaccel
  (Plasma registers X-KDE-Shortcuts from there: PR7-Q owns Print); `App.autostart` -> /etc/xdg/autostart. Other apps'
  keys are taken in `setup_look.py`: Spectacle's kglobalaccel entry diverted away (`spectacle_keys_off`), KRunner's
  diverted and replaced by a copy without Alt+Space (`krunner_keys`; an /etc/xdg/kglobalshortcutsrc default alone
  didn't move it: 0.4.0's first boot test). The look's trigger on /usr/share/kglobalaccel re-applies both.
- **The ISO**: `live/` is a live-build configuration (`auto/config`, `package-lists/paragon.list.chroot`, hooks:
  0100 apps venv + every app imports, 0200 look (Plasma style, GRUB fonts, Plymouth), 0300 system (os-release diverted,
  ID stays debian; Calamares branding; initramfs)). The generated tree goes in as `includes.chroot_after_packages`.
  `live/build.sh` runs in `debian:trixie` (CI: docker --privileged); `tools/live_bootloader.py` themes the ISO's own
  menus (GRUB's live-theme with our fonts, isolinux colours). GRUB finds fonts by their name inside the .pf2:
  `grub-fonts.py` reads them back (SemiBold needs `-n`, or it's named "Inter Regular").
- **Packages and updates** (0.2.0): `pr7os/packages.py` builds paragon-pr7os-{look,apps,updates} (all) and -python
  (amd64; version "1+<hash of its dists>") plus `pr7os-update.json` (versions, SHA-256, sizes); `live/build.sh` builds
  the venv at /opt/paragon/venv in the container, the packages, and live-build installs them (config/packages.chroot).
  The look's postinst runs `static/setup_look.py configure` (idempotent; dpkg triggers on Plasma's lock screen, Breeze
  components and Breeze Dark re-run it); the ISO's hook 0200 re-runs it `--strict`. The updater (`static/updater/`):
  `pr7os-update [--check]` (systemd user timer daily, notify-send actions), `window.py` (PySide6), the root helper
  (pkexec, no arguments, URLs built from the repo + tag, file names checked) installs with apt-get --force-confold.
  Release assets: the packages, the manifest, `paragon-pr7os-updates.deb` (fixed name for the one-time command).
  Tests: tests/test_packages.py, tests/test_updater.py (a stand-in GitHub); CI `update-test` (debian:trixie: old
  updater installed with apt, updated by the helper).
- **paragon-pr7os-system** (0.2.1): what a desktop needs beyond Plasma as Depends (avahi + libnss-mdns, cups +
  print-manager, unattended-upgrades (`etc/apt/apt.conf.d/52paragon-auto-upgrades`), curl / wget / git / unzip / htop,
  ufw + plasma-firewall, flatpak + Discover's backend, mesa-vulkan-drivers, gamemode) and `static/system/setup_system.py`
  (postinst: the firewall once, marker /var/lib/paragon/firewall-configured; Flathub `--if-not-exists`); `pr7os-steam`
  opens Discover on Steam (Flathub) or starts it. Depends names must exist in Debian 13 (the ISO build fails otherwise:
  0.2.0's `kscreenlocker`). The look's `faces()` gives accounts with no picture / Debian's (byte-identical to a file in
  desktop-base or pixmaps) `face.png`; never a chosen one. /etc/skel/.face(.icon) belong to desktop-base: diverted
  (`skel_faces`), never shipped (dpkg refuses another package's file: 0.2.1's first build). The helper's apt-get waits for the lock (DPkg::Lock::Timeout). The updater installs any `paragon-pr7os-<word>` the
  manifest lists (`PACKAGE`; 0.2.1's fixed list skipped -system: test_packages checks every built package passes), and
  after updating paragon-pr7os-updates re-runs its new copy once (PR7OS_UPDATE_RERUN / _DONE). Go back (0.4.1): the
  helper's only accepted word `previous` installs `pr7os_update.previous(current)` (newest older release with a
  manifest, never 0.0.x; no re-run); the window's GO BACK skips the newer version. Every run first takes a Timeshift
  snapshot (`snapshot`: config written once, system only, PR7-OS's three newest kept, skipped below 5 GB or without
  Timeshift: never fatal); PR7OS_TIMESHIFT / _CONFIG / PR7OS_SNAPSHOT_ROOT in tests. CI's update-test also goes back.
- **The lock screen** is Plasma's shell package (org.kde.plasma.desktop/contents/lockscreen), not the global theme,
  and its QML unlocks the session: `pr7os/static/lockscreen.py` (run by hook 0200) only restyles it with anchored edits
  (ParagonClock instead of Breeze's Clock; the password field's / unlock key's backgrounds; UserDelegate's gradient
  ring; MainBlock.qml's `import QtQuick 2.2` raised to 2.15, or Gradient.orientation fails the file), checks all
  of them before writing, diverts the files. `tests/data/plasma-6.3.6` holds Plasma's own files for
  the tests; on a Plasma upgrade, refresh them and re-check the anchors. The boot test locks (Meta+L) and unlocks.
- **CI** (`.github/workflows/build.yml`): tests, update-test, then **packages** on every push: `live/packages.sh`
  (venv + the five .debs, debian:trixie) and `live/install_test.sh` (all five installed with apt into a clean Debian 13,
  then the look / firewall / Flathub / every app import checked); a new non-x.y.0 `__version__` is published from there
  (packages + manifest, no ISO; the notes link the newest release that has one). The **iso** job runs only for x.y.0
  versions, `v*` tags or Run workflow with "iso": `live/build.sh` (calls packages.sh), `tools/boot_test.py` boots it in
  QEMU/KVM (UEFI: boot menu, splash, desktop; direct kernel with `live-config.noautologin`: login screen, password
  "live", desktop, lock / unlock, firewall, Flathub, avahi, Print -> PR7-Q (running from autostart, the screen changes),
  every app started in the session with `in_session` (runuser + the user's Wayland / bus env; alive and a window:
  `apps.png`, `apps.txt` with failures' logs)) and pushes the screenshots to the **ci-boot-screens** branch
  (CI only; fetch it to look: release downloads are blocked from the session). An x.y.0 is published by the iso job
  with its ISO (split into parts over 2 GB); a hand-started ISO of a released version is added to that release.
  **0.0.x versions never publish**.
- This session can't reach deb.debian.org: the ISO is only built in CI. Locally: the assets, the login screen
  (`tools/login_preview.py` renders Main.qml with stand-ins for SDDM), the apps starting, the live menus' theming.

## The look (family rules)

- Colours: the family's only (hues ~318 -> 0 -> 42 deg, pearl and onyx greys); tests check every colour in every
  generated file and sample the pictures. **Font: Bebas Neue everywhere on PR7-OS** (the owner's choice, 0.3.1:
  capitals only, one weight; `assets.UI_FONT`, Plasma's fonts a size up), except the login password field and GRUB's
  command line (Inter) and terminals (fixed-width). The apps keep asking for Inter: PR7-OS packages them without it and
  their launchers set FONTCONFIG_FILE=/etc/paragon/fonts-apps.conf (`apps.FONTS_APPS`: Inter rejected, aliased to
  Bebas Neue). Mock-up: `tools/mockup.py` (docs/mockup).

## Rules

- Behaviour questions: do what Debian and KDE Plasma do; the look is the family's.
- Tests: `python -m pytest` (offscreen). Never the real settings or system.
- Releases: bump `__version__` in `pr7os/__init__.py` and add a `## x.y.z` section to CHANGELOG.md, then push: CI
  publishes once the packages installed cleanly in Debian 13 (x.y.0 versions: once the ISO built and booted).
