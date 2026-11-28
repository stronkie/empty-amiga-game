# Stronkie Soft Amiga 500 toolkit

Everything a new chat needs to make, build, test and release an Amiga 500 game
for Mark Stronks (Stronkie Soft) - so nothing has to be downloaded, rewritten
or worked out again.

## Start of every new game chat

```sh
git clone --depth 1 https://github.com/stronkie/empty-amiga-game /home/claude/amiga-toolkit
. /home/claude/amiga-toolkit/setup.sh        # builds vasm + the packer (about a minute)
```

No GitHub? The same toolkit is in `C:\Users\mstro\Downloads\Stronkie Soft\Tools for Claude\amiga-toolkit.zip` (and in Dropbox\Amiga\amiga-toolkit).

Then read, in this order:

1. `docs/CONVENTIONS.md` - Mark's rules for every game (target machine, names, logo, demo, dev mode, versions...)
2. `docs/BUILD.md` - the project layout, the assembler, disks, icons, packing
3. `docs/WHDLOAD.md` - the WHDLoad version (every release has one)
4. `docs/TESTING.md` - the 68000 test harness and the emulator boot test
5. `docs/RELEASE.md` - GitHub, Dropbox, Downloads, itch (Sunday release day)

## What is in here

| Folder | What |
|---|---|
| `vasm/` | vasm source (unmodified, by Volker Barthelmann; free for M68k AmigaOS targets, also commercial - see `vasm/LICENSE`). `setup.sh` builds `bin/vasmm68k_mot` |
| `tools/asm68k.py` | a small Python 68000 assembler (no build step; used by Battleships and Slot Machine) |
| `tools/adf.py` | read / list / build OFS floppy images (Kickstart 1.3 bootable) |
| `tools/adfput.py` | replace a file inside an existing .adf in place (keeps icons, protection bits, boot block) |
| `tools/bootblock.bin` | the Kickstart 1.3 boot block |
| `tools/make_icon.py`, `tools/make_disk.py` | Workbench 1.3 icons (.info) for programs, drawers and disks |
| `tools/make_loading.py` | turn a picture into a loading screen (bitplanes + palette) |
| `tools/make_whdload.py` | WHDLoad drawer + icons + .lha writer (no LhA program needed) - from Slot Machine, adapt names |
| `tools/pack/` | the packer: floppy builds load about twice as fast; `crunch.py` verifies every packed file byte for byte on the 68000 interpreter |
| `tools/m68k.c`, `tools/m68k.h`, `tools/amiga.c`, `tools/emu68k.py` | 68000 interpreter + example AmigaOS test harness for automated game tests |
| `templates/build.sh` | build script template: assemble, icon, packed ADF, hard drive zip |
| `templates/whdload/` | three working WHDLoad slaves (no Kickstart image needed) |
| `templates/installer/` | two hard disk installers that go on the game disk |
| `printkit/` | manual (A5 booklet), 3D fold-up box (A3) and disk labels (A4) PDF makers |
| `intro/` | the Stronkie Soft boot intro (SSIntro): animated logo + music, runs before every game - see intro/README.md |
| `art/stronkiesoft_logo.png` | the Stronkie Soft logo (loading screen + title) |
| `emu/` | vAmigaWeb (GPL) with the free AROS ROMs + `test2.py` / `boot_shots.py`: boot an ADF headless in Chrome and take screenshots |

Keep this repo up to date: when a chat improves a tool, copy it back here and push.
