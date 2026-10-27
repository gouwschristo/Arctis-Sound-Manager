#!/usr/bin/env bash
# Build the current checkout into an installable pacman package.
#
# The packaged release comes from aur/PKGBUILD, which downloads a release
# tarball. Testing a *working tree* (a branch with local fixes) needs the same
# package built from this tree instead — same file layout, same services, same
# udev rules — so the result can be installed over the packaged version and
# rolled back with `pacman -S arctis-sound-manager`.
#
# Usage:
#   scripts/build-local-package.sh            # build, print the install command
#   scripts/build-local-package.sh --install  # build and install (needs sudo)
#
# Requires the same makedepends as the PKGBUILD: uv, python-installer,
# python-ruamel-yaml. Run as a normal user; makepkg refuses to run as root.
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_root"

pkgver=$(sed -n 's/^pkgver=//p' aur/PKGBUILD)
# -2 rather than -1 so the local build outranks the packaged release; bump it
# when rebuilding the same commit if pacman refuses a same-version reinstall.
pkgrel=${PKGREL:-2}
pkgname=$(sed -n 's/^pkgname=//p' aur/PKGBUILD)
build_dir=${BUILD_DIR:-/tmp/asm-local-build}

source_prefix="Arctis-Sound-Manager-$pkgver"
mkdir -p "$build_dir"
rm -f "$build_dir"/*.pkg.tar.zst "$build_dir"/*.tar.gz

echo "==> archiving $(git rev-parse --short HEAD) as $source_prefix"
git archive --prefix="$source_prefix/" HEAD \
    -o "$build_dir/$pkgname-$pkgver.tar.gz"

echo "==> preparing PKGBUILD in $build_dir"
cp aur/PKGBUILD aur/arctis-sound-manager.install "$build_dir/"
sed -e "s/^pkgrel=.*/pkgrel=$pkgrel/" \
    -e 's|^source=(".*")$|source=("$pkgname-$pkgver.tar.gz")|' \
    -i "$build_dir/PKGBUILD"

echo "==> building $pkgname $pkgver-$pkgrel"
(cd "$build_dir" && makepkg -f --noconfirm)

pkg=$(ls "$build_dir"/"$pkgname-$pkgver-$pkgrel"-*.pkg.tar.zst 2>/dev/null | head -1)
if [ -z "$pkg" ]; then
    echo "build produced no package" >&2
    exit 1
fi

echo
echo "built: $pkg"
if [ "${1:-}" = "--install" ]; then
    sudo pacman -U --noconfirm "$pkg"
    echo
    echo "installed. Restart the daemon to pick up the new code:"
    echo "  systemctl --user restart arctis-manager"
else
    echo "install with:"
    echo "  sudo pacman -U $pkg"
    echo "  systemctl --user restart arctis-manager"
fi
