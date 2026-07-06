#!/usr/bin/env bash
NEWEST=$(find ~/.codex -type f -name '*.jsonl' -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)
echo "newest: $NEWEST"
echo "=== session_meta payload (minus base_instructions) ==="
head -1 "$NEWEST" | python3 -c "import sys,json; d=json.load(sys.stdin); p=d.get('payload',{}); p.pop('base_instructions',None); print(json.dumps(p,indent=2))" 2>/dev/null
echo "=== turn_context / config records (first match) ==="
grep -hoE '\{[^{]*"reasoning[^}]*\}' "$NEWEST" 2>/dev/null | head -3
echo "=== effort/model/verbosity config across ALL sessions ==="
grep -rhoE '"reasoning_effort":"[a-z]+"|"effort":"[a-z]+"|"model":"[^"]+"|"model_reasoning_effort":"[a-z]+"|"verbosity":"[a-z]+"|"summary":"[a-z]+"' ~/.codex/sessions 2>/dev/null | sort | uniq -c | sort -rn | head -20
echo "=== any 'effort' substring anywhere in newest ==="
grep -oE '[a-z_]*effort[a-z_]*"?:?"?[a-z]*' "$NEWEST" 2>/dev/null | sort | uniq -c | head
