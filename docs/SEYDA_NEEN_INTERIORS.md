# Seyda Neen interior milestone

Owner request, 29 September 2026: implement all Seyda Neen interiors. This is a
follow-up to the v0.0.23-dev1 build checkpoint, not a claim of new gameplay.
The supplied base master contains these 13 named interior cells:

- Seyda Neen, Arrille's Tradehouse
- Seyda Neen, Census and Excise Office
- Seyda Neen, Census and Excise Warehouse
- Seyda Neen, Draren Thiralas' House
- Seyda Neen, Eldafire's House
- Seyda Neen, Erene Llenim's Shack
- Seyda Neen, Fargoth's House
- Seyda Neen, Fine-Mouth's Shack
- Seyda Neen, Foryn Gilnith's Shack
- Seyda Neen, Indrele Rathryon's Shack
- Seyda Neen, Lighthouse
- Seyda Neen, Terurise Girvayne's House
- Seyda Neen, Vodunius Nuccius' House

The Census and Excise Office is already converted. The separate Imperial Prison
Ship is also present, outside this set of 13. The other twelve town interiors
remain to implement and validate.

Convert original geometry, furnishing references, lighting and door destinations
through a reusable cell recipe. Preserve source cell/reference identity and
report excluded records explicitly. Link entrance/exit doors, place the player
safely, and test repeated transitions, music continuity, memory use and saves.
Do not describe decorative NPCs, containers or clutter as implemented behavior.
Keep detailed actor/inventory/script work distinct from traversable room coverage.
