#!/bin/sh
# Proves scripts/install-gitleaks.sh fails closed, before CI trusts the binary it
# installs. CI runs this on every change (.github/workflows/leaks.yml), next to
# the install step, which is the real download on linux_x64.
#
# No fixture touches the network. Each runs the script with a PATH that holds
# shims for curl, uname, sha256sum and shasum, plus links to the real utilities
# it needs and nothing else. The curl shim serves a tarball built here, which
# cannot match a pinned SHA-256, or fails the way curl -f does on an HTTP error.
# So no fixture can install anything: each proves a refusal, and the platform
# fixtures prove which tarball was requested.
#
# Usage:  sh scripts/test-install-gitleaks.sh
# Exits non-zero if any fixture fails. Needs sh and standard POSIX utilities.

set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd -P)
SCRIPT="$ROOT/scripts/install-gitleaks.sh"
SH=$(command -v sh)
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

passed=0
failed=0
ok() { passed=$((passed + 1)); }
bad() { echo "FAIL: $*" >&2; failed=$((failed + 1)); }

# --- The PATH each fixture runs with ------------------------------------------

TOOLS="$WORK/tools"
mkdir "$TOOLS"
for t in mktemp tar gzip mkdir install rm cp; do
  p=$(command -v "$t") || { echo "test-install-gitleaks: $t not found" >&2; exit 2; }
  ln -s "$p" "$TOOLS/$t"
done
REAL_SHA256SUM=$(command -v sha256sum || true)

SHIMS="$WORK/shims"
mkdir "$SHIMS"

# curl: log the URL, then either fail as curl -f does on a 404 (exit 22) or
# write the fixture tarball to the -o path.
cat > "$SHIMS/curl" <<'EOF'
#!/bin/sh
out=
while [ $# -gt 0 ]; do
  case $1 in
    -o) out=$2; shift ;;
    -*) ;;
    *) url=$1 ;;
  esac
  shift
done
echo "$url" >> "$CURL_LOG"
[ "$CURL_MODE" = serve ] || exit 22
cp "$FIXTURE_TARBALL" "$out"
EOF

cat > "$SHIMS/uname" <<'EOF'
#!/bin/sh
case $1 in
  -s) echo "$FAKE_UNAME_S" ;;
  -m) echo "$FAKE_UNAME_M" ;;
  *) exit 1 ;;
esac
EOF

# The macOS form, shasum -a 256 -c, checked by the real sha256sum.
cat > "$SHIMS/shasum" <<EOF
#!/bin/sh
[ "\$1 \$2 \$3" = "-a 256 -c" ] || exit 1
shift 2
exec "$REAL_SHA256SUM" "\$@"
EOF
chmod +x "$SHIMS/curl" "$SHIMS/uname" "$SHIMS/shasum"

# Two PATHs: Linux's, with sha256sum, and macOS's, with only shasum.
LINUX_BIN="$WORK/linux-bin"
MAC_BIN="$WORK/mac-bin"
mkdir "$LINUX_BIN" "$MAC_BIN"
[ -n "$REAL_SHA256SUM" ] || { echo "test-install-gitleaks: sha256sum not found" >&2; exit 2; }
ln -s "$REAL_SHA256SUM" "$LINUX_BIN/sha256sum"
ln -s "$SHIMS/shasum" "$MAC_BIN/shasum"

# A tarball shaped like a release, holding a stub gitleaks. Its hash matches no pin.
mkdir "$WORK/tarball"
printf '#!/bin/sh\necho 8.24.2\n' > "$WORK/tarball/gitleaks"
chmod +x "$WORK/tarball/gitleaks"
FIXTURE_TARBALL="$WORK/fixture.tar.gz"
tar -czf "$FIXTURE_TARBALL" -C "$WORK/tarball" gitleaks
export FIXTURE_TARBALL

# install_run <os> <arch> <curl-mode> <hash-bin> [args...]: run the script in
# a fresh HOME. Sets rc, out (stdout and stderr), urls (the requested URLs), and
# dest (the default install directory under that HOME).
n=0
install_run() {
  n=$((n + 1))
  os=$1 arch=$2 mode=$3 hashbin=$4
  shift 4
  home="$WORK/home-$n"
  mkdir "$home"
  dest="$home/.local/bin"
  log="$WORK/curl-$n.log"
  : > "$log"
  rc=0
  out=$(HOME=$home PATH="$SHIMS:$hashbin:$TOOLS" CURL_LOG=$log CURL_MODE=$mode \
    FAKE_UNAME_S=$os FAKE_UNAME_M=$arch "$SH" "$SCRIPT" "$@" 2>&1) || rc=$?
  urls=$(cat "$log")
}

# refused <description> <dir>: the run failed and installed nothing.
refused() {
  if [ "$rc" -eq 0 ]; then
    bad "$1: exit 0, expected a failure"
    printf '%s\n' "$out" | sed 's/^/    /' >&2
  elif [ -e "$2/gitleaks" ]; then
    bad "$1: exit $rc, but $2/gitleaks exists"
  else
    ok
  fi
}

# requested <description> <tarball-suffix>: the one URL requested ends in it.
requested() {
  case $urls in
    */gitleaks_[0-9]*_"$2") ok ;;
    *) bad "$1: requested '$urls', expected a URL ending in _$2" ;;
  esac
}

# --- Hash mismatch -------------------------------------------------------------

install_run Linux x86_64 serve "$LINUX_BIN" "$WORK/target"
refused "tampered tarball, sha256sum" "$WORK/target"

install_run Darwin arm64 serve "$MAC_BIN" "$WORK/target-mac"
refused "tampered tarball, shasum (macOS)" "$WORK/target-mac"

# --- Platform selection ----------------------------------------------------------

install_run Linux x86_64 fail "$LINUX_BIN" "$WORK/t1"
requested "Linux x86_64" linux_x64.tar.gz
install_run Linux aarch64 fail "$LINUX_BIN" "$WORK/t2"
requested "Linux aarch64" linux_arm64.tar.gz
install_run Darwin arm64 fail "$MAC_BIN" "$WORK/t3"
requested "Darwin arm64" darwin_arm64.tar.gz
install_run Darwin x86_64 fail "$MAC_BIN" "$WORK/t4"
requested "Darwin x86_64" darwin_x64.tar.gz

install_run FreeBSD amd64 serve "$LINUX_BIN" "$WORK/t5"
refused "unsupported platform" "$WORK/t5"
case $out in
  *"FreeBSD amd64"*) ok ;;
  *) bad "unsupported platform: the message does not name FreeBSD amd64" ;;
esac
[ -z "$urls" ] && ok || bad "unsupported platform: a download was requested"

# --- Failed download ---------------------------------------------------------------

install_run Linux x86_64 fail "$LINUX_BIN" "$WORK/t6"
refused "failed download" "$WORK/t6"

# --- Default directory ---------------------------------------------------------------

install_run Linux x86_64 fail "$LINUX_BIN"
refused "default directory, failed download" "$dest"
case $out in
  *"$dest"*) ok ;;
  *) bad "default directory: the output does not name $dest" ;;
esac

# --- Pins ----------------------------------------------------------------------------

pins=$("$SH" "$SCRIPT" --pins 2>&1) || true
versions=$(printf '%s\n' "$pins" | grep -c '^version [0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*$' || true)
platforms=$(printf '%s\n' "$pins" | grep -cE '^(linux|darwin)_(x64|arm64) [0-9a-f]{64}$' || true)
lines=$(printf '%s\n' "$pins" | grep -c . || true)
if [ "$versions" -eq 1 ] && [ "$platforms" -eq 4 ] && [ "$lines" -eq 5 ]; then
  ok
else
  bad "--pins: expected one version line and four platform lines, got:"
  printf '%s\n' "$pins" | sed 's/^/    /' >&2
fi

echo "Install script fixtures: $passed passed, $failed failed."
[ "$failed" -eq 0 ]
