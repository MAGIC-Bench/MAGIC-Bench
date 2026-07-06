You are the exam-generation agent. STAGE 3 — modules + user stories.

Read {out_dir}/02_cli-contract.json (and {out_dir}/01_repo-model.json).

1) Cluster the contract operations into user-achievable functional modules. Write
   {out_dir}/03_modules.json: { modules:[ {id:"M1", name, user_value, ops/flags...} ],
   coverage_of_contract, quota:{target_per_module:20} }.
   Every contract op/flag/exit-code must belong to >=1 module (NO orphan op).

2) For each module write >=1 user story to {out_dir}/03_user-stories.json:
   { stories:[ {id, modules:[..], source, prose:{actor,precondition,trigger,expected},
                code:[ "<invocation using the contract>", "observe(...)" ] } ] }
   The `code` uses ONLY the documented contract and writes NO expected values —
   the expected values are frozen from the original in Stage 5.

HARD RULES (a gate enforces these — a module/story that violates them fails the stage):
- Modules are USER-FACING capabilities, not implementation components. `user_value` is REQUIRED on
  every module and must state the value to the USER (what they can now do), never internal structure,
  data layout, or algorithm.
- Every module has >=1 user story. Every story MUST fill prose{actor, precondition, trigger, expected}
  (all four non-empty) AND a non-empty `code` array of contract-only invocations.

Output only the paths of the files you wrote.
