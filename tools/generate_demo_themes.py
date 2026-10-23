#!/usr/bin/env python3
"""Generate the two CC0 demo themes shipped with the store.

The output is deterministic so rebuilding the packages does not churn the
index. Run from the store root:

    python3 tools/generate_demo_themes.py
    python3 tools/build_index.py
"""

from __future__ import annotations

import io
import json
import math
import struct
import wave
import zipfile
from pathlib import Path

SAMPLE_RATE = 44_100
AUTHOR = "Audex Revival"
LICENSE = "CC0-1.0"
STORE_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = STORE_ROOT / "themes"

# (kind, frequency, start seconds, duration seconds, amplitude)
Note = tuple[str, float, float, float, float]


def bell(freq: float, duration: float, amplitude: float = 0.9, start: float = 0.0) -> Note:
    return ("bell", freq, start, duration, amplitude)


def pulse(freq: float, duration: float, amplitude: float = 0.8, start: float = 0.0) -> Note:
    return ("pulse", freq, start, duration, amplitude)


THEMES = {
    "chime": {
        "name": "Chime",
        "version": "1.0.0",
        "description": (
            "Bright struck-bell tones for every feedback event. C6 clicks and "
            "rising two-note cues make buttons, focus changes and charging easy "
            "to tell apart without overwhelming speech."
        ),
        "events": {
            "click": [bell(1046.50, 0.09)],
            "view_enter": [bell(880.00, 0.11)],
            "view_exit": [bell(698.46, 0.10)],
            "focus_interactive": [bell(987.77, 0.09)],
            "focus_non_interactive": [bell(783.99, 0.08)],
            "long_click": [bell(659.25, 0.20)],
            "scroll": [bell(1174.66, 0.055)],
            "gesture_begin": [bell(587.33, 0.08), bell(880.00, 0.08, start=0.055)],
            "gesture_end": [bell(880.00, 0.08), bell(587.33, 0.10, start=0.060)],
            "select": [bell(1318.51, 0.11)],
            "window_state": [
                bell(523.25, 0.16, amplitude=0.55),
                bell(659.25, 0.16, amplitude=0.55),
            ],
            "charger_plugged": [bell(659.25, 0.10), bell(987.77, 0.14, start=0.090)],
            "charger_unplugged": [bell(987.77, 0.10), bell(659.25, 0.14, start=0.090)],
            "screen_on": [
                bell(783.99, 0.12, amplitude=0.55),
                bell(1046.50, 0.16, amplitude=0.55, start=0.070),
            ],
            "screen_off": [bell(523.25, 0.18)],
        },
    },
    "pulse": {
        "name": "Pulse",
        "version": "1.0.0",
        "description": (
            "A softer, lower triangle-wave set. Short woody taps for clicks and "
            "focus, with gentle falling and rising pairs for gestures, charging "
            "and screen changes. Designed to sit under screen-reader speech."
        ),
        "events": {
            "click": [pulse(440.00, 0.08)],
            "view_enter": [pulse(349.23, 0.10)],
            "view_exit": [pulse(293.66, 0.09)],
            "focus_interactive": [pulse(392.00, 0.09)],
            "focus_non_interactive": [pulse(329.63, 0.08)],
            "long_click": [pulse(220.00, 0.22)],
            "scroll": [pulse(493.88, 0.06)],
            "gesture_begin": [pulse(261.63, 0.10), pulse(349.23, 0.10, start=0.070)],
            "gesture_end": [pulse(349.23, 0.10), pulse(261.63, 0.12, start=0.070)],
            "select": [pulse(523.25, 0.11)],
            "window_state": [
                pulse(196.00, 0.18, amplitude=0.55),
                pulse(261.63, 0.18, amplitude=0.55),
            ],
            "charger_plugged": [pulse(293.66, 0.10), pulse(440.00, 0.14, start=0.090)],
            "charger_unplugged": [pulse(440.00, 0.10), pulse(293.66, 0.14, start=0.090)],
            "screen_on": [
                pulse(392.00, 0.12, amplitude=0.55),
                pulse(523.25, 0.16, amplitude=0.55, start=0.080),
            ],
            "screen_off": [pulse(196.00, 0.20)],
        },
    },
}

BELL_PARTIALS = ((1.0, 1.00, 5.0), (2.01, 0.42, 7.0), (2.99, 0.22, 9.5), (4.07, 0.10, 12.0))
PULSE_PARTIALS = ((1.0, 1.00), (3.0, 1.0 / 9.0), (5.0, 1.0 / 25.0), (7.0, 1.0 / 49.0))


def _envelope(age: float, duration: float, attack: float, decay: float) -> float:
    if age < 0.0:
        return 0.0
    value = math.exp(-decay * age)
    if age < attack:
        value *= age / attack
    release = 0.014
    remaining = duration - age
    if remaining < release:
        value *= max(0.0, remaining / release)
    return value


def render(notes: list[Note]) -> bytes:
    total = max(start + duration for _, _, start, duration, _ in notes) + 0.02
    frames = int(total * SAMPLE_RATE)
    samples = [0.0] * frames

    for kind, freq, start, duration, amplitude in notes:
        offset = int(start * SAMPLE_RATE)
        count = int(duration * SAMPLE_RATE)
        for index in range(count):
            age = index / SAMPLE_RATE
            if kind == "bell":
                value = 0.0
                for ratio, level, decay in BELL_PARTIALS:
                    value += level * math.sin(2 * math.pi * freq * ratio * age) * math.exp(
                        -decay * age
                    )
                value *= _envelope(age, duration, 0.003, 0.0)
            else:
                value = 0.0
                for harmonic, level in PULSE_PARTIALS:
                    value += level * math.sin(2 * math.pi * freq * harmonic * age)
                value *= _envelope(age, duration, 0.012, 6.0)
            position = offset + index
            if 0 <= position < frames:
                samples[position] += amplitude * value

    peak = max((abs(value) for value in samples), default=0.0)
    scale = (0.85 / peak) if peak > 0 else 1.0
    pcm = bytearray()
    for value in samples:
        pcm += struct.pack("<h", int(max(-1.0, min(1.0, value * scale)) * 32767))
    return bytes(pcm)


def write_wav(data: bytes) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(data)
    return buffer.getvalue()


def build_theme(theme_id: str, theme: dict) -> Path:
    manifest = {
        "schema": 1,
        "id": theme_id,
        "name": theme["name"],
        "author": AUTHOR,
        "description": theme["description"],
        "version": theme["version"],
        "license": LICENSE,
        "sounds": {},
    }

    target = OUTPUT_DIR / f"{theme_id}-{theme['version']}.audextheme"
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for event, notes in theme["events"].items():
            entry = f"sounds/{event}.wav"
            info = zipfile.ZipInfo(entry, date_time=(2026, 10, 23, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, write_wav(render(notes)))
            manifest["sounds"][event] = entry

        info = zipfile.ZipInfo("theme.json", date_time=(2026, 10, 23, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        archive.writestr(info, json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")

    return target


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for theme_id, theme in THEMES.items():
        path = build_theme(theme_id, theme)
        print(f"wrote {path.relative_to(STORE_ROOT)} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
