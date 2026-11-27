# Stronkie Soft boot intro (SSIntro) - V1.0

A short intro before every Stronkie Soft Amiga game: the mascot drops in, STRONKIE and
SOFT rise up, PRESENTS types itself, copper raster bars bounce behind the logo, stars
scroll, the antenna lights up on the kick drum and a shine runs over the logo on the
snare. Music: "intro numma" by Animal of Superior Art Creations (1996) - the module asks
to be credited, so the credit is on screen and must stay there.

- About 11 seconds: everything is on screen after 4 s, the fade-out (picture + music)
  starts at 10 s (`T_FADE` in intro.s). Mouse button, fire or any key skips it (fast fade).
- 68000 only (`-m68000`), Kickstart 1.3 - 3.1, 512K chip is enough (about 67 KB chip).
- Takes over the system cleanly and gives it back (Forbid, own copper list, interrupts off,
  everything restored, returns 0), so a startup-sequence can run the game right after it.
- Timing follows CIA-A TOD (counts the vertical blanks), so the music keeps its tempo
  even when a frame takes too long.
- Own small ProTracker player in intro.s (effects 0,1,2,3,4,5,6,A,B,C,D,F) - enough for
  most modules; E-commands are ignored.

## Build
    . ../setup.sh ; ./build.sh
gives `build/SSIntro` (plain, for hard drive zips) and `build/StronkieSoftIntro_V1.0.adf`
(test disk; on the disk SSIntro is packed with tools/pack).

## Adding it to a game (floppy)
Put the packed SSIntro on the game ADF (tools/adfput.py) and add `SSIntro` as the first
line of the disk's s/startup-sequence. The game itself does not change. Not for WHDLoad
(the intro uses graphics.library); hard drive zips need a small script started from the icon.

## Files
- `intro.mod` - the music (keep the credit)
- `make_assets.py` - draws the final picture from art/stronkiesoft_logo.png (2x), the eyes-closed
  frame, the font texts, palette, drop/rise curves, bar colours, fade table
- `src/intro.s` - the intro + music player; `src/tables_gen.s` is generated
