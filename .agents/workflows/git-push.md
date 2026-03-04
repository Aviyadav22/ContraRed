---
description: Stage all changes, commit with a message, and push to the GitHub remote (origin)
---

# Git Push Workflow

Push all current changes to the GitHub repository at `https://github.com/Aviyadav22/ContraRed.git`.

## Steps

1. Check the current git status to see what files have changed:
// turbo
```
git status
```

2. Stage all changes:
```
git add -A
```

3. Commit with a descriptive message. Ask the user for a commit message, or if they've already provided one, use it. If no message is given, generate a concise commit message summarizing the staged changes.
```
git commit -m "<commit message>"
```

4. Push to the remote repository on the current branch:
```
git push origin <current-branch>
```

5. Confirm the push was successful by showing the latest commit:
// turbo
```
git log -1 --oneline
```
