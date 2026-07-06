You are the exam-generation agent. STAGE 0 — containerize an arbitrary repository.

Your working directory IS the cloned repo. scenario_type = {scenario_type}, language = {language}.

Goal: make this repo buildable + runnable in a hermetic container, and report how to run it.

1) Read the repo (README, build files, manifests, entry points) and write `Dockerfile.codebench`
   in the repo root that builds it into a RUNNABLE image:
   - Pick a base image appropriate for {language}. **Docker Hub is BLOCKED here — pull official base
     images from the China mirror `docker.m.daocloud.io/library/<name>:<tag>`** (e.g.
     `FROM docker.m.daocloud.io/library/golang:1.22-bookworm`, `.../library/python:3.12-slim`,
     `.../library/node:20-alpine`, `.../library/rust:1.82-slim`). The BUILD phase MAY use the network —
     use China mirrors (Go: `GOPROXY=https://goproxy.cn,direct`; Python:
     `-i https://pypi.tuna.tsinghua.edu.cn/simple`; Node: `--registry=https://registry.npmmirror.com`;
     Rust: USTC sparse crates mirror). **Install dependencies ONLINE during build — do NOT use
     offline/frozen installs** (`pip --no-index`, `pip wheel`+offline, `cargo build --frozen`/`--offline`,
     `CARGO_NET_OFFLINE=true`, `npm ci --offline`); they are the #1 build-failure cause. Only pre-fetch
     RUNTIME assets a tool downloads on first use (models/corpora) into the image. For a heavy monorepo,
     build only the single binary/package you need, not the whole workspace.
   - The image ENTRYPOINT must be the contract for scenario_type={scenario_type}:
       cli      -> the tool's binary/CLI (the harness appends cli args after the entrypoint)
       service  -> start the server, listen on `$PORT`, expose a health endpoint
       pipeline -> a command that reads an input path and writes an output path
   - The RUN phase runs WITH network available (the harness verifies determinism by running each
     input on the original TWICE and keeping only inputs whose two runs agree). A service reaches
     its declared DB/cache sidecars.

2) Write `{out_dir}/00_runtime.json` describing how to run it:
   {
     "scenario_type": "{scenario_type}",
     "service":  {"port": <int>, "health": "<path e.g. /health>", "env": { ... }},   // service ONLY
     "pipeline": {"in": "<container input path>", "out": "<container output path>", "cmd": [ ... ]}, // pipeline ONLY
     "dependencies": [ {"kind": "postgres|mysql|mongodb|redis|memcached", "env": "<ENV VAR the app reads for the connection URL>"} ],
     "smoke": [ "<args to pass for a quick cli --help/--version style smoke>" ],   // cli, optional
     "notes": "build/run caveats"
   }
   - `dependencies`: list ONLY external DB/cache the app needs at RUNTIME (not at build time).
     The harness starts them as sidecars on a shared network, injects the connection URL via the
     named env var, and RESETS their state before every test case.

Keep the image minimal, pinned, and deterministic. Output only the two file paths you wrote.
