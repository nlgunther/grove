# Vim Cheatsheet

The essentials, with a focus on the editor Git opens for commit messages and
`git rebase -i`. Vim is **modal**: the same key does different things
depending on the mode.

## Modes

| Mode | How to enter | What it is for |
|---|---|---|
| **Normal** | `Esc` (start here) | Move around, delete, copy, run commands |
| **Insert** | `i`, `a`, `o` (see below) | Typing text. Bottom line shows `-- INSERT --` |
| **Command-line** | `:` from Normal mode | Save, quit, search/replace |

**Lost? Press `Esc` once or twice.** That always returns you to Normal mode.

## Save and quit (type in Normal mode, then press Enter)

| Keys | Effect |
|---|---|
| `:wq` | Write (save) and quit. In a Git editor this *completes* the commit/rebase step |
| `:x` | Same as `:wq`, but only writes if there are changes |
| `ZZ` | Same as `:x` (no colon, no Enter) |
| `:w` | Save, stay in the editor |
| `:q` | Quit (refuses if there are unsaved changes) |
| `:q!` | Quit and **discard** changes. In a Git editor this *aborts* the commit |
| `:cq` | Quit with an error code. Git aborts the commit or rebase |

> `:qs` is **not** a command. The ones you want are `:wq` and `:q!`.

## Enter Insert mode

| Key | Where typing begins |
|---|---|
| `i` | Before the cursor |
| `a` | After the cursor |
| `I` | At the start of the line |
| `A` | At the end of the line |
| `o` / `O` | On a new line below / above |

## Move around (Normal mode)

| Keys | Effect |
|---|---|
| `h` `j` `k` `l` | Left, down, up, right (arrow keys also work) |
| `0` | Start of line |
| `$` | End of line |
| `w` / `b` | Forward / back one word |
| `gg` | First line of the file |
| `G` | Last line of the file |
| `:42` | Jump to line 42 |

## Delete, change, replace (Normal mode)

| Keys | Effect |
|---|---|
| `x` | Delete the character under the cursor |
| `dd` | Delete the current line |
| `5dd` | Delete 5 lines, starting at the current one |
| `dw` | Delete from the cursor to the end of the word |
| `D` | Delete from the cursor to the end of the line |
| `dG` | Delete from the current line to the end of the file |
| `gg` then `dG` | Delete the whole file (start with a blank buffer) |
| `:%d` | Delete the whole file (command-line equivalent) |
| `cw` | Change word: deletes it and enters Insert mode (type the replacement, `Esc`) |
| `cc` | Change the whole line |
| `r` + char | Replace one character, stay in Normal mode |

Pattern: **operator + motion**. `d` (delete) and `c` (change) combine with a
motion: `dw`, `d$`, `cw`, `c$`. A number first repeats it: `3dw`.

## Undo, redo, copy, paste

| Keys | Effect |
|---|---|
| `u` | Undo |
| `Ctrl-r` | Redo |
| `yy` | Copy (yank) the current line |
| `p` / `P` | Paste after / before the cursor |
| `.` | Repeat the last change |

## Search

| Keys | Effect |
|---|---|
| `/text` + Enter | Search forward for `text` |
| `n` / `N` | Next / previous match |
| `:%s/old/new/g` | Replace every `old` with `new` in the file |

## Recipes for Git

**Write a commit message from scratch** (`git commit` or `git commit --amend`):

1. `gg`, then `dG` to clear the buffer (the `#` lines are ignored anyway)
2. `i`, then type: subject line, blank line, body
3. `Esc`, then `:wq` and Enter

**Change `pick` to `squash`** in `git rebase -i`:

1. `j` to the line, `0` to the start of the line
2. `cw`, type `squash`, `Esc`
3. Repeat for other lines, then `:wq`

**Give up:** `:q!` (commit) or `:cq` (rebase/commit) cancels. In a rebase todo
list, deleting every line also cancels.

## Gotchas

- Typing text in Normal mode runs commands, not text. If random things happen,
  press `Esc` and use `u` to undo.
- No `-- INSERT --` at the bottom means you are in Normal mode.
- `:wq` needs the colon and Enter; `Esc` first if you were typing.
