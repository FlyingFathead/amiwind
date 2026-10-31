# AmiWind v0.0.58-dev1 (in development)

Development snapshot, 31 October 2026, in development. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.57](RELEASE-v0.0.57.md).

The first snapshot of v0.0.58, "Time To Talk": most of the conversation's services, and every voice and sound in its
place. The game needs 32 MB of Fast RAM, and the emulator presets of this snapshot have it. What v0.0.57 brought is
listed in its [notes](RELEASE-v0.0.57.md). This snapshot is for testing in game; none of the new parts below has been
checked in game yet.

## New since v0.0.57

- **Links in the conversation.** Topic names in an answer show as links, made by the builder with OpenMW's rule; a
  click, or Tab and Enter, asks about that topic.
- **Persuasion.** Admire, Intimidate, Taunt and Bribe 10, 100 or 1000, with the original's rules; bribes you cannot
  pay are greyed out. Disposition now also decides when a character attacks, in the conversation and in the world.
- **Services from the conversation.** Travel, Training, Spells, Barter (buy and sell, one thing at a time), Repair and
  Spellmaking, each refused when the character's own refusal answer applies. Things you sell to a merchant who does
  not stock them can be bought back. Every word in these windows is the game's own text.
- **Soul gems keep their souls,** and spells you make are kept in your saved game.
- **Voices and sounds.** Two Orcs whose names carry accented letters greet and talk again. Creatures make their own
  sounds as they move and fight (steps, moans, roars, screams). The sounds of one blow in a fight no longer cut each
  other off, and the sound system can no longer run out of room for new sounds in a long session.
- **Your own footsteps,** off by default: `dbg footsteps on` or Options > Audio.
- **Builds report their voice coverage:** every character with a voice and every creature with a sound, and anything
  missing named with its reason.

## Known in this build

- The new windows and sounds above are untested in game; this snapshot is how they get tested.
- The fuller combat sounds (the swing, the armour piece struck, blocks, punches) are still behind
  `dbg combat sounds on`; they become the default after an in-game check.
- Enchanting, casting the spells you make, and the original's full trade window are not in this snapshot.
- Some rooms still load in after you arrive ([CHIM-ROOM-POPIN-51](../../bugs/CHIM-ROOM-POPIN-51.md)).
