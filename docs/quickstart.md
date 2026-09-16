# 快速开始：把 vault-wiki 装进你的库

> 读者：想把框架装进自己目录（Obsidian 库或任意文件夹）的人，或替你动手的 agent。全程约十分钟；每一步都经干净目录彩排验证（2026-09-13，Windows / Git Bash / Python 3 纯标准库）。

## 你会得到什么

- `vault/` 收真实资产（任意格式），`wiki/` 做代理页与原生笔记；md + 纯文件底座，Obsidian 只是可选 viewer
- 一个替你经营库的 agent：放资产说「映射」、存洞见说「保存」、问知识说「检索」；索引 / 标签 / 热缓存 / 日志全自动维护
- additive 部署：目标库存量内容一个字节不动

## 前提

| 项 | 要求 |
|---|---|
| Python | 3.x，纯标准库零依赖 |
| agent | 能读 AGENTS.md 与 `.agents/skills/` 的编程助手（如 ZCode） |
| Obsidian | 可选，仅作 viewer |

## 部署五步

**① 取框架**：`git clone https://github.com/Josh-Zhangccc/vault-wiki.git`（或下载 ZIP 解压）。

**② 拷两棵树**到目标库根：`.meta/` 与 `.agents/skills/`——插件主本、命令主本与副本、协议工件、机械脚本全在其中。

**③ 写目标库 AGENTS.md**：外壳自拟（一段身份 + 布局说明）；注入区标记块（`<!-- wiki-inject:start -->` 至 `<!-- wiki-inject:end -->`）从本仓库 AGENTS.md **原样**拷入，一字不改——结构契约的唯一源（范例见 `test-repo/AGENTS.md`）。目标库已有 AGENTS.md 的，只贴注入区块。

**④ 建四个空目录**：`vault/`、`wiki/notes/`、`wiki/sessions/`、`wiki/vault/`。派生页（index / tags / hot / log）**不用手造**：首跑管道自建，根索引的 `format_version` 也由管道渲染。

**⑤ 收敛投影**，目标库根执行：

```
python .meta/scripts/wiki_plugin_kernel.py all
```

预期：当前 14 插件 validate 通过、投影收敛、命令副本同步。报错先按信息修复，再重跑。之后执行 `python .meta/scripts/wiki_plugin_kernel.py verify`，只读确认投影与副本一致。

## 首跑验证

1. 放任意一个文件进 `vault/`（如 `memo.txt`）
2. 目标库根开 agent 会话，说「**映射**」
3. agent 应产出：`wiki/vault/memo.txt.md` 代理页（含 SHA-256）→ 写后管道自建 `wiki/index.md`、各目录 `index.md`、`tags.md`、`hot.md`、`log.md` → 附检报告
4. 再说「**检查**」，全绿即部署成功

## 日常一句话

| 你说 | agent 做 |
|---|---|
| 映射 | vault 资产登记为代理页 |
| 保存 | 对话洞见沉淀为原生笔记 |
| 检索 | 热缓存 → 索引 → grep 综合回答（带 wikilink 引用） |
| 检查 | 库健康审计 |
| 插件 | 装卸结构插件 |
| 内核参考 | wiki_plugin_kernel 用法 |

命令细节以 `.agents/skills/` 各 SKILL.md 披露为准。

## 升级与卸载

- **升级**：重拷 `.meta/` 与 `.agents/skills/`，重跑 `all`——框架件与数据区分离，`wiki/`、`vault/` 不受影响
- **卸载**：删两棵树 + AGENTS.md 注入区块；数据区归你，自行处置

## 常见问题

- **目标库已有内容？** 框架只增不改，存量照旧；新资产进 `vault/` 走映射，旧内容是否代理由你逐步决定
- **拷整棵 `.agents/` 行不行？** 行，本仓库 `.agents/` 下只有 `skills/`
- **跨平台？** 纯标准库、路径无硬编码；已在 Windows（Git Bash）实测，macOS / Linux 无额外要求
