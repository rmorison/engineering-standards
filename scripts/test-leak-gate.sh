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

ROOT=$(git rev-parse --show-toplevel)
GITLEAKS=${GITLEAKS:-gitleaks}
CONFIG="$ROOT/.gitleaks.toml"
TEMPLATE="$ROOT/scripts/gitleaks-report.tmpl"
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

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

echo "Leak gate fixtures: $passed passed, $failed failed."
[ "$failed" -eq 0 ]
