You are the exam-generation agent. STAGE 0 (LOCAL) — your `build.sh` FAILED. Fix it.

scenario_type = {scenario_type}, language = {language}. Working dir IS the repo.

The build error:
---
{build_error}
---

Diagnose and fix `build.sh` (and `{out_dir}/00_runtime.json` if the `launch` path was wrong). Common causes:
- offline/frozen installs — remove `--frozen`/`--offline`/`--no-index`/`CARGO_NET_OFFLINE`; install ONLINE via China mirrors.
- missing toolchain — install it locally (venv / local target), avoid root system packages if possible.
- wrong build target in a monorepo — build only the single binary/package needed.
- collisions with other repos — isolate into THIS repo (.venv / local target / local node_modules).
- wrong `launch` in 00_runtime.json — point it at the actual built artifact (absolute path).

Re-run `build.sh` until it exits 0, then run `launch` with the smoke args to confirm. Output ONLY the file(s) you changed.
