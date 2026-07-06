#!/usr/bin/env bash
cd /mnt/d/code-bench || exit 9
DEST=out/exam-packages
# package yamllint candidate side (agent-facing only)
mkdir -p "$DEST/adrienverge-yamllint"
cp -a out/adrienverge-yamllint/07_exam/candidate/. "$DEST/adrienverge-yamllint/"
rm -rf "$DEST/adrienverge-yamllint/grader" "$DEST/adrienverge-yamllint/cases" 2>/dev/null
( cd "$DEST" && tar czf adrienverge-yamllint.tgz adrienverge-yamllint )
echo "=== final agent packages (out/exam-packages/) ==="
ls -1 "$DEST"
echo
echo "=== locate yamllint poisoned case (stdin fed malformed YAML but exit pinned 0) ==="
python3 - <<'PY'
import json, pathlib
cases = pathlib.Path("out/adrienverge-yamllint/07_exam/grader/cases")
for f in sorted(cases.glob("*.json")):
    d = json.loads(f.read_text(encoding="utf-8"))
    argv = d.get("input", {}).get("argv", [])
    stdin = d.get("input", {}).get("stdin") or d.get("input", {}).get("stdin_b64")
    uses_stdin = ("-" in argv) or bool(stdin)
    exit_a = [a.get("value") for a in d.get("assertions", []) if a.get("field") == "exit"]
    # flag stdin cases pinned to exit 0
    if uses_stdin and exit_a and (exit_a[0] in (0, {"int": 0})):
        print(f"  {f.name}  argv={argv}  exit_assert={exit_a}  modules={d.get('modules')}")
print("--- total yamllint grader cases:", len(list(cases.glob('*.json'))))
PY
echo
echo "=== cherrybomb grader cases total ==="
ls out/blst-security-cherrybomb/07_exam/grader/cases/*.json 2>/dev/null | wc -l
