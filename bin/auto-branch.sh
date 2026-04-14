#!/bin/bash
# auto-branch.sh — auto-commit & push tracked changes når Claude stopper
cd /home/victor

# Tjek om der er ændringer i tracked filer
if git diff --quiet && git diff --cached --quiet; then
    exit 0  # Ingen ændringer
fi

CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
DATE=$(date +%Y-%m-%d)
BRANCH="session/$DATE"

# Hvis på main, opret eller skift til dagens session-gren
if [ "$CURRENT_BRANCH" = "main" ]; then
    if git rev-parse --verify "$BRANCH" >/dev/null 2>&1; then
        git checkout "$BRANCH" 2>/dev/null
    else
        git checkout -b "$BRANCH" 2>/dev/null
    fi
fi

# Stage kun ændringer i tracked filer
git add -u

# Commit og push hvis der er noget staged
if ! git diff --cached --quiet; then
    git commit -m "Auto-sync $(date '+%H:%M'): session-ændringer"
    git push -u origin HEAD 2>/dev/null || true
fi
