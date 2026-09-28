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
# A CI runner has no git identity, and git cannot guess one there. Refuse to guess
# here too, so a fixture that needs an identity fails locally the way it would in CI.
git config --global user.useConfigOnly true
GIT_AUTHOR_NAME=fixture GIT_AUTHOR_EMAIL=fixture@example.invalid
GIT_COMMITTER_NAME=fixture GIT_COMMITTER_EMAIL=fixture@example.invalid
export GIT_AUTHOR_NAME GIT_AUTHOR_EMAIL GIT_COMMITTER_NAME GIT_COMMITTER_EMAIL

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
# The allow marker is assembled so no copied file carries it: the Python
# standard's pragma check rejects the literal outside tests/.
run 3 "inline allow comment does not suppress" "$NAME" -- \
  dir "$(fixture allow-comment "see $H/$NAME/x # gitleaks"":allow")"

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
  git "$REPO" --log-opts="--text -m $base..HEAD"
run 0 "same tree scanned as a snapshot" "" -- dir "$(fixture snapshot "clean")"
printf 'more\n' >> "$REPO/README.md"
g add README.md && g commit -q -m clean
run 0 "clean range" "" -- git "$REPO" --log-opts="--text -m HEAD~1..HEAD"

# A merge that introduces content, as a conflict resolution does. git log shows no
# diff for a merge commit unless -m is given, which is why CI passes it.
merge_base=$(g rev-parse HEAD)
g checkout -q -b side
printf 'side\n' > "$REPO/side.md"
g add side.md && g commit -q -m side
g checkout -q -
g merge -q --no-ff --no-commit side >/dev/null 2>&1 || { echo "fixture setup: merge failed" >&2; exit 2; }
printf 'see %s\n' "$H/$NAME/merged" > "$REPO/merged.md"
g add merged.md && g commit -q -m merge
run 3 "leak introduced by a merge commit" "$NAME" -- git "$REPO" --log-opts="--text -m $merge_base..HEAD"

# A .gitattributes entry that unsets the diff attribute makes git print "Binary
# files differ" for a text file, which gitleaks skips. CI passes --text.
printf 'hidden.txt -diff\n' > "$REPO/.gitattributes"
printf 'see %s\n' "$H/$NAME/hidden" > "$REPO/hidden.txt"
attr_base=$(g rev-parse HEAD)
g add .gitattributes hidden.txt && g commit -q -m hidden
g rm -q hidden.txt && g commit -q -m unhidden
run 3 "leak behind a -diff attribute, added then removed" "$NAME" -- \
  git "$REPO" --log-opts="--text -m $attr_base..HEAD"

# --text also puts binary content in front of the rules. Pinned so a change in
# gitleaks' handling of it is noticed: a NUL-bearing file is scanned.
bin_base=$(g rev-parse HEAD)
printf 'bin\000 see %s\n' "$H/$NAME/bin" > "$REPO/blob.dat"
g add blob.dat && g commit -q -m binary
run 3 "binary content is scanned under --text" "$NAME" -- git "$REPO" --log-opts="--text -m $bin_base..HEAD"

# --- Accepted gaps, pinned so a gitleaks upgrade that changes them is noticed ---

# Extending the default rules inherits gitleaks' default path allowlist, so the
# shape rule does not read lock files. process/repository-standards.md states it.
mkdir -p "$WORK/lockfile"
printf '{"resolved": "file:%s/%s/lib"}\n' "$H" "$NAME" > "$WORK/lockfile/package-lock.json"
run 0 "known gap: shape rule skips package-lock.json" "" -- dir "$WORK/lockfile"
# It also inherits the default global allowlist, which exempts some user
# directory names, such as one letter repeated.
run 0 "known gap: default allowlist exempts a repeated-letter name" "" -- \
  dir "$(fixture repeated "see $H/aaaa/x")"

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
# The value must never appear in the output, whatever the exit. Two optional
# settings apply to the next call only, and are cleared by it:
#   hook_git_dir  exported as GIT_DIR for the wrapper alone, as git does for a
#                 hook. Never exported here: while it is set, every git command
#                 in this script would act on that repository.
#   absent        text the output must not contain.
hook_git_dir=
absent=
gate() {
  want=$1 desc=$2 expect=$3 repo=$4
  shift 4
  git_dir=$hook_git_dir must_lack=$absent
  hook_git_dir= absent=
  rc=0
  out=$(cd "$repo" &&
    if [ -n "$git_dir" ]; then GIT_DIR=$git_dir; export GIT_DIR; fi &&
    GITLEAKS="$GITLEAKS" sh "$GATE" "$@" 2>&1) || rc=$?
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
  if [ -n "$must_lack" ]; then
    case $out in
      *"$must_lack"*)
        bad "wrapper, $desc: output has '$must_lack'"
        printf '%s\n' "$out" | sed 's/^/    /' >&2
        return ;;
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

# The dotfiles warning answers for the list's directory, also under a hook. Git
# exports GIT_DIR to hooks, and with it set, git -C <list dir> answers for the
# repository being committed to. Every repository is built before GIT_DIR is set.
DOT="$WORK/w-dotfiles"
git init -q "$DOT"
cp "$LISTS/values" "$DOT/values"
R=$(wrepo w-hook-env)
declare_list "$R" "$LISTS/values"
hook_git_dir="$R/.git" absent="inside a git work tree"
gate 0 "hook environment, list in no repository: no warning" "no leaks found" "$R" staged
declare_list "$R" "$DOT/values"
gate 0 "list in another repository that does not ignore it: warning" "inside a git work tree" "$R" staged
hook_git_dir="$R/.git"
gate 0 "hook environment, list in another repository that does not ignore it: warning" \
  "inside a git work tree" "$R" staged
printf 'values\n' > "$DOT/.gitignore"
hook_git_dir="$R/.git" absent="inside a git work tree"
gate 0 "hook environment, list ignored by its repository: no warning" "no leaks found" "$R" staged

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

# Usage errors exit 2, never 0.
gate 2 "no mode" "usage" "$R"
gate 2 "unknown mode" "usage" "$R" everything
gate 2 "range without its argument" "usage" "$R" range
gate 0 "empty range is reported" "holds no commits" "$R" range HEAD..HEAD

# The documented form of the declaration: a path under ~/.
R=$(wrepo w-tilde)
mkdir -p "$WORK/home/lists"
cp "$LISTS/values" "$WORK/home/lists/values"
git -C "$R" config leakgate.values '~/lists/values'
printf 'deploy to %s\n' "$VALUE" > "$R/notes.md"
git -C "$R" add notes.md
saved_home=$HOME
HOME="$WORK/home"
gate 1 "declaration under ~/" "notes.md:1" "$R" staged
HOME=$saved_home

R=$(wrepo w-toml)
printf "# a\n%s'''tail\n" "$VALUE" > "$LISTS/toml"
declare_list "$R" "$LISTS/toml"
gate 2 "list line containing three single quotes" "line 2" "$R" staged

R=$(wrepo w-lone-cr)
printf '# values\r%s\r' "$VALUE" > "$LISTS/lonecr"
declare_list "$R" "$LISTS/lonecr"
printf 'deploy to %s\n' "$VALUE" > "$R/notes.md"
git -C "$R" add notes.md
gate 1 "list with lone-CR line endings" "notes.md:1" "$R" staged

# gitleaks reads a path only through a text diff; git lists every path.
R=$(wrepo w-binary-name)
declare_list "$R" "$LISTS/values"
printf '\211PNG\000\001' > "$R/$VALUE.png"
wcommit "$R" binary
gate 1 "value in a binary file's name" "a tracked path matches" "$R" range HEAD~1..HEAD
R=$(wrepo w-empty-name)
declare_list "$R" "$LISTS/values"
: > "$R/$VALUE.md"
git -C "$R" add "$VALUE.md"
gate 1 "value in an empty staged file's name" "a tracked path matches" "$R" staged
R=$(wrepo w-rename)
declare_list "$R" "$LISTS/values"
git -C "$R" mv README.md "$VALUE.md"
wcommit "$R" rename
gate 1 "value in a renamed file's name" "a tracked path matches" "$R" range HEAD~1..HEAD

# Value rules read lock files, which the committed rules' allowlist skips.
R=$(wrepo w-lockfile)
declare_list "$R" "$LISTS/values"
printf '{"resolved": "https://%s/lib.tgz"}\n' "$VALUE" > "$R/package-lock.json"
git -C "$R" add package-lock.json
gate 1 "value in package-lock.json" "package-lock.json" "$R" staged

# A merge that introduces the value, in range and in history.
R=$(wrepo w-merge)
declare_list "$R" "$LISTS/values"
base=$(git -C "$R" rev-parse HEAD)
git -C "$R" checkout -q -b side
printf 'side\n' > "$R/side.md"
wcommit "$R" side
git -C "$R" checkout -q -
git -C "$R" merge -q --no-ff --no-commit side >/dev/null 2>&1 || { echo "fixture setup: merge failed" >&2; exit 2; }
printf 'deploy to %s\n' "$VALUE" > "$R/merged.md"
wcommit "$R" merge
gate 1 "value introduced by a merge commit (range)" "[private-value-3]" "$R" range "$base..HEAD"
gate 1 "value introduced by a merge commit (history)" "[private-value-3]" "$R" history

# An ignore file in the working directory must not suppress a value finding.
R=$(wrepo w-cwd-ignore)
declare_list "$R" "$LISTS/values"
mkdir -p "$R/sub"
printf 'sub/notes.md:private-value-3:1\n' > "$R/sub/.gitleaksignore"
printf 'deploy to %s\n' "$VALUE" > "$R/sub/notes.md"
git -C "$R" add sub/notes.md
gate 1 "run from a directory holding its own .gitleaksignore" "notes.md:1" "$R/sub" staged

# Identities and ref names reach a public repository too.
R=$(wrepo w-identity)
declare_list "$R" "$LISTS/values"
GIT_AUTHOR_EMAIL="dev@$VALUE" git -C "$R" commit -q --allow-empty -m identity
gate 1 "value in an author email (range)" "a commit author or committer matches" "$R" range HEAD~1..HEAD
gate 1 "value in an author email (history)" "a commit author or committer matches" "$R" history
R=$(wrepo w-branch)
declare_list "$R" "$LISTS/values"
git -C "$R" branch "feature/$VALUE"
gate 1 "value in a branch name" "a branch or tag name matches" "$R" history

# .gitattributes can hide a text file's contents from git's diff.
R=$(wrepo w-attr-staged)
declare_list "$R" "$LISTS/values"
printf 'notes.md -diff\n' > "$R/.gitattributes"
printf 'deploy to %s\n' "$VALUE" > "$R/notes.md"
git -C "$R" add .gitattributes notes.md
gate 1 "staged value behind a -diff attribute" "notes.md  [private-value-3]" "$R" staged
R=$(wrepo w-attr-staged-shape)
printf 'notes.md binary\n' > "$R/.gitattributes"
printf 'see %s\n' "$H/$NAME/x" > "$R/notes.md"
git -C "$R" add .gitattributes notes.md
gate 1 "staged home path behind the binary attribute" "notes.md:1" "$R" staged
case $out in *hidden/*) bad "wrapper, hidden-file report: output contains the temporary path" ;; *) ok ;; esac
R=$(wrepo w-attr-range)
declare_list "$R" "$LISTS/values"
printf 'notes.md -diff\n' > "$R/.gitattributes"
printf 'deploy to %s\n' "$VALUE" > "$R/notes.md"
wcommit "$R" hidden
git -C "$R" rm -q notes.md
wcommit "$R" unhidden
gate 1 "value behind a -diff attribute, added then removed" "[private-value-3]" "$R" range HEAD~2..HEAD

# git quotes a non-ASCII path unless told not to; the value must still match,
# and the output must withhold the file name.
R=$(wrepo w-nonascii)
UVALUE=fixture-münchen.example
printf '%s\n' "$UVALUE" > "$LISTS/unicode"
declare_list "$R" "$LISTS/unicode"
mkdir -p "$R/docs-$UVALUE"
printf 'see %s\n' "$UVALUE" > "$R/docs-$UVALUE/notes.md"
git -C "$R" add -A
rc=0
out=$(cd "$R" && GITLEAKS="$GITLEAKS" sh "$GATE" staged 2>&1) || rc=$?
case "$rc:$out" in
  1:*"file name withheld"*)
    case $out in
      *münchen*|*'\303\274'*|*fixture-m*) bad "wrapper, non-ASCII value: the value appears in the output" ;;
      *) ok ;;
    esac ;;
  *) bad "wrapper, non-ASCII value in a directory name: exit $rc, expected 1 with the file name withheld" ;;
esac

# A commit message is checked before a push, not only when going public.
R=$(wrepo w-range-message)
declare_list "$R" "$LISTS/values"
git -C "$R" commit -q --allow-empty -m "deploy to $VALUE"
gate 1 "value in a commit message (range)" "a commit message matches" "$R" range HEAD~1..HEAD

# An inline allow comment suppresses nothing unless the project opts in, and
# then only for the committed rules. The marker is assembled here so no copied
# file carries it, since the Python standard's pragma check rejects it.
ALLOW="gitleaks"":allow"
R=$(wrepo w-allow)
printf 'see %s # %s\n' "$H/$NAME/x" "$ALLOW" > "$R/notes.md"
git -C "$R" add notes.md
gate 1 "allow comment ignored by default" "notes.md:1" "$R" staged
saved_allow=${LEAKGATE_HONOR_ALLOW:-}
LEAKGATE_HONOR_ALLOW=1
export LEAKGATE_HONOR_ALLOW
gate 0 "allow comment honoured for committed rules when opted in" "no leaks found" "$R" staged
R=$(wrepo w-allow-value)
declare_list "$R" "$LISTS/values"
printf 'deploy to %s # %s\n' "$VALUE" "$ALLOW" > "$R/notes.md"
git -C "$R" add notes.md
gate 1 "allow comment never suppresses a value rule" "notes.md:1" "$R" staged
LEAKGATE_HONOR_ALLOW=$saved_allow

# A hex-like value must not match a commit or object SHA.
R=$(wrepo w-hex)
sha=$(git -C "$R" rev-parse HEAD)
printf '%s\n' "$(printf '%s' "$sha" | cut -c1-8)" > "$LISTS/hex"
declare_list "$R" "$LISTS/hex"
gate 0 "hex-like value does not match a SHA" "no leaks found" "$R" history

# gate_lacks <description> <text>: the last gate run's output must not contain text.
gate_lacks() {
  case $out in
    *"$2"*) bad "wrapper, $1: output contains '$2'" ;;
    *) ok ;;
  esac
}

# Hidden-file copies are read by blob ID: a path that starts with 0: to 3:
# must not be read as a conflict stage.
R=$(wrepo w-stage-names)
declare_list "$R" "$LISTS/values"
printf '* -diff\n' > "$R/.gitattributes"
printf 'deploy to %s\n' "$VALUE" > "$R/2:notes.md"
printf 'deploy to %s\n' "$VALUE" > "$R/0:notes.md"
git -C "$R" add -A
gate 1 "staged -diff file named 2:notes.md" "2:notes.md  [private-value-3]" "$R" staged
gate 1 "staged -diff file named 0:notes.md" "0:notes.md  [private-value-3]" "$R" staged
gate_lacks "hidden-file report" "hidden/"

# Content git itself detects as binary: value rules still match the bytes.
R=$(wrepo w-nul)
declare_list "$R" "$LISTS/values"
printf 'log\000 deploy to %s\n' "$VALUE" > "$R/app.log"
git -C "$R" add app.log
gate 1 "staged file with a NUL byte holding a value" "app.log  [private-value-3]" "$R" staged

# A staged .gitleaksignore that git hides must not suppress a hidden finding.
R=$(wrepo w-hidden-ignore)
printf '* -diff\n' > "$R/.gitattributes"
printf 'notes.md:home-directory-path:1\n' > "$R/.gitleaksignore"
printf 'see %s\n' "$H/$NAME/x" > "$R/notes.md"
git -C "$R" add -A
gate 1 "hidden .gitleaksignore does not suppress" "notes.md:1" "$R" staged

# Deletions and mode-only changes of hidden files finish cleanly.
R=$(wrepo w-hidden-delete)
printf '* -diff\n' > "$R/.gitattributes"
printf 'clean\n' > "$R/keep.sh"
wcommit "$R" attrs
git -C "$R" rm -q README.md
chmod +x "$R/keep.sh"
git -C "$R" add keep.sh
gate 0 "staged deletion and mode change of hidden files" "no leaks found" "$R" staged

# A path with a newline is refused, never skipped.
R=$(wrepo w-newline)
printf 'x\n' > "$R/two
lines.md"
git -C "$R" add -A
gate 2 "staged path containing a newline" "contains a newline" "$R" staged

# Only an exact 1 relaxes the committed rules.
R=$(wrepo w-allow-true)
printf 'see %s # %s\n' "$H/$NAME/x" "gitleaks"":allow" > "$R/notes.md"
git -C "$R" add notes.md
LEAKGATE_HONOR_ALLOW=true
export LEAKGATE_HONOR_ALLOW
gate 1 "LEAKGATE_HONOR_ALLOW=true stays strict" "notes.md:1" "$R" staged
LEAKGATE_HONOR_ALLOW=$saved_allow

# A Latin-1 author name must not hide a matching identity from grep. git commit
# rewrites a Latin-1 name as UTF-8, so the commit is written byte for byte, as
# fast-import or another tool can. Under a UTF-8 locale GNU grep without -a
# drops the line; under C it keeps it, so this fixture forces UTF-8.
R=$(wrepo w-latin1)
declare_list "$R" "$LISTS/values"
latin1=$(printf 'tree %s\nparent %s\nauthor Jos\351 <dev@%s> 1700000000 +0000\ncommitter fixture <fixture@example.invalid> 1700000000 +0000\n\nlatin1\n' \
  "$(git -C "$R" rev-parse 'HEAD^{tree}')" "$(git -C "$R" rev-parse HEAD)" "$VALUE" |
  git -C "$R" hash-object -t commit -w --stdin)
git -C "$R" update-ref HEAD "$latin1"
had_lc_all=${LC_ALL+set} saved_lc_all=${LC_ALL-}
LC_ALL=C.UTF-8
export LC_ALL
# The fixture proves -a only where grep without it drops the line. Elsewhere,
# such as BSD grep or a system with no C.UTF-8 locale, it still runs but proves
# less: a note locally, a failure in CI, where the platform is known to drop it.
probe=$(printf 'Jos\351 <dev@%s>\n' "$VALUE" | grep -n -i -F -e "$VALUE" 2>/dev/null) || true
if [ -n "$probe" ]; then
  if [ "${GITHUB_ACTIONS:-}" = true ]; then
    bad "wrapper, Latin-1 fixture: grep keeps a line that is not UTF-8 under C.UTF-8, so the fixture cannot fail without -a"
  else
    echo "note: grep here keeps a line that is not UTF-8, so the Latin-1 fixture does not exercise -a"
  fi
fi
gate 1 "Latin-1 author name with a value in the email" "a commit author or committer matches" "$R" range HEAD~1..HEAD
if [ -n "$had_lc_all" ]; then LC_ALL=$saved_lc_all; else unset LC_ALL; fi

# A value carrying a pasted no-break space would never match: refuse it.
R=$(wrepo w-nbsp)
printf '%s\302\240\n' "$VALUE" > "$LISTS/nbsp"
declare_list "$R" "$LISTS/nbsp"
gate 2 "value ending in a no-break space" "line 1" "$R" staged

echo "Leak gate fixtures: $passed passed, $failed failed."
[ "$failed" -eq 0 ]
