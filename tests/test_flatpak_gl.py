"""pr7os-flatpak-gl: Flatpak's NVIDIA libraries for the running driver, once per driver version (the real script, a
stand-in flatpak that records what it's asked and 'installs' what update would bring)."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "pr7os/static/system/pr7os-flatpak-gl"


@pytest.fixture
def pc(tmp_path):
    root, bin_, log, have = tmp_path / "root", tmp_path / "bin", tmp_path / "log", tmp_path / "installed"
    bin_.mkdir()
    have.write_text("org.freedesktop.Platform\n")                # Steam's runtime is there
    (bin_ / "flatpak").write_text(f"""#!/bin/sh
echo "flatpak $*" >> "{log}"
case "$1" in
  info) grep -qx "$3" "{have}";;
  list) cat "{have}";;
  update) [ -f "{tmp_path}/offline" ] || echo "$WANT" >> "{have}";;
  install) ;;
esac
""")
    (bin_ / "flatpak").chmod(0o755)
    env = dict(os.environ, PATH=f"{bin_}{os.pathsep}{os.environ['PATH']}", PR7OS_ROOT=str(root),
               WANT="org.freedesktop.Platform.GL.nvidia-550-163-01")
    log.write_text("")
    return root, env, log, have, tmp_path


def driver(root, name="nvidia", version="550.163.01"):
    (root / f"sys/module/{name}").mkdir(parents=True, exist_ok=True)
    (root / f"sys/module/{name}/version").write_text(version + "\n")


def run(env):
    return subprocess.run([sys.executable, str(SCRIPT)], env=env, capture_output=True, text=True)


def test_nothing_without_the_driver(pc):
    root, env, log, have, tmp = pc
    assert run(env).returncode == 0 and log.read_text() == ""


def test_installed_once_per_driver_version(pc):
    root, env, log, have, tmp = pc
    driver(root, "nvidia_current")                               # Debian's module name works too
    out = run(env).stdout
    assert "flatpak update --system -y --noninteractive" in log.read_text()
    assert "org.freedesktop.Platform.GL.nvidia-550-163-01 installed" in out
    assert (root / "var/lib/paragon/flatpak-gl-nvidia").read_text() == "550.163.01\n"
    log.write_text("")
    run(env)                                                     # the next start: nothing to do
    assert "update" not in log.read_text()
    driver(root, "nvidia_current", "550.163.02")                  # Debian updated the driver
    env["WANT"] = "org.freedesktop.Platform.GL.nvidia-550-163-02"
    run(env)
    assert "update" in log.read_text()
    assert (root / "var/lib/paragon/flatpak-gl-nvidia").read_text() == "550.163.02\n"


def test_offline_is_tried_again(pc):
    root, env, log, have, tmp = pc
    driver(root)
    (tmp / "offline").write_text("")
    assert "tried again at the next start" in run(env).stdout
    assert "flatpak install --system -y --noninteractive flathub org.freedesktop.Platform.GL.nvidia-550-163-01" \
        in log.read_text()
    assert not (root / "var/lib/paragon/flatpak-gl-nvidia").exists()


def test_nothing_without_flatpak_runtimes(pc):
    root, env, log, have, tmp = pc
    driver(root)
    have.write_text("")
    assert "nothing to do" in run(env).stdout and "update" not in log.read_text()
