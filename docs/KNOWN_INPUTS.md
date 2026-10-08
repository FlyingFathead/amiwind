# Known inputs: which files did the builder get?

The builder converts files you supply: your Morrowind data, optionally your own Amiga
FPU support libraries (`--amiga-libs`) and your Kickstart ROM (`--kickstart-file`).
At the start of every build it identifies each of them by size, SHA-256 and the version
written inside the file, and compares them with a table of builds that are known and
tested: [`config/known-inputs.json`](../config/known-inputs.json). The table holds
metadata only (name, size, version, SHA-256, source label, notes), never file contents.
One shared implementation does this for every kind of input: `tools/known_inputs.py`
(BUILD-INPUTS-UNVERIFIED-32).

## Verdicts

| Verdict | Meaning | What the builder does |
| --- | --- | --- |
| `known: <source> (tested)` | size and SHA-256 match a table entry | uses it |
| `unknown version of <name> v<version> (patched or modded? not tested; used)` | a readable file of the right kind that is not in the table | uses it, with a warning |
| `unknown build of <name> v<version> (not tested; used)` | the same, for an Amiga library | uses it, with a warning |
| `invalid: ... (not used)` | not that kind of file, or its version cannot be read | never uses it; a missing or invalid `Morrowind.esm`/`.bsa` stops the build |
| `unchecked` | `--check-hashes off` | uses it without verification (loud warning) |

What is read as the version:

- **Morrowind masters** (`Morrowind.esm`, `Tribunal.esm`, `Bloodmoon.esm`): the TES3
  header record (`HEDR`): format version, author, description, record count and the
  masters it needs.
- **Morrowind archives** (`.bsa`): the archive header (version `$100`, file count).
- **Amiga libraries**: the file is loaded as an AmigaDOS hunk executable (hunks and
  relocations), the resident library structure (RomTag, `RTC_MATCHWORD` with a
  relocated pointer to itself) gives the name and `rt_Version`; the revision comes
  from the library's initialisation data table when it sets one, otherwise from the
  `V.R` in the RomTag id string or the `$VER:` string. The resident name must match the
  file name, because exec opens libraries by that name.
- **Kickstart ROM**: a 256/512 KiB image with the `$1111`/`$1114` start word
  (version.revision at offset 12), or an Amiga Forever encrypted image. The ROM verdict
  is information only; the FS-UAE launcher checks the ROM too.

## Policies

`--game-data-policy` (Morrowind files) and `--amiga-libs-policy` (`--amiga-libs`)
take one of:

- `warn` (default): unknown files are used with a warning; invalid files are not used
  (an invalid required file stops the build).
- `fail`: as `warn`, but any invalid file stops the build.
- `require-known`: only known files pass; anything else stops the build.

The existing reference check of the installation still runs as before
([Game inputs and editions](BUILD_DEPENDENCIES.md#game-inputs-and-editions)): an
installation whose `Morrowind.esm`/`.bsa` differ from the reference stops unless
`--allow-data-differences` is given. The known-inputs verdict adds the name of the
edition and covers the expansion files, the Amiga libraries and the ROM.

## Editions

The masters of the GOG and Steam Game of the Year editions are byte-identical, so the
builder names the edition from the masters plus the three TrueType fonts in
`Data Files/BookArt`: `Game of the Year edition (GOG, reference)` when they are there,
`Game of the Year edition (Steam: bitmap fonts)` when they are not. Both are supported;
neither is a warning. The report also says which font source each family used and how
many loose files shadow a copy inside `Morrowind.bsa` (loose files override the archive
in several steps). Details: [Morrowind editions](MORROWIND_EDITIONS.md),
BUILD-EDITION-DIFFERENCES-32.

## Where the verdicts are recorded

- printed at the start of the build;
- `known_inputs` in the run's `build-state.json` and in `build-summary.json`, and the
  end-of-build summary (edition, font sources, loose overrides, one line per file);
- Amiga libraries also in `image/fpu-support.json`, `fpu_support` of
  `image/build.json` and the `FPU support library:` summary lines
  ([FPU support library](FPU_SUPPORT_LIBRARY.md#known-versions)).

## Input lock and `--check-hashes`

The build workspace keeps a private lock file, `amiwind-inputs.lock` (JSON, never
shipped or shared): for every input its path, size, modification time (nanoseconds),
birth time where the platform really provides one, SHA-256, verdict and the revision of
the known table it was judged against. It is the one place input hashes come from in a
build: the reference check, the build receipt and the cache checks of later steps (for
example the town importer's `Morrowind.esm` check) all read it, so no input is hashed
twice. Later steps find it through the `AMIWIND_INPUTS_LOCK` environment variable.

| `--check-hashes` | What is hashed |
| --- | --- |
| `core` (default) | the masters and archives, the Amiga libraries and the ROM are hashed in full on every build; the large loose set (music, sound, fonts, video...) is trusted when size, modification time and birth time are unchanged, and rehashed when they differ |
| `full` | every input on every build: use it for release builds |
| `auto` | every input, core files too, is trusted when unchanged |
| `off` | nothing is hashed; inputs are `unchecked` and the summary warns loudly |

Files are statted and, where needed, hashed in parallel. A file whose size or times
changed is rehashed and verified again, with a message naming it. A lock that cannot be
read is moved aside (`amiwind-inputs.lock.unreadable-<time>`) and rebuilt.

Why the core files are always hashed: only a hash proves that a file is unchanged. Size
and times can prove a change but not its absence: a same-length edit, a copy that keeps
time stamps, an overwrite within the same time-stamp tick or a restore from backup can
all leave them as they were. Hashing the core files is cheap (measured on 8 October 2026
for the six Morrowind masters and archives plus three Amiga libraries, 588 MB):

| Where | Serial | Parallel |
| --- | ---: | ---: |
| Windows host, Python, files in the OS cache | 0.53 s | 0.28 s |
| Linux container reading a Windows folder through a bind mount | 3.8-4.1 s | 2.7 s |

The whole loose set of a GOG installation (about 21,000 files, 1.29 GB with the videos)
took 7.4 s on the host and 26 s through the bind mount; only statting it took 0.6 s and
7.0 s. That is why the loose set uses the size-and-time fast path by default.

Birth time: on Windows the creation time; on macOS and BSD `st_birthtime`. On Linux
Python's `os.stat` does not read the `statx` birth time, and `st_ctime` there is the
inode change time, not a creation time, so Linux records `null`; Docker bind mounts can
hide it too. A `null` birth time on either side is ignored when comparing.

## Adding a known build

Add an entry to `config/known-inputs.json` with `kind` (`tes3-master`,
`tes3-archive`, `amiga-library`, `kickstart-rom`), `name`, `bytes`, `sha256`,
`version` (as the builder reads it), `source` (where the file comes from: release,
store, accelerator vendor, community build), `tested` and `notes`; raise `revision`.
Never add file contents. The repository test checks the schema and that no repository
file is one of the listed inputs.
