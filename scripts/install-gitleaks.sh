#!/bin/sh
# Installs the pinned gitleaks. This is the only place this repository writes
# the gitleaks version and the SHA-256 of each release tarball:
# .github/workflows/leaks.yml, the standards' install instructions and an
# adopter's `make dev` all run this script. process/repository-standards.md
# (Adopting the Gate) owns the upgrade steps.
#
# The download is checked against the hash pinned below, never against the
# release's checksums file: a replaced release asset would ship with a checksums
# file that matches it. Nothing is piped from curl into a shell, the download
# happens in a temporary directory, and nothing is installed unless the hash
# matches. It never prompts, so CI and `make dev` can run it unattended.
#
# Usage:
#   sh scripts/install-gitleaks.sh [DIR]   # install DIR/gitleaks; DIR defaults
#                                          # to ~/.local/bin
#   sh scripts/install-gitleaks.sh --pins  # print the pins and exit
#
# --pins prints "version <V>", then one "<os>_<arch> <sha256>" line per tarball.
# On success the installed path is printed on stdout; everything else goes to
# stderr. Exits 0 when installed, 1 when the platform has no pinned hash or the
# download, hash check or install fails, and 2 on a usage error. Needs curl,
# tar, mktemp, install, and sha256sum or shasum.

set -eu

# --- Pins --------------------------------------------------------------------
# Adopters copy this file whole. The names and the one-assignment-per-line form
# of this block are stable; an upgrade changes only the values.
GITLEAKS_VERSION=8.24.2
SHA256_linux_x64=fa0500f6b7e41d28791ebc680f5dd9899cd42b58629218a5f041efa899151a8e
SHA256_linux_arm64=574a6d52573c61173add7ddb5e3cc68c0e82cb0735818a1eeb9a0a2de1643fbc
SHA256_darwin_x64=bc3c46f8039ba716ba8461fa6745c9d1cfb90ca2f5f881d8d0cf66b7ba7b742c
SHA256_darwin_arm64=90d13686937ac7429b97a3acbf1e1d0ce90d92ae2d0cf46a690bd8ae5230bea0
# --- End of pins ---------------------------------------------------------------

die() { echo "install-gitleaks: $*" >&2; exit 1; }
usage() { echo "usage: install-gitleaks.sh [DIR] | --pins" >&2; exit 2; }

case ${1:-} in
  --pins)
    [ $# -eq 1 ] || usage
    echo "version $GITLEAKS_VERSION"
    echo "linux_x64 $SHA256_linux_x64"
    echo "linux_arm64 $SHA256_linux_arm64"
    echo "darwin_x64 $SHA256_darwin_x64"
    echo "darwin_arm64 $SHA256_darwin_arm64"
    exit 0 ;;
  -*) usage ;;
esac
[ $# -le 1 ] || usage
DIR=${1:-$HOME/.local/bin}

os=$(uname -s)
arch=$(uname -m)
case "$os $arch" in
  "Linux x86_64") platform=linux_x64 sha=$SHA256_linux_x64 ;;
  "Linux aarch64"|"Linux arm64") platform=linux_arm64 sha=$SHA256_linux_arm64 ;;
  "Darwin x86_64") platform=darwin_x64 sha=$SHA256_darwin_x64 ;;
  "Darwin arm64") platform=darwin_arm64 sha=$SHA256_darwin_arm64 ;;
  *) die "no SHA-256 is pinned for $os $arch; nothing installed" ;;
esac

if command -v sha256sum >/dev/null 2>&1; then
  check() { sha256sum -c -; }
elif command -v shasum >/dev/null 2>&1; then
  check() { shasum -a 256 -c -; }
else
  die "needs sha256sum or shasum to check the download; nothing installed"
fi

F="gitleaks_${GITLEAKS_VERSION}_${platform}.tar.gz"
URL="https://github.com/gitleaks/gitleaks/releases/download/v$GITLEAKS_VERSION/$F"
echo "install-gitleaks: installing gitleaks $GITLEAKS_VERSION ($platform) into $DIR" >&2

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
trap 'exit 130' INT TERM HUP

curl -sSfL -o "$WORK/$F" "$URL" || die "download failed: $URL; nothing installed"
# The hash check is the last command of its pipeline, so its status decides.
echo "$sha  $WORK/$F" | check >/dev/null ||
  die "$F does not match the pinned SHA-256; nothing installed"
tar -xzf "$WORK/$F" -C "$WORK" gitleaks || die "could not unpack gitleaks from $F; nothing installed"
mkdir -p "$DIR" || die "could not create $DIR"
install -m 755 "$WORK/gitleaks" "$DIR/gitleaks" || die "could not install into $DIR"

echo "$DIR/gitleaks"
if [ "$(command -v gitleaks 2>/dev/null || true)" != "$DIR/gitleaks" ]; then
  echo "install-gitleaks: $DIR is not first on PATH for gitleaks: add it to PATH, or set GITLEAKS to $DIR/gitleaks" >&2
fi
