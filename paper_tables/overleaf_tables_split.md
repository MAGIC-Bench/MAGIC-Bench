# Overleaf 表格 LaTeX 代码

导言区需要加入：

```latex
\usepackage{booktabs}
```

## 表 1：源仓库语言分布

```latex
\begin{table}[t]
\centering
\caption{Source-language distribution of the final 81 MAGIC-Bench tasks.}
\label{tab:dataset-source-languages}
\begin{tabular}{lrr}
\toprule
Category & \#Tasks & Rate \\
\midrule
Rust & 25 & 30.86\% \\
Go & 14 & 17.28\% \\
Python & 11 & 13.58\% \\
JavaScript & 7 & 8.64\% \\
C++ & 5 & 6.17\% \\
Ruby & 3 & 3.70\% \\
TypeScript & 3 & 3.70\% \\
C & 3 & 3.70\% \\
C\# & 2 & 2.47\% \\
Java & 2 & 2.47\% \\
Perl & 1 & 1.23\% \\
Elixir & 1 & 1.23\% \\
Swift & 1 & 1.23\% \\
PHP & 1 & 1.23\% \\
Kotlin & 1 & 1.23\% \\
Shell & 1 & 1.23\% \\
\bottomrule
\end{tabular}
\end{table}
```

## 表 2：目标实现语言分布

```latex
\begin{table}[t]
\centering
\caption{Target implementation-language distribution of the final 81 MAGIC-Bench tasks.}
\label{tab:dataset-target-languages}
\begin{tabular}{lrr}
\toprule
Category & \#Tasks & Rate \\
\midrule
Go & 46 & 56.79\% \\
Rust & 22 & 27.16\% \\
Python & 11 & 13.58\% \\
Node & 1 & 1.23\% \\
TypeScript & 1 & 1.23\% \\
\bottomrule
\end{tabular}
\end{table}
```

## 表 3：场景分布

```latex
\begin{table}[t]
\centering
\caption{Scenario distribution of the final 81 MAGIC-Bench tasks.}
\label{tab:dataset-scenarios}
\begin{tabular}{lrr}
\toprule
Category & \#Tasks & Rate \\
\midrule
CLI tools & 35 & 43.21\% \\
Serialization / format & 25 & 30.86\% \\
Security / crypto & 10 & 12.35\% \\
Database / storage & 6 & 7.41\% \\
Web API & 5 & 6.17\% \\
\bottomrule
\end{tabular}
\end{table}
```

## 表 4：RQ1 静态 NFR 指标准确率

```latex
\begin{table*}[t]
\centering
\small
\caption{Accuracy of agent-judge static NFR metrics against manual validation.}
\label{tab:rq1-static-nfr-accuracy}
\begin{tabular}{llr}
\toprule
评估指标 & 指标含义 & 准确率 (Accuracy) \\
\midrule
SEC2 & 无敏感信息硬编码 & 98.3\% \\
CMP1 & 共享环境可启动，无硬编码端口或绝对路径写入 & 96.7\% \\
MTN1 & 无超大单文件 & 99.2\% \\
MTN2 & 无跨层反向依赖 & 96.4\% \\
MTN3 & 无循环依赖 & 97.1\% \\
MTN4 & 认知复杂度合规 & 95.8\% \\
MTN5 & README 文档完整 & 97.5\% \\
PTB2 & 无硬编码路径 & 96.1\% \\
PTB3 & 日志或缓存不写入源码目录 & 97.8\% \\
PTB4 & 文件、网络流或字节转换具有显式编码声明 & 95.6\% \\
PTB5 & 无环境变量强依赖，或提供默认值/清晰错误提示 & 96.9\% \\
PTB6 & 无平台专属 API 强绑定，或提供条件分支/fallback & 96.3\% \\
\bottomrule
\end{tabular}
\end{table*}
```

## 表 5：RQ2 主结果

```latex
\begin{table*}[t]
\centering
\small
\caption{RQ2 results by coding agent. FR is average requirement correctness over build-success projects; NFR dimensions use build-success corrected applicable-item pass rates.}
\label{tab:rq2-main-results}
\begin{tabular}{lrrrrrrrrrr}
\toprule
Agent & Build-ok & FR & Full-FR & Test pass & CMP & MTN & PERF & PTB & RLY & SEC \\
\midrule
Claude Code & 61 & 31.75\% & 5/61 (8.20\%) & 65.13\% & 3.28\% & 65.90\% & 77.05\% & 54.37\% & 72.78\% & 75.61\% \\
Codex & 59 & 23.94\% & 3/59 (5.08\%) & 56.88\% & 5.08\% & 70.85\% & 74.01\% & 63.84\% & 71.84\% & 82.05\% \\
Cursor & 57 & 38.37\% & 10/57 (17.54\%) & 67.79\% & 7.02\% & 65.96\% & 79.41\% & 56.43\% & 77.51\% & 78.75\% \\
Kimi & 57 & 31.05\% & 6/57 (10.53\%) & 61.82\% & 1.92\% & 66.54\% & 80.70\% & 57.73\% & 76.79\% & 78.08\% \\
\bottomrule
\end{tabular}
\end{table*}
```

## 表 6：功能结果细表

```latex
\begin{table*}[t]
\centering
\small
\caption{Functional results under the build-success denominator.}
\label{tab:rq2-functional-details}
\begin{tabular}{lrrrrrr}
\toprule
Agent & Build-ok projects & Avg. requirement correctness & Passed tests / total & Test pass rate & Full-FR projects & Full-FR rate \\
\midrule
Claude Code & 61 & 31.75\% & 3443/5286 & 65.13\% & 5/61 & 8.20\% \\
Codex & 59 & 23.94\% & 2867/5040 & 56.88\% & 3/59 & 5.08\% \\
Cursor & 57 & 38.37\% & 3232/4768 & 67.79\% & 10/57 & 17.54\% \\
Kimi & 57 & 31.05\% & 3028/4898 & 61.82\% & 6/57 & 10.53\% \\
\bottomrule
\end{tabular}
\end{table*}
```

## 表 7：NFR 总体通过率

```latex
\begin{table}[t]
\centering
\caption{Overall NFR pass rates after excluding build-failed submissions from NFR denominators.}
\label{tab:nfr-overall-corrected}
\begin{tabular}{lrr}
\toprule
Dimension & Passed / applicable & Pass rate \\
\midrule
CMP (Compatibility) & 10/229 & 4.37\% \\
MTN (Maintainability) & 771/1145 & 67.34\% \\
PERF (Performance efficiency) & 545/701 & 77.75\% \\
PTB (Portability/buildability) & 801/1379 & 58.09\% \\
RLY (Reliability) & 516/691 & 74.67\% \\
SEC (Security) & 246/313 & 78.59\% \\
\bottomrule
\end{tabular}
\end{table}
```

## 表 8：CLI 接口符合度

```latex
\begin{table*}[t]
\centering
\small
\caption{CLI interface compliance under the build-success denominator. The main metric is project-level full compliance.}
\label{tab:cli-interface-compliance}
\begin{tabular}{lrrrrr}
\toprule
Agent & Build-ok projects & Fully compliant projects & Project-level full compliance & Probe pass rate & Avg. project probe pass \\
\midrule
Claude Code & 61 & 20/61 & 32.79\% & 1592/2777 (57.33\%) & 63.94\% \\
Codex & 59 & 23/59 & 38.98\% & 1612/2577 (62.55\%) & 71.39\% \\
Cursor & 57 & 14/57 & 24.56\% & 1449/2724 (53.19\%) & 65.54\% \\
Kimi & 57 & 16/57 & 28.07\% & 1437/2577 (55.76\%) & 63.07\% \\
Main total & 234 & 73/234 & 31.20\% & 6090/10655 (57.16\%) & -- \\
\bottomrule
\end{tabular}
\end{table*}
```

## 表 9：RQ3 维度级失败率

```latex
\begin{table}[t]
\centering
\caption{RQ3 dimension-level NFR failure rates. Only build-success submissions are included; null or non-applicable metrics are excluded.}
\label{tab:rq3-dimension-failures}
\begin{tabular}{lrr}
\toprule
Dimension & Failed / applicable & Failure rate \\
\midrule
CMP (Compatibility) & 380/463 & 82.07\% \\
PTB (Portability/buildability) & 578/1379 & 41.91\% \\
MTN (Maintainability) & 374/1145 & 32.66\% \\
RLY (Reliability) & 175/691 & 25.33\% \\
PERF (Performance efficiency) & 156/701 & 22.25\% \\
SEC (Security) & 67/313 & 21.41\% \\
\bottomrule
\end{tabular}
\end{table}
```

## 表 10：RQ3 高频 NFR 失败指标

```latex
\begin{table*}[t]
\centering
\small
\caption{Top NFR failure signals in RQ3. Only build-success submissions are included.}
\label{tab:rq3-top-nfr-failures}
\begin{tabular}{rlllrr}
\toprule
Rank & Dimension & Metric & Failure signal & Failed / applicable & Failure rate \\
\midrule
1 & PTB & PTB.PTB2 & No hard-coded paths & 226/229 & 98.69\% \\
2 & CMP & CMP.CMP1 & Shared-environment startup & 219/229 & 95.63\% \\
3 & MTN & MTN.MTN4 & Cognitive complexity within threshold & 170/229 & 74.24\% \\
4 & RLY & RLY.RLY1 & Long/repeated execution without failure & 170/234 & 72.65\% \\
5 & PTB & PTB.PTB4 & Explicit text encoding & 168/229 & 73.36\% \\
6 & CMP & CMP.CLI & Complete CLI contract compliance & 161/234 & 68.80\% \\
7 & MTN & MTN.MTN1 & No oversized single file & 132/229 & 57.64\% \\
8 & PERF & PERF.PERF4 & Timed correct pass & 124/234 & 52.99\% \\
9 & PTB & PTB.PTB6 & No platform-specific binding & 100/229 & 43.67\% \\
10 & PTB & PTB.PTB3 & No logs/cache in source tree & 65/229 & 28.38\% \\
\bottomrule
\end{tabular}
\end{table*}
```
