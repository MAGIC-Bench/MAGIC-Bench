# 按原文占位对齐的 Overleaf 表格

导言区需要：

```latex
\usepackage{booktabs}
\usepackage{tabularx}
```

说明：原文中“语言分布”是图，不在这里生成表；“方法框架图”也不在这里生成。

## 表 3.1：评估维度及定义

```latex
\begin{table*}[t]
\centering
\small
\caption{MAGIC-Bench non-functional quality dimensions and metric groups.}
\label{tab:quality-dimensions}
\begin{tabularx}{\textwidth}{l l X}
\toprule
Dimension & Abbr. & Definition and metric group \\
\midrule
Security & SEC & Measures whether generated projects protect data and system resources, including unauthorized read/write blocking, hard-coded secret detection, sensitive-field encryption, SQL-injection defense, and audit logging. \\
Compatibility & CMP & Measures whether generated projects can run in shared environments and conform to exposed interface contracts, including environment-safe startup and CLI/API contract compliance. \\
Reliability & RLY & Measures whether generated projects remain stable under repeated execution, restart, dependency failure, resource pressure, concurrent requests, and forced termination. \\
Maintainability & MTN & Measures whether generated projects are easy to understand and evolve, including oversized-file checks, reverse-dependency checks, cycle detection, cognitive complexity, and README completeness. \\
Performance efficiency & PERF & Measures runtime efficiency and stability, including crashes/OOM/timeouts, tail-latency stability, memory use, and timed correct execution. \\
Portability/buildability & PTB & Measures whether generated projects can be built and moved across environments, including build manifests, path handling, log/cache location, explicit encoding, environment-variable defaults, and platform-specific API use. \\
\bottomrule
\end{tabularx}
\end{table*}
```

## 表 3.2：五大场景比例

```latex
\begin{table}[t]
\centering
\caption{Scenario distribution of the final 81 MAGIC-Bench tasks.}
\label{tab:dataset-scenarios}
\begin{tabular}{lrr}
\toprule
Scenario & \#Tasks & Rate \\
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

## 表 5.1：RQ1 静态 NFR 指标准确率

```latex
\begin{table*}[t]
\centering
\small
\caption{Accuracy of agent-judge static NFR metrics against manual validation.}
\label{tab:rq1-static-nfr-accuracy}
\begin{tabularx}{\textwidth}{l X r}
\toprule
Metric & Meaning & Accuracy \\
\midrule
SEC2 & No hard-coded sensitive information & 98.3\% \\
CMP1 & Shared-environment startup without hard-coded ports or absolute-path writes & 96.7\% \\
MTN1 & No oversized single file & 99.2\% \\
MTN2 & No cross-layer reverse dependency & 96.4\% \\
MTN3 & No circular dependency & 97.1\% \\
MTN4 & Cognitive complexity within threshold & 95.8\% \\
MTN5 & Complete README documentation & 97.5\% \\
PTB2 & No hard-coded paths & 96.1\% \\
PTB3 & Logs or caches are not written into the source tree & 97.8\% \\
PTB4 & Explicit encoding for files, network streams, or byte conversion & 95.6\% \\
PTB5 & No strong environment-variable dependency, or defaults/clear errors are provided & 96.9\% \\
PTB6 & No platform-specific API binding, or conditional branches/fallbacks are provided & 96.3\% \\
\bottomrule
\end{tabularx}
\end{table*}
```

## 表 5.2：RQ2 总体结果

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

## 表 5.3：RQ3 高频 NFR 失败指标

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
1 & PTB & PTB2 & No hard-coded paths & 226/229 & 98.69\% \\
2 & CMP & CMP1 & Shared-environment startup & 219/229 & 95.63\% \\
3 & MTN & MTN4 & Cognitive complexity within threshold & 170/229 & 74.24\% \\
4 & RLY & RLY1 & Long/repeated execution without failure & 170/234 & 72.65\% \\
5 & PTB & PTB4 & Explicit text encoding & 168/229 & 73.36\% \\
6 & CMP & CLI & Complete CLI contract compliance & 161/234 & 68.80\% \\
7 & MTN & MTN1 & No oversized single file & 132/229 & 57.64\% \\
8 & PERF & PERF4 & Timed correct pass & 124/234 & 52.99\% \\
9 & PTB & PTB6 & No platform-specific binding & 100/229 & 43.67\% \\
10 & PTB & PTB3 & No logs/cache in source tree & 65/229 & 28.38\% \\
\bottomrule
\end{tabular}
\end{table*}
```

## 表 5.4：兼容性失败数统计

```latex
\begin{table}[t]
\centering
\caption{Compatibility failure statistics on build-success submissions.}
\label{tab:rq3-cmp-failures}
\begin{tabular}{l l rr}
\toprule
Metric & Failure signal & Failed / applicable & Failure rate \\
\midrule
CMP1 & Shared-environment startup & 219/229 & 95.63\% \\
CLI & Complete CLI contract compliance & 161/234 & 68.80\% \\
\bottomrule
\end{tabular}
\end{table}
```

## 表 5.5：可维护性失败数统计

```latex
\begin{table}[t]
\centering
\caption{Maintainability failure statistics on build-success submissions.}
\label{tab:rq3-mtn-failures}
\begin{tabular}{l l rr}
\toprule
Metric & Failure signal & Failed / applicable & Failure rate \\
\midrule
MTN4 & Cognitive complexity within threshold & 170/229 & 74.24\% \\
MTN1 & No oversized single file & 132/229 & 57.64\% \\
MTN5 & Complete README documentation & 34/229 & 14.85\% \\
MTN3 & No circular dependency & 20/229 & 8.73\% \\
MTN2 & No cross-layer reverse dependency & 18/229 & 7.86\% \\
\bottomrule
\end{tabular}
\end{table}
```

## 表 5.6：性能效率失败数统计

```latex
\begin{table}[t]
\centering
\caption{Performance-efficiency failure statistics on build-success submissions.}
\label{tab:rq3-perf-failures}
\begin{tabular}{l l rr}
\toprule
Metric & Failure signal & Failed / applicable & Failure rate \\
\midrule
PERF4 & Timed correct pass & 124/234 & 52.99\% \\
PERF2 & Stable tail latency & 31/233 & 13.30\% \\
PERF1 & No crash/OOM/timeout & 1/234 & 0.43\% \\
\bottomrule
\end{tabular}
\end{table}
```

## 表 5.7：可移植性失败数统计

```latex
\begin{table}[t]
\centering
\caption{Portability/buildability failure statistics on build-success submissions.}
\label{tab:rq3-ptb-failures}
\begin{tabular}{l l rr}
\toprule
Metric & Failure signal & Failed / applicable & Failure rate \\
\midrule
PTB2 & No hard-coded paths & 226/229 & 98.69\% \\
PTB4 & Explicit text encoding & 168/229 & 73.36\% \\
PTB6 & No platform-specific binding & 100/229 & 43.67\% \\
PTB3 & No logs/cache in source tree & 65/229 & 28.38\% \\
PTB5 & No strong environment-variable dependency & 19/229 & 8.30\% \\
PTB1 & Standard build passes & 0/234 & 0.00\% \\
\bottomrule
\end{tabular}
\end{table}
```

## 表 5.8：安全性失败数统计

```latex
\begin{table}[t]
\centering
\caption{Security failure statistics on build-success submissions.}
\label{tab:rq3-sec-failures}
\begin{tabular}{l l rr}
\toprule
Metric & Failure signal & Failed / applicable & Failure rate \\
\midrule
SEC5 & SQL injection defense & 17/22 & 77.27\% \\
SEC1 & Unauthorized read blocked & 11/20 & 55.00\% \\
SEC4 & Unauthorized write blocked & 14/29 & 48.28\% \\
SEC3 & Sensitive fields encrypted & 6/13 & 46.15\% \\
SEC2 & No hard-coded secrets & 19/229 & 8.30\% \\
\bottomrule
\end{tabular}
\end{table}
```

## 表 5.9：可靠性失败数统计

```latex
\begin{table}[t]
\centering
\caption{Reliability failure statistics on build-success submissions.}
\label{tab:rq3-rly-failures}
\begin{tabular}{l l rr}
\toprule
Metric & Failure signal & Failed / applicable & Failure rate \\
\midrule
RLY1 & Long/repeated execution without failure & 170/234 & 72.65\% \\
RLY4 & Resource-pressure tolerance & 5/223 & 2.24\% \\
RLY5 & Concurrent execution without failure & 0/234 & 0.00\% \\
\bottomrule
\end{tabular}
\end{table}
```
