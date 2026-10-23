"""Shared validation helpers for the Audex Revival theme store.

The store is a plain GitHub repository: theme packages are zip files under
``themes/`` and ``index.json`` describes them. This module is used by the
maintainer scripts and by CI, and mirrors the checks the Android app performs
before installing a downloaded package.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import wave
import zipfile
from pathlib import Path

SCHEMA_VERSION = 1
MIN_APP_VERSION = 610
INDEX_NAME = "index.json"
THEMES_DIR = "themes"
PACKAGE_SUFFIX = ".audextheme"

MAX_PACKAGE_BYTES = 8 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 20 * 1024 * 1024
MAX_ENTRIES = 40
MAX_AUDIO_BYTES = 2 * 1024 * 1024
MAX_AUDIO_SECONDS = 10.0

AUDIO_EXTENSIONS = {".wav", ".ogg", ".mp3", ".mid", ".m4a"}

EVENTS = (
    "click",
    "view_enter",
    "view_exit",
    "focus_interactive",
    "focus_non_interactive",
    "long_click",
    "scroll",
    "gesture_begin",
    "gesture_end",
    "select",
    "window_state",
    "charger_plugged",
    "charger_unplugged",
    "screen_on",
    "screen_off",
)

ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{1,31}$")
VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


class ThemeError(ValueError):
    """A package or the index is not valid."""


def _text(manifest: dict, key: str, *, maximum: int, minimum: int = 1) -> str:
    value = manifest.get(key)
    if not isinstance(value, str):
        raise ThemeError(f"theme.json: '{key}' must be a string")
    value = value.strip()
    if not minimum <= len(value) <= maximum:
        raise ThemeError(
            f"theme.json: '{key}' must be {minimum}-{maximum} characters long"
        )
    if any(ord(ch) < 32 for ch in value):
        raise ThemeError(f"theme.json: '{key}' must not contain control characters")
    return value


def _safe_entry(name: str) -> None:
    if not name or name.startswith("/") or "\\" in name or "//" in name:
        raise ThemeError(f"package contains an unsafe path: {name!r}")
    parts = name.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise ThemeError(f"package contains an unsafe path: {name!r}")
    if ":" in parts[0]:
        raise ThemeError(f"package contains an unsafe path: {name!r}")
    if name != "theme.json" and not name.startswith("sounds/"):
        raise ThemeError(f"package contains an unexpected file: {name!r}")


def _audio_problem(name: str, data: bytes) -> str | None:
    extension = Path(name).suffix.lower()
    if extension not in AUDIO_EXTENSIONS:
        return f"unsupported audio extension: {name}"
    if not data:
        return f"audio file is empty: {name}"
    if len(data) > MAX_AUDIO_BYTES:
        return f"audio file is larger than {MAX_AUDIO_BYTES // (1024 * 1024)} MiB: {name}"
    if extension == ".wav":
        try:
            with wave.open(io.BytesIO(data), "rb") as wav:
                frames = wav.getnframes()
                rate = wav.getframerate()
                if rate <= 0:
                    return f"invalid WAV sample rate: {name}"
                if frames / rate > MAX_AUDIO_SECONDS:
                    return f"audio is longer than {MAX_AUDIO_SECONDS:g}s: {name}"
                if wav.getsampwidth() not in (1, 2, 3, 4):
                    return f"unsupported WAV sample width: {name}"
        except (wave.Error, EOFError):
            return f"not a readable PCM WAV file: {name}"
    return None


def validate_package(path: Path) -> dict:
    """Validate one ``.audextheme`` zip and return its manifest plus hashes."""

    if path.suffix != PACKAGE_SUFFIX:
        raise ThemeError(f"expected a {PACKAGE_SUFFIX} file: {path.name}")
    if not path.is_file():
        raise ThemeError(f"missing package: {path}")
    size = path.stat().st_size
    if size > MAX_PACKAGE_BYTES:
        raise ThemeError(
            f"{path.name} is {size} bytes; the limit is {MAX_PACKAGE_BYTES} bytes"
        )

    digest = hashlib.sha256(path.read_bytes()).hexdigest()

    try:
        archive = zipfile.ZipFile(path)
    except zipfile.BadZipFile as exc:
        raise ThemeError(f"{path.name} is not a valid zip file") from exc

    with archive:
        if archive.testzip() is not None:
            raise ThemeError(f"{path.name} contains a corrupt entry")
        names = archive.namelist()
        if len(names) > MAX_ENTRIES:
            raise ThemeError(f"{path.name} contains more than {MAX_ENTRIES} files")
        if len(set(names)) != len(names):
            raise ThemeError(f"{path.name} contains duplicate file names")
        total = 0
        for info in archive.infolist():
            _safe_entry(info.filename)
            total += info.file_size
        if total > MAX_UNCOMPRESSED_BYTES:
            raise ThemeError(
                f"{path.name} unpacks to more than {MAX_UNCOMPRESSED_BYTES} bytes"
            )

        if "theme.json" not in names:
            raise ThemeError(f"{path.name} has no theme.json at its root")
        raw_manifest = archive.read("theme.json")
        if len(raw_manifest) > 64 * 1024:
            raise ThemeError(f"{path.name}: theme.json is too large")
        try:
            manifest = json.loads(raw_manifest)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ThemeError(f"{path.name}: theme.json is not valid JSON") from exc
        if not isinstance(manifest, dict):
            raise ThemeError(f"{path.name}: theme.json must be a JSON object")

        if manifest.get("schema") != SCHEMA_VERSION:
            raise ThemeError(
                f"{path.name}: 'schema' must be {SCHEMA_VERSION}"
            )
        theme_id = manifest.get("id")
        if not isinstance(theme_id, str) or not ID_PATTERN.match(theme_id):
            raise ThemeError(
                f"{path.name}: 'id' must be a lowercase slug such as 'warm-chime'"
            )
        if not VERSION_PATTERN.match(str(manifest.get("version", ""))):
            raise ThemeError(f"{path.name}: 'version' must look like 1.0.0")
        _text(manifest, "name", maximum=60)
        _text(manifest, "author", maximum=80)
        _text(manifest, "description", maximum=400)
        _text(manifest, "license", maximum=40)

        sounds = manifest.get("sounds")
        if not isinstance(sounds, dict) or not sounds:
            raise ThemeError(f"{path.name}: 'sounds' must be a non-empty object")
        unknown = sorted(set(sounds) - set(EVENTS))
        if unknown:
            raise ThemeError(
                f"{path.name}: unknown event(s): {', '.join(unknown)}"
            )
        if "click" not in sounds:
            raise ThemeError(f"{path.name}: 'click' is the one required event")

        for event, entry in sorted(sounds.items()):
            if not isinstance(entry, str):
                raise ThemeError(f"{path.name}: sound path for '{event}' must be a string")
            _safe_entry(entry)
            if not entry.startswith("sounds/"):
                raise ThemeError(f"{path.name}: '{event}' must point inside sounds/")
            if entry not in names:
                raise ThemeError(f"{path.name}: missing file referenced by '{event}'")
            problem = _audio_problem(entry, archive.read(entry))
            if problem:
                raise ThemeError(f"{path.name}: {problem}")

    return {
        "manifest": manifest,
        "sha256": digest,
        "size": size,
        "path": path,
    }


def expected_package_name(theme_id: str, version: str) -> str:
    return f"{theme_id}-{version}{PACKAGE_SUFFIX}"


def collect_packages(store_root: Path) -> list[dict]:
    """Validate every package in the store and return sorted index entries."""

    directory = store_root / THEMES_DIR
    if not directory.is_dir():
        raise ThemeError(f"missing folder: {directory}")

    entries = []
    seen_ids: dict[str, str] = {}
    for path in sorted(directory.glob(f"*{PACKAGE_SUFFIX}")):
        result = validate_package(path)
        manifest = result["manifest"]
        theme_id = manifest["id"]
        version = manifest["version"]
        if theme_id in seen_ids:
            raise ThemeError(
                f"duplicate theme id '{theme_id}' in {path.name} and {seen_ids[theme_id]}"
            )
        seen_ids[theme_id] = path.name
        expected = expected_package_name(theme_id, version)
        if path.name != expected:
            raise ThemeError(f"{path.name} should be named {expected}")
        entries.append(
            {
                "id": theme_id,
                "name": manifest["name"],
                "author": manifest["author"],
                "description": manifest["description"],
                "version": version,
                "license": manifest["license"],
                "sounds": len(manifest["sounds"]),
                "file": f"{THEMES_DIR}/{path.name}",
                "sha256": result["sha256"],
                "size": result["size"],
                "minAppVersion": MIN_APP_VERSION,
            }
        )

    if not entries:
        raise ThemeError("the store has no themes yet")
    entries.sort(key=lambda entry: (entry["name"].casefold(), entry["id"]))
    return entries


def render_index(entries: list[dict]) -> str:
    return json.dumps(
        {"schema": SCHEMA_VERSION, "themes": entries},
        indent=2,
        ensure_ascii=False,
    ) + "\n"
