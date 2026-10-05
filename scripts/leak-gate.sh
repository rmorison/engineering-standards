#!/bin/sh
# Local leak gate: the committed rules in .gitleaks.toml, plus private value
# rules generated from a list that never enters any repository.
#
# process/repository-standards.md owns the rules this enforces. In short:
#
#   - The value list is a plain text file, one literal value per line, blank
#     lines and lines starting with # ignored. It lives outside every repository.
#   - It is declared with a git config key holding its path, usually set once
#     per machine:      git config --global leakgate.values ~/.config/leakgate/values
#     A clone can point elsewhere, or opt out, with --local:
#                       git config --local leakgate.values none
#   - With no declaration, or an opt-out, only the committed rules run and a line
#     says so. That is what an outside contributor gets, so nobody is blocked by
#     a file they cannot have. With a declaration, a list that is missing, empty,
#     unreadable or inside this repository fails.
#   - CI never runs value rules: the list must never reach a public log.
#
# Nothing this prints contains a matched value or an entry from the list. gitleaks
# reports go through templates that name rule, line and commit, and the file only
# when no tracked path matches a value. A bad list entry is reported by its line
# number. gitleaks runs without -v, whose output includes the line around a match.
#
# Usage:
#   sh scripts/leak-gate.sh staged                 # pre-commit: what is staged
#   sh scripts/leak-gate.sh range <base>..<head>   # pre-push, and a maintainer's
#                                                  # pre-merge run over a pull
#                                                  # request's commits
#   sh scripts/leak-gate.sh history                # going public: every ref, plus
#                                                  # commit and tag messages,
#                                                  # identities and ref names
#
# Besides file contents, value rules check what gitleaks does not read: the path
# of every file the source touches (binary, empty and renamed files included),
# commit author and committer identities in range and history, and in history
# branch and tag names and commit and tag messages. Merge commits are scanned
# with git's -m, so content a merge introduces is not skipped.
#
# Run a pre-merge check from the default branch's own checkout, never from the
# pull request's: the pull request can edit this script, .gitleaks.toml and
# .gitleaksignore, and this machine holds the value list.
#
#   git fetch origin pull/<N>/head:refs/leakgate/pr-<N>
#   sh scripts/leak-gate.sh range origin/main..refs/leakgate/pr-<N>
#
# Exits 0 when clean, 1 when a leak is found, 2 on a usage, list or gitleaks
# error. Needs git, gitleaks (GITLEAKS may name its path) and standard POSIX
# utilities, plus iconv when a value list is declared.
#
# LEAKGATE_HONOR_ALLOW=1 lets inline gitleaks allow comments suppress findings
# from the committed rules only, for a project whose language standard permits
# reviewed ones (see process/repository-standards.md). Value rules ignore them
# always.

set -eu

GITLEAKS=${GITLEAKS:-gitleaks}
ROOT=$(git rev-parse --show-toplevel)
ROOT_REAL=$(cd "$ROOT" && pwd -P)
SCRIPTS=$(cd "$(dirname "$0")" && pwd -P)
# gitleaks reads .gitleaksignore from its working directory. Run from the root, so
# the only ignore file it reads is the one checked below.
cd "$ROOT"
CONFIG="$ROOT/.gitleaks.toml"
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
# dash runs no EXIT trap when a signal kills the shell, which would leave the
# generated value rules behind. Route signals through it.
trap 'exit 130' INT TERM HUP
chmod 700 "$WORK"

die() { echo "leak-gate: $*" >&2; exit 2; }
usage() { die "usage: leak-gate.sh staged | range <base>..<head> | history"; }

mode=${1:-}
case "$mode" in
  staged|history) [ $# -eq 1 ] || usage ;;
  range) [ $# -eq 2 ] || usage; range=$2 ;;
  *) usage ;;
esac
[ -f "$CONFIG" ] || die "no .gitleaks.toml at the repository root"
[ -f "$SCRIPTS/gitleaks-report.tmpl" ] || die "no gitleaks-report.tmpl beside this script"
# Fail closed with one line that says what to do, before anything else prints.
# It names no path: GITLEAKS is a local path, and a path can hold a home directory.
# What command -v finds must also be an executable file: for a name with a slash,
# dash's command -v accepts any existing path, a directory included.
gitleaks_path=$(command -v "$GITLEAKS" 2>/dev/null) &&
  [ -f "$gitleaks_path" ] && [ -x "$gitleaks_path" ] ||
  die "gitleaks was not found: install the pinned version with sh scripts/install-gitleaks.sh, or set GITLEAKS to its path"

# --- The value list ---------------------------------------------------------------

# Resolves a path to its real, symlink-free form, or prints nothing.
real_path() {
  dir=$(cd "$(dirname "$1")" 2>/dev/null && pwd -P) || return 0
  target="$dir/$(basename "$1")"
  if [ -L "$target" ] && command -v readlink >/dev/null 2>&1; then
    link=$(readlink "$target")
    case "$link" in /*) ;; *) link="$dir/$link" ;; esac
    real_path "$link"
    return 0
  fi
  printf '%s\n' "$target"
}

declared=$(git -C "$ROOT" config --get leakgate.values 2>/dev/null || true)
case "$declared" in
  "~/"*) declared="$HOME/${declared#\~/}" ;;
esac

values=0
if [ -z "$declared" ] || [ "$declared" = none ]; then
  echo "leak-gate: value rules skipped: no value list declared for this clone (git config leakgate.values)."
else
  list=$(real_path "$declared")
  case "$list/" in
    "$ROOT_REAL"/*) die "the declared value list is inside this repository; move it outside every repository" ;;
  esac
  [ -n "$list" ] && [ -f "$list" ] || die "the declared value list does not exist: $declared"
  [ -r "$list" ] || die "the declared value list cannot be read: $declared"

  # A list kept in another repository, such as a dotfiles repository, is one
  # commit from being published. Warn rather than fail: it may be ignored there.
  # A hook run in a worktree gets an absolute GIT_DIR from git (2.34; from the
  # main checkout it gets none), and with it set, git -C answers for the
  # repository being committed to. The probes run with git's repository-local
  # variables cleared.
  list_dir=$(dirname "$list")
  if (
    unset $(git rev-parse --local-env-vars)
    git -C "$list_dir" rev-parse --is-inside-work-tree >/dev/null 2>&1 &&
      ! git -C "$list_dir" check-ignore -q "$list" 2>/dev/null
  ); then
    echo "leak-gate: warning: the value list is inside a git work tree and not ignored there: $declared" >&2
  fi

  # CRLF and lone CR both end a line; a byte-order mark is dropped.
  bom=$(printf '\357\273\277')
  cr=$(printf '\r')
  # The C locale keeps sed and tr from stopping at an invalid byte, which on
  # BSD systems would silently truncate the list. Each step's status is checked.
  LC_ALL=C sed "1s/^$bom//; s/$cr\$//" "$list" > "$WORK/list.raw" ||
    die "the declared value list could not be read: $declared"
  LC_ALL=C tr '\r' '\n' < "$WORK/list.raw" > "$WORK/list" ||
    die "the declared value list could not be read: $declared"
  command -v iconv >/dev/null 2>&1 || die "iconv is needed to check the value list and was not found"

  {
    echo 'title = "private values"'
    echo '[extend]'
    echo 'useDefault = false'
  } > "$WORK/values.toml"
  : > "$WORK/entries"
  # No-break space, ideographic space, and the U+2000 to U+200A spaces, as bytes.
  nbsp=$(printf '\302\240')
  ideo=$(printf '\343\200\200')
  gen_space="$(printf '\342\200')[$(printf '\200')-$(printf '\212')]"

  n=0
  while IFS= read -r line || [ -n "$line" ]; do
    n=$((n + 1))
    value=$(printf '%s' "$line" | LC_ALL=C sed 's/^[[:space:]]*//; s/[[:space:]]*$//')
    case "$value" in ''|'#'*) continue ;; esac
    # Non-ASCII spaces at either end usually come from pasting, and the C locale
    # does not trim them; a value carrying one would silently never match.
    if printf '%s\n' "$value" | LC_ALL=C grep -q -e "^$nbsp" -e "$nbsp\$" \
         -e "^$ideo" -e "$ideo\$" -e "^$gen_space" -e "$gen_space\$"; then
      die "value list line $n starts or ends with a non-ASCII space"
    fi
    if ! printf '%s' "$value" | iconv -f UTF-8 -t UTF-8 >/dev/null 2>&1; then
      die "value list line $n is not valid UTF-8"
    fi
    if printf '%s' "$value" | tr -d '\t' | LC_ALL=C grep -q '[[:cntrl:]]'; then
      die "value list line $n holds a control character"
    fi
    case "$value" in
      *'\E'*|*"'''"*) die "value list line $n contains \\E or ''', which cannot be quoted as a literal" ;;
    esac
    if [ "${#value}" -lt 4 ]; then
      die "value list line $n is shorter than 4 characters and would match almost every file"
    fi
    values=$((values + 1))
    printf '%s\t%s\n' "$n" "$value" >> "$WORK/entries"
    # (?i)\Q...\E makes every value a case-insensitive literal: no value is
    # ever parsed as a regular expression, so none can fail to compile and
    # print itself in the error.
    printf '[[rules]]\nid = "private-value-%s"\nregex = '"'''"'(?i)\\Q%s\\E'"'''"'\n' \
      "$n" "$value" >> "$WORK/values.toml"
  done < "$WORK/list"

  [ "$values" -gt 0 ] || die "the declared value list has no values: $declared"
  chmod 600 "$WORK/values.toml" "$WORK/entries"

  # A value rule has no legitimate in-tree suppression.
  if [ -f "$ROOT/.gitleaksignore" ] && grep -q 'private-value-' "$ROOT/.gitleaksignore"; then
    die ".gitleaksignore names a private value rule; value findings cannot be suppressed in the tree"
  fi
fi

# --- What gitleaks does not read: paths, identities, ref names, messages -------------

# gitleaks sees a path only through a text diff, so a value in the name of a
# binary, empty or renamed file would pass it. git lists every path the scanned
# source touches, whatever the file holds.
case "$mode" in
  staged)
    git -c core.quotePath=false diff --cached --name-only --no-renames -z > "$WORK/paths.z" ;;
  range)
    if [ "$(git rev-list --count "$range")" -eq 0 ]; then
      echo "leak-gate: note: the range $range holds no commits, so there is nothing to scan."
    fi
    git -c core.quotePath=false log -m --format= --name-only --no-renames -z "$range" > "$WORK/paths.z"
    git log --format='%H%x09%an <%ae>%x09%cn <%ce>' "$range" > "$WORK/identities" ;;
  history)
    git -c core.quotePath=false log --all -m --format= --name-only --no-renames -z > "$WORK/paths.z"
    git log --all --format='%H%x09%an <%ae>%x09%cn <%ce>' > "$WORK/identities"
    git for-each-ref --format='%(objectname)%09%(refname)' > "$WORK/refs" ;;
esac
# git quotes a path holding non-ASCII or special characters unless told not to,
# and a quoted path would not match a value. -z output is never quoted.
tr '\0' '\n' < "$WORK/paths.z" > "$WORK/paths"
# A newline inside a path would split it into two lines that match nothing, so
# refuse such a path rather than skip it.
if [ "$(tr -cd '\n' < "$WORK/paths.z" | wc -c)" -ne 0 ]; then
  die "a scanned path contains a newline; rename it before this check can run"
fi

# Files git's staged diff shows as "Binary files differ": a -diff or binary
# attribute, a diff driver marked binary, or content git detects as binary.
# gitleaks --staged skips them, so their staged contents are copied out from the
# index by blob ID and scanned directly. Copies go under $WORK/hidden/t, so the
# scanned directory's own root never holds a copied .gitleaksignore.
: > "$WORK/hidden.list"
if [ "$mode" = staged ]; then
  git -c core.quotePath=false diff --cached --numstat --no-renames -z |
    tr '\0' '\n' | sed -n 's/^-	-	//p' > "$WORK/binary.paths"
  while IFS= read -r p; do
    [ -n "$p" ] || continue
    # The blob ID comes from the index entry, never from a ":<path>" revision,
    # which git reads as a stage number when the path starts with 0: to 3:.
    entry=$(git --literal-pathspecs ls-files -s -- "$p" | head -n 1)
    [ -n "$entry" ] || continue                   # a staged deletion
    mode_bits=${entry%% *}
    rest=${entry#* }
    sha=${rest%% *}
    case "$mode_bits" in 100644|100755) ;; *) continue ;; esac   # symlinks, submodules
    mkdir -p "$WORK/hidden/t/$(dirname "$p")"
    git cat-file blob "$sha" > "$WORK/hidden/t/$p" ||
      die "could not read the staged contents of a file"
    printf '%s\n' "$p" >> "$WORK/hidden.list"
  done < "$WORK/binary.paths"
fi

# sha_matches <file> <value>: the SHA in column 1 of each line whose other
# columns contain the value. Matching only those columns keeps a hex-like value
# from matching a SHA.
sha_matches() {
  # -a: under a UTF-8 locale GNU grep drops a matching line that is not valid
  # UTF-8, such as a Latin-1 author name written by fast-import or an old tool.
  # (git commit itself rewrites Latin-1 as UTF-8.)
  cut -f2- "$1" | grep -a -n -i -F -e "$2" | cut -d: -f1 > "$WORK/lines"
  awk -F '\t' 'NR == FNR { want[$1]; next } FNR in want { print $1 }' "$WORK/lines" "$1"
}

leaks=0
path_hit=0
if [ "$values" -gt 0 ]; then
  while IFS='	' read -r n value; do
    # Each report names the list line and a SHA, never the value or the text
    # around it.
    if grep -q -i -F -e "$value" "$WORK/paths"; then
      echo "a tracked path matches private value (list line $n)"
      leaks=1
      path_hit=1
    fi
    if [ -f "$WORK/identities" ]; then
      for sha in $(sha_matches "$WORK/identities" "$value"); do
        echo "a commit author or committer matches private value (list line $n): commit $sha"
        leaks=1
      done
    fi
    if [ "$mode" = range ]; then
      for sha in $(git log -i -F --grep="$value" --format=%H "$range"); do
        echo "a commit message matches private value (list line $n): commit $sha"
        leaks=1
      done
    fi
    [ "$mode" = history ] || continue
    for sha in $(sha_matches "$WORK/refs" "$value" | sort -u); do
      echo "a branch or tag name matches private value (list line $n): object $sha"
      leaks=1
    done
    for sha in $(git log --all -i -F --grep="$value" --format=%H); do
      echo "a commit message matches private value (list line $n): commit $sha"
      leaks=1
    done
    for tag in $(git for-each-ref refs/tags --format='%(objecttype):%(objectname)'); do
      case "$tag" in tag:*) ;; *) continue ;; esac
      sha=${tag#tag:}
      if git cat-file tag "$sha" | grep -q -i -F -e "$value"; then
        echo "an annotated tag message matches private value (list line $n): tag object $sha"
        leaks=1
      fi
    done
  done < "$WORK/entries"
fi

if [ "$mode" = history ] && ! grep -q '/pull/' "$WORK/refs"; then
  echo "leak-gate: note: no pull request refs are fetched, so their commits were not scanned." \
    "Fetch them first; see the going-public procedure in process/repository-standards.md."
fi

# --- Contents: gitleaks -------------------------------------------------------------

cat > "$WORK/nofile.tmpl" <<'EOF'
{{- range . }}
line {{ .StartLine }}  [{{ .RuleID }}]{{ if .Commit }} commit {{ .Commit }}{{ end }} (file name withheld: a tracked path matches a private value)
{{- end }}
EOF

# -m makes git show each merge commit's changes, so content first introduced by a
# merge, such as a conflict resolution, is scanned too. --text stops a
# .gitattributes entry such as "-diff" from turning a text file's changes into
# "Binary files differ", which gitleaks would skip.
case "$mode" in
  staged) source_arg="--staged" ;;
  range) source_arg="--log-opts=--text -m $range" ;;
  history) source_arg="--log-opts=--all --text -m" ;;
esac

# run_gitleaks <allow-flag> <args...>: one gitleaks run. Exit 3 is a leak; any
# other non-zero exit is an error, never mistaken for a clean result. Output goes
# only through the given template, with any temporary-directory prefix removed.
run_gitleaks() {
  allow=$1
  shift
  rc=0
  "$GITLEAKS" "$@" --gitleaks-ignore-path "$ROOT" $allow \
    --no-banner --no-color --log-level warn --redact --exit-code 3 \
    --report-format template --report-path - > "$WORK/out" || rc=$?
  # Strip the temporary prefix as a literal string: $WORK is not a safe regex.
  awk -v p="$WORK/hidden/t/" 'index($0, p) == 1 { $0 = substr($0, length(p) + 1) } { print }' "$WORK/out"
  case $rc in
    0) ;;
    3) leaks=1 ;;
    *) die "gitleaks exited $rc" ;;
  esac
}

# Inline allow comments suppress nothing unless the project opted in, and then
# only for the committed rules.
committed_allow="--ignore-gitleaks-allow"
[ "${LEAKGATE_HONOR_ALLOW:-}" = 1 ] && committed_allow=""

# scan <config> <allow-flag> <template>: the chosen source.
scan() {
  run_gitleaks "$2" git "$ROOT" "$source_arg" --config "$1" --report-template "$3"
}

# Once any path matches a value, no report names a file.
template="$SCRIPTS/gitleaks-report.tmpl"
[ "$path_hit" -eq 0 ] || template="$WORK/nofile.tmpl"
scan "$CONFIG" "$committed_allow" "$template"
[ "$values" -eq 0 ] || scan "$WORK/values.toml" --ignore-gitleaks-allow "$template"

# The staged files git's diff hides: the committed rules through gitleaks' dir
# mode, which still skips content that really is binary, and the value rules by
# a byte-level literal match, which does not.
if [ -s "$WORK/hidden.list" ]; then
  run_gitleaks "$committed_allow" dir "$WORK/hidden" --config "$CONFIG" --report-template "$template"
  if [ "$values" -gt 0 ]; then
    while IFS='	' read -r n value; do
      while IFS= read -r p; do
        LC_ALL=C grep -a -q -i -F -e "$value" "$WORK/hidden/t/$p" || continue
        if [ "$path_hit" -eq 0 ]; then
          echo "$p  [private-value-$n] (staged; git's diff shows this file as binary)"
        else
          echo "[private-value-$n] a staged file git's diff shows as binary (file name withheld: a tracked path matches a private value)"
        fi
        leaks=1
      done < "$WORK/hidden.list"
    done < "$WORK/entries"
  fi
fi

if [ "$leaks" -ne 0 ]; then
  echo "leak-gate: leaks found. Remediation is in process/repository-standards.md." >&2
  exit 1
fi
echo "leak-gate: no leaks found by the rules that ran. That is not a publication clearance."
