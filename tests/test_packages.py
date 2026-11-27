"""PR7-OS as Debian packages: the files split as they should be, complete control data, the install scripts, the
manifest the updater reads."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from pr7os import __version__, apps, packages

pytestmark = pytest.mark.skipif(not shutil.which("dpkg-deb"), reason="dpkg-deb isn't installed")
FAMILY = Path(os.environ.get("PR7OS_FAMILY", Path(__file__).resolve().parents[2]))


@pytest.fixture(scope="module")
def debs(built, tmp_path_factory):
    root, _ = built
    tree = tmp_path_factory.mktemp("tree")
    shutil.copytree(root, tree, dirs_exist_ok=True)
    if all((FAMILY / a.repo / a.package).is_dir() for a in apps.APPS):
        apps.stage(FAMILY, tree)
    venv = tmp_path_factory.mktemp("venv")          # a stand-in environment: a site-packages and the python link
    (venv / "lib/python3.13/site-packages/demo-1.0.dist-info").mkdir(parents=True)
    (venv / "lib/python3.13/site-packages/demo.py").write_text("x = 1\n")
    (venv / "bin").mkdir()
    (venv / "bin/python").symlink_to("/usr/bin/python3")
    out = tmp_path_factory.mktemp("debs")
    manifest = packages.build(tree, out, venv=venv)
    return out, manifest


def info(deb: Path, field: str) -> str:
    return subprocess.run(["dpkg-deb", "-f", str(deb), field], capture_output=True, text=True, check=True).stdout.strip()


def contents(deb: Path) -> list[str]:
    out = subprocess.run(["dpkg-deb", "-c", str(deb)], capture_output=True, text=True, check=True).stdout
    return [line.split()[5].lstrip("./") + (" -> " + line.split()[7] if " -> " in line else "")
            for line in out.splitlines()]


def test_four_packages_and_a_manifest(debs):
    out, manifest = debs
    names = {p["name"] for p in manifest["packages"]}
    assert names == {"paragon-pr7os-look", "paragon-pr7os-apps", "paragon-pr7os-updates", "paragon-pr7os-python"}
    assert manifest["version"] == __version__
    for p in manifest["packages"]:
        deb = out / p["file"]
        assert hashlib.sha256(deb.read_bytes()).hexdigest() == p["sha256"] and deb.stat().st_size == p["size"]
        assert info(deb, "Package") == p["name"] and info(deb, "Version") == p["version"]
        assert info(deb, "Maintainer") and info(deb, "Depends")
    assert json.loads((out / packages.MANIFEST).read_text()) == manifest
    python = next(p for p in manifest["packages"] if p["name"] == "paragon-pr7os-python")
    assert python["version"].startswith("1+") and python["file"].endswith("_amd64.deb")


def test_files_go_to_the_right_package(debs):
    out, manifest = debs
    files = {p["name"]: contents(out / p["file"]) for p in manifest["packages"]}
    look = files["paragon-pr7os-look"]
    assert "usr/share/color-schemes/ParagonObsidian.colors" in look
    assert "usr/share/paragon/setup_look.py" in look and "usr/share/paragon/lockscreen.py" in look
    assert "etc/xdg/kdeglobals" in look and not any(f.startswith("opt/paragon/apps") for f in look)
    updates = files["paragon-pr7os-updates"]
    assert "usr/libexec/paragon/pr7os-update-helper" in updates
    assert "usr/share/polkit-1/actions/org.paragon.pr7os.update.policy" in updates
    assert "usr/lib/systemd/user/pr7os-update-check.timer" in updates
    assert "opt/paragon/venv/bin/python -> /usr/bin/python3" in files["paragon-pr7os-python"]
    if any(f.startswith("opt/paragon/apps/") for f in files["paragon-pr7os-apps"]):
        app_files = files["paragon-pr7os-apps"]
        assert "usr/bin/pr7-e" in app_files and "etc/xdg/mimeapps.list" in app_files


def test_install_scripts_and_triggers(debs, tmp_path):
    out, manifest = debs
    look = out / next(p["file"] for p in manifest["packages"] if p["name"] == "paragon-pr7os-look")
    subprocess.run(["dpkg-deb", "-e", str(look), str(tmp_path / "ctl")], check=True)
    ctl = tmp_path / "ctl"
    assert "setup_look.py configure" in (ctl / "postinst").read_text() and os.access(ctl / "postinst", os.X_OK)
    assert "setup_look.py remove" in (ctl / "prerm").read_text()
    triggers = (ctl / "triggers").read_text()
    assert "interest-noawait /usr/share/plasma/shells/org.kde.plasma.desktop/contents/lockscreen" in triggers
    conffiles = (ctl / "conffiles").read_text().split()
    assert "/etc/xdg/kdeglobals" in conffiles and all(c.startswith("/etc/") for c in conffiles)
    for script in ("postinst", "prerm"):
        assert subprocess.run(["sh", "-n", str(ctl / script)]).returncode == 0


def test_executables_are_executable(debs):
    out, manifest = debs
    deb = out / next(p["file"] for p in manifest["packages"] if p["name"] == "paragon-pr7os-updates")
    listing = subprocess.run(["dpkg-deb", "-c", str(deb)], capture_output=True, text=True).stdout
    for line in listing.splitlines():
        if line.endswith(("usr/bin/pr7os-update", "pr7os-update-helper")):
            assert line.startswith("-rwxr-xr-x"), line


def test_setup_look_and_the_updater_are_valid_python():
    static = Path(__file__).resolve().parents[1] / "pr7os/static"
    for f in ("setup_look.py", "lockscreen.py", "updater/pr7os_update.py", "updater/pr7os-update",
              "updater/pr7os-update-helper", "updater/window.py"):
        compile((static / f).read_text(), f, "exec")
