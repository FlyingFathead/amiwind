# Installed Morrowind game inputs

Point `--data-files` at the installed game's `Data Files` directory or its
installation root. The builder locates the named `Morrowind.esm` and
`Morrowind.bsa` pair beneath that root. Use your own installed game files.

For example, a GOG installation may use `C:\GOG Games\Morrowind\` as its
installation root. That is an example, not a required drive or location.
The paths below are relative to that root; no workstation or account-specific
path is required.

| Relative path | Contents and current build use |
| --- | --- |
| `Data Files/Morrowind.esm` | Base-game master; required. |
| `Data Files/Morrowind.bsa` | Base-game asset archive; required. |
| `Data Files/Tribunal.esm`, `Data Files/Tribunal.bsa` | Expansion files may be present; the current base-game conversion does not load them. |
| `Data Files/Bloodmoon.esm`, `Data Files/Bloodmoon.bsa` | Expansion files may be present; the current base-game conversion does not load them. |
| `Data Files/BookArt/` | Book artwork and, in the development GOG installation, loose TrueType font extras. |
| `Data Files/Fonts/` | Original `.fnt` and `.tex` bitmap fonts. |
| `Data Files/Icons/` | Item icon groups such as `a/`, `c/`, `k/`, `l/`, `m/`, `n/`, `s/`, `w/`. |
| `Data Files/Meshes/` | NIF meshes in groups such as `a/`, `b/`, `d/`, `f/`, `i/`, `x/`; other groups and root meshes may be present. |
| `Data Files/Music/` | `Battle/`, `Explore/`, `Special/`. |
| `Data Files/Sound/Cr/` | Creature sound groups. |
| `Data Files/Sound/Fx/` | Effects, including environment, footsteps, interactions, items, magic and transitions. |
| `Data Files/Sound/Vo/` | Voice groups, commonly with `f/` and `m/` subdirectories; miscellaneous groups also exist. |
| `Data Files/Splash/` | Loading artwork. |
| `Data Files/Textures/` | Textures, including groups such as `Birthsigns/`, `levelup/`, `magicitem/`, `NVWater/`, `water/`. |
| `Data Files/Video/` | The base-game intro is `mw_intro.bik`. |

The `.esm` and `.bsa` files sit directly inside `Data Files/`, alongside the
asset directories. They are not inside `Meshes/`, `Textures/` or another nested
asset directory. Installations can differ in loose-file contents and casing;
supported meshes and textures may also be read from `Morrowind.bsa`. This is a
layout example, not a requirement to extract every archive into loose files or
create every listed subdirectory.

## Transfer archives are separate

Files named `Morrowind_<asset type>.zip`, `morrowind_datafiles.zip` or similar
are private transfer containers used to move owned inputs between workspaces.
They are not part of the normal GOG or Steam installation. The builder neither
requires nor extracts them, and excludes unrelated transfer archives from game
input discovery and provenance hashing.

Never copy those transfer ZIPs into an AmiWind build, public repository or
release. Original game assets, converted game assets and ROMs also remain
private. Source releases contain project source and explicitly approved project
documentation/media only. See [Linux build instructions](LINUX_BUILD.md) and
[release workflow](RELEASE_WORKFLOW.md).
