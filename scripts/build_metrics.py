"""Build dataset/metrics-table.json from the user's NFR.pdf content (38 metrics)."""
import json, pathlib

M = {
  "security": [
    ("未授权访问阻断率", "面对未登录/无token/无权限/伪造身份的请求时,是否阻止访问受保护资源。"),
    ("敏感信息泄露防护率", "是否避免在源码、配置中泄露密码/token/密钥/cookie/数据库连接串等敏感信息。"),
    ("敏感字段非明文存储率", "适用于存在数据库/文件持久化/缓存/用户凭据存储的项目;敏感字段是否非明文存储。"),
    ("外部通信安全配置率", "适用于存在HTTP client/数据库连接的项目;是否不默认用明文HTTP传敏感数据、不把token放URL query。"),
    ("未授权修改阻断率", "是否阻止未授权主体对数据/配置/状态/资源执行创建/修改/删除。"),
    ("恶意输入抗篡改率", "面对恶意输入是否避免状态破坏/注入/路径穿越/命令执行/解析异常导致的数据污染。"),
    ("安全事件证据覆盖率", "适用于原项目需要记录日志;关键安全相关事件是否留下可验证证据。"),
    ("审计字段完整率", "适用于原项目需要记录日志;日志字段是否完整记录事件。"),
  ],
  "compatibility": [
    ("共享环境部署成功率", "在存在其他服务/共享端口/共享文件系统/共享环境变量和资源限制时能否成功构建。"),
    ("共享资源非干扰率", "与其他服务共同运行时是否不过度抢占CPU/内存/FD/线程/进程/IO,导致邻居退化。"),
    ("接口契约符合率", "生成项目暴露的接口是否符合机器可读契约(HTTP API/CLI等)。"),
  ],
  "reliability": [
    ("长时无故障执行率", "持续运行/调用是否保持稳定,不crash/panic/死循环/资源耗尽/功能退化。"),
    ("可操作入口可用率", "主要入口是否能被自动调用并返回可接受结果。"),
    ("启动与重启可用率", "多次冷启动/热重启后能否稳定进入可用状态。"),
    ("外部依赖故障容忍率", "文件/网络/数据库/外部API/环境变量等依赖异常时是否优雅处理。"),
    ("资源压力容忍率", "资源受限下是否优雅失败或保持核心功能,而非崩溃/死锁/无限重试。"),
    ("并发故障容忍率", "并发调用/读写/启动任务时是否发生死锁/数据竞争/状态破坏/请求大面积失败。"),
    ("异常终止后重启恢复率", "被强制终止后是否能重启并恢复主要功能。"),
    ("状态与数据恢复完整率", "仅适用于有持久化状态的项目;异常终止后是否保持数据一致性。"),
  ],
  "maintainability": [
    ("巨型文件存在率", "是否存在过大的单文件。"),
    ("组件耦合控制度", "模块之间/业务层之间是否存在过强依赖。"),
    ("配置与环境解耦率", "是否将路径/端口/密钥/系统环境/外部服务地址写死在代码中。"),
    ("复杂度与理解成本", "圈复杂度/认知复杂度/参数数量/嵌套深度是否过高。"),
    ("文档与定位充分性", "README/rustdoc/公有API文档/example/错误信息是否足以快速理解结构与改法。"),
  ],
  "performance": [
    ("运行完成率", "运行hidden tests时是否避免timeout/crash/非零退出/OOM/连接失败/readiness丢失/runner error。"),
    ("延迟预算满足率", "功能正确的用例端到端耗时是否在统一时间预算内。"),
    ("尾部耗时稳定率", "hidden tests负载下是否存在明显长尾耗时放大。"),
    ("有效吞吐达成率", "限定总时间预算内单位时间能正确完成多少测试任务。"),
    ("内存峰值预算满足率", "运行hidden tests时内存峰值是否在统一内存预算内。"),
    ("静态性能风险控制率", "源码是否避免固定等待/忙等/无界循环/循环内起子进程或线程/热路径外部网络/全量读入/循环内过量日志/临时文件泄漏/高阶嵌套遍历。"),
  ],
  "portability": [
    ("标准构建成功率", "能否在统一评测Docker镜像中基于candidate_manifest/受限依赖目录/固定构建模板完成构建。"),
    ("受限依赖声明符合率", "声明的language_profile/project_type/dependencies/entry是否符合schema且依赖均在dependency_catalog中。"),
    ("环境扰动通过率", "在多个受控运行环境profile下复放hidden tests是否仍功能正确。"),
    ("最小环境变量适应率", "仅保留PATH/HOME/TMPDIR时是否避免依赖未声明环境变量。"),
    ("空格路径适应率", "工作目录含空格时路径拼接/命令调用/文件读写是否仍正常。"),
    ("非root系统用户运行通过率", "非root用户下是否避免依赖sudo/chown/chmod/系统目录写权限/低端口绑定等特权行为。"),
    ("临时目录变化适应率", "TMPDIR指向自定义可写目录时是否正确使用系统临时目录,避免硬编码/tmp/当前目录/源码目录。"),
    ("静态环境绑定风险控制率", "源码是否避免绝对路径/硬编码分隔符/shell专属命令/未保护系统API/无默认值环境变量/写源码目录/运行期外部网络依赖/未声明系统依赖/root依赖/缺失生成步骤。"),
  ],
}
PFX = {"security": "SEC", "compatibility": "COMPAT", "reliability": "REL",
       "maintainability": "MAINT", "performance": "PERF", "portability": "PORT"}

metrics = []
for cat, items in M.items():
    for i, (name, desc) in enumerate(items, 1):
        metrics.append({"id": f"{PFX[cat]}-{i}", "category": cat, "name": name, "description": desc})

out = pathlib.Path(r"D:\code-bench\dataset\metrics-table.json")
out.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
print("metrics:", len(metrics), "->", out)
from collections import Counter
print(dict(Counter(m["category"] for m in metrics)))
