---
description: Verify, commit, push, open a PR, squash-merge, and clean up after a feature is complete
allowed-tools: Read, Glob, Grep, Bash(git:*), Bash(python:*), Bash(pytest:*), mcp__github__create_pull_request, mcp__github__merge_pull_request, mcp__github__list_pull_requests
disable-model-invocation: true
---

## Global rules
- Run steps in order. **If any step fails, stop immediately**, report which step failed and why, and do not run later steps.
- Never commit or push directly to `main`.
- Never force-push. Never use `git add .` or `git add -A`.
- Never delete a branch unless Step 8 returned a confirmed merge.
- Print a "✓" line only for a step that actually succeeded.
- If the GitHub MCP tools are unavailable, stop and say:
  "GitHub MCP is not connected. Run /mcp to check connection."

## Step 1 — Pre-flight checks
```bash
git fetch origin
git branch --show-current
git remote get-url origin
git status --short
git log origin/main..HEAD --oneline
```
- Store the branch as CURRENT_BRANCH.
- If CURRENT_BRANCH is `main` (or empty): stop and say "Switch to a feature branch first."
- Derive OWNER and REPO from the origin URL (works for both https and ssh forms).
- If the working tree is clean AND there are no commits ahead of `origin/main`: stop and say "Nothing to ship."

## Step 2 — Find the spec
Match CURRENT_BRANCH to a file in `.claude/specs/`
(e.g. `feature/edit-expense` → `.claude/specs/*edit-expense*`).
- Zero matches or more than one: stop and ask which spec to use. Do not guess.
- Read the matched spec: Overview and Definition of done.

## Step 3 — Verify before committing
1. Run the test suite:
```bash
pytest
```
Stop if any test fails.

2. Check every Definition of done item against the code or tests.
   Record each item as **verified** or **not verified**.

3. If any item is not verified: list them, then stop and ask whether to
   continue. Do not proceed unless the user explicitly says yes.

## Step 4 — Stage safely
```bash
git status --short
git check-ignore -v expense_tracker.db .env .claude.json
```
- Stage files **by name**, only those that appear in `git status --short`
  and are not ignored. Include new untracked files that belong to the feature.
- Never stage: `*.db`, `.env`, `.claude.json`, `__pycache__/`, `*.pyc`,
  or anything that looks like a token or credential.
- If any of those appear as untracked or modified and are not ignored:
  stop and tell the user to add them to `.gitignore`.
```bash
git add <file1> <file2> ...
git diff --staged --stat
```

## Step 5 — Commit
Generate a Conventional Commit message from the staged diff and the spec:
- `feat:` new feature, `fix:` bug fix, `chore:` config or tooling, `docs:` documentation only
- Lowercase, no period at the end, under 72 characters
- Describes what the user can now do, not what the code does

Good: "feat: add delete expense button with confirmation dialog"
Bad: "feat: added DELETE route to app.py"

If nothing is staged but commits already exist ahead of `origin/main`,
skip the commit and continue. Otherwise:
```bash
git commit -m "<generated-message>"
```
Store the message as COMMIT_MESSAGE.
Report: "✓ Committed — <COMMIT_MESSAGE>"

## Step 6 — Push
```bash
git push -u origin CURRENT_BRANCH
```
If the push is rejected, stop and report the error. Never force-push.
Report: "✓ Pushed — CURRENT_BRANCH"

## Step 7 — Create or reuse the PR
First check whether an open PR already exists for CURRENT_BRANCH → `main`
(use `mcp__github__list_pull_requests`). If one exists, reuse it. Otherwise
create one with `mcp__github__create_pull_request` (owner=OWNER, repo=REPO,
head=CURRENT_BRANCH, base=`main`).

Title: plain English feature name, no prefix. Example: "Add delete expense functionality"

Get the changed-file list from:
```bash
git diff --name-status origin/main...HEAD
```

Description:
```markdown
## What this PR does
<one paragraph from the spec Overview>

## Changes
<bullet list of every changed file with a one-line description>

## Definition of done
<every spec checklist item; "[x]" only if verified in Step 3, otherwise "[ ]">

## How to test
1. Run `python app.py` (port 5001)
2. Log in with the demo credentials from the seed data (read them from the seed file; do not guess)
3. <steps derived from the Definition of done items>
```

If PR creation fails, stop. Do not continue to merge.
Report: "✓ PR ready — <PR URL>"

## Step 8 — Confirm and merge
Ask: "Ship '<COMMIT_MESSAGE>' to main with a squash merge? (y/n)". Continue only on "y".

Check the PR is mergeable (no conflicts, required checks not failing).
If not, stop and report; leave all branches untouched.

Merge with `mcp__github__merge_pull_request`, method **squash**, using
COMMIT_MESSAGE as the squash commit title so history keeps the Conventional Commit format.

Confirm the response says the merge succeeded. If it did not, stop.
Report: "✓ PR merged to main"

## Step 9 — Delete the remote branch (only after a confirmed merge)
```bash
git push origin --delete CURRENT_BRANCH
```
If this fails because the branch is already gone (auto-delete is enabled in
the repo settings), treat it as success.
Report: "✓ Remote branch deleted"

## Step 10 — Switch to main and update
```bash
git checkout main
git pull --ff-only origin main
```
If the pull cannot fast-forward, stop and report.
Report: "✓ Switched to main — up to date"

## Step 11 — Delete the local branch (only after a confirmed merge)
```bash
git branch -D CURRENT_BRANCH
```
`-D` is required because a squash merge leaves the local branch looking unmerged.
Report: "✓ Local branch deleted"

## Final summary
Print only the lines for steps that succeeded:
```
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
/ship-feature complete
✓ Committed — <message>
✓ Pushed — <branch>
✓ PR created and merged
✓ Remote branch deleted
✓ Switched to main
✓ Local branch deleted
Next: run /create-spec for the next feature
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
```
If anything was skipped or failed, replace the "complete" line with
"/ship-feature stopped at Step N" and say what to do next.