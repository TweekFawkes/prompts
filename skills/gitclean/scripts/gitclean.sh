#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: gitclean.sh [options]

Merge a clean task worktree into main, push main, detach/delete the merged
local branch when safe, and move the retired worktree under delete_me.

Options:
  --repo PATH               Task worktree to retire (default: current repo)
  --main BRANCH             Main branch name (default: main)
  --remote NAME             Remote name (default: origin)
  --target-parent PATH      Parent directory for retired worktrees
                            (default: sibling delete_me next to task worktree)
  --dry-run                 Print planned commands without mutating Git
  --no-fetch                Skip fetch/pull before merging
  --no-push                 Do not push main after merging
  --verified TEXT           Verification command(s) already run before cleanup
  --keep-branch             Do not delete the merged local branch
  --delete-remote-branch    Delete remote task branch after pushing main
  -h, --help                Show this help
USAGE
}

die() {
  printf 'gitclean: %s\n' "$*" >&2
  exit 1
}

die_with_lock_owner() {
  local lock_dir="$1"

  printf 'gitclean: another gitclean appears to be running; lock exists at %s\n' "$lock_dir" >&2
  if [ -f "$lock_dir/owner" ]; then
    printf 'gitclean: lock owner:\n' >&2
    sed 's/^/  /' "$lock_dir/owner" >&2 || true
  fi
  exit 1
}

quote_cmd() {
  printf '+'
  for arg in "$@"; do
    printf ' %q' "$arg"
  done
  printf '\n'
}

run() {
  quote_cmd "$@"
  if [ "$DRY_RUN" -eq 0 ]; then
    "$@"
  fi
}

abs_dir() {
  local path="$1"
  local parent
  local base

  if [ -d "$path" ]; then
    (cd "$path" && pwd -P)
    return 0
  fi

  if [ "$DRY_RUN" -eq 1 ]; then
    parent=$(dirname "$path")
    base=$(basename "$path")
    parent=$(abs_existing_dir "$parent")
    printf '%s/%s\n' "$parent" "$base"
    return 0
  fi

  mkdir -p "$path"
  (cd "$path" && pwd -P)
}

abs_existing_dir() {
  local path="$1"
  [ -d "$path" ] || die "directory does not exist: $path"
  (cd "$path" && pwd -P)
}

git_abs_dir() {
  local repo="$1"
  local mode="$2"
  local path

  if path=$(git -C "$repo" rev-parse --path-format=absolute "$mode" 2>/dev/null); then
    printf '%s\n' "$path"
    return 0
  fi

  path=$(git -C "$repo" rev-parse "$mode")
  case "$path" in
    /*) ;;
    *) path="$repo/$path" ;;
  esac
  (cd "$path" && pwd -P)
}

branch_worktree_path() {
  local repo="$1"
  local branch="$2"

  git -C "$repo" worktree list --porcelain | awk -v wanted="refs/heads/$branch" '
    $1 == "worktree" {
      path = substr($0, 10)
    }
    $1 == "branch" && $2 == wanted {
      print path
      exit
    }
  '
}

remote_exists() {
  git -C "$1" remote get-url "$2" >/dev/null 2>&1
}

ensure_no_git_operation() {
  local repo="$1"
  local label="$2"
  local git_dir

  git_dir=$(git_abs_dir "$repo" --git-dir)
  [ ! -f "$git_dir/MERGE_HEAD" ] || die "$label is in the middle of a merge"
  [ ! -d "$git_dir/rebase-merge" ] || die "$label is in the middle of a rebase"
  [ ! -d "$git_dir/rebase-apply" ] || die "$label is in the middle of a rebase/apply"
  [ ! -f "$git_dir/CHERRY_PICK_HEAD" ] || die "$label is in the middle of a cherry-pick"
}

ensure_clean() {
  local repo="$1"
  local label="$2"
  local status

  status=$(git -C "$repo" status --porcelain)
  if [ -n "$status" ]; then
    printf '%s\n' "$status" >&2
    die "$label has uncommitted or untracked files; commit or remove them intentionally first"
  fi
}

repo="."
main_branch="main"
remote="origin"
target_parent=""
DRY_RUN=0
FETCH=1
PUSH=1
KEEP_BRANCH=0
DELETE_REMOTE_BRANCH=0
verified="not recorded"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --repo)
      [ "$#" -ge 2 ] || die "--repo requires a path"
      repo="$2"
      shift 2
      ;;
    --main)
      [ "$#" -ge 2 ] || die "--main requires a branch name"
      main_branch="$2"
      shift 2
      ;;
    --remote)
      [ "$#" -ge 2 ] || die "--remote requires a name"
      remote="$2"
      shift 2
      ;;
    --target-parent)
      [ "$#" -ge 2 ] || die "--target-parent requires a path"
      target_parent="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --no-fetch)
      FETCH=0
      shift
      ;;
    --no-push)
      PUSH=0
      shift
      ;;
    --verified)
      [ "$#" -ge 2 ] || die "--verified requires text"
      [ -n "$2" ] || die "--verified requires non-empty text"
      verified="$2"
      shift 2
      ;;
    --keep-branch)
      KEEP_BRANCH=1
      shift
      ;;
    --delete-remote-branch)
      DELETE_REMOTE_BRANCH=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "unknown option: $1"
      ;;
  esac
done

task_worktree=$(abs_existing_dir "$repo")
git -C "$task_worktree" rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "not inside a Git worktree: $task_worktree"
task_worktree=$(git -C "$task_worktree" rev-parse --show-toplevel)
task_worktree=$(abs_existing_dir "$task_worktree")

case "$task_worktree" in
  */delete_me/*|*/delete_me) die "worktree is already inside delete_me: $task_worktree" ;;
esac

task_branch=$(git -C "$task_worktree" symbolic-ref --quiet --short HEAD || true)
[ -n "$task_branch" ] || die "task worktree is detached; nothing to merge"

case "$task_branch" in
  "$main_branch"|main|master) die "refusing to retire protected branch: $task_branch" ;;
esac

git -C "$task_worktree" show-ref --verify --quiet "refs/heads/$main_branch" || die "local main branch not found: $main_branch"
git -C "$task_worktree" show-ref --verify --quiet "refs/heads/$task_branch" || die "local task branch not found: $task_branch"

ensure_no_git_operation "$task_worktree" "task worktree"
ensure_clean "$task_worktree" "task worktree"

common_git_dir=$(git_abs_dir "$task_worktree" --git-common-dir)
lock_dir="$common_git_dir/gitclean-main.lock"
lock_acquired=0
temp_main_worktree=""
main_worktree_exists=1

cleanup() {
  local rc=$?
  if [ "$lock_acquired" -eq 1 ] && [ -d "$lock_dir" ]; then
    rm -f "$lock_dir/owner"
    rmdir "$lock_dir" 2>/dev/null || true
  fi
  if [ "$rc" -ne 0 ] && [ -n "$temp_main_worktree" ] && [ -d "$temp_main_worktree" ]; then
    printf 'gitclean: temporary main worktree left for inspection: %s\n' "$temp_main_worktree" >&2
  fi
  exit "$rc"
}
trap cleanup EXIT

if [ "$DRY_RUN" -eq 0 ]; then
  if ! mkdir "$lock_dir" 2>/dev/null; then
    die_with_lock_owner "$lock_dir"
  fi
  lock_acquired=1
  printf 'pid=%s\nworktree=%s\nbranch=%s\n' "$$" "$task_worktree" "$task_branch" > "$lock_dir/owner"
else
  quote_cmd mkdir "$lock_dir"
fi

main_worktree=$(branch_worktree_path "$task_worktree" "$main_branch")
if [ -n "$main_worktree" ]; then
  main_worktree=$(abs_existing_dir "$main_worktree")
else
  parent_dir=$(dirname "$task_worktree")
  stamp=$(date +%Y%m%d%H%M%S)
  temp_main_worktree="$parent_dir/.gitclean-main-$stamp-$$"
  if [ "$DRY_RUN" -eq 1 ]; then
    quote_cmd git -C "$task_worktree" worktree add "$temp_main_worktree" "$main_branch"
    main_worktree_exists=0
  else
    run git -C "$task_worktree" worktree add "$temp_main_worktree" "$main_branch"
  fi
  main_worktree="$temp_main_worktree"
fi

[ "$main_worktree" != "$task_worktree" ] || die "main worktree and task worktree are the same path"

main_read_repo="$main_worktree"
if [ "$main_worktree_exists" -eq 0 ]; then
  main_read_repo="$task_worktree"
  printf 'gitclean: dry run would create temporary main worktree: %s\n' "$main_worktree"
else
  ensure_no_git_operation "$main_worktree" "main worktree"
  ensure_clean "$main_worktree" "main worktree"
fi

if [ "$FETCH" -eq 1 ] && remote_exists "$main_read_repo" "$remote"; then
  run git -C "$main_worktree" fetch --prune "$remote"
  run git -C "$main_worktree" pull --ff-only "$remote" "$main_branch"
fi

if ! git -C "$main_read_repo" merge-base --is-ancestor "$task_branch" "$main_branch"; then
  if [ "$DRY_RUN" -eq 1 ]; then
    quote_cmd git -C "$main_worktree" merge --no-ff "$task_branch"
  else
    quote_cmd git -C "$main_worktree" merge --no-ff "$task_branch"
    if ! git -C "$main_worktree" merge --no-ff "$task_branch"; then
      die "merge failed; resolve or abort in main worktree: $main_worktree"
    fi
  fi
else
  printf 'gitclean: branch %s is already merged into %s\n' "$task_branch" "$main_branch"
fi

if [ "$DRY_RUN" -eq 1 ]; then
  main_commit="$(git -C "$main_read_repo" rev-parse --short "$main_branch") (pre-merge dry run)"
else
  main_commit=$(git -C "$main_worktree" rev-parse --short HEAD)
fi

if [ "$PUSH" -eq 1 ] && remote_exists "$main_read_repo" "$remote"; then
  run git -C "$main_worktree" push "$remote" "$main_branch"
fi

run git -C "$task_worktree" checkout --detach HEAD

branch_cleanup="kept"
if [ "$KEEP_BRANCH" -eq 0 ]; then
  run git -C "$main_worktree" branch -d "$task_branch"
  if [ "$DRY_RUN" -eq 1 ]; then
    branch_cleanup="would delete local"
  else
    branch_cleanup="local deleted"
  fi
fi

remote_cleanup="kept"
if [ "$DELETE_REMOTE_BRANCH" -eq 1 ]; then
  if remote_exists "$main_worktree" "$remote" && git -C "$main_worktree" ls-remote --exit-code --heads "$remote" "$task_branch" >/dev/null 2>&1; then
    run git -C "$main_worktree" push "$remote" --delete "$task_branch"
    if [ "$DRY_RUN" -eq 1 ]; then
      remote_cleanup="would delete remote"
    else
      remote_cleanup="remote deleted"
    fi
  else
    remote_cleanup="remote branch not found"
  fi
fi

if [ -z "$target_parent" ]; then
  target_parent="$(dirname "$task_worktree")/delete_me"
fi
target_parent=$(abs_dir "$target_parent")
if [ "$DRY_RUN" -eq 1 ] && [ ! -d "$target_parent" ]; then
  quote_cmd mkdir -p "$target_parent"
fi
target="$target_parent/$(basename "$task_worktree")-$(date +%Y%m%d%H%M%S)"
if [ -e "$target" ]; then
  target="$target-$$"
fi

run git -C "$main_worktree" worktree move "$task_worktree" "$target"
run git -C "$main_worktree" worktree prune

if [ -n "$temp_main_worktree" ]; then
  run git -C "$target" worktree remove "$temp_main_worktree"
fi

if [ "$DRY_RUN" -eq 1 ]; then
  result="dry-run"
else
  result="complete"
fi

cat <<REPORT
GITCLEAN: $result
BRANCH MERGED: $task_branch
MAIN COMMIT: $main_commit
PUSHED: $([ "$PUSH" -eq 1 ] && remote_exists "$target" "$remote" && printf yes || printf no)
VERIFIED: $verified
RETIRED WORKTREE: $target
BRANCH CLEANUP: $branch_cleanup, $remote_cleanup
REPORT
