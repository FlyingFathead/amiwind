# AmiWind v0.0.21-dev1 — opening and UI playtest

Development checkpoint; not a completed Morrowind implementation.

## Included

- UI defaults to 14 px. Options retains 16, 14, 12 px and the readable fallback.
  The main-menu panel is smaller and lower, with bounds and mouse rows derived
  from the selected font. All existing font assets remain available. Archived
  options reload from config.cfg after an ordinary quit; emulator termination
  does not guarantee that settings were written.
- Dock guard travel, original speech gates and a race/sex/face/hair picker with
  a rotating mesh head. Owned-data conversion produced 10 races, 21 classes,
  13 birthsigns and 275 head/hair parts.
- Census and Excise interior, Socucius Ergalla, the hall guard and Sellus Gravius;
  class list, birthsign artwork, complete attribute/skill review, papers reader,
  tutorial ring, duties/package checks and release adapters.
- 22 authored, rotated collision-only opening barriers, conditioned on
  CharGenState. Numeric globals, journal indices and inventory counts have
  distinct records. NPC script locals remain separate. Receiving the package
  checks the journal index, so losing an item cannot repeat the gold reward.
- Bounded AWS1 save format with stable character/content IDs, stats, numeric
  state, relevant opening changes and actor positions/greeting state. Save/load
  is available after registration and release. F5 quicksaves; F9 quickloads.
  The keyboard browser groups saves by character: arrows, Enter, Esc.
  Four manual slots and one quicksave; autosave history defaults to 3 and is
  adjustable from off to 16. Each logical slot has two validated generations.
- Original parchment/book font conversion and initial papers/directions pages;
  bounded, nonrecursive player-name/race/class substitutions. Owned source
  fonts, artwork, dialogue and ROMs are confined to private conversion outputs.

## Scope and remaining work

This is an opening-specific adapter over numeric game facts, not a complete
Morrowind script interpreter or general dialogue-condition evaluator. Class quiz
and custom classes, complete spell/effect execution, unlocked dialogue topics,
full inventory/container UI, arbitrary books/HTML and race-matched player hands
remain unfinished. Hands currently retain the Nord appearance. The tutorial
barrel has a direct ring action. Captain conversation uses a small reader flow;
its repeat conversations and exact paper-removal timing need further work.

The save schema is bounded (32 IDs per global/journal/item category, 64 actor
records, 16 KiB encoded maximum). It covers this implemented slice, not all
Morrowind world mechanics. Named manual slots, play-time/thumbnails, general
reference deltas, expanded persistence and controlled original ESS comparisons
remain planned. It neither reads nor writes Bethesda ESS/OpenMW saves. Saves
are content-fingerprinted and may be rejected after a development asset change.

Natural uninterrupted ship-to-release playthrough, all appearance combinations,
all barrier escape routes, sustained memory measurements and interrupted/full
Amiga-disk save recovery remain acceptance work. Debug-assisted component checks
must not be presented as a completed natural playthrough.

Both reported FS-UAE 3.1.66 intermittent freezes remain open. The missing Silt
Strider/driver remain unimplemented content; malformed port geometry is separate.

Compiler warnings are reviewed on every native build. The current warning
baseline is 93; new warnings block packaging until reviewed and fixed or recorded.
See the private build evidence for the exact binary/image hashes and test results.

## Build checks

- Native 68040 build: 93 warnings, no new messages against the reviewed baseline.
- Host suite: 209 tests passed, including malformed character/preview input,
  conditional quest state, stat construction, save truncation/CRC rejection,
  rotated barriers, retained mixer/debug behavior and menu interaction.
- Clean FFS/RDB HDF: all 477 payload files read back and matched byte hashes.
- FS-UAE 3.1.66: main-menu layout and rotating appearance selection checked;
  class/birthsign/review, papers/ring/duties/release and one 1,776-byte
  quicksave/quickload checked on the preceding runtime via debug-assisted
  travel. Final fixes include narrower entrance search steps, full UI redraw and
  correct symbol-font conversion. Exact coverage is in the private evidence.
