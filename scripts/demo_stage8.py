import sys, pathlib, json
root = pathlib.Path(r"D:\code-bench")
for d in ("engine", "stages"):
    sys.path.insert(0, str(root / d))
import stage8_package

repo_out = root / "out" / "groncx"
# what the updated Stage 1 would add:
p01 = repo_out / "01_repo-model.json"
rm = json.loads(p01.read_text(encoding="utf-8"))
rm["rewritable_languages"] = ["go", "rust", "python", "node", "cpp", "java", "ocaml"]
p01.write_text(json.dumps(rm, indent=2, ensure_ascii=False), encoding="utf-8")

config = {"repo_id": "groncx", "scenario_type": "cli", "language": "go"}
rep = stage8_package.run(repo_out, config, generation_language="rust")
print("package.json:", json.dumps(rep, ensure_ascii=False))
print("\n=== 07_exam tree ===")
exam = repo_out / "07_exam"
for p in sorted(exam.rglob("*")):
    if p.is_file() and "cases" not in p.parts:
        print(f"  {p.relative_to(repo_out)}  ({p.stat().st_size}b)")
print(f"  grader/cases/  ({len(list((exam/'grader'/'cases').glob('*.json')))} testcase json)")
