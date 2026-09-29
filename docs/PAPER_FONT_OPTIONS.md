# Paper font conversion options

The preferred Magic Cards TTF path remains unchanged. The bitmap paper correction
is a separate build choice, not storefront detection or a global font filter.

## Selection and defaults

| Actual reading source | Default | With `--bitmap-paper-ink original` |
| --- | --- | --- |
| Usable BookArt/Magic Cards.ttf | Existing TTF conversion | Same TTF conversion |
| Missing/unusable TTF, complete Bethesda FNT+TEX pair | Filled paper candidate | Original bitmap paper rendering |
| Neither source usable | Clear build error | Clear build error |

Both bitmap modes leave dialogue and menu glyphs unchanged, including the 12px
small-text character UI. TTF parsing failures are reported before the same bitmap
fallback is used. Output errors such as a full disk remain build failures.

## Font-source selection

Selection is automatic in both the guided build and native-image assembly.
A usable TTF wins; otherwise the complete corresponding FNT/TEX pair is used.
There is no `--font-source` switch in this checkpoint. `--bitmap-paper-ink`
controls bitmap paper coverage only and does not force the bitmap path when a
usable TTF exists. Testing a bitmap-only installation requires a separate input
copy without the loose BookArt TTFs; keep the owned installation unchanged.

## Command line and JSON

Append either option to the normal guided build command:

```sh
./build.sh --bitmap-paper-ink filled
./build.sh --bitmap-paper-ink original
```

These examples show the option only; existing data/workspace/tool options are
still required in noninteractive builds. The standalone reading stage accepts
the same switches.

The shipped default is in `config/build-defaults.json`:

```json
{
  "bitmap_paper_ink": "filled"
}
```

An external JSON file can override that default without editing public source:

```sh
./build.sh --build-config /path/to/local-build.json
```

Precedence is CLI > selected JSON > shipped defaults. This checkpoint's JSON
schema accepts only `bitmap_paper_ink`; unknown keys, malformed JSON and invalid
values fail before setup/build execution. A selected empty object inherits the
shipped value. This is a build-time option, not an in-game console toggle.

## Exact approved treatment

The original BOX resampling, glyph dimensions, bearings, advances and three-shade
AWF1 packing remain unchanged. After resampling, filled mode assigns coverage
0/85/170/255 at alpha cutoffs 43/80/190. The transparent cutoff stays at 43,
matching original mode; medium and solid ink are selected earlier. All 256
input-alpha values are checked by a synthetic test.
It does not dilate glyphs, close counters or alter line wrapping. The
nearest-neighbour operation used in the review image enlarged the preview only;
it is not the conversion correction.

The reading stage writes the filled candidate as private `gfx/paper12.awf`.
Native paper rendering prefers that optional asset. Normal `book12.awf` and
`magic12.awf` remain the small-UI sources, so character menus do not inherit the
correction. TTF/original builds omit the paper candidate. A rerun removes only
stale generated book/paper assets owned by this conversion stage; original game
files and ordinary UI assets are not changed.

A paper-specific font is loaded once on first paper use. Its allocation is the
actual validated byte count, bounded by the existing font capacity; the supplied
Magic Cards candidate is 4,535 bytes, plus allocator overhead. No new allocation
is made when the asset is absent. Missing, invalid or unallocatable candidates
retain the original reading font and cannot break the dialogue/menu font cache.
This resident cache lasts for the process lifetime, like the existing UI caches.

The build prints the effective source, treatment and runtime asset. The private
`gfx/paper-font-conversion.json` records input/output hashes and the requested and
effective mode. The top-level build receipt records the resolved setting and
config-file hashes. These records are local build outputs, not public game assets.

## Validation scope

Synthetic tests exercise defaults, JSON/CLI precedence, invalid values, TTF
preference, failed-TTF fallback, missing sources, stale-output cleanup, unchanged
UI bytes and unchanged metrics. The actual native C UI is compiled for the host
with undefined-behavior checks and synthetic font files: candidate isolation,
cache reuse and missing/corrupt/wrong-size/truncated/oversized/allocation-failure
fallbacks are checked. This is not a physical Amiga or emulator playtest.

Private tests on the supplied font sources preserve all 256 metrics. The
preview title and four body lines match the approved two-times-enlarged candidate
pixel-for-pixel in a host-side comparison. All twelve ordinary bitmap family/size outputs
remain byte-identical to dev5. No source or converted font files are distributed.
