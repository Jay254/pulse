# Agent scorecard from task history

Area: relay
Status: new
Added: 2026-11-19

- Problem: there is no data on which agent does which kind of task best.
- Idea: build a scorecard from `.relay/log/` entries, PRs, and reviews: CI pass on first push,
  number of review findings, fix rounds, and time to merge, per agent and task type. Use it to
  pick the agent for each new issue.
- Notes: the `Agent:` line in log entries is the join key. The same data can measure how often
  a reviewer's findings are real.
