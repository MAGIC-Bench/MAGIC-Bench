#!/usr/bin/env bash
export PATH="$HOME/.local/bin:$PATH"
echo "=== codex --help (reason/effort/model) ==="
codex --help 2>&1 | grep -iE 'reason|effort|model' | head
echo "=== codex exec --help ==="
codex exec --help 2>&1 | grep -iE 'reason|effort|--config|-c,|model' | head
echo "=== docs/skills mentions of reasoning_effort enum ==="
grep -rhoiE '(model_)?reasoning_effort[^A-Za-z]{0,4}("?(minimal|none|low|medium|high|xhigh)"?[ ,|/]*){1,6}' ~/.codex 2>/dev/null | sort | uniq -c | head
echo "=== invalid-value probe (clap/serde should reject locally and list valid variants) ==="
timeout 20 codex exec -c model_reasoning_effort=__bogus__ --skip-git-repo-check "noop" 2>&1 \
  | grep -iE 'reason|effort|expected|valid|one of|minimal|low|medium|high|xhigh|none|variant|unknown' | head
