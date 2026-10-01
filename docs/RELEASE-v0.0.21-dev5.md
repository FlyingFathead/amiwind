# AmiWind v0.0.21-dev5 — GOG TTF preference and Steam font fallback

Dev5 preserves the v0.0.21-dev4 gameplay and world-mapping checkpoint. This is a
host-side build/input compatibility update prompted by the first reported Steam
GOTY build failure at stage 13 (`reading`).

## Font-source policy

**GOG GOTY is the preferred AmiWind source installation.** The GOG layout used
for AmiWind development includes three loose TrueType sources under `BookArt/`:
`Magic Cards.ttf`, `GOTHIC.TTF` (Century Gothic) and `daedric_runes.ttf`.
TrueType outlines give the offline converter a better starting point when AmiWind
needs 16, 14 or 12 px rasterizations.

Steam GOTY normally lacks those loose TTFs but provides Bethesda's standard
`Fonts/*.fnt` + `.tex` font data. Dev4 accidentally treated `BookArt/` as if it
had to exist while preparing reading assets. Dev5 makes source selection explicit:

1. Prefer the matching loose TTF when present.
2. Otherwise use the matching Bethesda FNT+TEX pair.
3. Warn which preferred assets were absent, which fallback was selected, that
   visual results may vary or be inferior at scaled/non-native sizes, and link
   the preferred GOG GOTY edition.
4. Fail only when a font required by the current UI has no usable source.

GOG GOTY: <https://www.gog.com/en/game/the_elder_scrolls_iii_morrowind_goty_edition>

The converter emits 16/14/12 AWF variants for Magic Cards, Century Gothic,
Century Gothic Big and Daedric when usable source data exists. `GOTHIC.TTF`
identifies itself as Century Gothic and is the vector source for both Century
Gothic variants. A preferred TTF that cannot fit AmiWind's native AWF limits is
not clipped silently: that family falls back to its Bethesda bitmap source and
the converter reports the reason.

## Regression addressed

Dev4's `tools/prepare_reading.py` called `child_ci(data_files, 'BookArt')` as a
required lookup while only catching `FileNotFoundError`. `child_ci()` reports a
missing required child as `ValueError`, so a valid Steam GOTY tree without
`Data Files/BookArt` aborted before the intended bitmap/runtime fallback could
be used.

Dev5 removes that exception mismatch and shares explicit font capability
detection between preflight, UI conversion and reading preparation.

## Validation

Completed in the source workspace:

- Public-source allowlist/package inspection passes.
- 3/3 new font-source regression tests pass.
- 48/48 focused build/setup/release/repository tests pass.
- The owner-supplied GOG font archives were exercised directly: Magic Cards and
  Century Gothic use their preferred TTF paths at 16/14/12 px. The supplied
  Daedric TTF contains glyph metrics outside the current native AWF limits, so
  dev5 reports that condition and safely uses the matching Bethesda bitmap font.
- The same owner-supplied Bethesda `Fonts/` set was exercised in a Steam-shaped
  tree with no `BookArt/`; all four font families convert through FNT+TEX fallback
  at 16/14/12 px.
- Full host discovery reached 216 passing and 2 skipped tests. Two unrelated
  environment/baseline errors remain in this container: `fast_simplification` is
  not installed, and Python 3.13 exposes an existing mocked
  `os.process_cpu_count()` OSError path in `test_build_jobs`. These are not dev5
  font-patch failures and were not changed in this compatibility update.

A complete real Steam GOTY conversion has **not** been claimed from this sandbox.
The next acceptance step is the owner's requested build from a separate
`/path/to/workspace/tmp_amiwind_steam_compile/` source tree against the actual Steam
installation.

No gameplay, save-format or native renderer change is claimed relative to dev4.
