# Weather, ashstorms, blight and NPC reactions: OpenMW source study

This note records source behavior observed in OpenMW at the pinned mirror commit
[`def941246531187d27cc8ceea8baf8b1894a994e`](https://github.com/OpenMW/openmw/commit/def941246531187d27cc8ceea8baf8b1894a994e), dated 5 September 2026.
[OpenMWâ€™s canonical project](https://gitlab.com/OpenMW/openmw) is on GitLab; the code links
below pin the corresponding public GitHub mirror revision for stable references.
These findings describe OpenMW code, not a claim of exact original-executable
parity or an implemented AmiWind weather system.

## Verified in the inspected OpenMW code

- **Weather selection is regional.** `RegionWeather::chooseNewWeather` rolls
  against cumulative probabilities for the current region; invalid totals fall
  back to clear weather. The weather manager obtains the player exterior cell's
  region and updates weather when region/timer conditions call for it. The
  inspected selection and transition path has no special Ghostfence boundary
  rule: the assigned exterior-cell region is the relevant input. See
  [`weather.cpp`, `RegionWeather::chooseNewWeather` and `WeatherManager::update`](https://github.com/OpenMW/openmw/blob/def941246531187d27cc8ceea8baf8b1894a994e/apps/openmw/mwworld/weather.cpp#L320-L339)
  [`WeatherManager::update` region/timer transition logic](https://github.com/OpenMW/openmw/blob/def941246531187d27cc8ceea8baf8b1894a994e/apps/openmw/mwworld/weather.cpp#L766-L817)
  and [the cell-to-weather update path in `worldimp.cpp`](https://github.com/OpenMW/openmw/blob/def941246531187d27cc8ceea8baf8b1894a994e/apps/openmw/mwworld/worldimp.cpp#L3055-L3067).
- **Ashstorm and blight are distinct weather types.** The weather store's
  ordered types include Ashstorm and Blight, each with configured effects.
  Their particle direction uses a hard-coded Red Mountain origin and points
  outward toward the player. A configured wind-speed threshold determines the
  storm state. See [`weather.cpp`, weather setup and wind/storm direction](https://github.com/OpenMW/openmw/blob/def941246531187d27cc8ceea8baf8b1894a994e/apps/openmw/mwworld/weather.cpp#L42-L55)
  and [weather type setup](https://github.com/OpenMW/openmw/blob/def941246531187d27cc8ceea8baf8b1894a994e/apps/openmw/mwworld/weather.cpp#L133-L174),
  plus [the weather-type table](https://github.com/OpenMW/openmw/blob/def941246531187d27cc8ceea8baf8b1894a994e/apps/openmw/mwworld/weather.cpp#L555-L579).
- **The NPC storm pose has explicit gates.** Character code requests the
  `idlestorm` animation group when the actor is dry, has no active upper-body
  action, and faces into the wind (dot product below -0.5 against the outward
  direction from Red Mountain). It drives torso and right-arm groups at storm
  priority. Swimming and upper-body actions therefore suppress this pose; the
  inspected function contains no equipment or helmet protection check. See
  [`character.cpp`, storm reaction selection](https://github.com/OpenMW/openmw/blob/def941246531187d27cc8ceea8baf8b1894a994e/apps/openmw/mwmechanics/character.cpp#L1090-L1128).

## Unknowns and limits

The source path establishes region-driven selection, but this study does not
publish or claim original regional probability values, settlement boundaries,
or a complete CELL-to-REGN census. It does not establish the exact behavior of
the original executable, all script/save/load overrides, every NPC model's
animation availability, or whether any other gameplay system adds protection.
The absence of a Ghostfence test in the inspected weather-manager path does not
prove that no data, script, or other runtime behavior can affect weather there.
Visual parameters and weather probabilities for an AmiWind demake remain design
choices unless separately validated from permitted source evidence.

## AmiWind direction and acceptance

The requested art direction for the Red Mountain area is strongly reddened
skies with windblown ash, visually like a snowstorm made of ash. Treat this as
an art direction, not verified original color, extent, onset, or probability
data. Any regional-weather work should be an explicitly selectable demake
prototype, keep the v0.0.28 sky behavior available, and label simplified
probabilities and visual effects clearly.

Before accepting such a prototype, verify the authored cell-to-region mapping,
weather roll and transition timing, and behavior while crossing region
boundaries. Capture clear, Ashstorm and Blight states at representative views;
check ash direction relative to the player and Red Mountain. For NPC reactions,
verify facing thresholds, dry/wet transitions, animation-group availability,
and suppression by combat/equipment upper-body actions. Record any fallback
when a model lacks the storm group. Keep native Amiga frame-time and memory
measurements separate from source fixtures, since directional particles,
fog and palette changes can have material CPU and memory costs on the target.

The current AmiWind work is a source study and visual proposal. It does not
assert that regional weather, Ashstorm/Blight gameplay or NPC storm reactions
are implemented or target-accepted.