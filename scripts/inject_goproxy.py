import sys, pathlib
pkg = pathlib.Path(sys.argv[1])
t = pkg.joinpath("Dockerfile").read_text(encoding="utf-8")
out = []
for ln in t.splitlines():
    out.append(ln)
    s = ln.strip().lower()
    if s.startswith("from") and "golang" in s:          # GFW: route go modules via China proxy
        out.append("ENV GOPROXY=https://goproxy.cn,direct GOSUMDB=off GOFLAGS=-mod=mod")
pkg.joinpath("Dockerfile.grade").write_text("\n".join(out) + "\n", encoding="utf-8")
print("Dockerfile.grade written")
