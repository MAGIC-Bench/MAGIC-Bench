"""Fill manifest 'language' from GitHub API (token via GH_TOKEN env, never hardcoded)."""
import json, os, pathlib, time, urllib.request, urllib.error
from collections import Counter

MAN = "/mnt/d/code-bench/dataset/codegen-bench.manifest.json"
TOKEN = os.environ.get("GH_TOKEN", "")
man = json.loads(pathlib.Path(MAN).read_text(encoding="utf-8"))

# GitHub primary-language -> our preset key (go/python/rust/node have Dockerfile presets)
MAP = {"Go": "go", "Python": "python", "Rust": "rust", "JavaScript": "node", "TypeScript": "node",
       "C++": "cpp", "C": "c", "Ruby": "ruby", "PHP": "php", "Java": "java", "Scala": "scala",
       "Shell": "shell", "Perl": "perl", "Swift": "swift", "C#": "csharp", "Haskell": "haskell",
       "Kotlin": "kotlin", "Lua": "lua", "Elixir": "elixir", "OCaml": "ocaml", "Nix": "nix",
       "Zig": "zig", "Crystal": "crystal", "Dart": "dart", "Roff": "roff"}


def gh(owner_repo):
    req = urllib.request.Request(f"https://api.github.com/repos/{owner_repo}")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "codebench-lang-detect")
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read())


done, fail = 0, []
for repo in man["repos"]:
    name = repo["_repo"]
    try:
        d = gh(name)
        lang = d.get("language")
        repo["language"] = MAP.get(lang, lang.lower() if lang else "unknown")
        repo["_gh_language"] = lang
        repo["source"]["ref"] = None  # keep null; record branch for later pinning
        repo["_default_branch"] = d.get("default_branch")
        done += 1
    except Exception as e:
        fail.append((name, str(e)[:90]))
    time.sleep(0.04)

pathlib.Path(MAN).write_text(json.dumps(man, indent=2, ensure_ascii=False), encoding="utf-8")
print("detected:", done, "| failed:", len(fail))
print("languages:", dict(Counter(r["language"] for r in man["repos"]).most_common()))
preset = {"go", "python", "rust", "node"}
print("has-preset (runnable Dockerfile):", sum(1 for r in man["repos"] if r["language"] in preset),
      "| no-preset (need Dockerfile):", sum(1 for r in man["repos"] if r["language"] not in preset))
if fail:
    print("failures:", fail[:15])
