#!/usr/bin/env bash
BIN=/home/kiwi/.local/lib/node_modules/@openai/codex/node_modules/@openai/codex-linux-x64/vendor/x86_64-unknown-linux-musl/bin/codex
echo "=== distinct values seen as \"effort\": \"X\" ==="
strings "$BIN" 2>/dev/null | grep -oE '"effort": *"[a-z]+"' | sort | uniq -c
echo "=== distinct values seen as reasoning_effort=... / 'reasoning effort ... X' ==="
strings "$BIN" 2>/dev/null | grep -oiE 'reasoning_effort[\"= :]+[a-z]+' | sort | uniq -c | head
echo "=== context around 'Supported reasoning efforts' ==="
strings -n 4 "$BIN" 2>/dev/null | grep -iE 'supported reasoning effort|reasoning efforts:|valid reasoning' | head
echo "=== is 'none' a reasoning effort? (vs just the word none) ==="
strings "$BIN" 2>/dev/null | grep -oE '"effort": *"none"|reasoning_effort[\"= :]+none' | sort | uniq -c
