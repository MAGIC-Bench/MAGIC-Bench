# code-bench-v2 数据集

**黑盒差分跨语言基准**:每道题取一个真实开源仓库(原语言 X),让多个 AI 编程 Agent **用另一种语言 Y 从零重写**,候选**看不到原仓源码**,只依据卷面给出的对外可观察行为契约实现;判卷为**黑盒差分**——把候选与"原仓跑出的 golden"在相同输入下对比。

## 目录结构(总包 = 出卷包 + agent 生成的仓库)

```
出卷包/                          ← 主数据集(出卷侧)
├── 卷面-考生包/<仓库>/
│   ├── candidate/               给候选的卷面:项目描述 / 用户API使用手册 / 功能模块文档 /
│   │                            用户行为示例 / 非功能需求 / prompt / 02_cli-contract.json /
│   │                            generation_language.txt(目标语言)
│   └── meta.json                {id, scenario_type, generation_language}
└── golden-评分标准/<仓库>/07_exam/  原仓 golden + 判分 grader(差分判卷用)

候选提交-各agent生成/<仓库>/<agent>/work/   各 Agent 生成的仓库源码(已去除构建产物/依赖缓存)

成绩/<仓库>/<agent>/score.json   每份提交的判分:build_ok / 功能分 / nfr_by_dimension(6 维 0/1/null)

元数据/
├── repo-list.manifest.json      原仓清单(语言/场景/star/tier/描述/推荐改写语言)
└── report-lang.json             权威语言映射:原语言 → 推荐改写语言排名

analyze.py                       分析脚本:读上述数据生成 report.html
report.html                      分析报告(浏览器直接打开,详尽)
```

## 重新生成报告

在本目录(解压后的根)运行:

```
python analyze.py
```

会读 `成绩/`、`出卷包/卷面-考生包/`、`候选提交-各agent生成/`、`元数据/`,重新生成 `report.html`。
（需 Python 3.8+,无第三方依赖。）

## Agent

`claude` / `codex` / `cursor` / `kimi` 为主测;`agy`(Antigravity / Gemini)因无稳定代理、网络受限,作为"被墙 Agent 基线"参考,不参与主排名。

## 重要说明

- **有效题数 81**:`dosisod-refurb` 的 grader 缺失(出题只到 baseline 阶段),无法判卷。
- 分数为**修复两个判卷 bug 后的真实分**(launch 路径 bug + cwd 竞态 bug);详见 `report.html` 第 ⑩ 节"方法学局限与已知问题"。
- 判卷**不校验候选语言**,故存在"克隆原仓糊弄"现象(详见报告第 ⑧ 节)。
