# AmiWind v0.0.23-dev4 — dialogue and startup regression checkpoint

Based on published dev3, commit `7e36e9051da477147f78cf22236a0a4c0c7201ae`.
Owner publishing remains through the supplied guarded apply/publish helper.
Only public source archives and checksums belong on GitHub; the playtests contain
owned game data and a ROM and remain private.

## Changes

- Default dialogue layout measures the widest wrapped line and the complete
  visible glyph bounds, centers every line and adds eight pixels on all sides.
  The box is centered horizontally and keeps the bottom anchor. One-line replies
  get a small box; longer speech wraps and pages. No per-frame heap allocation.
  `dbg ui layout 1/2/3` selects legacy, centered full-width or content-sized
  (default). Archived parameter: `aw_dialogue_box_layout`. Existing speaker-name
  methods and aim-only voice identity remain independent. Lower HUD hints/bars
  stay covered during dialogue, avoiding partial labels beside narrow boxes.
- Opening sampled speech supports the nearby aiming label. Name-entry prompts
  and character selectors suppress it. The caret is a drawn vertical line;
  the appearance preview says `LMB: rotate`, matching its existing click action.
- Startup branding fades in for two seconds, holds five, fades out for one.
  Theme streaming starts at the fade and continues into the menu without reopening
  the track or clearing buffered audio. Space/Enter/Esc skip branding; Esc skips
  the owned intro video.
- Optional `--intro-captions /private/cards.json` on `build.sh` or `build_aga.py
  image` converts the first supplied quote into a runtime-switchable overlay.
  `aw_intro_text_overlay 1` uses it (default); `0` keeps original video pixels.
  The playtests include the owner's opening quote at 0.5–7 seconds. Other title
  cards and original movie PCM stay untouched. The sidecar is 64,784 bytes, loaded
  once for the movie and freed afterward; the Amiga does no font rasterization.
- Tree sprite pixels over the background retain a signed depth comparison.
  Nearer opaque scenery still occludes them; transparent pixels write no depth.
- NPC floor placement runs after static scenery is linked. Darvame stands on the
  port platform, retaining original x/y, appearance and greeting data. NPCs become
  solid immediately after this placement. No fabricated source relocation.

## Validation

262 host tests pass, including production sprite rasterization (failure before
fix), dialogue box geometry, short final pages, opening-card bounds/toggle,
branding skip keys, and title-stream continuity. Native compilation uses six
workers and retains the same 87 baseline warnings, with no new diagnostics.

Both TTF and no-TTF UI assets are converted during image assembly. Complete
payloads are read back from the finished HDFs. Final images are boot-tested in
FS-UAE through logo/menu, readable opening quote, blank ship transition, dialogue,
vertical name caret and F1 help. The full logo reports approximately eight seconds.
Music events show one title-track opening across branding and menu.

Native camera checks cover the reported tree position, both previously reported
house views, the corrected port rock, and Darvame on the platform. Host tests also
cover occlusion and alpha depth. No surface/edge overflow was reported in that
focused scene run. This does not certify every viewpoint or physical Amiga speed.

All dev3 maps, actor conversions, low-poly rocks, soundtrack and the once-only
-5 dB boat-hull sample are reused. The engine and QuakeC are freshly compiled;
fonts, logo and opening quote are rebuilt. This is not a claim of a complete new
Steam installation test: the two variants use the supplied owned data with and
without its usable TTF files. Prefer TTF for reading and dialogue.

## Still open

Deck/pier sideways escape, complete NPC conversation-facing and voice conditions,
interior door squeaks/animation, Strider travel service, sky/daylight/weather,
NPC schedules, rest recovery, bitmap-paper quality, earlier freeze observations,
and exhaustive interior floor/door acceptance. Owner confirms the port rock fix;
keep that distinction from these remaining issues.

Feedback and diagnosis: [dev3 tester notes](FEEDBACK-v0.0.23-dev3.md).
Controls: [dialogue and waiting](DIALOGUE_AND_WAIT.md).
