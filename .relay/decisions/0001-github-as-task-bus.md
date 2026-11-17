# 0001: GitHub issues are the task bus

**Context:** several agents (Claude, Cursor, Codex) work on this repo, often while the owner's
computer is off, and the owner directs them from a phone.

**Decision:** every task is a GitHub issue. Agents are started by mention (`@claude`, `@cursor`,
`@codex` on PRs), work on their own branch, and deliver a PR. They talk to each other in issue
and PR comments and leave durable notes in `.relay/`.

**Reason:** no custom infrastructure, works with the computer off, everything is visible from
the GitHub app, and each agent runs on its own subscription.
