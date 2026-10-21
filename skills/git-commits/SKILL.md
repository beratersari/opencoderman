---
name: git-commits
description: Atomic commit skill for implementers. Load when committing, splitting history, or writing commit messages. Combined from oh-my-opencode git-master. Do not load in the read-only review agent.
license: MIT
compatibility: opencode
---

# Git commits

Combined from oh-my-opencode `git-master`.

**Copy this repo's git history.** The five subjects below are a hard
gate. They win over conventional commits and over the rules further
down.

1. Read the related docs that describe commit messages: `AGENTS.md`,
   and `CONTRIBUTING.md` or commitlint when they exist.
2. Run `git log -5 --no-merges --format=%s` and read those five
   subjects before writing the message.
3. Use their pattern exactly: the same ticket-id position, brackets,
   separator, and type prefix. If those subjects do not start with
   `feat:`, `fix:`, or `chore:`, yours must not either.
4. When those five messages include a ticket id, put this job's ticket in that same place (prefix, scope, or trailer). When they do not, leave the ticket id out. Leave the work-branch name out unless those messages already include one, in the same place.
5. Conventional `type(scope): summary` is allowed only when those five
   subjects already use it, or they share no pattern at all. Still
   leave the ticket id out in that fallback.
6. A wrong subject on the tip is `git commit --amend` with no staged
   files and no `--all`. Do not reset or rebase.

## Rules

These apply only when the five subjects share no pattern, or they
already use this shape. They never replace a different pattern.

- One logical change per commit. Do not mix a behavior
  fix with an unrelated rename.
- Subject: imperative, ≤72 characters, no trailing period.
- Body: why, not a file list. Wrap at 72.
- Never commit `.env`, tokens, or generated secrets.
- Do not force-push `main`.
- Split when `git diff --stat` shows unrelated paths.

## Do not

- `update` / `wip` / `misc` as the subject.
