"""Rewrite Dockerfile `FROM` lines to pull Docker Hub images via a China mirror.

Docker Hub (registry-1.docker.io) is GFW-blocked in this environment; the daemon has
no registry-mirror configured and we lack sudo to add one. So before `docker build`
we rewrite every `FROM` base image that resolves to Docker Hub to the daocloud mirror
`docker.m.daocloud.io`. Left untouched: other registries (ghcr.io/gcr.io/quay.io/...),
`scratch`, already-mirrored refs, and multi-stage build-stage references (`FROM <stage>`
where <stage> was named by an earlier `AS <stage>`).

This is deterministic and independent of whatever base image the agent happened to write.
"""
from __future__ import annotations

import pathlib
import re

MIRROR = "docker.m.daocloud.io"
_DOCKERHUB = {"docker.io", "index.docker.io", "registry-1.docker.io"}
_FROM = re.compile(r"^(\s*FROM\s+)((?:--\S+\s+)*)(\S+)(.*)$", re.IGNORECASE)
_AS = re.compile(r"^\s*FROM\s+.*\bAS\s+(\S+)\s*$", re.IGNORECASE)


def _mirror_ref(ref: str) -> str:
    if ref == "scratch":
        return ref
    if "/" not in ref:                               # bare official: name[:tag][@digest]
        return f"{MIRROR}/library/{ref}"             # the ':' here is a TAG, not a host:port
    first = ref.split("/", 1)[0]
    has_registry = ("." in first) or (":" in first) or first == "localhost"
    if has_registry:
        if first in _DOCKERHUB:                      # docker.io/... -> mirror/...
            rest = ref.split("/", 1)[1]
            if "/" not in rest:                      # docker.io/golang -> library/golang
                rest = "library/" + rest
            return f"{MIRROR}/{rest}"
        return ref                                   # ghcr.io / gcr.io / already-mirror -> leave
    return f"{MIRROR}/{ref}"                         # user/img (Docker Hub non-official)


def mirrorize_text(text: str):
    lines = text.splitlines()
    stages = {m.group(1).lower() for line in lines if (m := _AS.match(line))}
    out, changes = [], []
    for line in lines:
        m = _FROM.match(line)
        if not m:
            out.append(line)
            continue
        pre, flags, ref, tail = m.groups()
        if ref.lower() in stages:                    # FROM <earlier-stage> -> not an image
            out.append(line)
            continue
        new_ref = _mirror_ref(ref)
        if new_ref != ref:
            changes.append((ref, new_ref))
        out.append(f"{pre}{flags}{new_ref}{tail}")
    new_text = "\n".join(out) + ("\n" if text.endswith("\n") else "")
    return new_text, changes


def mirrorize_file(path) -> list:
    """Rewrite Docker Hub FROM refs in `path` in place. Returns [(old, new), ...]."""
    p = pathlib.Path(path)
    new_text, changes = mirrorize_text(p.read_text(encoding="utf-8"))
    if changes:
        p.write_text(new_text, encoding="utf-8")
    return changes
