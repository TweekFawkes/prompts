#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  create_worktree.sh <task-slug> [options]

Creates a timestamped agent/<task-slug>-<timestamp> branch and a sibling
worktree at <repo>-worktrees/<task-slug>-<timestamp>.

Options:
  --base REF       Base ref to branch from. Default: origin/main, then main, then HEAD.
  --branch NAME    Branch name to create. Default: agent/<task-slug>-<timestamp>.
  --path PATH      Worktree path. Default: sibling <repo>-worktrees/<task-slug>-<timestamp>.
  --no-fetch       Skip git fetch --prune origin.
  --dry-run        Print commands without creating the branch or worktree.
  -h, --help       Show this help.
EOF
}

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

warn() {
  printf 'warning: %s\n' "$*" >&2
}

abs_path_maybe_missing() {
  local path="$1"
  local suffix=""
  local probe
  local prefix

  case "$path" in
    /*) ;;
    *) path="$(pwd)/$path" ;;
  esac

  probe="$path"
  while [ ! -e "$probe" ]; do
    suffix="/$(basename "$probe")$suffix"
    probe="$(dirname "$probe")"
  done

  if [ -d "$probe" ]; then
    prefix="$(cd "$probe" && pwd -P)"
  else
    prefix="$(cd "$(dirname "$probe")" && pwd -P)/$(basename "$probe")"
  fi

  printf '%s%s\n' "$prefix" "$suffix"
}

ensure_outside_repo() {
  local path="$1"
  local repo="$2"

  case "$path/" in
    "$repo/"*) die "worktree path must be outside the tracked repo: $path" ;;
  esac
}

print_cmd() {
  printf '+'
  for arg in "$@"; do
    printf ' %q' "$arg"
  done
  printf '\n'
}

run() {
  print_cmd "$@"
  if [ "$dry_run" -eq 0 ]; then
    "$@"
  fi
}

slug=""
base_ref=""
branch=""
worktree_path=""
fetch_origin=1
dry_run=0
custom_branch=0
custom_path=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --base)
      shift
      [ "$#" -gt 0 ] || die "--base requires a ref"
      base_ref="$1"
      ;;
    --branch)
      shift
      [ "$#" -gt 0 ] || die "--branch requires a branch name"
      branch="$1"
      custom_branch=1
      ;;
    --path)
      shift
      [ "$#" -gt 0 ] || die "--path requires a path"
      worktree_path="$1"
      custom_path=1
      ;;
    --no-fetch)
      fetch_origin=0
      ;;
    --dry-run)
      dry_run=1
      ;;
    --)
      shift
      break
      ;;
    -*)
      die "unknown option: $1"
      ;;
    *)
      if [ -z "$slug" ]; then
        slug="$1"
      else
        die "unexpected argument: $1"
      fi
      ;;
  esac
  shift
done

[ -n "$slug" ] || die "missing task slug"

safe_slug="$(printf '%s' "$slug" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//; s/-+/-/g')"
[ -n "$safe_slug" ] || die "task slug must contain at least one letter or digit"
if [ "$safe_slug" != "$slug" ]; then
  warn "normalized task slug '$slug' to '$safe_slug'"
fi

repo_root="$(git rev-parse --show-toplevel 2>/dev/null)" || die "not inside a Git worktree"
repo_root="$(cd "$repo_root" && pwd -P)"
repo_name="$(basename "$repo_root")"
repo_parent="$(dirname "$repo_root")"
timestamp="$(date +%Y%m%d%H%M%S)"

dirty_status="$(git -C "$repo_root" status --short)"
if [ -n "$dirty_status" ]; then
  warn "source worktree has uncommitted changes; they will not be copied into the new worktree"
  printf '%s\n' "$dirty_status" | sed -n '1,20p' >&2
fi

if [ "$fetch_origin" -eq 1 ] && git -C "$repo_root" remote get-url origin >/dev/null 2>&1; then
  if ! run git -C "$repo_root" fetch --prune origin; then
    warn "fetch failed; continuing with local refs"
  fi
fi

if [ -z "$base_ref" ]; then
  if git -C "$repo_root" rev-parse --verify --quiet "origin/main^{commit}" >/dev/null; then
    base_ref="origin/main"
  elif git -C "$repo_root" rev-parse --verify --quiet "main^{commit}" >/dev/null; then
    base_ref="main"
  else
    base_ref="HEAD"
  fi
fi

git -C "$repo_root" rev-parse --verify --quiet "${base_ref}^{commit}" >/dev/null || die "base ref is not a commit: $base_ref"

attempt=1
selected_suffix=""
selected=0
while [ "$attempt" -le 99 ]; do
  if [ "$attempt" -eq 1 ]; then
    suffix=""
  else
    suffix="-$attempt"
  fi

  if [ "$custom_branch" -eq 0 ]; then
    candidate_branch="agent/${safe_slug}-${timestamp}${suffix}"
  else
    candidate_branch="$branch"
  fi

  if [ "$custom_path" -eq 0 ]; then
    candidate_path="${repo_parent}/${repo_name}-worktrees/${safe_slug}-${timestamp}${suffix}"
  else
    candidate_path="$worktree_path"
  fi

  git -C "$repo_root" check-ref-format --branch "$candidate_branch" >/dev/null || die "invalid branch name: $candidate_branch"
  candidate_path="$(abs_path_maybe_missing "$candidate_path")"
  ensure_outside_repo "$candidate_path" "$repo_root"

  if git -C "$repo_root" show-ref --verify --quiet "refs/heads/$candidate_branch"; then
    [ "$custom_branch" -eq 0 ] || die "branch already exists: $candidate_branch"
    attempt=$((attempt + 1))
    continue
  fi

  if [ -e "$candidate_path" ]; then
    [ "$custom_path" -eq 0 ] || die "worktree path already exists: $candidate_path"
    attempt=$((attempt + 1))
    continue
  fi

  branch="$candidate_branch"
  worktree_path="$candidate_path"
  selected_suffix="$suffix"
  selected=1
  break
done

[ "$selected" -eq 1 ] || die "could not find an unused branch/path suffix after 99 attempts"
if [ -n "$selected_suffix" ]; then
  warn "using collision suffix '$selected_suffix' for branch/path"
fi

printf 'source:   %s\n' "$repo_root"
printf 'base:     %s\n' "$base_ref"
printf 'branch:   %s\n' "$branch"
printf 'worktree: %s\n' "$worktree_path"

run mkdir -p "$(dirname "$worktree_path")"
run git -C "$repo_root" worktree add -b "$branch" "$worktree_path" "$base_ref"

if [ "$dry_run" -eq 1 ]; then
  printf 'dry-run: no worktree created\n'
else
  printf '\ncreated worktree:\n'
  printf '  cd %s\n' "$worktree_path"
  printf '  git status --short\n'
fi
