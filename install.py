#!/usr/bin/env python3
"""Replace-install OpenCoderman into the user OpenCode home.

Renames ~/.opencode to ~/.opencode_backup_YYYYMMDD_HHMMSS. A leftover
~/.config/opencode is also renamed (so OpenCode does not load a second
tree) but nothing is written back there. Any other OpenCode copy is
left in place; its directory is dropped from PATH so `opencode` does
not resolve there.

If vendor/bin has a CLI (CI artifact or vendor.sh), copy it to
~/.opencode/bin. If vendor is missing, reuse the binary from the
newest ~/.opencode_backup_*. Agents/skills-only checkouts skip the CLI.
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

STOCK_CONFIG = """{
  "$schema": "https://opencode.ai/config.json",
  "autoupdate": false,
  "plugin": []
}
"""

PATH_BEGIN = "# >>> opencoderman PATH >>>"
PATH_END = "# <<< opencoderman PATH <<<"
PATH_EXPORT = 'export PATH="$HOME/.opencode/bin:$PATH"'
UNIX_PROFILE_NAMES = (".profile", ".bashrc", ".zshrc")
BINARY_NAMES = ("opencode.exe", "opencode.cmd", "opencode.bat", "opencode.ps1", "opencode")
DEDICATED_DIR_NAMES = {".opencode", "opencode"}
PROTECTED_DIR_NAMES = {
    "windows",
    "system32",
    "syswow64",
    "program files",
    "program files (x86)",
    "usr",
    "bin",
    "sbin",
    "etc",
    "lib",
    "lib64",
}


def home(user_home: Path | None = None) -> Path:
    if user_home is not None:
        return Path(user_home)
    if os.name == "nt":
        profile = os.environ.get("USERPROFILE")
        if profile:
            return Path(profile)
    return Path.home()


def opencode_home(user_home: Path | None = None) -> Path:
    return home(user_home) / ".opencode"


def config_home(user_home: Path | None = None) -> Path:
    return home(user_home) / ".config" / "opencode"


def bin_dir(user_home: Path | None = None) -> Path:
    return opencode_home(user_home) / "bin"


def _norm_path(entry: str) -> str:
    text = (entry or "").strip().strip('"')
    if not text:
        return ""
    text = os.path.expandvars(os.path.expanduser(text))
    # PATH copies from the other OS (Git Bash, WSL, CI) use the other slash.
    text = text.replace("\\", "/") if os.name != "nt" else text.replace("/", "\\")
    path = Path(text)
    try:
        if path.exists():
            # Windows CI temp dirs often mix 8.3 (RUNNER~1) and long names.
            text = str(path.resolve())
    except OSError:
        pass
    return os.path.normcase(os.path.normpath(text))


def is_opencode_bin_entry(entry: str) -> bool:
    """True for the default home bin, or a dedicated …/opencode/bin dir."""
    norm = _norm_path(entry)
    if not norm:
        return False
    if norm.endswith(os.path.normcase(os.path.join(".opencode", "bin"))):
        return True
    parts = Path(norm).parts
    if len(parts) >= 2 and parts[-1].lower() == "bin" and parts[-2].lower() in DEDICATED_DIR_NAMES:
        return True
    if Path(norm).name.lower() in DEDICATED_DIR_NAMES:
        return True
    return False


def is_protected_dir(path: Path) -> bool:
    """True for OS dirs we must never strip from PATH or delete."""
    try:
        resolved = path.resolve()
    except OSError:
        return True
    if len(resolved.parts) <= (2 if os.name == "nt" else 1):
        return True
    name = resolved.name.lower()
    if name in {"windows", "system32", "syswow64", "program files", "program files (x86)"}:
        return True
    posix = resolved.as_posix().lower()
    if posix in {"/usr/bin", "/usr/local/bin", "/bin", "/sbin", "/usr/sbin", "/usr/local/sbin"}:
        return True
    return False


def dedicated_install_root(binary: Path) -> Path | None:
    """Return the tree to delete when the binary lives in its own OpenCode folder."""
    try:
        binary = binary.resolve()
    except OSError:
        return None
    parent = binary.parent
    if parent.name.lower() == "bin" and parent.parent.name.lower() in DEDICATED_DIR_NAMES:
        return parent.parent
    if parent.name.lower() in DEDICATED_DIR_NAMES:
        return parent
    return None


def dir_has_other_executables(directory: Path) -> bool:
    try:
        entries = list(directory.iterdir())
    except OSError:
        return True
    for item in entries:
        if not item.is_file():
            continue
        stem = item.stem.lower()
        suffix = item.suffix.lower()
        if stem == "opencode":
            continue
        if suffix in {"", ".exe", ".cmd", ".bat", ".com", ".ps1"} or item.name.lower() in BINARY_NAMES:
            return True
    return False


def split_path(raw: str, *, windows: bool | None = None) -> list[str]:
    sep = ";" if (os.name == "nt" if windows is None else windows) else os.pathsep
    return [part for part in str(raw or "").split(sep) if part]


def join_path(parts: list[str], *, windows: bool | None = None) -> str:
    sep = ";" if (os.name == "nt" if windows is None else windows) else os.pathsep
    return sep.join(parts)


def strip_opencode_bin_entries(
    parts: list[str],
    extra_drop: list[str] | None = None,
) -> list[str]:
    extra = {_norm_path(item) for item in (extra_drop or []) if _norm_path(item)}
    kept: list[str] = []
    for part in parts:
        if is_opencode_bin_entry(part):
            continue
        if _norm_path(part) in extra:
            continue
        kept.append(part)
    return kept


def opencode_binaries_in_dir(directory: Path) -> list[Path]:
    found: list[Path] = []
    try:
        if not directory.is_dir():
            return found
    except OSError:
        return found
    for name in BINARY_NAMES:
        candidate = directory / name
        try:
            if candidate.is_file():
                found.append(candidate)
        except OSError:
            continue
    return found


def find_opencode_binaries(
    *,
    user_home: Path | None = None,
    path_parts: list[str] | None = None,
) -> list[Path]:
    """Locate opencode executables from PATH, env, and the default homes."""
    found: list[Path] = []
    seen: set[str] = set()

    def add(path: Path) -> None:
        try:
            resolved = path.resolve()
        except OSError:
            return
        try:
            if not resolved.is_file():
                return
        except OSError:
            return
        if not resolved.name.lower().startswith("opencode"):
            return
        key = os.path.normcase(str(resolved))
        if key in seen:
            return
        seen.add(key)
        found.append(resolved)

    parts = list(path_parts or [])
    if user_home is None:
        parts.extend(split_path(os.environ.get("PATH", "")))
        for name in BINARY_NAMES:
            which = shutil.which(name)
            if which:
                add(Path(which))
        for key in ("OPENCODE_INSTALL", "OPENCODE_HOME", "OPENCODE_BIN"):
            raw = (os.environ.get(key) or "").strip()
            if not raw:
                continue
            hint = Path(os.path.expandvars(os.path.expanduser(raw)))
            if hint.is_file():
                add(hint)
            else:
                for binary in opencode_binaries_in_dir(hint / "bin"):
                    add(binary)
                for binary in opencode_binaries_in_dir(hint):
                    add(binary)

    for entry in parts:
        directory = Path(os.path.expandvars(os.path.expanduser(entry.strip().strip('"'))))
        for binary in opencode_binaries_in_dir(directory):
            add(binary)

    for base in (opencode_home(user_home), config_home(user_home)):
        for binary in opencode_binaries_in_dir(base / "bin"):
            add(binary)
        for binary in opencode_binaries_in_dir(base):
            add(binary)
    return found


def path_dirs_for_install(binary: Path) -> list[Path]:
    """PATH directories that belong to this install (safe to drop)."""
    dirs: list[Path] = [binary.parent]
    root = dedicated_install_root(binary)
    if root is not None:
        dirs.append(root)
        dirs.append(root / "bin")
    return dirs


def unlink_binary(path: Path) -> None:
    try:
        path.unlink()
        print(f"[OK] Removed binary {path}")
    except OSError as exc:
        print(f"[WARN] could not remove {path}: {exc}")


def _is_path_block_begin(line: str) -> bool:
    text = line.strip()
    return text.startswith("# >>> ") and text.endswith(" PATH >>>")


def _is_path_block_end(line: str) -> bool:
    text = line.strip()
    return text.startswith("# <<< ") and text.endswith(" PATH <<<")


def strip_profile_block(text: str) -> str:
    out: list[str] = []
    skipping = False
    for line in (text or "").splitlines():
        if _is_path_block_begin(line):
            skipping = True
            continue
        if skipping:
            if _is_path_block_end(line):
                skipping = False
            continue
        out.append(line)
    while out and out[-1] == "":
        out.pop()
    body = "\n".join(out)
    return body + ("\n" if body else "")


def insert_profile_block(text: str, *, bin_export: str = PATH_EXPORT) -> str:
    cleaned = strip_profile_block(text)
    block = f"{PATH_BEGIN}\n{bin_export}\n{PATH_END}\n"
    if cleaned and not cleaned.endswith("\n"):
        cleaned += "\n"
    return cleaned + ("\n" if cleaned else "") + block


def list_agent_files(root: Path) -> list[Path]:
    folder = Path(root) / "agents"
    if not folder.is_dir():
        raise FileNotFoundError(f"agents/ missing under {root}")
    files = sorted(path for path in folder.glob("*.md") if path.is_file())
    if not files:
        raise FileNotFoundError(f"no agent markdown under {folder}")
    return files


def list_skill_dirs(root: Path) -> list[Path]:
    folder = Path(root) / "skills"
    if not folder.is_dir():
        raise FileNotFoundError(f"skills/ missing under {root}")
    dirs = sorted(
        path for path in folder.iterdir() if path.is_dir() and (path / "SKILL.md").is_file()
    )
    if not dirs:
        raise FileNotFoundError(f"no skills with SKILL.md under {folder}")
    return dirs


def backup_destination(path: Path, when: datetime | None = None) -> Path:
    stamp = (when or datetime.now()).strftime("%Y%m%d_%H%M%S")
    dest = path.with_name(f"{path.name}_backup_{stamp}")
    extra = 2
    while dest.exists():
        dest = path.with_name(f"{path.name}_backup_{stamp}_{extra}")
        extra += 1
    return dest


def backup_home(path: Path) -> Path | None:
    """Move a default OpenCode home aside. Does not delete it."""
    if not path.exists():
        return None
    resolved = path.resolve()
    if resolved.name.lower() not in DEDICATED_DIR_NAMES:
        raise RuntimeError(f"refusing to move unexpected path {resolved}")
    if is_protected_dir(resolved):
        raise RuntimeError(f"refusing to move protected path {resolved}")
    dest = backup_destination(path)
    last: OSError | None = None
    for _ in range(8):
        try:
            shutil.move(str(path), str(dest))
            print(f"[OK] Moved {path} -> {dest}")
            return dest
        except OSError as exc:
            last = exc
            time.sleep(0.05)
    if last is not None:
        raise last
    return dest


def purge_discovered(
    *,
    user_home: Path | None = None,
    path_parts: list[str] | None = None,
) -> tuple[list[Path], list[str]]:
    """Move ~/.opencode and leftover ~/.config/opencode to backups.

    Nothing is written back under ~/.config/opencode. Any other OpenCode
    binary stays on disk. Its directory is returned so PATH can drop it;
    the user can add that path back later.
    """
    binaries = find_opencode_binaries(user_home=user_home, path_parts=path_parts)
    default_home = opencode_home(user_home).resolve()
    drop_dirs: list[str] = []
    seen_drop: set[str] = set()
    for binary in binaries:
        parent = binary.parent
        try:
            if default_home in parent.resolve().parents or parent.resolve() == default_home:
                continue
        except OSError:
            pass
        if is_protected_dir(parent):
            print(f"[OK] Left system PATH dir in place: {parent}")
            continue
        key = os.path.normcase(str(parent))
        if key not in seen_drop:
            seen_drop.add(key)
            drop_dirs.append(str(parent))
            print(f"[OK] Will unhook PATH dir (files kept): {parent}")
    removed: list[Path] = []
    for path in (opencode_home(user_home), config_home(user_home)):
        if path.exists():
            backed = backup_home(path)
            if backed is not None:
                removed.append(backed)
        else:
            print(f"[OK] Already absent {path}")
    return removed, drop_dirs


def purge_homes(user_home: Path | None = None) -> list[Path]:
    removed, _drop = purge_discovered(user_home=user_home)
    return removed


def read_user_path(*, user_home: Path | None = None) -> tuple[list[str], object]:
    if user_home is not None:
        store = home(user_home) / ".opencode-path"
        if store.is_file():
            return split_path(store.read_text(encoding="utf-8")), store
        return [], store
    if os.name == "nt":
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_READ | winreg.KEY_WRITE
        )
        try:
            try:
                raw, typ = winreg.QueryValueEx(key, "Path")
            except FileNotFoundError:
                raw, typ = "", winreg.REG_EXPAND_SZ
            return split_path(str(raw), windows=True), (key, typ)
        except Exception:
            key.Close()
            raise
    return split_path(os.environ.get("PATH", ""), windows=False), None


def write_user_path(parts: list[str], handle: object, *, user_home: Path | None = None) -> None:
    if user_home is not None:
        store = home(user_home) / ".opencode-path"
        store.parent.mkdir(parents=True, exist_ok=True)
        store.write_text(join_path(parts), encoding="utf-8")
        return
    if os.name == "nt":
        import winreg

        key, typ = handle  # type: ignore[misc]
        try:
            winreg.SetValueEx(key, "Path", 0, typ, join_path(parts, windows=True))
        finally:
            key.Close()
        return
    os.environ["PATH"] = join_path(parts, windows=False)


def close_path_handle(handle: object, *, user_home: Path | None = None) -> None:
    if user_home is not None or handle is None or os.name != "nt":
        return
    try:
        handle[0].Close()  # type: ignore[index]
    except Exception:
        pass


def remove_from_path(
    *,
    user_home: Path | None = None,
    extra_drop: list[str] | None = None,
) -> list[str]:
    parts, handle = read_user_path(user_home=user_home)
    try:
        kept = strip_opencode_bin_entries(parts, extra_drop=extra_drop)
        dropped = [part for part in parts if part not in kept]
        write_user_path(kept, handle, user_home=user_home)
    except Exception:
        close_path_handle(handle, user_home=user_home)
        raise
    base = home(user_home)
    for name in UNIX_PROFILE_NAMES:
        path = base / name
        if not path.is_file():
            continue
        old = path.read_text(encoding="utf-8", errors="replace")
        new = strip_profile_block(old)
        if new != old:
            path.write_text(new, encoding="utf-8")
            print(f"[OK] Stripped PATH block from {path}")
    if user_home is None:
        current = split_path(os.environ.get("PATH", ""))
        os.environ["PATH"] = join_path(
            strip_opencode_bin_entries(current, extra_drop=extra_drop)
        )
    for entry in dropped:
        print(f"[OK] Removed from PATH: {entry}")
    if not dropped:
        print("[OK] No OpenCode bin dir on PATH")
    return dropped


def prepend_to_path(*, user_home: Path | None = None) -> None:
    dest = bin_dir(user_home)
    dest.mkdir(parents=True, exist_ok=True)
    parts, handle = read_user_path(user_home=user_home)
    try:
        kept = strip_opencode_bin_entries(parts)
        write_user_path([str(dest)] + kept, handle, user_home=user_home)
    except Exception:
        close_path_handle(handle, user_home=user_home)
        raise
    if os.name != "nt":
        export = f'export PATH="{dest}:$PATH"'
        base = home(user_home)
        profile = base / ".profile"
        old = profile.read_text(encoding="utf-8", errors="replace") if profile.is_file() else ""
        profile.write_text(insert_profile_block(old, bin_export=export), encoding="utf-8")
        print(f"[OK] Wrote PATH block in {profile}")
    if user_home is None:
        current = strip_opencode_bin_entries(split_path(os.environ.get("PATH", "")))
        os.environ["PATH"] = join_path([str(dest)] + current)
    print(f"[OK] Prepended to PATH: {dest}")


def write_files(root: Path, user_home: Path | None = None) -> list[Path]:
    written: list[Path] = []
    base = opencode_home(user_home)
    for src in list_agent_files(root):
        dest = base / "agents" / src.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        written.append(dest)
        print(f"[OK] Agent {src.stem} -> {dest}")
    for skill in list_skill_dirs(root):
        dest = base / "skills" / skill.name / "SKILL.md"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text((skill / "SKILL.md").read_text(encoding="utf-8"), encoding="utf-8")
        written.append(dest)
        print(f"[OK] Skill {skill.name} -> {dest}")
    cfg = base / "opencode.json"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(STOCK_CONFIG, encoding="utf-8")
    written.append(cfg)
    return written


def binary_name() -> str:
    return "opencode.exe" if os.name == "nt" else "opencode"


def vendor_bin_tag() -> str:
    if os.name == "nt":
        return "windows"
    if sys.platform == "darwin":
        machine = platform.machine().lower()
        return "darwin-arm64" if machine in {"arm64", "aarch64"} else "darwin-x64"
    return "linux"


def vendor_binary(root: Path) -> Path | None:
    """Return the packaged CLI for this OS, or None if the pack has none."""
    vendor_bin = Path(root) / "vendor" / "bin"
    name = binary_name()
    candidates = (
        vendor_bin / vendor_bin_tag() / name,
        vendor_bin / name,
    )
    for path in candidates:
        if path.is_file():
            return path
    return None


def latest_backup_binary(user_home: Path | None = None) -> Path | None:
    base = home(user_home)
    name = binary_name()
    backups = sorted(base.glob(".opencode_backup_*"), reverse=True)
    for backup in backups:
        candidate = backup / "bin" / name
        if candidate.is_file():
            return candidate
    return None


def install_cli_binary(
    root: Path,
    *,
    user_home: Path | None = None,
    required: bool | None = None,
) -> Path | None:
    dest = bin_dir(user_home) / binary_name()
    src = vendor_binary(root) or latest_backup_binary(user_home)
    vendor_dir = Path(root) / "vendor" / "bin"
    if required is None:
        required = vendor_dir.is_dir()
    if src is None:
        if required:
            raise FileNotFoundError(
                f"No OpenCode binary under {vendor_dir}. "
                "Use a CI artifact, or run vendor.bat / vendor.sh "
                "(python packaging/build_artifact.py --in-place)."
            )
        print("[OK] No vendored OpenCode CLI (agents/skills only)")
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    if os.name != "nt":
        dest.chmod(dest.stat().st_mode | 0o111)
    print(f"[OK] Binary installed: {dest}")
    return dest


def install(
    root: Path,
    *,
    user_home: Path | None = None,
    require_binary: bool | None = None,
) -> Path:
    root = Path(root).expanduser().resolve()
    list_agent_files(root)
    list_skill_dirs(root)
    print("Purging previous OpenCode install (folders + PATH)…")
    parts, handle = read_user_path(user_home=user_home)
    close_path_handle(handle, user_home=user_home)
    _removed, drop_dirs = purge_discovered(user_home=user_home, path_parts=parts)
    remove_from_path(user_home=user_home, extra_drop=drop_dirs)
    print("Installing OpenCoderman…")
    write_files(root, user_home=user_home)
    install_cli_binary(root, user_home=user_home, required=require_binary)
    prepend_to_path(user_home=user_home)
    dest = opencode_home(user_home) / "agents" / "code-reviewer.md"
    if not dest.is_file():
        raise FileNotFoundError(f"code-reviewer agent missing after install: {dest}")
    alias = opencode_home(user_home) / "agents" / "gitlab-reviewer.md"
    if not alias.is_file():
        alias.write_text(dest.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"[OK] Agent gitlab-reviewer alias -> {alias}")
    return dest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Backup ~/.opencode, unhook other installs from PATH, then install OpenCoderman (CLI if vendored)."
    )
    parser.add_argument(
        "--root",
        default=str(Path(__file__).resolve().parent),
        help="Directory that contains agents/, skills/, and optionally vendor/bin",
    )
    parser.add_argument("--user-home", default="", help="Override home (tests / CI)")
    parser.add_argument(
        "--require-binary",
        action="store_true",
        help="Fail if vendor/bin and the backup home have no OpenCode CLI",
    )
    args = parser.parse_args(argv)
    user_home = Path(args.user_home).expanduser() if str(args.user_home).strip() else None
    try:
        dest = install(
            Path(args.root),
            user_home=user_home,
            require_binary=True if args.require_binary else None,
        )
    except (OSError, RuntimeError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    print(f"[OK] OpenCoderman ready: {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
