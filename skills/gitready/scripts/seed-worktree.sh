#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  seed-worktree.sh [options]

Copies gitignored local state (env files, local secrets, seeded config —
anything a fresh `git worktree add` checkout won't have because it was never
tracked) from the repo's main checkout into the worktree this script is run
from. A fresh worktree only contains tracked files, so without this step a
newly created worktree is often missing what it needs to actually run.

Driven by a tracked config file, .worktree-seed-paths, at the repo root: one
path per line, relative to the repo root (files or directories), blank lines
and lines starting with # ignored. See worktree-seed-paths.example next to
this script for the format. Nothing is copied until that file exists —
this script is a safe no-op by default.

Options:
  --worktree PATH   Worktree to seed. Default: the worktree containing the
                     current directory.
  --config PATH     Seed-paths config file. Default: <worktree>/.worktree-seed-paths.
  --force           Overwrite files that already exist in the worktree.
                     Default: skip anything already present, so local edits
                     inside the worktree are never clobbered.
  --dry-run         Print what would be copied without copying anything.
  -h, --help        Show this help.

This script is a template: the interesting part is what you list in
.worktree-seed-paths, not this script. A common last step is redacting
anything a worktree should never carry — e.g. a copied .env's production
credentials, since worktrees are for task work, not prod deploys. Add that
redaction inline after the copy loop below if your project needs it.
EOF
}

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

warn() {
  printf 'warning: %s\n' "$*" >&2
}

worktree=""
config=""
force=0
dry_run=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --worktree)
      shift
      [ "$#" -gt 0 ] || die "--worktree requires a path"
      worktree="$1"
      ;;
    --config)
      shift
      [ "$#" -gt 0 ] || die "--config requires a path"
      config="$1"
      ;;
    --force)
      force=1
      ;;
    --dry-run)
      dry_run=1
      ;;
    *)
      die "unknown argument: $1"
      ;;
  esac
  shift
done

if [ -z "$worktree" ]; then
  worktree="$(git rev-parse --show-toplevel 2>/dev/null)" || die "not inside a Git worktree; pass --worktree"
fi
worktree="$(cd "$worktree" && pwd -P)"

common_dir="$(git -C "$worktree" rev-parse --git-common-dir 2>/dev/null)" || die "not a Git repo: $worktree"
case "$common_dir" in
  /*) ;;
  *) common_dir="$worktree/$common_dir" ;;
esac
main_checkout="$(cd "$(dirname "$common_dir")" && pwd -P)"

if [ "$worktree" = "$main_checkout" ]; then
  echo "seed-worktree: running in the main checkout — nothing to seed."
  exit 0
fi

[ -n "$config" ] || config="$worktree/.worktree-seed-paths"

if [ ! -f "$config" ]; then
  cat <<EOF
seed-worktree: no config at $config — nothing to seed.
To use this script, create .worktree-seed-paths at the repo root listing the
gitignored files/directories each worktree needs (one per line, relative to
the repo root). See worktree-seed-paths.example next to this script.
EOF
  exit 0
fi

printf 'seeding %s\n  from %s\n  using %s\n' "$worktree" "$main_checkout" "$config"

copied=0
skipped=0
missing=0

while IFS= read -r line || [ -n "$line" ]; do
  # Strip comments and surrounding whitespace; skip blank lines.
  rel="${line%%#*}"
  rel="$(printf '%s' "$rel" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')"
  [ -n "$rel" ] || continue

  src="$main_checkout/$rel"
  dst="$worktree/$rel"

  if [ ! -e "$src" ]; then
    warn "skip $rel (not present in main checkout: $src)"
    missing=$((missing + 1))
    continue
  fi

  if [ -e "$dst" ] && [ "$force" -eq 0 ]; then
    echo "seed-worktree: skip $rel (already present in worktree; use --force to overwrite)"
    skipped=$((skipped + 1))
    continue
  fi

  if [ "$dry_run" -eq 1 ]; then
    echo "dry-run: would copy $rel"
    continue
  fi

  mkdir -p "$(dirname "$dst")"
  cp -R "$src" "$dst"
  echo "seed-worktree: copied $rel"
  copied=$((copied + 1))
done <"$config"

if [ "$dry_run" -eq 1 ]; then
  echo "dry-run: no files copied"
else
  printf 'seed-worktree: done. copied=%d skipped=%d missing=%d\n' "$copied" "$skipped" "$missing"
fi
