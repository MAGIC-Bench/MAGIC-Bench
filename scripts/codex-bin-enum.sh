#!/usr/bin/env bash
BIN=$(find ~/.local/lib/node_modules/@openai/codex -type f -size +5M 2>/dev/null | head -1)
echo "binary: $BIN"
echo "=== lines listing the effort variants together (help / enum) ==="
strings -n 6 "$BIN" 2>/dev/null | grep -iE 'minimal.*low.*medium.*high|low.*medium.*high|effort' | grep -iE 'minimal|low|medium|high|none|xhigh' | head -12
echo "=== does an 'xhigh' tier exist? ==="
strings "$BIN" 2>/dev/null | grep -iwE 'xhigh' | head -3 || echo "  (no xhigh)"
echo "=== does a 'none' effort exist near reasoning? ==="
strings -n 5 "$BIN" 2>/dev/null | grep -iE 'reasoning' | grep -iE 'none|minimal' | head -5
