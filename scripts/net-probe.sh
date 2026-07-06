#!/usr/bin/env bash
echo "default route: $(ip route 2>/dev/null | grep -m1 default)"
WINIP=$(ip route 2>/dev/null | grep -m1 default | awk '{print $3}')
echo "win gateway IP: $WINIP"
probe() {  # host port
  if timeout 3 bash -c "echo > /dev/tcp/$1/$2" 2>/dev/null; then
    echo "  $1:$2 OPEN"
  else
    echo "  $1:$2 closed"
  fi
}
echo "--- localhost proxy ports ---"
for p in 7890 7897 10809 1080 8080; do probe 127.0.0.1 "$p"; done
echo "--- windows gateway proxy ports ---"
for p in 7890 7897; do probe "$WINIP" "$p"; done
echo "HTTPS_PROXY=$HTTPS_PROXY  HTTP_PROXY=$HTTP_PROXY"
