# 项目日志

> 追加与修改须标注日期（精确到天）；总量 <2k 字；整合压缩须用户同意。

## 现状（2026-09-13）

工程定位：**个人自用**——矩阵测试裁撤，SASU-L 为镜，边用边改。架构终态：概念双插件 wiki/vault（纯声明）+ 桥接 mapping + 十一结构插件，共十四、无分层（注入序=依赖拓扑+字母序）；六命令 map/save/query/check/plugin/wiki_plugin_kernel（末者为插件内核使用参考）。三投影一源：manifest（inject/checks/usage）→ AGENTS 注入区、check 检查块、命令用法块（consumes 序即执行序）；PLUGIN.md 纯文档，内核 wiki_plugin_kernel.py 唯一投影机；registry 字段注册表（预留段可认领回填）。docs/ 现行三件（quickstart/pointers/research）。`test-repo/` 自足虚拟库，根侧同步重拷。

## 阶段

框架构建（✓，2026-09-08~12）→ 日常使用与边用边改（**当前**）。原阶段③④⑤⑥（蒸馏/普世化/回填/自进化）不排期：模式重复时再蒸馏，回填随部署自然发生，自进化以「摩擦点即规范空洞」轻量随行。

## 下一步

- wiki 初始化机制（画像首建与建构/整合命令同批）：冷启动时机与首建内容——随设计文档一并解决
- 设计文档：导论随后开卷（章=文件，问题驱动；OKF 不收编）
- 部署进个人库（**用户自行执行**，agent 不主动触碰；走查见 `docs/quickstart.md`，additive，存量页不动、旧页渐进代理）
- skill 打磨随摩擦滚动；delegate（vault 放入通道）与裁撤项不排期

## 过往操作

- 2026-09-16 内核可靠性修复与体验：见 docs/kernel-reliability.md。
- 2026-09-14 structure 0.2：声明页落 `wiki/structure.md`（structure 块映射机械可读，type 领地值扩 structure；漂移检测升级附检 diff，冒烟双向实锤）；wikilib 子键放宽（目录名/中文键曾解析为 None，承重件实锤修补）
- 2026-09-14 vault 治理批次：structure 立设（第十四，布局声明+漂移检测）；vault 0.4 认领 url；mapping 0.7——孤儿报文带引用计数、重算写 log 行；user-write 四预设入档
- 2026-09-14 指针概念成文 `docs/pointers.md`：定义 / 五件构成 / 系统实例盘点（含 todo 时间维）/ 设计准则；AGENTS 与 README 指针随更
- 2026-09-14 todo 立设（第十三插件）：`wiki/todo.md` 委托队列（日期/情境触发，新 session 先读）；销账写 log、已结 ≤20 清理；不挂命令
- 2026-09-14 notes 0.13 瘦身：type 分层（领地封闭/形态开放）；补边界与 README
- 2026-09-13 user-profile 立设（第十二）：`wiki/profile.md` 收敛式画像（零字段复用 trust），depends 四项，双通道挂 save/map，检查三项；09-14 补 usage 提炼方法论（SASU-L 闭环）
- 2026-09-13 save 首跑与角色纠偏：踩坑热缓存短名断链（全名约定应验即修）；裁定**工程是开发框架非跑库**——蒸馏笔记回迁 docs，wiki 数据区归零
- 2026-09-13 画像调研蒸馏入 docs（定位=使用者持续认知档案）
- 2026-09-13 框架收束日：quickstart 开卷、上 GitHub、评审修补七项、test-repo 立设、命令审计、投影定形（三投影一源）
- 2026-09-12 定位与重构：裁定个人自用、以用代验；架构重构四提交；OKF v0.2 成文；雾港与真实库实验全绿，确立 SASU-L 与零污染纪律
- 2026-09-08~11 原型落地：六插件四命令起步；registry/actions 与装卸内核；分层对齐；命令-插件绑定、trust 立设
- 2026-09-07 插件规范草案写入 user-write（已删，见 git）
- 2026-08-26~28 创始期：个人库结构副本起建，旋即重定位为 vault-wiki 框架；一次骨架定稿经用户回退
