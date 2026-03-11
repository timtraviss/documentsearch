# /ship — Ship an enhancement

Run this after completing any improvement to the Document Search app.
It will bump the version number, update the README, reconcile the roadmap
checklist, commit everything, and push to GitHub.

## Steps

### 1. Review what changed
Run `git diff --stat HEAD` and `git diff HEAD` to understand exactly what files were modified and what the changes do. Read any modified files if needed to fully understand the enhancement.

### 2. Bump the version number
Read the current version from `backend/app.py` (look for `APP_VERSION = "X.Y"`).
Increment the minor component by 0.1 (e.g. `0.1` → `0.2`, `0.9` → `1.0`).
Get the current date and time (use the `currentDate` value from memory, plus the current wall-clock time in HH:MM 24-hour format, formatted as `YYYY-MM-DD HH:MM`).

Update the version string in **all three** locations:

**`backend/app.py`** — find and update:
```python
APP_VERSION = "X.Y"
```
Replace with the new version number.

**`setup.py`** — find and update:
```python
'CFBundleVersion': 'X.Y.0',
'CFBundleShortVersionString': 'X.Y',
...
version='X.Y.0',
```
Replace all three with the new version.

**`README.md`** — add or update a `## Version History` section near the bottom (just above `## License`) with a new line:
```
- **vX.Y** — YYYY-MM-DD HH:MM — <one-sentence description of what changed>
```
Prepend the new entry at the top of the list so the most recent version is first.

### 3. Update README.md roadmap
Open `README.md` and make the following updates in the `## Roadmap` section:
- If the enhancement completes a planned item, change its `- [ ]` to `- [x]`.
- If it is a new feature not already listed, add it as `- [x]` under the most appropriate subsection (or create one).
- If it introduces follow-on work, add it as a new `- [ ]` item.

**Do not** rewrite the prose sections (Quick Start, Usage, etc.) unless the enhancement changes how the app is set up or used — in that case, update only the affected paragraphs.

### 4. Stage and commit
Stage only the files that relate to the enhancement plus `README.md`, `backend/app.py`, and `setup.py`:
```
git add <changed source files> README.md backend/app.py setup.py
```
Write a clear, concise commit message (imperative mood, ≤72 chars subject line). Append the co-author trailer:
```
Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

### 5. Push to GitHub
```
git push
```
Confirm the push succeeded and report the commit hash and branch.

### 6. Summary
Print a short summary to the user:
- New version number and timestamp
- What changed (one sentence)
- Which README roadmap items were checked off or added
- The commit hash
