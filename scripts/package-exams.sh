#!/usr/bin/env bash
# Build agent-facing exam packages = candidate/ side ONLY (prompt + gen-language + 功能模块文档 +
# 用户行为示例 + contract). The grader/ (hidden tests + golden + metrics) is NOT included.
cd /mnt/d/code-bench || exit 9
DEST=out/exam-packages
rm -rf "$DEST"; mkdir -p "$DEST"
for id in cisco-ai-defense-skill-scanner blst-security-cherrybomb; do
  cand="out/$id/07_exam/candidate"
  dst="$DEST/$id"
  mkdir -p "$dst"
  cp -a "$cand"/. "$dst"/
  rm -rf "$dst"/grader "$dst"/cases 2>/dev/null         # belt: never ship hidden content
  ( cd "$DEST" && tar czf "$id.tgz" "$id" )
  echo "=== $id (agent package) ==="; ls -1 "$dst"
  echo "  grader tests (kept separately for YOU): $(ls out/$id/07_exam/grader/cases/*.json 2>/dev/null | wc -l)"
done
echo "=== packages at out/exam-packages/ ==="; ls -la "$DEST"
