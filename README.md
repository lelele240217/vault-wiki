# vault-wiki

**个人自用的 agent 知识库框架**：vault 容纳真实资产，wiki 做 md 代理与原生笔记，agent 按 SASU-L 披露顺序零先验读写。md + 纯文件是底座，Obsidian 等仅为可替换 viewer。

> 状态：原型已冻结（2026-09-08~12 构建，两轮真实操作 + 冷启动披露审计通过），当前阶段为日常使用、边用边改。2026-09-12 裁定定位个人自用，普世化与矩阵化测试搁置（沿革见 `log.md`）。

## 它做什么

让 AI 编程助手（agent）替你经营一座「个人维基」：

- 资产放进 `vault/`（任意格式：md / txt / csv / pdf / 图像……），**映射（map）**命令登记为 `wiki/vault/` 下的 md 代理页（SHA-256 + 元数据 + 链接）
- 对话中的洞见与决策，**保存**命令沉淀为 `wiki/notes/` 原生笔记；会话骨干页入 `wiki/sessions/`
- **检索**命令先读热缓存与索引再综合回答，产出带 wikilink 引用的答案
- 索引 / 标签 / 热缓存 / 运行日志全为派生层自动维护；**检查**命令审计库健康，**插件**命令装卸结构插件

## 核心概念

| 概念 | 定义 |
|---|---|
| vault | 真实资产仓库；命令侧只增，删改自由属于人 |
| wiki | vault 的 md 代理层 + 原生笔记区 + 派生层（index / tags / hot / log） |
| SASU-L | 披露范式：agent 只经 system prompt → AGENTS.md → Skills → 用户原话 → loop 获知信息 |

## 布局

| 目录 | 内容 |
|------|------|
| `.meta/` | 原型核心：十四插件（概念双插件 wiki/vault、桥接 mapping、notes/sessions/link/tag/trust/index/hot/log/user-profile/todo/structure；无分层，注入序=依赖拓扑+字母序）、六命令主本、协议工件（registry / actions / experiments）、机械脚本（wiki_plugin_kernel / pipeline / wikilib，纯标准库零依赖） |
| `wiki/`、`vault/` | 数据区骨架（保持空种子：内容属部署实例，工程内不积累——跑库验证走 test-repo） |
| `.agents/skills/` | 命令部署副本 |
| `test-repo/` | 参考实例：自足虚拟库（实例侧 AGENTS.md 外壳 + 样例数据，内部不感知构建工程）；框架变更由根侧同步重拷 |
| `docs/` | 设计档案：现行 `quickstart.md` 部署走查、`pointers.md` 指针机制、`research-user-profile.md` 设计依据；历史档案 `00-principles.md`、`01-okf.md` 不起现行作用 |

## 上手

前提：Python 3（纯标准库，无需安装依赖）、git、能读 AGENTS.md 与 skills 的 agent 环境（如 ZCode）；Obsidian 可选，仅作 viewer。

在仓库根打开 agent 会话即可——AGENTS.md 是宪法（含插件注入区），六个命令以自然语言触发：**映射 / 保存 / 检索 / 检查 / 插件 / 内核参考**（map / save / query / check / plugin / wiki_plugin_kernel，主本见 `.meta/command/`）。把文件放进 `vault/`，对 agent 说「映射」，就是第一次使用。

## 部署：装进你自己的库

框架本体三件：`.meta/`、`.agents/skills/`、AGENTS.md 注入区。部署是 additive 拷贝——拷两棵树 + 写 AGENTS 外壳 + 建空目录 + 内核收敛，目标库存量内容不动；派生页首跑自建，无需手造。逐步走查见 [docs/quickstart.md](docs/quickstart.md)（经干净目录彩排验证）。

## 文档指针

- [本轮改动清单：内核可靠性与体验](docs/changes/2026-09-16-kernel-reliability.md) — 修改位置、原因、前后差异与验证结果
- `docs/quickstart.md` — 快速开始：部署五步与首跑验证（走查）
- `AGENTS.md` — 宪法与准则（agent 先读）
- `log.md` — 工程日志：现状、阶段、过往操作
- `.meta/protocol/` — 字段注册表、动作纪律、披露范式

## 沿革

2026-08-26 以个人库结构副本起建，08-28 重定位为本工程，09-08 起「插件 + 命令」原型直接落地、经真实操作验证后冻结；09-12 重构：概念双插件 wiki/vault 立设、原 vault 插件更名 mapping、废除分层、标识符英文化。设计谱系讨论存于个人库（见 AGENTS.md 指针）。
