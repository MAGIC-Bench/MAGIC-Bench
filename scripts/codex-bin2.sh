#!/usr/bin/env bash
BIN=$(find ~/.local/lib/node_modules/@openai/codex -type f -printf '%s\t%p\n' 2>/dev/null \
      | grep -i codex | grep -viE '/rg$|\.js$|\.json$|\.node$' | sort -rn | head -1 | cut -f2)
echo "binary: $BIN ($(stat -c%s "$BIN" 2>/dev/null) bytes)"
echo "=== minimal/xhigh occurrences (distinctive tiers) ==="
strings "$BIN" 2>/dev/null | grep -iwE 'minimal|xhigh' | sort | uniq -c | head
echo "=== a line listing the variants / possible values ==="
strings -n 8 "$BIN" 2>/dev/null | grep -iE 'minimal.{0,4}low.{0,4}medium.{0,4}high|possible values|reasoning effort' | head -6
