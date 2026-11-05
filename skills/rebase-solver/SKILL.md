---
name: rebase-solver
description: Resolve a rebase onto the target branch that stopped on conflicts. Use when Yaver names repositories whose rebase onto the target failed.
license: MIT
compatibility: opencode
---

# Rebase solver

Yaver already ran `git rebase origin/<target>` on the work branch. Finish that rebase. Do not ask questions. Do not push.

## Which repository

The prompt names each repository that stopped. In a multi-repo workspace, `cd` into that repository first. Leave every other repository alone.

## If a rebase is already in progress

1. Run `git status`. Conflicted files are the unmerged paths.
2. Open each conflict. Keep both sides' intent. `<<<<<<< HEAD` is the target branch (`--ours`). The commit under `=======` is this job's work commit (`--theirs`).
3. Delete every conflict marker (`<<<<<<<`, `=======`, `>>>>>>>`).
4. `git add` each resolved file. Do not `git add -A` over unrelated untracked files.
5. Continue without an editor. In PowerShell run:

   ```powershell
   $env:GIT_EDITOR = "true"
   git rebase --continue
   ```

   Do not write `GIT_EDITOR=true git rebase --continue`. PowerShell does not set the variable that way, and git opens its editor. Yaver already puts Git's `true` on PATH and sets `GIT_EDITOR` for the job, so `git rebase --continue` alone also skips the editor.
6. Repeat until `git status` shows no rebase in progress.
7. Do not `git rebase --skip` unless the commit is empty after the resolution.

## When to abort

Abort when a conflict cannot be resolved safely:

- a conflicted path is binary, or git says the file is binary (`binary files differ`, images, archives, libraries, pdf)
- the conflict is too large or too tangled to resolve without guessing

Then:

```text
git rebase --abort
```

Confirm `git status` shows no rebase in progress. The work branch is back where it was before this rebase. Stop. Do not push and do not start the ticket work.

## If the rebase is not in progress

The prompt says the rebase did not start. Start it:

```text
git fetch origin <target>
git rebase origin/<target>
```

Then resolve conflicts the same way. `<target>` is the target branch named for that repository.

## Do not

- Do not checkout another branch.
- Do not commit a new feature on top of the conflict.
- Do not push or open a merge request.
- Do not resolve a repository the prompt did not name.
