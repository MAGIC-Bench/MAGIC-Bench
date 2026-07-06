# 论文图片生成结果

所有图片均由 `scripts/generate_paper_figures.py` 从本地实验数据生成。图内不包含论文 caption 式标题，标题请放在 LaTeX/Word 的图注中。

| 图片 | Source data | Notes |
|---|---|---|
| `语言分布饼图` | `rerun_all_project_summaries_v2.json`, `dataset/repo-list.manifest.json`, `generation_language.txt` | 81 个任务的原仓库语言与目标实现语言分布。 |
| `研究问题二-功能正确性结果` | `rerun_all_project_summaries_v2.json` | 功能指标，分母只统计 `original_score_build_ok=true` 的项目。 |
| `研究问题二-七维指标结果` | functional rerun data + `nfr_corrected_summary.json` | FR 与修正后的 NFR 维度通过率。 |
| `研究问题三-非功能维度失败率` | `rq3_nfr_failure_top10.json` | build-success 项目内的 NFR 维度失败率。 |
| `研究问题三-高频非功能失败指标` | `rq3_nfr_failure_top10.json` | 高频 NFR 失败指标 Top 10。 |

每张图片同时输出 `.svg` 和 `.png`；同目录 CSV 文件保存绘图数据。

注：方法框架图不再生成；当前仅保留语言分布图和实验结果/缺陷分析图。
