# RQ3 NFR Failure Top 10

口径：主测四模型 Claude Code、Codex、Cursor、Kimi Code；仅统计 `build_ok=true` 的提交；`null`/不适用指标不进分母；CLI 接口完全符合按项目二值指标并入 CMP。

## 失败最多的 NFR 指标 Top 10

| 排名 | 维度 | 指标 | 未通过/适用 | 未通过率 | Claude | Codex | Cursor | Kimi |
|---:|---|---|---:|---:|---:|---:|---:|---:|
| 1 | 可移植/构建 | `PTB.PTB2` 无硬编码路径 | 226/229 | 98.69% | 61/61 | 57/59 | 56/57 | 52/52 |
| 2 | 兼容性 | `CMP.CMP1` 共享环境可启动 | 219/229 | 95.63% | 59/61 | 56/59 | 53/57 | 51/52 |
| 3 | 可维护性 | `MTN.MTN4` 认知复杂度合规 | 170/229 | 74.24% | 46/61 | 45/59 | 41/57 | 38/52 |
| 4 | 可靠性 | `RLY.RLY1` 长时/重复执行无故障 | 170/234 | 72.65% | 47/61 | 48/59 | 37/57 | 38/57 |
| 5 | 可移植/构建 | `PTB.PTB4` 显式编码声明 | 168/229 | 73.36% | 46/61 | 35/59 | 48/57 | 39/52 |
| 6 | 兼容性 | `CMP.CLI` CLI 接口契约完全符合 | 161/234 | 68.80% | 41/61 | 36/59 | 43/57 | 41/57 |
| 7 | 可维护性 | `MTN.MTN1` 无超大单文件 | 132/229 | 57.64% | 30/61 | 27/59 | 42/57 | 33/52 |
| 8 | 性能效率 | `PERF.PERF4` 限时正确通过 | 124/234 | 52.99% | 34/61 | 38/59 | 24/57 | 28/57 |
| 9 | 可移植/构建 | `PTB.PTB6` 无平台强绑定 | 100/229 | 43.67% | 27/61 | 18/59 | 31/57 | 24/52 |
| 10 | 可移植/构建 | `PTB.PTB3` 日志不写源码目录 | 65/229 | 28.38% | 25/61 | 15/59 | 10/57 | 15/52 |

## 维度级失败率（同口径）

| 维度 | 未通过/适用 | 未通过率 |
|---|---:|---:|
| 兼容性（CMP） | 380/463 | 82.07% |
| 可移植/构建（PTB） | 578/1379 | 41.91% |
| 可维护性（MTN） | 374/1145 | 32.66% |
| 可靠性（RLY） | 175/691 | 25.33% |
| 性能效率（PERF） | 156/701 | 22.25% |
| 安全性（SEC） | 67/313 | 21.41% |

## Top 指标样例候选

- `PTB.PTB2` 无硬编码路径：1password-typeshare/claude, 1password-typeshare/codex, 1password-typeshare/cursor, 1password-typeshare/kimi, 23andme-yamale/claude
- `CMP.CMP1` 共享环境可启动：1password-typeshare/claude, 1password-typeshare/codex, 1password-typeshare/cursor, 1password-typeshare/kimi, 23andme-yamale/claude
- `MTN.MTN4` 认知复杂度合规：1password-typeshare/codex, 1password-typeshare/cursor, 1password-typeshare/kimi, 23andme-yamale/claude, 23andme-yamale/codex
- `RLY.RLY1` 长时/重复执行无故障：1password-typeshare/claude, 1password-typeshare/codex, 1password-typeshare/cursor, 1password-typeshare/kimi, 23andme-yamale/codex
- `PTB.PTB4` 显式编码声明：1password-typeshare/claude, 1password-typeshare/codex, 1password-typeshare/cursor, 1password-typeshare/kimi, 23andme-yamale/claude
