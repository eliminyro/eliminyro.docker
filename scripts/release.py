#!/usr/bin/env python3
"""Release automation script for Ansible collection.

Handles version bumping, changelog updates, and GitHub Actions output.

Usage:
    python scripts/release.py [--dry-run]

Commit message prefixes:
    [MAJOR] or [BREAKING] - Major version bump (1.0.0 -> 2.0.0)
    [FEAT] or [FEATURE]   - Minor version bump (1.0.0 -> 1.1.0)
    [FIX] or [BUGFIX]     - Patch version bump (1.0.0 -> 1.0.1)
    [CHORE], [DOCS], etc. - Patch version bump
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path


class BumpType(Enum):
    NONE = "none"
    PATCH = "patch"
    MINOR = "minor"
    MAJOR = "major"


@dataclass
class ReleaseInfo:
    current_version: str
    new_version: str
    bump_type: BumpType
    tag: str
    commits: list[str]
    changelog_content: str
    should_release: bool


def run_git(args: list[str]) -> str:
    """Run a git command and return output."""
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip()


def get_current_version(galaxy_path: Path) -> str:
    """Read current version from galaxy.yml."""
    content = galaxy_path.read_text()
    match = re.search(r'^version:\s*["\']?([^"\'"\n]+)["\']?', content, re.MULTILINE)
    if not match:
        raise ValueError("Could not find version in galaxy.yml")
    return match.group(1).strip()


def get_last_tag() -> str | None:
    """Get the most recent git tag."""
    tag = run_git(["describe", "--tags", "--abbrev=0"])
    return tag if tag else None


def tag_exists(tag: str) -> bool:
    """Check if a git tag already exists."""
    result = run_git(["tag", "-l", tag])
    return result == tag


def get_commits_since_tag(tag: str | None) -> list[str]:
    """Get commit messages since the last tag."""
    if tag:
        output = run_git(["log", f"{tag}..HEAD", "--oneline", "--format=%s"])
    else:
        output = run_git(["log", "--oneline", "--format=%s"])

    if not output:
        return []
    return output.split("\n")


def get_commits_with_hash(tag: str | None) -> list[str]:
    """Get commit messages with hashes since the last tag."""
    if tag:
        output = run_git(["log", f"{tag}..HEAD", "--oneline", "--format=- %s (%h)"])
    else:
        output = run_git(["log", "--oneline", "--format=- %s (%h)"])

    if not output:
        return []
    return output.split("\n")


def determine_bump_type(commits: list[str]) -> BumpType:
    """Determine version bump type from commit messages."""
    if not commits:
        return BumpType.NONE

    major_pattern = re.compile(r"^\[(MAJOR|BREAKING)\]", re.IGNORECASE)
    minor_pattern = re.compile(r"^\[(FEAT|FEATURE)\]", re.IGNORECASE)
    patch_pattern = re.compile(
        r"^\[(FIX|BUGFIX|CHORE|DOCS|STYLE|REFACTOR|TEST)\]", re.IGNORECASE
    )

    for commit in commits:
        if major_pattern.match(commit):
            return BumpType.MAJOR

    for commit in commits:
        if minor_pattern.match(commit):
            return BumpType.MINOR

    for commit in commits:
        if patch_pattern.match(commit):
            return BumpType.PATCH

    return BumpType.NONE


def bump_version(version: str, bump_type: BumpType) -> str:
    """Calculate new version based on bump type."""
    parts = version.split(".")
    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])

    if bump_type == BumpType.MAJOR:
        return f"{major + 1}.0.0"
    elif bump_type == BumpType.MINOR:
        return f"{major}.{minor + 1}.0"
    elif bump_type == BumpType.PATCH:
        return f"{major}.{minor}.{patch + 1}"
    else:
        return version


def extract_unreleased_content(changelog_path: Path) -> str:
    """Extract content from [Unreleased] section of CHANGELOG.md."""
    if not changelog_path.exists():
        return ""

    content = changelog_path.read_text()
    lines = content.split("\n")

    unreleased_idx = None
    next_version_idx = None

    for i, line in enumerate(lines):
        if line.startswith("## [Unreleased]"):
            unreleased_idx = i
        elif (
            unreleased_idx is not None
            and line.startswith("## [")
            and i > unreleased_idx
        ):
            next_version_idx = i
            break

    if unreleased_idx is None:
        return ""

    if next_version_idx is None:
        unreleased_lines = lines[unreleased_idx + 1 :]
    else:
        unreleased_lines = lines[unreleased_idx + 1 : next_version_idx]

    # Strip leading/trailing empty lines
    while unreleased_lines and not unreleased_lines[0].strip():
        unreleased_lines.pop(0)
    while unreleased_lines and not unreleased_lines[-1].strip():
        unreleased_lines.pop()

    return "\n".join(unreleased_lines)


def update_galaxy(galaxy_path: Path, new_version: str) -> None:
    """Update version in galaxy.yml."""
    content = galaxy_path.read_text()
    updated = re.sub(
        r"^version:\s*.*$",
        f"version: {new_version}",
        content,
        flags=re.MULTILINE,
    )
    galaxy_path.write_text(updated)


def update_changelog(
    changelog_path: Path,
    new_version: str,
    commits: list[str],
    unreleased_content: str,
) -> str:
    """Update CHANGELOG.md with new version entry. Returns the changelog entry."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Build new entry
    entry_lines = [f"## [{new_version}] - {today}", "", "### Changes", ""]
    entry_lines.extend(commits)

    if unreleased_content:
        entry_lines.append("")
        entry_lines.append(unreleased_content)

    new_entry = "\n".join(entry_lines)

    if not changelog_path.exists():
        # Create new changelog
        changelog_content = f"""# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

{new_entry}
"""
        changelog_path.write_text(changelog_content)
        return new_entry

    content = changelog_path.read_text()
    lines = content.split("\n")

    # Find [Unreleased] section
    unreleased_idx = None
    next_version_idx = None

    for i, line in enumerate(lines):
        if line.startswith("## [Unreleased]"):
            unreleased_idx = i
        elif (
            unreleased_idx is not None
            and line.startswith("## [")
            and i > unreleased_idx
        ):
            next_version_idx = i
            break

    if unreleased_idx is None:
        # No [Unreleased] section, add at top after header
        # Find first ## line or end of file
        insert_idx = 0
        for i, line in enumerate(lines):
            if line.startswith("## ["):
                insert_idx = i
                break
        else:
            insert_idx = len(lines)

        new_lines = lines[:insert_idx]
        new_lines.append(new_entry)
        new_lines.append("")
        new_lines.extend(lines[insert_idx:])
        changelog_path.write_text("\n".join(new_lines))
        return new_entry

    # Build new content: header + empty [Unreleased] + new entry + old entries
    new_lines = lines[: unreleased_idx + 1]  # Up to and including [Unreleased]
    new_lines.append("")
    new_lines.append(new_entry)

    if next_version_idx is not None:
        new_lines.append("")
        new_lines.extend(lines[next_version_idx:])

    changelog_path.write_text("\n".join(new_lines))
    return new_entry


def set_github_output(name: str, value: str) -> None:
    """Set GitHub Actions output variable."""
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            if "\n" in value:
                # Multiline value
                f.write(f"{name}<<EOF\n{value}\nEOF\n")
            else:
                f.write(f"{name}={value}\n")
    else:
        # Local testing - print to stdout
        print(f"{name}={value}")


def main() -> int:
    dry_run = "--dry-run" in sys.argv

    root = Path(__file__).parent.parent
    galaxy_path = root / "galaxy.yml"
    changelog_path = root / "CHANGELOG.md"

    # Get current state
    current_version = get_current_version(galaxy_path)
    last_tag = get_last_tag()
    commits = get_commits_since_tag(last_tag)
    commits_with_hash = get_commits_with_hash(last_tag)

    print(f"Current version: {current_version}")
    print(f"Last tag: {last_tag or 'none'}")
    print(f"Commits since tag: {len(commits)}")

    # Determine bump type
    bump_type = determine_bump_type(commits)
    print(f"Bump type: {bump_type.value}")

    if bump_type == BumpType.NONE:
        print("No version bump needed")
        set_github_output("should_release", "false")
        set_github_output("version", current_version)
        set_github_output("tag", f"v{current_version}")
        return 0

    # Calculate new version
    new_version = bump_version(current_version, bump_type)
    tag = f"v{new_version}"
    print(f"New version: {new_version}")

    # Pre-flight checks
    if tag_exists(tag):
        print(
            f"::error::Tag {tag} already exists. Aborting to prevent duplicate release."
        )
        return 1

    # Extract unreleased content
    unreleased_content = extract_unreleased_content(changelog_path)

    if not dry_run:
        # Update files
        print("Updating galaxy.yml...")
        update_galaxy(galaxy_path, new_version)

        print("Updating CHANGELOG.md...")
        changelog_entry = update_changelog(
            changelog_path, new_version, commits_with_hash, unreleased_content
        )
    else:
        print("[DRY RUN] Would update galaxy.yml and CHANGELOG.md")
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        changelog_entry = f"## [{new_version}] - {today}\n\n### Changes\n\n"
        changelog_entry += "\n".join(commits_with_hash)
        if unreleased_content:
            changelog_entry += f"\n\n{unreleased_content}"

    # Set outputs
    set_github_output("should_release", "true")
    set_github_output("version", new_version)
    set_github_output("tag", tag)
    set_github_output("changelog", changelog_entry)

    print(f"\nRelease prepared: {tag}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
