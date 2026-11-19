# Request a Codex review when a PR opens

Area: relay
Status: new
Added: 2026-11-19

- Problem: Codex reviews a PR only after someone comments `@codex review`, unless automatic
  reviews are enabled for the repo.
- Idea: Relay posts `@codex review` as soon as an agent opens a PR.
- Notes: check first whether the Codex automatic review setting covers PRs opened by every
  agent. If it does, this is not needed.
