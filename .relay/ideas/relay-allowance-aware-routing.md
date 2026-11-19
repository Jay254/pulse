# Route tasks by remaining agent allowance

Area: relay
Status: new
Added: 2026-11-19

- Problem: each agent runs on a plan with its own usage limit (Claude Pro, Cursor Pro, ChatGPT
  Plus). When one runs out, for example Cursor credits until the next reset, tasks labeled for
  it stall until the owner reassigns them.
- Idea: Relay tracks each agent's usage and reset date and assigns new issues to an agent that
  has allowance left. It also spaces out jobs on the same plan instead of running them in
  parallel.
- Notes: limits are not exposed by an API for every plan, so start with counts of runs per
  agent and manual reset dates.
