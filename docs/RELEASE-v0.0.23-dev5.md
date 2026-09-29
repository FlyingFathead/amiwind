# AmiWind v0.0.23-dev5: flat windows, dialogue and console

This checkpoint targets dev4's slow façade views, cramped speech layout and lost
full-height console. It retains the original owned inputs and full-detail rebuild
option. The public release contains source only; game assets and ROM stay private.

## Changes

- Host-side decorative-window flattening, enabled for the two Nord window types:
  source textures are depth-baked to flat panels and mounted against the supporting
  house wall. All 21 selected instances retain original collision. Change
  `decorative_windows.flatten` in `config/surface-flattening.json` to rebuild with
  original geometry. This is a conversion option, not a runtime toggle.
- One BSP face per selected window, previously 145 or 123. Matched-camera median
  frame time improved from 86.425 to 77.619 ms in the reference emulator. Remaining
  façade detail still costs time; this is not an all-exterior performance fix.
- Frame-local far-visibility caching; the visibility rule itself is unchanged.
- Sentence-aware subtitle pages and page-length-weighted timing, with word-wrap
  fallback for sentences too large for a page. Painted glyph bounds determine
  vertical centering, including the two-line follow-guard prompt.
- Names default below the viewport, above Talk: E, with intro aim labels suppressed.
  Speaker name stays out of the speech box; alternative styles remain selectable.
- F10 cycles half/full/closed console; Escape closes directly. F1 states the cycle.
  Both bare `dbg` and `debug` display help.
- `intro_docks_variant 2` selects a smaller derived exterior during creation.
  Variant 1 retains the full scene. Distant draw references are removed and a
  boundary hull contains the patch; full-route acceptance remains open.

## Verification and limits

Six-worker native engine compile succeeds. Both TTF and bitmap HDFs have every
payload file independently read back and hash-compared. Bitmap paper ink remains
filled. Native checks cover the two reported façade viewpoints, target-name
placement, F10 console sizes, F1 help, bare dbg help and the ship name-entry caret.
Host tests cover paging, centering, converter off/on, mounting, unchanged source
geometry and console behaviour. No physical Amiga or Windows validation claimed.

Private map delivery reuses dev4 assets and collision, replaces window visuals,
and adds the derived dock scene; unused old face records remain resident. A full
source rebuild emits the simplified visuals directly. Font assets reuse verified
owned inputs. No new independent Steam/GOG installation audit is claimed.

Still open: the reported parchment appearance issue, complete dock-route acceptance,
full NPC voice behaviour and services, Darvame travel, door sound/animation, wider
house-detail optimization and exhaustive interior collision acceptance. Existing
clock/wait support is retained; sun/sky/weather work remains separate.

See [dev4 feedback](FEEDBACK-v0.0.23-dev4.md), [mesh findings](MESH_TIPS_AND_TRICKS.md)
and [the dated roadmap](PLAN-2026-09-29.md).
