You are the exam-generation agent. STAGE 2 — contract.

Read {out_dir}/01_repo-model.json and the source at {repo_dir}.

For a `cli` repo, write {out_dir}/02_cli-contract.json with keys:
  contract_type:"cli", binary, usage,
  actions {precedence:[...], <action>:doc, ...},
  flags[] — each {long, short, alias?, type, doc},
  input_resolution {...},
  exit_codes {"<n>": meaning, ...},
  io_contract {stdin, stdout, stderr, color},
  candidate_delivery {must, network_inputs}.

Every flag, action, and exit code that exists in the source MUST appear. This is the
locked contract the candidate implements and the black-box tests bind to.

Write the contract to the EXACT path for this repo's scenario_type — do NOT invent a
different filename:
  - cli      -> {out_dir}/02_cli-contract.json       (the keys listed above)
  - service  -> {out_dir}/02_contract.openapi.json   (a valid OpenAPI 3 spec as JSON:
                paths, methods, status codes, request/response schemas, auth)
  - pipeline -> {out_dir}/02_contract.io.json        (input path/format -> output
                path/format, the invocation command, exit codes)
Output only the path of the file you wrote.
