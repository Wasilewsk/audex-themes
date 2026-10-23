# Audex Revival theme store

[![Validate theme store](https://github.com/Wasilewsk/audex-themes/actions/workflows/validate.yml/badge.svg)](https://github.com/Wasilewsk/audex-themes/actions/workflows/validate.yml)

Community sound themes for [Audex Revival](https://github.com/Wasilewsk/audex-revival), the
accessible sound-feedback app for blind and low-vision Android users.

The store is just this GitHub repository. The app reads
[`index.json`](index.json) over HTTPS, lists the themes below, and downloads the
package you choose. There is no server, account, or tracking.

## Themes

| Theme | Author | Sounds | Description |
| --- | --- | --- | --- |
| **Chime** | Audex Revival | 15 | Bright struck-bell tones; C6 clicks and rising two-note cues. |
| **Pulse** | Audex Revival | 15 | Softer, lower triangle-wave taps that sit under speech. |

Both demo themes are original synthesis released under CC0-1.0.

## Install from the app

1. Open **Audex Revival → Theme store**.
2. Pick a theme and choose **Install**.
3. Choose **Apply** to make it the active sound scheme.

Installed themes appear in the sound-scheme picker on the main settings and
event screens. Removing a theme that is in use falls back to the built-in
Innovex scheme.

## Submit a theme

The fastest path is from the app itself:

1. Open **Settings → Event settings**, choose the **Custom** scheme, and assign
   the sounds you want for each event.
2. Choose **Share as theme**, enter a name, author and description, and save the
   `.audextheme` package.
3. Share the file anywhere, then open
   [the upload page](https://github.com/Wasilewsk/audex-themes/upload/main/themes)
   and add it to `themes/`.
4. Clone the repository locally, run `python3 tools/build_index.py`, and commit
   the regenerated `index.json` with your package.
5. Run `python3 tools/build_index.py --check`, then open a pull request.
   GitHub Actions runs the same validation on the pull request, and a maintainer
   reviews the audio before merging.

If you prefer to build a package by hand, see [CONTRIBUTING.md](CONTRIBUTING.md)
and [`schema/theme.schema.json`](schema/theme.schema.json).

## Package format

A `.audextheme` file is a zip archive:

```
theme.json
sounds/click.wav
sounds/view_enter.wav
...
```

`theme.json`:

```json
{
  "schema": 1,
  "id": "warm-chime",
  "name": "Warm Chime",
  "author": "Your name",
  "description": "One or two sentences shown in the store.",
  "version": "1.0.0",
  "license": "CC0-1.0",
  "sounds": {
    "click": "sounds/click.wav",
    "view_enter": "sounds/view_enter.wav",
    "view_exit": "sounds/view_exit.wav",
    "focus_interactive": "sounds/focus_interactive.wav",
    "focus_non_interactive": "sounds/focus_non_interactive.wav",
    "long_click": "sounds/long_click.wav",
    "scroll": "sounds/scroll.wav",
    "gesture_begin": "sounds/gesture_begin.wav",
    "gesture_end": "sounds/gesture_end.wav",
    "select": "sounds/select.wav",
    "window_state": "sounds/window_state.wav",
    "charger_plugged": "sounds/charger_plugged.wav",
    "charger_unplugged": "sounds/charger_unplugged.wav",
    "screen_on": "sounds/screen_on.wav",
    "screen_off": "sounds/screen_off.wav"
  }
}
```

- Accepted audio: PCM WAV, OGG, MP3, MIDI (`.mid`) or M4A, up to 2 MiB and
  10 seconds per sound.
- `click` is required. Any event you leave out falls back to Innovex, so partial
  themes are allowed — but all 15 is a better experience.
- Packages are limited to 8 MiB zipped / 20 MiB unpacked and 40 files.
- ids are lowercase slugs (`^[a-z0-9][a-z0-9-]{1,31}$`); versions look like
  `1.0.0`. The package must be named `<id>-<version>.audextheme`.
- Audio must be original or properly licensed. State the license in the
  manifest; CC0-1.0 or CC-BY-4.0 are good choices for sound packs.

## Validate locally

```bash
python3 tools/build_index.py --check   # validates packages and the index
python3 tools/build_index.py           # regenerates index.json
```

## Safety

The app only downloads from `raw.githubusercontent.com`, requires HTTPS,
verifies the SHA-256 in the index, rejects path traversal and unexpected files,
and never executes package contents. Themes are audio and metadata only.

## License

Tooling and documentation are MIT. Each theme carries its own license in
`theme.json`; the two demo themes are CC0-1.0.
