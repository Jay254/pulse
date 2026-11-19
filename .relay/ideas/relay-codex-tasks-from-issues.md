# Start Codex tasks from issue comments

Area: relay
Status: new
Added: 2026-11-19

- Problem: commenting `@codex` with a task on an issue replied "create an environment for this
  repo", even though a published environment existed. Codex is used only for reviews for now.
- Idea: find the cause (workspace, repository field, or timing) so Codex can take
  implementation issues the same way Claude and Cursor do. Starting a task from
  chatgpt.com/codex is the fallback.
- Notes: a Codex-written PR should be reviewed by a different model, for example
  `@claude review this PR`.
