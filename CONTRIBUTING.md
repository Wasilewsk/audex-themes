# Contributing a theme

Thanks for making Audex Revival sound better. This repository is the store: a
theme is one zip package in `themes/` plus an entry in `index.json`.

## 1. Build the sounds

Use **Audex Revival → Settings → Event settings → Custom** to assign an audio
file to each event. Then choose **Share as theme** and save the `.audextheme`
package. The app warns you if some events are missing; missing events fall back
to Innovex.

You can also assemble a package by hand. The format is documented in
[README.md](README.md#package-format) and
[`schema/theme.schema.json`](schema/theme.schema.json).

Guidelines:

- Keep feedback short — under a second for clicks, focus and scrolling. Long
  sounds overlap speech and other feedback.
- Test with TalkBack or another screen reader. Feedback should complement
  speech, not cover it.
- Make events distinguishable without being startling. Avoid sudden loud
  transients and long silence at the start of a file.
- Do not use audio you do not have the right to redistribute. Say which license
  applies in `theme.json`; CC0-1.0 and CC-BY-4.0 are welcome, "all rights
  reserved" is not.

## 2. Add the package

Name the file `<id>-<version>.audextheme`, for example
`warm-chime-1.0.0.audextheme`, and place it in `themes/`.

The manifest's `id` must match the file name. To update an existing theme, bump
`version` and replace the file rather than adding a second package with the same
id — the store keeps one current version per theme.

## 3. Rebuild the index

```bash
python3 tools/build_index.py
```

This validates every package (zip safety, manifest fields, audio headers,
duration and size limits) and rewrites `index.json`. Commit the package and the
index together.

## 4. Open a pull request

Run `python3 tools/build_index.py --check` before pushing. GitHub Actions runs
the same check on the pull request; a maintainer listens to the audio and checks
the license before merging. Merged themes are available in the app immediately
after the index update, no app release needed.

## Review criteria

- All audio is original or licensed for redistribution.
- The manifest is accurate: name, author, description, license, version.
- Sounds are usable at the app's default volume and do not clip.
- The theme is not a duplicate of an existing one and has no offensive content.
- The package passes validation and the index is current.

## Updating or removing a theme

Open a pull request with the new package and regenerated index. To remove a
theme, delete its package, run `python3 tools/build_index.py`, and explain why
in the pull request. Running installations keep working offline; the app simply
stops offering it.
