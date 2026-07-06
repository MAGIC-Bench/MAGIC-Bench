# 性能效率维度评测文档（ISO 25010 对齐 · 动态 + 机械静态 + LLM 静态 · v3）

> **重构说明**:在原「被动式绝对预算定稿版」基础上做三件事——
> 1. 按 **ISO/IEC 25010 Performance Efficiency** 的三子特性(**Time Behaviour 时间行为 / Resource Utilisation 资源利用 / Capacity 容量**)重组评分;
> 2. **完整保留**被动动态监听(复用 `05_tests/*.json`,不造性能专用用例)与**可机械判定**的静态扫描;
> 3. 把**静态难以可靠判定**的规则(busy-wait / 无界循环 / 整文件入内存 / 临时文件泄漏 / 热路径判断 / 容量上限等语义)交给 **LLM 扫描**。规则由本文定义,**LLM 只产 finding,扣分与总分仍由代码按固定表 + 封顶计算,LLM 不打分**。

---

## 0. 三层测量结构（总览）

| 层 | 实现 | 负责 | 状态 |
|---|---|---|---|
| **L1 动态(passive observer)** | `PerfObserverRunner` 包裹执行,复放 `05_tests/*.json`,记录 wall/cpu/mem/io | 真实运行的时间/资源观测 | **保留原文** |
| **L2 机械静态(regex/AST)** | 关键字命中 + 循环结构(AST)命中 | 可确定判定的性能反模式(高召回候选) | **保留** |
| **L3 LLM 静态(semantic)** | LLM 读源码 + 规则卡 → 结构化 finding | 热路径/无界/泄漏/容量等语义判断 + 纯语义风险检测 | **新增** |

**关键原则(不变):** finding 由 L2 或 L3 产生;**penalty、封顶、StaticScore、总分一律由代码按固定表计算,LLM 绝不打分**。

> **测量有效性提醒(沿用既有结论):** hidden tests 是正确性小输入,不是性能负载。因此 L1 的 Latency/Throughput 在小输入上主要反映**进程/容器启动开销**,是**粗信号**(可靠区分"慢一个数量级/超时/OOM",难区分算法复杂度)。落地要求:**计时移入容器内**(只计程序,不绕 `docker run`)、**串行 + 固定 `--cpus/--memory`**、每用例 3 次取中位数、每次前执行 reset。**Capacity 子特性因此以 L3 LLM 静态为主**(见 §6)。

---

## 1. ISO 子特性映射

| ISO 子特性 | L1 动态 | L2 机械静态 | L3 LLM 静态 |
|---|---|---|---|
| **Time Behaviour 时间行为**<br>(响应/处理时间、吞吐) | LatencyBudgetScore、TailStabilityScore、EffectiveThroughputScore | `hard_coded_sleep`、循环内 `subprocess`、嵌套循环、网络调用关键字 | 判"是否在热路径/随规模放大";`busy_wait`(纯语义) |
| **Resource Utilisation 资源利用**<br>(资源用量与类型) | MemPeakScore(cgroup)+ CPU 秒 / IO 字节(可选 composite) | 循环内 `thread spawn`/日志、整文件读关键字 | 判"是否无界/无池化/泄漏";`temp_file_leak`(纯语义) |
| **Capacity 容量**<br>(参数最大限制) | RuntimeCompletionScore(无 OOM/timeout 的**弱下限**) | (弱) | **主力**:`unbounded_loop`/`unbounded_recursion`/`no_streaming_for_large_input`/`hardcoded_capacity_limit` |

---

## 2. 保留不变的机制（引用原文）

- **§5.1 `Observation.perf` 字段**:`wall_time_s, start_ts, end_ts, timed_out, failure_kind, cpu_seconds, mem_peak_bytes, io_read_bytes, io_write_bytes`(不参与 `classify.check`,功能判卷只读功能字段)。
- **§5.2 `PerfObserverRunner`**(改:计时移入容器内,见 §0 提醒)。
- **§5.3 `failure_kind`**:`timeout / process_crash / nonzero_exit / oom_kill / connection_failure / readiness_lost / runner_error / wrong_output / unsupported_library`。
- **§11.5 重复运行**:每用例 3 次、每次前 reset、取中位数耗时;任一次异常计入 summary。
- **配置** `configs/perf_policy.yaml`(预算、权重)。`library` 仍为 schema 保留值,执行器返回 `unsupported_library` 并剔除。

---

## 3. L1 动态测量（保留，按 ISO 归位）

动态指标与原文公式一致,只是**归入 ISO 子特性**(`time_floor_s=0.001`):

**Time Behaviour:**
- `LatencyBudgetScore = max(0, 100*(1 - L95 / L95_upper_s))`,`L95_upper_s=30`,只统计功能正确用例。
- `TailStabilityScore`:`TAR = L99 / max(L50, time_floor_s)`;`TAR<=1 → 100`,否则 `max(0, 100*(4 - TAR)/3)`。
- `EffectiveThroughputScore = SR * RawThroughputScore`,`RawThroughputScore = min(100, 100*ET/TargetET)`,`ET=N_correct/T_elapsed`,`TargetET=N_total/suite_time_budget_s`(600),`SR=N_correct/N_total`。

**Resource Utilisation:**
- `MemPeakScore = max(0, 100*(1 - MemPeak / mem_peak_upper_bytes))`,`mem_peak_upper_bytes=4 GiB`;缺 cgroup 采样 → 0(故 docker 模式必须开 cgroup)。
- (可选)`CpuScore`/`IoScore`:同 budget 形式,用 `cpu_seconds` / `io_*_bytes`,默认权重 0 或低,记录优先。

**Capacity:**
- `RuntimeCompletionScore = 100 * N_completed / N_total`(`N_completed` = 无 timeout/crash/oom/nonzero_exit/connection_failure/readiness_lost/runner_error/unsupported_library 的用例)。**仅作容量弱下限**——它只证明"在给定小负载下没崩",不证明真实容量上限。

---

## 4. 静态扫描：L2 机械 + L3 LLM（核心改动）

### 4.1 原 10 类规则重新归类与分层（+ 新增 3 条 Capacity LLM 规则）

| rule | ISO 子特性 | L2 机械(可确定) | L3 LLM(语义裁决/检测) | sev / penalty |
|---|---|---|---|---:|
| `hard_coded_sleep` | Time | 命中 `sleep()/time.sleep/Thread.sleep` | 判"在运行/热路径,而非合理退避或测试夹具" | high / 3 |
| `busy_wait` | Time | (弱) | **纯语义**:自旋等待,循环内无 sleep/yield/阻塞 | high / 4 |
| `nested_loop_hot_path` | Time | AST 命中嵌套循环 | 判"在热路径且随输入规模放大" | low / 1 |
| `network_call_in_hot_path` | Time | 命中网络调用 API | 判"在热路径/每用例都打" | high / 3 |
| `subprocess_in_loop` | Time | AST 命中循环内 `subprocess/exec` | 判"每次迭代启动外部进程" | high / 4 |
| `thread_spawn_in_loop` | Resource | AST 命中循环内 `spawn/Thread()` | 判"无界线程、无池化" | high / 4 |
| `full_file_load` | Resource | 命中 `read()/read_to_string/readlines` | 判"整文件入内存、无流式、对大输入" | medium / 2 |
| `temp_file_leak` | Resource | (弱) | **纯语义**:建临时文件/句柄未删、未用上下文管理 | medium / 2 |
| `excessive_logging_in_loop` | Resource | AST 命中循环内日志调用 | 判"高频日志在热路径" | medium / 2 |
| `unbounded_loop` | Capacity | (弱) | **纯语义**:无终止界 / 无界增长 / 无背压 | high / 4 |
| `unbounded_recursion` *(新)* | Capacity | (弱) | **纯语义**:递归无深度界,大输入栈溢出 | high / 4 |
| `no_streaming_for_large_input` *(新)* | Capacity | (弱) | **纯语义**:一次性构造/加载全量,无分块/流式,容量受内存限 | medium / 2 |
| `hardcoded_capacity_limit` *(新)* | Capacity | 命中固定缓冲/上限常量 | 判"超限即失败,且非合理设计上限" | low / 1 |

### 4.2 L2 机械静态扫描（保留）

扫描范围、排除目录、扩展名、字节上限、`skipped_file`:沿用原文。L2 只做确定性命中(关键字 + 循环结构 AST),输出候选 finding,标 `layer: mechanical`;带"热路径/无界/泄漏"判断的,交 L3 裁决。

### 4.3 L3 LLM 静态扫描（新增）

#### 4.3.1 规则卡格式（本文定义）

```yaml
- id: busy_wait
  subcharacteristic: time_behaviour
  intent: 自旋忙等浪费 CPU、拖慢整体,且无确定退出时机
  detect_when: 出现 while/loop 反复检查条件而循环体内无 sleep/yield/阻塞调用/事件等待
  not_a_finding_when:
    - 循环体内有 sleep/backoff/condition-variable/select/poll 等让出 CPU 的等待
    - 有明确的超时/最大次数上界
  severity: high
  penalty: 4
  evidence_required: [file, line_start, line_end, code_snippet]
```

（其余 L3 规则卡同构:`detect_when` / `not_a_finding_when` 取自上表语义列;`full_file_load`/`unbounded_*`/`no_streaming_for_large_input` 重点判"对大输入是否成问题"。)

#### 4.3.2 LLM 扫描提示（模板）

> 你是**静态性能效率审查器**。输入:候选源码 + 规则卡 + L2 候选命中(可选)。
> 对每条规则:**仅当**满足 `detect_when`、**不满足任何** `not_a_finding_when`、且置信度 ≥ 0.7 时产出 finding。
> **不要打分、不要改 penalty、不要新增规则。** 无法确认就不产出(高精度低召回)。
> 判"热路径"时,优先看该代码是否在 contract 的主处理路径 / 每个 testcase 都会走到的路径。
> 输出 JSON:`{"findings":[{"rule_id","subcharacteristic","file","line_start","line_end","evidence","confidence","why"}]}`。

#### 4.3.3 输出 schema 与合并扣分

- 输出 schema 同可移植性文档 §4.3.3。
- **合并扣分(代码侧,确定性)**:L2 候选 + L3 检测 → 裁决(带语义判断的以 L3 为准)→ 去重 →
  - 沿用原文封顶 `same_rule_cap=6`、`same_file_cap=8`;**按子特性各自封顶 `subchar_cap=20`**;
  - `StaticPenalty_<subchar> = min(20, capped_sum(该子特性 finding penalty))`;
  - explanation:L2 用模板,L3 用 LLM 的 `why`。

---

## 5. 执行器改动（最小）

- `engine/perf_passive.py`:聚合 L1 指标 → 三个子特性的动态分;调 `static_perf_scan` 得三个 `StaticPenalty_<subchar>`;按 §6 合成。
- `engine/static_perf_scan.py`:拆 `l2_mechanical_scan()` + `l3_llm_scan(rules, files)` + `merge_and_penalize()`。
- `PerfObserverRunner`:计时**移入容器内**(只计程序);cgroup 读 `mem_peak/cpu/io`(短命容器用 detached 或 `/usr/bin/time`,避免 `--rm` 即丢)。

---

## 6. 评分（按 ISO 子特性重组）

每个子特性 = **0.85 动态 + 0.15 静态(100 − 5 × 该子特性静态扣分)**:

```
TimeBehaviour      = 0.85 * (0.45*Latency + 0.30*Tail + 0.25*Throughput)
                   + 0.15 * max(0, 100 - 5 * StaticPenalty_time)

ResourceUtilisation= 0.85 * (1.00*MemPeak [+ 可选 CPU/IO])
                   + 0.15 * max(0, 100 - 5 * StaticPenalty_resource)

Capacity           = 0.85 * RuntimeCompletionScore        # 弱下限
                   + 0.15 * max(0, 100 - 5 * StaticPenalty_capacity)

PerformanceEfficiencyScore = 0.45*TimeBehaviour + 0.35*ResourceUtilisation + 0.20*Capacity
PerformanceEfficiencyScore = min(100, max(0, ...))
```

- 权重(0.45/0.35/0.20、子项权重、预算阈值)在 `perf_policy.yaml` 可调。
- **诚实标注**:Capacity 的动态部分只是"没崩"的弱下限,**真实容量需 scale 输入(被动设计不生成)**,故 Capacity 实际由 **L3 LLM 静态主导**;Time/Throughput 在小输入上是粗信号(见 §0)。若你只信硬信号,可把 Time/Throughput 子项权重调低,让分数主要由 **RuntimeCompletion(无 OOM/超时)+ 资源峰值 + 静态反模式** 承载。

---

## 7. 报告格式（扩展，按子特性 + 分层）

`out/<repo>/06_performance/run_report.<candidate_id>.json`:

```json
{
  "mode": "iso_aligned_passive_observer",
  "candidate_id": "codex_run_001",
  "runner": {"mode": "docker", "image": "bench-eval-env:2026-06", "cpu_limit": "2", "memory_limit": "4g", "timing": "in_container"},
  "subcharacteristics": {
    "time_behaviour":      {"dynamic": 71.0, "static_penalty": 7, "static": 65, "score": 70.1,
                            "metrics": {"L50_s":0.021,"L95_s":8.4,"L99_s":0.131,"TAR":6.24,"ET":0.12}},
    "resource_utilisation":{"dynamic": 84.0, "static_penalty": 4, "static": 80, "score": 83.4,
                            "metrics": {"MemPeakBytes":687194767}},
    "capacity":            {"dynamic": 95.0, "static_penalty": 6, "static": 70, "score": 91.25,
                            "note": "dynamic 仅弱下限;真实容量需 scale 输入,主要看静态"}
  },
  "summary": {"N_total":80,"N_correct":72,"N_completed":76,"N_timeout":2,"N_crash":1,"N_oom":0},
  "static_scan": {"l2_mechanical_findings": 3, "l3_llm_findings": 2,
                  "by_subcharacteristic": {"time_behaviour":7,"resource_utilisation":4,"capacity":6}},
  "final": {"formula": "0.45*Time + 0.35*Resource + 0.20*Capacity", "PerformanceEfficiencyScore": 77.6}
}
```

`static_scan_report.<candidate_id>.json` 每条 finding 含 `layer`(mechanical|llm)、`subcharacteristic`、`confidence`(仅 llm)、`explanation`。

---

## 8. 最终定义

> 性能效率 = 候选仓库在统一执行环境、统一资源预算、现有 hidden tests 工作负载下,按 ISO 25010 的**时间行为 / 资源利用 / 容量**三子特性表现出的性能属性。三层测量:**被动动态监听(时间/资源观测)+ 可机械判定的静态反模式 + 需要语义判断的 LLM 静态扫描**;LLM 只产 finding,扣分与总分由代码按固定表与封顶统一计算。受被动设计与小输入工作负载限制,时间/吞吐为粗信号、容量以静态为主——这是与功能正确性(frozen assertions)解耦后,该维度可落地、可归因的实现边界。
