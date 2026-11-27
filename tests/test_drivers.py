"""Welcome's DRIVERS: pr7os-drivers-helper (the real script, with stand-ins for apt, lspci, nvidia-detect, mokutil, dkms
and systemctl on PATH and PR7OS_ROOT for /etc) and the card that runs it."""
import importlib.machinery
import importlib.util
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

WELCOME = Path(__file__).resolve().parent.parent / "pr7os" / "static" / "welcome"
HELPER = WELCOME / "pr7os-drivers-helper"

RTX = """00:02.0 VGA compatible controller [0300]: Intel Corporation Raptor Lake-S GT1 [UHD Graphics 770] [8086:a780] (rev 04)
\tSubsystem: ASUSTeK Computer Inc. Device [1043:8882]
\tKernel driver in use: i915
\tKernel modules: i915, xe
01:00.0 VGA compatible controller [0300]: NVIDIA Corporation AD104 [GeForce RTX 4070] [10de:2786] (rev a1)
\tSubsystem: Micro-Star International Co., Ltd. [MSI] Device [1462:5125]
\tKernel driver in use: nouveau
\tKernel modules: nouveau
01:00.1 Audio device [0403]: NVIDIA Corporation AD104 High Definition Audio Controller [10de:22bc] (rev a1)
\tKernel driver in use: snd_hda_intel
"""
DETECT_OK = """Detected NVIDIA GPUs:
01:00.0 VGA compatible controller [0300]: NVIDIA Corporation AD104 [GeForce RTX 4070] [10de:2786] (rev a1)

Checking card:  NVIDIA Corporation AD104 [GeForce RTX 4070] (rev a1)
Your card is supported by all driver versions.
Your card is also supported by the Tesla 535 drivers series.
It is recommended to install the
    nvidia-driver
package.
"""
DETECT_NO = """Checking card:  NVIDIA Corporation Device 2b85 (rev a1)
Uh oh. Your card is not supported by any driver version up to 550.163.01.
A newer driver may add support for your card.
"""


def load():
    loader = importlib.machinery.SourceFileLoader("drivers_helper", str(HELPER))
    spec = importlib.util.spec_from_loader("drivers_helper", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def test_cards_from_lspci():
    cards = load().gpus(RTX)
    assert [(g["name"], g["vendor"], g["device"], g["driver"]) for g in cards] == [
        ("Intel UHD Graphics 770", "8086", "a780", "i915"),
        ("NVIDIA GeForce RTX 4070", "10de", "2786", "nouveau")]          # the card's audio part isn't a display


def test_debians_areas_are_turned_on():
    h = load()
    text = ("# deb cdrom:[Debian]/ trixie main\n"
            "deb http://deb.debian.org/debian/ trixie main\n"
            "deb [arch=amd64] http://security.debian.org/debian-security trixie-security main non-free-firmware\n"
            "deb https://repo.example.com/ stable main\n")
    new, changed = h.one_line(text)
    assert changed and new.splitlines() == [
        "# deb cdrom:[Debian]/ trixie main",
        "deb http://deb.debian.org/debian/ trixie main contrib non-free non-free-firmware",
        "deb [arch=amd64] http://security.debian.org/debian-security trixie-security main non-free-firmware contrib non-free",
        "deb https://repo.example.com/ stable main"]                    # somebody else's repository is left alone
    assert h.one_line(new) == (new, False)
    sources = ("Types: deb\nURIs: http://deb.debian.org/debian\nSuites: trixie trixie-updates\nComponents: main\n"
               "Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg\n\n"
               "Types: deb\nURIs: https://dl.flathub.example/\nSuites: stable\nComponents: main\n")
    new, changed = h.deb822(sources)
    assert changed and "Components: main contrib non-free non-free-firmware\nSigned-By" in new
    assert new.endswith("Suites: stable\nComponents: main\n")


@pytest.fixture
def pc(tmp_path, monkeypatch):
    """A made-up PC: an NVIDIA card on nouveau, Secure Boot on, every tool a stand-in that writes what it was asked."""
    root, bin_, log = tmp_path / "root", tmp_path / "bin", tmp_path / "log"
    (root / "etc/apt").mkdir(parents=True)
    (root / "etc/apt/sources.list").write_text("deb http://deb.debian.org/debian/ trixie main\n")
    (root / "var/lib/dkms").mkdir(parents=True)
    (root / "var/lib/dkms/mok.pub").write_text("key")
    bin_.mkdir()
    (tmp_path / "lspci.txt").write_text(RTX)
    (tmp_path / "detect.txt").write_text(DETECT_OK)
    tools = {
        "apt-get": 'echo "apt-get $*" >> "$LOG"',
        "apt-cache": 'case "$3" in firmware-mediatek|nvidia-suspend-common|linux-headers-amd64|firmware-*|*microcode|'
                     'bluez-firmware) echo "Package: $3";; esac',
        "lspci": 'cat "$PCI"',
        "nvidia-detect": 'echo "nvidia-detect $*" >> "$LOG"; cat "$DETECT"',
        "dkms": 'echo "nvidia/550.163.01, 6.12.48-amd64, x86_64: installed"',
        "mokutil": 'echo "mokutil $*" >> "$LOG"; case "$1" in --sb-state) echo "SecureBoot enabled";; '
                   '--test-key) echo "$2 is not enrolled";; --generate-hash=*) echo \'$6$salt$hash\';; esac',
        "systemctl": 'echo "systemctl $*" >> "$LOG"',
        "update-initramfs": 'echo "update-initramfs $*" >> "$LOG"',
        "dpkg-query": 'echo "nvidia-driver not-installed"',
    }
    for name, body in tools.items():
        f = bin_ / name
        f.write_text("#!/bin/sh\n" + body + "\n")
        f.chmod(f.stat().st_mode | stat.S_IEXEC)
    env = dict(os.environ, PATH=f"{bin_}{os.pathsep}{os.environ['PATH']}", PR7OS_ROOT=str(root), LOG=str(log),
               PCI=str(tmp_path / "lspci.txt"), DETECT=str(tmp_path / "detect.txt"))
    env.pop("PR7OS_SIMULATE", None)
    log.write_text("")
    return tmp_path, root, env, log


def run(env, word="install"):
    return subprocess.run([sys.executable, str(HELPER), word], env=env, capture_output=True, text=True)


def test_nvidia_driver_install(pc):
    tmp, root, env, log = pc
    done = run(env)
    assert done.returncode == 0, done.stdout + done.stderr
    calls = log.read_text().splitlines()
    assert (root / "etc/apt/sources.list").read_text() == \
        "deb http://deb.debian.org/debian/ trixie main contrib non-free non-free-firmware\n"
    installs = [c for c in calls if " install -y " in c]
    assert "firmware-iwlwifi" in installs[0] and "firmware-realtek" in installs[0]
    assert installs[1].endswith("install -y nvidia-detect")
    assert "nvidia-detect 10de:2786" in calls                            # Debian decides for this card's own id
    assert installs[2].endswith("linux-headers-amd64 nvidia-driver nvidia-suspend-common")
    assert calls.index(installs[0]) > calls.index(next(c for c in calls if c.endswith("update -qq")))
    conf = (root / "etc/modprobe.d/paragon-nvidia.conf").read_text()
    assert "options nvidia-drm modeset=1" in conf and "NVreg_PreserveVideoMemoryAllocations=1" in conf
    assert "systemctl enable nvidia-suspend.service" in calls and "update-initramfs -u" in calls
    imported = next(c for c in calls if c.startswith("mokutil --import"))
    assert str(root / "var/lib/dkms/mok.pub") in imported and "--hash-file" in imported
    mok = next(line for line in done.stdout.splitlines() if line.startswith("MOK "))
    password = mok.split()[1]
    assert len(password) == 8 and password.isdigit()
    assert f"--generate-hash={password}" in log.read_text()
    assert done.stdout.splitlines()[-1] == "DONE nvidia-driver: restart the PC to use it"


def test_a_card_debian_has_no_driver_for(pc):
    tmp, root, env, log = pc
    (tmp / "detect.txt").write_text(DETECT_NO)
    done = run(env)
    assert done.returncode == 1
    assert done.stdout.splitlines()[-1] == ("ERROR Debian 13 has no driver for the NVIDIA GeForce RTX 4070: Uh oh. Your "
                                           "card is not supported by any driver version up to 550.163.01.")
    assert "nvidia-driver" not in log.read_text().replace("nvidia-detect", "")
    assert not (root / "etc/modprobe.d/paragon-nvidia.conf").exists()


def test_without_nvidia_only_firmware(pc):
    tmp, root, env, log = pc
    (tmp / "lspci.txt").write_text(RTX.split("01:00.0")[0])
    done = run(env)
    assert done.returncode == 0 and done.stdout.splitlines()[-1] == "DONE firmware: restart the PC to use it"
    assert "nvidia" not in log.read_text() and "mokutil --import" not in log.read_text()


def test_state(pc):
    tmp, root, env, log = pc
    s = json.loads(run(env, "state").stdout)
    assert s["nvidia"] and not s["in_use"] and not s["installed"] and s["secure_boot"]
    assert [g["name"] for g in s["gpus"]] == ["Intel UHD Graphics 770", "NVIDIA GeForce RTX 4070"]


def test_other_words_are_refused(pc):
    tmp, root, env, log = pc
    for args in (["remove"], ["install", "now"], []):
        done = subprocess.run([sys.executable, str(HELPER), *args], env=env, capture_output=True, text=True)
        assert done.returncode == 2 and done.stdout.startswith("ERROR")
    assert log.read_text() == ""


# ---------------------------------------------------------------- the card
@pytest.fixture
def welcome(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("PARAGON_FAMILY_FILE", str(tmp_path / "family"))
    ssh = tmp_path / "ssh"
    ssh.write_text("#!/bin/sh\necho off\n")
    ssh.chmod(0o755)
    monkeypatch.setenv("PR7OS_SSH_HELPER", str(ssh))
    state = tmp_path / "state.json"
    state.write_text(json.dumps({"gpus": [{"name": "NVIDIA GeForce RTX 4070", "vendor": "10de", "device": "2786",
                                           "driver": "nouveau", "class": "0300"}], "nvidia": True, "in_use": False,
                                 "installed": False, "secure_boot": True, "key_waiting": False}))
    fake = tmp_path / "drivers"
    fake.write_text(f"""#!/bin/sh
if [ "$1" = state ]; then cat "{state}"; exit 0; fi
echo "STEP Installing nvidia-driver"
echo "MOK 12345678"
echo "DONE nvidia-driver: restart the PC to use it"
""")
    fake.chmod(0o755)
    monkeypatch.setenv("PR7OS_DRIVERS_HELPER", str(fake))
    sys.path.insert(0, str(WELCOME))
    import welcome as mod
    sys.path.remove(str(WELCOME))
    w = mod.Window(sync=True)
    yield mod, w, state
    w.close()


def test_the_card(welcome):
    mod, w, state = welcome
    assert w.drivers_key.text() == "INSTALL NVIDIA DRIVER" and "RTX 4070" in w.drivers_text.text()
    w.drivers_key.click()
    note = w.drivers_text.text()
    assert "Enroll MOK" in note and "1234 5678" in note                    # shown once, as MOK manager wants it
    assert "12345678" not in w.last_line
    assert mod.drivers_view({"gpus": []}) == ("Firmware for Wi-Fi, Bluetooth, sound and graphics, and your "
                                              "processor's security fixes.", "INSTALL FIRMWARE")
    gpu = json.loads(state.read_text())["gpus"]
    assert "in use" in mod.drivers_view({"gpus": gpu, "in_use": True})[0]
    assert "restart" in mod.drivers_view({"gpus": gpu, "installed": True})[0]
