from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_builder():
    path = ROOT / "packaging" / "build_artifact.py"
    spec = importlib.util.spec_from_file_location("ocfg_build_artifact", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Artifact(unittest.TestCase):
    def test_stage_contains_agents_and_installers(self) -> None:
        dest = Path(tempfile.mkdtemp(prefix="ocfg-art-")) / "pack"
        _load_builder().stage(ROOT, dest)
        self.assertTrue((dest / "agents" / "code-reviewer.md").is_file())
        self.assertTrue((dest / "skills" / "cpp98" / "SKILL.md").is_file())
        self.assertTrue((dest / "install.py").is_file())
        self.assertTrue((dest / "install.bat").is_file())
        self.assertTrue((dest / "install.sh").is_file())
        self.assertTrue((dest / "vendor.bat").is_file())
        self.assertTrue((dest / "vendor.sh").is_file())
        self.assertTrue((dest / "packaging" / "versions.env").is_file())
        self.assertFalse((dest / "vendor" / "bin").exists())
        self.assertFalse(dest.suffix == ".zip")
        self.assertFalse(any(dest.rglob("*.zip")))

    def test_artifact_name_includes_opencode_version(self) -> None:
        mod = _load_builder()
        version = mod.read_opencode_version(ROOT)
        self.assertEqual(version, "1.18.10")
        self.assertEqual(
            mod.artifact_name(version, "linux"),
            "opencoderman-1.18.10-linux",
        )
        self.assertEqual(
            mod.artifact_name(version, "windows"),
            "opencoderman-1.18.10-windows",
        )
        self.assertFalse(mod.artifact_name(version, "linux").endswith(".zip"))

    def test_ci_uploads_folder_not_zip(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertIn("upload-artifact", workflow)
        self.assertIn("build_artifact.py", workflow)
        self.assertIn("code-reviewer.md", workflow)
        self.assertIn("PYTHONSAFEPATH", workflow)
        self.assertIn("vendor/bin/linux/opencode", workflow)
        self.assertIn("vendor\\bin\\windows\\opencode.exe", workflow)
        self.assertIn("tail -n 1", workflow)
        self.assertIn("--require-binary", workflow)
        self.assertNotIn("--skip-binary", workflow)
        self.assertNotIn("agents/review.md", workflow)
        self.assertNotIn("opencoderman-*-linux.zip", workflow)
        self.assertNotIn("opencoderman-*-windows.zip", workflow)

    def test_opencode_download_url(self) -> None:
        mod = _load_builder()
        ver = {
            "OPENCODE_VERSION": "1.18.10",
            "OPENCODE_REPO": "anomalyco/opencode",
            "OPENCODE_WINDOWS_ASSET": "opencode-windows-x64.zip",
            "OPENCODE_LINUX_ASSET": "opencode-linux-x64.tar.gz",
            "OPENCODE_DARWIN_ARM64_ASSET": "opencode-darwin-arm64.zip",
        }
        url, asset = mod.opencode_download_url(ver, "windows", "x64")
        self.assertEqual(asset, "opencode-windows-x64.zip")
        self.assertEqual(
            url,
            "https://github.com/anomalyco/opencode/releases/download/v1.18.10/opencode-windows-x64.zip",
        )
        self.assertTrue(mod.opencode_asset(ver, "linux", "x64").endswith(".tar.gz"))
        self.assertIn("arm64", mod.opencode_asset(ver, "darwin", "arm64"))
        self.assertEqual(mod.vendor_rel("windows", "x64"), ("windows", "opencode.exe"))
        self.assertEqual(mod.vendor_rel("linux", "x64"), ("linux", "opencode"))
        self.assertEqual(mod.vendor_rel("darwin", "arm64"), ("darwin-arm64", "opencode"))

    def test_attach_cli_copies_planted_vendor(self) -> None:
        import shutil

        dest = Path(tempfile.mkdtemp(prefix="ocfg-art-")) / "pack"
        dest.mkdir(parents=True)
        planted = Path(tempfile.mkdtemp(prefix="ocfg-ven-"))
        self.addCleanup(lambda: shutil.rmtree(planted, ignore_errors=True))
        src = planted / "vendor" / "bin" / "linux" / "opencode"
        src.parent.mkdir(parents=True)
        src.write_bytes(b"CLI")
        attached = _load_builder().attach_cli(planted, dest, "linux", "x64", fetch=False)
        self.assertIsNotNone(attached)
        copied = dest / "vendor" / "bin" / "linux" / "opencode"
        self.assertTrue(copied.is_file())
        self.assertEqual(copied.read_bytes(), b"CLI")

    def test_main_skip_binary_does_not_add_vendor(self) -> None:
        dest = Path(tempfile.mkdtemp(prefix="ocfg-skip-")) / "pack"
        rc = _load_builder().main(
            ["--root", str(ROOT), "--skip-binary", "--out", str(dest), "--os", "linux"]
        )
        self.assertEqual(rc, 0)
        self.assertTrue((dest / "install.py").is_file())
        self.assertFalse((dest / "vendor" / "bin").exists())

    def test_main_stdout_is_only_dest_path(self) -> None:
        import io
        from contextlib import redirect_stderr, redirect_stdout

        dest = Path(tempfile.mkdtemp(prefix="ocfg-out-")) / "pack"
        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = _load_builder().main(
                ["--root", str(ROOT), "--skip-binary", "--out", str(dest), "--os", "linux"]
            )
        self.assertEqual(rc, 0)
        lines = [line for line in out.getvalue().splitlines() if line.strip()]
        self.assertEqual(len(lines), 1, out.getvalue())
        self.assertEqual(Path(lines[0]), dest.resolve())

    def test_vendor_scripts_call_in_place(self) -> None:
        bat = (ROOT / "vendor.bat").read_text(encoding="utf-8")
        sh = (ROOT / "vendor.sh").read_text(encoding="utf-8")
        self.assertIn("build_artifact.py", bat)
        self.assertIn("--in-place", bat)
        self.assertIn("build_artifact.py", sh)
        self.assertIn("--in-place", sh)
        for line in bat.splitlines():
            if line.strip().upper().startswith("REM"):
                continue
            self.assertNotIn("->", line)


if __name__ == "__main__":
    unittest.main()
