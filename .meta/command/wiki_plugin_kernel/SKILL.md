---
name: wiki_plugin_kernel
owner: framework
description: "插件内核使用参考：校验、附检、同步、只读一致性检查 verify、卸载预检查 can-uninstall。Triggers on: 插件内核, wiki_plugin_kernel, kernel, 注入块更新, 投影重建, 更新注入."
---

# wiki_plugin_kernel：插件内核

`python .meta/scripts/wiki_plugin_kernel.py <子命令>`——框架侧唯一投影机：PLUGIN.yaml 是本体，AGENTS 注入区、check 检查块、命令用法块、注册表插件段、命令副本全是它的投影。幂等，随时可跑，漂移即修复。

## 子命令

| 子命令 | 作用 | 写盘 |
|---|---|---|
| `ls` | 插件清单 + 依赖 + 驱动命令 | 无 |
| `validate` | 合规检查：manifest 字段、依赖无环、owner×commands 双向一致、consumes 在场且带 usage 列表；错误退出码 1 | 无 |
| `audit` | 附检：发现式执行各插件 `scripts/check.py`，只读报告（可带插件 id 只查一个） | 无 |
| `inject` | 重建三种投影：AGENTS 注入区 + check 检查块 + 命令用法块 | AGENTS.md、含注入区的命令 SKILL.md |
| `registry` | 重建 registry.yaml 插件段（自各 manifest `fields`） | registry.yaml |
| `deploy` | 同步命令主本 → `.agents/skills/` 副本；孤儿副本仅报告（删除属人） | 副本 |
| `all` | validate + inject + registry + deploy 一步到位 | 以上全部 |
| `verify` | 只读对比全部投影与技能副本；漂移或孤儿副本退出码 1，不执行插件附检脚本 | 无 |
| `can-uninstall <id>` | 只读列出依赖插件及命令 owner/consumes 引用；阻塞或未知插件退出码 1；不自动卸载 | 无 |

## 典型场景

- **改了 PLUGIN.yaml**（inject / checks / usage / fields / 版本）：`python .meta/scripts/wiki_plugin_kernel.py all`——日常标准动作，一条命令全部收敛；validate 不过则阻断，修完重跑
- **只刷注入块**：`inject` 够用，但注意它改的是 `.meta/command/` 主本，副本须 `deploy` 才同步——所以日常一律用 `all`
- **健康快检**：`verify`（结构与投影）+ `audit`（附检）；完整审计（含语义项）走 check 命令。插件加载失败、未知 audit 目标、附检返回格式错误均失败；单插件附检出错仍继续其余插件。
- **装卸插件**：语义流程（决策、目录归档、log 行）走 plugin 命令；其中的机械步骤即本 CLI 的 `validate` / `all` / `audit`

## 边界

- 脚本只碰四处：插件目录进出、注入区标记块、registry 插件段、命令副本；protocol / reserved 段与 AGENTS.md 手写区永不动
- 纯标准库零依赖（Python 3）；中文输出
- 写操作先在内存准备本次全部输出，预检查通过后才写盘；标记须唯一且有序。每文件临时写入后替换，不保证跨文件断电原子性；系统写入故障后检查差异并重跑。
- `audit` 的只读是插件约定，不是代码沙箱；它会执行已安装插件的 Python 附检。`verify` 不执行附检，也不产生字节码缓存。
- 数据区派生层（`wiki/index.md`、`tags.md`、`hot.md`、`log.md`）不归本 CLI——那是 `pipeline.py`（`index` / `tags` / `hot` / `log` / `verify`），由 map / save 的写后管道调用

## Parameters

- 子命令（见上表）；`audit` 可带插件 id，`can-uninstall` 必须带插件 id
