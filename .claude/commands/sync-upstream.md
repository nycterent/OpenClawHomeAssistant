---
description: Sync fork with upstream techartdev/OpenClawHomeAssistant and push to origin
allowed-tools: Bash(git *), Bash(grep *), Read, Grep
---

## Sync upstream into this fork

You are syncing the fork (origin: nycterent/OpenClawHomeAssistant) with upstream (techartdev/OpenClawHomeAssistant).

### Steps

1. **Ensure clean working tree** — run `git status`. If there are uncommitted changes, STOP and tell the user to commit or stash first.

2. **Fetch upstream** — run `git fetch upstream`. If the `upstream` remote doesn't exist, add it:
   ```
   git remote add upstream https://github.com/techartdev/OpenClawHomeAssistant.git
   ```

3. **Show what's new** — run `git log --oneline HEAD..upstream/main` to show incoming commits. Summarize the changes for the user (version bumps, new features, fixes).

4. **Merge upstream/main** — run `git merge upstream/main`. If there are conflicts:
   - List all conflicted files
   - For each conflict, show the diff and explain both sides
   - Ask the user how to resolve before making changes
   - NEVER auto-resolve conflicts without user approval

5. **Post-merge version checks** — After a successful merge (or after conflicts are resolved), check for version coherence:
   - Read `openclaw_assistant/config.yaml` and extract the `version:` field
   - Read `openclaw_assistant/Dockerfile` and find the `openclaw@` version in the `npm install -g` line
   - Compare with what upstream had — the fork's add-on version should always be **>=** upstream
   - If upstream bumped the OpenClaw package version, flag it clearly
   - Report both versions to the user

6. **Check for new/changed options** — diff `openclaw_assistant/config.yaml` between HEAD and the merge base to see if upstream added new options. If so, remind the user to check `translations/` files (bg, de, en, es, pl) for matching entries.

7. **Version bump decision** — Ask the user if they want to bump the add-on version in `config.yaml`. Suggest the next patch version.

8. **Push** — Only push to origin when the user explicitly approves:
   ```
   git push origin main
   ```

### Rules
- NEVER force-push
- NEVER auto-resolve merge conflicts
- NEVER push without explicit user approval
- Always summarize what changed before and after the merge
- If the merge is a no-op (already up to date), say so and stop
