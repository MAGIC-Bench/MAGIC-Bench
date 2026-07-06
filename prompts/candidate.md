You are the system under evaluation. Build a complete, working project from a specification.

The specification is in `./SPEC/` — read EVERY file:
- `项目描述.md`             — what the program does for its users (business background)
- `用户API使用手册.md`      — the external interface you MUST expose (commands/flags/exit-codes/IO, or HTTP endpoints)
- `功能模块文档.md`          — the feature list to implement (organize the code however you like)
- `用户行为示例文档.md`      — worked user-behaviour examples (NO expected values)
- `非功能需求.md`            — non-functional requirements to satisfy
- `02_*` (if present)       — the machine-readable contract, consistent with the API manual
- `generation_language.txt` — the REQUIRED implementation language

Build the project in the CURRENT directory:
- Implement it in EXACTLY the language named in `generation_language.txt`.
- Implement every operation / flag / endpoint / exit-code in the contract, with the documented behavior.
- Provide a `Dockerfile` that builds a runnable image whose entrypoint matches scenario_type={scenario_type}:
  - cli      → ENTRYPOINT is the tool binary; the test harness passes cli args
  - service  → listens on `$PORT`, serves the documented endpoints + a health endpoint
  - pipeline → a command that reads the input path and writes the output path
- The image must build and run (the network is available at run time; the grader verifies
  determinism by replaying frozen, double-run-checked test cases).
- Match the contract's EXACT output format / status codes / exit codes — grading is black-box.

Write all source files + the `Dockerfile` to the current working directory. Do not read anything
outside `./SPEC/` and your own files. When done, stop.
