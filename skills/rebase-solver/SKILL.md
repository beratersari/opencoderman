---
name: rebase-solver
description: Resolve a rebase onto the target branch that stopped on conflicts. Use when Mirai names repositories whose rebase onto the target failed.
license: MIT
compatibility: opencode
---

# Rebase solver

Mirai already ran `git rebase origin/<target>` on the work branch. Finish that rebase. Do not ask questions. Do not push.

## Which repository

The prompt names each repository that stopped. In a multi-repo workspace, `cd` into that repository first. Leave every other repository alone.

## Rebase only. Never merge

The merge request accepts a linear branch on top of the target. A merge commit does not make it mergeable. Do not run `git merge`, `git pull`, or `git commit` with two parents. Do not abort the rebase to merge the target in instead. `git merge-base` is a read and is allowed.

## One commit at a time

A rebase replays the work commits one by one. Git stops on each commit that conflicts. Every stop is one commit, and the next commit may conflict in the same file again. Resolve each stop on its own:

1. Find the commit Git stopped on: `git show --stat REBASE_HEAD` shows that one commit and what it changed. Progress is `Rebasing (N/M)`.
2. Conflicted files are the unmerged paths in `git status`.
3. Open each conflict. `<<<<<<< HEAD` is the target plus the work commits already replayed (`--ours`). The part under `=======` is the commit Git stopped on (`--theirs`). Keep the target's change and apply that commit's own change on top of it. Do not pull in a later commit's change early. That later commit applies it when Git reaches it.
4. Delete every conflict marker (`<<<<<<<`, `=======`, `>>>>>>>`). `git diff --check` finds a marker you missed.
5. `git add` each resolved file. Do not `git add -A` over unrelated untracked files.
6. Continue by running the continue command named in the user message. It is a shell script on Windows and on Linux. The script sets `GIT_EDITOR` itself. An inherited value such as `cmd.exe /c exit 0` is not an editor Git can run, and `git -c core.editor=` does not override `GIT_EDITOR`.

   To continue by hand, set `GIT_EDITOR` and `GIT_SEQUENCE_EDITOR` to the absolute program named in the prompt, then run `git rebase --continue`. Do not write `GIT_EDITOR=true git rebase --continue`. That is not a PowerShell assignment, and a bare `true` is not on PATH there. Do not use `$env:GIT_EDITOR` either.
7. Git now replays the next commit. If it stops again, go back to step 1 for that commit. Repeat until `git status` shows no rebase in progress.
8. Do not `git rebase --skip` unless the commit is empty after the resolution. Git already drops a commit the target contains (`skipped previously applied commit`). That is expected.

## Check before you finish

From the repository, with `<target>` the target branch:

- `git status` shows no rebase in progress.
- `git merge-base --is-ancestor origin/<target> HEAD` exits 0.
- `git rev-list --merges origin/<target>..HEAD` prints nothing.
- `git grep -n -e '^<<<<<<< ' -e '^>>>>>>> '` prints nothing.

If a check fails, fix it in this rebase. Do not add a merge commit to pass it.

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

- Do not `git merge` or `git pull`. Do not create a merge commit.
- Do not checkout another branch.
- Do not commit a new feature on top of the conflict.
- Do not push or open a merge request.
- Do not resolve a repository the prompt did not name.
