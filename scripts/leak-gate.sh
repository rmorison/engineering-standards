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
#                                                  # commit and tag messages
#
# Run a pre-merge check from the default branch's own checkout, never from the
# pull request's: the pull request can edit this script, .gitleaks.toml and
# .gitleaksignore, and this machine holds the value list.
#
#   git fetch origin pull/<N>/head && sh scripts/leak-gate.sh range origin/main..FETCH_HEAD
#
# Exits 0 when clean, 1 when a leak is found, 2 on a usage, list or gitleaks
# error. Needs git and gitleaks (GITLEAKS may name its path); nothing else.

set -eu

GITLEAKS=${GITLEAKS:-gitleaks}
ROOT=$(git rev-parse --show-toplevel)
ROOT_REAL=$(cd "$ROOT" && pwd -P)
SCRIPTS=$(cd "$(dirname "$0")" && pwd -P)
CONFIG="$ROOT/.gitleaks.toml"
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
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
  echo "$target"
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
  list_dir=$(dirname "$list")
  if git -C "$list_dir" rev-parse --is-inside-work-tree >/dev/null 2>&1 &&
     ! git -C "$list_dir" check-ignore -q "$list" 2>/dev/null; then
    echo "leak-gate: warning: the value list is inside a git work tree and not ignored there: $declared" >&2
  fi

  # CRLF and lone CR both end a line; a byte-order mark is dropped.
  bom=$(printf '\357\273\277')
  cr=$(printf '\r')
  sed "1s/^$bom//; s/$cr\$//" "$list" | tr '\r' '\n' > "$WORK/list"

  {
    echo 'title = "private values"'
    echo '[extend]'
    echo 'useDefault = false'
  } > "$WORK/values.toml"
  cp "$WORK/values.toml" "$WORK/paths.toml"
  : > "$WORK/entries"

  n=0
  while IFS= read -r line || [ -n "$line" ]; do
    n=$((n + 1))
    value=$(printf '%s' "$line" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')
    case "$value" in ''|'#'*) continue ;; esac
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
    printf '%s\n' "$value" >> "$WORK/entries"
    # (?i)\Q...\E makes every value a case-insensitive literal: no value is
    # ever parsed as a regular expression, so none can fail to compile and
    # print itself in the error.
    printf '[[rules]]\nid = "private-value-%s"\nregex = '"'''"'(?i)\\Q%s\\E'"'''"'\n' \
      "$n" "$value" >> "$WORK/values.toml"
    printf '[[rules]]\nid = "private-value-%s-path"\npath = '"'''"'(?i)\\Q%s\\E'"'''"'\n' \
      "$n" "$value" >> "$WORK/paths.toml"
  done < "$WORK/list"

  [ "$values" -gt 0 ] || die "the declared value list has no values: $declared"
  chmod 600 "$WORK/values.toml" "$WORK/paths.toml" "$WORK/entries"

  # A value rule has no legitimate in-tree suppression.
  if [ -f "$ROOT/.gitleaksignore" ] && grep -q 'private-value-' "$ROOT/.gitleaksignore"; then
    die ".gitleaksignore names a private value rule; value findings cannot be suppressed in the tree"
  fi
fi

# --- Scanning ---------------------------------------------------------------------

cat > "$WORK/path.tmpl" <<'EOF'
{{- range . }}
a tracked path matches [{{ .RuleID }}]{{ if .Commit }} in commit {{ .Commit }}{{ end }}
{{- end }}
EOF
cat > "$WORK/nofile.tmpl" <<'EOF'
{{- range . }}
line {{ .StartLine }}  [{{ .RuleID }}]{{ if .Commit }} commit {{ .Commit }}{{ end }} (file name withheld: a tracked path matches a private value)
{{- end }}
EOF

case "$mode" in
  staged) source_args="--staged" ;;
  range) source_args="--log-opts=$range" ;;
  history) source_args="--log-opts=--all" ;;
esac

leaks=0
# gitleaks <config> <template>: one scan of the chosen source. Exit 3 is a leak;
# any other non-zero exit is an error, never mistaken for a clean result.
scan() {
  rc=0
  "$GITLEAKS" git "$ROOT" $source_args --config "$1" \
    --no-banner --no-color --log-level warn --redact --ignore-gitleaks-allow --exit-code 3 \
    --report-format template --report-template "$2" --report-path - || rc=$?
  case $rc in
    0) ;;
    3) leaks=1 ;;
    *) die "gitleaks exited $rc" ;;
  esac
}

template="$SCRIPTS/gitleaks-report.tmpl"
if [ "$values" -gt 0 ]; then
  scan "$WORK/paths.toml" "$WORK/path.tmpl"
  # Once any path matches a value, no later report names a file.
  [ "$leaks" -eq 0 ] || template="$WORK/nofile.tmpl"
fi
scan "$CONFIG" "$template"
[ "$values" -eq 0 ] || scan "$WORK/values.toml" "$template"

# --- Going public: messages gitleaks does not read ----------------------------------

if [ "$mode" = history ]; then
  if ! git -C "$ROOT" for-each-ref --format='%(refname)' | grep -q '/pull/'; then
    echo "leak-gate: note: no pull request refs are fetched, so their commits were not scanned." \
      "Fetch them first; see the going-public procedure in process/repository-standards.md."
  fi
  if [ "$values" -gt 0 ]; then
    i=0
    while IFS= read -r value; do
      i=$((i + 1))
      for sha in $(git -C "$ROOT" log --all -i -F --grep="$value" --format=%H); do
        echo "a commit message matches a private value: commit $sha"
        leaks=1
      done
      for tag in $(git -C "$ROOT" for-each-ref refs/tags --format='%(objecttype):%(objectname)'); do
        case "$tag" in tag:*) ;; *) continue ;; esac
        sha=${tag#tag:}
        if git -C "$ROOT" cat-file tag "$sha" | grep -q -i -F -e "$value"; then
          echo "an annotated tag message matches a private value: tag object $sha"
          leaks=1
        fi
      done
    done < "$WORK/entries"
  fi
fi

if [ "$leaks" -ne 0 ]; then
  echo "leak-gate: leaks found. Remediation is in process/repository-standards.md." >&2
  exit 1
fi
echo "leak-gate: no leaks found by the rules that ran. That is not a publication clearance."
