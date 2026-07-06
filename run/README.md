# 出卷→考试→判卷 流水线（共享 NFS 队列 + 原子认领）

队列状态根：`/mnt/yangh559/chuti-run/`。每节点先 `source /mnt/yangh559/bench/env_profile.sh`。

## 三种角色（互不重叠的主机集）
| 角色 | 脚本 | 要求 |
|---|---|---|
| **出卷** ×5 | `launch_chuti.sh`（出完一题自动 `publish_exam.sh`）| 有 golden（挂 `out/`）|
| **考试** ×15（5类×3）| `AGENT=<type> exam_worker.sh` | **不应挂 golden**（见隔离）|
| **判卷** | `grade_worker.sh`（复用出卷节点）| 有 golden |
| **总控** | netnode `coordinator.sh` | 不当 worker，唯一集群出口，**不清零** |

每道题被 5 类各 1 个 agent 考（每类 3 节点对每题原子抢占，1 抢到、其余跳下一题）。

## 持续运营（netnode）
```bash
bash run/coordinator.sh --launch-all     # SSH 拉起所有节点 worker(poll 持续轮询)
bash run/coordinator.sh                   # 看板
bash run/coordinator.sh --scoreboard      # 成绩矩阵 题×agent
bash run/coordinator.sh --stop-all        # 置 STOP + pkill 所有 worker
```
先在 `run/roles.env` 填真实 hostname。考试 agent 现仅 **codex** 就绪；其余登录/安装后填 `EXAM_NODES_*`。

## 隔离（关键，平台层）
进程级硬隔离在本非特权容器做不到（无 namespace/bwrap）。**真隔离 = 考试节点建 pod 时不挂 `code-bench-v2/out`（golden），只挂 `chuti-run/exams`（考生包）。** 否则 agent 能 `cat out/<id>/07_exam/grader/cases/*` 看答案。
- `exam_worker.sh` 启动自检：能读到 golden 会**警告**；`EXAM_REQUIRE_ISOLATION=1` 则拒跑。
- 考试节点必须与出卷/判卷节点**主机不重叠**。

## 故障恢复
```bash
bash run/chuti_status.sh                  # 出卷进度
bash run/chuti_status.sh --reset-stale    # 释放死节点遗留认领(出卷+考试+判卷;仅所有节点已停时)
bash run/chuti_status.sh --retry-failed   # 清失败标记重跑
```
认领=原子 `mkdir`；done/failed/SUBMITTED/GRADED 标记防重复。硬崩溃遗留的认领由 `--reset-stale` 回收。
