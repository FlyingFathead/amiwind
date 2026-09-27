# Setup with an existing Morrowind installation

The user supplies original game data. No game downloads, installer execution or
account access happen in these tools. Install your purchased copy normally, then
point this project at its `Data Files` directory or its parent game directory.

A fresh install is unnecessary when the original base files are intact. For a
heavily modified installation, keep a separate clean copy of the base data to
make conversion results reproducible. This proof of concept does not merge
plugins, apply loose model/texture overrides or support replacement masters.

## Inputs

| Input | Current purpose |
| --- | --- |
| `Morrowind.esm` | Required: world records, terrain and placements |
| `Morrowind.bsa` | Required: direct model inventory |
| `Music/` | Inventoried; intended for later local audio conversion |
| `Sound/`, including `Sound/Vo/` | Inventoried; intended for later effects and speech |
| `Video/` | Unused in this prototype |
| Tribunal / Bloodmoon files | Unused; base Morrowind only |

The file lookup handles filename case differences. Audio inventory is optional
for the terrain experiment. Do not put any of these files inside the repository.

## Configure once, convert locally

```sh
python tools/mwad.py setup --data-files "/path/to/Morrowind/Data Files" --workspace "../morrowind-amiga-workspace" --target a500
python tools/mwad.py doctor --data-files "/path/to/Morrowind/Data Files"
python tools/mwad.py convert --workspace "../morrowind-amiga-workspace"
```

On Windows, a quoted path such as `D:/Games/Morrowind/Data Files` works with the
same commands. On Linux use `python3` if that is your Python command.

`setup` creates a new external workspace or updates an existing recognized
workspace. It remembers the absolute game path and selected target in the
external `workspace.json`. It does not copy, alter or upload the game files.
The target records hardware intent; no native target binary is built yet.

`convert` reads the configured installation and writes `generated/seyda-neen/`.
It exports the selected terrain and audit data, then verifies the packet stream.
Existing output directories are never overwritten. For another experiment:

```sh
python tools/mwad.py convert --workspace "../morrowind-amiga-workspace" --name seyda-coarse --stride 4
```

The default region is nine exterior cells around (-2, -9). `--center X Y`,
`--radius N` and `--stride 1|2|4|8` allow other experiments. Missing terrain in the
selected square is an error. Interior cells and plugin merging are unsupported.

## Optional PC preview

```sh
python -m pip install -e ".[preview]"
python tools/mwad.py preview "../morrowind-amiga-workspace/generated/seyda-neen" "../morrowind-amiga-workspace/previews/seyda-neen.png"
```

This inspection view uses analytical colours; it is not a target screenshot or
performance demonstration. Optional dependencies are NumPy and Matplotlib.
Installing the package also provides the `mwad` command as an alternative to
`python tools/mwad.py`.

## Lower-level tools

`audit --data-files PATH --out EXTERNAL_PATH` performs conversion without saved
workspace settings. `verify EXTERNAL_AREA` checks an existing packet stream.
`audit --dialogue-search TEXT` optionally finds dialogue text and voice-file
references, writing those results only to the external output.

`init-workspace PATH` creates an empty workspace without a game path. Run `setup`
afterward to configure it. `--help` lists all command options.
