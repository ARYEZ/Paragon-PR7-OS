#!/bin/bash
# PR7-OS's Debian packages and the manifest the updater reads, into /work/debs. Runs as root in a Debian 13 container
# (CI: docker run debian:trixie) with the repository at /work and the generated tree at /work/build/root. Used by every
# release (the update channel) and by live/build.sh (the ISO is built from the same packages).
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends ca-certificates python3 python3-venv dpkg-dev xz-utils

# the apps' Python environment, at its final path, with Debian 13's python3 (the image's): one venv for every app;
# PySide6's parts come separately so its web engine (which no app uses) stays out
rm -rf /opt/paragon/venv
python3 -m venv /opt/paragon/venv
/opt/paragon/venv/bin/pip install --no-cache-dir --upgrade pip
req=/work/build/root/opt/paragon/requirements.txt
grep -v -i '^pyside6' "$req" > /tmp/paragon-req.txt
pyside=$(grep -i '^pyside6' "$req" | sed 's/^[Pp]y[Ss]ide6//')
/opt/paragon/venv/bin/pip install --no-cache-dir -r /tmp/paragon-req.txt \
    "PySide6_Essentials${pyside}" "PySide6_Addons${pyside}" "PySide6_Pdf"
# byte-compiled as far as it goes (PySide6 ships template files named .py that aren't Python)
/opt/paragon/venv/bin/python -m compileall -q -x '(\.tmpl\.py$|/deploy_lib/)' /opt/paragon/venv/lib > /dev/null || true
python3 -m compileall -q /work/build/root/opt/paragon/apps          # the apps strictly: an error there is a bug

# the packages, and the manifest the updater reads
rm -rf /work/debs
PYTHONPATH=/work python3 -m pr7os.packages --root /work/build/root --venv /opt/paragon/venv --out /work/debs

