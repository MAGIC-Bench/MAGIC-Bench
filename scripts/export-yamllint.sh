#!/usr/bin/env bash
cd /mnt/d/code-bench || exit 9
SRC=out/adrienverge-yamllint/07_exam
# drop the 2nd confirmed-poisoned stdin case (the grading exposed it; 1st was dropped earlier)
mkdir -p "$SRC/grader/_dropped_poisoned"
mv "$SRC/grader/cases/D-M3-M6-stdin-no-final-newline.json" "$SRC/grader/_dropped_poisoned/" 2>/dev/null \
   && echo "dropped no-final-newline poison" || echo "(no-final-newline already dropped)"
DEST=out/exports/yamllint-exam
rm -rf "$DEST"; mkdir -p "$DEST"
cp -a "$SRC/candidate" "$DEST/candidate"
cp -a "$SRC/grader"    "$DEST/grader"
rm -rf "$DEST/grader/_dropped_poisoned"            # don't ship dropped cases
cat > "$DEST/README.md" <<'EOF'
# yamllint exam (codegen-bench-v2)
candidate/  = 考生包(给做题 agent):prompt.md + generation_language.txt(python) + 02_cli-contract.json
              + 功能模块文档.md + 用户行为示例文档.md
grader/     = 判卷集(隐藏,别给做题 agent):带 golden 的黑盒用例 + pytest 套件
判卷:  CANDIDATE_BIN=<bin> pytest grader -q     或     CANDIDATE_IMAGE=<docker-img> pytest grader -q
注:已剔除 2 个 poisoned case(原仓 stdin 读取路径有 bug,把 stdin 输入误冻成 exit 0)。
EOF
( cd out/exports && tar czf yamllint-exam.tgz yamllint-exam )
echo "=== exported -> out/exports/yamllint-exam (+ .tgz) ==="
echo "candidate:"; ls -1 "$DEST/candidate"
echo "grader fair cases:"; ls "$DEST/grader/cases"/*.json | wc -l
echo "tarball size:"; du -h out/exports/yamllint-exam.tgz | cut -f1
