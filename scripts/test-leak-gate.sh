#!/bin/sh
# Proves each leak-gate rule fails on a planted leak and passes its allowlisted
# cases, before any real scan is trusted. CI runs this on every pull request
# (.github/workflows/leaks.yml); run it locally with the pinned gitleaks on PATH,
# or with GITLEAKS set to its path.
#
# Planted values are assembled from shell variables at run time, so this file
# matches none of the rules it tests. Fixtures live in a temporary directory and
# never enter a commit.
#
# A planted leak must exit exactly 3. gitleaks also exits non-zero on a missing
# config, a bad path or a bad range, so "it failed" alone proves nothing. Every
# fixture also checks that the planted text is absent from the output, because
# the output of a CI run is public.
#
# Usage:  sh scripts/test-leak-gate.sh
# Exits non-zero if any fixture fails. Needs git and gitleaks; nothing else.

set -eu

# The wrapper reads its value list from git config. Point git at an empty global
# config so a maintainer's real list is never read by a fixture.
GIT_CONFIG_NOSYSTEM=1
GIT_CONFIG_GLOBAL=$(mktemp)
export GIT_CONFIG_NOSYSTEM GIT_CONFIG_GLOBAL

ROOT=$(git rev-parse --show-toplevel)
GITLEAKS=${GITLEAKS:-gitleaks}
CONFIG="$ROOT/.gitleaks.toml"
TEMPLATE="$ROOT/scripts/gitleaks-report.tmpl"
WORK=$(mktemp -d)
trap 'rm -rf "$WORK" "$GIT_CONFIG_GLOBAL"' EXIT

passed=0
failed=0
ok() { passed=$((passed + 1)); }
bad() { echo "FAIL: $*" >&2; failed=$((failed + 1)); }

# The flags every gitleaks call in CI uses: no verbose output, which prints the
# line around a match, and findings only through the committed template.
scan() {
  "$GITLEAKS" "$@" --config "$CONFIG" --no-banner --no-color --log-level warn \
    --redact --ignore-gitleaks-allow --exit-code 3 \
    --report-format template --report-template "$TEMPLATE" --report-path -
}

# run <expected-exit> <description> <secret-that-must-not-print> -- <gitleaks args>
run() {
  want=$1 desc=$2 secret=$3
  shift 4
  rc=0
  out=$(scan "$@" 2>&1) || rc=$?
  if [ "$rc" -ne "$want" ]; then
    bad "$desc: exit $rc, expected $want"
    printf '%s\n' "$out" | sed 's/^/    /' >&2
    return
  fi
  if [ -n "$secret" ]; then
    case $out in
      *"$secret"*) bad "$desc: the planted text appears in the output"; return ;;
    esac
  fi
  ok
}

# fixture <name> <line>: a directory holding one file with one line.
fixture() {
  mkdir -p "$WORK/$1"
  printf '%s\n' "$2" > "$WORK/$1/notes.md"
  echo "$WORK/$1"
}

H=/home
U=/Users
NAME=somebody-example
# A token in GitHub's personal access token format, assembled so no line of this
# file holds it whole. It is random, not a credential.
TOKEN="ghp_""Xq7Lm2Rt9Vb4Nc8Kd1Fs6Hj3Wp5Zy0Ga2Eu"

# --- Shape rule ---------------------------------------------------------------

run 3 "home path under an unlisted name" "$NAME" -- \
  dir "$(fixture unlisted "see $H/$NAME/project")"
run 3 "macOS home path, name ending a sentence" "$NAME" -- \
  dir "$(fixture mac "it lives in $U/$NAME.")"
run 3 "home path with no further segment" "$NAME" -- \
  dir "$(fixture bare "cd $H/$NAME")"
for dir in runner linuxbrew vscode node user you username; do
  run 0 "allowlisted $dir" "" -- dir "$(fixture "allow-$dir" "path $H/$dir/work")"
done
run 0 "allowlisted name ending a sentence" "" -- \
  dir "$(fixture allow-dot "the checkout is in $H/runner.")"
run 0 "relative home/ link" "" -- dir "$(fixture rel "see [x](home/$NAME/y.md)")"
run 0 "tilde path through home/" "" -- dir "$(fixture tilde "~$H/$NAME/x")"
run 0 "URL path containing /home/" "" -- dir "$(fixture url "https://example.com$H/$NAME/x")"

# --- Credentials and suppression -----------------------------------------------

run 3 "credential in gitleaks' default format" "$TOKEN" -- \
  dir "$(fixture token "export GITHUB_TOKEN=$TOKEN")"
run 3 "credential and home path on one line" "$NAME" -- \
  dir "$(fixture both "GITHUB_TOKEN=$TOKEN in $H/$NAME/.env")"
run 3 "credential and home path on one line (token text)" "$TOKEN" -- \
  dir "$WORK/both"
run 3 "inline gitleaks:allow does not suppress" "$NAME" -- \
  dir "$(fixture allow-comment "see $H/$NAME/x # gitleaks:allow")"

# --- Commit range ---------------------------------------------------------------

REPO="$WORK/repo"
git init -q "$REPO"
g() { git -C "$REPO" -c user.name=fixture -c user.email=fixture@example.invalid "$@"; }
printf 'clean\n' > "$REPO/README.md"
g add README.md && g commit -q -m base
base=$(g rev-parse HEAD)
printf 'see %s\n' "$H/$NAME/x" > "$REPO/leak.md"
g add leak.md && g commit -q -m add
g rm -q leak.md && g commit -q -m remove
run 3 "leak added then removed within a range" "$NAME" -- \
  git "$REPO" --log-opts="$base..HEAD"
run 0 "same tree scanned as a snapshot" "" -- dir "$(fixture snapshot "clean")"
printf 'more\n' >> "$REPO/README.md"
g add README.md && g commit -q -m clean
run 0 "clean range" "" -- git "$REPO" --log-opts="HEAD~1..HEAD"

# --- An error is not a leak -----------------------------------------------------

rc=0
"$GITLEAKS" dir "$WORK/does-not-exist" --config "$CONFIG" --no-banner --exit-code 3 \
  >/dev/null 2>&1 || rc=$?
if [ "$rc" -eq 3 ] || [ "$rc" -eq 0 ]; then
  bad "a missing scan path exited $rc; the fixtures cannot tell an error from a leak"
else
  ok
fi

# --- The local wrapper: scripts/leak-gate.sh ---------------------------------------

GATE="$ROOT/scripts/leak-gate.sh"
# An invented value, standing in for a private hostname. Value rules exist only
# on a developer's machine, so no committed rule matches it.
VALUE=fixture-private.example
LISTS="$WORK/lists"
mkdir -p "$LISTS"
printf '# private values\n\n%s\n' "$VALUE" > "$LISTS/values"

# wrepo <name>: a fresh repository with the committed rules and a clean commit.
wrepo() {
  r="$WORK/$1"
  git init -q "$r"
  cp "$CONFIG" "$r/.gitleaks.toml"
  printf 'clean\n' > "$r/README.md"
  git -C "$r" add -A
  git -C "$r" -c user.name=fixture -c user.email=fixture@example.invalid commit -q -m base
  echo "$r"
}
wcommit() { git -C "$1" add -A && git -C "$1" -c user.name=fixture -c user.email=fixture@example.invalid commit -q -m "$2"; }

# gate <expected-exit> <description> <must-print or ""> <repo> <mode args...>
# The value must never appear in the output, whatever the exit.
gate() {
  want=$1 desc=$2 expect=$3 repo=$4
  shift 4
  rc=0
  out=$(cd "$repo" && GITLEAKS="$GITLEAKS" sh "$GATE" "$@" 2>&1) || rc=$?
  if [ "$rc" -ne "$want" ]; then
    bad "wrapper, $desc: exit $rc, expected $want"
    printf '%s\n' "$out" | sed 's/^/    /' >&2
    return
  fi
  case $out in
    *"$VALUE"*|*fixture-private*) bad "wrapper, $desc: the value appears in the output"; return ;;
  esac
  if [ -n "$expect" ]; then
    case $out in
      *"$expect"*) ;;
      *) bad "wrapper, $desc: output lacks '$expect'"; return ;;
    esac
  fi
  ok
}
declare_list() { git -C "$1" config leakgate.values "$2"; }

R=$(wrepo w-content)
declare_list "$R" "$LISTS/values"
printf 'deploy to %s\n' "$VALUE" > "$R/notes.md"
git -C "$R" add notes.md
gate 1 "value staged in a file" "notes.md:1" "$R" staged
wcommit "$R" leak
gate 1 "value in a committed range" "[private-value-3]" "$R" range HEAD~1..HEAD

R=$(wrepo w-path)
declare_list "$R" "$LISTS/values"
mkdir -p "$R/$VALUE"
printf 'nothing here\n' > "$R/$VALUE/notes.md"
wcommit "$R" path
gate 1 "value only in a file name" "a tracked path matches" "$R" range HEAD~1..HEAD

R=$(wrepo w-path-content)
declare_list "$R" "$LISTS/values"
mkdir -p "$R/docs-$VALUE"
printf 'see %s\n' "$VALUE" > "$R/docs-$VALUE/notes.md"
wcommit "$R" both
gate 1 "value in content inside a value-named directory" "file name withheld" "$R" range HEAD~1..HEAD

R=$(wrepo w-errors)
declare_list "$R" "$LISTS/missing"
gate 2 "declared list is missing" "$LISTS/missing" "$R" staged
cp "$LISTS/values" "$R/values"
declare_list "$R" "$R/values"
gate 2 "declared list inside the repository" "inside this repository" "$R" staged
rm "$R/values"
printf '# only a comment\n\n   \n' > "$LISTS/empty"
declare_list "$R" "$LISTS/empty"
gate 2 "list with no values" "has no values" "$R" staged
printf '# a\n%s\\Etail\n' "$VALUE" > "$LISTS/quote"
declare_list "$R" "$LISTS/quote"
gate 2 "list line containing \\E" "line 2" "$R" staged
printf '%s\377\n' "$VALUE" > "$LISTS/utf8"
declare_list "$R" "$LISTS/utf8"
gate 2 "list line that is not UTF-8" "line 1" "$R" staged
printf '%s\001x\n' "$VALUE" > "$LISTS/ctrl"
declare_list "$R" "$LISTS/ctrl"
gate 2 "list line with a control character" "line 1" "$R" staged
printf 'abc\n' > "$LISTS/short"
declare_list "$R" "$LISTS/short"
gate 2 "list value shorter than four characters" "line 1" "$R" staged

R=$(wrepo w-crlf)
printf '\357\273\277# values\r\n%s\r\n' "$VALUE" > "$LISTS/crlf"
declare_list "$R" "$LISTS/crlf"
printf 'deploy to %s\n' "$VALUE" > "$R/notes.md"
wcommit "$R" leak
gate 1 "CRLF list with a byte-order mark" "[private-value-2]" "$R" range HEAD~1..HEAD

R=$(wrepo w-undeclared)
gate 0 "no declaration" "value rules skipped" "$R" staged
git config --global leakgate.values "$LISTS/values"
git -C "$R" config leakgate.values none
gate 0 "local opt-out overrides a global declaration" "value rules skipped" "$R" staged
git -C "$R" config --unset leakgate.values
git config --global leakgate.values "$LISTS/missing"
git -C "$R" config leakgate.values "$LISTS/values"
gate 0 "local path overrides a global path" "no leaks found" "$R" staged
git config --global --unset leakgate.values

R=$(wrepo w-ignore)
declare_list "$R" "$LISTS/values"
printf 'notes.md:private-value-3:1\n' > "$R/.gitleaksignore"
gate 2 ".gitleaksignore naming a value rule" "cannot be suppressed" "$R" staged

R=$(wrepo w-history)
declare_list "$R" "$LISTS/values"
printf 'see %s\n' "$VALUE" > "$R/old.md"
wcommit "$R" old
git -C "$R" rm -q old.md
wcommit "$R" removed
gate 1 "history: value in a removed file" "[private-value-3]" "$R" history
R=$(wrepo w-message)
declare_list "$R" "$LISTS/values"
git -C "$R" -c user.name=fixture -c user.email=fixture@example.invalid \
  commit -q --allow-empty -m "deploy to $VALUE"
gate 1 "history: value in a commit message" "a commit message matches" "$R" history
R=$(wrepo w-tag)
declare_list "$R" "$LISTS/values"
git -C "$R" -c user.name=fixture -c user.email=fixture@example.invalid \
  tag -a v1 -m "released to $VALUE"
gate 1 "history: value in an annotated tag message" "an annotated tag message matches" "$R" history

R=$(wrepo w-clean)
declare_list "$R" "$LISTS/values"
gate 0 "clean history" "no leaks found" "$R" history

echo "Leak gate fixtures: $passed passed, $failed failed."
[ "$failed" -eq 0 ]
