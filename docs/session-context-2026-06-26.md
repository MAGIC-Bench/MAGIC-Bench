# code-bench-v2 会话上下文导出
> 导出时间: 2026-06-26

---

## 一、项目目标

`D:\code-bench-v2` 是一个**自动化考试生成框架**，将真实开源仓库转换为"项目级代码生成"黑盒考试：

- 生成测试输入，跑原仓得到 golden 输出，打包去标识化考生卷面 + 隐藏评分器
- **差分 golden oracle**：原仓跑两次，仅在两次一致时冻结（双跑确定性）
- 以后全部工作只在 `D:\code-bench-v2` 下进行

---

## 二、Stage 0–8 流水线

| Stage | 说明 |
|-------|------|
| 0 | 摄入 + 容器化（Docker build，build-repair 循环） |
| 1 | 仓库理解（01_repo-model.json），生成 `candidate_brief` |
| 2 | 合约文档（02_*-contract.json，CLI/OpenAPI/IO 三种场景） |
| 3 | 模块拆分 + 用户故事（03_modules.json / 03_user-stories.json） |
| 4 | NFR 探针（04_nfr-probes.json） |
| 5 | 测试生成循环（05_tests/*.json，golden 冻结，quota=20） |
| 6 | 对抗性审查 → 返修 → 复审循环（最多 max_repairs=5 轮） |
| 7 | 高水位验证（stage7_verify，drop > 5% 丢废） |
| 8 | 打包出厂（07_exam/candidate/ + grader） |

---

## 三、关键文件清单与核心改动

### `engine/classify.py`
- `check()` 整体包 `try/except`：非法 rule → `ok=False`（不崩溃）
- `freeze_golden()` / `inv_check()` / `norm_apply()` 保持原逻辑
- 修复动机：jd 的 `rfc6902_transforms:before.json:after.json` 导致 stage7 `ValueError` 整仓崩溃

### `orchestrate.py`
- `_VALID_NORM` / `_VALID_INV` 合法规则常量集
- `_malformed_findings(repo_out)`: 机械扫描 05_tests，返回含非法 class/rule 的合成 critical findings
- `_run_stage6(repo_src, repo_out, config, agent_mode)`: 完整 **review → repair → scoped-re-review** 循环
  - `max_repairs=5`（可配）
  - `_malformed_findings` 的结果叠加进 `oc`（open_critical）
  - 精准返修：若 critical findings 都有具体 test_id → `focus_ids` 只复审那几个 case（节省 token）
  - 若 finding 是 `suite:` / `ALL` 范式 → 退化为全量复审

### `agent/agent_stages.py`
- `adversarial_review(repo_dir, repo_out, config, mode, focus_ids=None)`:
  - `focus_ids=None` → 完整审查所有 case
  - `focus_ids=[...]` → SCOPED RE-REVIEW 注入提示词，只审那几个 case
- `repair_stage6(repo_dir, repo_out, config, mode, findings)`:
  - 仅处理 `severity == "critical"` 的 findings
  - 提示词替换 `{findings}` → JSON

### `agent/client.py`
- `CODEX_REASONING_EFFORT = "medium"` （从 `"high"` 改为加速，每轮 ~45s vs 原来 2–3 min）

### `engine/gates.py`
- `_content_coverage_ratio()`: 共享 helper，统计有 content 字段值检查的 case 比例
  - 计入：`exact` / `normalized` 或 `invariant: regex:/eq_int:/valid_json`
  - 不计入：`ignored`、只有 exit 断言
- `gate_stage5`: 使用 `_content_coverage_ratio()` ≥ 50%
- `gate_stage6`: `open_critical == 0` **AND** `_content_coverage_ratio()` ≥ 50%（反作弊）
- `GATES = {1, 3, 5, 6, 7}`（stage6 正式成为硬门槛）

### `engine/deident.py`
- `identity_tokens(repo_id, binary=None)`: 提取辨识 token（binary 强制包含；过滤 yaml/json/http 等通用词）
- `scrub_text(text, toks)`: 子串、大小写无关替换 → `GENERIC="app"`；处理 camelCase 复合词
- `leak_tokens(text, toks)`: 单词边界检查（gate_stage1 反泄题）

### `stages/stage8_package.py`
- 统一考生包：`07_exam/candidate/` 8 文件
  - 项目描述.md / 用户API使用手册.md / 功能模块文档.md / 用户行为示例文档.md
  - 非功能需求.md / 02_*-contract.json / generation_language.txt / prompt.md
- `_scrub_contract()`: 用 `deident.scrub_text()` 抹合约文档中的 VALUES（不动结构键）
- 所有考生文档均经过去标识化

### `stages/stage5_loop.py`
- `argv[0] == prog_name` 守卫：丢弃程序名作为第一 argv 的 draft → `dropped_argv_binary`
- `dropped_timeout`：exit 124 / timed_out 的 golden 不冻结
- Coverage ledger 中报告 `dropped_argv_binary`

### `prompts/stage5_gen.md`
- HARD RULES 新增：
  - 禁止内部 API / 插件特性（只能黑盒）
  - 禁止白盒模式（debug/AST-dump、`StrExpr(...)` 等）
  - exit 断言用 `invariant:eq_int:<n>`（不用 exact），使原仓违约时 `freeze_golden` 自动丢弃
  - ARGV 排除程序名
  - DON'T FREEZE CONTRACT-VIOLATING ORIGINAL

### `prompts/stage6_adversarial.md`
- 新增 `{focus}` 占位符（精准复审注入）
- Critical findings 强判准则：程序名/banner、内部符号、golden 矛盾合约、argv 含程序名、白盒泄露

### `prompts/stage6_repair.md` *(新文件)*
- 返修指令 + VALID ASSERTION GRAMMAR ONLY 白名单：
  ```
  normalized rule ∈ {crlf_lf, strip, rstrip_eol, lines_sorted, json_canonical, regex_extract:<re>}
  invariant  rule ∈ {nonempty, empty, valid_json, regex:<re>, eq_int:<n>}
  ```
- 场景覆盖：过度约束 → regex；golden 矛盾合约 → DELETE；程序名在 argv → DELETE；
  白盒泄露 → regex 公开部分或 ignored；固有白盒特性 → DELETE；无稳定核心 → DELETE
- 反作弊条款：不得全 ignored（≥50% case 须保留内容值检查）

### `scripts/launch-validate-v3.sh`
- 智能续跑（②）：stage5 已完成 → 从 stage6 续跑（跳过重新生成 golden）；stage5 未完 → 从 stage5
- `--jobs 2`（两仓并行）

### `scripts/watch-v3.sh`
- 实时仪表盘：per-repo 进度条、`open_crit=N`、`rep=N`（返修轮数）、`argv_drop=N`

### 安全性测试用例(req 2.7)+ 冒烟测试交付物(req 2.8) — 2026-06-26 新增
- **`engine/nfr_security.py`(新)**：`pick_security_metrics(repo_out)` 从 04_nfr-probes.json 的
  `implemented[]` ∩ metrics-table.json,按关键词(未授权/越权/恶意输入/注入/抗篡改/穿越)筛出
  3 类可测安全指标(unauthorized_access/unauthorized_modify/malicious_input)。对两套指标命名(SEC-1/5/6
  与 SEC1/4/5)都鲁棒。
- **`prompts/stage4_nfr.md`**：新增"安全指标强制显式判定"块,要求 agent 明确判定这 3 类指标是否
  已实现(解析型工具默认实现恶意输入抗篡改)。修复了 jd/sq 标 SEC-6 但 bee-san/refurb 不标的不一致。
- **`prompts/stage5_gen.md`**：新增 SECURITY TEST CASES 段(用 `{sec_metrics}` 注入);draft schema 加
  可选 `security_metric`。每个已实现安全指标 ≥3 条带标注的黑盒安全用例(越权/恶意输入→安全拒绝/不崩溃,
  双跑冻结,原仓自己崩则丢弃)。
- **`agent/agent_stages.py`**：`draft_provider` 调 `nfr_security.pick_security_metrics` 注入 `{sec_metrics}`。
- **`stages/stage5_loop.py`**：`_testcase` 透传 `security_metric`/`smoke`;`_smoke_invocations` +
  `_freeze_smoke` 生成 `05_smoke/*.json`(配置 smoke + --help/--version/-h,双跑冻结,exit==观测 + 非空);
  summary 加 `security_tests`/`security_by_metric`/`smoke_tests`。
- **`engine/pytest_emit.py`**：`emit()` 把 05_tests + 05_smoke 拷进 grader/cases,产
  `test_blackbox.py`(过滤掉 smoke)+ `test_smoke.py`(只选 smoke);conftest 报告安全 NFR 通过率 + 跳过
  SMOKE 模块;`emit()` 返回 `{n_tests,n_smoke,n_security,security_by_metric}`。
- **`stages/stage8_package.py`**：消费 emit dict;`_nfr_md(nfr, security)` 加"安全性专项测试"段;
  package.json 加 security_tests/smoke_tests。
- **`schemas/testcase.schema.json`**：加 `security_metric`/`smoke`/`kind:"smoke"`。
- **自检**：`scripts/test_sec_smoke.py`(24 项全绿)+ `scripts/smoke_v2.py`(38 项全绿)。
- 各仓安全拾取现状:sq→SEC-6,ogen→SEC-1/5/6,jd→SEC-6,bee-san/refurb→需重跑 stage4(新判定)。
- **对抗复核(9-agent workflow)修复**:
  - (major) `gates._content_coverage_ratio` 排除 security_metric/smoke 用例出分母 —— 安全用例多为
    exit-only,否则会假性拖垮 ≥50% 内容门槛。
  - (major) 冒烟改为场景感知(cli argv / service 健康 GET / pipeline 空输入),全量 121 仓的 22 个
    service 仓也有冒烟了。
  - (minor) prompt 去掉"断言无文件副作用"(语法不可表达,改为沙箱保证 + exit/marker 可判信号);
    冒烟不再对 --help/--version 钉死精确退出码(仅原仓成功时钉 exit 0,跨实现公平);去 U+0385;
    `pick_security_metrics` 加 list 类型守卫;obs2 二跑超时守卫。
  - 自检:`scripts/test_sec_smoke.py` 升到 31 项全绿。

### sq 卡 stage6 诊断(2026-06-26)
- **非代码 bug**:sq 是**有状态/会话式**工具(持久 source 注册表 + config/cache 跨调用)。stage5 生成的
  数据操作用例引用了"前一条命令注册的 @source",但 harness 每次重置状态 → stage7 复跑 90% 不复现被丢 →
  只剩 2 条无状态错误路径(exit 2 + ignored)→ 内容覆盖 0% → 反作弊门槛正确拦截。
- **本质**:sq 不适配单调用 CLI 黑盒模型(更像有状态 service)。框架是**正确地**判其为不合格考卷。
- **已做(不重跑)**:stage5_gen.md 加"有状态 CLI"硬规则 —— 优先无状态一次性调用(stdin/inline 输入、
  确定性转换、json_canonical/lines_sorted),禁止依赖前序调用建立的注册表/配置/缓存。
- **待办(重跑时二选一)**:① 用新规则重跑 sq stage5+(大概率出更稳的无状态卷面);② 换一个
  database_storage 候选仓(若 sq 仍边缘)。

### `dataset/repo-list.manifest.json`
- 121 仓，5 场景，从 `benchmark_screening_report.html` 的 `const DATA.candidates` 解析

### `dataset/pilot-v3.manifest.json`
- 5 仓（每场景 1 个）：
  - `dosisod-refurb` (py, cli_tool)
  - `josephburnett-jd` (go, serialization_format)
  - `ogen-go-ogen` (go, web_api)
  - `bee-san-name-that-hash` (py, cryptography_security)
  - `neilotoole-sq` (go, database_storage)

---

## 四、修复的 Bug 记录

| Bug | 原因 | 修复 |
|-----|------|------|
| jd stage7 `ValueError: unknown invariant rule: rfc6902_transforms:...` | repair agent 编造了不存在的规则关键字 | `classify.py` try/except；`_malformed_findings` 机械抓取；`stage6_repair.md` 白名单 |
| refurb `StrExpr(.pdf)` open_critical=1 不收敛 | Mypy 内部 AST 类名固有白盒，无稳定黑盒核心 | `stage6_repair.md` 新增 "NO STABLE CORE → DELETE" + "INHERENTLY WHITE-BOX FEATURE → DELETE" |
| stage6 每轮全量复审太贵 | 已清案例被重复审查 | `adversarial_review(focus_ids=...)` 精准复审 |
| jobs=1 太慢 | 单仓串行 | stage5 完成后改 `--jobs 2` 并行 |
| codex `high` reasoning 慢 | 每轮 2–3 min | 改 `medium`，~45s/轮 |
| `bee-san-name-that-hash` stage0 失败 | TLS 握手超时（`python:3.9-slim`） | 待重试 |
| `neilotoole-sq` stage0 失败 | 720s build 超时 | 待重试 |

---

## 五、当前运行状态（2026-06-26）

- **PID 272803**：`run_dataset.py` 后台跑，两仓从 stage6 续跑
  - `dosisod-refurb`：stage5 已完，stage6 返修循环中（StrExpr 问题，max_repairs=5）
  - `josephburnett-jd`：stage5 已完，stage6 将抓到 3 条 `rfc6902_transforms:` 合成 critical → 返修
- 监听：`bash scripts/watch-v3.sh` 或 `tail -f scripts/pilot-v3.log`

---

## 六、待办事项

- [ ] 等 refurb + jd 通过 stage6→7→8，确认 `[DONE]`
- [ ] 重试另外 3 个 pilot 仓（ogen, name-that-hash, sq）
  - `bee-san-name-that-hash`：TLS timeout，需代理或换基础镜像
  - `neilotoole-sq`：build timeout，可能需要 `--timeout 1200`
  - `ogen-go-ogen`：未跑过，直接启动
- [ ] 全量 121 仓 `repo-list.manifest.json` 批量跑（pilot 验证通过后）

---

## 七、常用命令

```bash
# 续跑 pilot-v3（jd + refurb）
cd /mnt/d/code-bench-v2 && bash scripts/launch-validate-v3.sh

# 监听
bash scripts/watch-v3.sh
tail -f scripts/pilot-v3.log

# 跑单仓（从 stage0）
python3 run_dataset.py --manifest dataset/pilot-v3.manifest.json \
  --agent codex --only josephburnett-jd --from 0 --to 8

# 单仓从 stage6 续跑
python3 run_dataset.py --manifest dataset/pilot-v3.manifest.json \
  --agent codex --only dosisod-refurb --from 6 --to 8

# 查看 stage6 结果
cat out/josephburnett-jd/06_adversarial.json | python3 -m json.tool
```

---

## 八、架构约束备忘

- **考生包**: `07_exam/candidate/` 是唯一卷面，`candidate.py:assemble_spec` 只是拷贝它
- **去标识化**: 所有考生文档须经 `deident.scrub_text()`，camelCase 复合词也处理
- **反作弊**: `_content_coverage_ratio()` ≥ 50%，gate_stage5 和 gate_stage6 均检查
- **合法断言**: 只允许白名单规则，repair 提示词和 `_malformed_findings` 双重保障
- **网络隔离**: build 阶段联网 warm-up，run 阶段断网 hermetic（`--network none`）
- **并发上限**: jobs=2（防 OOM，历史教训：jobs=3 时 Go build 并发 OOM）
