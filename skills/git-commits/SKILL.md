---
name: git-commits
description: Atomic commit skill for implementers. Load when committing, splitting history, or writing commit messages. Combined from oh-my-opencode git-master. Do not load in the read-only review agent.
license: MIT
compatibility: opencode
---

# Git commits

Combined from oh-my-opencode `git-master`.

**Copy this repo's git history.**

1. Read the related docs that describe commit messages: `AGENTS.md`,
   and `CONTRIBUTING.md` or commitlint when they exist.
2. Read the last 5 commit messages, skipping merges:
   `git log -5 --no-merges --format=%B`.
3. Copy that style exactly: the same prefix, punctuation, scope,
   body, and wording those five messages use.
4. When those five messages include a ticket id, put this job's ticket in that same place (prefix, scope, or trailer). When they do not, leave the ticket id out. Leave the work-branch name out unless those messages already include one, in the same place.
5. If the docs and those five messages have no pattern, use
   `type: description` with
   `feat|fix|refactor|test|docs|chore|perf|ci|build|revert`.
   Still leave the ticket id out.

## Rules

- One logical change per commit. Do not mix a behavior
  fix with an unrelated rename.
- Subject: imperative, ≤72 characters, no trailing period.
- Body: why, not a file list. Wrap at 72.
- Never commit `.env`, tokens, or generated secrets.
- Do not force-push `main`.
- Split when `git diff --stat` shows unrelated paths.

## Do not

- `update` / `wip` / `misc` as the subject.
