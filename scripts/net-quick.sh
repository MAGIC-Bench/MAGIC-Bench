#!/usr/bin/env bash
echo "=== networking (mirrored should NOT show 172.23.x NAT gateway) ==="
ip route 2>/dev/null | grep -m1 default || echo "no default route"
echo "=== reachability (401=reachable+unauth=GOOD, 000=blocked) ==="
curl -sS -o /dev/null -w "api.openai.com -> %{http_code} (%{time_total}s)\n" --max-time 20 https://api.openai.com/v1/models 2>&1 || echo "api FAILED"
curl -sS -o /dev/null -w "google.com    -> %{http_code} (%{time_total}s)\n" --max-time 15 https://www.google.com 2>&1 || echo "google FAILED"
