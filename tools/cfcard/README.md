# CF card image tools

Read and change files on Mark's CF card image (`StronkieSoft_betatester_CF.img`, RDB with
DH0: Workbench and DH1: Games, both FFS `DOS\1`) without an Amiga.

- `ffs.py` - class `FFS(img, lowcyl, highcyl)`: `path()`, `entries()`, `readfile()`, `create()`
  (replaces a file of the same name), `delete()`, `mkdir()`, `close()` (writes the bitmap). DH1 on the
  beta tester image is cylinders 206 - 1899 (16 heads, 63 sectors); DH0 is 2 - 205.
- `ffscheck.py <img>` - walks DH1 and checks checksums, double-used blocks and the bitmap.
  Run it before and after a change: the numbers must stay the same (the image has 4 lost blocks).

Card rules (memory /areas/amiga-cf-card.md): games start with WHDLoad from `Games:WHDLoad/<game>`,
demos from `Games:Demos/<game>Demo`, each with an AGS entry `.run` / `.txt` / `.iff` (320x128, 8 colours)
in `AGS/` or `AGS/Demos.ags`; the quit key is HELP (`QUITKEY=95`, and ws_keyexit byte $5F in the slave).
Work on the newest `StronkieSoft_betatester_CF_LATEST.zip`, keep a `_before_...` copy, and commit with
`expectedMtimeMs` so a newer image made by another chat is never overwritten.
