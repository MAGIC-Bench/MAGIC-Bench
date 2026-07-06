# 消融实验调研 + 我们可做的消融清单

> 目的:调研同类代码生成/SWE-agent 基准做过哪些消融(ablation),再从易到难列出我们这套"差分 oracle 重建基准"可以做的消融。日期:2026-06。

---

## 一、同类论文的消融实验调研

按"消融变量族"归类,每族给出代表论文做了什么、结论,以及和我们的关联。

### 1. 给候选的输入/上下文(context provided)
- **SWE-bench**(ICLR'24, arXiv:2310.06770):对"检索上下文"做消融——`oracle`(只给真实改动的文件/行 ±15 行)vs `BM25` 检索(13k/27k/40k token)。结论:**给 oracle 上下文分数上升**(GPT-4 1.3%→3.4%);**上下文越长反而越差**(模型不擅长在长上下文里定位)。
- **Agentless**(FSE'25, arXiv:2407.01489):对"定位粒度"消融——file / function / line。结论:**function 级定位的修复率最高**。

启示:**"给候选多少 spec"是一个标准消融维度**(我们对应:契约-only vs +用户故事 vs +NFR)。

### 2. agent 脚手架(scaffold / agent-computer interface)
- **SWE-agent**(NeurIPS'24, arXiv:2405.15793):对 ACI 组件消融(在 300 题子集上)。结论:**精心设计的 ACI 比裸 Linux shell 多解 +10.7 个百分点**;其中**上下文管理 + 错误护栏**贡献最大。

启示:**脚手架/工具集本身是变量**(我们对应:codex vs claude、full-auto vs 受限工具、给不给执行反馈)。

### 3. 测试时计算(test-time compute)
- **Scaling Test-Time Compute for Agentic Coding**(arXiv:2604.16529):多尝试 + 并行/串行扩展(Recursive Tournament Voting、Parallel-Distill-Refine)。结论:**允许更多尝试一致提升通过率**(o1 多 6 次尝试通过率近 3 倍);Claude-4.5-Opus 在 SWE-bench Verified 70.9%→77.6%。并区分 **pass@k(至少成功一次,偏乐观)vs pass^k(k 次全成功,衡量可靠性)**。

启示:**尝试次数 / pass@k vs pass^k 是衡量"能力 vs 可靠性"的关键消融**。

### 4. 反记忆 / 跨语言(anti-memorization)
- **ProgramBench**(arXiv:2605.03546,我们的直接参照):**§4.1 强制用与原仓不同的语言重写** → 绕过记忆/背题。结论:跨语言设置能有效压制 memorization 带来的虚高。

启示:**这正是我们纠结的"跨语言重写";它在参照论文里就是一个核心消融**(同语言 vs 跨语言)。

### 5. 网络访问(internet access)
- **ProgramBench**:**允许联网 vs 断网**的消融。结论:**联网导致大量作弊,需要 LM-as-judge 标记并取消资格;但除作弊样本外,联网并不显著提分**。

启示:**这正是我们纠结的"agent 全程联网"问题;参照论文的实测结论是"联网 ≈ 作弊放大器,而非能力提升"** —— 支持我们"联网必须配出口白名单 + 作弊检测"的设计。

### 6. 基准有效性自审(benchmark validity)
- **SWE-bench+ / "Why we no longer evaluate SWE-bench Verified"**(arXiv:2410.06992;OpenAI 博文):
  - **弱测试**:约 **31% 通过的补丁其实是测试套件太弱放过的**(语义错却"看起来对");TestEnhancer 补强测试后,top 模型解决率**平均下降约 36 个百分点**。
  - **答案泄漏 / 污染**:SWE-bench Verified 约 **22.6% 的题存在答案泄漏**(issue 文本/评论里有提示或解法);94%+ 的题早于模型知识截止 → 记忆风险。
  - **只跑改动过的测试**:导致通过率**被高估 4–7 个百分点**(漏掉回归)。

启示:**"测试套件强度 / 污染 / 跑全 vs 跑部分测试"是基准自审型消融** —— 直接对应我们 pilot 发现的 grype 弱卷、cisco 坏题、以及"只验 exit code"的问题。

---

## 二、我们可做的消融实验(从易到难)

格式:**变量 | 回答什么 | 成本 | 需要的改动 | 对应先例**。

### A. 容易(改配置/重算分,复用现有卷,基本不加基建)

**E1. 网络:断网 vs 联网+白名单代理**
- 回答:联网到底带来"能力提升"还是"作弊放大"?(我们最纠结的决策)
- 成本:低(每候选 2 跑)。改动:网络开关 + 一个作弊检测(候选↔原仓相似度,或 LLM-judge)。先例:ProgramBench internet 消融。

**E2. 题面丰富度:契约-only vs +用户故事 vs +NFR**
- 回答:给候选更多 spec 是否真的帮它(还是噪声)?
- 成本:低(改 SPEC 拷贝集,1 跑/档)。改动:`candidate.generate` 只拷不同子集。先例:SWE-bench oracle-context。

**E3. 测试时计算:pass@1 vs pass@k / pass^k**
- 回答:模型是"能力强"还是"靠运气多试"?可靠性如何?
- 成本:中(k× 跑同候选)。改动:重复跑 + 统计。先例:Scaling Test-Time Compute。

**E4. 候选模型 / 脚手架:同卷换模型、full-auto vs 受限工具**
- 回答:分差来自模型还是脚手架?(leaderboard 主轴)
- 成本:低-中(按模型数)。改动:`client.py` 切引擎/旗标。先例:SWE-agent ACI。

### B. 中等(改 prompt 或重算分,需捕获候选输出)

**M1. 同语言 vs 跨语言重写**
- 回答:分数里有多少是"背题/记忆"?跨语言能压多少虚高?
- 成本:中(2 跑/候选 + candidate.md 加语言约束)。先例:ProgramBench §4.1。

**M2. 断言紧度:现状断言 vs "内容断言门"重算**
- 回答:把"只验 exit code"收紧到"必须验 stdout 内容"后,分数/区分度变化多少?(量化 grype 型弱卷的影响)
- 成本:中(需先**捕获候选每题输出**,再用两套断言重算)。先例:SWE-bench+ 弱测试 / TestEnhancer。

**M3. 维度贡献:functional-only vs +perf vs +portability vs 全 7 维**
- 回答:每个维度对最终排名的边际贡献;哪些维度其实不改变排序(冗余)?
- 成本:低-中(各维度都跑过后重聚合)。改动:重算分。先例:多目标基准常见。

**M4. 测试数量:每模块 quota 20 → 10 → 5 子采样**
- 回答:分数对"每模块多少题"是否稳定?20 是不是过/不足?
- 成本:低(子集重算)。改动:聚合脚本。先例:基准稳定性分析。

**M5. 仓库档位:tier1(非常适合 oracle)vs tier2(较适合)**
- 回答:oracle 适配度低的仓,是否分数方差更大/更不可靠?(验证预筛分档的必要性)
- 成本:低(加档位标签 + 分组对比)。改动:接预筛 tier。先例:SWE-bench Lite/Verified 子集对比。

### C. 困难(需要新机制 / 大量运行)

**H1. 测试集强度:废物候选必须被拒 + 紧度↔区分度相关性**
- 回答:我们的卷能不能识别错实现?哪些卷是"高数量低区分度"?
- 成本:高(需"区分度关"基建,即问题清单 #4)。先例:SWE-bench+ TestEnhancer。

**H2. 确定性/环境处理:单冻 vs 双跑 vs 扰动-env 三跑**
- 回答:有多少 golden 是非确定/环境依赖的(不可靠)?扰动-env 能多揪出多少?
- 成本:高(需扰动-env 运行基建,即问题清单 #6)。先例:无直接先例(我们的贡献点)。

**H3. 依赖供给:离线 catalog vs 在线代理**
- 回答:两种供给对构建成功率/可复现/公平性的影响。
- 成本:高(两条基建都要)。先例:无直接先例。

**H4. 全跨语言矩阵:每仓在 N 种语言各重写一遍**
- 回答:同一题在不同目标语言下分数是否公平可比?(perf 的语言偏置实测)
- 成本:很高(N× 候选跑)。先例:ProgramBench 跨语言的加强版。

**H5. 作弊量化:联网下候选↔原仓相似度 / LLM-judge 标作弊比例**
- 回答:联网到底有多少分是抄来的?
- 成本:高(相似度/judge 基建)。先例:ProgramBench(需 LM-judge 取消资格)。

**H6. 人工核验子集(SWE-bench Verified 类)**
- 回答:人工筛掉坏题后,raw 卷 vs verified 子集的分数差多少?(基准有效性上界)
- 成本:高(人工标注)。先例:SWE-bench Verified。

---

## 三、建议优先级

先做**直接验证你正在纠结的设计决策、且成本低**的四个:

1. **E1 网络(断网 vs 联网+代理)** —— 参照论文结论是"联网≈作弊放大",自己复现一遍最有说服力。
2. **M1 同语言 vs 跨语言** —— 量化记忆成分,决定要不要强制跨语言。
3. **E2 题面丰富度** —— 决定 SPEC 给到哪一层。
4. **M3 维度贡献** —— 看 7 维里哪些真有信息量、哪些冗余。

H1/H2 虽难,但它们正是 pilot 暴露的核心质量问题(弱卷、非确定/环境依赖),做出来既是消融、也是基准质量的"卖点"和论文贡献。

---

## 四、补充调研:更贴近我们的工作(项目级构建 + 非 LLM 构造/修复)

### A. 项目级"从零构建"基准(最像我们)
- **Commit0**(arXiv:2412.01769)——"从零写库":给 API spec + 交互式单测,agent 实现到过测,54 个 Python 库。**消融做的是"反馈通道"**:交互式反馈(尤其单测执行)**稳定提分**;**静态分析反馈效果含糊甚至有害**(尤其开源模型);结论是**单测反馈 + import 上下文最有用**。→ 启示:"给候选哪些反馈通道"是一条标准消融。
- **DevBench**(arXiv:2403.08604)——全 SDLC **分阶段**评测(设计 / 环境搭建 / 实现 / 验收测试 / 单测),22 仓 × 4 语言。做法是**每阶段单独评分**(= 阶段级拆解,定位瓶颈);GPT-4-Turbo 仓库级实现 <10%。→ 启示:"按阶段/维度拆贡献"(强化我们的 M3)。

### B. 非 LLM 的构造/修复(generate-and-validate)——以及它最值钱的方法论
这一支是经典**自动程序修复(APR)/遗传编程(GP)**,即非 LLM 的"自动构造"代表(GenProg 等)。它们的消融惯例:
- **故障定位质量**(改哪些语句)、**适应度函数**(过测数加权;消除 plateau 的更细 fitness)、**遗传算子**(Operator/Fault/Fix 子空间)、**搜索预算**。
- **最值钱的一条:测试集充分性 vs 过拟合(overfitting)** —— 直接对应你的"弱卷放过错实现":
  - **Smith et al. 2015《Is the Cure Worse Than the Disease?》**:用**留出测试集(held-out tests,修复时没用过)**评估补丁;GenProg 等补丁在留出测试上通过率显著低于人写补丁 → **过拟合**(过了输入测试集、但语义错)。这就是 grype 弱卷问题在 APR 界的标准刻画。
  - **Lim 2020《Impact of Test Suite Coverage on Overfitting in GP》**:**消融测试集覆盖率/规模 → 量化过拟合率**。正是可照搬的消融(改 #tests → 看漏判变化)。
  - LLM-APR 过拟合(arXiv:2511.16858):过拟合率约 5.8% / 11.3%(Claude / GPT-4o)。

**核心可迁移方法论:held-out / 过拟合度量。** 把"评测卷"和"独立留出卷"分开——候选过了评测卷、却在留出卷上挂 = "对卷过拟合"。它**同时量化卷的强度和候选的真实性**,比单纯 mutation 更标准、更有说服力,也是相对 ProgramBench 的差异化贡献点。

## 五、由此新增的消融项(并入易→难清单)

- **E5(易/中)反馈通道消融**:给候选 0 反馈 / 仅编译错误 / + 部分测试执行反馈 → 提分几何?(对应 Commit0)
- **M6(中)阶段·维度瓶颈拆解**:按"构建成功 / 功能 / perf / portability / …"逐段拆分数,看瓶颈与冗余(对应 DevBench 分阶段,强化 M3)。
- **H7(中/难)留出测试过拟合度量**:除评测卷外,独立再生成一批 held-out 输入+golden;报告候选"评测卷分 − 留出卷分"= 过拟合 gap;并消融"每模块测试数 → 过拟合 gap"。**把你的 #4 区分度门升级成 APR 界公认的强度度量。**(对应 Smith 2015 / Lim 2020)

---

## 六、近邻论文消融详表(从零 / 从 spec / 项目级构建 —— 这才是我们的参照系)

> §一的 SWE-bench / SWE-agent / Agentless 属于"在已有仓里改 bug"的**问题修补类**,离我们较远,只作方法学借鉴。下面是"**从 spec/文档从零造出整段程序、用行为测试判分**",才是真正的同类。每条给:设定有多近 · 消融做了啥 · 结论 · 对我们的启示。

**1. ProgramBench**(arXiv:2605.03546,已在 §一/§三)——最直接同类。消融:**跨语言重写**(反记忆)、**联网 vs 断网**(联网≈作弊放大,非提分)。

**2. Commit0**(arXiv:2412.01769,已在 §四A)——从零写库。消融:**反馈通道**(单测执行反馈有用;静态分析反馈含糊甚至有害;单测+import 上下文最有用)。

**3. DevBench**(arXiv:2403.08604,已在 §四A)——全 SDLC **分阶段**评分,定位瓶颈(repo 级实现 <10%)。

**4. AlphaCode**(arXiv:2203.07814)——从题面生成**整个程序**:大规模采样 → 样例测试过滤 → 行为聚类选 ≤10 份提交。消融:**① 采样预算**(每题最多 1M,解率随样本数对数增长)·**② 测试过滤**(样例测试去掉 ~99% 样本)·**③ 行为聚类选择**(另训一个"按题面生成输入"的模型,按"对相同输入是否同输出"聚类,选大簇)·**④ 模型规模/集成**(300M→41B);五项增强合计 10@100k 15.2%→24.1%。**启示**:采样预算 / 测试过滤 / **行为聚类**是 whole-program 生成的核心消融;行为聚类 = 用生成输入区分行为,**和我们差分 oracle 同源**。

**5. AlphaCodium**(arXiv:2401.08500)——题面 → 整程序,走**测试驱动多阶段 flow**(问题反思 → 推理公开测试 → AI 造额外测试 → 生成 → 跑 → 修),pass@5 19%→44%。消融:**逐 flow 阶段开关**;关键发现**"造测试比写对代码容易"**。**启示**:flow/反馈阶段逐个消融(= 我们 E5);且其前提正支持差分 oracle(我们替模型把 golden 也生成了)。

**6. ClassEval**(arXiv:2308.01861)——类级 spec → **整个类**(多方法协同),手工 100 题。消融:**生成策略** holistic(一次产整类)vs incremental(逐方法、看前文)vs compositional(逐方法、独立后拼)。结论:**强模型 holistic 最好,弱模型逐方法更好**。**启示**:"整体 vs 分块构建"是一条消融(候选一次产整项目 vs 按模块/契约分块产)。

**7. EvoCodeBench / DevEval**(arXiv:2410.22821 等)——真实仓库按需求生成代码(带依赖)。重点:**EvoCodeBench 用"演进式/定期更新"反数据泄漏**;指标除 Pass@k 还有 **Recall@k(依赖召回)**;DevEval 为开发者标注、1874 样本/117 仓。**启示**:**反污染(时间演进/定期换题)+ "依赖用对没有"的召回指标**,对应我们对 memorization 与依赖选择的关注。

**由此再加两条消融(并入易→难清单):**
- **E6(易/中)生成粒度**:候选一次性产整项目 vs 按模块/契约分块产(对应 ClassEval)。
- **M7(中)选择策略**:单样本 vs best-of-N + **行为聚类选择**(对应 AlphaCode;聚类正好复用我们差分 oracle 的输入)。

---

## Sources
- SWE-bench — https://arxiv.org/pdf/2310.06770
- SWE-agent (ACI) — https://arxiv.org/abs/2405.15793
- Agentless — https://arxiv.org/abs/2407.01489
- ProgramBench — https://arxiv.org/abs/2605.03546
- Scaling Test-Time Compute for Agentic Coding — https://arxiv.org/abs/2604.16529
- SWE-bench+ (weak tests / leakage) — https://arxiv.org/pdf/2410.06992
- OpenAI: Why we no longer evaluate SWE-bench Verified — https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/
- Commit0: Library Generation from Scratch — https://arxiv.org/abs/2412.01769
- DevBench: A Comprehensive Benchmark for Software Development — https://arxiv.org/html/2403.08604v1
- Smith et al. 2015, Is the Cure Worse Than the Disease? (APR overfitting) — https://people.cs.umass.edu/~brun/pubs/pubs/Smith15fse.pdf
- Lim 2020, Impact of Test Suite Coverage on Overfitting in GP — http://www0.cs.ucl.ac.uk/staff/J.Petke/papers/Lim_2020_SSBSE_RENE.pdf
- Is the Cure Still Worse? Test Overfitting by LLMs in APR — https://arxiv.org/html/2511.16858v1
- GenProg: A Generic Method for Automatic Software Repair — https://roars.dev/pubs/le2011genprog.pdf
- AlphaCode: Competition-Level Code Generation — https://arxiv.org/abs/2203.07814
- AlphaCodium: From Prompt Engineering to Flow Engineering — https://arxiv.org/abs/2401.08500
- ClassEval: Class-level Code Generation benchmark — https://arxiv.org/abs/2308.01861
- EvoCodeBench: Evolving repo-level code generation benchmark — https://arxiv.org/pdf/2410.22821
