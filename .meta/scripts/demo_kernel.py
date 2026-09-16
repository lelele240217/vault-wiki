"""建立独立体验库并运行机械演示；仅接受不存在的目标目录，不覆盖用户文件。"""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SOURCE = Path(__file__).resolve().parents[2]
IGNORE = shutil.ignore_patterns("__pycache__", "smoke-tmp")


def write(root, path, text):
    dest = root / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")


def call(root, *args, script="wiki_plugin_kernel.py"):
    result = subprocess.run([sys.executable, "-B", str(root / ".meta/scripts" / script), *args],
                            cwd=root, capture_output=True, text=True, encoding="utf-8", timeout=30)
    return result.returncode, result.stdout + result.stderr


def snapshot(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def main():
    if len(sys.argv) != 2:
        raise SystemExit("用法：python .meta/scripts/demo_kernel.py <新的体验库目录>")
    target = Path(sys.argv[1]).resolve()
    if target == SOURCE or SOURCE in target.parents:
        raise SystemExit("体验库须在框架仓库外，避免混入实例数据。")
    target.mkdir(parents=True, exist_ok=False)
    for folder in (".meta", ".agents"):
        shutil.copytree(SOURCE / folder, target / folder, ignore=IGNORE)
    agents = (SOURCE / "test-repo/AGENTS.md").read_text(encoding="utf-8")
    write(target, "AGENTS.md", agents.replace("# test-repo", "# 虚构会议体验库", 1))
    for folder in ("vault", "wiki/notes", "wiki/sessions", "wiki/vault"):
        (target / folder).mkdir(parents=True, exist_ok=True)
    write(target, "vault/demo-meeting.txt",
          "【虚构资料，仅用于演示，不是用户的真实会议】\n"
          "2026-09-16，示例团队讨论知识库插件。\n"
          "决定：本周先完善内核的检查与同步，不开发插件市场。\n"
          "理由：规则没同步时，AI 可能读到旧说明；先保证基础流程可靠。\n"
          "待办：小林在 2026-09-18 前整理三个插件使用场景。\n"
          "开放问题：用户是否愿意自己制作和分享插件，还需要访谈。\n")
    write(target, ".meta/plugins/meeting-guide/PLUGIN.yaml",
          "id: meeting-guide\nversion: 0.1\ndepends:\n  - notes\nupdated: 2026-09-16\n"
          "attachment: []\nfields: {}\n"
          "inject: 整理会议时分别写清决定、理由、待办，并链接原始资料代理页；本插件仅提供写作规则，不自动转录音频。\n"
          "usage:\n  - 输出决定、理由、待办；没有明确的信息写未说明，不编造。\n")
    write(target, ".meta/plugins/meeting-guide/PLUGIN.md",
          "# meeting-guide（教学示例）\n\n## Role\n会议整理规则。\n\n"
          "## Structure\n复用 notes 页面，无自有字段或命令。\n\n"
          "## Invariants\n保留来源，不补造负责人或日期。\n\n"
          "## Changelog\n0.1：演示规则通过 AGENTS 注入区进入上下文。\n")
    code, output = call(target, "all")
    if code:
        raise RuntimeError(output)
    for command in ("index", "tags"):
        code, output = call(target, command, script="pipeline.py")
        if code:
            raise RuntimeError(output)
    results = []
    for case in ("规则更新尚未同步", "同步后再检查", "卸载被依赖插件", "坏插件检查", "后段错误不留下半同步", "待办写日志"):
        with tempfile.TemporaryDirectory(prefix="vault-wiki-demo-") as tmp:
            root = Path(tmp)
            for folder in (".meta", ".agents", "wiki", "vault"):
                shutil.copytree(target / folder, root / folder, ignore=IGNORE)
            shutil.copyfile(target / "AGENTS.md", root / "AGENTS.md")
            manifest = root / ".meta/plugins/meeting-guide/PLUGIN.yaml"
            evidence = ""
            if case in ("规则更新尚未同步", "同步后再检查", "后段错误不留下半同步"):
                manifest.write_text(manifest.read_text(encoding="utf-8").replace("version: 0.1", "version: 0.2"), encoding="utf-8")
            if case == "规则更新尚未同步":
                before = snapshot(root)
                code, output = call(root, "verify")
                passed = code == 1 and "AGENTS.md" in output and before == snapshot(root)
                evidence = "发现版本漂移，检查没有改变文件。"
            elif case == "同步后再检查":
                code1, out1 = call(root, "all")
                before = snapshot(root)
                code, output = call(root, "verify")
                code2, out2 = call(root, "all")
                passed = code1 == code == code2 == 0 and before == snapshot(root)
                output = out1 + output + out2
                evidence = "同步后通过检查；重复同步没有额外变化。"
            elif case == "卸载被依赖插件":
                before = snapshot(root)
                code, output = call(root, "can-uninstall", "notes")
                passed = code == 1 and "meeting-guide" in output and before == snapshot(root)
                evidence = "指出 meeting-guide 依赖 notes，且没有移动任何文件。"
            elif case == "坏插件检查":
                write(root, ".meta/plugins/broken/PLUGIN.md", "缺少声明的演示插件")
                code, output = call(root, "audit")
                passed = code == 1 and "broken" in output
                evidence = "缺少声明的插件使检查明确失败。"
            elif case == "后段错误不留下半同步":
                registry = root / ".meta/protocol/registry.yaml"
                registry.write_text(registry.read_text(encoding="utf-8").replace("reserved:", "broken:"), encoding="utf-8")
                before = snapshot(root)
                code, output = call(root, "all")
                passed = code == 1 and before == snapshot(root)
                evidence = "发现后续注册表结构错误；全部原文件保持不变。"
            else:
                code, output = call(root, "log", "todo", "完成虚构待办", script="pipeline.py")
                passed = code == 0 and "todo：完成虚构待办" in (root / "wiki/log.md").read_text(encoding="utf-8")
                evidence = "todo 类型日志成功写入。"
            results.append(f"## {case}：{'通过' if passed else '失败'}\n\n{evidence}\n\n```text\n{output.strip()}\n```\n")
            if not passed:
                raise RuntimeError(case + "\n" + output)
    write(target, "DEMO-RESULTS.md", "# 内核机械演示结果\n\n"
          "以下为实际执行结果。每个故障在独立临时副本中制造，不破坏本体验库。\n"
          "退出码 1 在故障场景中是预期的阻止结果，不是演示失败。\n\n" + "\n".join(results))
    write(target, "START-HERE.md", "# 从这里开始\n\n"
          "这是一个独立的虚构会议体验库，无需 GitHub 操作。\n\n"
          "1. 打开 vault/demo-meeting.txt 看原始资料。\n"
          "2. 对 Agent 说：把这份虚构会议整理进知识库，我授权在这个演示目录创建代理页和笔记。\n"
          "3. 查看 wiki/vault/ 的资料卡和 wiki/notes/ 的整理结果。\n"
          "4. 打开 DEMO-RESULTS.md 查看已执行的六个内核场景。\n\n"
          "你也可以说：检查这个体验库的插件规则是否同步，先不要修复。\n\n"
          "此目录不是独立聊天软件；资料理解由 Agent 完成，脚本负责同步与检查。\n"
          "本地体验不需要推送到 GitHub。脚本不会调用模型，也不会自动转录音频。\n")
    print(f"体验库已建立：{target}\n六个机械场景全部通过；请打开 START-HERE.md。")


if __name__ == "__main__":
    main()
