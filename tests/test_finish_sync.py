"""One finish for the whole desktop (static/finish_sync.py), run for real on a stand-in config folder with a stand-in
plasma-apply-lookandfeel that writes kdeglobals as the real one does."""
import importlib.util
from pathlib import Path

import pytest

STATIC = Path(__file__).resolve().parents[1] / "pr7os/static"


@pytest.fixture
def desk(tmp_path, monkeypatch):
    cfg = tmp_path / "config"
    cfg.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(cfg))
    monkeypatch.delenv("PARAGON_FAMILY_FILE", raising=False)
    log = tmp_path / "applied.txt"
    tool = tmp_path / "plasma-apply-lookandfeel"
    tool.write_text(f'#!/bin/sh\necho "$2" >> "{log}"\n'
                    f'printf "[General]\\nColorScheme=x\\n\\n[KDE]\\nLookAndFeelPackage=%s\\n" "$2" > "{cfg}/kdeglobals"\n')
    tool.chmod(0o755)
    monkeypatch.setenv("PR7OS_APPLY_LOOKANDFEEL", str(tool))
    spec = importlib.util.spec_from_file_location("finish_sync", STATIC / "finish_sync.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, cfg, log


def plasma_is(cfg, pkg):
    (cfg / "kdeglobals").write_text(f"[General]\nfont=Inter\n\n[KDE]\nLookAndFeelPackage={pkg}\nother=1\n")


def test_an_app_switching_the_finish_switches_plasma(desk):
    mod, cfg, log = desk
    plasma_is(cfg, "org.paragon.pr7os.obsidian")
    sync = mod.Sync()
    assert mod.family() == "obsidian"                         # at sign-in, Plasma's choice is the family's
    (cfg / "paragon/family-finish").write_text("aurora")       # View > Finish > AURORA in any Paragon app
    assert sync.step() == "plasma"
    assert log.read_text().split() == ["org.paragon.pr7os.aurora"] and mod.plasma() == "aurora"
    assert sync.step() == ""                                   # settled: nothing more to do


def test_picking_a_paragon_theme_in_system_settings_switches_the_apps(desk):
    mod, cfg, log = desk
    plasma_is(cfg, "org.paragon.pr7os.obsidian")
    sync = mod.Sync()
    plasma_is(cfg, "org.paragon.pr7os.aurora")                 # System Settings > Global Theme
    assert sync.step() == "family" and mod.family() == "aurora"
    assert not log.exists()                                    # Plasma was already there: nothing applied


def test_other_global_themes_leave_the_apps_alone(desk):
    mod, cfg, log = desk
    plasma_is(cfg, "org.paragon.pr7os.aurora")
    sync = mod.Sync()
    plasma_is(cfg, "org.kde.breeze.desktop")
    assert sync.step() == "" and mod.family() == "aurora"
    (cfg / "paragon/family-finish").write_text("obsidian")      # but an app's switch still brings Plasma back
    assert sync.step() == "plasma" and mod.plasma() == "obsidian"


def test_a_new_account_without_choices(desk):
    mod, cfg, log = desk
    sync = mod.Sync()                                           # no kdeglobals yet, no family file
    assert mod.family() is None and sync.step() == ""
