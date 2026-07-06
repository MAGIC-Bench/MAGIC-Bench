#!/usr/bin/env bash
for id in afuh-rick-and-morty-api supabase-postgres-meta; do
  echo "===== out/$id =====";
  ls -la "/mnt/d/code-bench/out/$id/" 2>&1
  echo "  -- any contract-ish files anywhere in the dir --"
  find "/mnt/d/code-bench/out/$id/" -maxdepth 2 -iname '*contract*' -o -iname '*openapi*' -o -iname '02_*' 2>/dev/null
  echo
done
