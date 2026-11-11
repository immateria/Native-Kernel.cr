#!/bin/bash
# Dependency setup and identity checks for standard native macOS runners.
set -euo pipefail

mode=${1:?usage: setup.sh dependencies|verify PROFILE [CRYSTAL_VERSION]}
profile=${2:?missing profile}
case "$profile" in
  macos-15-arm64|macos-26-arm64) expected_arch=arm64; brew_root=/opt/homebrew ;;
  macos-15-x86_64|macos-26-x86_64) expected_arch=x86_64; brew_root=/usr/local ;;
  *) printf 'Unknown CI profile: %s\n' "$profile" >&2; exit 1 ;;
esac
[[ $(uname -s) == Darwin && $(uname -m) == "$expected_arch" ]]
# Local Rosetta runs cannot establish native Intel CI qualification.
translated=$(sysctl -in sysctl.proc_translated 2>/dev/null || true)
[[ "$translated" != 1 ]]
[[ $(brew --prefix) == "$brew_root" ]]

case "$mode" in
  dependencies)
    export HOMEBREW_NO_AUTO_UPDATE=1
    export HOMEBREW_NO_INSTALL_CLEANUP=1
    brew install openssl@3 libevent pkg-config
    openssl_prefix=$(brew --prefix openssl@3)
    libevent_prefix=$(brew --prefix libevent)
    # Override host defaults: macOS 26 images may carry OpenSSL 4.
    pkgconfig_dirs="$openssl_prefix/lib/pkgconfig:$libevent_prefix/lib/pkgconfig:$brew_root/lib/pkgconfig:$brew_root/share/pkgconfig"
    {
      printf 'HOMEBREW_NO_AUTO_UPDATE=1\nHOMEBREW_NO_INSTALL_CLEANUP=1\n'
      printf 'PKG_CONFIG_PATH=%s\nPKG_CONFIG_LIBDIR=%s\n' "$pkgconfig_dirs" "$pkgconfig_dirs"
      printf 'LIBRARY_PATH=%s/lib:%s/lib\n' "$openssl_prefix" "$libevent_prefix"
      printf 'LDFLAGS=-L%s/lib -L%s/lib\n' "$openssl_prefix" "$libevent_prefix"
      printf 'CPPFLAGS=-I%s/include -I%s/include\n' "$openssl_prefix" "$libevent_prefix"
    } >> "${GITHUB_ENV:?GITHUB_ENV is required for CI dependency setup}"
    PKG_CONFIG_PATH="$pkgconfig_dirs" PKG_CONFIG_LIBDIR="$pkgconfig_dirs" pkg-config --modversion openssl libevent
    ;;
  verify)
    version=${3:?missing exact Crystal version}
    details=$(crystal --version)
    printf '%s\n' "$details"
    [[ "$details" == "Crystal $version "* ]]
    case "$expected_arch" in
      arm64) [[ "$details" == *"Default target: aarch64-apple-"* ]] ;;
      x86_64) [[ "$details" == *"Default target: x86_64-apple-"* ]] ;;
    esac
    [[ $(pkg-config --modversion openssl) == 3.* ]]
    ;;
  *) printf 'Unknown setup operation: %s\n' "$mode" >&2; exit 1 ;;
esac
