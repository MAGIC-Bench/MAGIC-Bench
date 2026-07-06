import re, pathlib, html as ht
P = pathlib.Path(r"C:\Users\16611\AppData\Roaming\Claude\local-agent-mode-sessions\f9b20565-7a07-43a1-9132-d53a519015b4\417d732e-5246-4abc-99b9-c718780f9c37\local_0efcdd53-aba7-4f2d-b7f8-74f6c8ccf94b\outputs\final_report.html")
s = P.read_text(encoding="utf-8", errors="replace")
out = []
out.append(f"chars: {len(s)}   lines: {s.count(chr(10))+1}")
out.append("=== headings (h1-h4) ===")
for m in re.finditer(r"<(h[1-4])[^>]*>(.*?)</\1>", s, re.I | re.S):
    t = re.sub(r"<[^>]+>", "", m.group(2)).strip()
    if t:
        out.append(f"  {m.group(1)} {ht.unescape(t)[:90]!r}")
out.append("=== table headers (th) ===")
ths = [ht.unescape(re.sub(r"<[^>]+>", "", m.group(1)).strip()) for m in re.finditer(r"<th[^>]*>(.*?)</th>", s, re.I | re.S)]
out.append("  " + repr(ths[:30]))
out.append("=== sample window around first github url ===")
i = s.find("github.com")
out.append(repr(s[i-400:i+150]))
out.append("=== js data vars ===")
for m in re.finditer(r"(var|const|let)\s+(\w+)\s*=", s):
    out.append("  jsvar: " + m.group(2))
pathlib.Path(r"D:\code-bench\scripts\report-structure.txt").write_text("\n".join(out), encoding="utf-8")
print("written")
