"""De-identification shared by the Stage-1 gate and the Stage-8 packager.

extract the repo-identity tokens (binary + repo/owner name parts, minus generic domain/structural
words) and scrub them out of EVERY candidate-facing string, so the exam package can't be used to
re-identify the original repo. Substring (not word-boundary) match so camelCase / compound forms
like `yamllintRun` are caught too. The binary name is ALWAYS an identity token even if it collides
with a generic word (e.g. httpie's `http`) -- de-identification beats contract prettiness.
"""
from __future__ import annotations

import re

GENERIC = "app"

# domain / structural words that are NOT uniquely identifying -> never treated as identity tokens
# (so a YAML tool's contract keeps the word "yaml"; only the distinctive name/owner get scrubbed).
NAME_STOP = {
    "yaml", "yml", "json", "http", "https", "xml", "csv", "html", "toml", "ini", "md", "cli", "api",
    "tool", "tools", "lib", "libs", "go", "py", "js", "ts", "rs", "rb", "run", "out", "exit", "file",
    "std", "app", "core", "main", "src", "util", "utils", "service", "pipeline", "the", "and", "for",
    "cmd", "bin", "data", "text", "code", "io", "os", "db",
    # common English function/domain words that are NOT repo-identifying
    "that", "this", "with", "from", "name", "type", "types", "hash", "key", "id",
    "check", "test", "run", "get", "set", "new", "old", "all", "any", "by",
    # host / VCS / TLD noise from repo_id (e.g. github.com/...) -- not identifying, and short ones
    # like "com" used to substring-corrupt words ("command" -> "appmand")
    "com", "github", "gitlab", "bitbucket", "gitee", "www", "net", "org", "git",
}


def _binary_names(binary):
    """All program-name strings from a binary spec. Handles str, list, or a dict like
    {primary, name, additional/aliases:[...], module_entrypoint:"python3 -m name_that_hash"}.
    Without this, dict-shaped binaries (ogen->jschemagen, nth->name-that-hash) leak into candidate docs."""
    out = []
    if isinstance(binary, str):
        if binary.strip():
            out.append(binary.strip())
    elif isinstance(binary, (list, tuple)):
        out += [x.strip() for x in binary if isinstance(x, str) and x.strip()]
    elif isinstance(binary, dict):
        for k in ("primary", "name", "binary"):
            v = binary.get(k)
            if isinstance(v, str) and v.strip():
                out.append(v.strip())
        for k in ("additional", "aliases", "names", "alias"):
            v = binary.get(k)
            if isinstance(v, (list, tuple)):
                out += [x.strip() for x in v if isinstance(x, str) and x.strip()]
            elif isinstance(v, str) and v.strip():
                out.append(v.strip())
        me = binary.get("module_entrypoint")       # "python3 -m name_that_hash" -> name_that_hash
        if isinstance(me, str):
            for t in me.replace("-m", " ").split():
                if t and not t.startswith("-") and t not in ("python", "python3", "python2"):
                    out.append(t)
    return out


def identity_tokens(repo_id, binary=None):
    """Distinctive identity strings to scrub: the binary name(s) (always, even if dict-shaped) + repo_id
    name/owner parts (split on / - _ . space), dropping generic domain words."""
    toks = set()
    for name in _binary_names(binary):                 # binary name(s) ALWAYS identity tokens (added whole)
        toks.add(name)
    for part in re.split(r"[/\-_. ]+", str(repo_id or "")):
        part = part.strip()
        if len(part) >= 2 and part.lower() not in NAME_STOP:
            toks.add(part)
    return sorted({t for t in toks if t}, key=len, reverse=True)   # longest first: scrub compounds before parts


def scrub_text(text, toks):
    """Replace every identity token (case-insensitive) with the generic placeholder. SHORT tokens
    (<=4 chars: nth, sq, jd, com) match only at word boundaries -- substring would corrupt unrelated
    words (sqlite->applite, command->appmand). LONGER tokens use substring so camelCase compounds
    (yamllintRun) are still caught."""
    s = str(text)
    for n in toks:
        pat = (r"\b" + re.escape(n) + r"\b") if len(n) <= 4 else re.escape(n)
        s = re.sub(pat, GENERIC, s, flags=re.IGNORECASE)
    return s


def leak_tokens(text, toks):
    """Identity tokens that appear (word-boundary) in text -> used by the gate to reject a leaky brief."""
    return [n for n in toks if re.search(r"\b" + re.escape(n) + r"\b", str(text), re.IGNORECASE)]
