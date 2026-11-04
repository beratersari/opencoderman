---
name: planning
description: Implementation-planning skill. Load when writing a design, PR plan, or task breakdown before coding. Combined from obra/superpowers writing-plans.
license: MIT
compatibility: opencode
---

# Planning

Combined from obra/superpowers `writing-plans`.

## Rules

- State the goal, non-goals, and the smallest vertical
  slice that proves the design.
- List files you expect to touch. Call out unknowns.
- Acceptance: a command or scenario that would fail
  today and pass after.
- Risks and rollback. No “then we rewrite X” without a
  reason.
- One milestone the user can ship or throw away.

## Do not

- A 20-file rewrite as step 1.
