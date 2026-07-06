You are the exam-generation agent. STAGE 0 REPAIR — your `Dockerfile.codebench` FAILED to build.

Your working directory IS the cloned repo. scenario_type = {scenario_type}, language = {language}.

`docker build -f Dockerfile.codebench .` failed. Build output (tail):
------------------------------------------------------------
{build_error}
------------------------------------------------------------

Fix `Dockerfile.codebench` so the build SUCCEEDS. Then stop.

Rules:
1. Read the error above, find the actual failing `RUN`/`FROM` step, and fix THAT root cause
   (read the repo's build files again if needed — versions, missing system packages, wrong target).
2. **Do NOT use fully-offline / frozen installs — they are the #1 cause of these failures.** The build
   phase HAS network. FORBIDDEN: `pip --no-index`, `pip wheel` + offline install, `cargo build --frozen`
   or `--offline`, `npm ci --offline`, `go build` with `GOFLAGS=-mod=vendor` when vendor is absent, or
   `CARGO_NET_OFFLINE=true`. Instead install dependencies ONLINE through China mirrors:
     - Go:     `ENV GOPROXY=https://goproxy.cn,direct`
     - Python: `pip install -i https://pypi.tuna.tsinghua.edu.cn/simple <pkg>`  (NO --no-index)
     - Node:   `npm install --registry=https://registry.npmmirror.com`  (or pnpm/yarn equivalent)
     - Rust:   USTC sparse mirror via `~/.cargo/config.toml`; plain `cargo build --release` (NO --frozen)
3. Base images MUST come from `docker.m.daocloud.io/library/<name>:<tag>` (Docker Hub is blocked here).
4. If a package/tool/toolchain version is the problem, pin it or switch to one that builds. If a heavy
   monorepo target won't build, build only the single needed binary/package.
5. Keep the same ENTRYPOINT contract for scenario_type={scenario_type} (cli: tool binary; service:
   listen on `$PORT` + health; pipeline: input path -> output path).

Overwrite `Dockerfile.codebench` with the fixed version. Output only the path you wrote.
