"""Paragon PR7-OS updates: what's newer on GitHub, downloaded and checked, installed with apt (standard library only).

Each release of ARYEZ/Paragon-PR7-OS carries pr7os-update.json (every package's version, file, SHA-256 and size) and
the packages. A package whose installed version differs from the manifest's is pending; pending packages are
downloaded from that release only, checked against the manifest, and installed together with apt-get (new Debian
dependencies come from Debian). The addresses are built here from the repository and the release's tag: nothing
outside decides where the root helper downloads from. PR7OS_UPDATE_SERVER (tests) serves both the API and the
downloads; pkexec clears the environment, so it never reaches the helper there.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
import urllib.request
from pathlib import Path

REPO = "ARYEZ/Paragon-PR7-OS"
MANIFEST = "pr7os-update.json"
USER_AGENT = "Paragon-PR7-OS-update"           # names only the program
DEB_NAME = re.compile(r"^paragon-pr7os-[a-z]+_[A-Za-z0-9.+~]+_(all|amd64)\.deb$")
PACKAGES = ("paragon-pr7os-look", "paragon-pr7os-apps", "paragon-pr7os-python", "paragon-pr7os-updates")


class UpdateError(Exception):
    pass


def _server() -> str | None:
    return os.environ.get("PR7OS_UPDATE_SERVER")


def api_url(path: str) -> str:
    return f"{_server() or 'https://api.github.com'}/repos/{REPO}/{path}"


def download_url(tag: str, name: str) -> str:
    return f"{_server() or 'https://github.com'}/{REPO}/releases/download/{tag}/{name}"


def fetch(url: str, timeout: float = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except OSError as e:
        raise UpdateError(f"GitHub can't be reached ({e})") from e


def latest() -> dict:
    """The newest release: {"tag", "version", "notes", "manifest"}."""
    try:
        rel = json.loads(fetch(api_url("releases/latest")))
        tag = rel["tag_name"]
        if not re.fullmatch(r"v[0-9][0-9A-Za-z.+~-]*", tag):
            raise UpdateError(f"unexpected release tag {tag!r}")
        manifest = json.loads(fetch(download_url(tag, MANIFEST)))
    except (ValueError, KeyError) as e:
        raise UpdateError(f"the release's details can't be read ({e})") from e
    return {"tag": tag, "version": manifest.get("version", tag[1:]), "notes": rel.get("body") or "",
            "manifest": manifest}


def installed() -> dict[str, str]:
    """The PR7-OS packages installed now and their versions (dpkg's records)."""
    cmd = os.environ.get("PR7OS_DPKG_QUERY", "dpkg-query")
    done = subprocess.run([cmd, "-W", "-f", "${Package}\\t${Version}\\t${db:Status-Status}\\n", "paragon-pr7os-*"],
                          capture_output=True, text=True)
    out = {}
    for line in done.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) == 3 and parts[2] == "installed":
            out[parts[0]] = parts[1]
    return out


def pending(manifest: dict, have: dict[str, str]) -> list[dict]:
    """The manifest's packages whose installed version differs (or that aren't installed yet)."""
    out = []
    for p in manifest.get("packages", []):
        if p.get("name") in PACKAGES and have.get(p["name"]) != p.get("version"):
            out.append(p)
    return out


def needs_logout(pkgs: list[dict]) -> bool:
    """The look changes what Plasma loaded at login: logging out and in shows it everywhere."""
    return any(p["name"] == "paragon-pr7os-look" for p in pkgs)


def download(tag: str, pkgs: list[dict], folder: Path, progress=None) -> list[Path]:
    """Each package from the release, checked against the manifest (name, size, SHA-256)."""
    files = []
    for i, p in enumerate(pkgs, 1):
        name = p.get("file", "")
        if not DEB_NAME.match(name) or not name.startswith(p["name"] + "_"):
            raise UpdateError(f"the manifest names an unexpected file {name!r}")
        if progress:
            progress(i, len(pkgs), name)
        data = fetch(download_url(tag, name), timeout=600)
        if len(data) != int(p["size"]) or hashlib.sha256(data).hexdigest() != p["sha256"]:
            raise UpdateError(f"{name} didn't arrive intact (its size or checksum doesn't match the release)")
        path = folder / name
        path.write_bytes(data)
        files.append(path)
    return files


def install(files: list[Path], output=print) -> int:
    """apt-get installs the packages together (Debian's dependencies from Debian); changed config files are kept."""
    apt = os.environ.get("PR7OS_APT", "apt-get")
    env = dict(os.environ, DEBIAN_FRONTEND="noninteractive")
    subprocess.run([apt, "update", "-qq"], env=env)                 # best effort: fresh lists for new dependencies
    cmd = [apt, "install", "-y", "--allow-downgrades", "-o", "Dpkg::Options::=--force-confdef",
           "-o", "Dpkg::Options::=--force-confold"] + [str(f.resolve()) for f in files]
    proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in proc.stdout:
        output(line.rstrip())
    return proc.wait()


def settings_path() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "paragon" / "pr7os-update.json"


def skipped() -> str:
    try:
        return json.loads(settings_path().read_text()).get("skip", "")
    except (OSError, ValueError):
        return ""


def skip(version: str) -> None:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"skip": version}))
