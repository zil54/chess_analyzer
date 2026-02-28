#!/bin/bash
# Remove sf.exe from all git history
git filter-branch --tree-filter 'rm -f app/engine/sf.exe' -f -- --all

# Clean up
rm -rf .git/refs/original/
git reflog expire --all --expire=now
git gc --prune=now --aggressive

echo "sf.exe removed from all history"

