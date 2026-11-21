# Mark's rules for every Stronkie Soft Amiga game

## The machine
- Target: a stock **Amiga 500, Kickstart / Workbench 1.3, 512 KB chip + 512 KB trapdoor** (1 MB total), joystick in port 2. Must also run on an A500 with an ACA500(plus) and in WinUAE - Mark tests on all three.
- An **Enhanced** edition (more chip RAM, faster CPU, ACA500 at 42 MHz, ...) goes on the SAME itch page as the normal game, never on its own page. It must say clearly what it needs and refuse to run (with a message) on a machine that is too small or slow.
- Write 68000 assembly (vasm, Motorola syntax, `-Fhunkexe -kick1hunks`). Take over the system cleanly and give it back on exit (quit to Workbench works).

## Names and credits
- Credit line everywhere: **"Created By Mark Stronks, Stronkie Soft"** (© year).
- The **Stronkie Soft logo** (`art/stronkiesoft_logo.png`) on the loading screen and on the title screen.
- Use own names for things: no trademarked game names in the game, files or itch page (e.g. "Man, don't get annoyed" style renames).
- Files: `Stronkies<Game>_V<x.y>.adf`, `..._V<x.y>_harddrive.zip`, `..._V<x.y>_WHDLoad.zip` (or .lha), `..._Demo.adf`, `..._Manual.pdf`, `..._Box.pdf`, `..._DiskLabels.pdf`. Multi-disk: `_Disk1`, `_Disk2`.
- Show the version number on the title or credits screen.

## Every game has
- A **free demo** (limited: a few levels / one event / one mode), with DEMO on the title and in the game, and a page at the end saying what the full game has. The demo stays frozen when the full game is updated.
- A **developer mode** with cheats and shortcuts, opened with a key combination (for example CTRL + ALT + D on the title) - **never F10**, because F10 quits WHDLoad. Show "DEV" on screen while it is on, and do not save records while it is on. Add the keys to `Stronkie Soft - Games, Developer Modes & Cheats.xlsx` in Dropbox\Amiga.
- A **hard disk installer** on the game disk (see `templates/installer/`) and a hard drive / CF card zip (a drawer with the game, its icon and the ReadMe).
- A **WHDLoad version** for every release (see `WHDLOAD.md`) - F10 quits.
- A **print kit**: instruction manual (A5 booklet PDF), 3D fold-up box (A3 PDF, with the system requirements) and disk labels (A4 PDF) - `printkit/`.
- Music turned down so effects and voices can be heard; music on/off key (M).
- A ReadMe on the disk with controls, requirements and the changelog.
- Floppy builds are **packed** (`tools/pack`) so they load fast.

## Versions
- V0.x while in development, V1.0 (or V2.0) = "Final Release"; after that only bug fixes unless Mark asks for more.
- Every build gets a new version number and a changelog entry (what changed and why).
- Keep older ADFs in `previous versions/` in the repo.

## Never
- Never mention the GitHub repo or a GitHub link on itch pages, in readmes or game files (the full games are in the repos).
- Never use the built-in browser for itch - only the Claude in Chrome extension (on the "Feb2026" computer if several are connected).
