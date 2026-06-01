"""
Bundle scanner_sidecar.py into a standalone executable using Nuitka.

Tauri expects the sidecar binary at:
  src-tauri/binaries/scanner_sidecar-{target_triple}[.exe]

Usage:
  python scripts/bundle_sidecar.py
"""
import os
import platform
import shutil
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIDECAR_SCRIPT = os.path.join(PROJECT_ROOT, "scanner_sidecar.py")
BINARIES_DIR = os.path.join(PROJECT_ROOT, "src-tauri", "binaries")


def get_target_triple() -> str:
    """Return the Rust-style target triple for the current platform."""
    machine = platform.machine().lower()
    system = platform.system().lower()

    arch_map = {
        "x86_64": "x86_64",
        "amd64": "x86_64",
        "aarch64": "aarch64",
        "arm64": "aarch64",
    }
    arch = arch_map.get(machine, machine)

    if system == "windows":
        return f"{arch}-pc-windows-msvc"
    elif system == "linux":
        return f"{arch}-unknown-linux-gnu"
    elif system == "darwin":
        return f"{arch}-apple-darwin"
    else:
        raise RuntimeError(f"Unsupported platform: {system}")


def main():
    target_triple = get_target_triple()
    ext = ".exe" if platform.system() == "Windows" else ""
    output_name = f"scanner_sidecar-{target_triple}{ext}"

    print(f"[bundle_sidecar] Target triple: {target_triple}")
    print(f"[bundle_sidecar] Output: {output_name}")
    print(f"[bundle_sidecar] Using Nuitka")

    # Ensure output directory exists
    os.makedirs(BINARIES_DIR, exist_ok=True)

    # Build with Nuitka
    output_dir = os.path.join(PROJECT_ROOT, "nuitka_build")

    cmd = [
        sys.executable,
        "-m", "nuitka",
        "--onefile",
        "--onefile-no-compression",
        "--assume-yes-for-downloads",
        f"--output-dir={output_dir}",
        f"--output-filename=scanner_sidecar{ext}",
        "--remove-output",
        "--follow-imports",
        "--include-package-data=tesserocr",
        SIDECAR_SCRIPT,
    ]

    # tesserocr's Cython extension imports cysignals at the C level,
    # which Nuitka cannot trace statically — include it explicitly.
    # cysignals is Unix-only; the Windows wheel is built without it.
    if platform.system() != "Windows":
        cmd.insert(-1, "--include-package=tesserocr.cysignals")

    print(f"[bundle_sidecar] Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        print("[bundle_sidecar] Nuitka build failed!")
        sys.exit(1)

    # Move the built executable to the Tauri binaries directory
    src_exe = os.path.join(output_dir, f"scanner_sidecar{ext}")
    dst_exe = os.path.join(BINARIES_DIR, output_name)

    if os.path.exists(dst_exe):
        os.remove(dst_exe)

    shutil.move(src_exe, dst_exe)
    print(f"[bundle_sidecar] Sidecar bundled: {dst_exe}")
    print(f"[bundle_sidecar] Size: {os.path.getsize(dst_exe) / 1024 / 1024:.1f} MB")

    # Cleanup temp dirs
    shutil.rmtree(output_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
