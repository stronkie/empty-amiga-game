# Releasing

## Where things go
- **GitHub**: one private repo per game (`stronkie/<repo>`, list in Claude's memory `/topics/github-repos.md`). New repo for a new game - Mark creates it (Claude cannot create repos), then `add_repo` with access "push".
- **Dropbox**: `C:\Users\mstro\Dropbox\Amiga\<Game name>` (folder named like the game; old builds in `Old`).
- **Mark's files: `C:\Users\mstro\Downloads\Stronkie Soft`** (since 2026-11-22). Find files there and put every new file in the right folder:
  - `Amiga Games\<game folder>`: the latest ADF / WHDLoad / hard drive zip at the top; the builds they replace into that game's old-versions folder (it is called `Old`, `Older versions`, `old versions`... - use the one that is there); manual and print kit into its `docs` folder; screenshots into its `screenshots` folder. A new game gets a new folder with `docs`, `older versions` and `screenshots`.
  - `C64\<game>`: C64 builds.
  - `itch stuff`: itch upload sets and covers.
  - `Tools for Claude`: this toolkit (`amiga-toolkit` + `amiga-toolkit.zip`), WHDLoad dev files, AGS2.
  - `Graphics`: Stronkie Soft logos, banners, loading and title art.
  - `Amiga CF Card`: CF card images. `Browser test`: browser demos. `ready to port`: source material for ports.
  - Anything that fits none of them goes loose into `C:\Users\mstro\Downloads`.
- **itch.io**: https://stronkie.itch.io/ - one page per game.

## When
- New builds are NOT published right away: they wait for **Sunday**, when the one scheduled task "Stronkie Soft Update Sunday" publishes everything newer than what itch shows. Exception: Mark asks to publish now.
- Changelog: every version in between is listed in the Sunday devlog.

## itch page rules (Mark's)
- Every game page is paid; never touch a price. A new paid file copies the price settings of the file it replaces.
- Visible: the latest version (ADF, hard drive zip, Enhanced edition) + its WHDLoad, exactly one free demo, free manual / box / labels (and other extras). Older files hidden, not deleted.
- A release = new files + "New in Vx.y" section in the description + screenshots + a devlog (what changed and why) + a short announcement asking people to test, rate and give feedback.
- Never mention GitHub on itch.

## itch upload recipe (Claude in Chrome)
1. On `https://itch.io/game/edit/<id>` run JavaScript: override `HTMLInputElement.prototype.click` so a file input is appended to the page (made visible) instead of opening a dialog; click "Upload files"; `find` the input; `file_upload` with files under `/home/claude/...` (other paths are refused; max 3.8 MB per call).
2. Wait ~15 s, reload the edit page.
3. Move the new row (`.file_list` children) to the old file's place and the old row to the end; tick "hidden" on the old one, untick it on the new one (new uploads may start hidden); set the display names LAST (`upload[<id>][display_name]` hidden inputs - clicking checkboxes resets them); click Save; reload and check.
4. Description: `textarea[name="game[description]"]` + the `.redactor-in` editor, then Save.
5. Devlog: `https://itch.io/dashboard/game/<id>/new-devlog`, fill `post[title]`, `post[user_classification]`, `.redactor-in` + `textarea[name="post[body]"]`, tick `post[published]`, Save.
JavaScript runs on itch.io but not on stronkie.itch.io (use fetch from itch.io pages).
