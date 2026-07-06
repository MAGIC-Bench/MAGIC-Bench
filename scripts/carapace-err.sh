#!/usr/bin/env bash
cd /mnt/d/code-bench || exit 9
echo "=== carapace full STATUS ==="
cat out/carapace-sh-carapace-bin/STATUS.json
echo; echo "=== stage7 verify artifact (if any) ==="
cat out/carapace-sh-carapace-bin/07_verify.json 2>/dev/null | head -30 || echo "(none)"
echo "=== runtime / image info ==="
cat out/carapace-sh-carapace-bin/00_runtime.json 2>/dev/null | head -20
echo "=== what stage7_verify references (grep its source) ==="
grep -nE "FileNotFound|repo_src|cover|\.exe|/bin|launch|binary|open\(|read_text|Path\(" stages/stage7_verify.py | head -25
