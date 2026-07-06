# 论文图表插入位置与文字修改建议

这份 notes 按当前 LaTeX 附件检查。结论先说清楚：

- 图只有两个：方法框架图、语言分布饼图。
- 表格按 `paper_tables/outline_aligned_tables.md` 使用。
- 当前正文里有几处 `Table X`、重复语言分布图、错误的源语言表、旧版 RQ2 假数据表，需要改。

## 0. 导言区需要补包

当前导言区已有 `graphicx`，但表格使用了 `booktabs`、`tabularx`，RQ1 的 `enumerate[label=...]` 还需要 `enumitem`。

```latex
\usepackage{booktabs}
\usepackage{tabularx}
\usepackage{enumitem}
```

## 1. Introduction：加入方法框架图引用

当前正文说了框架流程，但没有引用方法框架图。建议在 Introduction 中介绍 MAGIC-Bench 的段落之后插入方法框架图，并在前一句显式引用。

位置：Introduction 中这段之后：

```latex
We have implemented this framework as \textit{MAGIC-Bench}, ...
```

建议把段落末尾改成：

```latex
Figure~\ref{fig:framework} summarizes the overall workflow, from source-hidden task construction to black-box functional testing and multidimensional quality assessment.
```

方法框架图占位：

```latex
\begin{figure*}[t]
    \centering
    \includegraphics[width=0.95\textwidth]{figs/framework.pdf}
    \caption{Overview of the MAGIC-Bench construction and evaluation workflow.}
    \label{fig:framework}
\end{figure*}
```

注意：当前 LaTeX 在 Related Work 后面有一个 `figs/2.jpg`，caption 写的是语言分布。这个位置不对。如果 `figs/2.jpg` 是你们的方法框架图，就把 caption 和 label 改成上面的；如果不是，就删除这一整个 figure。

## 2. Related Work 后的语言分布图要删除或改成框架图

当前附件第 95 行附近：

```latex
\begin{figure*}[htbp]
    \centering
    \includegraphics[width=0.95\textwidth]{figs/2.jpg}
    \caption{Distribution of source repository languages and target translation languages across all 81 tasks.}
    \label{fig:lang-distribution}
\end{figure*}
```

问题：

- 它放在 Related Work 后面，位置不符合正文逻辑。
- 后面 Benchmark Statistics 又放了一张语言分布图，重复。
- label `fig:lang-distribution` 和后面的 `fig:lang_distribution` 语义重复。

处理：

- 如果这是方法框架图：改成 `fig:framework`，caption 改为方法框架，并移动到 Introduction 或 MAGIC-Bench 开头。
- 如果不是方法框架图：整段删除。

## 3. Section 3.2.4：质量维度表前后文字要引用表

当前表 `tab:quality-dimensions` 已经插入，但正文后面还写 `Table X`。

把这句：

```latex
The mapping relationship between the dimension classifications and specific evaluation methods is detailed in Table X.
```

改成：

```latex
Table~\ref{tab:quality-dimensions} summarizes the six automated non-functional dimensions and the metric groups used to operationalize them. The mapping relationship between these dimension classifications and concrete checks is then instantiated by the metric-specific graders.
```

另外，表已经放在 3.2.4 开头，正文可以在表前加一句引导：

```latex
The resulting non-functional dimensions are summarized in Table~\ref{tab:quality-dimensions}.
```

## 4. Section 3.3：语言分布图只保留一张，并在文字中引用

当前 3.3 有语言分布图 `figs/1.png`，这是对的，但文字没有引用图。

把这一句：

```latex
This section details the statistical characteristics of the benchmark from two dimensions: programming language distribution and application scenarios.
```

改成：

```latex
This section details the statistical characteristics of the benchmark from two perspectives: programming language distribution, shown in Figure~\ref{fig:lang_distribution}, and application scenarios, summarized in Table~\ref{tab:dataset-scenarios}.
```

当前语言图可以保留：

```latex
\begin{figure}[htbp]
    \centering
    \includegraphics[width=0.95\linewidth]{figs/1.png}
    \caption{Distribution of source repository languages and target implementation languages across all 81 tasks.}
    \label{fig:lang_distribution}
\end{figure}
```

建议 caption 里把 `translation languages` 改成 `target implementation languages`，更贴合任务。

## 5. Section 3.3：删除源语言分布表

当前第 235 行附近插入了：

```latex
\caption{Source-language distribution of the final 81 MAGIC-Bench tasks.}
\label{tab:dataset-source-languages}
```

这张表应删除。原文这里要求的是：

- `[图 语言分布的饼状图]`
- `[表 5大场景的比例表]`

所以语言分布只保留图，不要再放源语言表或目标语言表。

## 6. Section 3.3：加入五大场景比例表，并替换 Table X

当前有：

```latex
As presented in Table X, the task instances within the benchmark comprehensively cover 5 core application scenarios.
```

改成：

```latex
As shown in Table~\ref{tab:dataset-scenarios}, the task instances cover five core application scenarios. CLI tools form the largest group, followed by serialization and format-processing tasks, while security/crypto, database/storage, and Web API tasks provide more specialized engineering settings.
```

然后插入 `paper_tables/outline_aligned_tables.md` 里的“表 3.2：五大场景比例”。

## 7. RQ1：需要加入表 5.1，并让文字显式指向表

当前 RQ1 最后一段只说计算 accuracy 和 Cohen's Kappa，没有表。

建议改成：

```latex
By comparing the automated framework's outputs against this human-verified Golden Dataset, we calculate the accuracy of each static NFR metric. Table~\ref{tab:rq1-static-nfr-accuracy} reports the resulting accuracy values. Across the 12 inspected static indicators, the judge achieves consistently high agreement with the human-verified labels, with all metric-level accuracies above 95\%.
```

然后插入 `paper_tables/outline_aligned_tables.md` 的“表 5.1：RQ1 静态 NFR 指标准确率”。

注意：如果正文没有真的报告 Cohen's Kappa 数值，就先不要写 `and Cohen's Kappa`，否则会被审稿人抓住。

## 8. RQ2：当前表是旧假数据，必须替换

当前 `tab:rq2_results` 中的数据是旧的：

```latex
Functional Suitability & 27.00 ...
Full-Pass Projects & 14 ...
```

这和我们最新结果不一致。整张表替换为 `paper_tables/outline_aligned_tables.md` 的“表 5.2：RQ2 总体结果”。

同时，RQ2 正文里的数字也要改：

当前：

```latex
Cursor ... achieving the highest $AvgReqAcc$ (27\%) ...
```

改成：

```latex
Cursor achieves the highest average requirement correctness (38.37\%) and the highest full-FR rate, with 10 out of 57 build-success projects passing all functional requirements.
```

当前：

```latex
Kimi Code and Claude Code follow closely...
```

建议改成：

```latex
Claude Code and Kimi follow with similar average requirement correctness values (31.75\% and 31.05\%, respectively), while Codex obtains the lowest functional score (23.94\%).
```

当前：

```latex
Codex ... achieves superior pass rates in several non-functional dimensions (e.g., Security and Maintainability).
```

可以保留，但更精确：

```latex
Codex, despite its weaker functional score, obtains the highest pass rates in maintainability (70.85\%), portability/buildability (63.84\%), and security (82.05\%).
```

## 9. RQ2：表引用 label 要统一

你当前正文引用：

```latex
Table~\ref{tab:rq2_results}
```

而我们生成的表 label 是：

```latex
\label{tab:rq2-main-results}
```

二选一统一即可。建议保留正文现有 label，最省事：

```latex
\label{tab:rq2_results}
```

也就是把新表里的 label 改成 `tab:rq2_results`。

## 10. RQ3：开头先引用总排序表

当前 RQ3 开头只说做了分析，但没有引用表。

建议把 RQ3 开头改成：

```latex
To understand why autonomous agents fail in project-level reconstruction, we aggregate 324 submissions from four subject agents and conduct a fine-grained error analysis across the seven quality dimensions of \textit{MAGIC-Bench}. Table~\ref{tab:rq3-top-nfr-failures} ranks the most frequent NFR failure signals among build-success submissions.
```

然后插入 `paper_tables/outline_aligned_tables.md` 的“表 5.3：RQ3 高频 NFR 失败指标”。

## 11. RQ3：每个缺陷段落都要引用对应表

### Compatibility 段

当前段落数字是对的，但没有表引用。第一句改成：

```latex
As shown in Table~\ref{tab:rq3-cmp-failures}, among successfully built projects, the failure rate in Compatibility (CMP) is a staggering 82.07\%.
```

插入“表 5.4：兼容性失败数统计”。

### Maintainability 段

第一句改成：

```latex
Table~\ref{tab:rq3-mtn-failures} shows that maintainability defects remain prevalent, with a dimension-level failure rate of 32.66\%.
```

插入“表 5.5：可维护性失败数统计”。

另外当前写：

```latex
MTN5, 4.85\%
```

应改成：

```latex
MTN5, 14.85\%
```

### Performance 段缺失

当前 RQ3 没有性能效率段，但原文有 `[表 性能效率失败数统计]`。建议在 Maintainability 后加入：

```latex
\textbf{Performance-Efficiency Degradation.}
As shown in Table~\ref{tab:rq3-perf-failures}, performance-efficiency failures mainly arise from timed correct execution rather than immediate crashes. PERF4 fails in 124 out of 234 build-success submissions (52.99\%), indicating that many generated projects can start but cannot correctly complete enough workload within the time budget. Tail-latency instability is less frequent but still visible (PERF2: 31/233, 13.30\%), while crash/OOM/timeout failures are rare after filtering to build-success projects (PERF1: 1/234, 0.43\%).
```

插入“表 5.6：性能效率失败数统计”。

### Portability 段

第一句改成：

```latex
Table~\ref{tab:rq3-ptb-failures} shows that the Portability/buildability (PTB) dimension records the largest number of NFR defects, with a dimension-level failure rate of 41.91\%.
```

插入“表 5.7：可移植性失败数统计”。

### Security 段

第一句改成：

```latex
As summarized in Table~\ref{tab:rq3-sec-failures}, Security (SEC) has the lowest overall failure rate (21.41\%), but the remaining defects are critical.
```

插入“表 5.8：安全性失败数统计”。

### Reliability 段缺失

当前 RQ3 没有单独可靠性段，但原文有可靠性维度。建议加入：

```latex
\textbf{Reliability under Repeated Execution.}
Reliability failures are dominated by repeated-execution instability, as shown in Table~\ref{tab:rq3-rly-failures}. RLY1 fails in 170 out of 234 build-success submissions (72.65\%), suggesting that many generated projects can pass a basic startup gate but cannot remain stable across longer or repeated runs. By contrast, resource-pressure and concurrency checks fail far less frequently after build-success filtering.
```

插入“表 5.9：可靠性失败数统计”。

## 12. 表格文件对应关系

直接从这里复制：

```text
paper_tables/outline_aligned_tables.md
```

对应关系：

```text
表 3.1 -> tab:quality-dimensions
表 3.2 -> tab:dataset-scenarios
表 5.1 -> tab:rq1-static-nfr-accuracy
表 5.2 -> tab:rq2_results 或 tab:rq2-main-results，二选一统一
表 5.3 -> tab:rq3-top-nfr-failures
表 5.4 -> tab:rq3-cmp-failures
表 5.5 -> tab:rq3-mtn-failures
表 5.6 -> tab:rq3-perf-failures
表 5.7 -> tab:rq3-ptb-failures
表 5.8 -> tab:rq3-sec-failures
表 5.9 -> tab:rq3-rly-failures
```

## 13. 当前最需要立刻改的清单

1. 删除 Related Work 后的重复语言图，或改成方法框架图并移到 Introduction。
2. 删除 3.3 的源语言分布表。
3. 在 3.3 加五大场景比例表，并把 `Table X` 改成 `Table~\ref{tab:dataset-scenarios}`。
4. 把 3.2.4 的 `Table X` 改成 `Table~\ref{tab:quality-dimensions}`。
5. RQ1 插入表 5.1，并删除没有数值支撑的 Cohen's Kappa 表述。
6. RQ2 整表替换为真实结果表，正文数字从旧值改成真实值。
7. RQ3 加总排序表和各维度表引用。
8. RQ3 补 Performance 和 Reliability 两段。
9. 修正 MTN5 失败率：`4.85%` -> `14.85%`。
