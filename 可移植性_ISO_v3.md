# 可移植性维度评测文档（ISO 25010 对齐 · 动态 + 机械静态 + LLM 静态 · v3）

> **重构说明**:在原「统一评测镜像·纯机械脚本定稿版」基础上做三件事——
> 1. 按 **ISO/IEC 25010 Portability** 的三子特性(**Adaptability 适应性 / Installability 可安装性 / Replaceability 可替换性**)重组评分;
> 2. **完整保留**原有的动态测试(统一镜像 + profile matrix + 复放 hidden tests)与**可机械判定**的静态扫描;
> 3. 把**静态难以可靠判定**的规则(需要"是否有保护 / 是否运行期 / 是否写进源码树 / 是否需要缺失的生成步骤"等语义判断)交给 **LLM 扫描**。规则由本文定义,**LLM 只产出 finding,扣分与总分仍由代码按固定表 + 封顶计算,LLM 不打分**。

---

## 0. 三层测量结构（总览）

| 层 | 实现 | 负责 | 状态 |
|---|---|---|---|
| **L1 动态(execution)** | 统一评测镜像 + profile matrix + 复放 `05_tests/*.json` | 真实环境扰动下能不能构建/运行/通过 | **保留原文** |
| **L2 机械静态(code regex/AST)** | 关键字/字面量命中、对 `dependency_catalog.yaml` 交叉引用 | **可确定判定**的环境绑定信号(高召回候选) | **保留** |
| **L3 LLM 静态(semantic)** | LLM 读源码 + 规则卡 → 结构化 finding | 需要语义判断的规则(高精度裁决 + 纯语义风险检测) | **新增** |

**关键原则(不变):** finding 可由 L2 或 L3 产生;**penalty、封顶、StaticScore、总分一律由代码按固定表计算,LLM 绝不打分**。L2 负责"高召回地框出候选",L3 负责"高精度地裁定是否真风险 + 检测无关键字可抓的纯语义风险"。这恰好实现原文「高精度低召回」目标,且比纯机械更准。

---

## 1. ISO 子特性映射

| ISO 子特性 | L1 动态 | L2 机械静态 | L3 LLM 静态 |
|---|---|---|---|
| **Adaptability 适应性**<br>(适应不同/演变环境) | profile matrix **P1 minimal-env / P2 path-with-spaces / P3 non-root / P4 tmpdir**(相对 P0 的通过率) | 绝对路径/路径分隔符/OS 专属 API/读 env/root 关键字**命中** | 判"是否无保护/无 fallback/无默认值";`writes_into_source_tree`(运行期写源码树,纯语义) |
| **Installability 可安装性**<br>(成功安装/卸载) | **StandardBuildScore**(统一镜像内**离线**按模板构建成功)+ 依赖声明校验 | `undeclared_system_dependency`(对 catalog 交叉引用) | `generated_artifact_required`(运行依赖缺失的生成步骤);卸载残留(scatter 到树外) |
| **Replaceability 可替换性**<br>(替换同类产品/drop-in) | **契约一致性**:在文档化契约下复用 P0 功能通过率作为"可替换/drop-in"信号 | —— | 接口/数据格式兼容性、专有锁定、运行期绑定特定上游(`external_network_required_at_runtime`) |

> Replaceability 与功能正确性(frozen assertions)天然重叠——它**借用**功能信号,权重最低,且单独报告,避免重复计分。

---

## 2. 保留不变的机制（引用原文，不复述细节）

以下原文机制**原样保留**,本次不改:

- **§2 候选提交要求**:`candidate_manifest.yaml`(language_profile / project_type / dependencies / entry);不接受候选自带 Dockerfile 作为评分依据。
- **§3 统一评测镜像** `bench-eval-env:<version>`、容器目录结构、构建期与运行期 `network_mode=none`。
- **§4 依赖目录** `dependency_catalog.yaml` + 依赖校验 + 离线安装命令。
- **§6 `portability_policy.yaml`** 的 execution / dependency_policy / profiles(P0–P4)定义。
- **§7 执行器** `EvalContainerRunner` / `ProfileRunner` / `engine/portability.py`。
- **§9 Profile 定义**(P0_default、P1_minimal_env、P2_path_with_spaces、P3_non_root_user、P4_tmpdir_variation),**固定 5 个,报告不得删减**。
- **§14 判定边界**(构建失败 / profile-case 失败 / 源码缺失 / manifest 缺失 / 网络策略固定)。

> 唯一新增的执行器模块见 §5;唯一改动的是**静态扫描拆成 L2+L3**(§4)与**评分按 ISO 子特性重组**(§6)。

---

## 3. L1 动态测量（保留，按 ISO 归位）

动态部分逻辑与原文一致,只是把产出**归入 ISO 子特性**:

- **Installability ← StandardBuildScore**:统一镜像内离线按固定模板构建成功 = 100,失败 = 0(失败时该仓 Installability 动态分 = 0,但 L2/L3 静态扫描仍执行)。涵盖原 INS1/INS2/INS3/INS5。
- **Adaptability ← ProfilePassScore**:对 P1–P4 复放 hidden tests 的通过率(P0 为基线/功能复用)。
  - `ProfilePassScore = 100 * N_pass / N_total`,profile-case 通过条件同原文 §8.2(无 timeout/crash/nonzero_exit/oom/connection_failure/readiness_lost 且 `classify.check` 全过)。
  - 每个 profile 仍单独报 `ProfileScore(profile_id)`。涵盖原 A1/A3/A4。
- **Replaceability ← ContractConformanceScore**(新口径,借用信号):P0_default 下在**文档化契约**(02_*-contract)上的功能通过率,作为"能否 drop-in 替换原产品"的代理。涵盖原 REP1/REP2/REP3。**标注为 borrowed,单独报告。**

---

## 4. 静态扫描：L2 机械 + L3 LLM（核心改动）

### 4.1 原 10 类规则的重新归类与分层

| rule | ISO 子特性 | L2 机械(可确定) | L3 LLM(语义裁决/检测) | severity / penalty |
|---|---|---|---|---:|
| `unguarded_hardcoded_absolute_path` | Adaptability | 命中 `/tmp/ /var/ /usr/ /etc/ C:\ D:\` 等字面量 | 判"无 env/config/tmpdir 保护**且**参与读写/执行/输出路径" | high / 4 |
| `hardcoded_path_separator` | Adaptability | 命中字符串拼接 `"/"`/`"\\"` | 判"未用标准库 path-join" | medium / 3 |
| `shell_specific_command` | Adaptability | 命中 `bash sh chmod chown rm -rf cp -r mkdir -p` 等 | 判"运行期调用,且非构建期/非镜像模板完成" | high / 4 |
| `unguarded_os_specific_api` | Adaptability | 命中 `std::os::* unistd.h windows.h sys.platform process.platform runtime.GOOS` | 判"附近无 cfg/平台判断/fallback 保护" | high / 5 |
| `required_env_without_default` | Adaptability | 命中读 env(`getenv`/`os.environ`/`process.env`) | 判"无默认值 / 无清晰报错 / 无文档 / 无 .env.example" | medium / 3 |
| `writes_into_source_tree` | Adaptability | (弱:命中写文件 API) | **纯语义**:判"运行期把 cache/log/db/产物写进 `src/tests/app/lib/crates`" | high / 4 |
| `root_permission_required` | Adaptability | 命中 `sudo su chmod 777`、写 `/usr /etc /var`、bind <1024 端口 | 判"运行期确需 root" | high / 4 |
| `undeclared_system_dependency` | Installability | 命中 `openssl sqlite ffmpeg protoc gcc ...` **且** catalog 未声明 | (可选)判"确在运行期调用" | high / 4 |
| `generated_artifact_required` | Installability | (弱) | **纯语义**:判"运行依赖生成产物(protobuf/编译 schema/前端 dist/迁移产物)**且**仓库与构建模板都缺生成步骤" | medium / 3 |
| `external_network_required_at_runtime` | Replaceability | (弱:命中网络调用) | **纯语义**:判"复放 hidden tests 所需路径需访问非 localhost / 非容器内 sidecar 的外网" | high / 5 |

> 规则识别口径(命中对象、保护条件)沿用原文 §11,但**"保护条件成立与否"的判断从机械改判给 L3 LLM**(这正是原机械版做不准的部分)。

### 4.2 L2 机械静态扫描（保留）

- 扫描范围、固定排除目录、固定扩展名、单文件/单仓字节上限、`skipped_file` 处理:**沿用原文 §10.2**。
- L2 只做**确定性命中**(关键字/字面量/对 catalog 交叉引用),输出"候选 finding(candidate)",标 `layer: mechanical`。
- 对带"保护条件"的规则,L2 命中后**不直接定罪**,而是作为候选交给 L3 裁决(见 4.4)。

### 4.3 L3 LLM 静态扫描（新增）

#### 4.3.1 规则卡格式（本文定义，喂给 LLM）

每条 L3 规则用统一"规则卡"描述,LLM 读卡 + 读源码后判定:

```yaml
- id: writes_into_source_tree
  subcharacteristic: adaptability
  intent: 运行期把缓存/日志/DB/产物写进源码目录,换工作目录或只读挂载会失败
  detect_when: 运行路径中向 src/tests/app/lib/crates 等源码目录写文件(open(...,'w')/create/mkdir/落盘)
  not_a_finding_when:        # 命中任一即不算 finding(高精度)
    - 写入目标来自 TMPDIR / XDG_CACHE_HOME / 用户配置目录 / 可配置的输出路径
    - 仅发生在测试夹具或构建期,而非运行期
  severity: high
  penalty: 4
  evidence_required: [file, line_start, line_end, code_snippet]
```

（其余 9 条规则的卡片同构,字段取自上表 §4.1 + 原文 §11 的命中对象/保护条件。）

#### 4.3.2 LLM 扫描提示（模板）

> 你是**静态可移植性审查器**。输入:候选源码文件 + 一组规则卡 + L2 给出的候选命中(可选)。
> 对每条规则:**仅当**代码满足 `detect_when`、**不满足任何** `not_a_finding_when`、且你的置信度 ≥ 0.7 时,产出一条 finding。
> **不要打分,不要改 penalty,不要新增规则。** 无法确认就**不产出**(高精度低召回,漏的交给 profile matrix 暴露)。
> 输出 JSON:`{"findings":[{"rule_id","subcharacteristic","file","line_start","line_end","evidence","confidence","why"}]}`。
> `why` 是你对"为什么这是真风险、为什么不被保护条件豁免"的一句话解释(将作为报告里的 explanation)。

#### 4.3.3 LLM 输出 schema

```json
{ "findings": [
  { "rule_id": "writes_into_source_tree", "subcharacteristic": "adaptability",
    "file": "src/cache.py", "line_start": 31, "line_end": 36,
    "evidence": "open(os.path.join('src','.cache'), 'w')",
    "confidence": 0.88, "why": "运行期把缓存写进源码目录,只读挂载/换目录会失败,且未走 TMPDIR" } ] }
```

### 4.4 L2 + L3 合并 → penalty（代码侧，确定性）

1. **候选汇总**:L2 命中(带保护条件的)+ L3 纯语义检测,统一进入裁决池。
2. **裁决**:带保护条件的规则,以 **L3 的判定为准**(L2 命中但 L3 判为被保护 → 丢弃);无保护条件的纯语义规则,直接采 L3 finding(confidence ≥ 0.7)。
3. **去重**:同 (rule_id, file, line) 合并。
4. **扣分(沿用原文 §10.5/§10.6 的表与封顶,但按子特性分桶)**:
   - 每条 finding 读 `penalty`;`same_rule_cap=8`、`same_file_cap=10`;
   - **按 ISO 子特性各自封顶 `subchar_cap=20`**(原来是全仓 global_cap=20,现拆到每个子特性)。
   - `StaticPenalty_<subchar> = min(20, capped_sum(该子特性下的 finding penalty))`
5. **explanation**:L2 finding 用模板文本(原文 §10.7);L3 finding 用 LLM 的 `why`。

---

## 5. 执行器改动（最小）

- 新增 `engine/static_portability_scan.py` 拆为两段:`l2_mechanical_scan()`(原机械逻辑)+ `l3_llm_scan(rules, files)`(调 LLM,headless,只读源码);`merge_and_penalize()` 做 §4.4 的合并与扣分。
- `engine/portability.py` 在算分时把 StandardBuildScore / ProfilePassScore / ContractConformanceScore 与三个 `StaticPenalty_<subchar>` 一起喂给 §6 的评分。
- 其余(EvalContainerRunner / ProfileRunner / profile matrix)**不动**。

---

## 6. 评分（按 ISO 子特性重组）

每个子特性 = **0.85 动态 + 0.15 静态(100 − 5 × 该子特性静态扣分)**,保持原文 0.85/0.15 平衡:

```
Adaptability   = 0.85 * ProfilePassScore            + 0.15 * max(0, 100 - 5 * StaticPenalty_adaptability)
Installability = 0.85 * StandardBuildScore          + 0.15 * max(0, 100 - 5 * StaticPenalty_installability)
Replaceability = 0.85 * ContractConformanceScore    + 0.15 * max(0, 100 - 5 * StaticPenalty_replaceability)

PortabilityScore = 0.45 * Adaptability + 0.30 * Installability + 0.25 * Replaceability
PortabilityScore = min(100, max(0, PortabilityScore))
```

- 权重 0.45/0.30/0.25 可在 `portability_policy.yaml` 调(Adaptability 信号最丰富给最高;Replaceability 借用功能信号给最低)。
- **硬边界保留**:构建失败 → Installability 动态 = 0(连带 Adaptability 动态 = 0,因为没东西可跑);源码缺失 → 三个 StaticPenalty 均置满(各 20)→ 三个静态项 = 0。

---

## 7. 报告格式（扩展，按子特性 + 分层）

`out/<repo>/07_portability/run_report.<candidate_id>.json`:

```json
{
  "mode": "iso_aligned_unified_eval_image",
  "candidate_id": "codex_run_001",
  "bench_eval_image": "bench-eval-env:2026-06",
  "subcharacteristics": {
    "adaptability":   {"dynamic": 84.0, "static_penalty": 6, "static": 70, "score": 75.9},
    "installability": {"dynamic": 100.0,"static_penalty": 3, "static": 85, "score": 97.75},
    "replaceability": {"dynamic": 92.0, "static_penalty": 5, "static": 75, "score": 89.45, "note": "borrowed from functional"}
  },
  "profiles": [{"id":"P0_default","passed":80,"total":80,"score":100.0}, "..."],
  "static_scan": {
    "l2_mechanical_findings": 2,
    "l3_llm_findings": 1,
    "by_subcharacteristic": {"adaptability": 6, "installability": 3, "replaceability": 5}
  },
  "final": {
    "formula": "0.45*Adapt + 0.30*Install + 0.25*Replace",
    "PortabilityScore": 84.6
  }
}
```

`static_scan_report.<candidate_id>.json` 增加每条 finding 的 `layer`(mechanical | llm)、`subcharacteristic`、`confidence`(仅 llm)、`explanation`(模板或 LLM why)。

---

## 8. 最终定义

> 可移植性 = 候选仓库在 benchmark 统一评测镜像、受限依赖目录、五个受控 profile、现有 hidden tests 工作负载下,按 ISO 25010 的**适应性 / 可安装性 / 可替换性**三子特性表现出的:在不同/演变环境保持可运行(Adaptability)、能离线成功构建安装(Installability)、能作为原产品的行为 drop-in 替换(Replaceability)的能力,以及源码层避免环境绑定风险的能力。静态风险检测分两层:**可机械判定的用代码、需要语义判断的用 LLM**;两层产出的 finding 由代码按固定表与封顶统一扣分。
