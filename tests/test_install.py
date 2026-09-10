from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import install  # noqa: E402


class PathHelpers(unittest.TestCase):
    def test_detects_default_and_dedicated_bin(self) -> None:
        self.assertTrue(install.is_opencode_bin_entry(r"C:\Users\x\.opencode\bin"))
        self.assertTrue(install.is_opencode_bin_entry("C:/Users/x/.opencode/bin"))
        self.assertTrue(install.is_opencode_bin_entry("/home/x/.opencode/bin"))
        self.assertTrue(install.is_opencode_bin_entry(r"C:\tools\opencode\bin"))
        self.assertTrue(install.is_opencode_bin_entry("/opt/opencode/bin"))
        self.assertFalse(install.is_opencode_bin_entry("/usr/local/bin"))
        self.assertFalse(install.is_opencode_bin_entry(r"C:\tools\bin"))
        self.assertFalse(install.is_opencode_bin_entry("C:/tools/bin"))
        self.assertFalse(install.is_opencode_bin_entry(""))

    def test_dedicated_root_from_binary(self) -> None:
        import tempfile

        tmp = Path(tempfile.mkdtemp(prefix="ocfg-"))
        self.addCleanup(lambda: __import__("shutil").rmtree(tmp, ignore_errors=True))
        binary = tmp / "apps" / "opencode" / "bin" / "opencode.exe"
        binary.parent.mkdir(parents=True)
        binary.write_text("x", encoding="utf-8")
        root = install.dedicated_install_root(binary)
        self.assertEqual(root, binary.resolve().parent.parent)

    def test_strip_removes_only_opencode_bin(self) -> None:
        parts = [r"C:\Windows", r"C:\Users\x\.opencode\bin", r"C:\git\cmd"]
        kept = install.strip_opencode_bin_entries(parts)
        self.assertEqual(kept, [r"C:\Windows", r"C:\git\cmd"])

    def test_norm_path_resolves_existing_dir(self) -> None:
        import tempfile

        tmp = Path(tempfile.mkdtemp(prefix="ocfg-"))
        self.addCleanup(lambda: __import__("shutil").rmtree(tmp, ignore_errors=True))
        self.assertEqual(install._norm_path(str(tmp)), install._norm_path(str(tmp.resolve())))

    def test_profile_block_roundtrip(self) -> None:
        raw = "export PATH=/usr/bin\n"
        written = install.insert_profile_block(raw)
        self.assertIn(install.PATH_BEGIN, written)
        self.assertIn("opencoderman PATH", written)
        self.assertIn(install.PATH_EXPORT, written)
        cleaned = install.strip_profile_block(written)
        self.assertEqual(cleaned.strip(), "export PATH=/usr/bin")

    def test_other_path_block_markers_are_stripped(self) -> None:
        raw = (
            "keep=1\n"
            "# >>> leftover PATH >>>\n"
            'export PATH="$HOME/.opencode/bin:$PATH"\n'
            "# <<< leftover PATH <<<\n"
        )
        cleaned = install.strip_profile_block(raw)
        self.assertEqual(cleaned.strip(), "keep=1")
        self.assertNotIn("leftover PATH", cleaned)

    def test_review_agent_is_opencoderman(self) -> None:
        text = (ROOT / "agents" / "code-reviewer.md").read_text(encoding="utf-8")
        self.assertIn("You are OpenCoderman", text)
        self.assertIn("OpenCoderman code reviewer", text)
        self.assertIn("opencoderman-findings", text)


class ReplaceInstall(unittest.TestCase):
    def test_lists_shipped_agents_and_skills(self) -> None:
        agents = [p.stem for p in install.list_agent_files(ROOT)]
        skills = [p.name for p in install.list_skill_dirs(ROOT)]
        self.assertIn("code-reviewer", agents)
        self.assertIn("derman-build", agents)
        self.assertIn("derman-plan", agents)
        self.assertIn("cpp98", skills)
        self.assertIn("modern-cpp", skills)
        self.assertIn("cpp-memory-safety", skills)
        self.assertIn("cmake-cpp", skills)
        self.assertIn("secrets", skills)
        self.assertIn("python", skills)
        self.assertIn("web-security", skills)
        self.assertIn("frontend-ui", skills)
        self.assertIn("security-owasp", skills)
        self.assertIn("go", skills)
        self.assertIn("git-commits", skills)
        self.assertIn("planning", skills)
        self.assertIn("typescript", skills)
        self.assertIn("react", skills)
        self.assertIn("android", skills)
        self.assertIn("django", skills)
        self.assertIn("postgresql", skills)
        self.assertIn("aws", skills)
        self.assertIn("machine-learning", skills)
        self.assertGreaterEqual(len(skills), 70)

    def test_derman_plan_bash_is_git_read_only(self) -> None:
        text = (ROOT / "agents" / "derman-plan.md").read_text(encoding="utf-8")
        bash = text.split("bash:", 1)[1].split("edit:", 1)[0]
        self.assertRegex(bash, r'"\*"\s*:\s*deny')
        for getter in (
            '"git log*"',
            '"git show*"',
            '"git status*"',
            '"git blame*"',
            '"git rev-parse*"',
            '"git ls-files*"',
            '"git show-ref*"',
            '"git for-each-ref*"',
            '"git reflog*"',
            '"git branch --show-current*"',
            '"git tag -l*"',
            '"git remote -v*"',
            '"git stash list*"',
            '"git config --get*"',
            '"rg *"',
        ):
            self.assertIn(getter, bash, f"missing getter allow {getter}")
        self.assertNotIn("git-commits: allow", text)
        self.assertNotIn('"git push*"', bash)
        self.assertNotIn('"git commit*"', bash)
        self.assertNotIn('"git add*"', bash)
        self.assertNotIn('"git checkout*"', bash)
        self.assertNotIn('"git reset*"', bash)

    def test_derman_build_bash_denies_push(self) -> None:
        text = (ROOT / "agents" / "derman-build.md").read_text(encoding="utf-8")
        self.assertIn('"git push*"', text)
        self.assertIn('"git send-pack*"', text)
        self.assertIn('"git checkout*"', text)
        self.assertIn('"git switch*"', text)
        self.assertIn('"git checkout --*"', text)
        self.assertIn("Stay on that HEAD", text)
        bash = text.split("bash:", 1)[1].split("skill:", 1)[0]
        star = bash.find('"*"')
        checkout_deny = bash.find('"git checkout*"')
        restore = bash.find('"git checkout --*"')
        self.assertTrue(star != -1 and checkout_deny > star, bash)
        self.assertTrue(restore > checkout_deny, bash)
        self.assertIn("git-commits: allow", text)
        self.assertIn("Do **not** `git push`", text)
        self.assertIn("current working directory", text)

    def test_derman_agents_do_not_treat_host_data_dir_as_the_repo(self) -> None:
        for name in ("derman-plan.md", "derman-build.md", "derman-test.md"):
            text = (ROOT / "agents" / name).read_text(encoding="utf-8")
            self.assertNotIn("KAN-481", text, name)
            self.assertNotIn("C:\\vd\\yaver", text, name)
            self.assertNotIn("/vd/yaver", text, name)
            self.assertIn("current working directory", text, name)
            self.assertIn("parent directory", text, name)
            self.assertIn("host data", text, name)
        plan = (ROOT / "agents" / "derman-plan.md").read_text(encoding="utf-8")
        self.assertIn("PLAN_DONE", plan)
        self.assertIn("questions: none", plan)
        tester = (ROOT / "agents" / "derman-test.md").read_text(encoding="utf-8")
        self.assertIn("AGENTS.md", tester)
        self.assertIn("Unit test best practices", tester)
        self.assertIn("unit tests", tester.lower())
        self.assertIn("line", tester.lower())
        self.assertIn("branch", tester.lower())
        self.assertIn("condition", tester.lower())
        self.assertIn("Not hacky", tester)
        self.assertIn("expect_call", tester)
        self.assertIn("exact", tester.lower())
        self.assertIn("assert_not_called", tester)
        self.assertIn("assert_has_calls", tester)
        self.assertIn("must fail", tester)
        self.assertIn("Boundaries", tester)
        self.assertIn("When you are done", tester)

    def test_derman_build_allows_every_shipped_skill(self) -> None:
        text = (ROOT / "agents" / "derman-build.md").read_text(encoding="utf-8")
        skills = [p.name for p in install.list_skill_dirs(ROOT)]
        missing = [name for name in skills if f"{name}: allow" not in text]
        self.assertEqual(missing, [], f"derman-build missing skill allows: {missing}")

    def test_reviewer_allows_non_implementer_skills(self) -> None:
        text = (ROOT / "agents" / "gitlab-reviewer.md").read_text(encoding="utf-8")
        skip = {"tdd", "debugging", "git-commits", "planning"}
        skills = [p.name for p in install.list_skill_dirs(ROOT)]
        missing = [
            name
            for name in skills
            if name not in skip and f"{name}: allow" not in text
        ]
        self.assertEqual(missing, [], f"gitlab-reviewer missing skill allows: {missing}")

    def test_purge_removes_homes_and_path(self) -> None:
        import tempfile

        tmp = Path(tempfile.mkdtemp(prefix="ocfg-"))
        self.addCleanup(lambda: __import__("shutil").rmtree(tmp, ignore_errors=True))
        oc = tmp / ".opencode"
        cfg = tmp / ".config" / "opencode"
        (oc / "bin").mkdir(parents=True)
        (oc / "bin" / "old.exe").write_text("old", encoding="utf-8")
        (cfg / "agents").mkdir(parents=True)
        (cfg / "agents" / "stale.md").write_text("stale", encoding="utf-8")
        (tmp / ".opencode-path").write_text(
            install.join_path([str(oc / "bin"), str(tmp / "keep-me")]),
            encoding="utf-8",
        )
        profile = tmp / ".profile"
        profile.write_text(install.insert_profile_block("keep=1\n"), encoding="utf-8")

        dropped = install.remove_from_path(user_home=tmp)
        self.assertTrue(any(install.is_opencode_bin_entry(p) for p in dropped))
        kept = install.split_path((tmp / ".opencode-path").read_text(encoding="utf-8"))
        self.assertEqual(kept, [str(tmp / "keep-me")])
        self.assertNotIn(install.PATH_BEGIN, profile.read_text(encoding="utf-8"))

        install.purge_homes(tmp)
        self.assertFalse(oc.exists())
        self.assertFalse(cfg.exists())
        backups = list(tmp.glob(".opencode_backup_*"))
        self.assertEqual(len(backups), 1)
        self.assertTrue((backups[0] / "bin" / "old.exe").is_file())
        cfg_backups = list((tmp / ".config").glob("opencode_backup_*"))
        self.assertEqual(len(cfg_backups), 1)
        self.assertTrue((cfg_backups[0] / "agents" / "stale.md").is_file())

    def test_install_replaces_old_tree(self) -> None:
        import tempfile
        import shutil

        tmp = Path(tempfile.mkdtemp(prefix="ocfg-"))
        self.addCleanup(lambda: shutil.rmtree(tmp, ignore_errors=True))
        old = tmp / ".opencode" / "keep-old.txt"
        old.parent.mkdir(parents=True)
        old.write_text("old", encoding="utf-8")
        (tmp / ".opencode" / "bin").mkdir()
        (tmp / ".opencode-path").write_text(str(tmp / ".opencode" / "bin"), encoding="utf-8")

        leftover = tmp / ".config" / "opencode" / "agents" / "stale.md"
        leftover.parent.mkdir(parents=True)
        leftover.write_text("stale", encoding="utf-8")

        dest = install.install(ROOT, user_home=tmp)
        self.assertTrue(dest.is_file())
        self.assertEqual(dest, tmp / ".opencode" / "agents" / "code-reviewer.md")
        self.assertFalse(old.exists())
        backups = list(tmp.glob(".opencode_backup_*"))
        self.assertEqual(len(backups), 1)
        self.assertTrue((backups[0] / "keep-old.txt").is_file())
        self.assertIn("mode: primary", dest.read_text(encoding="utf-8"))
        self.assertTrue((tmp / ".opencode" / "skills" / "cpp98" / "SKILL.md").is_file())
        self.assertTrue((tmp / ".opencode" / "opencode.json").is_file())
        self.assertFalse((tmp / ".config" / "opencode").exists())
        cfg_backups = list((tmp / ".config").glob("opencode_backup_*"))
        self.assertEqual(len(cfg_backups), 1)
        self.assertTrue((cfg_backups[0] / "agents" / "stale.md").is_file())
        path = install.split_path((tmp / ".opencode-path").read_text(encoding="utf-8"))
        self.assertTrue(path)
        self.assertTrue(install.is_opencode_bin_entry(path[0]))
        self.assertEqual(len([p for p in path if install.is_opencode_bin_entry(p)]), 1)

    def test_backup_destination_uses_timestamp(self) -> None:
        from datetime import datetime

        dest = install.backup_destination(
            Path("/tmp/.opencode"), when=datetime(2026, 9, 4, 15, 30, 45)
        )
        self.assertEqual(dest.name, ".opencode_backup_20260904_153045")

    def test_install_picks_up_new_agent_file(self) -> None:
        import tempfile
        import shutil

        tmp = Path(tempfile.mkdtemp(prefix="ocfg-"))
        pack = tmp / "pack"
        shutil.copytree(ROOT / "agents", pack / "agents")
        shutil.copytree(ROOT / "skills", pack / "skills")
        (pack / "agents" / "extra.md").write_text("---\nmode: primary\n---\nextra\n", encoding="utf-8")
        home = tmp / "home"
        install.install(pack, user_home=home)
        self.assertTrue((home / ".opencode" / "agents" / "extra.md").is_file())
        self.assertFalse((home / ".config" / "opencode").exists())

    def test_custom_location_kept_on_disk_removed_from_path(self) -> None:
        import tempfile
        import shutil

        tmp = Path(tempfile.mkdtemp(prefix="ocfg-"))
        self.addCleanup(lambda: shutil.rmtree(tmp, ignore_errors=True))
        home = tmp / "home"
        custom = tmp / "apps" / "opencode" / "bin"
        custom.mkdir(parents=True)
        (custom / "opencode.exe").write_text("old", encoding="utf-8")
        keep = tmp / "keep-me"
        home.mkdir(parents=True)
        (home / ".opencode-path").write_text(
            install.join_path([str(custom), str(keep)]),
            encoding="utf-8",
        )
        install.install(ROOT, user_home=home)
        self.assertTrue((custom / "opencode.exe").is_file())
        path = install.split_path((home / ".opencode-path").read_text(encoding="utf-8"))
        self.assertNotIn(str(custom), path)
        self.assertIn(str(keep), path)
        self.assertTrue((home / ".opencode" / "agents" / "code-reviewer.md").is_file())
        self.assertFalse((home / ".config" / "opencode").exists())

    def test_shared_bin_files_kept_path_unhooked(self) -> None:
        import tempfile
        import shutil

        tmp = Path(tempfile.mkdtemp(prefix="ocfg-"))
        self.addCleanup(lambda: shutil.rmtree(tmp, ignore_errors=True))
        tools = tmp / "tools" / "bin"
        tools.mkdir(parents=True)
        (tools / "opencode.exe").write_text("old", encoding="utf-8")
        (tools / "git.exe").write_text("git", encoding="utf-8")
        home = tmp / "home"
        (home / ".opencode-path").parent.mkdir(parents=True)
        (home / ".opencode-path").write_text(str(tools), encoding="utf-8")
        install.install(ROOT, user_home=home)
        self.assertTrue((tools / "opencode.exe").is_file())
        self.assertTrue((tools / "git.exe").exists())
        path = install.split_path((home / ".opencode-path").read_text(encoding="utf-8"))
        self.assertNotIn(str(tools), path)

    def _plant_cli(self, root: Path, payload: bytes = b"NEW") -> Path:
        path = root / "vendor" / "bin" / install.vendor_bin_tag() / install.binary_name()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        return path

    def test_vendor_binary_prefers_os_folder(self) -> None:
        import tempfile
        import shutil

        tmp = Path(tempfile.mkdtemp(prefix="ocfg-"))
        self.addCleanup(lambda: shutil.rmtree(tmp, ignore_errors=True))
        planted = self._plant_cli(tmp, b"OS")
        (tmp / "vendor" / "bin" / install.binary_name()).write_bytes(b"FLAT")
        got = install.vendor_binary(tmp)
        self.assertEqual(got, planted)
        self.assertEqual(got.read_bytes(), b"OS")

    def test_install_copies_vendored_cli(self) -> None:
        import tempfile
        import shutil

        tmp = Path(tempfile.mkdtemp(prefix="ocfg-"))
        self.addCleanup(lambda: shutil.rmtree(tmp, ignore_errors=True))
        pack = tmp / "pack"
        shutil.copytree(ROOT / "agents", pack / "agents")
        shutil.copytree(ROOT / "skills", pack / "skills")
        self._plant_cli(pack, b"NEW")
        home = tmp / "home"
        install.install(pack, user_home=home)
        dest = home / ".opencode" / "bin" / install.binary_name()
        self.assertTrue(dest.is_file())
        self.assertEqual(dest.read_bytes(), b"NEW")

    def test_install_reuses_backup_cli_when_vendor_missing(self) -> None:
        import tempfile
        import shutil

        tmp = Path(tempfile.mkdtemp(prefix="ocfg-"))
        self.addCleanup(lambda: shutil.rmtree(tmp, ignore_errors=True))
        pack = tmp / "pack"
        shutil.copytree(ROOT / "agents", pack / "agents")
        shutil.copytree(ROOT / "skills", pack / "skills")
        home = tmp / "home"
        oc = home / ".opencode"
        (oc / "bin").mkdir(parents=True)
        (oc / "bin" / install.binary_name()).write_bytes(b"OLD-BINARY")
        install.install(pack, user_home=home)
        dest = home / ".opencode" / "bin" / install.binary_name()
        self.assertTrue(dest.is_file())
        self.assertEqual(dest.read_bytes(), b"OLD-BINARY")
        backups = list(home.glob(".opencode_backup_*"))
        self.assertEqual(len(backups), 1)

    def test_install_without_vendor_is_agents_skills_only(self) -> None:
        import tempfile
        import shutil

        tmp = Path(tempfile.mkdtemp(prefix="ocfg-"))
        self.addCleanup(lambda: shutil.rmtree(tmp, ignore_errors=True))
        pack = tmp / "pack"
        shutil.copytree(ROOT / "agents", pack / "agents")
        shutil.copytree(ROOT / "skills", pack / "skills")
        home = tmp / "home"
        install.install(pack, user_home=home)
        dest = home / ".opencode" / "bin" / install.binary_name()
        self.assertFalse(dest.exists())
        self.assertTrue((home / ".opencode" / "agents" / "code-reviewer.md").is_file())
        self.assertFalse((home / ".config" / "opencode").exists())

    def test_require_binary_fails_without_cli(self) -> None:
        import tempfile
        import shutil

        tmp = Path(tempfile.mkdtemp(prefix="ocfg-"))
        self.addCleanup(lambda: shutil.rmtree(tmp, ignore_errors=True))
        pack = tmp / "pack"
        shutil.copytree(ROOT / "agents", pack / "agents")
        shutil.copytree(ROOT / "skills", pack / "skills")
        with self.assertRaises(FileNotFoundError) as ctx:
            install.install(pack, user_home=tmp / "home", require_binary=True)
        self.assertIn("vendor", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
