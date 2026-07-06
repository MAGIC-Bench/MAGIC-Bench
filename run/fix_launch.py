#!/usr/bin/env python3
"""判卷前修正候选 run.json 的 launch 路径:做题节点把 launch 写成自己本地的绝对路径
(/tmp/exam_work/<agent>/<id>/... 或旧的 /root/exam_work/...),判卷在另一台节点、build.sh 重建在
submissions/.../work,所以要把那段本地绝对路径重写成本机 work 目录下的路径。python/node 这类命令保持不变。
  fix_launch.py <work_dir>  ->  打印重写后的 launch(空格分隔)"""
import json, os, re, sys

work = sys.argv[1]
try:
    launch = json.load(open(os.path.join(work, "run.json"), encoding="utf-8")).get("launch", [])
except Exception:
    launch = []

def fix(p):
    # 做题节点本地绝对路径 -> 本机 work。WORKROOT 现在是 /tmp/exam_work(隔离后改的),也兼容旧的 /root/exam_work。
    m = re.match(r"^/(?:tmp|root)/exam_work/[^/]+/[^/]+/(.*)$", p)
    if m:
        return os.path.join(work, m.group(1))
    if not p.startswith("/") and ("/" in p or os.path.exists(os.path.join(work, p))):
        return os.path.join(work, p)                        # 相对文件路径 -> work 下
    return p                                                # python / node / 系统绝对路径 等保持

print(" ".join(fix(x) for x in launch))
