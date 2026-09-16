"""第一轮缺陷复现；每例在系统临时目录复制框架，不触碰真实知识库。"""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[2]


class KernelReliability(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="vault-wiki-check-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name in (".meta", ".agents"):
            shutil.copytree(SOURCE / name, self.root / name,
                            ignore=shutil.ignore_patterns("__pycache__", "smoke-tmp"))
        shutil.copyfile(SOURCE / "AGENTS.md", self.root / "AGENTS.md")
        (self.root / "wiki").mkdir()
        (self.root / "vault").mkdir()

    def run_cli(self, *args, script="wiki_plugin_kernel.py"):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        return subprocess.run([sys.executable, "-B", str(self.root / ".meta/scripts" / script), *args],
                              cwd=self.root, env=env, capture_output=True, text=True,
                              encoding="utf-8", timeout=30)

    def write(self, rel, text):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def replace(self, rel, old, new):
        path = self.root / rel
        self.write(rel, path.read_text(encoding="utf-8").replace(old, new))

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes()
                for p in self.root.rglob("*") if p.is_file() and "__pycache__" not in p.parts}

    def test_audit_load_error_is_failure(self):
        self.write(".meta/plugins/broken/PLUGIN.md", "缺少声明的插件")
        result = self.run_cli("audit")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("broken", result.stdout)

    def test_bad_audit_result_does_not_hide_other_checks(self):
        for bad in ("[{'level': 'oops', 'message': 'bad'}]", "['bad']", "None"):
            with self.subTest(bad=bad):
                self.write(".meta/plugins/hot/scripts/check.py", f"def check(ctx):\n    return {bad}\n")
                self.write(".meta/plugins/log/scripts/check.py",
                           "def check(ctx):\n    return [{'level': 'info', 'message': 'STILL-RAN'}]\n")
                result = self.run_cli("audit")
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn("STILL-RAN", result.stdout)
                self.assertNotIn("Traceback", result.stderr)

    def test_unknown_audit_target_is_failure(self):
        self.assertEqual(self.run_cli("audit", "not-installed").returncode, 1)

    def test_late_marker_error_does_not_partially_write(self):
        self.replace(".meta/plugins/hot/PLUGIN.yaml", "version: 0.9", "version: 0.99")
        self.replace(".meta/protocol/registry.yaml", "reserved:", "broken:")
        before = self.snapshot()
        result = self.run_cli("all")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertEqual(before, self.snapshot())

    def test_duplicate_marker_is_rejected_without_writes(self):
        self.replace("AGENTS.md", "<!-- wiki-inject:end -->",
                     "<!-- wiki-inject:end -->\n<!-- wiki-inject:end -->")
        before = self.snapshot()
        self.assertEqual(self.run_cli("all").returncode, 1)
        self.assertEqual(before, self.snapshot())

    def test_uninstall_precheck_is_targeted_and_read_only(self):
        before = self.snapshot()
        result = self.run_cli("can-uninstall", "wiki")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("mapping", result.stdout)
        result = self.run_cli("can-uninstall", "user-profile")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("save", result.stdout)
        self.assertEqual(self.run_cli("can-uninstall", "todo").returncode, 0)
        self.assertEqual(before, self.snapshot())

    def test_consistency_readonly_and_sync_idempotent(self):
        self.assertEqual(self.run_cli("all").returncode, 0)
        self.replace(".meta/plugins/hot/PLUGIN.yaml", "version: 0.9", "version: 0.99")
        before = self.snapshot()
        result = self.run_cli("verify")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("AGENTS.md", result.stdout)
        self.assertEqual(before, self.snapshot())
        self.assertEqual(self.run_cli("all").returncode, 0)
        before = self.snapshot()
        self.assertEqual(self.run_cli("verify").returncode, 0)
        self.assertEqual(self.run_cli("all").returncode, 0)
        self.assertEqual(before, self.snapshot())
        self.write(".agents/skills/save/SKILL.md", "旧副本")
        result = self.run_cli("verify")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("save", result.stdout)

    def test_orphan_copy_is_reported_and_preserved(self):
        self.assertEqual(self.run_cli("all").returncode, 0)
        self.write(".agents/skills/orphan/SKILL.md", "用户保留的副本")
        before = self.snapshot()
        result = self.run_cli("verify")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("orphan", result.stdout)
        self.assertEqual(before, self.snapshot())

    def test_todo_log_preserves_history(self):
        old = "- 2026-09-01 other：原有事件"
        self.write("wiki/log.md", "# 日志\n\n" + old + "\n")
        result = self.run_cli("log", "todo", "完成演示待办", script="pipeline.py")
        self.assertEqual(result.returncode, 0, result.stdout)
        text = (self.root / "wiki/log.md").read_text(encoding="utf-8")
        self.assertIn("todo：完成演示待办", text)
        self.assertIn(old, text)

    def test_all_projection_surfaces_and_handwritten_text(self):
        self.assertEqual(self.run_cli("all").returncode, 0)
        for rel, marker in (
            (".meta/command/check/SKILL.md", "<!-- check-inject:start -->"),
            (".meta/command/save/SKILL.md", "<!-- cmd-inject:start -->"),
            (".meta/protocol/registry.yaml", "plugins:"),
        ):
            with self.subTest(rel=rel):
                self.replace(rel, marker, marker + "\nSTALE-PROJECTION")
                before = self.snapshot()
                result = self.run_cli("verify")
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertEqual(before, self.snapshot())
                self.assertEqual(self.run_cli("all").returncode, 0)
                self.assertNotIn("STALE-PROJECTION", (self.root / rel).read_text(encoding="utf-8"))
        agents = (self.root / "AGENTS.md").read_text(encoding="utf-8")
        self.write("AGENTS.md", "手写前言\n" + agents + "\n手写后记\n")
        self.replace(".meta/plugins/hot/PLUGIN.yaml", "version: 0.9", "version: 0.99")
        self.assertEqual(self.run_cli("all").returncode, 0)
        actual = (self.root / "AGENTS.md").read_text(encoding="utf-8")
        self.assertTrue(actual.startswith("手写前言\n"))
        self.assertTrue(actual.endswith("\n手写后记\n"))

    def test_invalid_field_type_is_reported_before_writing(self):
        self.replace(".meta/plugins/log/PLUGIN.yaml", "fields: {}", "fields: invalid")
        before = self.snapshot()
        result = self.run_cli("all")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("fields", result.stdout)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(before, self.snapshot())


if __name__ == "__main__":
    unittest.main(verbosity=2)
