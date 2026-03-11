# /ship — Ship an enhancement

Run this after completing any improvement to the Document Search app.
It will update the README, reconcile the roadmap checklist, commit everything, and push to GitHub.

## Steps

### 1. Review what changed
Run `git diff --stat HEAD` and `git diff HEAD` to understand exactly what files were modified and what the changes do. Read any modified files if needed to fully understand the enhancement.

### 2. Update README.md
Open `README.md` and make the following updates:

**Roadmap checklist** (`## Roadmap` section):
- If the enhancement completes a planned item, change its `- [ ]` to `- [x]`.
- If it is a new feature not already listed, add it as `- [x]` under the most appropriate subsection (or create one).
- If it introduces follow-on work, add it as a new `- [ ]` item.

**Do not** rewrite the prose sections (Quick Start, Usage, etc.) unless the enhancement changes how the app is set up or used — in that case, update only the affected paragraphs.

### 3. Stage and commit
Stage only the files that relate to the enhancement plus README.md:
```
git add <changed source files> README.md
```
Write a clear, concise commit message (imperative mood, ≤72 chars subject line). Append the co-author trailer:
```
Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

### 4. Push to GitHub
```
git push
```
Confirm the push succeeded and report the commit hash and branch.

### 5. Summary
Print a short summary to the user:
- What changed (one sentence)
- Which README roadmap items were checked off or added
- The commit hash
