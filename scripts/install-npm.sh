#!/usr/bin/env bash
# Install npm into $HOME (no sudo) for an existing node that shipped without npm.
# Uses the China mirror (registry.npmmirror.com). Also sets the global prefix to
# ~/.local so later `npm i -g <pkg>` needs no sudo either.
set -e
NPM_VER="${NPM_VER:-10.9.2}"
REG="https://registry.npmmirror.com"

echo "node: $(node -v)"
mkdir -p "$HOME/.local/bin" "$HOME/.local/lib/node_modules"
cd /tmp
URL="$REG/npm/-/npm-$NPM_VER.tgz"
echo "downloading $URL"
if command -v curl >/dev/null 2>&1; then
  curl -fsSL "$URL" -o npm.tgz
else
  wget -qO npm.tgz "$URL"
fi

rm -rf "$HOME/.local/lib/node_modules/npm"
mkdir -p "$HOME/.local/lib/node_modules/npm"
tar xf npm.tgz -C "$HOME/.local/lib/node_modules/npm" --strip-components=1
ln -sf "$HOME/.local/lib/node_modules/npm/bin/npm-cli.js" "$HOME/.local/bin/npm"
ln -sf "$HOME/.local/lib/node_modules/npm/bin/npx-cli.js" "$HOME/.local/bin/npx"

export PATH="$HOME/.local/bin:$PATH"
grep -q '.local/bin' "$HOME/.bashrc" 2>/dev/null || \
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
npm config set registry "$REG"
npm config set prefix "$HOME/.local"

echo "OK npm: $(npm --version)"
echo "which npm: $(command -v npm)"
echo "global prefix: $(npm config get prefix)"
