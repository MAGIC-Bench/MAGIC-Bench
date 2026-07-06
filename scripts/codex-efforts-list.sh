#!/usr/bin/env bash
BIN=/home/kiwi/.local/lib/node_modules/@openai/codex/node_modules/@openai/codex-linux-x64/vendor/x86_64-unknown-linux-musl/bin/codex
echo "=== explicit comma-separated lists of the tiers ==="
strings "$BIN" 2>/dev/null | grep -oiE '(minimal, ?)?low, ?medium, ?high(, ?xhigh)?' | sort | uniq -c
echo "=== 'possible values' lines mentioning effort tiers ==="
strings "$BIN" 2>/dev/null | grep -iE 'possible values' | grep -iE 'minimal|medium|xhigh' | head
echo "=== clap value-enum style [minimal|low|medium|high|xhigh] ==="
strings "$BIN" 2>/dev/null | grep -oiE '\[?(minimal\|)?low\|medium\|high(\|xhigh)?\]?' | sort | uniq -c
echo "=== standalone 'xhigh' and 'minimal' as bare tokens ==="
strings "$BIN" 2>/dev/null | grep -cxiE 'xhigh'; strings "$BIN" 2>/dev/null | grep -cxiE 'minimal'
