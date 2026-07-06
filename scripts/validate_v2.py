import sys, json, pathlib
sys.path.insert(0, r"D:\code-bench\engine")
import config as cfg
out = []
for name in ["codegen-bench-v2", "pilot-v2"]:
    m = cfg.load_manifest(rf"D:\code-bench\dataset\{name}.manifest.json")
    cfgs = cfg.repo_configs(m, r"D:\code-bench")
    langs = {}
    forms = {}
    for c in cfgs:
        langs[c["language"]] = langs.get(c["language"], 0) + 1
        forms[c["scenario_type"]] = forms.get(c["scenario_type"], 0) + 1
    s = cfgs[0]
    out.append(f"{name}: {len(cfgs)} repos OK")
    out.append(f"  forms={forms}")
    out.append(f"  langs={dict(sorted(langs.items(), key=lambda x:-x[1]))}")
    out.append(f"  sample normalized: id={s['repo_id']} type={s['scenario_type']} lang={s['language']} image={s['image']} src={s['src']}")
pathlib.Path(r"D:\code-bench\scripts\v2-validate.txt").write_text("\n".join(out), encoding="utf-8")
print("\n".join(out[:1]))
