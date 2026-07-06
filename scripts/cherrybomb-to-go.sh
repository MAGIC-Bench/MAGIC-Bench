#!/usr/bin/env bash
cd /mnt/d/code-bench/out/exam-packages/blst-security-cherrybomb || exit 9
printf 'go\n' > generation_language.txt
python3 - <<'PY'
import pathlib
p = pathlib.Path("prompt.md")
t = p.read_text(encoding="utf-8")
t = t.replace("**rust**", "**go**").replace("用 rust", "用 go")
p.write_text(t, encoding="utf-8")
PY
echo "--- generation_language.txt ---"; cat generation_language.txt
echo "--- prompt.md (language line) ---"; grep -n "实现一个项目" prompt.md
cd /mnt/d/code-bench/out/exam-packages && rm -f blst-security-cherrybomb.tgz && tar czf blst-security-cherrybomb.tgz blst-security-cherrybomb
echo "repackaged: $(ls -1 blst-security-cherrybomb.tgz)"
