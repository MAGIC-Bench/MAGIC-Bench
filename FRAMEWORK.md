# code-bench — 出卷自动化框架（设计与维护文档）

> **维护约定**：本文档与代码**同步维护**。任何对引擎/流水线/manifest 结构/策略的改动,都要在本文档对应章节同步更新,保持文档与代码对齐。文末 §12 有"文档↔代码对齐表"。
> README.md = 快速上手;本文 = 权威设计参考。

---

## 1. 这是什么
把一个真实仓库**自动反向出成一张黑盒考卷**,用来评测"agent 的项目级代码生成能力"。
- 给候选的**题面**:对外契约 + 功能模块 + 用户故事 + 非功能需求(NFR)。
- 隐藏的**判卷集**:黑盒测试,其断言(golden)**冻结自原仓的真实输出**(差分 oracle)。
范围:非库类的 `cli` / `service` / `pipeline`,候选跨语言,只在进程/网络边界判卷。**零仓库逻辑硬编码**——每仓的事实写在 manifest,每仓的创造性工作由出题 agent(codex/claude)在运行时产出。

## 2. 三段架构 A → B → C
| 段 | 名称 | 输入→输出 | SUT(被测) | 入口 | 状态 |
|---|---|---|---|---|---|
| **A** | 出题 | 原仓 → 题面 + 判卷集 | 原仓 | `chuti.py` / `run_dataset.py` / `orchestrate.py` | ✅ 已建 |
| **B** | 答题(考生) | 题面 → 候选 agent 生成项目 | 候选码 | `run_candidate.py` + `agent/candidate.py` | ✅ 已建(未实跑) |
| **C** | 判卷 | 候选码 + 判卷集 → 分数 | 候选码 | `engine/grade.py`(接在 B 里) | ✅ 已建(未实跑) |

## 3. 核心原则
- **差分 oracle**:出题 agent **从不预测期望值**;它只写"输入序列",由引擎把输入喂给跑在容器里的原仓、捕获 contract 可观测输出 = golden(归一化后冻结)。
- **双跑定性**:每条输入在原仓**跑两次**,仅当两次输出在断言分类下一致(`classify.agrees`)才冻结 golden;不一致的输入丢弃(`dropped_nondeterministic`)——把非确定项挡在卷外,取代旧的"断网 hermetic"。
- **断言分类**:`exact` / `normalized(rule)` / `invariant(rule)` / `ignored`——跨实现公平的命脉(版本号、时间戳、顺序、错误文案等不能判 exact)。
- **★逐用例状态清空(§8)**:原仓**每跑完一个测试用例就清空全部状态**(DB 数据、缓存),防止污染下一个用例。**判卷时对候选采取同一策略**。
- **≥20/模块配额**:每个功能模块至少 20 条测试;一个测试可带多个模块标签(merge-on-collision);凑不够标 `needs_review`(质量门 > 配额,不塞 filler)。
- **联网构建 + 双跑定性(取代旧"断网 hermetic")**:`docker build` 期联网(国内镜像源 + warm-up 首跑下载);`run`/判卷期**也联网**,确定性改由"原仓双跑一致"(§3 差分 oracle)保证,不再 `--network none`。
- **跨语言公平**:NFR 优先能力门/不变量,绝对竞速只报不排名。

## 4. 出题流水线 Stage 0–7
| Stage | 干啥 | 要 Docker? | 实现 |
|---|---|---|---|
| 0 ingest | clone;**docker 模式:agent 给任意仓写 `Dockerfile.codebench`+`00_runtime.json`→build→离线 smoke**(构建失败的仓在此出局);local 模式:跑自带测试+`-cover` 二进制 | ✅ | `stages/stage0_ingest.py` + `prompts/stage0_build.md` |
| 1 comprehension | agent 读源码 → `01_repo-model.json`(含 external_deps 分类) | ❌ | `prompts/stage1` |
| 2 contract | OpenAPI / cli / io 契约 | ❌ | `prompts/stage2` |
| 3 modules+stories | 功能模块 + 带可执行代码的用户故事 | ❌ | `prompts/stage3` |
| 4 NFR | **读用户 NFR 清单 `metrics-table.json` 逐条判可测**(运行时黑盒 ∨ 源码静态)→ 探针 | ❌ | `prompts/stage4_nfr.md` |
| 5 测试闭环 | 差分 oracle + fill_quota(≥20/模块)+ 覆盖率;**v2:丢弃 124/超时 golden(环境产物)** | ✅ | `stages/stage5_loop.py` (+ `engine/cli_gen.py` 离线 stub) |
| 6 对抗验卷 | break-the-exam(过约束/误冻/白盒泄漏) | ❌ | `prompts/stage6` |
| 7 验卷 | high-water(原仓≈100%);**v2:原仓自己挂的用例=坏 golden→移入 `05_tests_dropped/` 重算,`gate_stage7` 在 drop-rate>5% 时判废(防 cisco 0.89 误发)。mutation 已删(go 专属、跨语言无法对齐)** | ✅ | `stages/stage7_verify.py` |
每 Stage:schema + 业务门(`engine/gates.py`)→ `STATUS.json` 断点续跑;Stage 6/7 初期人工。

**v2 卷面/公平修订**(`D:\code-bench-v2`,2026-06-25):① `gate_stage5` 要求 ≥50% 用例对内容字段(stdout/stderr/file)做 exact/normalized——仅查 exit 太弱;② `stage5_gen.md` 增硬规则:解析器报错措辞/版本串/宿主环境值(用户名/wifi/音量…)→ ignored/invariant,禁 exact;③ 考生包仅给 `rewritable_languages[0]` 作要求语言,不泄露原仓 `language`;④ 功能清单去 M-id、用户故事去 modules 标签(模块组织交给考生);⑤ codex 批量用 `--full-auto`。

**v2 严格对齐修订**(2026-06-25,承接需求规格逐条):
- **统一考生包**:`stage8` 的 `07_exam/candidate/` 是**唯一**卷面定义(8 文件);`agent/candidate.py:assemble_spec` 改为拷贝它(不再自建第二套 SPEC)。卷面=`项目描述.md`(去标识业务描述)+`用户API使用手册.md`(由脱敏契约渲染)+`功能清单`+`用户行为示例`+`非功能需求.md`+脱敏 `02_*`+`generation_language.txt`+`prompt.md`。
- **去标识**(`engine/deident.py` 单一真相):`identity_tokens`(binary+repo/owner 名,去通用域词)+`scrub_text`(子串、大小写不敏、含 camelCase)。`gate_stage1` 用 `leak_tokens` 拦 `candidate_brief` 里的仓库名(含 jq/bat 短名);`stage8` 把 token 从**每个**卷面文档(契约+功能清单+用户故事+手册+NFR)里抹掉(契约只抹值不抹结构键=接口);`stage1` 新增必填 `candidate_brief`(禁实现/架构/语言/仓库名)。
- **NFR (a)/(b)**:`stage4_nfr.md` 要求同时产出"原仓已实现"与"原仓未做但应做"(`origin` 必填 + `added_requirements[]`)。
- **判卷全场景**:`pytest_emit` 的 emitted conftest 含 `Cli/Service/Pipeline SUT`,按 `_grader_meta.json` 选(service 自带 `deps.py`);`stage8` 把 runtime 传给 `emit`。
- **模块/故事强约束**:`modules.schema` 把 `user_value` 设必填、新增 `user-stories.schema`,`gate_stage3` 兜底校验;`gate_stage5` 经 `business_gate(config)` 用配置 quota(不再硬编码 20)。
- **爬取原仓自带测试**:`stage5_gen.md` 要 agent 读 `{repo_dir}` 测试目录、只取输入不取期望;`draft_provider` 加 `Grep/Glob`。
- 自检:`scripts/smoke_v2.py`(导入+接线+整套 stage8 渲染+泄漏断言,全绿)。

## 5. 引擎模块清单
| 文件 | 职责 |
|---|---|
| `engine/runner.py` | `LocalRunner`(字节精确 subprocess)/ `DockerRunner`(`--rm` 联网一次性容器,**以宿主 uid 跑** `_docker_user_args` 防 root 文件) |
| `engine/dockermirror.py` | **build 前改写 Dockerfile `FROM`**:Docker Hub 被墙→官方/用户镜像改走 `docker.m.daocloud.io`(多阶段 `AS` 名/他 registry/`scratch` 不动) |
| `engine/harness.py` | 按 runtime 选 Local/Docker runner + cli/service/pipeline backend |
| `engine/replay.py` | 场景后端:`CliBackend`(实测) · `ServiceBackend`(deps+逐用例reset,见§8) · `PipelineBackend` |
| `engine/deps.py` | **外部依赖**:DB/缓存 sidecar 起停 + **逐用例 reset**(§8) |
| `engine/classify.py` | 断言分类 freeze_golden / check(支持 cli `exit/stdout/stderr/file:` 与 service `http:N:status\|body\|header`) |
| `engine/coverage.py`+`gocover.py` | 覆盖率:go(covdata)/ lcov / coveragepy / none |
| `engine/grade.py` | 判卷:`grade_suite`(任意场景)/ `score`(每模块归一化通过率)——mutation 与候选打分双用 |
| `engine/gates.py` | schema 校验 + 各 Stage 业务门(stage1 场景类型 / stage3 无孤儿 op / stage5 ≥20) |
| `engine/cli_gen.py` | 离线等价类输入生成器(`--agent stub` 用;生产由 agent 生成) |
| `engine/record_replay.py` | URL 输入的 mock 上游录制/重放 |
| `engine/config.py` | manifest → 规范化 config(语言 preset) |
| `agent/client.py` | 无头 agent 调用:`claude -p` / `codex exec`(`run_headless(...,engine=)`) |
| `agent/agent_stages.py` | 各模型 Stage 的 stub\|claude\|codex 提供者 |
| `agent/candidate.py` | B 段:驱动候选 agent 生成项目 + build cand-image |

## 6. 数据集 manifest（`dataset/manifest.json`）
每仓一条;省略字段由语言 preset(`engine/config.py`)补全。关键字段:
`id` · `scenario`(你的 5 个标签)· `scenario_type`(cli\|service\|pipeline)· `language` · `source`(git/path)· `runtime`{mode,dockerfile,cover{go\|lcov\|coveragepy\|none}} · `service`{port,health,env} · `pipeline`{in,out,cmd} · **`dependencies`**(§8)· `quota`。schema:`dataset/manifest.schema.json`。

## 7. 运行方式
```bash
# A 出题(默认 8 仓并行;codex/claude/stub 三选一)
python3 run_dataset.py --manifest dataset/manifest.json --agent codex --jobs 8
python3 chuti.py --repo <id> --agent codex            # 单仓
python3 orchestrate.py --repo <id> --from 1 --to 1    # 单仓单阶段

# B+C 判卷一个候选
python3 run_candidate.py --repo <id> --candidate-engine codex --candidate-id c1
```
**并行**:仓库级,`--jobs N`(默认 8)用 ThreadPoolExecutor;活儿全是 subprocess(docker/codex/go),GIL 在子进程期间释放,线程真并行。**注意**:单仓内部 stages 串行、Stage 5 测试串行(测试级并行是待办);codex 受 ChatGPT 订阅速率封顶,堆 `--jobs` 到一定程度对 agent 阶段不再提速。

## 8. ★外部依赖 与 逐用例状态清空（本轮新增）
**外部依赖只两类**:数据库(`postgres`/`mysql`/`mongodb`)、缓存(`redis`/`memcached`)。运行时配置(`service`/`pipeline`/`dependencies`)由 agent 在 Stage 0 写进 `00_runtime.json`,`orchestrate._merge_runtime` 合并进 config。**agent-built docker 镜像未插桩 → `coverage='none'`**(Stage 5 靠模块配额填,不靠覆盖率提示)。
- **构建期不需要**连 DB/缓存(`docker build` 只编译);**运行期**才需要。
- 在 manifest 的 `dependencies` 声明,例如:
  ```json
  "dependencies": [
    {"kind":"postgres","env":"DATABASE_URL","db_name":"appdb"},
    {"kind":"redis","env":"REDIS_URL"}
  ]
  ```
- **运行时**(出题 Stage 5 冻 golden + 判卷):`engine/deps.py` 把 DB/缓存作为 **sidecar 容器**起在一个共享 docker 网络上,SUT 通过 `env` 指定的环境变量(`DATABASE_URL`/`REDIS_URL`)连接。
- **逐用例状态清空(策略)**:`ServiceBackend` 把 deps + SUT **只起一次**(session),在**每个测试用例之前** `deps.reset()` 清空全部状态,防止污染下一个用例。**判卷对候选采用同一策略**(同一份 deps 起停 + reset)。
  - reset 机制:postgres = `TRUNCATE` 所有表(保留 schema 与 SUT 连接,快);mysql = 同理;redis = `FLUSHALL`;memcached = `flush_all`。
  - cli:本就隔离(每次调用 = 全新进程/容器),无需额外 reset。
  - pipeline:每次 run = 全新容器;若也用 DB,复用同一 deps 层(扩展点)。
  - 覆盖率注意:service 是长驻进程,Go 覆盖率在 SUT **停止(teardown)时**才 flush,所以 service 覆盖率是 session 末尾汇总,轮内 climb 不可用(回退到模块配额驱动)。
- **写进卷子**:外部依赖会进 `01_repo-model.json` 的 `external_deps`,并在候选提示中声明——候选不自己选 DB,而是由 harness 提供同样的 DB/缓存,候选按 `env` 连接;候选也被告知"用例间状态会被清空"。

## 9. 评分（C 段）
`run_gate`(候选镜像能起 + 联网 smoke 通过)· `functional`(每模块内归一化通过率 → 跨模块均值)· `nfr`(逐探针)· 报告**向量** `{run, func, per_module[], nfr[], na[]}`,leaderboard 再压标量。产物:`candidates/<repo>/<cid>/report.json`。

## 10. 运行环境（当前）
宿主 Windows;实际在 **WSL(Ubuntu, mirrored 网络)** 里跑:`python3`(无需 pip,引擎全标准库;jsonschema 可选)、`docker`(systemd 自启,用户在 docker 组)、`codex`(ChatGPT 登录;**OpenAI 被 GFW,必须开 TUN VPN + mirrored 网络**)。代码在 `/mnt/d/code-bench`。详见 memory `chuti-automation-design`。

## 11. 已实现 vs 待办
**已实现**:A 段 Stage 0–7(cli/go 路径实测:差分 oracle/覆盖率/≥20 配额/mutation 75% kill-rate)· B+C 段代码(`run_candidate`,未实跑)· 多语言/Docker/service-pipeline 后端(未实跑)· deps + 逐用例 reset(未实跑)· codex/claude 双引擎(codex 已实测能无头写 artifact)· 默认 8 仓并行。
**待办**:`--agent codex` 实跑 A 段产真 artifact · service/pipeline + deps 端到端 · py/rust/node 覆盖率接线 · Stage 5 测试级并行 · `ref.Dockerfile.*` 的 base digest · NFR 指标表接 Stage 4 · 真实仓 manifest。

## 12. 文档 ↔ 代码对齐表（改代码时按此同步本文档）
| 改了什么 | 同步更新本文 |
|---|---|
| 新增/改 Stage | §4 表 + §5 |
| 新增引擎模块 | §5 |
| manifest 字段 | §6(+ `manifest.schema.json`) |
| 并发/运行方式 | §7 |
| 依赖/状态清空策略 | §8 |
| 评分 | §9 |
| 新增/改后端或 runner | §5 / §3 原则 |

## 13. 实跑记录：gron 全流程 codex（2026-06-21，首次真 agent 端到端）
Stage 0–7 全过(local 模式 · WSL · `--agent codex`):
- **Stage 1–4/6 由 codex 生成,质量高**:repo-model 抓到 external_deps/determinism_hazards;modules 自带 `coverage_of_contract` 证明无孤儿;Stage 6 对抗判 `open_critical=0`。
- **Stage 5:116 用例,覆盖率 93%**(stub/cli_gen 版仅 71.6% —— codex 覆盖更全,含 URL 抓取路径),6/7 模块≥20;**M6(URL 模块)=17 → needs_review**(URL 行为要 record/replay 才能确定化+凑够,设计内的质量门)。`dropped_bad_spec=7`(坏断言被丢弃没崩)。
- **Stage 7:high-water 116/116(100%),mutation kill-rate 75%**(3 杀,1 良性存活)。

**本次实跑修的 4 个真问题**(已改代码 + 本文同步):
1. **codex 把 `rule` 当注释写整句** → `prompts/stage5_gen.md` 钉死 rule 关键字表(normalized/invariant 各自可用值)、理由放 `note`;`stage5_loop` 对坏断言 catch `(AssertionError,ValueError,KeyError)` **丢弃不崩**(`dropped_bad_spec` 计数)。
2. **fill_quota 凑不够的模块没被标** → `stage5_loop` 末尾把仍 `<quota` 的模块**统一标 needs_review**;`orchestrate` 加 `max_rounds`(manifest 可配,gron 用 5)。
3. **★GOCOVERDIR 坑**:`go build -cover` 二进制在未设 `GOCOVERDIR` 时往 **stderr** 打 `warning: GOCOVERDIR not set`;Stage 5 冻 golden 时设了(stderr 干净),但 `grade_suite` 判卷时没设 → 每条 exact-stderr 断言失败(high-water 一度只 37%)。→ `grade.grade_suite` 对 go-cover SUT **设一个 throwaway GOCOVERDIR**,使判卷行为与 golden 一致。mutation 不受影响(mutant 是普通 `go build`,不打 warning)。
4. **WSL 控制台输出常乱码/截断** → 所有 WSL 命令**输出重定向到文件再 Read**;别在 PowerShell 里写 `python3 -c` 嵌套引号(改用脚本文件或 host python)。

**2026-06-21 续:加了 agent 驱动 Stage 0(任意仓构建)** —— docker 模式 codex 按 `prompts/stage0_build.md` 给每个仓写 `Dockerfile.codebench`(含国内镜像源/warm-up)+`00_runtime.json`(service/pipeline/dependencies/smoke)→build→离线 smoke;构建失败的仓 Stage0 出局(脚本不花 codex);`_merge_runtime` 合并运行时配置;agent-built 镜像 `coverage='none'`。deps 加 `mongodb`。语言已用 GitHub API 补全(`scripts/detect_lang.py`),manifest=`dataset/codegen-bench.manifest.json`(109 仓),pilot 选 15=`dataset/pilot.manifest.json`。

待办:把 `record_replay` 接进 Stage 5 让 URL 模块确定化;B+C 段实跑。

**2026-06-22:需求两改 + pilot 开跑**
- ① 出题/判卷**不再断网**(`--network none` 全移除:runner/replay/pytest_emit/stage0 smoke + 两个 prompt),确定性改由**原仓双跑一致**保证:`classify.agrees(obs1,obs2,golden)` 按断言分类比对;`stage5_loop` 每条输入冻 golden 后**再跑一次**,不一致 → `dropped_nondeterministic` 丢弃(把非确定项挡在卷外)。
- ② Stage 4 读**用户 NFR 清单**(`NFR.pdf` → `dataset/metrics-table.json`,38 指标 SEC/COMPAT/REL/MAINT/PERF/PORT;`orchestrate` 启动时自动拷进每仓 `out/<id>/metrics-table.json`),逐条判**运行时黑盒 ∨ 源码静态**可测(`prompts/stage4_nfr.md` 明确 grader 既能跑候选也能读候选源码)。
- ③ **Docker Hub 被 GFW**(`registry-1.docker.io` 连接 reset,IPv6)且**无 sudo** 配 daemon `registry-mirrors` → 新增 `engine/dockermirror.py`:`docker build` 前把 Dockerfile 的 `FROM` 改写到 `docker.m.daocloud.io`(实测 codex **不照 prompt** 写镜像、仍写 `golang:1.20`,故必须引擎侧兜底;stage0_ingest + candidate.build_image 都接了)。国内镜像 daocloud/1ms/1panel 实测可拉。
- pilot = 15 仓 docker 模式,先跑 **goawk 单仓 canary** 验 docker 全链路(Stage0 build→1-8),通过再 fan-out 其余 14 仓。

**2026-06-22(续):pilot 跑完(6/15 出全卷)+ 修 3 个框架 bug**
- pilot 结果:**6/15 出完整考卷**(goawk/betterleaks/srgn/name-that-hash/eralchemy/dyff)。9 失败 = 6 个 Stage0 docker 构建失败(仓库自身难容器化:rust native 编译 / monorepo / 老 Go / apt 装包 —— Stage0 筛子按设计淘汰)+ 2 个 service 契约门 bug + 1 个 sq 权限 bug。**双跑确定性生效**(确定性工具 `dropped_nondeterministic=0`)。
- **修 BUG 1(卡所有 service 仓)**:Stage 2 产物门写死 `02_cli-contract.json`;但**实查发现** service 仓其实写了很好的 OpenAPI(29–65KB),只是 codex **自己起名 `02_openapi-contract.json`**(既非 cli 名也非任何约定名)。故彻底修:① `agent_stages.CONTRACT` 给每场景定**唯一规范名 + 别名表**(cli→`02_cli-contract.json` · service→`02_contract.openapi.json` · pipeline→`02_contract.io.json`),`_normalize_contract` 在 agent 跑完后把命中的别名**重命名成规范名**,门 + 下游(candidate/stage8)都按规范名找;② `prompts/stage2_contract.md` **钉死每场景的确切输出路径**(codex 已两次无视松散指令:镜像前缀、契约名);③ candidate.py/stage8 的 `.openapi.yaml` 统一改 `.openapi.json`;④ 报错文案 `claude stageN`→`{mode}`。`gates.py` 无 stage2 门、orchestrate schema 也不查 stage2。
- **修 BUG 2(卡所有写文件输出的 docker 仓)**:容器默认 **root** 跑,往 bind-mount workdir 写的输出文件归 root(sq 的 `export.yml` 还是 0600)→ 宿主非 root `_snapshot`/`read_bytes` 抓输出时 `PermissionError`。新增 `runner._docker_user_args()`(`--user $(id -u):$(id -g) -e HOME=/tmp`),接到 **`DockerRunner` / `PipelineBackend` / grader conftest** 三处 docker run → 输出文件归宿主、可读。**实测复现+修复**:root 写 0600 文件宿主读=PermissionError;`--user` 后归 uid1000、宿主读 OK。
- **修 BUG 3**:`stage8_package._prompt_md` 卷面残留 `--network none` → 改"运行期允许联网,判卷用冻结的双跑用例黑盒比对"。
- **健壮性**:`stage5_loop` 把 `backend.run`(run1+run2)包进 try 捕 `OSError` → 单条输入失败只丢该条(新计数 `dropped_run_error`),不再像 sq 那样崩掉整仓(原因:run1 在 try 外)。
- **可观测性**:`stage0_ingest` 构建失败时把**完整** build 日志写 `out/<id>/00_baseline/docker_build.log`(之前只存 `stderr[-1500:]`,真正的编译器报错被截断、6 个失败没法一眼诊断)。
- 全 24 模块 import 通过;重新生成的 grader(conftest/test_blackbox/_assert)`py_compile` 通过。**未重跑** afuh/postgres-meta/sq 端到端(需 codex)。`dropped_bad_spec` 偏高经查=codex draft 质量(stdout-only 仓也高),非崩溃 bug。

**2026-06-22(再续):codex 思考深度钉成 `xhigh`**。实测 codex(gpt-5.5)reasoning effort 档位 = `low < medium < high < xhigh`(`minimal` 这版未暴露;之前框架/config 都没设 → null ≈ medium)。现 `agent/client.py` 的 `_run_codex` 统一加 `-c model_reasoning_effort=xhigh`(常量 `CODEX_REASONING_EFFORT`,`run_headless(..., reasoning_effort=)` 可按调用覆盖)。实测一条 trivial 调用,session log 记录 `"reasoning_effort":"xhigh"` ✓。目的:提升 Stage 2 契约 / Stage 5 draft 质量(代价:token + 时延涨)。

**2026-06-23:Stage 0 加 agent build-repair 循环 + 新数据集 v2**。原 Stage 0 = codex 写 Dockerfile → 编排器 `docker build` 一次 → 失败即丢弃(**错误不反馈给 codex**)。现 `stage0_ingest.run` 改成**构建修复循环**(`config.build_repair_attempts`,默认 3):build 失败 → `_agent_fix_dockerfile` 把完整 build 日志喂回 codex(`prompts/stage0_fix.md`)让它改 Dockerfile → 重 build。根因:**codex 即便 xhigh 也爱写"全离线/frozen" Dockerfile**(`pip --no-index`、`pip wheel`+offline、`cargo build --frozen`、`CARGO_NET_OFFLINE`),零容错一碰就碎(v1 diffsitter、v2 yamllint/ruff 都栽这);`stage0_fix.md` + `stage0_build.md` 明确**禁离线花活、构建期联网走国内镜像、巨型 monorepo 只 build 需要的那个 binary**。新数据集:从新版 `final_report.html`(216 仓/5 场景)抽出 `dataset/codegen-bench-v2.manifest.json`(全量)+ `dataset/pilot-v2.manifest.json`(每场景 3,全 cli/pipeline、偏 go/rust/python、避 service、不复用 v1),可读清单 `dataset/repo-list-v2.md`;看板 `scripts/watch-v2.sh`。

## 14. 产物结构:做题侧 / 卷面（2026-06-21 改）
Stage 8(`stages/stage8_package.py`)把考卷拆两份,放 `out/<id>/07_exam/`:

**做题侧 `grader/`(做题 agent 看不到)**
- **pytest 黑盒套件**(`engine/pytest_emit.py` 生成):`test_blackbox.py`(参数化加载 cases)+ `conftest.py`(SUT fixture,候选经 `CANDIDATE_BIN`/`CANDIDATE_IMAGE` 注入;service 逐用例 `deps.reset`)+ `_assert.py`(exact/normalized/invariant/ignored 独立实现)+ `cases/*.json`(带 golden 的用例)。跑法 `CANDIDATE_BIN=./impl pytest grader/ -q`,末尾打印**每模块通过率 + functional 均值**。**实测:gron.exe 判卷 116/116=100%**。
- `measurable_metrics.json` —— Stage 4 从用户 `metrics-table.json` 判定**可测**的指标(+`not_observable` 不可黑盒测的及理由)。
- `rewritable_languages.json` —— Stage 1 给出的可重构语言池。

**卷面 `candidate/`(做题 agent 能看到)**
- `generation_language.txt`(从可重构池选定的实现语言)· `功能模块文档.md` · `用户行为示例文档.md` · `prompt.md`(任务提示)· `02_*` 契约。

配套 prompt 改动:**Stage 1** 加 `rewritable_languages`;**Stage 4** 改为读用户 `metrics-table.json` **逐指标判可测性**(probes=可测 / not_observable=不可测);**Stage 5** 加**自包含**硬规则——干净状态(每用例前 deps.reset)下用例**自建所有前置**(测登录先注册),防悬空。`orchestrate` STAGES 扩到 0–8。

> 注意:DockerRunner / Service+pipeline 在容器里跑用例**仍未实测**(docker 拉 Docker Hub 基础镜像被 GFW,需配 registry 镜像);现已证明的判卷路径是 LocalRunner / pytest-CANDIDATE_BIN。
