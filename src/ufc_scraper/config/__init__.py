"""Project configuration loaded from TOML files."""

from __future__ import annotations

from pathlib import Path
import tomllib


CONFIG_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = CONFIG_ROOT.parents[2]


def load_toml(filename: str) -> dict:
    """Load a TOML file from the package configuration directory."""
    with (CONFIG_ROOT / filename).open("rb") as handle:
        return tomllib.load(handle)


PATHS = load_toml("paths.toml")


def project_path(section: str, name: str) -> Path:
    """Resolve a configured project-relative path."""
    return PROJECT_ROOT / PATHS[section][name]


__all__ = ["CONFIG_ROOT", "PATHS", "PROJECT_ROOT", "load_toml", "project_path"]
