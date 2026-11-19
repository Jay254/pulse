# Review and fix loop between agents

Area: relay
Status: new
Added: 2026-11-19

- Problem: when Codex finds issues in a PR, the owner has to read the review and comment
  `@claude` on GitHub to start a fix.
- Idea: when a review finishes, Relay sends a short summary to the owner's phone with Fix,
  Ignore, and Merge buttons. Fix posts the `@claude` comment as the owner, which starts the next
  round.
- Notes:
  - A later step could let review comments start fixes on their own. If so, cap it at two fix
    rounds, act only on serious findings, and leave merging to the owner.
  - First measure how often review findings are real before automating. The workflow only runs
    for the owner's comments, which blocks prompt injection through bot comments; keep that
    unless there is a safe replacement.
