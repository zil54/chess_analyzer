# -*- coding: utf-8 -*-
r"""
UTF-8 Encoding Validation - Pre-commit Hook (Windows compatible)

Install as .git/hooks/pre-commit in Windows using:
    copy scripts\pre_commit_encoding_check.py .git\hooks\pre-commit

Or add to .git/hooks/pre-commit:
    python scripts\pre_commit_encoding_check.py
"""

import subprocess
import sys
import os
from pathlib import Path


CORRUPTED_PATTERNS = [
    ("\u00e2\u00a9\u00b2", "⩲ (U+2A72)"),     # Corrupted slightly better
    ("\u00e2\u00a9\u00b1", "⩱ (U+2A71)"),     # Corrupted slightly worse
    ("\u00c2\u00b1", "± (U+00B1)"),           # Corrupted plus-minus
    ("\u00e2\u0088\u0093", "∓ (U+2213)"),     # Corrupted minus-plus
    ("\u00e2\u0080\u0093", "– (U+2013)"),     # Corrupted en dash
    ("\u00e2\u0086\u0092", "→ (U+2192)"),     # Corrupted arrow
]


def get_staged_files():
    """Get list of staged files."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True,
            text=True,
            check=True
        )
        return [f for f in result.stdout.strip().split('\n') if f]
    except Exception as e:
        print(f"Error getting staged files: {e}")
        return []


def check_python_encoding_declaration(file_path):
    """Check if Python file has UTF-8 declaration in first 5 lines."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i >= 5:
                    break
                if "# -*- coding: utf-8 -*-" in line or "# coding: utf-8" in line:
                    return True
        return False
    except Exception:
        return True  # Skip if we can't read


def check_for_corrupted_sequences(file_path):
    """Check for corrupted UTF-8 sequences."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            for corrupted, correct in CORRUPTED_PATTERNS:
                if corrupted in content:
                    return corrupted, correct
    except Exception:
        pass
    return None, None


def check_encoding_issues():
    """Run all encoding checks."""
    staged_files = get_staged_files()
    issues = []

    print("Checking UTF-8 encoding compliance...")

    # Check Python files for UTF-8 declaration
    print("\n1. Checking Python files for UTF-8 declaration...")
    python_files = [f for f in staged_files if f.endswith('.py')]

    for file_path in python_files:
        if not os.path.exists(file_path):
            continue
        if any(skip in file_path for skip in ['__pycache__', 'node_modules', '.venv']):
            continue

        if not check_python_encoding_declaration(file_path):
            line_count = len(open(file_path, 'r', encoding='utf-8').readlines())
            if line_count > 2:
                msg = f"⚠ Warning: {file_path} missing UTF-8 declaration"
                print(msg)
                issues.append((msg, "warning"))

    # Check for corrupted UTF-8 sequences
    print("\n2. Checking for corrupted UTF-8 sequences...")
    for file_path in staged_files:
        if not os.path.exists(file_path):
            continue
        # Skip documentation files (they contain unicode examples)
        if file_path.endswith(('.md', '.txt', '.pyc', '.pyo', '.png', '.jpg', '.bin', '.db')):
            continue

        corrupted, correct = check_for_corrupted_sequences(file_path)
        if corrupted:
            msg = f"✗ ERROR: Corrupted UTF-8 in {file_path}: '{corrupted}' → '{correct}'"
            print(msg)
            issues.append((msg, "error"))

    # Print summary
    print("\n" + "="*60)
    errors = [i for i in issues if i[1] == "error"]
    warnings = [i for i in issues if i[1] == "warning"]

    if errors:
        print(f"\n✗ COMMIT BLOCKED: {len(errors)} encoding error(s) found:")
        for msg, _ in errors:
            print(f"  {msg}")
        return False

    if warnings:
        print(f"\n⚠ {len(warnings)} warning(s):")
        for msg, _ in warnings:
            print(f"  {msg}")
        print("\nWarnings are informational only - commit will proceed")

    if not errors and not warnings:
        print("\n✓ UTF-8 encoding check passed!")

    return True


if __name__ == "__main__":
    success = check_encoding_issues()
    sys.exit(0 if success else 1)


