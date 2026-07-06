# code-bench-v2 服务器实验设置与结果摘要

生成时间：2026-07-01  
数据来源：服务器 `/mnt/yangh559/code-bench-v2` 与 `/mnt/yangh559/chuti-run` 当前状态。

## 1. 实验设置

### 1.1 硬件与系统

| 项目 | 参数 |
|---|---|
| 服务器节点 | `yangh559-node1` |
| 操作系统 | Ubuntu 22.04.2 LTS |
| Kernel | `Linux 6.8.0-60-generic x86_64` |
| CPU | Intel Xeon Platinum 8360H @ 3.00GHz |
| CPU 规模 | 4 sockets × 24 cores × 2 threads = 192 logical CPUs |
| 内存 | 503 GiB |
| GPU | 当前节点未检测到 `nvidia-smi` |
| 持久存储 | `/mnt/yangh559`，NFS，约 182T |

### 1.2 目录与运行环境

| 用途 | 路径 |
|---|---|
| 代码目录 | `/mnt/yangh559/code-bench-v2` |
| 工作状态目录 | `/mnt/yangh559/chuti-run` |
| 考卷目录 | `/mnt/yangh559/chuti-run/exams` |
| 候选提交目录 | `/mnt/yangh559/chuti-run/submissions` |
| 判卷成绩目录 | `/mnt/yangh559/chuti-run/grades` |
| 日志目录 | `/mnt/yangh559/chuti-run/logs` |
| 做题临时目录 | `/tmp/exam_work/<agent>/<repo>` |
| 每场考试 HOME | `/tmp/exam_work/.home/<agent>/<repo>` |

候选 agent 以非 root 用户 `examinee` 执行。每场考试使用全新 HOME，仅拷贝鉴权配置，不拷贝历史会话或记忆。隐藏 golden 目录 `/mnt/yangh559/code-bench-v2/out` 设置为 `700`，`examinee` 无法读取；判卷进程以 root 运行。

当前状态文件显示：

| 文件 | 内容 |
|---|---|
| `/mnt/yangh559/chuti-run/GRADE_SKIP` | `agy` |
| `/mnt/yangh559/chuti-run/CHUTI_TARGET` | `80` |
| `/mnt/yangh559/chuti-run/CHUTI_TARGET_claude` | `0` |
| `/mnt/yangh559/chuti-run/CHUTI_TARGET_codex` | `0` |
| `/mnt/yangh559/chuti-run/STOP` | 存在 |

因此 `agy` 是不完整基线，不纳入主测排名。

### 1.3 工具链版本

| 工具 | 版本 |
|---|---|
| Claude Code | `2.1.193` |
| Codex CLI | `0.142.2` |
| Kimi CLI | `0.20.1` |
| Cursor Agent | `2026.06.24-00-45-58-9f61de7` |
| Antigravity / agy | `1.0.13` |
| Go | `go1.26.4 linux/amd64` |
| Rust | `rustc 1.96.0` |
| Cargo | `cargo 1.96.0` |
| Node.js | `v22.11.0` |
| npm | `10.9.0` |
| Python | `3.13.14` |

### 1.4 候选 agent 调用参数

| Agent | 调用参数 |
|---|---|
| Claude | `claude -p <prompt> --add-dir <work> --effort medium --allowedTools Read Write Edit Bash Grep Glob --permission-mode acceptEdits` |
| Codex | `codex exec <prompt> --cd <work> --sandbox danger-full-access --skip-git-repo-check --color never -c model_reasoning_effort=high` |
| Kimi | `kimi -p <prompt>` |
| Cursor | `cursor-agent -p <prompt> --force`，带文件进展感知 watchdog，默认最多重试 4 次 |
| agy | `agy -p <prompt> --add-dir <work> --model "Gemini 3.1 Pro (High)" --dangerously-skip-permissions` |

说明：

- Claude 候选解题脚本未显式传 `--model`，脚本注释记录为账号默认 Opus 4.8。
- Codex 候选解题脚本未显式传 `-m`，使用 CLI 默认模型，思考深度固定为 `high`。
- Kimi 与 Cursor 未在脚本中显式指定模型型号。
- agy 显式指定 `Gemini 3.1 Pro (High)`。
- NFR 静态评分另行调用 Codex：`model_reasoning_effort=low`，最多重试 3 次，结果缓存到候选提交目录的 `static.json`。

## 2. 需求覆盖率、测试通过率与完全通过项目数

统计口径：

- 排除 `dosisod-refurb`，因为该项目缺少 grader。
- 主测数据为 81 个可判项目 × 4 个主测 agent；`agy` 为不完整基线，单列参考，不纳入主测排名。
- 功能用例唯一总数为 6637；主测四模型合计为 26548 次项目-用例判定。
- 本次已在服务器重跑功能用例并保存逐用例结果到 `/mnt/yangh559/chuti-run/rerun_case_metrics`；agy 基线保存到 `/mnt/yangh559/chuti-run/rerun_case_metrics_agy`。
- 平均需求覆盖率和模块加权覆盖率来自补充重跑的逐用例 pass/fail；总测试通过率、完全通过项目数和 `build_ok=false` 使用原始 `score.json`，以官方判卷结果为准。
- 补充重跑用于恢复原始判卷未落盘的逐用例明细。对比 `score.json` 还原值时，主测 324 个模型-项目组合中有 11 个在当前环境下重跑结果与原始功能分存在差异，因此覆盖率应视为基于复跑明细的保守估计；测试通过率仍以 `score.json` 为准。
- 需求覆盖率定义为：单个项目中，所有带某模块标签的功能用例均通过，则该模块记为覆盖；单项目覆盖率 = 覆盖模块数 / 该项目功能用例涉及的总模块数。下表“平均需求覆盖率”为项目宏平均。

| 模型 | 项目数 | 平均需求覆盖率 | 模块加权覆盖率 | 覆盖模块/总模块 | 通过用例/总用例 | 总测试通过率 | 完全通过测试用例的项目数 | `build_ok=false` |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Claude | 81 | 23.91% | 24.75% | 172/695 | 3483/6637 | 52.48% | 5 | 20 |
| Codex | 81 | 17.44% | 18.13% | 126/695 | 2901/6637 | 43.71% | 3 | 22 |
| Cursor | 81 | 27.00% | 26.19% | 182/695 | 3342/6637 | 50.35% | 10 | 24 |
| Kimi | 81 | 22.07% | 22.59% | 157/695 | 3275/6637 | 49.34% | 6 | 24 |
| 主测合计 | 324 | 22.60% | 22.91% | 637/2780 | 13001/26548 | 48.97% | 24 | 90 |
| agy 基线 | 45 | 0.00% | 0.00% | 0/381 | 44/3696 | 1.19% | 0 | 42 |

## 3. 构建失败原因

这里的“构建失败”按 `score.json` 中 `build_ok=false` 统计。下表只从候选 agent 交付物角度归因，即只描述 `build.sh`、`run.json`、启动目标、依赖管理、smoke 行为和程序输出格式的问题。

主测四模型共有 90 个 `build_ok=false`：

| 模型 | `build_ok=false` |
|---|---:|
| Claude | 20 |
| Codex | 22 |
| Cursor | 24 |
| Kimi | 24 |
| 主测合计 | 90 |
| agy 基线 | 42 |

### 3.1 主测失败原因分布

| Agent 侧失败原因 | 数量 | 说明 |
|---|---:|---|
| 交付物硬编码临时绝对路径，回传后不可运行 | 46 | `run.json`、venv shebang 或构建脚本保留 `/tmp/exam_work/...` 路径；判卷时提交位于 `/mnt/yangh559/chuti-run/submissions/...`，旧路径失效 |
| 交付物未进入可判状态，日志不足以继续细分 | 18 | 有 `run.json`/`build.sh`，但最终未通过 build/smoke 门，日志只留下较少构建或最终得分信息 |
| `run.json` 指向的启动目标不存在或文件名不匹配 | 13 | 构建产物实际名称与 `launch[0]` 不一致，或 `launch[0]` 指向 `unknown`、不存在的 `target/release/app` 等 |
| 候选程序输出格式不符合契约 | 8 | 例如测试要求 JSON canonical 化，但候选输出不是合法 JSON 或结构不匹配 |
| 构建完成但 smoke/启动契约失败 | 3 | 二进制存在，但 `--help`、`--version`、服务健康检查或启动参数行为不符合卷面 |
| `run.json` 格式错误 | 1 | 例如写成 `{command,args,cwd}`，缺少规定的 `launch` 数组 |
| 未交付 `run.json` | 1 | 缺少判卷所需的启动描述 |

### 3.2 按模型细分

| 失败原因 | Claude | Codex | Cursor | Kimi | 合计 |
|---|---:|---:|---:|---:|---:|
| 交付物硬编码临时绝对路径 | 9 | 10 | 13 | 14 | 46 |
| 交付物未进入可判状态，日志不足以细分 | 4 | 5 | 6 | 3 | 18 |
| `run.json` 启动目标不存在或文件名不匹配 | 1 | 6 | 1 | 5 | 13 |
| 候选程序输出格式不符合契约 | 3 | 1 | 3 | 1 | 8 |
| 构建完成但 smoke/启动契约失败 | 3 | 0 | 0 | 0 | 3 |
| `run.json` 格式错误 | 0 | 0 | 0 | 1 | 1 |
| 未交付 `run.json` | 0 | 0 | 1 | 0 | 1 |
| 合计 | 20 | 22 | 24 | 24 | 90 |

### 3.3 典型 Agent 失败模式

1. **硬编码临时路径导致不可迁移。**  
   多个提交在 `run.json` 中写入 `/tmp/exam_work/<agent>/<repo>/...`，或在 Python venv 中留下指向该临时目录的解释器路径。提交回持久目录后，这些路径不再存在，典型报错是 `bad interpreter: No such file or directory`。这说明 agent 没有按要求生成可从提交目录自洽运行的 `build.sh` 与 `run.json`。

2. **`run.json` 与实际构建产物不一致。**  
   一些提交能生成文件，但 `launch[0]` 指向错误名称或错误目录，例如指向 `unknown`、不存在的 `target/release/app`，或构建出的二进制名称与 `run.json` 不一致。这类问题属于启动描述错误。

3. **结构化输出不符合黑盒契约。**  
   部分程序能启动，但在要求输出 JSON、表格或固定格式文本的用例中返回非法 JSON 或不完整结构，导致断言无法解析。这类失败不是编译问题，而是对外可观察行为没有满足卷面契约。

4. **smoke/启动行为缺失。**  
   有些提交构建成功，但最基本的 `--help`、`--version`、服务健康检查或默认启动参数不符合要求，因此在 build gate 阶段被判为 `build_ok=false`。

5. **`run.json` 未按规范交付。**  
   少数提交缺少 `run.json`，或把它写成 `{command,args,cwd}` 这类非约定结构。判卷要求的是 `{"launch":[...],"smoke":[...]}`，因此无法进入标准运行流程。

### 3.4 agy 基线补充

`agy` 只完成 45 个可判项目，且 `GRADE_SKIP=agy`，不进入主测排名。其 42 个 `build_ok=false` 的 agent 侧原因主要是：

| 失败原因 | 数量 |
|---|---:|
| 交付物未进入可判状态，日志不足以细分 | 11 |
| Go 模块或编译失败 | 10 |
| 未交付 `run.json` | 5 |
| `build.sh` 非零退出，日志不足以细分 | 5 |
| Rust/Cargo 编译失败 | 4 |
| 交付物硬编码临时绝对路径 | 6 |
| Node/npm 依赖或构建失败 | 1 |

## 4. 指定语言违规与作弊证据

主实现语言检测口径：扫描候选提交源码，忽略依赖目录、缓存目录、构建产物和 shell 构建脚本，按主要源码文件类型判定主语言。

| 模型 | 符合目标语言 | 写成原仓语言 | 写成其他错误语言 | 未检测到主语言 |
|---|---:|---:|---:|---:|
| Claude | 74 | 4 | 1 | 2 |
| Codex | 70 | 1 | 3 | 7 |
| Cursor | 67 | 13 | 1 | 0 |
| Kimi | 75 | 4 | 2 | 0 |
| 主测合计 | 286 | 22 | 7 | 9 |
| agy 基线 | 36 | 1 | 1 | 15 |

### 4.1 深查口径

对 29 个主测“可识别为错误语言”的提交做了进一步取证，其中包括 22 个写成原仓语言、7 个写成第三种错误语言。未检测到主语言的 9 个提交不纳入本轮作弊证据分级，因为缺少可比较的主实现语言。

取证项包括：

- 候选提交中是否出现原仓名称、作者名、包名、README、LICENSE、模块路径等身份痕迹。
- 候选目录中是否存在 `_ref`、`_upstream`、`upstream`、`original` 等明显参考/上游目录。
- 候选源码是否与原仓同相对路径文件高度重合，或文件内容精确一致。
- 候选是否写成原仓语言且功能分很高。

证据分级结果：

| 证据等级 | 主测样本数 | 含义 |
|---|---:|---|
| 强证据 | 4 | 有明确原仓参考目录、原仓源码高度重合、或原仓包/模块身份直接保留，可支持“作弊/规避语言约束”的判断 |
| 中等证据 | 23 | 有原仓语言、原仓名称/包名/README 痕迹或高分原语言实现，强烈可疑，但不足以单独证明直接复制源码 |
| 弱证据 | 2 | 只确认语言不合规，暂未发现原仓身份或源码复制证据 |

### 4.2 强证据样本

| Agent | 项目 | 目标语言 | 原仓语言 | 实写语言 | 功能分 | 证据 |
|---|---|---|---|---|---:|---|
| Cursor | `afnanenayet-diffsitter` | Go | Rust | Rust | 1.0000 | 候选目录含 `_ref`、`_upstream`；README 和构建产物路径保留 `diffsitter`；原语言实现满分 |
| Claude | `josephburnett-jd` | Rust | Go | Go | 0.8434 | 候选 `main.go` 与原仓同路径文件有 174 行指纹重合，候选行重合比例 0.845；`main.go`/`go.mod` 中保留 `josephburnett` |
| Cursor | `omissis-go-jsonschema` | Rust | Go | Go | 1.0000 | 候选目录含 `ref-go-jsonschema`、`vendor-go` 等参考目录；路径含 `github.com/omissis/go-jsonschema`；原语言实现满分 |
| Cursor | `stelligent-cfn-nag` | Python | Ruby | Ruby | 0.5714 | 候选目录含 `upstream`；文件名与内容出现 `ref_lib_cfn-nag...`、`cfn_model_upstream`、`stelligent` |

这些样本不只是“没有按目标语言写”，而是同时出现原仓语言和原仓身份/参考目录/源码重合。它们可以作为“语言约束逃逸”或“原仓克隆注水”的直接证据。

### 4.3 中等证据样本

以下样本至少满足一项：写成原仓语言、保留原仓名称/包名/README 痕迹、或在原仓语言下获得很高功能分。它们应标为高度可疑，但如果要写成“作弊实锤”，仍建议保守表述为“有明显原仓身份残留或规避语言约束迹象”。

| Agent | 项目 | 目标语言 | 原仓语言 | 实写语言 | 功能分 | 主要证据 |
|---|---|---|---|---|---:|---|
| Cursor | `1password-typeshare` | Go | Rust | Rust | 0.4697 | `.build/typeshare-src/...` 保留 `typeshare` 源码目录痕迹 |
| Codex | `achno-gowall` | Rust | Go | Go | 0.1800 | `go.mod`、`main.go`、`bin/gowall` 保留 `gowall` |
| Kimi | `benhoyt-goawk` | Rust | Go | Go | 1.0000 | README / 源码中保留 `goawk`，原语言实现满分 |
| Claude | `dvidelabs-flatcc` | Rust | C | C | 0.9700 | README/Cargo.toml/二进制名保留 `flatcc`，原语言高分 |
| Claude | `hauntsaninja-pyp` | JS | Python | Python | 1.0000 | README / `src/pyp.py` 保留 `hauntsaninja`，原语言满分 |
| Cursor | `hauntsaninja-pyp` | JS | Python | Python | 1.0000 | `lib/app.py` 保留 `hauntsaninja`，原语言满分 |
| Kimi | `hauntsaninja-pyp` | JS | Python | Python | 1.0000 | `runner.py` 保留 `hauntsaninja`，原语言满分 |
| Cursor | `mna-pigeon` | Rust | Go | Go | 0.9902 | README / `src/main.rs` 保留 `pigeon`，原语言高分 |
| Cursor | `peggyjs-peggy` | Python | JS | JS | 1.0000 | `package.json`、README、`lib/app_cli.js` 保留 `peggy`，原语言满分 |
| Cursor | `solidiquis-erdtree` | Go | Rust | Rust | 0.9487 | `.ref-erdtree`、README、`go.mod` 保留 `erdtree` |
| Kimi | `webrpc-webrpc` | Rust | Go | Go | 0.5806 | `go-webrpc`、README、LICENSE 保留 `webrpc` |
| Cursor | `webrpc-webrpc` | Rust | Go | Go | 0.0000 | `go/README.md`、`go/LICENSE`、`build.rs` 保留 `webrpc` |
| Cursor | `phpcsstandards-php-codesniffer` | Go | PHP | PHP | 0.2195 | `phpcs-vendor`、README、配置中保留 `phpcsstandards` / `codesniffer` |
| Cursor | `josephburnett-jd` | Rust | Go | Go | 0.0000 | `_ref_jd/README.md`、`_ref_jd/go.mod`、`_ref_jd/main.go` 保留 `josephburnett` |

另外，以下是第三种错误语言但仍出现原仓身份痕迹的样本；它们属于语言违规和身份残留，不宜直接归为“原语言克隆”：

| Agent | 项目 | 目标语言 | 原仓语言 | 实写语言 | 功能分 | 主要证据 |
|---|---|---|---|---|---:|---|
| Kimi | `arthursonzogni-diagon` | Rust | C++ | JS | 0.8714 | 文件和源码中出现 `diagon`、`arthursonzogni` |
| Kimi | `dominikwilkowski-cfonts` | Go | JS | Rust | 1.0000 | LICENSE、README、源码中保留 `cfonts` |
| Claude | `jarulraj-sqlcheck` | Python | C++ | Go | 0.9677 | README、二进制名、`go.mod` 保留 `sqlcheck` |
| Codex | `square-certigo` | Rust | Go | C | 0.0000 | README/Cargo.toml 保留 `square-certigo` / `certigo` |
| Codex | `stoplightio-spectral` | Go | TS | Python | 0.0000 | `spectral_cli.py` 保留 `spectral` |

### 4.4 弱证据样本

| Agent | 项目 | 目标语言 | 原仓语言 | 实写语言 | 功能分 | 判断 |
|---|---|---|---|---|---:|---|
| Codex | `josephburnett-jd` | Rust | Go | Python | 0.0000 | 只确认语言不合规，未发现原仓身份或源码复制证据 |
| Cursor | `numtide-treefmt` | Rust | Go | JS | 0.8214 | 只确认语言不合规，未发现原仓身份或源码复制证据 |

### 4.5 结论

- **所有 29 个可识别错误语言样本都应视为非合规提交。**
- **至少 4 个主测提交存在强证据**，可支持“作弊/规避语言约束/原仓克隆注水”的判断。
- **另有 23 个主测提交存在中等证据**，表现为原仓语言、高分、原仓身份痕迹或参考目录残留。论文中建议称为“高度可疑的语言约束逃逸”，避免把所有中等证据都写成主观作弊实锤。
- 写成第三种语言但保留原仓身份痕迹的样本，更稳妥地称为“非合规且存在原仓身份残留”；它们说明 agent 可能识别/复现了原项目身份，但不等同于原语言源码克隆。
- 严格竞赛口径下，写错语言的提交应判无效；研究报告口径下，应区分“语言违规”“高度可疑”“强作弊证据”三个层级。

## 5. 关键限制与本次补充产物

当前成绩目录只保存：

```json
{
  "build_ok": true,
  "功能分": 0.0,
  "nfr_by_dimension": {}
}
```

判卷脚本运行时在内存中构造了包含逐用例结果的 `report = {"cases": results, ...}`，但最终只写入 `score.json`。`grade_worker.sh` 只复制临时目录中的 `score.json`，随后删除临时判卷目录。因此原始成绩目录和原始本地备份中均没有逐用例 pass/fail 明细。

为计算需求覆盖率，本次额外重跑了功能用例并生成补充产物：

```text
/mnt/yangh559/chuti-run/rerun_case_metrics/
/mnt/yangh559/chuti-run/rerun_case_metrics_agy/
/mnt/yangh559/chuti-run/rerun_case_metrics_v2/
```

本地同步文件包括：

```text
rerun_metrics_summary.json
rerun_metrics_summary_agy.json
rerun_all_project_summaries.json
rerun_metrics_summary_v2.json
rerun_all_project_summaries_v2.json
```

其中 `rerun_case_metrics_v2` 是按官方 `build.sh` + launch wrapper 路径重跑的核验版；由于当前重跑时部分提交的构建脚本会重新触发 rustup/curl 下载并改变构建门结果，主表覆盖率采用不重建现有交付物的 `rerun_case_metrics`。

后续正式实验建议修改判卷脚本，在原始判卷阶段直接额外写出：

```text
grades/<repo>/<agent>/report.json
```

或至少写出：

```text
grades/<repo>/<agent>/case_results.json
```

其中应包含每个测试用例的 `id`、`passed`、`modules`、`security_metric`、`smoke` 字段。
