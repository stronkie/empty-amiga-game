# Testing

## 1. 68000 interpreter (fast, automatic)
`tools/m68k.c` is a small 68000 interpreter (Musashi-compatible API). `tools/amiga.c`
is the harness Blocks uses: fake chip RAM / custom chips, runs the game for N frames,
feeds joystick input and dumps the screen. `tools/emu68k.py` is the Python version
(Slot Machine / Battleships). Build: `gcc -O2 -w -Itools -o build/amiga tools/amiga.c tools/m68k.c -lm`.
`tools/pack/harness.c` shows the minimal version (run code until a PC is reached).

### Test harness extras (from Stronkie's Space Trader, 2026-11-22)
`tools/amiga.c` also does:
- Blitter: D-only fills (minterm 00/FF) and A->D copies (BLTCON0 09F0). Other modes still stop with an error.
- dos.library: `CON:` windows (Open/Read/Write, typed input from `conline`), Lock, UnLock, CreateDir (for hard disk installers). graphics.library LVO -456/-462 are allowed.
- Script commands: `mdelta dx dy` (move the mouse, port 1), `lhold n` (hold the left mouse button n frames), `down KEY` / `up KEY` (hold and release a key), `conline TEXT` (a line typed into a CON: window).
- `watch SYMBOL+off` now also reports byte and long writes, with d0-d7, a0, a1, sp and the return addresses on the stack - the quickest way to find who overwrites a variable.

`tools/asm68k.py -sym` writes a symbol hunk, so the harness can show routine names in its reports (build a `test.game` with it next to the release build).

`tools/fixbr.py` fixes "short branch out of range" errors by turning `bxx.s` into `bxx` until the source assembles.

### Test harness extras (from Stronkie's Clover Snake, 2026-11-27)
- WHDLoad slaves: `resload_LoadFile` and `resload_Relocate` are emulated, so a slave built from `slave_simple_resload.s` runs in the harness: `amiga Game.slave <data dir> script`. Build slaves with `-Fhunkexe -nosym` (not `-Fbin`).
- Key names `CTRL`, `LSHIFT`, `RSHIFT`, `LALT`, `RALT`, `LAMIGA`, `RAMIGA` for `down` / `up` (test dev-mode key combos).

## 2. Boot test in a real Amiga emulator (vAmigaWeb + AROS ROMs)
Boots the ADF like a real A500 (with the free AROS Kickstart replacement) in headless
Chrome and takes screenshots - this is how the packed releases were checked.
```sh
cd $AMIGA_TK/emu
cp /path/Game_V1.0.adf vamigaweb/emu/games/
python3 serve.py vamigaweb/emu &    # http://127.0.0.1:8000 (the emulator page is in emu/)
python3 test2.py Game_V1.0.adf shots/game 30,60,90 "35:Space;65:Digit1,Space"
#   adf (relative to games/), output prefix, screenshot times (s), "time:key,key;..."
```
Needs python playwright + /usr/bin/google-chrome (both in the sandbox). AROS is not
Kickstart 3.1: a game that runs there almost always runs on a real A500, but Mark
still tests on his A500, ACA500 and WinUAE before a Final Release. Compare old vs
new builds side by side (same timings) when you change loading or packing.

### Playing a mouse game in vAmigaWeb (from World of Stronkie remake, 2026-11-27)
`emu/webplay.py disk.adf outdir steps.txt` drives vAmigaWeb with the **mouse**: `g X Y` puts the
pointer on game pixel X,Y, `l` / `r` click, `k KEY` presses a key, `w S` waits, `s NAME` takes a
screenshot. The pointer is homed with small moves first: the Amiga's mouse counters are 8 bit,
so one move of 128 or more wraps around (that is why a single -200 move sends the pointer the
wrong way). Emulation in headless Chrome runs a bit slower than real time: wait generously.

`tools/adf.py`: the built-in boot block (used when no boot block file is given) pointed 6 bytes
past "dos.library" and did not boot (AROS showed "waiting for bootable media"); fixed 2026-11-27.
Pass `tools/bootblock.bin` to be sure.

## 3. Mark
After a build, give Mark the ADF (Downloads + Dropbox) and ask him to test on his
Amiga 500 / ACA500 / WinUAE. His CF card has an AGS2 "Game Selector" with all games
(WHDLoad versions).

