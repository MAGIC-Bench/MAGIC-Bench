import json, pathlib
out = pathlib.Path('/mnt/d/code-bench/out')
done = ['alexpovel-srgn', 'bee-san-name-that-hash', 'benhoyt-goawk',
        'betterleaks-betterleaks', 'eralchemy-eralchemy', 'homeport-dyff']
hdr = "%-30s %5s  %-9s %6s %7s  %s" % ("repo", "tests", "mods>=20", "nondet", "badspec", "needs_review")
print(hdr)
for r in done:
    led = out / r / '05_coverage-ledger.json'
    ex = out / r / '07_exam'
    if not led.exists():
        print("%-30s (no ledger)" % r)
        continue
    s = json.loads(led.read_text(encoding='utf-8')).get('summary', {})
    pm = s.get('per_module', {})
    q = s.get('quota', 20)
    atq = sum(1 for v in pm.values() if v >= q)
    bundle = "OK" if (ex / "grader").exists() and (ex / "candidate").exists() else "MISSING"
    print("%-30s %5s  %-9s %6s %7s  %s  [bundle:%s]" % (
        r, s.get("tests_emitted", "?"), "%d/%d" % (atq, len(pm)),
        s.get("dropped_nondeterministic", 0), s.get("dropped_bad_spec", 0),
        s.get("needs_review", []), bundle))
