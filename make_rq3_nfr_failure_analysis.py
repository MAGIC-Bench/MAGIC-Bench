#!/usr/bin/env python3
import json
from collections import defaultdict, Counter
from pathlib import Path

ROOT = Path('backup_clean/chuti-run')
GRADES = ROOT / 'grades'
SUBS = ROOT / 'submissions'
CLI_SUMMARY = Path('cli_interface_compliance_summary.json')
OUT_JSON = Path('rq3_nfr_failure_top10.json')
OUT_MD = Path('rq3_nfr_failure_top10.md')

MAIN_AGENTS = ['claude', 'codex', 'cursor', 'kimi']
EXCLUDE_REPOS = {'dosisod-refurb'}
AGENT_LABEL = {'claude':'Claude Code','codex':'Codex','cursor':'Cursor','kimi':'Kimi Code','agy':'agy 基线'}
DIM_LABEL = {'CMP':'兼容性','MTN':'可维护性','PERF':'性能效率','PTB':'可移植/构建','RLY':'可靠性','SEC':'安全性'}
METRIC_LABEL = {
    'CMP.CMP1': '共享环境可启动',
    'CMP.CLI': 'CLI 接口契约完全符合',
    'CMP.CMP2': '服务接口契约符合',
    'MTN.MTN1': '无超大单文件',
    'MTN.MTN2': '无跨层反向依赖',
    'MTN.MTN3': '无循环依赖',
    'MTN.MTN4': '认知复杂度合规',
    'MTN.MTN5': 'README 文档完整',
    'PERF.PERF1': '运行无崩溃/OOM/超时',
    'PERF.PERF2': '尾部延迟稳定',
    'PERF.PERF3': '内存峰值合规',
    'PERF.PERF4': '限时正确通过',
    'PTB.PTB1': '标准构建通过',
    'PTB.PTB2': '无硬编码路径',
    'PTB.PTB3': '日志不写源码目录',
    'PTB.PTB4': '显式编码声明',
    'PTB.PTB5': '无环境变量强依赖',
    'PTB.PTB6': '无平台强绑定',
    'RLY.RLY1': '长时/重复执行无故障',
    'RLY.RLY2': '脏状态重启可用',
    'RLY.RLY3': '数据库断连容错',
    'RLY.RLY4': '资源压力容错',
    'RLY.RLY5': '并发执行无故障',
    'RLY.RLY6': '强制终止后可恢复',
    'SEC.SEC1': '未授权读阻断',
    'SEC.SEC2': '无敏感信息硬编码',
    'SEC.SEC3': '敏感字段加密存储',
    'SEC.SEC4': '未授权写阻断',
    'SEC.SEC5': 'SQL 注入防护',
    'SEC.SEC6': '审计日志完备',
}

stats = defaultdict(lambda: {
    'metric': '', 'dim': '', 'name': '', 'applicable': 0, 'passed': 0, 'failed': 0,
    'by_agent': {a: {'applicable':0,'passed':0,'failed':0} for a in MAIN_AGENTS},
    'examples': []
})
project_build_ok = defaultdict(dict)

for score_path in GRADES.glob('*/*/score.json'):
    repo = score_path.parent.parent.name
    agent = score_path.parent.name
    if agent not in MAIN_AGENTS or repo in EXCLUDE_REPOS:
        continue
    try:
        data = json.loads(score_path.read_text(encoding='utf-8'))
    except Exception:
        continue
    build_ok = data.get('build_ok') is True
    project_build_ok[agent][repo] = build_ok
    if not build_ok:
        continue
    bydim = data.get('nfr_by_dimension') or {}
    for dim, metrics in bydim.items():
        if not isinstance(metrics, dict):
            continue
        for mid, val in metrics.items():
            if val is None:
                continue
            key = f'{dim}.{mid}'
            s = stats[key]
            s['metric'] = key
            s['dim'] = dim
            s['name'] = METRIC_LABEL.get(key, mid)
            s['applicable'] += 1
            s['by_agent'][agent]['applicable'] += 1
            if int(val) == 1:
                s['passed'] += 1
                s['by_agent'][agent]['passed'] += 1
            else:
                s['failed'] += 1
                s['by_agent'][agent]['failed'] += 1
                if len(s['examples']) < 12:
                    s['examples'].append({'repo': repo, 'agent': agent, 'score_path': str(score_path)})

# Add CLI full-contract compliance as a CMP metric, project-level binary, build_ok-only denominator.
if CLI_SUMMARY.exists():
    cli = json.loads(CLI_SUMMARY.read_text(encoding='utf-8'))
    key = 'CMP.CLI'
    s = stats[key]
    s['metric'] = key
    s['dim'] = 'CMP'
    s['name'] = METRIC_LABEL[key]
    for agent in MAIN_AGENTS:
        a = cli['agents'][agent]
        app = int(a['build_ok_projects'])
        passed = int(a['fully_compliant_projects'])
        failed = app - passed
        s['applicable'] += app
        s['passed'] += passed
        s['failed'] += failed
        s['by_agent'][agent] = {'applicable': app, 'passed': passed, 'failed': failed}
    # Pull failed examples from detailed project summaries if available.
    detail_path = Path('cli_interface_all_project_summaries.json')
    if detail_path.exists():
        detail = json.loads(detail_path.read_text(encoding='utf-8'))
        rows = []
        if isinstance(detail, dict):
            rows = detail.get('projects') or detail.get('rows') or []
        elif isinstance(detail, list):
            rows = detail
        for row in rows:
            agent = row.get('agent')
            repo = row.get('repo') or row.get('project') or row.get('rid')
            if agent in MAIN_AGENTS and row.get('build_ok') is True:
                full = row.get('fully_compliant')
                if full is False or full == 0:
                    if len(s['examples']) < 12:
                        s['examples'].append({'repo': repo, 'agent': agent, 'diagnostic': row})

rows = []
for key, s in stats.items():
    if s['applicable'] <= 0:
        continue
    rate = s['failed'] / s['applicable']
    rows.append({
        'metric': key,
        'dimension': s['dim'],
        'dimension_name': DIM_LABEL.get(s['dim'], s['dim']),
        'name': s['name'],
        'failed': s['failed'],
        'applicable': s['applicable'],
        'passed': s['passed'],
        'failure_rate': rate,
        'by_agent': s['by_agent'],
        'examples': s['examples'],
    })
rows.sort(key=lambda r: (r['failed'], r['failure_rate'], r['applicable']), reverse=True)

dim_stats = defaultdict(lambda: {'applicable':0,'passed':0,'failed':0})
for r in rows:
    d = dim_stats[r['dimension']]
    d['applicable'] += r['applicable']
    d['passed'] += r['passed']
    d['failed'] += r['failed']

dim_rows = []
for dim, d in dim_stats.items():
    dim_rows.append({
        'dimension': dim,
        'dimension_name': DIM_LABEL.get(dim, dim),
        **d,
        'failure_rate': d['failed']/d['applicable'] if d['applicable'] else None,
    })
dim_rows.sort(key=lambda r: (r['failure_rate'], r['failed']), reverse=True)

result = {'scope': 'main_agents_build_ok_only', 'agents': MAIN_AGENTS, 'top10_metrics': rows[:10], 'all_metrics': rows, 'dimensions': dim_rows}
OUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')

lines = []
lines.append('# RQ3 NFR Failure Top 10\n')
lines.append('口径：主测四模型 Claude Code、Codex、Cursor、Kimi Code；仅统计 `build_ok=true` 的提交；`null`/不适用指标不进分母；CLI 接口完全符合按项目二值指标并入 CMP。\n')
lines.append('## 失败最多的 NFR 指标 Top 10\n')
lines.append('| 排名 | 维度 | 指标 | 未通过/适用 | 未通过率 | Claude | Codex | Cursor | Kimi |')
lines.append('|---:|---|---|---:|---:|---:|---:|---:|---:|')
for i, r in enumerate(rows[:10], 1):
    cells = []
    for a in MAIN_AGENTS:
        ba = r['by_agent'][a]
        cells.append(f"{ba['failed']}/{ba['applicable']}")
    lines.append(f"| {i} | {r['dimension_name']} | `{r['metric']}` {r['name']} | {r['failed']}/{r['applicable']} | {r['failure_rate']:.2%} | " + ' | '.join(cells) + ' |')
lines.append('\n## 维度级失败率（同口径）\n')
lines.append('| 维度 | 未通过/适用 | 未通过率 |')
lines.append('|---|---:|---:|')
for r in dim_rows:
    lines.append(f"| {r['dimension_name']}（{r['dimension']}） | {r['failed']}/{r['applicable']} | {r['failure_rate']:.2%} |")
lines.append('\n## Top 指标样例候选\n')
for r in rows[:5]:
    lines.append(f"- `{r['metric']}` {r['name']}：" + ', '.join(f"{e.get('repo')}/{e.get('agent')}" for e in r.get('examples', [])[:5]))
OUT_MD.write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(OUT_MD.read_text(encoding='utf-8'))
