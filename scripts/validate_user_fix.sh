#!/usr/bin/env bash
mkdir -p /tmp/usertest && rm -f /tmp/usertest/* 2>/dev/null
IMG=docker.1ms.run/library/python:3.12-slim
echo "host uid:gid = $(id -u):$(id -g)"
echo "=== OLD behavior: container as root writes a 0600 output file ==="
docker run --rm -v /tmp/usertest:/work -w /work "$IMG" \
  python -c "import os;f='/work/root600.yml';open(f,'w').write('x');os.chmod(f,0o600)" 2>&1
echo "=== NEW behavior (the fix): --user host-uid + HOME=/tmp ==="
docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp -v /tmp/usertest:/work -w /work "$IMG" \
  python -c "import os;f='/work/user600.yml';open(f,'w').write('x');os.chmod(f,0o600)" 2>&1
echo "=== file ownership (uid in 3rd col) ==="
ls -ln /tmp/usertest
echo "=== host (non-root) read root600.yml  -> reproduces the bug ==="
( cat /tmp/usertest/root600.yml >/dev/null 2>&1 && echo "  read OK" ) || echo "  PermissionError (the original sq failure)"
echo "=== host read user600.yml  -> fixed path ==="
( cat /tmp/usertest/user600.yml >/dev/null 2>&1 && echo "  read OK (fix works)" ) || echo "  still denied"
