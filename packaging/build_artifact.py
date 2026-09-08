#!/usr/bin/env python3
"""Stage OpenCoderman as a folder. GitHub Actions zips the upload; do not zip here.

By default the staged folder includes the OpenCode CLI for that OS
(downloaded here; target install.py is offline). --skip-binary builds
an agents/skills-only folder. --in-place writes vendor/bin into the
checkout.
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

INCLUDE = (
    "README.md",
    "install.py",
    "install.bat",
    "install.sh",
    "vendor.bat",
    "vendor.sh",
    "agents",
    "skills",
    "packaging/versions.env",
)


def read_versions(root: Path) -> dict[str, str]:
    path = Path(root) / "packaging" / "versions.env"
    if not path.is_file():
        raise SystemExit(f"missing {path}")
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip()
    return out


def read_opencode_version(root: Path) -> str:
    version = read_versions(root).get("OPENCODE_VERSION", "").strip()
    if not version:
        raise SystemExit(f"OPENCODE_VERSION missing in {Path(root) / 'packaging' / 'versions.env'}")
    return version


def artifact_name(version: str, os_tag: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in version)
    tag = os_tag.strip().lower()
    return f"opencoderman-{safe}-{tag}"


def host_platform() -> tuple[str, str]:
    machine = platform.machine().lower()
    if os.name == "nt":
        os_tag = "windows"
    elif sys.platform == "darwin":
        os_tag = "darwin"
    else:
        os_tag = "linux"
    if machine in {"arm64", "aarch64"}:
        arch = "arm64"
    else:
        arch = "x64"
    return os_tag, arch


def vendor_rel(os_tag: str, arch: str) -> tuple[str, str]:
    """Return (vendor/bin/<dir>, binary file name) for this OS."""
    tag = os_tag.strip().lower()
    if tag == "windows":
        return "windows", "opencode.exe"
    if tag == "linux":
        return "linux", "opencode"
    if tag == "darwin":
        suffix = "arm64" if arch == "arm64" else "x64"
        return f"darwin-{suffix}", "opencode"
    raise SystemExit(f"unsupported os {os_tag!r}")


def opencode_asset(ver: dict[str, str], os_tag: str, arch: str) -> str:
    tag = os_tag.strip().lower()
    if tag == "windows":
        return ver.get("OPENCODE_WINDOWS_ASSET") or "opencode-windows-x64.zip"
    if tag == "linux":
        if arch == "arm64":
            return "opencode-linux-arm64.tar.gz"
        return ver.get("OPENCODE_LINUX_ASSET") or "opencode-linux-x64.tar.gz"
    if tag == "darwin":
        if arch == "arm64":
            return ver.get("OPENCODE_DARWIN_ARM64_ASSET") or "opencode-darwin-arm64.zip"
        return ver.get("OPENCODE_DARWIN_X64_ASSET") or "opencode-darwin-x64.zip"
    raise SystemExit(f"unsupported os {os_tag!r}")


def opencode_download_url(ver: dict[str, str], os_tag: str, arch: str) -> tuple[str, str]:
    version = (ver.get("OPENCODE_VERSION") or "").strip()
    if not version:
        raise SystemExit("OPENCODE_VERSION missing")
    repo = ver.get("OPENCODE_REPO") or "anomalyco/opencode"
    asset = opencode_asset(ver, os_tag, arch)
    return f"https://github.com/{repo}/releases/download/v{version}/{asset}", asset


def find_file(root: Path, names: tuple[str, ...]) -> Path | None:
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in names:
            if name in filenames:
                return Path(dirpath) / name
    return None


def extract_archive(archive: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    name = archive.name.lower()
    if name.endswith(".zip"):
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(dest)
        return
    if name.endswith(".tar.gz") or name.endswith(".tgz"):
        with tarfile.open(archive, "r:gz") as tf:
            tf.extractall(dest)
        return
    raise SystemExit(f"Unknown archive type: {archive}")


def _log(message: str) -> None:
    # stdout is only the dest path so `dest=$(python ...)` stays a single line.
    print(message, file=sys.stderr)


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    _log(f"  Downloading {url}")
    _log(f"           to {dest}")
    req = urllib.request.Request(url, headers={"User-Agent": "opencoderman-vendor"})
    with urllib.request.urlopen(req) as resp, dest.open("wb") as handle:
        shutil.copyfileobj(resp, handle)
    size = dest.stat().st_size
    _log(f"  OK ({size / (1024 * 1024):.1f} MB)")


def copy_opencode_binary(src: Path, dest_bin: Path) -> Path:
    dest_bin.mkdir(parents=True, exist_ok=True)
    target = dest_bin / src.name
    shutil.copy2(src, target)
    if src.name != "opencode.exe":
        target.chmod(target.stat().st_mode | 0o111)
    _log(f"  OpenCode binary: {target} ({target.stat().st_size / (1024 * 1024):.1f} MB)")
    return target


def fetch_opencode(ver: dict[str, str], os_tag: str, arch: str, dest_bin: Path) -> str:
    url, asset = opencode_download_url(ver, os_tag, arch)
    dest_bin.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ocfg-oc-") as tmp:
        tmp_path = Path(tmp)
        archive = tmp_path / asset
        download(url, archive)
        extracted = tmp_path / "extract"
        extract_archive(archive, extracted)
        names = ("opencode.exe", "opencode") if os_tag == "windows" else ("opencode", "opencode.exe")
        binary = find_file(extracted, names)
        if binary is None:
            raise SystemExit(f"OpenCode binary not found in {asset}")
        copy_opencode_binary(binary, dest_bin)
    return asset


def existing_vendor_binary(root: Path, os_tag: str, arch: str) -> Path | None:
    folder, name = vendor_rel(os_tag, arch)
    vendor_bin = Path(root) / "vendor" / "bin"
    for path in (vendor_bin / folder / name, vendor_bin / name):
        if path.is_file():
            return path
    return None


def attach_cli(
    root: Path,
    dest: Path,
    os_tag: str,
    arch: str,
    *,
    fetch: bool,
) -> Path | None:
    folder, _name = vendor_rel(os_tag, arch)
    dest_bin = dest / "vendor" / "bin" / folder
    existing = existing_vendor_binary(root, os_tag, arch)
    if existing is not None:
        return copy_opencode_binary(existing, dest_bin)
    if not fetch:
        return None
    fetch_opencode(read_versions(root), os_tag, arch, dest_bin)
    return dest_bin


def stage(root: Path, dest: Path) -> Path:
    root = root.resolve()
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    review = root / "agents" / "code-reviewer.md"
    if not review.is_file():
        raise SystemExit(f"missing {review}")
    for name in INCLUDE:
        src = root / name
        if src.is_file():
            target = dest / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target)
            continue
        if not src.is_dir():
            raise SystemExit(f"missing {src}")
        for path in src.rglob("*"):
            if path.is_file() and ".git" not in path.parts:
                target = dest / path.relative_to(root)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
    return dest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Stage an offline OpenCoderman folder (agents, skills, CLI)."
    )
    parser.add_argument("--root", default=".")
    parser.add_argument("--os", choices=("linux", "windows", "darwin"), default="")
    parser.add_argument(
        "--out",
        default="",
        help="Full folder path. Default: dist/opencoderman-<version>-<os>/",
    )
    parser.add_argument("--out-dir", default="dist")
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Download the host CLI into vendor/bin (no pack folder).",
    )
    parser.add_argument(
        "--skip-binary",
        action="store_true",
        help="Do not download or copy the OpenCode CLI.",
    )
    args = parser.parse_args(argv)
    root = Path(args.root)
    host_os, host_arch = host_platform()
    os_tag = args.os or host_os
    arch = "x64" if os_tag == "windows" else host_arch
    ver = read_versions(root)
    if args.in_place:
        if args.skip_binary:
            raise SystemExit("--in-place needs the CLI; omit --skip-binary")
        folder, _name = vendor_rel(os_tag, arch)
        dest_bin = root / "vendor" / "bin" / folder
        fetch_opencode(ver, os_tag, arch, dest_bin)
        print(dest_bin.resolve())
        return 0
    if args.out:
        dest = Path(args.out)
    else:
        dest = Path(args.out_dir) / artifact_name(read_opencode_version(root), os_tag)
    path = stage(root, dest)
    if not args.skip_binary:
        attached = attach_cli(root, dest, os_tag, arch, fetch=True)
        if attached is None:
            raise SystemExit("failed to attach OpenCode CLI")
    print(path.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
