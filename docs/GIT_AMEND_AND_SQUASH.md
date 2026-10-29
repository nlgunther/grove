# Git: Amending and Squashing Commits

How to rewrite recent commits, with the safety nets. Written for `cmd.exe` on
Windows (see "cmd.exe gotchas"). Both techniques **rewrite history**.

## First: has it been pushed?

| Situation | What to do |
|---|---|
| Commit is **local only** | Amend or squash freely |
| Commit is **pushed**, repo is yours alone | Safe to rewrite, but the next push must be forced (`--force-with-lease`) |
| Commit is **pushed and others have pulled it** | Don't rewrite. Add a new commit or use `git revert` |

Rule of thumb: amend/squash to tidy **unpushed** work. For already-pushed
work, a plain follow-up commit is usually better.

## Safety net (do this first)

```
git branch backup-before-squash
```

The backup branch keeps pointing at the original commits. To undo everything:

```
git reset --hard backup-before-squash
```

Other escapes: `git rebase --abort` (mid-rebase) and `git reflog` (shows every
recent HEAD position; old commits stay reachable for weeks).

## 1. Overwrite the most recent commit (amend)

```
git commit --amend                  # opens the editor to rewrite the message
git commit --amend -F msg.txt       # use a message from a file
git commit --amend --no-edit        # keep the message, fold in staged changes
```

Include a forgotten or fixed file: stage it first, then amend.

```
git add pyproject.toml uv.lock
git commit --amend --no-edit
```

### Example: forgot a file in the last commit

You committed, then noticed `uv.lock` was left out. If the commit is **not
pushed**, amending is safe and needs no force push:

```
git add uv.lock
git commit --amend --no-edit
git show --stat HEAD                # verify: the file now appears in the commit
git push                            # plain push is enough (never pushed before)
```

- `git add uv.lock` stages only that file. Other modified or untracked files
  are left alone, so they are not swept in. Check `git status` first.
- `--no-edit` keeps the existing message. Drop it (plain `git commit --amend`)
  to reword the message, e.g. to mention the lockfile.
- If a file such as a lockfile depends on another change (say a
  `requires-python` bump), regenerate it first (`uv lock`) so you commit the
  current version.
- If the commit **was already pushed**, the same amend works but the push must
  be `git push --force-with-lease`. Prefer a small follow-up commit instead
  when others may have pulled it.

Amend changes the commit's hash. If it was already pushed, finish with
`git push --force-with-lease`.

## 2. Squash several recent commits into one

There is no `git squash` command. Two ways to get the result:

### A. Reset and recommit (simplest, scriptable)

```
git branch backup-before-squash
git reset --soft HEAD~3             # un-commit the last 3, keep changes staged
git commit -F COMMIT_MSG.txt        # one new commit (or plain `git commit`)
```

`--soft` leaves the combined changes staged, so nothing is lost. Change `3`
to however many commits to squash.

### B. Interactive rebase (more control)

```
git branch backup-before-squash
git rebase -i HEAD~3
```

1. **First editor, the todo list.** Commits are listed **oldest first**
   (opposite of `git log`). Keep the first as `pick`; change the others to
   `squash` (or `s`). In Vim: `j`, `0`, `cw`, type `squash`, `Esc`, then
   `:wq`.

   ```
   pick   1c1c25b first commit
   squash e22841b second commit
   squash 372f625 third commit
   ```

2. **Second editor, the combined message.** Git stacks all the messages. Lines
   beginning with `#` are ignored. Delete what you don't want (`dd`) and write
   one good message. Do **not** leave the placeholder "This is a combination
   of 3 commits." as the subject. Save with `:wq`.

Other todo-list verbs: `reword` (change a message only), `fixup` (squash and
discard that commit's message), `drop` (remove a commit), `edit` (stop to
change a commit).

If the subject came out wrong, fix it (when unpushed):

```
git commit --amend
```

## 3. Check, test, push

```
git log --oneline -3                          # expect one new commit
uv run --with pytest --with pandas pytest tests -q   # test before pushing
git push --force-with-lease                   # only needed if already pushed
```

`--force-with-lease` overwrites the remote **only if** `origin/main` is still
where your local copy last saw it. If someone else pushed in the meantime, it
refuses instead of destroying their work. Plain `--force` has no such check.
Caveat: running `git fetch` first updates the lease reference, so it won't
protect you from commits you fetched but haven't looked at.

Clean up after a successful push:

```
git branch -D backup-before-squash
del COMMIT_MSG.txt
```

(`-D`, capital, is needed because the backup branch's commits are no longer in
`main`. It only deletes the local branch.)

## Commit message conventions

- **Subject**: one line, imperative mood ("Add", "Fix", "Accept"), about 50
  characters (72 max). Optional area prefix: `text2ics: accept YYYYMMDD dates`.
- Blank line, then a **body** explaining what and why (not how).
- Details like docs, tests, and dependency bumps belong in the body.

## When to commit separately

Prefer **atomic commits**: one logical change per commit, with its tests (and
usually docs) so every commit passes the suite. Separate commits suit separable
concerns (a bug fix vs. an unrelated refactor). Commits are cheap; size comes
from large files, not commit count.

## cmd.exe gotchas

- **No heredocs.** `git commit -F- <<'EOF'` fails ("<< was unexpected"), and
  every pasted line then runs as a command.
- **Inline `-m` quoting is fragile** with multiple `-m` flags or inner quotes.
  Use `git commit -F file.txt`, or plain `git commit` and the editor.
- **Don't paste multi-line text at the prompt.** A line starting with `time`
  or `date` runs the Windows command of that name.
- **Test on Windows before committing.** A Linux sandbox passed while Windows
  failed on the missing `tzdata` package.
