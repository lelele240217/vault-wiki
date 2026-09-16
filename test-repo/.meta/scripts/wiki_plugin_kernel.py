#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""vault-wiki 插件生命周期机械核心（装卸 / 合规 / 依赖 / 注入 / 注册表 / 副本同步）。

定位（见 .meta/protocol/actions.md 执行原则）：确定性的结构操作交给本脚本，
语义判断交给 LLM。脚本只碰四处：插件目录进出、AGENTS.md 注入区标记块、
registry.yaml 插件段、.agents/skills/ 命令副本；protocol / reserved 段与手写区永不动。

用法:
  python .meta/scripts/wiki_plugin_kernel.py ls          # 清单 + 依赖
  python .meta/scripts/wiki_plugin_kernel.py validate    # 合规与依赖检查（只读，错误退出码 1）
  python .meta/scripts/wiki_plugin_kernel.py audit       # 插件附检（发现式执行各插件 scripts/check.py）
  python .meta/scripts/wiki_plugin_kernel.py inject      # 重建 AGENTS.md 注入区、check 检查块与命令用法块（幂等）
  python .meta/scripts/wiki_plugin_kernel.py registry    # 重建 registry.yaml 插件段（幂等）
  python .meta/scripts/wiki_plugin_kernel.py deploy      # 同步命令部署副本（幂等）
  python .meta/scripts/wiki_plugin_kernel.py all         # validate + inject + registry + deploy
  python .meta/scripts/wiki_plugin_kernel.py verify      # 只读检查全部投影与副本
  python .meta/scripts/wiki_plugin_kernel.py can-uninstall <id>  # 只读卸载预检查

manifest 最小 YAML 子集：顶层 `key: value`、`key: []`、块式列表（`  - 项`）、
一层字段字典（`  name: 描述`）；双引号包裹的值去引号；行内注释（` #` 起）剥离。

依赖与注入序：
- depends 声明行为或语义依赖（桥接件依赖两端概念插件即语义依赖）；validate 校验存在性与无环
- 注入序 = 依赖拓扑（被依赖者先注入）+ 同批字母序；无分层概念

命令-插件绑定（双向声明，validate 校验一致）：
- 命令 frontmatter 增 owner：插件 id（多个用 [a, b] 列表）或 framework（跨切面，显式无主）
- 插件 manifest 增可选字段 commands：本插件驱动的命令名列表
- error 情形：命令缺 owner、owner 指向未装插件、framework 与其他 owner 并列、
  插件声明不存在的命令、任一侧单边声明（owner 未被 commands 认领，或反之）

命令注入（第三种投影：插件写侧契约 → 命令）：
- 命令 frontmatter 增可选 consumes：消费其写侧契约的插件 id 有序列表（序即执行序）；
  owner 驱动的命令必填且须含全部 owner
- manifest 的 usage / checks 列表是写侧契约与检查规则的唯一投影源：checks 按注入序
  投影进 check 命令，usage 按命令 consumes 序投影进其 SKILL.md 的 cmd-inject 标记块
  （在场即注册）；改契约改 PLUGIN.yaml，命令正文只留操作流程。
  PLUGIN.md 回归纯文档（Role / Structure / Invariants / Changelog）

插件附检契约（scripts/check.py，可选）：
- 必须定义 check(ctx)，返回 issue 列表：{"level": "error"|"warning"|"info", "message": str}
- ctx.root = 仓库根；ctx.pages = [(wiki 相对路径, frontmatter dict, 正文)]，单次扫描共享
- 只读零副作用：修复动作归命令/人，附检只报告；中文消息，无第三方依赖
"""
import ast
import importlib.util
import os
import re
import sys
import tempfile
import types

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PLUGINS_DIR = os.path.join(ROOT, ".meta", "plugins")
COMMANDS_DIR = os.path.join(ROOT, ".meta", "command")
SKILLS_DIR = os.path.join(ROOT, ".agents", "skills")
AGENTS_MD = os.path.join(ROOT, "AGENTS.md")
REGISTRY = os.path.join(ROOT, ".meta", "protocol", "registry.yaml")

# manifest 七字段（id / version / depends / updated / attachment / fields / inject）+ 可选 commands
REQUIRED_KEYS = ["id", "version", "depends", "updated", "attachment", "fields", "inject"]
INJECT_START = "<!-- wiki-inject:start -->"
INJECT_END = "<!-- wiki-inject:end -->"
CHECK_SKILL = os.path.join(COMMANDS_DIR, "check", "SKILL.md")
CHECK_INJECT_START = "<!-- check-inject:start -->"
CHECK_INJECT_END = "<!-- check-inject:end -->"
CMD_INJECT_START = "<!-- cmd-inject:start -->"
CMD_INJECT_END = "<!-- cmd-inject:end -->"


def ordered_plugins(plugins):
    """注入序 = 依赖拓扑（被依赖者先注入）+ 同批字母序；投影区共用。

    环或悬挂依赖时按字母序兜底输出（validate 另行报错，不在此重复）。
    """
    remaining = dict(plugins)
    order = []
    while remaining:
        ready = sorted(p for p, m in remaining.items()
                       if all(d not in remaining for d in (m.get("depends") or [])))
        if not ready:
            order.extend(sorted(remaining))
            break
        order.extend(ready)
        for p in ready:
            del remaining[p]
    return order


def strip_quotes(s):
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        return s[1:-1]
    return s


def strip_comment(s):
    """剥离行内注释（` #` 起）；完整值含 # 前须加引号。"""
    return re.split(r"\s+#", s, maxsplit=1)[0].strip()


def parse_manifest(path):
    """解析 manifest 的最小 YAML 子集；失败抛出 ValueError。"""
    data, target = {}, None
    for raw in open(path, encoding="utf-8").read().splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw.startswith("  - "):
            if target is None:
                raise ValueError(f"list item before any key: {raw!r}")
            item = strip_quotes(strip_comment(raw.strip()[2:]))
            if not isinstance(data.get(target), list):
                data[target] = []
            data[target].append(item)
            continue
        m = re.match(r"^(\s*)([A-Za-z_][\w-]*):\s*(.*)$", raw)
        if not m:
            raise ValueError(f"unparsable line: {raw!r}")
        key, val = m.group(2), strip_comment(m.group(3))
        if m.group(1):  # 缩进行：fields 字典项
            if target is None:
                raise ValueError(f"field item before any key: {raw!r}")
            if not isinstance(data.get(target), dict):
                data[target] = {}
            data[target][key] = strip_quotes(val)
        else:
            target = key
            if val == "":
                data[key] = None  # 块式，待后续行填充
            elif val == "[]":
                data[key] = []
            elif val == "{}":
                data[key] = {}
            else:
                data[key] = strip_quotes(val)
    return data


def load_plugins():
    """读取全部插件 manifest；返回 (plugins, errors)。"""
    plugins, errors = {}, []
    for name in sorted(os.listdir(PLUGINS_DIR)):
        pdir = os.path.join(PLUGINS_DIR, name)
        if not os.path.isdir(pdir):
            continue
        yml = os.path.join(pdir, "PLUGIN.yaml")
        md = os.path.join(pdir, "PLUGIN.md")
        if not os.path.exists(yml) or not os.path.exists(md):
            errors.append(f"[error] {name}/: PLUGIN.yaml or PLUGIN.md missing")
            continue
        try:
            m = parse_manifest(yml)
        except (ValueError, OSError) as e:
            errors.append(f"[error] {name}/PLUGIN.yaml: {e}")
            continue
        plugins[name] = m
    return plugins, errors


def validate(plugins, errors):
    """合规与依赖检查；错误追加进 errors。"""
    for name, m in sorted(plugins.items()):
        for k in REQUIRED_KEYS:
            if k not in m:
                errors.append(f"[error] {name}/PLUGIN.yaml: missing field {k}")
        for k in ("id", "version", "updated", "inject"):
            if not isinstance(m.get(k), str) or not m[k].strip():
                errors.append(f"[error] {name}/: {k} must be a non-empty string")
        for k in ("depends", "attachment", "commands", "usage", "checks"):
            if k in m and (not isinstance(m[k], list) or
                           any(not isinstance(v, str) or not v.strip() for v in m[k])):
                errors.append(f"[error] {name}/: {k} must be a list of strings")
        if not isinstance(m.get("fields"), dict):
            errors.append(f"[error] {name}/: fields must be a mapping")
        if m.get("id") and m["id"] != name:
            errors.append(f"[error] {name}/: id ({m['id']}) != directory name")
        if m.get("version") and not re.fullmatch(r"\d+\.\d+", str(m["version"])):
            errors.append(f"[error] {name}/: version ({m['version']}) not X.Y")
        if m.get("updated") and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(m["updated"])):
            errors.append(f"[error] {name}/: updated ({m['updated']}) not YYYY-MM-DD")
        deps = m.get("depends")
        if deps is not None and not isinstance(deps, list):
            errors.append(f"[error] {name}/: depends must be a list")
        if not m.get("inject"):
            errors.append(f"[error] {name}/: inject (projection line) empty")
        # 附检契约（可选）：scripts/check.py 存在则必须定义 check(ctx)——AST 静态查，不执行
        cpath = os.path.join(PLUGINS_DIR, name, "scripts", "check.py")
        if os.path.exists(cpath):
            try:
                tree = ast.parse(open(cpath, encoding="utf-8").read())
            except SyntaxError as e:
                errors.append(f"[error] {name}/scripts/check.py syntax error: {e}")
            else:
                if not any(isinstance(n, ast.FunctionDef) and n.name == "check" for n in tree.body):
                    errors.append(f"[error] {name}/scripts/check.py: check(ctx) not defined (audit contract)")
    if errors:
        return  # 类型未通过时不遍历依赖，避免错误输入引发异常
    # 依赖存在性
    for name, m in sorted(plugins.items()):
        for dep in m.get("depends") or []:
            if dep not in plugins:
                errors.append(f"[error] {name}/: dependency {dep} not found")
    # 环检测（DFS 三色标记）
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {k: WHITE for k in plugins}

    def dfs(node, path):
        color[node] = GRAY
        for dep in plugins[node].get("depends") or []:
            if dep not in plugins:
                continue
            if color[dep] == GRAY:
                errors.append(f"[error] dependency cycle: {' -> '.join(path + [node, dep])}")
            elif color[dep] == WHITE:
                dfs(dep, path + [node])
        color[node] = BLACK

    for k in sorted(plugins):
        if color[k] == WHITE:
            dfs(k, [])


def _owner_list(owner):
    """owner 值规范化为 id 列表：list 原样，字符串按逗号拆（容忍 [a, b] 形态）。"""
    if isinstance(owner, list):
        vals = [str(v).strip() for v in owner]
    else:
        vals = [v.strip() for v in str(owner).replace("[", "").replace("]", "").split(",")]
    return [v for v in vals if v]


def validate_bindings(plugins, errors):
    """命令-插件绑定：命令 frontmatter owner × 插件 manifest commands 双向一致。"""
    import wikilib

    commands, claimed = [], {}  # claimed: 命令 -> owner 集合（framework 除外）
    for name in sorted(os.listdir(COMMANDS_DIR)):
        cdir = os.path.join(COMMANDS_DIR, name)
        path = os.path.join(cdir, "SKILL.md")
        if not os.path.isdir(cdir) or not os.path.exists(path):
            continue
        commands.append(name)
        fm = wikilib.parse_frontmatter(open(path, encoding="utf-8").read())
        if fm.get("owner") is None:
            errors.append(f"[error] command {name}/: frontmatter missing owner (plugin id or framework)")
            continue
        owners = _owner_list(fm["owner"])
        # consumes（可选；owner 驱动的命令必填且须含全部 owner）：写侧契约消费声明，序即执行序
        consumes = fm.get("consumes")
        consumes = _owner_list(consumes) if consumes else []
        if "framework" not in owners and not consumes:
            errors.append(f"[error] command {name}/: owner-driven command requires consumes (owner usage projects too)")
        for pid in consumes:
            if pid not in plugins:
                errors.append(f"[error] command {name}/: consumes {pid} is not an installed plugin")
                continue
            if not (plugins[pid].get("usage") or []):
                errors.append(f"[error] command {name}/: consumes {pid} but its manifest lacks a usage list")
        if "framework" not in owners:
            for pid in owners:
                if pid not in consumes:
                    errors.append(f"[error] command {name}/: owner {pid} not in consumes (owner usage projects too)")
        if "framework" in owners:
            if len(owners) > 1:
                errors.append(f"[error] command {name}/: framework cannot combine with other owners ({', '.join(owners)})")
            continue
        claimed[name] = set(owners)
        for pid in owners:
            if pid not in plugins:
                errors.append(f"[error] command {name}/: owner {pid} is not an installed plugin")
    for pid, m in sorted(plugins.items()):
        cmds = m.get("commands")
        if cmds is None:
            continue
        if not isinstance(cmds, list):
            errors.append(f"[error] {pid}/: commands must be a list")
            continue
        for c in cmds:
            if c not in commands:
                errors.append(f"[error] {pid}/: commands declares missing command {c} (.meta/command/{c}/)")
            elif c not in claimed:
                errors.append(f"[error] command {c}/: {pid} one-sided claim (owner is framework or missing)")
            elif pid not in claimed[c]:
                errors.append(f"[error] command {c}/: {pid} one-sided claim (owner does not include {pid})")
    for c, owners in sorted(claimed.items()):
        for pid in owners:
            if pid in plugins and c not in (plugins[pid].get("commands") or []):
                errors.append(f"[error] command {c}/: owner {pid} not claimed in manifest commands (one-sided)")


def do_audit(plugins, only=None):
    """插件附检：发现式执行各插件 scripts/check.py（契约见模块 docstring）。

    这是「代码注入」的机制形态：插件目录里存在契约合规的附检脚本即自动入列，
    卸载目录移出即自动出列——与 AGENTS.md 注入区同构（在场即注册），但代码
    不做文本拼接（避免命名空间与合并噪音），改为发现 + 调用。
    """
    import wikilib

    if only and only not in plugins:
        print(f"[error] 未安装插件：{only}")
        return 1
    pages = list(wikilib.walk_pages(ROOT))  # 单次扫描，全部插件共享（调用节俭）
    ctx = types.SimpleNamespace(root=ROOT, pages=pages)
    counts = {"error": 0, "warning": 0, "info": 0}
    ran = 0
    for pid in sorted(plugins):
        if only and pid != only:
            continue
        cpath = os.path.join(PLUGINS_DIR, pid, "scripts", "check.py")
        if not os.path.exists(cpath):
            continue
        try:
            spec = importlib.util.spec_from_file_location(f"plugin_check_{pid}", cpath)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            issues = mod.check(ctx)
            if not isinstance(issues, list):
                raise ValueError("check(ctx) 必须返回列表（无问题返回 []）")
            for it in issues:
                if (not isinstance(it, dict) or
                        it.get("level") not in ("error", "warning", "info") or
                        not isinstance(it.get("message"), str)):
                    raise ValueError("附检条目必须包含 level(error/warning/info) 与字符串 message")
        except Exception as e:  # 附检脚本自身故障按 error 报告，不拖垮其余插件
            print(f"[error] ({pid}) check script failed: {e}")
            counts["error"] += 1
            ran += 1
            continue
        ran += 1
        for it in issues:
            level = str(it.get("level", "warning"))
            counts[level] = counts.get(level, 0) + 1
            print(f"[{level}] ({pid}) {it.get('message', '')}")
    if ran == 0:
        print("[audit] no plugin carries scripts/check.py (optional contract; currently semantic-only)")
        return 0
    print(f"[audit] {ran} plugins, error {counts['error']} / warning {counts.get('warning', 0)} / info {counts.get('info', 0)}")
    return 1 if counts["error"] else 0


class ProjectionPlan:
    """先渲染全部变更，再写盘；单文件替换，不承诺跨文件断电原子性。"""

    def __init__(self):
        self.files = {}

    def content(self, path):
        if path in self.files:
            return self.files[path]
        with open(path, "rb") as handle:
            return handle.read()

    def read(self, path):
        return self.content(path).decode("utf-8").replace("\r\n", "\n")

    def stage(self, path, content):
        self.files[path] = content.encode("utf-8") if isinstance(content, str) else content

    def apply(self, check_only=False):
        changed = []
        for path, content in self.files.items():
            if os.path.exists(path):
                with open(path, "rb") as handle:
                    if handle.read() == content:
                        continue
            changed.append((path, content))
        if check_only:
            for path, _ in changed:
                print(f"[drift] {os.path.relpath(path, ROOT)}")
            return not changed
        # 所有输出先落临时文件，写入准备失败时不替换原文件。
        staged = []
        try:
            for path, content in changed:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with tempfile.NamedTemporaryFile(dir=os.path.dirname(path),
                                                 prefix=".kernel-", delete=False) as handle:
                    staged.append((handle.name, path))
                    handle.write(content)
            for temp, path in staged:
                os.replace(temp, path)
                print(f"[write] {os.path.relpath(path, ROOT)}")
        finally:
            for temp, _ in staged:
                if os.path.exists(temp):
                    os.unlink(temp)
        if not changed:
            print("[sync] 无需更改")
        return True


def find_region(text, start, end):
    """标记须唯一且顺序正确，避免修改到错误区域。"""
    if text.count(start) != 1 or text.count(end) != 1:
        return None
    return re.search(re.escape(start) + r"\n(.*?)" + re.escape(end), text, re.S)


def do_inject(plugins, plan):
    """自 manifests 重建 AGENTS.md 注入区（保留前置说明，块按依赖拓扑+字母序，幂等）。"""
    text = plan.read(AGENTS_MD)
    m = find_region(text, INJECT_START, INJECT_END)
    if not m:
        print("[error] AGENTS.md: inject markers (wiki-inject:start/end) not found")
        return False
    region = m.group(1)
    first = region.find("<!-- plugin:")
    preamble = region[:first].rstrip() if first != -1 else region.rstrip()
    blocks = []
    for pid in ordered_plugins(plugins):
        ver = plugins[pid].get("version")
        line = plugins[pid].get("inject", "")
        blocks.append(f"<!-- plugin:{pid} v{ver} -->\n- {line}\n<!-- /plugin:{pid} -->")
    new_region = preamble + "\n\n" + "\n\n".join(blocks) + "\n\n"
    if new_region == region:
        print("[inject] region unchanged")
        return True
    plan.stage(AGENTS_MD, text[: m.start(1)] + new_region + text[m.end(1):])
    print(f"[inject] 待同步 {len(blocks)} 个插件块")
    return True


def do_check_inject(plugins, plan):
    """自各 manifest 的 checks 列表重建 check 命令注入区（在场即注册，幂等）。

    与 AGENTS.md 注入区同构：manifest 是本体，check 块是投影——改检查规则
    改 manifest checks 列表，投影与手写块的漂移就此消失。
    """
    if not os.path.exists(CHECK_SKILL):
        print("[check-inject] check command absent, skipped")
        return True
    text = plan.read(CHECK_SKILL)
    m = find_region(text, CHECK_INJECT_START, CHECK_INJECT_END)
    if not m:
        print("[error] check/SKILL.md: inject markers (check-inject:start/end) not found")
        return False
    blocks = []
    for pid in ordered_plugins(plugins):
        items = plugins[pid].get("checks") or []
        if not items:
            continue
        body = "\n".join(f"- {it}" for it in items)
        blocks.append(f"<!-- check:{pid} -->\n{body}\n<!-- /check:{pid} -->")
    new_region = "\n\n".join(blocks) + "\n" if blocks else "\n"
    if new_region == m.group(1):
        print("[check-inject] unchanged")
        return True
    plan.stage(CHECK_SKILL, text[: m.start(1)] + new_region + text[m.end(1):])
    print(f"[check-inject] 待同步 {len(blocks)} 个检查块")
    return True


def do_cmd_inject(plugins, plan):
    """自各 manifest 的 usage 列表按命令 consumes 序重建命令注入区（在场即注册，幂等）。

    第三种投影：插件写侧契约 → 命令。命令 frontmatter 声明 consumes（有序，
    序即执行序），各块为对应 manifest usage 列表原文——命令正文只留操作流程，
    字段契约与管道调用以本区为唯一文本源，装卸插件自动增删。
    """
    import wikilib

    ok = True
    for name in sorted(os.listdir(COMMANDS_DIR)):
        path = os.path.join(COMMANDS_DIR, name, "SKILL.md")
        if not os.path.exists(path):
            continue
        text = plan.read(path)
        consumes = wikilib.parse_frontmatter(text).get("consumes")
        if consumes is None:
            continue
        if not isinstance(consumes, list):
            consumes = _owner_list(consumes)
        m = find_region(text, CMD_INJECT_START, CMD_INJECT_END)
        if not m:
            print(f"[error] command {name}/: inject markers (cmd-inject:start/end) not found")
            ok = False
            continue
        blocks = []
        for pid in consumes:
            items = plugins.get(pid, {}).get("usage") or []
            if items:
                body = "\n".join(f"- {it}" for it in items)
                blocks.append(f"<!-- usage:{pid} -->\n{body}\n<!-- /usage:{pid} -->")
        new_region = "\n\n".join(blocks) + "\n" if blocks else "\n"
        if new_region == m.group(1):
            continue
        plan.stage(path, text[: m.start(1)] + new_region + text[m.end(1):])
        print(f"[cmd-inject] {name}: 待同步 {len(blocks)} 个用法块")
    return ok


def do_registry(plugins, plan):
    """自 manifests 的 fields 重建 registry.yaml 插件段（protocol / reserved 段不动）。"""
    text = plan.read(REGISTRY)
    m = re.search(r"^plugins:\n(.*?)^reserved:", text, re.S | re.M)
    if not m or len(re.findall(r"^plugins:", text, re.M)) != 1 or len(re.findall(r"^reserved:", text, re.M)) != 1:
        print("[error] registry.yaml: plugins:/reserved: section structure not found")
        return False
    lines = []
    for pid in sorted(plugins):
        fields = plugins[pid].get("fields")
        if not fields:
            continue  # 无自有字段的插件不入注册表插件段
        lines.append(f"  {pid}:")
        for f in sorted(fields):
            lines.append(f"    {f}:")
            lines.append(f"      note: {fields[f]}")
    body = "\n".join(lines) + "\n\n"
    if body == m.group(1):
        print("[registry] plugin section unchanged")
        return True
    plan.stage(REGISTRY, text[: m.start(1)] + body + text[m.end(1):])
    print("[registry] 插件段待同步")
    return True


def do_deploy(plan):
    """同步 .meta/command/*/SKILL.md → .agents/skills/*/SKILL.md；孤儿副本仅报告。"""
    names = sorted(
        d for d in os.listdir(COMMANDS_DIR)
        if os.path.isdir(os.path.join(COMMANDS_DIR, d))
    )
    orphans = []
    for name in names:
        src = os.path.join(COMMANDS_DIR, name, "SKILL.md")
        if not os.path.exists(src):
            raise ValueError(f"command {name}/: SKILL.md missing")
        dst_dir = os.path.join(SKILLS_DIR, name)
        dst = os.path.join(dst_dir, "SKILL.md")
        plan.stage(dst, plan.content(src))
    if os.path.isdir(SKILLS_DIR):
        for d in sorted(os.listdir(SKILLS_DIR)):
            if d not in names and os.path.isdir(os.path.join(SKILLS_DIR, d)):
                print(f"[warning] orphan copy .agents/skills/{d}/ (master gone; deletion belongs to human)")
                orphans.append(d)
    return orphans


def can_uninstall(plugins, target):
    """只报告阻塞原因；不移动目录，不自动级联。"""
    import wikilib

    if target not in plugins:
        print(f"[error] 未安装插件：{target}")
        return 1
    blockers = []
    for pid, manifest in sorted(plugins.items()):
        if target in manifest.get("depends", []):
            blockers.append(f"插件 {pid} 依赖 {target}")
    for name in sorted(os.listdir(COMMANDS_DIR)):
        path = os.path.join(COMMANDS_DIR, name, "SKILL.md")
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8") as handle:
            fm = wikilib.parse_frontmatter(handle.read())
        for field in ("owner", "consumes"):
            if target in _owner_list(fm.get(field) or ""):
                blockers.append(f"命令 {name} 的 {field} 引用 {target}")
    for message in blockers:
        print(f"[blocked] {message}")
    if blockers:
        print("[uninstall] 请先处理上述依赖和命令引用，再重新预检查；未移动任何文件")
        return 1
    print(f"[uninstall] {target} 可移出插件目录；预检查通过，未移动任何文件")
    return 0


def do_ls(plugins):
    for pid in sorted(plugins):
        deps = ", ".join(plugins[pid].get("depends") or []) or "—"
        cmds = ", ".join(plugins[pid].get("commands") or []) or "—"
        print(f"  {pid:<10} {plugins[pid].get('version', '?'):<6} deps {deps}; commands {cmds}")
    print(f"{len(plugins)} plugins (.meta/plugins/; injection order = dependency topo + alphabetical)")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    plugins, errors = load_plugins()
    if cmd == "ls":
        do_ls(plugins)
        if errors:
            print(f"[warning] {len(errors)} manifest load errors — run validate for details")
        return 0
    if cmd == "audit":
        for e in errors:
            print(e)
        result = do_audit(plugins, sys.argv[2] if len(sys.argv) > 2 else None)
        return 1 if errors else result
    if cmd not in ("validate", "inject", "registry", "deploy", "all", "verify", "can-uninstall"):
        print(__doc__)
        return 2
    validate(plugins, errors)
    if not errors:
        validate_bindings(plugins, errors)
    for e in errors:
        print(e)
    if errors:
        print(f"[result] validation failed ({len(errors)} errors) — mechanical actions blocked")
        return 1
    print(f"[validate] all {len(plugins)} plugins passed (fields / id match / deps exist / acyclic / command bindings)")
    if cmd == "can-uninstall":
        if len(sys.argv) != 3:
            print("用法：wiki_plugin_kernel.py can-uninstall <id>")
            return 2
        return can_uninstall(plugins, sys.argv[2])
    plan = ProjectionPlan()
    if cmd in ("inject", "all", "verify"):
        if not do_inject(plugins, plan):
            return 1
        if not do_check_inject(plugins, plan):
            return 1
        if not do_cmd_inject(plugins, plan):
            return 1
    if cmd in ("registry", "all", "verify"):
        if not do_registry(plugins, plan):
            return 1
    orphans = do_deploy(plan) if cmd in ("deploy", "all", "verify") else []
    ok = plan.apply(check_only=cmd == "verify")
    if cmd == "verify":
        ok = ok and not orphans
        print("[verify] " + ("投影与副本一致" if ok else "存在漂移或孤儿副本；未修改文件"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.dont_write_bytecode = True  # 只读检查也不产生 __pycache__
    try:
        sys.exit(main())
    except (OSError, ValueError) as exc:
        print(f"[error] {exc}")
        sys.exit(1)
