import re, json, pathlib

data = json.loads(pathlib.Path(r"D:\code-bench\scripts\report-data.json").read_text(encoding="utf-8"))

SCEN_KEY = {
    "CLI Tool": "cli_tool",
    "Serialization / Format": "serialization_format",
    "Cryptography / Security": "cryptography_security",
    "Web API": "web_api",
    "Database / Storage": "database_storage",
}
LANG = {"Rust": "rust", "Go": "go", "Python": "python", "JavaScript": "node", "TypeScript": "node",
        "C": "c", "C++": "cpp", "Java": "java", "Kotlin": "kotlin", "PHP": "php", "Ruby": "ruby",
        "C#": "csharp", "Shell": "shell"}
FORM = {"cli": "cli", "pipe": "pipeline", "svc": "service"}
PRESET = {"go", "rust", "python", "node"}


def scen_key(name):
    for k, v in SCEN_KEY.items():
        if name.startswith(k):
            return v
    return re.sub(r"[^a-z]+", "_", name.lower()).strip("_")


def rid(url):
    path = url.split("github.com/", 1)[-1]
    return re.sub(r"[^a-z0-9]+", "-", path.lower()).strip("-")


def norm(r, scen):
    return {
        "id": rid(r["url"]),
        "scenario": scen,
        "scenario_type": FORM.get(r["form"], "cli"),
        "language": LANG.get(r["lang"], r["lang"].lower()),
        "source": {"kind": "git", "url": r["url"] if r["url"].endswith(".git") else r["url"] + ".git", "ref": None},
        "_repo": r["url"].split("github.com/", 1)[-1],
        "_form": r["form"], "_build": r["build"], "_lang": r["lang"], "_src": r["src"],
    }


full = {"dataset": "codegen-bench-v2", "defaults": {"quota": 20, "runtime_mode": "docker"}, "repos": []}
for sc in data:
    key = scen_key(sc["scenario"])
    for r in sc["repos"]:
        full["repos"].append(norm(r, key))
pathlib.Path(r"D:\code-bench\dataset\codegen-bench-v2.manifest.json").write_text(
    json.dumps(full, ensure_ascii=False, indent=1), encoding="utf-8")


# exclude repos already used in pilot v1 (a NEW pilot should be new repos)
try:
    v1 = json.loads(pathlib.Path(r"D:\code-bench\dataset\pilot.manifest.json").read_text(encoding="utf-8"))
    V1 = {r["id"] for r in v1["repos"]}
except Exception:
    V1 = set()

# language reliability tier from v1 evidence: go/rust/python all completed exams; node was 0/4
# (monorepo builds + services all failed); java/etc. unproven; C/C++ native builds painful.
LTIER = {"go": 40, "rust": 40, "python": 40, "node": 16,
         "java": 9, "kotlin": 9, "csharp": 9, "ruby": 9, "php": 4, "shell": 4, "c": 2, "cpp": 2}


def score(r):
    s = {"cli": 100, "pipe": 50, "svc": 0}[r["_form"]]            # cli >> pipe >> svc (svc breaks @ stage5)
    s += LTIER.get(r["language"], 5)
    s += 4 if any(b in r["_build"] for b in ("go build", "cargo", "pip", "npm", "make ")) else 0
    return s


pilot = {"dataset": "codegen-bench-pilot-v2", "defaults": {"quota": 20, "runtime_mode": "docker"}, "repos": []}
report = []
for sc in data:
    key = scen_key(sc["scenario"])
    cands = [c for c in sorted((norm(r, key) for r in sc["repos"]), key=score, reverse=True)
             if c["id"] not in V1]
    picked, seen_lang = [], set()
    for c in cands:                                              # pass 1: 3 DISTINCT languages, best first
        if len(picked) >= 3:
            break
        if c["language"] in seen_lang:
            continue
        picked.append(c); seen_lang.add(c["language"])
    for c in cands:                                             # pass 2: backfill if <3 distinct available
        if len(picked) >= 3:
            break
        if c not in picked:
            picked.append(c)
    pilot["repos"].extend(picked)
    report.append((key, [(p["id"], p["scenario_type"], p["language"], p["_build"][:24]) for p in picked]))

pathlib.Path(r"D:\code-bench\dataset\pilot-v2.manifest.json").write_text(
    json.dumps(pilot, ensure_ascii=False, indent=1), encoding="utf-8")

out = [f"FULL manifest: {len(full['repos'])} repos -> dataset/codegen-bench-v2.manifest.json",
       f"PILOT v2: {len(pilot['repos'])} repos (3/scenario) -> dataset/pilot-v2.manifest.json", ""]
for key, picks in report:
    out.append(f"## {key}")
    for pid, st, lang, build in picks:
        out.append(f"   {pid:38s} {st:9s} {lang:8s} build={build}")
pathlib.Path(r"D:\code-bench\scripts\pilot-v2-selection.txt").write_text("\n".join(out), encoding="utf-8")
print("done")
