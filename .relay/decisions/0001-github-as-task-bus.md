# 0001 — GitHub issues are the task bus

**Context:** Several agents (Claude, Cursor/Grok, Codex) work on this repo, often while the owner's
PC is off, and the owner directs them from a phone.

**Decision:** Every task is a GitHub issue. Agents are summoned by mention (`@claude`, `@cursor`,
`@codex` on PRs), work on their own branch, and deliver a PR. Agents talk to each other in
issue/PR comments and leave durable notes in `.relay/`.

**Why:** No custom infra needed, works with the PC off, everything is visible from the GitHub app,
and each agent runs on its own subscription.
