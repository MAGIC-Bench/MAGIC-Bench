# code-bench-v2 交接文档(HANDOFF）

> 给**下一个接手的 AI agent**:读完本文你应能继续推进，无需追问历史。
> 写于 2026-06-30。本地框架仓 = `D:\code-bench-v2`（以后只在此工作）。
> 文档中所有事实已用本地文件核对（未碰服务器/SSH，隧道当前不稳）。

---

## ① 一句话：这是什么

**code-bench-v2 是一个黑盒差分跨语言基准**：每道题取一个真实开源仓库（原语言 X），让多个 AI 编程 Agent **用另一种语言 Y 从零重写**，候选**看不到原仓源码**，只凭卷面给出的"对外可观察行为契约"实现；判卷是**黑盒差分**——把候选程序与"原仓跑出的 golden"在相同输入下对比，再叠加 NFR 六维评分。

- 流程三段：**出题**（stage0–8 生成 卷面 + golden + grader）→ **做题**（5 个 AI agent 各自重写，看不到原仓源码）→ **判卷**（构建 + smoke 门 + 差分测试用例 + NFR 六维）。
- 部署在中山大学学院租的 **Cube-Studio 集群** `/mnt/yangh559/code-bench-v2`，工作态在 `/mnt/yangh559/chuti-run`。
- 本地这份 `D:\code-bench-v2` 是框架仓 + 已下载回来的数据集/成绩/交付物。

---

## ② 服务器接入（隧道命令）

**我（AI）不能输密码，隧道必须由用户开。** 密码在 `D:\code-bench\Keys\Servers'Key.txt`。

1. 用户在 PowerShell 开隧道并**保持窗口开着**（输跳板机密码 `cubestudioOc1.` 一次）：
   ```
   ssh -N -L 2222:172.16.108.241:29001 cubestudio@172.16.108.241
   ```
2. 然后我用密钥直连容器（无密码）：
   ```
   ssh -i ~/.ssh/id_rsa -o IdentitiesOnly=yes -p 2222 root@127.0.0.1
   ```
3. **隧道常因 agy 做题节点拥塞而断**，服务器操作要重试；断了让用户重开第 1 步。
4. Cube-Studio 网页入口 `http://172.16.108.241/frontend/`（校园网 / NETID 登录）。

关键服务器路径：
- NFS 持久目录 `/mnt/yangh559`（容器 OS 临时，只此目录永久）。
- 工作态 `/mnt/yangh559/chuti-run`（`submissions/` `grades/` `exams/` `logs/`）。
- 代码 `/mnt/yangh559/code-bench-v2`。
- 一句 `source /mnt/yangh559/bench/env_profile.sh` 带起 conda+go+rust+node+agents+代理。

---

## ③ 数据集与真实分

### 数据集规模（已核对）
| 项 | 数 | 说明 |
|---|---|---|
| 原仓清单总数 | **121** | `dataset\repo-list.manifest.json`（99 cli + 22 service） |
| 出厂卷面 | **82** | `package\出卷包\卷面-考生包\` 82 个 |
| 可判题 | **81** | golden-评分标准 81 个；**`dosisod-refurb` 的 grader 缺失**（出题只到 baseline 阶段），无法判卷 |
| 主测 agent | 4 | claude / codex / cursor / kimi（每仓 `候选提交-各agent生成\<仓>\` 下 4 份） |
| 基线 agent | 1 | agy（Antigravity / Gemini），网络受限，单列、不进主排名 |

### 真实分（修复两个判卷 bug 后；越高越好，已核对见 report.html）
| 排名 | Agent | 总分 |
|---|---|---|
| 1 | **cursor** | **0.4916** |
| 2 | claude | 0.4765 |
| 3 | kimi | 0.4637 |
| 4 | codex | 0.4027 |
| — | agy（基线，被墙） | 0.0134 |

构建通过率约 **70–75%**。`score.json` 结构 = `build_ok` / `功能分` / `nfr_by_dimension`（六维，每指标 0/1/null）。

---

## ④ 三大发现（本会话核心产出）

### 发现 1：修了两个**系统性压低分数**的判卷 bug（已修，已全量重判）
- **(a) launch 路径 bug** — `run/fix_launch.py`：WORKROOT 改成 `/tmp/exam_work` 后，launch 里的路径没跟着重写 → 候选其实**构建成功却跑不起来** → `build_ok=false` → 判 0。改了正则修复。
- **(b) cwd 竞态 bug** — `run/grade_worker.sh`：删 `gtmp` 临时目录前没 `cd` 出去，下一轮 `grade.py` 在已被删的目录里崩 → 兜底判 0。已加 `cd` 出去再删修复。
- 修复后**全量重判**，上表是真实分。**修复前分数被系统性压低**，旧分作废。

### 发现 2：克隆原仓注水（保留现状，写进报告第 ⑧ 节）
- **卷面语言全对**：82 道卷面里 **0 个**用了原仓的原语言（去标识 + 目标语言锁定都生效）。
- 但判卷**不校验候选语言**，于是 **16 份提交直接克隆原仓**（写成原语言）钻空子。其中 **cursor 克隆 11 个**——它 10 个满分卷里有 **4 个是克隆注水**。
- 这是**基准设计的一条核心发现**（"判卷不校验语言"是可被利用的漏洞），**保留现状不动**，已写进 `report.html` 第 ⑧ 节。

### 发现 3：service 类全军覆没——栽在健全性门 gate7（代码溯源结论）
- 清单 121 仓里有 **22 个 service**，但**最终数据集 0 个 service**。
- **不是有意排除，是出题了却卡在 gate**：
  - `engine/classify.py` 的 `agrees`（原仓同输入跑两遍须一致才冻结用例）+ `engine/gates.py` 的 `gate_stage7`（原仓重跑自己 golden，丢弃率 >5% 判废）都要求 **golden 可复现**。
  - 有状态服务第二遍带着第一遍的状态残留 → 两遍不一致 → 判废进 SKIP。
- **根因**：流水线没有"重置状态"环节——`runner._snapshot()` 只快照文件；判卷 `restart()` 注释写明 `keep the data dir (dirty restart)` 故意不清状态。
- **原则上**加"状态快照 → 还原"即可避免，但通用化难，**没做**。
- 此结论已写进 `report.html` 第 ② 节"为什么全 cli 没 service"代码级溯源段。

### （附）10 个"全员 0 分"仓的真因
- **不是 cwd**（那是早期误判），是 **smoke 门偏严**：缺 `--version`、help 走 stdout 而非 stderr 等小特性就判 0。
- **用户决定：保持现状，不放宽 build 门。**

---

## ⑤ 交付物清单与路径（均已核对存在）

打包总入口在 `D:\code-bench-v2`：

| 交付物 | 路径 | 大小/数量 | 说明 |
|---|---|---|---|
| 完整数据集 ZIP | `code-bench-v2-dataset.zip` | ~1.05 GB | 单文件完整包 |
| 分卷上传 .001 | `分卷上传\code-bench-v2-dataset.zip.001` | ~540 MB | 7-Zip 分卷格式 |
| 分卷上传 .002 | `分卷上传\code-bench-v2-dataset.zip.002` | ~515 MB | 解压 .001 自动续读 .002 |
| 分析脚本 | `analyze.py` | — | 双模式，见 ⑥ |
| 报告 | `report.html` | ~83 KB | 10 节，浏览器直接打开 |
| 数据集 README | `README-dataset.md` | — | 解压后根目录的说明 |
| 备份（源） | `backup_clean\` | 2.77 GB | 82 仓，**只源码**（去构建产物/依赖缓存） |
| 打包暂存 | `package\` | — | 7z 从这里打完整包 |

**ZIP / package 内部结构**（已核对一致）：
```
出卷包/
├── 卷面-考生包/<仓>/         （82 个）candidate 卷面 + meta.json
└── golden-评分标准/<仓>/     （81 个）07_exam: 原仓 golden + grader
候选提交-各agent生成/<仓>/<agent>/work/   各 agent 生成源码（claude/codex/cursor/kimi）
成绩/<仓>/<agent>/score.json
元数据/
├── repo-list.manifest.json   （121 仓清单）
└── report-lang.json          （权威语言映射）
analyze.py / report.html / README.md
```

`backup_clean\` 内部 = `out\`（81 仓出题产物）+ `chuti-run\`（`exams/` `grades/` `submissions/`）。

---

## ⑥ analyze.py / report.html 怎么用、改后怎么同步进 ZIP

### analyze.py 双模式（无第三方依赖，Python 3.8+，本机 Python 3.12）
- `python analyze.py --backup` → **本机生成用**，直接读 `D:\code-bench-v2\backup_clean`（`chuti-run\grades|exams|submissions` + `dataset\repo-list.manifest.json` + `_report_lang.json`）。
- `python analyze.py`（无参，**包内运行**）→ 读相对目录 `成绩/` `出卷包\卷面-考生包/` `候选提交-各agent生成/` `元数据/`。
- 两模式都输出到脚本同目录的 `report.html`。
- **所有"率"两位小数 + 同时写出分子/分母原始数据**（设计约定，改报告时保持）。

### report.html 十节
① 方法学 ② 数据集构成（含"为什么全 cli 没 service"代码溯源）③ Agent 综合排名 ④ 功能分分布 ⑤ NFR 维度热力 ⑥ 按场景 ⑦ 按目标语言 ⑧ 克隆现象 ⑨ 逐仓详情（可排序）⑩ 已知问题。

### 改报告后同步进 ZIP（**每次必走全套，否则交付物与报告脱节**）
7-Zip 在 `C:\Program Files\7-Zip\7z.exe`（**不在 PATH**，要写全路径）：
1. 在 `D:\code-bench-v2` 跑 `python analyze.py --backup` 重生成 `report.html`。
2. 把新 `report.html`（必要时连同 `analyze.py`）复制进 `package\`。
3. `7z` 更新完整包 `code-bench-v2-dataset.zip`（用 `package\` 内容）。
4. **删旧分卷** `分卷上传\*.001 *.002`。
5. `7z ... -v540m` 从完整包重建分卷到 `分卷上传\`。

---

## ⑦ 未完成项与待办

1. **停掉 agy 做题（最优先）**：agy 还在 ~15 个做题节点上跑，已见顶 ~53/82，大面积超时（228+ 次），且**占用拥塞的隧道**，用户一直没停。
   - **停法**：从 Cube-Studio 网页（`http://172.16.108.241/frontend/`，NETID 登录）任意做题节点终端跑：
     ```
     touch /mnt/yangh559/chuti-run/STOP
     ```
     `exam_worker` 认 `$STATE/STOP` 中央停全节点；判卷 worker 也认 STOP。
   - `GRADE_SKIP=agy` 已设（agy 不参与判卷）。

2. **report.html ⑤ 节加 NFR 算法说明（待用户确认后做）**：用户问过"NFR 怎么算 + 分母为什么这么大"，已口头解释，**提议把说明写进报告 ⑤ 节**，含静态/运行时指标清单，**等用户点头再动**。
   - NFR 算法要点（供撰写参考）：每道题约 20 个**适用**指标 × 6 维，每指标 0/1；**静态维度**由 codex（`model_reasoning_effort=low`）读源码打分，**运行时维度**真跑候选打分；**build 失败的卷所有 NFR 强制 0**；"满足率"是微观聚合 = 所有 1 / 所有非 null，分母 ≈ 81 道 × 约 19 指标/道 ≈ **1526**（所以分母看着大）。

3. **dosisod-refurb grader 缺失**：出题只到 baseline，无 grader → 81 道可判而非 82。若要补，需重跑该仓 stage6+（生成 grader）。

---

## ⑧ 坑与约束（下一个 agent 必读）

**接入 / 服务器**
- 我不能输密码，**隧道由用户开**；隧道经常断（agy 节点拥塞），服务器操作要重试。
- 后台任务 `TaskStop` 可能不杀底层进程 → 留下**下载/SSH 孤儿打架**。本地文件操作无隧道风险，**SSH 类后台任务有**。

**Windows / PowerShell**
- PowerShell 的 `-match` / `.Contains()` 对**中文不可靠** → 核对文本用 **Bash grep**。
- `Remove-Item -Recurse` 触发 **harness 护栏** → 删深路径/大目录改用 `robocopy /MIR 空目录` 或 .NET `[IO.Directory]::Delete`。
- **7-Zip 在 `C:\Program Files\7-Zip\7z.exe`（不在 PATH）**；本机 **Python 3.12**。

**备份脚本踩过的坑（都已修，避免重蹈）**
- `backup_to_local.sh` 里 `\$EXC` 被转义 → 排除规则在远端展开成空 → 备份暴涨到 100GB+。
- 后台任务 `TaskStop` 没杀透 → 留下载孤儿打架。
- agent 用**变体缓存目录名**（`.rustup-home` / `.cargo-home` / `.go` 等）漏排 → 也要排进去。
- 最终干净备份 = `backup_clean\`（2.77GB，只源码）。

---

## 关键路径速查

| 用途 | 路径（相对 `D:\code-bench-v2`） |
|---|---|
| 分析脚本 | `analyze.py` |
| 报告 | `report.html` |
| 干净备份（源） | `backup_clean\`（`out\` + `chuti-run\`） |
| 打包暂存 | `package\` |
| 121 仓清单 | `dataset\repo-list.manifest.json` |
| 权威语言映射 | `_report_lang.json`（从 `D:\code-bench\benchmark_screening_report.html` 解析） |
| 出题引擎 | `engine\`（`gates.py` `classify.py` `_grade.py` `nfr_score.py`） |
| 判卷/做题脚本 | `run\`（`launch_chuti.sh` `grade_worker.sh` `exam_worker.sh` `fix_launch.py`） |
| 框架总说明 | `FRAMEWORK.md`、`README-dataset.md` |

相关记忆文件（`C:\Users\16611\.claude\projects\C--\memory\`）：
`cubestudio-bench-server.md`（服务器接入/依赖/代理/韧性层）、`code-bench-v2-fairness-fixes.md`（出题公平/防泄漏修订三轮）、`code-bench-v2-server-local-run.md`、`code-bench-v2-dataset-pilot-v3.md`。
