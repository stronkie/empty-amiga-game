# The WHDLoad version

Every release has one: a drawer with the slave, the game and icons, zipped
(`..._V<x.y>_WHDLoad.zip`) and/or as LhA (`.lha`, written by `tools/make_whdload.py`
without an LhA program). F10 quits. Needs WHDLoad installed on the Amiga.

The games use their **own slaves with no Kickstart image** (so nobody needs a
ROM file). `templates/whdload/`:

| File | How it works |
|---|---|
| `slave_noKick_hunkloader.s` | Slot Machine: loads `SSlots.game` hunk by hunk itself (resload_LoadFileOffset), relocates, saves the high scores with resload_SaveFile |
| `slave_baseball.s` | Baseball Enhanced: same idea, chip memory layout for a 1 MB chip game, two data files |
| `slave_simple_resload.s` | Wurtel Tiel 1: resload_LoadFile + resload_Relocate (simplest) |

The game must not call the OS while it runs under such a slave (it takes over
the hardware anyway); file access goes through small hooks the slave patches in.
Keep the WHDLoad build's game file UNPACKED.

`tools/make_whdload.py` (from Slot Machine) builds the drawer, the slave's
project icon (default tool WHDLoad), the drawer icon and the .lha - change the
names at the top.
