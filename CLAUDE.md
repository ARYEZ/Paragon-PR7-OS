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
- **The apps** (`pr7os/apps.py`): 19 apps copied from their repositories (checked out next to this one, or
  `PR7OS_FAMILY`) to `/opt/paragon/apps/<repo>/`, one venv `/opt/paragon/venv` built in the image from the merged
  requirements (PySide6 as Essentials + Addons + Pdf: no web engine), launchers `/usr/bin/pr7-<x>`, menu entries,
  icons, `/etc/xdg/mimeapps.list` (folders PR7-E, images PR7-P, PDF PR7-R, media PR7-M, text PR7-W, archives PR7-Z).
  Left out for now (`LEFT_OUT`): AR, UN, U (Windows-only), CB, LN, Q, IS (global keys, Wayland, NTFS).
- **The ISO**: `live/` is a live-build configuration (`auto/config`, `package-lists/paragon.list.chroot`, hooks:
  0100 apps venv + every app imports, 0200 look (Plasma style, GRUB fonts, Plymouth), 0300 system (os-release diverted,
  ID stays debian; Calamares branding; initramfs)). The generated tree goes in as `includes.chroot_after_packages`.
  `live/build.sh` runs in `debian:trixie` (CI: docker --privileged); `tools/live_bootloader.py` themes the ISO's own
  menus (GRUB's live-theme with our fonts, isolinux colours). GRUB finds fonts by their name inside the .pf2:
  `grub-fonts.py` reads them back (SemiBold needs `-n`, or it's named "Inter Regular").
- **The lock screen** is Plasma's shell package (org.kde.plasma.desktop/contents/lockscreen), not the global theme,
  and its QML unlocks the session: `pr7os/static/lockscreen.py` (run by hook 0200) only restyles it with anchored edits
  (ParagonClock instead of Breeze's Clock; the password field's / unlock key's backgrounds; UserDelegate's gradient
  ring), checks all of them before writing, diverts the files. `tests/data/plasma-6.3.6` holds Plasma's own files for
  the tests; on a Plasma upgrade, refresh them and re-check the anchors. The boot test locks (Meta+L) and unlocks.
- **CI** (`.github/workflows/build.yml`): tests, then the ISO (ubuntu runner, docker debian:trixie), then
  `tools/boot_test.py` boots it in QEMU/KVM (UEFI: boot menu, splash, desktop; direct kernel with
  `live-config.noautologin`: login screen, password "live", desktop) and pushes the screenshots to the
  **ci-boot-screens** branch (CI only; fetch it to look: release downloads are blocked from the session). A new
  `__version__` publishes the ISO (split into parts over 2 GB); **0.0.x versions never publish**.
- This session can't reach deb.debian.org: the ISO is only built in CI. Locally: the assets, the login screen
  (`tools/login_preview.py` renders Main.qml with stand-ins for SDDM), the apps starting, the live menus' theming.

## The look (family rules)

- Colours: the family's only (hues ~318 -> 0 -> 42 deg, pearl and onyx greys); tests check every colour in every
  generated file and sample the pictures. Inter; labels UPPER CASE. Mock-up: `tools/mockup.py` (docs/mockup).

## Rules

- Behaviour questions: do what Debian and KDE Plasma do; the look is the family's.
- Tests: `python -m pytest` (offscreen). Never the real settings or system.
- Releases: bump `__version__` in `pr7os/__init__.py` and add a `## x.y.z` section to CHANGELOG.md, then push: CI
  publishes once the ISO built and booted.
