import json, pathlib
raw = pathlib.Path(r"C:\Users\16611\AppData\Local\Temp\claude\C--\8e07b3fa-bd67-44cd-906c-c2e099ed0fb8\tasks\w2ec9e5gt.output").read_text(encoding="utf-8")
data = json.loads(raw)
result = data["result"] if isinstance(data, dict) and "result" in data else data
tx = next(r for r in result if r.get("repo") == "dinedal-textql")
df = tx["fixed_dockerfile"]
assert df and "FROM" in df, "no fixed_dockerfile"
p = pathlib.Path(r"D:\code-bench\repos\dinedal-textql\Dockerfile.codebench")
p.write_text(df, encoding="utf-8")
print(f"wrote {p} ({len(df)} chars)")
for ln in df.splitlines():
    if ln.strip().upper().startswith(("FROM", "RUN apt", "ENTRYPOINT")):
        print("  ", ln[:90])
