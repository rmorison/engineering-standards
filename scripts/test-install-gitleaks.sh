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
# fixtures prove which tarball was requested and which pinned hash it was
# checked against.
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

chmod +x "$SHIMS/curl" "$SHIMS/uname"

# Three PATHs for the hash check: Linux's, with sha256sum; macOS's, with only
# shasum; and one with neither. Both tools log the hash they are asked to check,
# then hand the line to the real sha256sum (shasum -a 256 -c is the macOS form).
[ -n "$REAL_SHA256SUM" ] || { echo "test-install-gitleaks: sha256sum not found" >&2; exit 2; }
LINUX_BIN="$WORK/linux-bin"
MAC_BIN="$WORK/mac-bin"
NO_HASH_BIN="$WORK/no-hash-bin"
mkdir "$LINUX_BIN" "$MAC_BIN" "$NO_HASH_BIN"
cat > "$LINUX_BIN/sha256sum" <<EOF
#!/bin/sh
[ "\$1 \$2" = "-c -" ] || exit 1
IFS= read -r line
echo "\${line%% *}" >> "\$HASH_LOG"
printf '%s\n' "\$line" | "$REAL_SHA256SUM" -c -
EOF
cat > "$MAC_BIN/shasum" <<EOF
#!/bin/sh
[ "\$1 \$2 \$3 \$4" = "-a 256 -c -" ] || exit 1
IFS= read -r line
echo "\${line%% *}" >> "\$HASH_LOG"
printf '%s\n' "\$line" | "$REAL_SHA256SUM" -c -
EOF
chmod +x "$LINUX_BIN/sha256sum" "$MAC_BIN/shasum"

# A tarball shaped like a release, holding a stub gitleaks. Its hash matches no pin.
mkdir "$WORK/tarball"
printf '#!/bin/sh\necho 8.24.2\n' > "$WORK/tarball/gitleaks"
chmod +x "$WORK/tarball/gitleaks"
FIXTURE_TARBALL="$WORK/fixture.tar.gz"
tar -czf "$FIXTURE_TARBALL" -C "$WORK/tarball" gitleaks
export FIXTURE_TARBALL

# install_run <os> <arch> <curl-mode> <hash-bin> [args...]: run the script in
# a fresh HOME. Sets rc, out (stdout and stderr), urls (the requested URLs),
# hashes (the hashes the check was asked for), and dest (the default install
# directory under that HOME).
n=0
install_run() {
  n=$((n + 1))
  os=$1 arch=$2 mode=$3 hashbin=$4
  shift 4
  home="$WORK/home-$n"
  mkdir "$home"
  dest="$home/.local/bin"
  log="$WORK/curl-$n.log"
  hlog="$WORK/hash-$n.log"
  : > "$log"
  : > "$hlog"
  rc=0
  out=$(HOME=$home PATH="$SHIMS:$hashbin:$TOOLS" CURL_LOG=$log CURL_MODE=$mode \
    HASH_LOG=$hlog FAKE_UNAME_S=$os FAKE_UNAME_M=$arch "$SH" "$SCRIPT" "$@" 2>&1) || rc=$?
  urls=$(cat "$log")
  hashes=$(cat "$hlog")
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

# says <description> <text>: the output contains the text.
says() {
  case $out in
    *"$2"*) ok ;;
    *) bad "$1: the output does not say '$2'" ;;
  esac
}

# The pins, as the script prints them.
pins=$("$SH" "$SCRIPT" --pins 2>&1) || true

# platform <description> <platform>: the one URL requested is that platform's
# tarball, and the download was checked against that platform's pinned hash.
platform() {
  case $urls in
    */gitleaks_[0-9]*_"$2".tar.gz) ok ;;
    *) bad "$1: requested '$urls', expected a URL ending in _$2.tar.gz" ;;
  esac
  pin=$(printf '%s\n' "$pins" | sed -n "s/^$2 //p")
  if [ -n "$pin" ] && [ "$hashes" = "$pin" ]; then
    ok
  else
    bad "$1: checked against '$hashes', expected the $2 pin"
  fi
}

# --- Hash mismatch -------------------------------------------------------------

install_run Linux x86_64 serve "$LINUX_BIN" "$WORK/target"
refused "tampered tarball, sha256sum" "$WORK/target"
says "tampered tarball, sha256sum" "does not match the pinned SHA-256"

install_run Darwin arm64 serve "$MAC_BIN" "$WORK/target-mac"
refused "tampered tarball, shasum (macOS)" "$WORK/target-mac"
says "tampered tarball, shasum (macOS)" "does not match the pinned SHA-256"

install_run Linux x86_64 serve "$NO_HASH_BIN" "$WORK/target-none"
refused "no sha256sum or shasum" "$WORK/target-none"
says "no sha256sum or shasum" "needs sha256sum or shasum"
[ -z "$urls" ] && ok || bad "no sha256sum or shasum: a download was requested"

# --- Platform selection ----------------------------------------------------------

install_run Linux x86_64 serve "$LINUX_BIN" "$WORK/t1"
platform "Linux x86_64" linux_x64
install_run Linux aarch64 serve "$LINUX_BIN" "$WORK/t2"
platform "Linux aarch64" linux_arm64
install_run Darwin arm64 serve "$MAC_BIN" "$WORK/t3"
platform "Darwin arm64" darwin_arm64
install_run Darwin x86_64 serve "$MAC_BIN" "$WORK/t4"
platform "Darwin x86_64" darwin_x64

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
says "failed download" "download failed"

# --- Default directory ---------------------------------------------------------------

install_run Linux x86_64 fail "$LINUX_BIN"
refused "default directory, failed download" "$dest"
case $out in
  *"$dest"*) ok ;;
  *) bad "default directory: the output does not name $dest" ;;
esac

# --- Pins ----------------------------------------------------------------------------

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
